/**
 * Trades.gs — one table for all trades + the new MT5 import (2026-10-24, docs/EA_SYSTEM_PLAN.md).
 * Add next to Code.gs and EA_Live.gs.
 *
 * Table switch (no data is changed in "Entries"):
 *   1. migrateToTrades()   copies the whole spreadsheet as a backup, builds the sheet "Trades" from "Entries"
 *                          (columns cleaned, 9 image columns -> 3) and checks rows / profit / pips / images. Prints a report.
 *   2. switchToTrades()    the app (Code.gs) reads and writes "Trades" from now on.   switchBackToEntries() undoes it.
 *   Later, by hand when you are sure: mergeMemosIntoIdeas(), cleanPairsEAColumns(), archiveOldSheets().
 * The app keeps its field names: on "Trades" the images are stored as EntryImages / ExitImages / PreImages (one per line)
 * and handed to the app as ChartImage..ChartImage4 / 決済チャート..決済チャート4 / 事前チャート (tradesExpand_ / tradesCollapse_).
 *
 * MT5 import (actions routed from EA_Live.gs):
 *   app  eaImportRequest  -> the EA PC gets it with its next heartbeat and starts mt5_ea/live/importer.py
 *   PC   eaImportBatch    -> executions appended to "Executions" (once per ExecID); each trade either updates the trade it
 *                           is already linked to, links to one hand-written trade (same pair / direction, entry within 3 h),
 *                           or becomes a draft (ステータス = 下書き) to check in the MT5 tab
 *   app  eaImportStatus / eaImportAdopt / eaImportLink / eaImportSplit / eaImportMerge / eaImportDiscard
 */
const TRADES_SHEET_ = 'Trades';
const EXEC_SHEET_ = 'Executions';
const EXEC_HEADERS_ = ['ExecID', 'Account', 'PositionID', 'Deal', 'Symbol', 'Direction', 'InOut', 'DealTime', 'DealPrice', 'Volume', 'Profit', 'Swap',
                       'Commission', 'SL', 'TP', 'Magic', 'Comment', 'TradeID', 'ImportedAt'];
const IMG_GROUPS_ = {EntryImages: ['ChartImage', 'ChartImage2', 'ChartImage3', 'ChartImage4'],
                     ExitImages: ['決済チャート', '決済チャート2', '決済チャート3', '決済チャート4'], PreImages: ['事前チャート']};
const TRADES_DROP_ = ['Pair', 'M15決済', 'H1決済', 'M15決済損益', 'H1決済損益', 'MT5SyncKey', 'MT5LastSyncAt', 'MT5OpenLot', 'MT5ClosedLot',
                      'MT5EntryCount', 'MT5ExitCount', 'MT5ManualBackup', 'MT5ExecutionIDs', 'MT5Ticket', 'MT5Account', 'TradeGroupID', ''];
const CHECKLIST_PREFIX_ = ['ダウに見誤り', '損切りはM15', 'H1MA80の傾き', 'MAや横軸', '1:2や1:3', 'わざわざリスク'];
const TRADES_NEW_ = ['Accounts', 'ExecCount', 'MergeMode', 'RiskJPY', 'EntryImages', 'ExitImages', 'PreImages', 'CreatedAt', 'UpdatedAt'];

function tradesActive_() { return PropertiesService.getScriptProperties().getProperty('TRADES_ACTIVE') === '1'; }
/** Code.gs uses this instead of ENTRIES_SHEET. */
function tradesSheetName_() { return tradesActive_() ? TRADES_SHEET_ : ENTRIES_SHEET; }
function tradesNow_() { return Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm') + '+09:00'; }

/** Trades row object -> the field names the app uses. */
function tradesExpand_(obj) {
  if (!tradesActive_()) return obj;
  Object.keys(IMG_GROUPS_).forEach(function (g) {
    const xs = String(obj[g] || '').split('\n').filter(String);
    IMG_GROUPS_[g].forEach(function (k, i) { obj[k] = xs[i] || ''; });
    if (xs.length > IMG_GROUPS_[g].length) obj[IMG_GROUPS_[g][IMG_GROUPS_[g].length - 1]] = xs.slice(IMG_GROUPS_[g].length - 1).join('\n');
  });
  return obj;
}
/** App fields -> Trades fields. current = the full current row object (expanded) for updates, null for new rows. */
function tradesCollapse_(data, current) {
  if (!tradesActive_()) return data;
  const out = Object.assign({}, data), merged = Object.assign({}, current || {}, data);
  Object.keys(IMG_GROUPS_).forEach(function (g) {
    const keys = IMG_GROUPS_[g];
    if (keys.some(function (k) { return k in data; })) out[g] = keys.map(function (k) { return merged[k] || ''; }).filter(String).join('\n');
    keys.forEach(function (k) { delete out[k]; });
  });
  out.UpdatedAt = tradesNow_();
  if (!current) { out.CreatedAt = out.UpdatedAt; out.Source = out.Source || '手入力'; }
  return out;
}

// ------------------------------------------------------------------ migration
function migrateToTrades() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), src = ss.getSheetByName(ENTRIES_SHEET);
  if (ss.getSheetByName(TRADES_SHEET_)) throw new Error('"Trades" already exists. Delete it first if you want to run the migration again.');
  const stamp = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd_HHmm');
  const backup = DriveApp.getFileById(SPREADSHEET_ID).makeCopy('トレードアプリ_backup_' + stamp);
  const vals = src.getDataRange().getValues(), H = vals[0].map(function (h) { return String(h).trim(); });
  const imgKeys = [].concat.apply([], Object.keys(IMG_GROUPS_).map(function (g) { return IMG_GROUPS_[g]; }));
  const drop = function (h) { return TRADES_DROP_.indexOf(h) >= 0 || imgKeys.indexOf(h) >= 0 || CHECKLIST_PREFIX_.some(function (p) { return h.indexOf(p) === 0; }); };
  const keep = H.filter(function (h) { return !drop(h); });
  const header = keep.concat(TRADES_NEW_.filter(function (h) { return keep.indexOf(h) < 0; }));
  const rows = [], idx = {}; H.forEach(function (h, i) { if (!(h in idx)) idx[h] = i; });
  const cell = function (r, h) { return h in idx ? r[idx[h]] : ''; };
  let imgSrc = 0, imgDst = 0;
  vals.slice(1).forEach(function (r) {
    if (!r[0]) return;
    const o = {};
    keep.forEach(function (h) { o[h] = cell(r, h); });
    Object.keys(IMG_GROUPS_).forEach(function (g) {
      const xs = IMG_GROUPS_[g].map(function (k) { return String(cell(r, k) || ''); }).filter(String);
      imgSrc += xs.length; imgDst += xs.length; o[g] = xs.join('\n');
    });
    if (!o.Source) o.Source = '手入力';
    o.Accounts = cell(r, 'MT5Account') || '';
    o.MergeMode = o.Accounts ? 'auto' : '';
    o.CreatedAt = o.CreatedAt || ''; o.UpdatedAt = tradesNow_();
    rows.push(header.map(function (h) { return o[h] === undefined ? '' : o[h]; }));
  });
  const dst = ss.insertSheet(TRADES_SHEET_);
  dst.getRange(1, 1, 1, header.length).setValues([header]); dst.setFrozenRows(1);
  if (rows.length) dst.getRange(2, 1, rows.length, header.length).setValues(rows);
  // keep the text format of date / time columns as they were
  ['EntryDate', 'EntryTime', 'ExitDate', 'ExitTime'].forEach(function (h) {
    const j = header.indexOf(h), i = idx[h];
    if (j >= 0 && i !== undefined && rows.length) dst.getRange(2, j + 1, rows.length, 1).setNumberFormats(src.getRange(2, i + 1, rows.length, 1).getNumberFormats());
  });
  const sum = function (table, hdr, name) { const j = hdr.indexOf(name); return j < 0 ? 0 : table.reduce(function (a, r) { return a + (Number(r[j]) || 0); }, 0); };
  const srcRows = vals.slice(1).filter(function (r) { return r[0]; });
  const rep = {
    backup: backup.getName(), rowsEntries: srcRows.length, rowsTrades: rows.length,
    profitEntries: sum(srcRows, H, '損益'), profitTrades: sum(rows, header, '損益'),
    pipsEntries: sum(srcRows, H, '実取得pips'), pipsTrades: sum(rows, header, '実取得pips'),
    imagesEntries: imgSrc, imagesTrades: imgDst, droppedColumns: H.filter(drop), newColumns: TRADES_NEW_
  };
  rep.ok = rep.rowsEntries === rep.rowsTrades && Math.abs(rep.profitEntries - rep.profitTrades) < 1e-6 && Math.abs(rep.pipsEntries - rep.pipsTrades) < 1e-6;
  Logger.log(JSON.stringify(rep, null, 1));
  return rep;
}

