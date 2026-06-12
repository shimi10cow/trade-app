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
  getIdeas:         () => getIdeas(),
  getReviews:       () => getReviews(),
  getCalendar:      () => getCalendarEvents(),
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
  } else if (action === 'updatePair') {
    result = updatePair(body.pairName, body.data);
  } else if (action === 'saveIdea') {
    result = saveIdea(body.data);
  } else if (action === 'updateIdea') {
    result = updateIdea(body.ideaId, body.data);
  } else if (action === 'deleteIdea') {
    result = deleteIdea(body.ideaId);
  } else if (action === 'saveReview') {
    result = saveReview(body.data);
  } else if (action === 'updateReview') {
    result = updateReview(body.reviewId, body.data);
  } else if (action === 'recalculateCaseBScores') {
    result = recalculateCaseBScores();
  } else if (action === 'migrateExitRefPerfect') {
    result = migrateExitRefPerfect();
  } else if (action === 'recalculateAllScores') {
    result = recalculateAllScores(body.config);
  } else if (action === 'ensureScoreColumns') {
    result = ensureScoreColumns(body.config);
  } else if (action === 'ensureColumns') {
    result = ensureNamedColumns(body.columns);
  } else if (action === 'ensurePairColumns') {
    result = ensurePairColumns(body.columns);
  } else if (action === 'migrateEntryFields') {
    result = migrateEntryFields();
  } else if (action === 'migrateEntryFieldsV2') {
    result = migrateEntryFieldsV2();
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

function updatePair(pairName, data) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(PAIRS_SHEET);
  const sheetData = sheet.getDataRange().getValues();
  const headers = sheetData[0].map(h => String(h).trim());
  const pairCol = headers.indexOf('PairName（元）') >= 0 ? headers.indexOf('PairName（元）') : headers.indexOf('PairName');
  if (pairCol < 0) return { success: false, error: 'PairName column not found' };

  const rowIdx = sheetData.slice(1).findIndex(r => String(r[pairCol]) === String(pairName));
  if (rowIdx < 0) return { success: false, error: 'Pair not found: ' + pairName };

  const sheetRow = rowIdx + 2; // 1-indexed + header row
  Object.keys(data).forEach(key => {
    const colIdx = headers.indexOf(key);
    if (colIdx >= 0) {
      sheet.getRange(sheetRow, colIdx + 1).setValue(data[key]);
    }
  });
  return { success: true };
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
// 勝敗列一括更新（±10pips閾値）
// GASエディタから手動実行: updateWinLossColumn()
// =============================================
function updateWinLossColumn() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(ENTRIES_SHEET);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return;

  // AQ列(実取得pips) = 43列目、AP列(勝敗) = 42列目
  const pipCol = 43;  // AQ
  const resultCol = 42; // AP

  const pipValues = sheet.getRange(2, pipCol, lastRow - 1, 1).getValues();
  const updates = pipValues.map(([pips]) => {
    if (pips === '' || pips === null) return [''];
    const p = parseFloat(pips);
    if (isNaN(p)) return [''];
    return [p > 10 ? '勝ち' : (p < -10 ? '負け' : '引き分け')];
  });

  sheet.getRange(2, resultCol, updates.length, 1).setValues(updates);
  Logger.log('勝敗列を' + updates.length + '件更新しました');
}

// =============================================
// アイデアメモ (Ideas シート)
// 列はヘッダー名で解決（ID, 日付, 本文, 画像URL, ステータス, 画像URL2, 画像URL3, お気に入り）
// =============================================
const IDEAS_SHEET = 'Ideas';
const IDEA_FIELDS = ['日付','本文','画像URL','ステータス','画像URL2','画像URL3','お気に入り'];

function getOrCreateIdeasSheet() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = ss.getSheetByName(IDEAS_SHEET);
  if (!sheet) {
    sheet = ss.insertSheet(IDEAS_SHEET);
    sheet.getRange(1, 1, 1, 1 + IDEA_FIELDS.length).setValues([['ID'].concat(IDEA_FIELDS)]);
  } else {
    // 足りないヘッダーを末尾に追加
    const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
    IDEA_FIELDS.forEach(f => {
      if (headers.indexOf(f) === -1) {
        sheet.getRange(1, sheet.getLastColumn() + 1).setValue(f);
        headers.push(f);
      }
    });
  }
  return sheet;
}

