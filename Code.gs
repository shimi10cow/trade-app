// =============================================
// Code.gs - トレード記録アプリ サーバーサイド
// Google Apps Scriptにそのまま貼り付けてください
// =============================================

const SPREADSHEET_ID = '1wPbALJwAZs7gUGs7anNvTqql2udX8lsMP51zSsHSkAM';
const ENTRIES_SHEET  = 'Entries';
const PAIRS_SHEET    = 'Pairs';
const DRIVE_FOLDER   = 'TradeImages';
const CACHE_KEY      = 'entries_cache';
const CACHE_TTL      = 300; // 5分

// =============================================
// エントリーポイント
// =============================================
const GAS_ACTIONS = {
  getEntries:       () => getEntries(),
  getPairs:         () => getPairs(),
  getAnalysisStats: () => getAnalysisStats(),
};

function doGet(e) {
  const action = e.parameter.action;

  // 画像URL解決（Entries_Images/xxx.jpg のようなパスからDrive URLを返す）
  if (action === 'getImageUrl') {
    const path = e.parameter.path || '';
    const result = { success: true, data: getImageUrlByPath(path) };
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  }

  let result;
  if (action && GAS_ACTIONS[action]) {
    result = { success: true, data: GAS_ACTIONS[action]() };
  } else {
    result = { success: false, error: 'Unknown action: ' + action };
  }

  const json = JSON.stringify(result);
  return ContentService
    .createTextOutput(json)
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const body = JSON.parse(e.postData.contents);
  const action = body.action;

  let result;
  if (action === 'saveEntry') {
    result = saveEntry(body.data);
  } else if (action === 'updateEntry') {
    result = updateEntry(body.entryId, body.data);
  } else if (action === 'deleteEntry') {
    result = deleteEntry(body.entryId);
  } else if (action === 'uploadImage') {
    result = uploadImage(body.base64Data, body.filename);
  } else if (action === 'getSimilarTrades') {
    result = getSimilarTrades(body.conditions);
  } else if (action === 'getImgBBKey') {
    const key = PropertiesService.getScriptProperties().getProperty('IMGBB_API_KEY') || '';
    result = { success: true, key: key };
  } else if (action === 'getGroqKey') {
    const key = PropertiesService.getScriptProperties().getProperty('GROQ_API_KEY') || '';
    result = { success: true, key: key };
  } else {
    result = { success: false, error: 'Unknown action' };
  }

  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// =============================================
// データ読み込み
// =============================================
function getEntries() {
  // キャッシュ確認
  const cache = CacheService.getScriptCache();
  const cached = cache.get(CACHE_KEY);
  if (cached) {
    return JSON.parse(cached);
  }

  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];

  const headers = data[0].map(h => String(h).trim());
  const entries = data.slice(1)
    .filter(row => row[0]) // EntryIDが空の行をスキップ
    .map(row => {
      const obj = {};
      headers.forEach((h, i) => {
        let val = row[i];
        if (val instanceof Date) {
          // Excelエポック（1899年）= 時刻のみのセル → HH:mm形式で返す
          if (val.getFullYear() <= 1900) {
            val = Utilities.formatDate(val, 'Asia/Tokyo', 'HH:mm');
          } else {
            val = Utilities.formatDate(val, 'Asia/Tokyo', 'yyyy/MM/dd');
          }
        }
        obj[h] = val !== null && val !== undefined ? String(val) : '';
      });
      return obj;
    });

  try {
    cache.put(CACHE_KEY, JSON.stringify(entries), CACHE_TTL);
  } catch(e) {
    // キャッシュサイズ超過は無視
  }
  return entries;
}

function getPairs() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(PAIRS_SHEET);
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];

  const headers = data[0].map(h => String(h).trim());
  return data.slice(1)
    .filter(row => row[0])
    .map(row => {
      const obj = {};
      headers.forEach((h, i) => {
        let val = row[i];
        if (val instanceof Date) {
          if (val.getFullYear() <= 1900) {
            val = Utilities.formatDate(val, 'Asia/Tokyo', 'HH:mm');
          } else {
            val = Utilities.formatDate(val, 'Asia/Tokyo', 'yyyy/MM/dd HH:mm');
          }
        }
        obj[h] = val !== null && val !== undefined ? String(val) : '';
      });
      return obj;
    });
}