function switchToTrades() {
  if (!SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(TRADES_SHEET_)) throw new Error('run migrateToTrades() first');
  PropertiesService.getScriptProperties().setProperty('TRADES_ACTIVE', '1');
  CacheService.getScriptCache().remove(CACHE_KEY);
  Logger.log('The app now uses "Trades". "Entries" is kept as it was (switchBackToEntries() to go back).');
}
function switchBackToEntries() {
  PropertiesService.getScriptProperties().deleteProperty('TRADES_ACTIVE');
  CacheService.getScriptCache().remove(CACHE_KEY);
  Logger.log('The app uses "Entries" again. Trades written while "Trades" was active are only in "Trades".');
}

/** Old memo sheet "メモ" -> "Ideas" (the app's memo list). Rows already copied are skipped. */
function mergeMemosIntoIdeas() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), m = ss.getSheetByName('メモ'), ideas = ss.getSheetByName(IDEAS_SHEET);
  if (!m || !ideas) return Logger.log('nothing to do');
  const mv = m.getDataRange().getValues(), mh = mv[0].map(String), iv = ideas.getDataRange().getValues(), ih = iv[0].map(String);
  const have = {}; iv.slice(1).forEach(function (r) { have[String(r[ih.indexOf('ID')])] = 1; });
  const col = function (name) { return mh.indexOf(name); };
  const add = mv.slice(1).filter(function (r) { return r[col('ID')] && !have['memo-' + r[col('ID')]]; }).map(function (r) {
    const o = {ID: 'memo-' + r[col('ID')], '日付': r[col('日付')], '本文': r[col('詳細内容')], '画像URL': r[col('画像')], 'ステータス': r[col('ステータス')] || '未解決', 'カテゴリ': 'その他'};
    return ih.map(function (h) { return o[h] === undefined ? '' : o[h]; });
  });
  if (add.length) ideas.getRange(ideas.getLastRow() + 1, 1, add.length, ih.length).setValues(add);
  Logger.log('copied ' + add.length + ' memos into Ideas (the sheet "メモ" is kept)');
}

/** Pairs: drop the old EA columns (EA許可BUY / EA許可SELL / TL推進環境 / TL逆トレ環境 / EA環境確認日時 / EA許可方向). */
function cleanPairsEAColumns() {
  const sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(PAIRS_SHEET);
  const h = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
  ['EA許可BUY', 'EA許可SELL', 'TL推進環境', 'TL逆トレ環境', 'EA環境確認日時', 'EA許可方向'].map(function (n) { return h.indexOf(n); })
    .filter(function (i) { return i >= 0; }).sort(function (a, b) { return b - a; }).forEach(function (i) { sh.deleteColumn(i + 1); });
  if (typeof pairsCacheClear_ === 'function') pairsCacheClear_();
  Logger.log('Pairs EA columns removed');
}

/** Sheets the app no longer reads -> a separate spreadsheet "トレードアプリ_保管", then removed here. */
function archiveOldSheets() {
  const names = ['データ分析', '集計', '単利複利', 'パラメータ', '手法', 'EA_Replay_Requests', 'MT5_Import_Requests', 'メモ'];
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), arc = SpreadsheetApp.create('トレードアプリ_保管_' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd'));
  names.forEach(function (n) { const sh = ss.getSheetByName(n); if (!sh) return; sh.copyTo(arc).setName(n); ss.deleteSheet(sh); });
  const first = arc.getSheets()[0]; if (arc.getSheets().length > 1 && first.getName().indexOf('Sheet') === 0) arc.deleteSheet(first);
  Logger.log('archived to ' + arc.getUrl());
}

// ------------------------------------------------------------------ table helpers
function trSheet_() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  return ss.getSheetByName(tradesSheetName_());
}
function trRead_() {
  const sh = trSheet_(), v = sh.getDataRange().getValues(), h = v[0].map(function (x) { return String(x).trim(); });
  const rows = v.slice(1).map(function (r, i) {
    const o = {_row: i + 2}; h.forEach(function (k, j) { let x = r[j]; if (x instanceof Date) x = x.getFullYear() <= 1900 ? Utilities.formatDate(x, 'Asia/Tokyo', 'HH:mm') : Utilities.formatDate(x, 'Asia/Tokyo', 'yyyy/MM/dd'); o[k] = x; });
    return o;
  }).filter(function (o) { return o.EntryID; });
  return {sh: sh, h: h, rows: rows};
}
function trEnsureCols_(T, names) {
  const miss = names.filter(function (n) { return T.h.indexOf(n) < 0; });
  if (!miss.length) return;
  T.sh.getRange(1, T.h.length + 1, 1, miss.length).setValues([miss]); T.h = T.h.concat(miss);
}
function trWrite_(T, o) {      // o has _row (update) or not (append)
  const full = tradesCollapse_(o, o._row ? o : null);
  trEnsureCols_(T, Object.keys(full).filter(function (k) { return k[0] !== '_'; }));
  const vals = [T.h.map(function (k) { return full[k] === undefined || full[k] === null ? '' : full[k]; })];
  if (o._row) T.sh.getRange(o._row, 1, 1, T.h.length).setValues(vals);
  else { T.sh.getRange(T.sh.getLastRow() + 1, 1, 1, T.h.length).setValues(vals); o._row = T.sh.getLastRow(); }
  CacheService.getScriptCache().remove(CACHE_KEY);
}
function execSheet_() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sh = ss.getSheetByName(EXEC_SHEET_);
  if (!sh) { sh = ss.insertSheet(EXEC_SHEET_); sh.getRange(1, 1, 1, EXEC_HEADERS_.length).setValues([EXEC_HEADERS_]); sh.setFrozenRows(1); }
  return sh;
}
function execRead_() {
  const sh = execSheet_(), n = sh.getLastRow();
  if (n < 2) return {sh: sh, rows: []};
  const v = sh.getRange(2, 1, n - 1, EXEC_HEADERS_.length).getValues();
  return {sh: sh, rows: v.map(function (r, i) { const o = {_row: i + 2}; EXEC_HEADERS_.forEach(function (k, j) { o[k] = r[j]; }); return o; })};
}
function execSetTradeId_(E, ids, tradeId) {
  const want = {}; ids.forEach(function (x) { want[String(x)] = 1; });
  const col = EXEC_HEADERS_.indexOf('TradeID') + 1;
  E.rows.forEach(function (r) { if (want[String(r.ExecID)]) { r.TradeID = tradeId; E.sh.getRange(r._row, col).setValue(tradeId); } });
}