// ヘッダー名 → 0始まり列indexのマップ
function ideaHeaderMap(sheet) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(h => String(h).trim());
  const map = {};
  headers.forEach((h, i) => { if (h) map[h] = i; });
  return map;
}

function getIdeas() {
  const sheet = getOrCreateIdeasSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];
  const map = ideaHeaderMap(sheet);
  const rows = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();
  return rows
    .filter(r => r[map['ID'] || 0] !== '')
    .map(r => {
      const obj = { id: String(r[map['ID'] || 0]) };
      IDEA_FIELDS.forEach(f => {
        let v = map[f] !== undefined ? r[map[f]] : '';
        if (v instanceof Date) v = Utilities.formatDate(v, 'Asia/Tokyo', 'yyyy-MM-dd');
        obj[f] = String(v || (f === 'ステータス' ? '未解決' : ''));
      });
      return obj;
    });
}

function ideaRowValues(sheet, map, id, data) {
  const row = new Array(sheet.getLastColumn()).fill('');
  row[map['ID'] || 0] = String(id);
  IDEA_FIELDS.forEach(f => {
    if (map[f] !== undefined) row[map[f]] = data[f] !== undefined ? data[f] : '';
  });
  return row;
}

function saveIdea(data) {
  const sheet = getOrCreateIdeasSheet();
  const map = ideaHeaderMap(sheet);
  const id = String(Date.now());
  if (!data['ステータス']) data['ステータス'] = '未解決';
  const range = sheet.getRange(sheet.getLastRow() + 1, 1, 1, sheet.getLastColumn());
  range.setNumberFormat('@');
  range.setValues([ideaRowValues(sheet, map, id, data)]);
  return { success: true, id: id };
}

function updateIdea(ideaId, data) {
  const sheet = getOrCreateIdeasSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return { success: false, error: 'Not found' };
  const map = ideaHeaderMap(sheet);
  const idCol = (map['ID'] || 0) + 1;
  const ids = sheet.getRange(2, idCol, lastRow - 1, 1).getValues().flat();
  const rowIdx = ids.findIndex(id => String(id) === String(ideaId));
  if (rowIdx === -1) return { success: false, error: 'Not found' };
  if (!data['ステータス']) data['ステータス'] = '未解決';
  sheet.getRange(rowIdx + 2, 1, 1, sheet.getLastColumn())
    .setValues([ideaRowValues(sheet, map, ideaId, data)]);
  return { success: true };
}

function deleteIdea(ideaId) {
  const sheet = getOrCreateIdeasSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return { success: false, error: 'Not found' };
  const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues().flat();
  // 数値・文字列どちらで保存されていても一致させる
  const rowIdx = ids.findIndex(id => String(id) === String(ideaId));
  if (rowIdx === -1) return { success: false, error: 'Not found' };
  sheet.deleteRow(rowIdx + 2);
  return { success: true };
}
// =============================================

// =============================================
// 経済指標カレンダー（Forex Factory 週間JSON・非公式）
// 6時間キャッシュ。取得失敗時は error を返すだけ（フォールバックなし）
// =============================================
const CALENDAR_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json';
const CALENDAR_CACHE_KEY = 'calendar_cache_v1';

function getCalendarEvents() {
  const cache = CacheService.getScriptCache();
  const cached = cache.get(CALENDAR_CACHE_KEY);
  if (cached) {
    try { return JSON.parse(cached); } catch(e) {}
  }

  try {
    const res = UrlFetchApp.fetch(CALENDAR_URL, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) {
      return { error: 'HTTP ' + res.getResponseCode(), events: [] };
    }
    const raw = JSON.parse(res.getContentText());
    const events = raw
      .filter(e => e && e.date && e.country)
      .map(e => ({
        title:    String(e.title || ''),
        currency: String(e.country || '').toUpperCase(),
        datetime: Utilities.formatDate(new Date(e.date), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm'),
        impact:   String(e.impact || ''),
      }))
      .filter(e => e.impact === 'High' || e.impact === 'Medium');

    const result = { events: events };
    try { cache.put(CALENDAR_CACHE_KEY, JSON.stringify(result), 21600); } catch(e) {} // 6時間
    return result;
  } catch(e) {
    return { error: e.message, events: [] };
  }
}

// =============================================
// 週次・月次レビュー (Reviews シート)
// 列: A=ID, B=種別(weekly/monthly), C=期間キー, D=メモ, E=約束, F=約束判定(JSON), G=作成日
// =============================================
const REVIEWS_SHEET = 'Reviews';

function getOrCreateReviewsSheet() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = ss.getSheetByName(REVIEWS_SHEET);
  if (!sheet) {
    sheet = ss.insertSheet(REVIEWS_SHEET);
    sheet.getRange(1, 1, 1, 7).setValues([['ID','種別','期間キー','メモ','約束','約束判定','作成日']]);
  }
  return sheet;
}