// =============================================
// トレード保存
// =============================================
function saveEntry(entryData) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = ss.getSheetByName(ENTRIES_SHEET);

    // ヘッダー取得
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0]
      .map(h => String(h).trim());

    // EntryID生成（UUIDの先頭8文字）
    const entryId = Utilities.getUuid().substring(0, 8);
    const now = new Date();

    entryData['EntryID'] = entryId;

    // フォームから日付・時刻が送られていればそれを優先、なければ現在時刻
    if (!entryData['EntryDate'] || entryData['EntryDate'] === '') {
      entryData['EntryDate'] = Utilities.formatDate(now, 'Asia/Tokyo', 'yyyy/MM/dd');
    }
    if (!entryData['EntryTime'] || entryData['EntryTime'] === '') {
      entryData['EntryTime'] = Utilities.formatDate(now, 'Asia/Tokyo', 'HH:mm');
    }

    // ステータスが送られていなければデフォルト
    if (!entryData['ステータス'] || entryData['ステータス'] === '') {
      entryData['ステータス'] = '保有中';
    }

    // 列順に並べてappend
    const row = headers.map(h => entryData[h] !== undefined ? entryData[h] : '');
    sheet.appendRow(row);

    // キャッシュ削除
    CacheService.getScriptCache().remove(CACHE_KEY);

    return { success: true, entryId: entryId };
  } catch(e) {
    return { success: false, error: e.message };
  } finally {
    lock.releaseLock();
  }
}

function updateEntry(entryId, updateData) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
    const data = sheet.getDataRange().getValues();
    const headers = data[0].map(h => String(h).trim());
    const idCol = headers.indexOf('EntryID');

    if (idCol < 0) return { success: false, error: 'EntryID列が見つかりません' };

    for (let i = 1; i < data.length; i++) {
      if (String(data[i][idCol]).trim() === String(entryId).trim()) {
        Object.keys(updateData).forEach(key => {
          const col = headers.indexOf(key);
          if (col >= 0) {
            sheet.getRange(i + 1, col + 1).setValue(updateData[key]);
          }
        });
        CacheService.getScriptCache().remove(CACHE_KEY);
        return { success: true };
      }
    }
    return { success: false, error: 'EntryID not found: ' + entryId };
  } catch(e) {
    return { success: false, error: e.message };
  } finally {
    lock.releaseLock();
  }
}

function deleteEntry(entryId) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
    const data = sheet.getDataRange().getValues();
    const headers = data[0].map(h => String(h).trim());
    const idCol = headers.indexOf('EntryID');

    if (idCol < 0) return { success: false, error: 'EntryID列が見つかりません' };

    for (let i = 1; i < data.length; i++) {
      if (String(data[i][idCol]).trim() === String(entryId).trim()) {
        sheet.deleteRow(i + 1);
        CacheService.getScriptCache().remove(CACHE_KEY);
        return { success: true };
      }
    }
    return { success: false, error: 'EntryID not found: ' + entryId };
  } catch(e) {
    return { success: false, error: e.message };
  } finally {
    lock.releaseLock();
  }
}

