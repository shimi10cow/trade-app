/**
 * EA_Live.gs — backend for the new live EAs (2026-10-24, docs/EA_SYSTEM_PLAN.md).
 * Add this file to the Apps Script project next to Code.gs. Code.gs routes every action starting with "ea" here
 * (see the two lines at the top of doGet / doPost).
 *
 * Keys (Script properties): EA_KEY for the EA PC, APP_KEY for the phone app. Run eaSetupKeys() once in the editor:
 * it creates both keys and prints them in the log. Every ea* call must carry the matching key.
 *
 * Sheets (created on first use):
 *   EA_Config  : Account | ConfigJSON | UpdatedAt        one row per account (demo / live)
 *   EA_Status  : Account | ... | UpdatedAt               one row per account, overwritten by each heartbeat
 *   EA_Daily   : Date | Account | Balance | Equity | Peak | DD    one row per account per day
 *   EA_Trades  : one row per EA trade (opened, then updated when closed)
 *   EA_Log     : errors and signals that were not traded (kept 90 days)
 *   Reservations : reservation entries (予約) made in the app; the EA PC reads the waiting ones and enters on the stochastic trigger
 * Times are written in Japan time with the offset, e.g. 2026-10-24 21:15+09:00.
 */
const EAL_ = {
  config: ['Account', 'ConfigJSON', 'UpdatedAt'],
  status: ['Account', 'Login', 'Balance', 'Equity', 'Peak', 'DD', 'Positions', 'Outbox', 'EATime', 'UpdatedAt'],
  daily: ['Date', 'Account', 'Balance', 'Equity', 'Peak', 'DD'],
  trades: ['TradeID', 'Account', 'Source', 'EA', 'Symbol', 'Direction', 'Ticket', 'SignalTime', 'EntryTime', 'EntryPrice', 'SLPrice', 'TPPrice',
           'Lot', 'RiskJPY', 'LotMult', 'Weight', 'Reason', 'Note', 'ExitTime', 'ExitPrice', 'Profit', 'R', 'Status', 'CreatedAt', 'UpdatedAt'],
  log: ['Time', 'Account', 'Level', 'EA', 'Message'],
  res: ['ResID', 'Account', 'Symbol', 'Direction', 'Trigger', 'SLPrice', 'TPPrice', 'LotMode', 'LotValue', 'Status', 'TradeID', 'Note', 'CreatedAt', 'UpdatedAt']
};
const EAL_SHEETS_ = {config: 'EA_Config', status: 'EA_Status', daily: 'EA_Daily', trades: 'EA_Trades', log: 'EA_Log', res: 'Reservations'};

function eaSetupKeys() {
  const p = PropertiesService.getScriptProperties();
  ['EA_KEY', 'APP_KEY'].forEach(k => {
    if (!p.getProperty(k)) p.setProperty(k, Utilities.getUuid().replace(/-/g, ''));
    Logger.log(k + ' = ' + p.getProperty(k));
  });
}

function ealNow_() { return Utilities.formatDate(new Date(), 'Asia/Tokyo', "yyyy-MM-dd HH:mm") + '+09:00'; }

function ealSheet_(kind) {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID), name = EAL_SHEETS_[kind];
  let sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.getRange(1, 1, 1, EAL_[kind].length).setValues([EAL_[kind]]); sh.setFrozenRows(1); }
  return sh;
}

function ealRows_(kind) {
  const sh = ealSheet_(kind), n = sh.getLastRow();
  if (n < 2) return [];
  const h = EAL_[kind], v = sh.getRange(2, 1, n - 1, h.length).getValues();
  return v.map((r, i) => { const o = {_row: i + 2}; h.forEach((k, j) => o[k] = r[j] instanceof Date ? Utilities.formatDate(r[j], 'Asia/Tokyo', 'yyyy-MM-dd HH:mm') : r[j]); return o; });
}

function ealWriteRow_(kind, row, obj) {     // row = sheet row number or null to append; one setValues call
  const sh = ealSheet_(kind), h = EAL_[kind], vals = [h.map(k => (obj[k] === undefined || obj[k] === null) ? '' : obj[k])];
  if (row) sh.getRange(row, 1, 1, h.length).setValues(vals); else sh.getRange(sh.getLastRow() + 1, 1, 1, h.length).setValues(vals);
}

function ealAuth_(body, who) {
  const want = PropertiesService.getScriptProperties().getProperty(who === 'ea' ? 'EA_KEY' : 'APP_KEY');
  if (!want) throw new Error('key not set up: run eaSetupKeys() in the editor');
  if (String(body.key || '') !== want) throw new Error('bad key');
}

const EAL_EA_ACTIONS_ = {eaHeartbeat: 1, eaTradeOpen: 1, eaTradeClose: 1, eaSignal: 1, eaLog: 1, eaResList: 1, eaResFilled: 1};
const EAL_APP_ACTIONS_ = {eaGetDashboard: 1, eaSaveConfig: 1, eaGetTrades: 1, eaResSave: 1};