function getReviews() {
  const sheet = getOrCreateReviewsSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];
  const rows = sheet.getRange(2, 1, lastRow - 1, 7).getValues();
  return rows
    .filter(r => r[0] !== '')
    .map(r => ({
      id:        String(r[0]),
      種別:      String(r[1] || ''),
      期間キー:  r[2] instanceof Date
                   ? Utilities.formatDate(r[2], 'Asia/Tokyo', 'yyyy-MM-dd')
                   : String(r[2] || ''),
      メモ:      String(r[3] || ''),
      約束:      String(r[4] || ''),
      約束判定:  String(r[5] || ''),
      作成日:    r[6] instanceof Date
                   ? Utilities.formatDate(r[6], 'Asia/Tokyo', 'yyyy-MM-dd HH:mm')
                   : String(r[6] || ''),
    }));
}

function saveReview(data) {
  const sheet = getOrCreateReviewsSheet();
  const id = String(Date.now());
  const range = sheet.getRange(sheet.getLastRow() + 1, 1, 1, 7);
  range.setNumberFormat('@');
  range.setValues([[
    id,
    data['種別'] || 'weekly',
    data['期間キー'] || '',
    data['メモ'] || '',
    data['約束'] || '',
    data['約束判定'] || '',
    Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm'),
  ]]);
  return { success: true, id: id };
}

function updateReview(reviewId, data) {
  const sheet = getOrCreateReviewsSheet();
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return { success: false, error: 'Not found' };
  const ids = sheet.getRange(2, 1, lastRow - 1, 1).getValues().flat();
  const rowIdx = ids.findIndex(id => String(id) === String(reviewId));
  if (rowIdx === -1) return { success: false, error: 'Not found' };
  const row = rowIdx + 2;
  const current = sheet.getRange(row, 1, 1, 7).getValues()[0];
  sheet.getRange(row, 1, 1, 7).setValues([[
    String(reviewId),
    data['種別']     !== undefined ? data['種別']     : current[1],
    data['期間キー'] !== undefined ? data['期間キー'] : current[2],
    data['メモ']     !== undefined ? data['メモ']     : current[3],
    data['約束']     !== undefined ? data['約束']     : current[4],
    data['約束判定'] !== undefined ? data['約束判定'] : current[5],
    current[6],
  ]]);
  return { success: true };
}

// =============================================
// スコア全件再計算
// =============================================
function recalculateAllScores(config) {
  if (!config || !Array.isArray(config) || config.length === 0) {
    return { success: false, error: 'config が不正です' };
  }

  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'Entriesシートが見つかりません' };

  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return { success: true, updated: 0 };

  const headers = data[0].map(String);
  const scoreCol = headers.indexOf('エントリースコア');
  if (scoreCol === -1) return { success: false, error: 'エントリースコア列が見つかりません' };

  let updated = 0;
  for (let row = 1; row < data.length; row++) {
    const entry = {};
    headers.forEach((h, i) => { entry[h] = data[row][i]; });

    let score = 0;
    config.forEach(item => {
      if (item.enabled === false) return; // 無効項目はスキップ
      const keys = [item.key].concat(item.aliases || []);
      let val = null;
      for (const k of keys) {
        if (entry[k] !== undefined && entry[k] !== '') { val = String(entry[k]).trim(); break; }
      }
      if (val === null) return;
      // 〇(U+3007) と ○(U+25CB) の表記ゆれを正規化
      val = val.replace(/〇/g, '○');
      if (val === item.okLabel) score += Number(item.okScore) || 0;
      else if (val === item.ngLabel) score += Number(item.ngScore) || 0;
    });

    sheet.getRange(row + 1, scoreCol + 1).setValue(score);
    updated++;
  }

  try { CacheService.getScriptCache().remove(CACHE_KEY); } catch(e) {}

  return { success: true, updated };
}