// =============================================
// 類似トレード検索
// =============================================
function getSimilarTrades(conditions) {
  const entries = getEntries();
  const closed = entries.filter(e => e['勝敗'] === '勝ち' || e['勝敗'] === '負け');

  const scored = closed.map(e => {
    let score = 0;

    // 方向一致: 30点
    if (e['Direction'] === conditions.direction) score += 30;

    // 時間足方向: D1=15, H4=15, H1=10
    if (e['D1'] === conditions.D1) score += 15;
    if (e['H4'] === conditions.H4) score += 15;
    if (e['H1'] === conditions.H1) score += 10;

    // MA条件: 各5点
    if (e['H4MA480.1200'] === conditions.H4MA480)   score += 5;
    if (e['H4MA乖離']    === conditions.H4MA_kairi) score += 5;
    if (e['H1MA20.80']   === conditions.H1MA2080)   score += 5;
    if (e['H4MA20.80']   === conditions.H4MA2080)   score += 5;

    // エントリー根拠: 各2.5点 × 6 = 15点
    if (e['水平線D1.H4']  === conditions.suihei)    score += 2.5;
    if (e['H1MAエリア']   === conditions.H1MA_area)  score += 2.5;
    if (e['TL推進']       === conditions.TL_suishin) score += 2.5;
    if (e['TL逆トレ']     === conditions.TL_gyaku)   score += 2.5;
    if (e['TL_M15']       === conditions.TL_M15)     score += 2.5;
    if (e['直近波理論']   === conditions.chikinha)   score += 2.5;

    // 上位足リスク: 5点
    if (e['上位足リスク'] === conditions.joui_risk) score += 5;

    return { entry: e, score: Math.round(score) };
  })
  .filter(s => s.score >= 40)
  .sort((a, b) => b.score - a.score)
  .slice(0, 5);

  // 統計計算
  const total = scored.length;
  const wins  = scored.filter(s => s.entry['勝敗'] === '勝ち').length;
  const winRate  = total > 0 ? Math.round(wins / total * 100) : null;
  const avgPips  = total > 0
    ? Math.round(scored.reduce((s, t) => s + (Number(t.entry['実取得pips']) || 0), 0) / total)
    : null;
  const avgRR = total > 0
    ? Math.round(scored.reduce((s, t) => s + (Number(t.entry['実RR']) || 0), 0) / total * 10) / 10
    : null;

  // アドバイス文章生成
  const advice = buildAdvice(conditions, scored, winRate, avgPips);

  return {
    winRate, avgPips, avgRR, total,
    advice,
    trades: scored.map(s => ({
      entryId:   s.entry['EntryID'],
      pair:      s.entry['PairName'],
      direction: s.entry['Direction'],
      date:      s.entry['EntryDate'],
      timeZone:  s.entry['時間帯'],
      winLoss:   s.entry['勝敗'],
      pips:      s.entry['実取得pips'],
      pl:        s.entry['損益'],
      review:    s.entry['エントリー振り返り'],
      exitReview: s.entry['決済振り返り'],
      score:     s.score
    }))
  };
}

function buildAdvice(cond, scored, winRate, avgPips) {
  const parts = [];

  // 方向一致チェック
  const dirArrow = cond.direction === 'Sell' ? '↓' : '↑';
  if (cond.D1 === dirArrow && cond.H4 === dirArrow) {
    parts.push(`D1${cond.D1}H4${cond.H4}で${cond.direction}方向が揃っています。`);
  } else if (cond.D1 !== dirArrow || cond.H4 !== dirArrow) {
    parts.push(`⚠ 上位足と方向が一致していない部分があります。`);
  }

  // 根拠の強さ
  const goodConds = ['suihei', 'H1MA_area', 'TL_suishin', 'TL_gyaku', 'TL_M15', 'chikinha']
    .filter(k => cond[k] === '〇').length;
  if (goodConds >= 4) parts.push(`エントリー根拠が${goodConds}つ揃っています。`);
  else if (goodConds <= 1) parts.push(`⚠ エントリー根拠が少ない（${goodConds}つ）。`);

  // 乖離警告
  if (cond.H4MA_kairi === '✕') parts.push(`乖離あり。過去データでは勝率が下がる傾向があります。`);

  // 統計
  if (winRate !== null) {
    parts.push(`類似パターン${scored.length}件：勝率${winRate}%、平均${avgPips >= 0 ? '+' : ''}${avgPips}pips。`);
  } else {
    parts.push(`類似パターンのデータがまだ少ないです。`);
  }

  return parts.join(' ');
}