/** Router: called from doGet / doPost for every action starting with "ea". */
function routeEALive_(action, body) {
  try {
    if (EAL_EA_ACTIONS_[action]) ealAuth_(body, 'ea');
    else if (EAL_APP_ACTIONS_[action]) ealAuth_(body, 'app');
    else return null;                                   // not ours: let Code.gs handle it (old EA actions)
    const fn = {eaHeartbeat: ealHeartbeat_, eaTradeOpen: ealTradeOpen_, eaTradeClose: ealTradeClose_, eaSignal: ealSignal_, eaLog: ealLog_,
                eaGetDashboard: ealDashboard_, eaSaveConfig: ealSaveConfig_, eaGetTrades: ealGetTrades_,
                eaResList: ealResList_, eaResFilled: ealResFilled_, eaResSave: ealResSave_}[action];
    const lock = LockService.getScriptLock();
    const write = !(action === 'eaGetDashboard' || action === 'eaGetTrades' || action === 'eaResList');
    if (write) lock.waitLock(20000);
    try { return fn(body); } finally { if (write) lock.releaseLock(); }
  } catch (e) {
    return {success: false, error: String(e && e.message || e)};
  }
}

function ealConfigFor_(account) {
  const r = ealRows_('config').find(x => String(x.Account) === String(account));
  if (!r) return null;
  try { return JSON.parse(r.ConfigJSON); } catch (e) { return null; }
}

function ealHeartbeat_(b) {
  const acc = String(b.account || 'demo'), now = ealNow_();
  const st = ealRows_('status').find(x => String(x.Account) === acc);
  ealWriteRow_('status', st ? st._row : null, {Account: acc, Login: b.login, Balance: b.balance, Equity: b.equity, Peak: b.peak, DD: b.dd,
                                              Positions: b.positions, Outbox: b.outbox, EATime: b.time, UpdatedAt: now});
  const day = now.slice(0, 10), d = ealRows_('daily');
  const today = d.find(x => String(x.Date).slice(0, 10) === day && String(x.Account) === acc);
  ealWriteRow_('daily', today ? today._row : null, {Date: day, Account: acc, Balance: b.balance, Equity: b.equity, Peak: b.peak, DD: b.dd});
  PropertiesService.getScriptProperties().setProperty('EA_LAST_HEARTBEAT_' + acc, String(Date.now()));
  return {success: true, config: ealConfigFor_(acc), reservations: ealWaiting_(acc)};
}

function ealTradeOpen_(b) {
  const now = ealNow_(), id = String(b.account) + ':' + String(b.ticket);
  if (ealRows_('trades').some(x => String(x.TradeID) === id)) return {success: true, duplicate: true};
  ealWriteRow_('trades', null, {TradeID: id, Account: b.account, Source: b.source || 'EA', EA: b.ea, Symbol: b.symbol, Direction: Number(b.side) === 1 ? 'BUY' : 'SELL',
    Ticket: b.ticket, SignalTime: b.signal_time, EntryTime: b.entry_time, EntryPrice: b.fill, SLPrice: b.sl, TPPrice: b.tp, Lot: b.lots,
    RiskJPY: b.risk_jpy, LotMult: b.mult, Weight: b.weight, Reason: b.reason, Note: b.note, Status: 'OPEN', CreatedAt: now, UpdatedAt: now});
  return {success: true};
}

function ealTradeClose_(b) {
  const id = String(b.account) + ':' + String(b.ticket), r = ealRows_('trades').find(x => String(x.TradeID) === id);
  if (!r) { ealLog_({account: b.account, level: 'warn', ea: b.ea, message: 'close for unknown ticket ' + b.ticket}); return {success: true, unknown: true}; }
  ealWriteRow_('trades', r._row, Object.assign({}, r, {ExitTime: b.exit_time, ExitPrice: b.exit, Profit: b.profit, R: b.R, Status: 'CLOSED', UpdatedAt: ealNow_()}));
  return {success: true};
}

function ealSignal_(b) {          // signals that were NOT traded (signal-only mode, stopped, min-lot skip): log only
  return ealLog_({account: b.account, level: 'signal', ea: b.ea, message: [b.symbol, Number(b.side) === 1 ? 'BUY' : 'SELL', b.price, 'SL ' + b.sl, b.status || ''].join(' ')});
}

function ealLog_(b) {
  const sh = ealSheet_('log');
  sh.getRange(sh.getLastRow() + 1, 1, 1, EAL_.log.length).setValues([[ealNow_(), b.account || '', b.level || 'info', b.ea || '', String(b.message || '').slice(0, 500)]]);
  if (Math.random() < 0.02) ealPruneLog_();
  return {success: true};
}

function ealPruneLog_() {
  const sh = ealSheet_('log'), n = sh.getLastRow(); if (n < 3) return;
  const cut = Utilities.formatDate(new Date(Date.now() - 90 * 864e5), 'Asia/Tokyo', 'yyyy-MM-dd');
  const t = sh.getRange(2, 1, n - 1, 1).getValues(); let k = 0;
  while (k < t.length && String(t[k][0]).slice(0, 10) < cut) k++;
  if (k > 0) sh.deleteRows(2, k);
}