// =============================================
// Case B スコア直接再計算（文字コード問題を回避）
// =============================================
function recalculateCaseBScores() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'シートが見つかりません' };

  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return { success: true, updated: 0 };

  const headers = data[0].map(function(h) { return String(h).trim(); });

  function colIdx(name) { return headers.indexOf(name); }

  const scoreCol  = colIdx('エントリースコア');
  const suiCol    = colIdx('水平線D1.H4');
  const h1maCol   = colIdx('H1MAエリア');
  const tlpCol    = colIdx('トレンドライン（推進）');
  const tlrCol    = colIdx('トレンドライン（逆トレ）');
  const m15Col    = colIdx('トレンドライン（M15）');
  const h4waveCol = colIdx('H4の5波以降');
  const riskCol   = colIdx('上位足リスク');

  if (scoreCol === -1) return { success: false, error: 'エントリースコア列が見つかりません', headers: headers.join(',') };

  function isOk(val) {
    var s = String(val).trim();
    return s === '〇' || s === '○' || s === '◎';
  }

  var updated = 0;
  var updates = [];
  for (var row = 1; row < data.length; row++) {
    if (!data[row][0]) continue; // EntryIDなし行はスキップ
    var score = 0;
    if (suiCol >= 0    && isOk(data[row][suiCol]))    score += 1;
    if (h1maCol >= 0   && isOk(data[row][h1maCol]))   score += 1;
    if (tlpCol >= 0    && isOk(data[row][tlpCol]))    score += 2;
    if (tlrCol >= 0    && isOk(data[row][tlrCol]))    score += 1;
    if (m15Col >= 0    && isOk(data[row][m15Col]))    score += 1;
    if (h4waveCol >= 0 && isOk(data[row][h4waveCol])) score -= 1;
    if (riskCol >= 0   && String(data[row][riskCol]).trim() === 'アリ') score -= 1; // アリ
    updates.push([score]);
    updated++;
  }

  // バッチ書き込み
  if (updates.length > 0) {
    sheet.getRange(2, scoreCol + 1, updates.length, 1).setValues(updates);
  }

  try { CacheService.getScriptCache().remove(CACHE_KEY); } catch(e) {}
  return { success: true, updated: updated };
}

// =============================================
// 決済振り返り「完璧！」→「決済タイミングOK」置換
// =============================================
function migrateExitRefPerfect() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'シートが見つかりません' };
  const data = sheet.getDataRange().getValues();
  const headers = data[0].map(function(h) { return String(h).trim(); });
  const col = headers.indexOf('決済振り返り');
  if (col === -1) return { success: false, error: '決済振り返り列が見つかりません' };
  var updated = 0;
  for (var row = 1; row < data.length; row++) {
    if (String(data[row][col]).trim() === '完璧！') {
      sheet.getRange(row + 1, col + 1).setValue('決済タイミングOK');
      updated++;
    }
  }
  try { CacheService.getScriptCache().remove(CACHE_KEY); } catch(e) {}
  return { success: true, updated: updated };
}

// =============================================
// 任意の列名をEntriesシートに追加（なければ）
// =============================================
function ensureNamedColumns(columns) {
  if (!columns || !Array.isArray(columns)) return { success: false, error: 'columns不正' };
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'Entriesシートが見つかりません' };
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
  let added = 0;
  columns.forEach(col => {
    if (!headers.includes(col)) {
      sheet.getRange(1, sheet.getLastColumn() + 1).setValue(col);
      headers.push(col);
      added++;
    }
  });
  return { success: true, added };
}