// =============================================
// 全体統計
// =============================================
function getAnalysisStats() {
  const entries = getEntries();
  const closed  = entries.filter(e => e['勝敗'] === '勝ち' || e['勝敗'] === '負け');

  const total    = closed.length;
  const wins     = closed.filter(e => e['勝敗'] === '勝ち').length;
  const winRate  = total > 0 ? Math.round(wins / total * 100) : 0;
  const totalPips = closed.reduce((s, e) => s + (Number(e['実取得pips']) || 0), 0);
  const avgRR    = total > 0
    ? Math.round(closed.reduce((s, e) => s + (Number(e['実RR']) || 0), 0) / total * 10) / 10
    : 0;

  // 月次集計
  const monthly = {};
  closed.forEach(e => {
    const d = e['EntryDate'];
    const month = d ? d.substring(0, 7).replace('/', '-') : '不明';
    if (!monthly[month]) monthly[month] = 0;
    monthly[month] += Number(e['実取得pips']) || 0;
  });

  // 条件別勝率（上位5件）
  const condStats = computeConditionStats(closed);

  // インサイト生成
  const insights = buildInsights(closed, condStats);

  return { total, wins, winRate, totalPips, avgRR, monthly, condStats, insights };
}

function computeConditionStats(entries) {
  const conditions = [
    { key: 'H4MA480.1200', goodVal: '◎', label: 'H4MA480 良好' },
    { key: 'H4MA乖離',    goodVal: '✕', label: '乖離なし' },
    { key: '水平線D1.H4', goodVal: '〇', label: '水平線あり' },
    { key: 'H1MAエリア',  goodVal: '〇', label: 'H1MAエリアあり' },
    { key: 'TL逆トレ',   goodVal: '〇', label: 'TL逆トレあり' },
    { key: 'TL_M15',     goodVal: '〇', label: 'TL M15あり' },
    { key: '上位足リスク', goodVal: 'ナシ', label: '上位足リスクなし' },
  ];

  return conditions.map(c => {
    const subset = entries.filter(e => e[c.key] === c.goodVal);
    const w = subset.filter(e => e['勝敗'] === '勝ち').length;
    return {
      label:   c.label,
      count:   subset.length,
      winRate: subset.length > 0 ? Math.round(w / subset.length * 100) : 0
    };
  }).sort((a, b) => b.winRate - a.winRate);
}

function buildInsights(entries, condStats) {
  const insights = [];

  // ビビり決済の損失試算
  const bibiTrades = entries.filter(e => e['決済振り返り'] === 'ビビり決済');
  if (bibiTrades.length > 0) {
    const lostPips = bibiTrades.reduce((s, e) => {
      const actual = Number(e['実取得pips']) || 0;
      const target = Number(e['TakeProfitPips']) || 0;
      return s + Math.max(0, target - actual);
    }, 0);
    if (lostPips > 0) {
      insights.push(`「ビビり決済」${bibiTrades.length}件で約${lostPips}pips機会損失。`);
    }
  }

  // 乖離ありの勝率
  const kairiEntries = entries.filter(e => e['H4MA乖離'] === '◎');
  if (kairiEntries.length >= 3) {
    const kw = kairiEntries.filter(e => e['勝敗'] === '勝ち').length;
    const kr = Math.round(kw / kairiEntries.length * 100);
    if (kr < 55) {
      insights.push(`H4MA乖離ありの勝率${kr}%（${kairiEntries.length}件）。見送ると改善の可能性。`);
    }
  }

  // 最高勝率条件
  if (condStats.length > 0 && condStats[0].winRate >= 65) {
    insights.push(`「${condStats[0].label}」時の勝率${condStats[0].winRate}%（${condStats[0].count}件）が最高。`);
  }

  return insights;
}

// =============================================
// DriveApp 認証テスト（GASエディタから一度手動で実行してください）
// 実行すると OAuth 認証ダイアログが表示されます → 承認してください
// =============================================
function testDriveAuth() {
  var root = DriveApp.getRootFolder();
  Logger.log('✅ DriveApp 認証OK: ' + root.getName());
  // TradeImagesフォルダの確認
  var folders = DriveApp.getFoldersByName('TradeImages');
  Logger.log('TradeImages フォルダ: ' + (folders.hasNext() ? '存在する' : '存在しない'));
}