// ------------------------------------------------------------------ aggregation (same rules as importer.py)
function impAggregate_(rs) {
  const ins = rs.filter(function (r) { return r.InOut === 'IN' || r.InOut === 'INOUT'; }), outs = rs.filter(function (r) { return r.InOut === 'OUT' || r.InOut === 'OUT_BY'; });
  const vol = function (xs) { return xs.reduce(function (a, r) { return a + Number(r.Volume || 0); }, 0); };
  const wavg = function (xs) { const v = vol(xs); return v ? xs.reduce(function (a, r) { return a + Number(r.DealPrice) * Number(r.Volume); }, 0) / v : ''; };
  const vin = vol(ins), vout = vol(outs), closed = vin > 0 && vout >= vin - 1e-9;
  const byT = function (a, b) { return String(a.DealTime) < String(b.DealTime) ? -1 : 1; };
  const first = rs.slice().sort(byT)[0] || {};
  const sl = (ins.slice().sort(byT).filter(function (r) { return Number(r.SL); })[0] || {}).SL || '';
  const tp = (ins.slice().sort(byT).filter(function (r) { return Number(r.TP); })[0] || {}).TP || '';
  return {symbol: first.Symbol, direction: first.Direction, accounts: Object.keys(rs.reduce(function (a, r) { a[r.Account] = 1; return a; }, {})),
    exec_ids: rs.map(function (r) { return String(r.ExecID); }), entry_time: (ins.slice().sort(byT)[0] || first).DealTime || '',
    entry_price: wavg(ins), exit_time: closed ? (outs.slice().sort(byT).pop() || {}).DealTime || '' : '', exit_price: closed ? wavg(outs) : '',
    lot: Math.round(vin * 1e4) / 1e4, profit: Math.round(rs.reduce(function (a, r) { return a + Number(r.Profit || 0) + Number(r.Swap || 0) + Number(r.Commission || 0); }, 0) * 100) / 100,
    swap: rs.reduce(function (a, r) { return a + Number(r.Swap || 0); }, 0), open: !closed, sl: sl, tp: tp, exec_count: rs.length};
}
function impAppPair_(sym) { return typeof mt5AppPair_ === 'function' ? mt5AppPair_(sym) : String(sym || '').toUpperCase(); }
function impDT_(s) { const m = String(s || '').match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/); return m ? {date: m[1] + '/' + m[2] + '/' + m[3], time: m[4] + ':' + m[5], ms: Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5])} : {date: '', time: '', ms: NaN}; }
function impEntryMs_(t) { const d = String(t.EntryDate || '').replace(/\//g, '-').slice(0, 10), tm = String(t.EntryTime || '00:00').slice(0, 5); return impDT_(d + ' ' + tm).ms; }
/** Fields a trade gets from its MT5 numbers (the hand-written fields are never touched). */
function impFields_(a) {
  const en = impDT_(a.entry_time), ex = impDT_(a.exit_time), pair = impAppPair_(a.symbol), dir = String(a.direction).toUpperCase() === 'BUY' ? 'Buy' : 'Sell';
  const pips = typeof mt5Pips_ === 'function' && a.exit_price !== '' ? mt5Pips_(a.symbol, a.direction, a.entry_price, a.exit_price) : '';
  return {'PairName（元）': pair, PairName: pair, Direction: dir, EntryDate: en.date, EntryTime: en.time, EntryPrice: a.entry_price, Lot: a.lot,
    InitialSLPrice: a.sl || '', TakeProfitPrice: a.tp || '', ExitPrice: a.exit_price, ExitDate: ex.date, ExitTime: ex.time,
    '損益': a.open ? '' : a.profit, Profit: a.open ? '' : a.profit, Swap: a.swap, '実取得pips': a.open ? '' : pips,
    Accounts: a.accounts.join(','), ExecCount: a.exec_count};
}

// ------------------------------------------------------------------ actions
function impProps_() { return PropertiesService.getScriptProperties(); }
function impGet_(k, d) { try { return JSON.parse(impProps_().getProperty(k) || 'null') || d; } catch (e) { return d; } }

/** app: save the import settings (the import itself is started on the PC with its desktop button). */
function impSaveSettings_(b) {
  const lh = Number(b.linkHours), rd = Math.round(Number(b.readDays));
  const day = function (v) { return /^\d{4}-\d{2}-\d{2}$/.test(String(v || '')) ? String(v) : ''; };
  // read period (2026-10-25): continue = from the last import (PC default) / days = the last readDays days / range = readFrom..readTo (JST dates, readTo may be empty)
  const mode = ['continue', 'days', 'range'].indexOf(b.readMode) >= 0 ? b.readMode : 'continue';
  const st = {groupHours: Number(b.groupHours) || 24, mergeAcross: b.mergeAcross !== false,
              linkHours: lh > 0 && lh <= 72 ? lh : IMP_LINK_HOURS_,
              readMode: mode, readDays: rd >= 1 && rd <= 365 ? rd : 30, readFrom: day(b.readFrom), readTo: day(b.readTo)};
  if (st.readFrom && st.readTo && st.readFrom > st.readTo) throw new Error('開始日が終了日より後です');
  impProps_().setProperty('IMPORT_SETTINGS', JSON.stringify(st));
  return {success: true, settings: st};
}
/** app: ask the EA PC to import (not used since 2026-10-25: the import runs from the PC's desktop button). */
function impRequest_(b) {
  const st = {groupHours: Number(b.groupHours) || 24, mergeAcross: b.mergeAcross !== false, reread90: !!b.reread90};
  const req = {id: 'I' + Date.now(), at: tradesNow_(), settings: st, taken: ''};
  impProps_().setProperty('IMPORT_REQUEST', JSON.stringify(req));
  impProps_().setProperty('IMPORT_SETTINGS', JSON.stringify({groupHours: st.groupHours, mergeAcross: st.mergeAcross}));
  return {success: true, request: req};
}
/** heartbeat helper (EA_Live.gs): hand the request out once (again after 30 min if no result came back). */
function impTakeRequest_() {
  const r = impGet_('IMPORT_REQUEST', null);
  if (!r) return null;
  if (r.taken && Date.now() - Number(r.takenMs || 0) < 30 * 60e3) return null;
  r.taken = tradesNow_(); r.takenMs = Date.now(); impProps_().setProperty('IMPORT_REQUEST', JSON.stringify(r));
  return r;
}

/** PC: results of one import run. */
function impBatch_(b) {
  const E = execRead_(), have = {}; E.rows.forEach(function (r) { have[String(r.ExecID)] = r; });
  const now = tradesNow_(), add = [];
  (b.executions || []).forEach(function (x) {
    if (have[String(x.ExecID)]) return;
    const o = Object.assign({}, x, {TradeID: '', ImportedAt: now});
    add.push(EXEC_HEADERS_.map(function (k) { return o[k] === undefined ? '' : o[k]; }));
    have[String(x.ExecID)] = o;
  });
  if (add.length) E.sh.getRange(E.sh.getLastRow() + 1, 1, add.length, EXEC_HEADERS_.length).setValues(add);
  const E2 = execRead_(), byExec = {}; E2.rows.forEach(function (r) { byExec[String(r.ExecID)] = r; });
  const T = trRead_(); trEnsureCols_(T, ['Accounts', 'ExecCount', 'MergeMode', 'Source', 'ExitPrice', 'ExitDate', 'ExitTime', 'Profit', 'Swap', 'EntryPrice', 'InitialSLPrice', 'TakeProfitPrice']);
  const byId = {}; T.rows.forEach(function (r) { byId[String(r.EntryID)] = r; });
  let updated = 0, linked = 0, drafts = 0;
  (b.trades || []).forEach(function (a) {
    // the full execution set of an already linked trade decides (a partial read must not shrink it)
    const ids = a.exec_ids.map(String), tids = ids.map(function (i) { return String((byExec[i] || {}).TradeID || ''); }).filter(String);
    // a position read only in part (e.g. its exit after the window that read its entry) joins the trade that has its other executions
    const pos = {}; ids.forEach(function (i) { const r = byExec[i]; if (r && r.PositionID !== '') pos[r.Account + ':' + r.PositionID] = 1; });
    E2.rows.forEach(function (r) { if (r.TradeID && pos[r.Account + ':' + r.PositionID] && ids.indexOf(String(r.ExecID)) < 0) tids.push(String(r.TradeID)); });
    if (tids.indexOf('IGNORED') >= 0) return;
    const tid = tids[0];
    if (tid && byId[tid]) {
      const row = byId[tid], all = E2.rows.filter(function (r) { return String(r.TradeID) === tid || ids.indexOf(String(r.ExecID)) >= 0; });
      const agg = impAggregate_(all), f = impFields_(agg);
      if (String(row.MergeMode) === 'manual') { ['ExitPrice', 'ExitDate', 'ExitTime', '損益', 'Profit', 'Swap', '実取得pips'].forEach(function (k) { row[k] = f[k]; }); }
      else Object.keys(f).forEach(function (k) {
        if (row['ステータス'] !== '下書き') {             // a kept record: hand-written fields stay, MT5 only fills what is empty
          if (['PairName（元）', 'PairName', 'Direction', 'EntryDate', 'EntryTime'].indexOf(k) >= 0) return;
          if ((k === '損益' || k === '実取得pips') && row[k] !== '' && row[k] !== undefined) return;
        }
        row[k] = f[k];
      });
      if (!agg.open && row['ステータス'] === '保有中') row['ステータス'] = '決済';
      trWrite_(T, row); execSetTradeId_(E2, ids, tid); updated++; return;
    }
    // new trades are never linked automatically (user 2026-10-25): every one becomes a draft to check in the MT5 tab,
    // which lists the hand-written candidates (impStatus_)
    const f = impFields_(a);
    const d = Object.assign({EntryID: Utilities.getUuid().substring(0, 8), 'ステータス': '下書き', Source: 'MT5', MergeMode: 'auto'}, f);
    trWrite_(T, d); T.rows.push(d); byId[d.EntryID] = d; execSetTradeId_(E2, ids, d.EntryID); drafts++;
  });
  const status = impGet_('IMPORT_STATUS', {accounts: {}});
  (b.accounts || []).forEach(function (x) {
    const old = status.accounts[x.login] || {};
    if (x.error) status.accounts[x.login] = Object.assign({}, old, {label: x.label || old.label || '', error: String(x.error), errorAt: now});   // keep its last good read
    else status.accounts[x.login] = {label: x.label || '', last: x.last || '', deals: x.deals, at: now, error: ''};
  });
  status.last = {at: now, request: b.request_id || '', executionsNew: add.length, updated: updated, linked: linked, drafts: drafts, errors: b.errors || [],
                 period: String((b.settings || {}).period || '')};
  impProps_().setProperty('IMPORT_STATUS', JSON.stringify(status));
  const req = impGet_('IMPORT_REQUEST', null);
  if (req && (!b.request_id || req.id === b.request_id)) impProps_().deleteProperty('IMPORT_REQUEST');
  return {success: true, executionsNew: add.length, updated: updated, linked: linked, drafts: drafts};
}

const IMP_LINK_HOURS_ = 3;      // default: a draft's link candidates are hand-written entries within this many hours
const IMP_RECENT_DAYS_ = 14;    // "最近記録にしたもの" in the MT5 tab
const IMP_TRASH_ = 'ゴミ箱';     // status of a discarded draft (kept until the trash is emptied)
// fields a link copies from MT5 onto the hand-written trade; their old values are kept in LinkBackup so the link can be undone
const IMP_LINK_FIELDS_ = ['EntryPrice', 'Lot', 'ExitPrice', 'ExitDate', 'ExitTime', 'Profit', 'Swap', 'Accounts', 'ExecCount',
                          'InitialSLPrice', 'TakeProfitPrice', '損益', '実取得pips', 'ステータス', 'MergeMode'];

function impExecOf_(E, tradeId) {
  return E.rows.filter(function (r) { return String(r.TradeID) === String(tradeId); }).map(function (r) { const o = Object.assign({}, r); delete o._row; return o; });
}
function impPosCount_(ex) { return Object.keys(ex.reduce(function (a, r) { a[r.Account + ':' + r.PositionID] = 1; return a; }, {})).length; }
function impBrief_(t) {
  return {EntryID: t.EntryID, 'PairName（元）': t['PairName（元）'] || t.PairName, Direction: t.Direction, EntryDate: t.EntryDate, EntryTime: t.EntryTime,
          ExitDate: t.ExitDate, ExitTime: t.ExitTime, Lot: t.Lot, '損益': t['損益'], '実取得pips': t['実取得pips'], 'ステータス': t['ステータス'],
          Source: t.Source, Accounts: t.Accounts, TrashedAt: t.TrashedAt, AdoptedAt: t.AdoptedAt, LinkedAt: t.LinkedAt, linked: !!t.LinkBackup};
}

/** app: MT5 tab data. */
function impStatus_() {
  const T = trRead_(), E = execRead_();
  const st = impGet_('IMPORT_SETTINGS', {groupHours: 24, mergeAcross: true});
  const linkH = Number(st.linkHours) > 0 ? Number(st.linkHours) : IMP_LINK_HOURS_;
  const drafts = T.rows.filter(function (t) { return t['ステータス'] === '下書き'; }).map(function (t) {
    const ex = impExecOf_(E, t.EntryID);
    // link candidates: hand-written trades (open or closed, the whole history) with the same pair and direction whose
    // entry is within linkH hours; not drafts / trash / missed entries / reservations / trades already linked to MT5
    const ms = impEntryMs_(t);
    const cands = T.rows.filter(function (c) {
      return c !== t && !c.Accounts && ['下書き', IMP_TRASH_, '決済（見逃し）'].indexOf(String(c['ステータス'])) < 0 && String(c.Source || '') !== '予約'
        && String(c['PairName（元）'] || c.PairName || '').toUpperCase() === String(t['PairName（元）'] || t.PairName || '').toUpperCase()
        && String(c.Direction) === String(t.Direction) && Math.abs(impEntryMs_(c) - ms) <= linkH * 3600e3;
    }).sort(function (x, y) { return Math.abs(impEntryMs_(x) - ms) - Math.abs(impEntryMs_(y) - ms); })     // closest first
      .map(function (c) { return {EntryID: c.EntryID, EntryDate: c.EntryDate, EntryTime: c.EntryTime, Lot: c.Lot, '損益': c['損益'], 'ステータス': c['ステータス']}; });
    const o = tradesExpand_(Object.assign({}, t)); delete o._row;
    return {trade: o, executions: ex, positions: impPosCount_(ex), candidates: cands};
  });
  const trash = T.rows.filter(function (t) { return t['ステータス'] === IMP_TRASH_; }).map(function (t) {
    const ex = impExecOf_(E, t.EntryID); return {trade: impBrief_(t), executions: ex, positions: impPosCount_(ex)};
  });
  const since = Date.now() - IMP_RECENT_DAYS_ * 86400e3, when = function (s) { const d = new Date(String(s || '').replace(' ', 'T')); return isNaN(d) ? 0 : d.getTime(); };
  const recent = T.rows.filter(function (t) { return ['下書き', IMP_TRASH_].indexOf(String(t['ステータス'])) < 0 && Math.max(when(t.AdoptedAt), t.LinkBackup ? when(t.LinkedAt) : 0) >= since; })
    .sort(function (a, b) { return Math.max(when(b.AdoptedAt), when(b.LinkedAt)) - Math.max(when(a.AdoptedAt), when(a.LinkedAt)); })
    .map(function (t) { const ex = impExecOf_(E, t.EntryID); return {trade: impBrief_(t), executions: ex, positions: impPosCount_(ex)}; });
  const eaStatus = {}; try { ealRows_('status').forEach(function (r) { eaStatus[r.Account] = r.UpdatedAt; }); } catch (e) {}
  return {success: true, request: impGet_('IMPORT_REQUEST', null), status: impGet_('IMPORT_STATUS', {accounts: {}}),
          settings: Object.assign({linkHours: linkH}, st), drafts: drafts, trash: trash, recent: recent, eaStatus: eaStatus,
          features: {trash: 1, unadopt: 1, linkHours: 1, readPeriod: 1}};
}

function impFind_(T, id) { const t = T.rows.filter(function (r) { return String(r.EntryID) === String(id); })[0]; if (!t) throw new Error('trade not found: ' + id); return t; }

/** app: keep a draft as a real record (status from whether it is closed). */
function impAdopt_(b) {
  const T = trRead_(), t = impFind_(T, b.entryId);
  t['ステータス'] = t.ExitDate ? '決済' : '保有中'; t.AdoptedAt = tradesNow_(); trWrite_(T, t);
  return {success: true, status: t['ステータス']};
}
/** app: a trade recorded from the MT5 tab goes back to "確認が必要なトレード".
 *  - recorded from a draft (Source MT5): back to a draft
 *  - linked to a hand-written trade: the hand-written values come back from LinkBackup and the MT5 part becomes a draft again */
function impUnadopt_(b) {
  const T = trRead_(), t = impFind_(T, b.entryId), E = execRead_();
  if (t.LinkBackup) return {success: true, draftId: impUnlinkRow_(T, E, t, JSON.parse(t.LinkBackup))};
  // linked without a backup (the old automatic link, or a link made before the undo existed): the MT5 part becomes a draft;
  // the hand-written values come back from Entries when they are there from before the link, else the values MT5 wrote are emptied
  if (String(t.Source) !== 'MT5' && String(t.Source) !== '予約' && t.Accounts) { const o = impOrigFor_(t, impEntriesById_()); return {success: true, draftId: impUnlinkRow_(T, E, t, o.back, !o.restored), restored: o.restored}; }
  if (String(t.Source) !== 'MT5') throw new Error('MT5 から記録したトレードではありません');
  t['ステータス'] = '下書き'; t.AdoptedAt = ''; trWrite_(T, t);
  return {success: true, draftId: t.EntryID};
}
/** Entries rows by EntryID (only when the app already reads "Trades": then Entries is the copy from before the switch). */
function impEntriesById_() {
  const orig = {};
  if (!tradesActive_()) return orig;
  const sh = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(ENTRIES_SHEET);
  if (!sh) return orig;
  const v = sh.getDataRange().getValues(), h = v[0].map(function (x) { return String(x).trim(); });
  v.slice(1).forEach(function (r) {
    const o = {}; h.forEach(function (k, j) { let x = r[j]; if (x instanceof Date) x = x.getFullYear() <= 1900 ? Utilities.formatDate(x, 'Asia/Tokyo', 'HH:mm') : Utilities.formatDate(x, 'Asia/Tokyo', 'yyyy/MM/dd'); o[k] = x; });
    if (o.EntryID) orig[String(o.EntryID)] = o;
  });
  return orig;
}
/** Values a linked trade gets back when its link is undone without LinkBackup: from Entries if that row is from before the
 *  link (no MT5 accounts on it), else the current values with only the MT5 marks (Accounts / ExecCount / MergeMode) cleared. */
function impOrigFor_(t, orig) {
  const o = orig[String(t.EntryID)], ok = !!(o && !o.Accounts);
  const back = {}; IMP_LINK_FIELDS_.forEach(function (k) { back[k] = ok ? (o[k] === undefined ? '' : o[k]) : (['Accounts', 'ExecCount', 'MergeMode'].indexOf(k) >= 0 ? '' : t[k]); });
  return {back: back, restored: ok};
}
/** The MT5 part of a linked trade becomes a new draft; the hand-written trade gets `orig` back. Returns the draft id.
 *  clearSame (no backup of the values from before the link): the values that are the same as MT5's are emptied instead. */
function impUnlinkRow_(T, E, t, orig, clearSame) {
  const rs = E.rows.filter(function (r) { return String(r.TradeID) === String(t.EntryID); });
  const f = rs.length ? impFields_(impAggregate_(rs)) : null;
  let draftId = '';
  if (rs.length) {
    const d = Object.assign({EntryID: Utilities.getUuid().substring(0, 8), 'ステータス': '下書き', Source: 'MT5', MergeMode: 'auto'}, f);
    trWrite_(T, d); T.rows.push(d); draftId = d.EntryID;
    execSetTradeId_(E, rs.map(function (r) { return r.ExecID; }), d.EntryID);
  }
  IMP_LINK_FIELDS_.forEach(function (k) { t[k] = orig[k] === undefined ? '' : orig[k]; });
  if (clearSame && f) impClearMT5Values_(t, f);
  t.LinkBackup = ''; t.LinkedAt = '';
  trWrite_(T, t);
  return draftId;
}
/** A value equal to MT5's (prices, lot, exit, profit, pips, stop, target) was written by the link: empty it (user 2026-10-25).
 *  No exit date and no 損益 left on a closed trade -> back to 保有中. Values typed by hand (different from MT5's) stay.
 *  Returns the emptied fields. */
const IMP_MT5_VALUE_FIELDS_ = ['EntryPrice', 'Lot', 'ExitPrice', 'ExitDate', 'ExitTime', 'Profit', 'Swap', '損益', '実取得pips', 'InitialSLPrice', 'TakeProfitPrice'];
function impSameValue_(a, b) {
  if (a === '' || a === undefined || a === null || b === '' || b === undefined || b === null) return false;
  const x = Number(a), y = Number(b);
  if (String(a).trim() !== '' && String(b).trim() !== '' && isFinite(x) && isFinite(y)) return Math.abs(x - y) < 1e-9;
  return String(a).replace(/-/g, '/').trim() === String(b).replace(/-/g, '/').trim();
}
function impClearMT5Values_(t, f) {
  const cleared = IMP_MT5_VALUE_FIELDS_.filter(function (k) { return impSameValue_(t[k], f[k]); });
  cleared.forEach(function (k) { t[k] = ''; });
  ['Accounts', 'ExecCount', 'MergeMode'].forEach(function (k) { t[k] = ''; });
  // back to 保有中 only when nothing of an exit is left (a 損益 typed by hand keeps it 決済)
  if (!t.ExitDate && (t['損益'] === '' || t['損益'] === undefined) && String(t['ステータス']) === '決済') t['ステータス'] = '保有中';
  return cleared;
}
/** app: attach a draft's MT5 numbers to a hand-written trade, then remove the draft. */
function impLink_(b) {
  const T = trRead_(), d = impFind_(T, b.draftId), t = impFind_(T, b.entryId), E = execRead_();
  // any hand-written trade may be chosen in the app (not only the candidates); these are never a link target
  if (['下書き', IMP_TRASH_].indexOf(String(t['ステータス'])) >= 0) throw new Error('確認待ち・ゴミ箱のトレードには紐付けられません');
  if (t.Accounts || t.LinkBackup) throw new Error('このトレードはもう MT5 と紐付いています（先に「確認待ちに戻す」で外す）');
  if (String(t.Direction) !== String(d.Direction)) throw new Error('向きが違うトレードには紐付けられません');
  const backup = {}; IMP_LINK_FIELDS_.forEach(function (k) { backup[k] = t[k] === undefined ? '' : t[k]; });   // to undo the link later
  t.LinkBackup = JSON.stringify(backup); t.LinkedAt = tradesNow_();
  ['EntryPrice', 'Lot', 'ExitPrice', 'ExitDate', 'ExitTime', 'Profit', 'Swap', 'Accounts', 'ExecCount', 'InitialSLPrice', 'TakeProfitPrice'].forEach(function (k) { if (d[k] !== '' && d[k] !== undefined) t[k] = d[k]; });
  if (!t['損益'] && d['損益'] !== '') t['損益'] = d['損益'];
  if (!t['実取得pips'] && d['実取得pips'] !== '') t['実取得pips'] = d['実取得pips'];
  t.MergeMode = d.MergeMode || 'auto'; if (d.ExitDate && t['ステータス'] === '保有中') t['ステータス'] = '決済';
  trWrite_(T, t);
  execSetTradeId_(E, E.rows.filter(function (r) { return String(r.TradeID) === String(d.EntryID); }).map(function (r) { return r.ExecID; }), String(t.EntryID));
  T.sh.deleteRow(d._row); CacheService.getScriptCache().remove(CACHE_KEY);
  return {success: true};
}
/** app: one draft per MT5 position. */
function impSplit_(b) {
  const T = trRead_(), d = impFind_(T, b.draftId), E = execRead_();
  const rs = E.rows.filter(function (r) { return String(r.TradeID) === String(d.EntryID); }), by = {};
  rs.forEach(function (r) { (by[r.Account + ':' + r.PositionID] = by[r.Account + ':' + r.PositionID] || []).push(r); });
  const keys = Object.keys(by); if (keys.length < 2) return {success: true, unchanged: true};
  keys.forEach(function (k) {
    const n = Object.assign({EntryID: Utilities.getUuid().substring(0, 8), 'ステータス': '下書き', Source: 'MT5', MergeMode: 'manual'}, impFields_(impAggregate_(by[k])));
    trWrite_(T, n); execSetTradeId_(E, by[k].map(function (r) { return r.ExecID; }), n.EntryID);
  });
  T.sh.deleteRow(d._row); CacheService.getScriptCache().remove(CACHE_KEY);
  return {success: true, parts: keys.length};
}
/** app: several drafts -> one. */
function impMerge_(b) {
  const T = trRead_(), ids = (b.ids || []).map(String); if (ids.length < 2) throw new Error('choose 2 or more');
  const ds = ids.map(function (i) { return impFind_(T, i); }), E = execRead_();
  // only the same pair and direction (2026-10-25: a mixed merge made one trade out of different instruments)
  const kinds = {}; ds.forEach(function (d) { kinds[String(d['PairName（元）'] || d.PairName || '').toUpperCase() + ' ' + d.Direction] = 1; });
  if (Object.keys(kinds).length > 1) throw new Error('通貨か向きが違うものはまとめられません（' + Object.keys(kinds).join(' / ') + '）');
  if (ds.some(function (d) { return d['ステータス'] !== '下書き'; })) throw new Error('まとめられるのは確認が必要なトレードだけです');
  const rs = E.rows.filter(function (r) { return ids.indexOf(String(r.TradeID)) >= 0; });
  const keepRow = ds[0]; Object.assign(keepRow, impFields_(impAggregate_(rs)), {MergeMode: 'manual'}); trWrite_(T, keepRow);
  execSetTradeId_(E, rs.map(function (r) { return r.ExecID; }), String(keepRow.EntryID));
  ds.slice(1).map(function (d) { return d._row; }).sort(function (a, b) { return b - a; }).forEach(function (r) { T.sh.deleteRow(r); });
  CacheService.getScriptCache().remove(CACHE_KEY);
  return {success: true};
}
/** app: not a trade to record -> the trash (status ゴミ箱). Its executions keep pointing to it, so a new import neither
 *  brings it back as a new draft nor duplicates it; it can be restored until the trash is emptied. */
function impDiscard_(b) {
  const T = trRead_(), ids = (b.ids || [b.draftId]).map(String);
  ids.forEach(function (id) { const d = impFind_(T, id); d['ステータス'] = IMP_TRASH_; d.TrashedAt = tradesNow_(); trWrite_(T, d); });
  return {success: true, trashed: ids.length};
}
/** app: trash -> back to "確認が必要なトレード". */
function impRestore_(b) {
  const T = trRead_(), ids = (b.ids || []).map(String);
  ids.forEach(function (id) { const d = impFind_(T, id); if (d['ステータス'] !== IMP_TRASH_) return; d['ステータス'] = '下書き'; d.TrashedAt = ''; trWrite_(T, d); });
  return {success: true, restored: ids.length};
}
/** app: delete for good (some ids, or the whole trash with all: true). The executions are marked IGNORED so they never
 *  come back as a draft, even with the 90-day reread. */
function impPurge_(b) {
  const T = trRead_(), E = execRead_();
  const rows = T.rows.filter(function (t) { return t['ステータス'] === IMP_TRASH_ && (b.all || (b.ids || []).map(String).indexOf(String(t.EntryID)) >= 0); });
  rows.forEach(function (d) {
    execSetTradeId_(E, E.rows.filter(function (r) { return String(r.TradeID) === String(d.EntryID); }).map(function (r) { return r.ExecID; }), 'IGNORED');
  });
  rows.map(function (d) { return d._row; }).sort(function (a, b) { return b - a; }).forEach(function (r) { T.sh.deleteRow(r); });
  CacheService.getScriptCache().remove(CACHE_KEY);
  return {success: true, purged: rows.length};
}

/** One-off (run from the editor): the hand-written trades linked to MT5 without a backup (the old import's automatic links
 *  before 2026-10-25, and links made with the older GAS) go back: the MT5 part to "確認が必要なトレード". Run with apply = false first (the default) and read the log.
 *  The hand-written values come back from the Entries sheet when the app already uses Trades (the migration left Entries
 *  untouched); otherwise only the link is undone and the values MT5 wrote are listed so they can be checked by hand. */
function impRevertAutoLinksOnce(apply) {
  const T = trRead_(), E = execRead_();
  const auto = T.rows.filter(function (t) {
    // every hand-written trade linked to MT5 without a backup (the old automatic links, and links made with the older GAS)
    return t.Accounts && !t.LinkBackup && String(t.Source || '') !== 'MT5' && String(t.Source || '') !== '予約'
      && ['下書き', IMP_TRASH_].indexOf(String(t['ステータス'])) < 0;
  });
  const orig = impEntriesById_();
  const report = auto.map(function (t) {
    const ob = impOrigFor_(t, orig), back = ob.back;
    const line = {EntryID: t.EntryID, pair: t['PairName（元）'] || t.PairName, dir: t.Direction, entry: t.EntryDate + ' ' + t.EntryTime,
                  source: ob.restored ? 'Entries (元の値を戻す)' : 'なし (結び付きだけ外す。今の値: ' + ['EntryPrice', 'Lot', 'ExitDate', 'ExitTime', 'Profit', '損益', '実取得pips'].map(function (k) { return k + '=' + t[k]; }).join(' ') + ')'};
    if (apply) line.draftId = impUnlinkRow_(T, E, t, back, !ob.restored);     // no backup: the values MT5 wrote are emptied
    return line;
  });
  Logger.log(JSON.stringify({apply: !!apply, tradesActive: tradesActive_(), count: report.length, trades: report}, null, 1));
  return report;
}
function impRevertAutoLinksApply() { return impRevertAutoLinksOnce(true); }

/** Check (run from the editor): which trade every MT5 execution belongs to. Executions that belong to no draft / record /
 *  linked trade (e.g. left on a hand-written trade whose link was undone, or on a trade that no longer exists) are listed;
 *  with apply = true they become drafts in "確認が必要なトレード" again. Hand-written trades still carrying the numbers MT5
 *  wrote (the link was undone without a backup) are listed too (leftValues); apply empties those values (user 2026-10-25:
 *  exit date / time etc. written by the link should go; no exit left -> 保有中). Run without apply first and read the log. */
function impCheckLinksOnce(apply) {
  const T = trRead_(), E = execRead_(), byId = {}; T.rows.forEach(function (t) { byId[String(t.EntryID)] = t; });
  const groups = {}; E.rows.forEach(function (r) { const k = String(r.TradeID || ''); if (k === 'IGNORED') return; (groups[k] = groups[k] || []).push(r); });
  const rep = {apply: !!apply, executions: E.rows.length, drafts: 0, recorded: 0, linked: 0, trash: 0, orphans: []};
  Object.keys(groups).forEach(function (k) {
    const t = k ? byId[k] : null, rs = groups[k];
    let why = '';
    if (!k) why = 'どのトレードにも付いていない';
    else if (!t) why = '付いているトレードがもう無い';
    else if (t['ステータス'] === '下書き') { rep.drafts++; return; }
    else if (t['ステータス'] === IMP_TRASH_) { rep.trash++; return; }
    else if (String(t.Source) === 'MT5') { rep.recorded++; return; }
    else if (t.Accounts) { rep.linked++; return; }
    else why = '紐付けを外したのに、手入力のトレードに残っている';
    // one draft per trade (no trade id: per account + position)
    const parts = {}; rs.forEach(function (r) { const pk = k || (r.Account + ':' + r.PositionID); (parts[pk] = parts[pk] || []).push(r); });
    Object.keys(parts).forEach(function (pk) {
      const f = impFields_(impAggregate_(parts[pk]));
      const line = {why: why, tradeId: k, pair: f['PairName（元）'], dir: f.Direction, entry: f.EntryDate + ' ' + f.EntryTime, executions: parts[pk].length};
      if (t) line.sameAsMT5 = IMP_MT5_VALUE_FIELDS_.filter(function (x) { return impSameValue_(t[x], f[x]); }).join(' ') || 'なし';
      if (apply) {
        const d = Object.assign({EntryID: Utilities.getUuid().substring(0, 8), 'ステータス': '下書き', Source: 'MT5', MergeMode: 'auto'}, f);
        trWrite_(T, d); T.rows.push(d); execSetTradeId_(E, parts[pk].map(function (r) { return r.ExecID; }), d.EntryID); line.draftId = d.EntryID;
        if (t) { line.cleared = impClearMT5Values_(t, f).join(' ') || 'なし'; trWrite_(T, t); }     // the values MT5 wrote on it
      }
      rep.orphans.push(line);
    });
  });
  // hand-written trades whose link was already undone but still carry MT5's numbers: compared with each draft of the same
  // pair / direction entered within 3 days; 3 or more identical values (entry, lot, exit, exit date / time, profit) = written by MT5
  rep.leftValues = [];
  const pk = function (x) { return String(x['PairName（元）'] || x.PairName || '').toUpperCase(); };
  const keyF = ['EntryPrice', 'Lot', 'ExitPrice', 'ExitDate', 'ExitTime', '損益'];
  T.rows.filter(function (d) { return d['ステータス'] === '下書き'; }).forEach(function (d) {
    T.rows.forEach(function (t) {
      if (t === d || t.Accounts || t.LinkBackup || ['MT5', '予約'].indexOf(String(t.Source || '')) >= 0 || ['下書き', IMP_TRASH_].indexOf(String(t['ステータス'])) >= 0) return;
      if (pk(t) !== pk(d) || String(t.Direction) !== String(d.Direction) || Math.abs(impEntryMs_(t) - impEntryMs_(d)) > 3 * 86400e3) return;
      const hits = keyF.filter(function (x) { return impSameValue_(t[x], d[x]); });
      if (hits.length < 3) return;
      const line = {EntryID: t.EntryID, pair: pk(t), dir: t.Direction, entry: t.EntryDate + ' ' + t.EntryTime, sameAsDraft: d.EntryID,
                    values: IMP_MT5_VALUE_FIELDS_.filter(function (x) { return impSameValue_(t[x], d[x]); }).map(function (x) { return x + '=' + t[x]; }).join(' ')};
      if (apply) { line.cleared = impClearMT5Values_(t, d).join(' '); line.status = t['ステータス']; trWrite_(T, t); }
      rep.leftValues.push(line);
    });
  });
  Logger.log(JSON.stringify(rep, null, 1));
  return rep;
}
function impCheckLinksApply() { return impCheckLinksOnce(true); }

// ------------------------------------------------------------------ time stamps
/** One-off: rewrite old time stamps to Japan time with the offset (2026-10-24 21:15+09:00). Run once from the editor.
 *  Only "when was this written" columns; EntryDate / EntryTime / ExitDate / ExitTime stay as the app uses them (already Japan time). */
function fixOldTimestamps() {
  const targets = {App_Settings: ['UpdatedAt'], EA_Calendar_Reminders: ['CreatedAt', 'UpdatedAt'], Reviews: ['作成日'], Pairs: ['確認日時'],
                   Trades: ['CreatedAt', 'UpdatedAt']};
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), rep = {};
  const conv = function (v) {
    if (v === '' || v === null || v === undefined) return v;
    if (v instanceof Date) return jstNow_(v);
    const s = String(v).trim();
    if (/\+09:00$/.test(s)) return s;
    if (/^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:?\d{2})$/.test(s)) { const d = new Date(s); return isNaN(d) ? s : jstNow_(d); }   // ISO with zone (UTC)
    const m = s.match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})[ T](\d{1,2}):(\d{2})/);                                              // already Japan time
    return m ? m[1] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[3]).slice(-2) + ' ' + ('0' + m[4]).slice(-2) + ':' + m[5] + '+09:00' : s;
  };
  Object.keys(targets).forEach(function (name) {
    const sh = ss.getSheetByName(name); if (!sh || sh.getLastRow() < 2) return;
    const h = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
    targets[name].forEach(function (col) {
      const j = h.indexOf(col); if (j < 0) return;
      const rg = sh.getRange(2, j + 1, sh.getLastRow() - 1, 1), vals = rg.getValues();
      let n = 0; const out = vals.map(function (r) { const x = conv(r[0]); if (x !== r[0]) n++; return [x]; });
      rg.setNumberFormat('@'); rg.setValues(out); rep[name + '.' + col] = n;
    });
  });
  Logger.log(JSON.stringify(rep));
  return rep;
}