// =============================================
// 任意の列名をPairsシートに追加（なければ）
// =============================================
function ensurePairColumns(columns) {
  if (!columns || !Array.isArray(columns)) return { success: false, error: 'columns不正' };
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(PAIRS_SHEET);
  if (!sheet) return { success: false, error: 'Pairsシートが見つかりません' };
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
  let added = 0;
  columns.forEach(col => {
    if (!headers.includes(col)) {
      sheet.getRange(1, sheet.getLastColumn() + 1).setValue(col);
      headers.push(col);
      added++;
    }
  });
  return { success: true, added };
}

// =============================================
// スコア列をEntriesシートに追加（なければ）
// =============================================
function ensureScoreColumns(config) {
  if (!config || !Array.isArray(config)) return { success: false, error: 'config不正' };

  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'Entriesシートが見つかりません' };

  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
  let added = 0;

  config.forEach(item => {
    const keys = [item.key].concat(item.aliases || []);
    const exists = keys.some(k => headers.includes(k));
    if (!exists) {
      sheet.getRange(1, sheet.getLastColumn() + 1).setValue(item.key);
      headers.push(item.key);
      added++;
    }
  });

  return { success: true, added };
}

// =============================================
// エントリー振り返りフィールド移行（GASエディタから手動実行）
// =============================================
function migrateEntryFields() {
  var sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'Entriesシートが見つかりません' };

  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return { success: true, updated: 0 };

  var entryRefCol = headers.indexOf('エントリー振り返り');
  var exitRefCol  = headers.indexOf('決済振り返り');
  if (entryRefCol < 0) return { success: false, error: 'エントリー振り返り列が見つかりません' };

  // 新列インデックスを取得（なければ追加）
  function getOrAddCol(name) {
    var idx = headers.indexOf(name);
    if (idx < 0) {
      sheet.getRange(1, sheet.getLastColumn() + 1).setValue(name);
      idx = sheet.getLastColumn() - 1;
      headers.push(name);
    }
    return idx;
  }
  var colDow     = getOrAddCol('ダウ認識');
  var colTlPush  = getOrAddCol('TL推進認識');
  var colTlRev   = getOrAddCol('TL逆トレ認識');
  var colTlM15   = getOrAddCol('TL(M15)認識');
  var colUpper   = getOrAddCol('上位足リスク認識');
  var colLotSl   = getOrAddCol('Lot/損切り設定');

  var data = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();
  var updated = 0;

  data.forEach(function(row, i) {
    var entryRef = String(row[entryRefCol] || '').trim();
    var exitRef  = exitRefCol >= 0 ? String(row[exitRefCol] || '').trim() : '';
    var rowNum = i + 2;

    // ① エントリー振り返り の移行
    var newEntryRef = entryRef;
    var dow = '', tlPush = '', tlRev = '', tlM15 = '', upper = '', lotSl = '';

    if (entryRef === '完璧！') {
      newEntryRef = '完璧エントリー';
      dow = tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === 'アーリー') {
      newEntryRef = 'アーリー';
      dow = tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === 'レイト') {
      newEntryRef = 'レイト';
      dow = tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === 'トレンドライン認識甘い') {
      newEntryRef = '完璧エントリー';
      dow = upper = lotSl = 'OK';
      // tlPush, tlRev, tlM15 は空欄
    } else if (entryRef === 'ダウ認識ミス') {
      newEntryRef = '完璧エントリー';
      dow = 'NG'; tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === 'ルール外') {
      newEntryRef = 'DowRule外';
      dow = 'NG'; tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === '上位足リスク') {
      newEntryRef = '完璧エントリー';
      dow = tlPush = tlRev = tlM15 = lotSl = 'OK'; upper = 'NG';
    } else if (entryRef === '指標') {
      newEntryRef = '完璧エントリー';
      dow = tlPush = tlRev = tlM15 = upper = lotSl = 'OK';
    } else if (entryRef === 'Lotミス') {
      newEntryRef = '完璧エントリー';
      dow = tlPush = tlRev = tlM15 = upper = 'OK'; lotSl = 'NG';
    } else if (entryRef === '損切り設定ミス') {
      newEntryRef = '完璧エントリー';
      dow = tlPush = tlRev = tlM15 = upper = 'OK'; lotSl = 'NG';
    }

    // ② 決済振り返り の移行
    var newExitRef = exitRef;
    if (exitRef === '完璧利確' || exitRef === '適切損切り') newExitRef = '完璧決済';
    else if (exitRef === 'エントリー過ち') newExitRef = 'ルール外気づき';
    else if (exitRef === '損切り設定ミス') newExitRef = 'SL設定ミス';
    // SL無視→SLずらし（移行後の値も念のため変換）
    else if (exitRef === 'SL無視') newExitRef = 'SLずらし';

    // 書き込み
    if (newEntryRef !== entryRef) {
      sheet.getRange(rowNum, entryRefCol + 1).setValue(newEntryRef);
    }
    if (exitRefCol >= 0 && newExitRef !== exitRef) {
      sheet.getRange(rowNum, exitRefCol + 1).setValue(newExitRef);
    }
    if (dow !== '')    sheet.getRange(rowNum, colDow + 1).setValue(dow);
    if (tlPush !== '') sheet.getRange(rowNum, colTlPush + 1).setValue(tlPush);
    if (tlRev !== '')  sheet.getRange(rowNum, colTlRev + 1).setValue(tlRev);
    if (tlM15 !== '')  sheet.getRange(rowNum, colTlM15 + 1).setValue(tlM15);
    if (upper !== '')  sheet.getRange(rowNum, colUpper + 1).setValue(upper);
    if (lotSl !== '')  sheet.getRange(rowNum, colLotSl + 1).setValue(lotSl);

    if (newEntryRef !== entryRef || newExitRef !== exitRef || dow || tlPush || tlRev || tlM15 || upper || lotSl) updated++;
  });

  return { success: true, updated: updated };
}