// =============================================
// 画像URL解決（パス → base64 data URL）
// DriveApp不要：UrlFetchApp + Drive REST API で認証問題を回避
// =============================================
function getImageUrlByPath(path) {
  if (!path) return { url: '' };
  try {
    const token = ScriptApp.getOAuthToken();
    const parts = path.split('/');
    const folderName = parts[0];
    const fileName   = parts[parts.length - 1];

    let fileId = null;

    // ★ drive_images/FILEID.jpg → ファイルIDが直接わかる
    if (folderName === 'drive_images') {
      fileId = fileName.replace(/\.(jpg|jpeg|png|gif|webp)$/i, '');
    } else {
      // Drive REST API でファイル名検索（AppSheet: Entries_Images/xxx.jpg など）
      const safeName = fileName.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
      const q = encodeURIComponent("name='" + safeName + "' and trashed=false");
      const listRes = UrlFetchApp.fetch(
        'https://www.googleapis.com/drive/v3/files?q=' + q + '&fields=files(id)&pageSize=5',
        { headers: { 'Authorization': 'Bearer ' + token }, muteHttpExceptions: true }
      );
      const listData = JSON.parse(listRes.getContentText());
      if (listData.files && listData.files.length > 0) {
        fileId = listData.files[0].id;
      }
    }

    if (!fileId) return { url: '', error: 'file not found: ' + fileName };

    // Drive REST API でファイル内容取得
    const mediaRes = UrlFetchApp.fetch(
      'https://www.googleapis.com/drive/v3/files/' + fileId + '?alt=media',
      { headers: { 'Authorization': 'Bearer ' + token }, muteHttpExceptions: true }
    );

    if (mediaRes.getResponseCode() !== 200) {
      return { url: '', error: 'download failed: ' + mediaRes.getResponseCode() };
    }

    const bytes = mediaRes.getContent();

    // 3MB超はスキップ（GASタイムアウト防止）
    if (bytes.length > 3 * 1024 * 1024) {
      return { url: '', error: 'file too large: ' + bytes.length + ' bytes' };
    }

    const base64 = Utilities.base64Encode(bytes);
    return { url: 'data:image/jpeg;base64,' + base64 };

  } catch(e) {
    return { url: '', error: e.message };
  }
}

// =============================================
// 画像アップロード（Google Drive）
// =============================================
function uploadImage(base64Data, filename) {
  try {
    // DriveApp不使用 → Drive REST API + UrlFetchApp で実装
    // 必要スコープ: drive.file（フルdriveスコープ不要）
    const base64 = base64Data.replace(/^data:image\/\w+;base64,/, '');
    const token  = ScriptApp.getOAuthToken();

    // マルチパートアップロード
    const boundary = 'trade_app_' + Utilities.getUuid().replace(/-/g,'');
    const metadata = JSON.stringify({ name: filename, mimeType: 'image/jpeg' });
    const body =
      '--' + boundary + '\r\n' +
      'Content-Type: application/json; charset=UTF-8\r\n\r\n' +
      metadata + '\r\n' +
      '--' + boundary + '\r\n' +
      'Content-Type: image/jpeg\r\n' +
      'Content-Transfer-Encoding: base64\r\n\r\n' +
      base64 + '\r\n' +
      '--' + boundary + '--';

    const uploadRes = UrlFetchApp.fetch(
      'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart',
      {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type' : 'multipart/related; boundary=' + boundary
        },
        payload: body,
        muteHttpExceptions: true
      }
    );
    const uploaded = JSON.parse(uploadRes.getContentText());
    if (!uploaded.id) throw new Error('Upload failed: ' + uploadRes.getContentText());

    // 全員に閲覧権限を付与
    UrlFetchApp.fetch(
      'https://www.googleapis.com/drive/v3/files/' + uploaded.id + '/permissions',
      {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type' : 'application/json'
        },
        payload: JSON.stringify({ role: 'reader', type: 'anyone' }),
        muteHttpExceptions: true
      }
    );

    return { success: true, fileId: uploaded.id };
  } catch(e) {
    return { success: false, error: e.message };
  }
}


// =============================================