function ealDashboard_(b) {
  const cfg = {}; ealRows_('config').forEach(r => { try { cfg[r.Account] = JSON.parse(r.ConfigJSON); } catch (e) {} });
  const status = {}; ealRows_('status').forEach(r => { delete r._row; status[r.Account] = r; });
  const res = ealRows_('res').filter(r => r.Status === 'WAIT' || String(r.UpdatedAt).slice(0, 10) >= Utilities.formatDate(new Date(Date.now() - 30 * 864e5), 'Asia/Tokyo', 'yyyy-MM-dd'))
    .map(r => { delete r._row; return r; });
  return {success: true, config: cfg, status: status, trades: ealGetTrades_({limit: b.limit || 300}).data, reservations: res,
          daily: ealRows_('daily').slice(-800).map(r => { delete r._row; return r; })};
}

function ealGetTrades_(b) {
  const rows = ealRows_('trades'), lim = Number(b.limit || 300);
  return {success: true, data: rows.slice(-lim).map(r => { delete r._row; return r; })};
}

function ealSaveConfig_(b) {
  const acc = String(b.account || 'demo');
  if (!b.config || typeof b.config !== 'object') throw new Error('config required');
  const r = ealRows_('config').find(x => String(x.Account) === acc);
  ealWriteRow_('config', r ? r._row : null, {Account: acc, ConfigJSON: JSON.stringify(b.config), UpdatedAt: ealNow_()});
  return {success: true};
}

// ---------- reservations (予約エントリー)
function ealWaiting_(acc) {
  return ealRows_('res').filter(r => r.Status === 'WAIT' && String(r.Account) === String(acc)).map(r => { delete r._row; return r; });
}
function ealResList_(b) { return {success: true, reservations: ealWaiting_(String(b.account || 'demo'))}; }

function ealResFilled_(b) {
  const r = ealRows_('res').find(x => String(x.ResID) === String(b.res_id));
  if (!r) return {success: true, unknown: true};
  ealWriteRow_('res', r._row, Object.assign({}, r, {Status: 'FILLED', TradeID: b.trade_id || '', UpdatedAt: ealNow_()}));
  return {success: true};
}

/** App: op = 'create' (fields below) or 'cancel' (resId). */
function ealResSave_(b) {
  const now = ealNow_();
  if (b.op === 'cancel') {
    const r = ealRows_('res').find(x => String(x.ResID) === String(b.resId));
    if (!r) throw new Error('reservation not found');
    if (r.Status !== 'WAIT') return {success: true, status: r.Status};
    ealWriteRow_('res', r._row, Object.assign({}, r, {Status: 'CANCEL', UpdatedAt: now}));
    return {success: true, status: 'CANCEL'};
  }
  const sym = String(b.symbol || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (!sym) throw new Error('symbol required');
  const dir = String(b.direction || '').toUpperCase(); if (dir !== 'BUY' && dir !== 'SELL') throw new Error('direction BUY or SELL');
  const trig = String(b.trigger || 'M15').toUpperCase() === 'H1' ? 'H1' : 'M15';
  const mode = ['pct', 'jpy', 'lot'].indexOf(b.lotMode) >= 0 ? b.lotMode : 'pct';
  const id = 'R' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyMMddHHmmss') + Math.floor(Math.random() * 90 + 10);
  const row = {ResID: id, Account: String(b.account || 'demo'), Symbol: sym, Direction: dir, Trigger: trig, SLPrice: b.sl || '', TPPrice: b.tp || '',
               LotMode: mode, LotValue: Number(b.lotValue) || 0, Status: 'WAIT', TradeID: '', Note: String(b.note || '').slice(0, 300), CreatedAt: now, UpdatedAt: now};
  ealWriteRow_('res', null, row);
  return {success: true, reservation: row};
}

/** Hourly time trigger (add in the editor: Triggers > eaWatchdog, every hour). Telegram once when an EA PC stopped
 * sending heartbeats for over 2 hours, and once when it comes back. Needs Script properties TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID. */
function eaWatchdog() {
  const p = PropertiesService.getScriptProperties();
  ['demo', 'live'].forEach(acc => {
    const last = Number(p.getProperty('EA_LAST_HEARTBEAT_' + acc) || 0); if (!last) return;
    const down = Date.now() - last > 2 * 3600e3, flag = 'EA_DOWN_NOTIFIED_' + acc, was = p.getProperty(flag) === '1';
    if (down && !was) { ealTelegram_('EA（' + acc + '）からの通信が 2 時間以上ありません'); p.setProperty(flag, '1'); }
    if (!down && was) { ealTelegram_('EA（' + acc + '）の通信が戻りました'); p.deleteProperty(flag); }
  });
}

function ealTelegram_(text) {
  const p = PropertiesService.getScriptProperties(), tok = p.getProperty('TELEGRAM_BOT_TOKEN'), chat = p.getProperty('TELEGRAM_CHAT_ID');
  if (!tok || !chat) return;
  UrlFetchApp.fetch('https://api.telegram.org/bot' + tok + '/sendMessage', {method: 'post', payload: {chat_id: chat, text: text}, muteHttpExceptions: true});
}