// ------------------------------------------------------------------ reservations = hand-written trades
/** A filled reservation becomes a normal trade record (same as hand-written, Source 予約) so it is in every 裁量 view. */
function resRecordOpen_(b, eaTradeId) {
  const T = trRead_();
  if (T.rows.some(function (t) { return String(t.EATradeID || '') === eaTradeId; })) return;
  const en = impDT_(String(b.entry_time || tradesNow_()).replace('+09:00', ''));
  const pair = String(b.symbol || '').toUpperCase(), dir = Number(b.side) === 1 ? 'Buy' : 'Sell';
  const res = (ealRows_('res').filter(function (r) { return 'RES:' + r.ResID === String(b.ea); })[0]) || {};
  const o = {EntryID: Utilities.getUuid().substring(0, 8), 'ステータス': '保有中', Source: '予約', EATradeID: eaTradeId,
    'PairName（元）': pair, PairName: pair, Direction: dir, EntryDate: en.date, EntryTime: en.time, EntryPrice: b.fill, Lot: b.lots,
    InitialSLPrice: b.sl, TakeProfitPrice: b.tp || '', RiskJPY: b.risk_jpy, Accounts: String(b.account || ''),
    'エントリー時メモ': ['予約 ' + (res.Trigger || '') + ' エントリー', res.Note || ''].filter(String).join(' / ')};
  trWrite_(T, o);
}
function resRecordClose_(eaRow, b) {
  const T = trRead_(), id = String(eaRow.TradeID);
  const t = T.rows.filter(function (x) { return String(x.EATradeID || '') === id; })[0];
  if (!t) return;
  const ex = impDT_(String(b.exit_time || '').replace('+09:00', ''));
  const sym = String(eaRow.Symbol || ''), dir = String(eaRow.Direction || '').toUpperCase();
  const pips = typeof mt5Pips_ === 'function' ? mt5Pips_(sym, dir, eaRow.EntryPrice, b.exit) : '';
  Object.assign(t, {'ステータス': '決済', ExitPrice: b.exit, ExitDate: ex.date, ExitTime: ex.time, Profit: b.profit, '損益': b.profit, '実取得pips': pips});
  trWrite_(T, t);
}