// =============================================
// v2移行: 完璧エントリー→エントリータイミングOK、完璧決済→決済タイミングOK
// =============================================
function migrateEntryFieldsV2() {
  var sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  if (!sheet) return { success: false, error: 'Entriesシートが見つかりません' };
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(String);
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return { success: true, updated: 0 };

  var entryRefCol = headers.indexOf('エントリー振り返り');
  var exitRefCol  = headers.indexOf('決済振り返り');
  var updated = 0;
  var data = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).getValues();

  data.forEach(function(row, i) {
    var rowNum = i + 2;
    if (entryRefCol >= 0) {
      var v = String(row[entryRefCol] || '').trim();
      if (v === '完璧エントリー') {
        sheet.getRange(rowNum, entryRefCol + 1).setValue('エントリータイミングOK');
        updated++;
      }
    }
    if (exitRefCol >= 0) {
      var v2 = String(row[exitRefCol] || '').trim();
      if (v2 === '完璧決済') {
        sheet.getRange(rowNum, exitRefCol + 1).setValue('決済タイミングOK');
        updated++;
      }
    }
  });
  return { success: true, updated: updated };
}

// ===== Ideas CRUD テスト関数（GASエディタから手動実行） =====
function testIdeasCRUD() {
  Logger.log('=== Ideas CRUD テスト開始 ===');

  // 1. シート取得
  const sheet = getOrCreateIdeasSheet();
  Logger.log('シート名: ' + sheet.getName());
  Logger.log('最終行: ' + sheet.getLastRow());

  // 2. 保存テスト
  const saveResult = saveIdea({ '日付': '2026-01-01', '本文': 'テストメモ', '画像URL': '', 'ステータス': '未解決' });
  Logger.log('saveIdea結果: ' + JSON.stringify(saveResult));

  if (!saveResult.success) { Logger.log('★ 保存失敗'); return; }
  const testId = saveResult.id;
  Logger.log('発行されたID: ' + testId);

  // 3. 一覧取得テスト
  const ideas = getIdeas();
  Logger.log('getIdeas件数: ' + ideas.length);
  const found = ideas.find(i => i.id === testId);
  Logger.log('IDで検索: ' + JSON.stringify(found));

  // 4. 更新テスト
  const updateResult = updateIdea(testId, { '日付': '2026-01-02', '本文': 'テストメモ（更新）', '画像URL': '', 'ステータス': '解決済み' });
  Logger.log('updateIdea結果: ' + JSON.stringify(updateResult));

  // 5. 削除テスト
  const deleteResult = deleteIdea(testId);
  Logger.log('deleteIdea結果: ' + JSON.stringify(deleteResult));

  Logger.log('=== テスト完了 ===');
}