// ------------------------------------------------------------------ everything at once
/** Run once from the editor: backup + Trades (stops here if the numbers do not match), switch the app to Trades,
 *  old memos into Ideas, old Pairs EA columns removed, time stamps unified, unused sheets moved to "トレードアプリ_保管". */
function upgradeSheetsOnce() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), log = [];
  if (!ss.getSheetByName(TRADES_SHEET_)) {
    const rep = migrateToTrades();
    log.push('Trades: ' + rep.rowsTrades + ' 件、損益 ' + rep.profitTrades + '（Entries ' + rep.rowsEntries + ' 件、' + rep.profitEntries + '）バックアップ ' + rep.backup);
    if (!rep.ok) { Logger.log(log.join('\n') + '\n数が合わないので、ここで止めました（アプリは Entries のまま）'); return {ok: false, log: log}; }
  } else log.push('Trades はもうある（作り直しはしない）');
  switchToTrades(); log.push('アプリは Trades を読む');
  mergeMemosIntoIdeas(); log.push('古いメモを Ideas へ');
  cleanPairsEAColumns(); log.push('Pairs の古い EA 列を削除');
  log.push('時刻の書き方: ' + JSON.stringify(fixOldTimestamps()));
  archiveOldSheets(); log.push('使っていない表を「トレードアプリ_保管」へ');
  Logger.log(log.join('\n'));
  return {ok: true, log: log};
}
