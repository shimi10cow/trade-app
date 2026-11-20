// EA settings tab for the new live EAs (2026-10-24, docs/EA_SYSTEM_PLAN.md, mockup artifact 1SGsxraBBzz7PbVN9npFTB).
// Also owns the 裁量 / EA switch of the analysis tab (the old ea.js was removed 2026-10-25).
// Backend: GAS EA_Live.gs (eaGetDashboard / eaSaveConfig) with the app key (asked once, kept on this phone).
(function () {
  const KEY_LS = 'eaLiveAppKey_v1', ACC_LS = 'eaLiveAccount_v1', CACHE_LS = 'eaLiveDash_v1';
  const CARDS = [
    {id: 'T', title: 'トレンド・ダウ', code: 'T2・T', desc: '日足 MA の向きに H4 がトレンドの時、H1 ダウの向きに M15 で入る（H4 が三角持ち合いの時は見送り）', keys: [['T2@EURUSD', 'EURUSD', ' T2'], ['T@US30', 'US30', ' T']]},
    {id: 'C', title: 'M15調整TL抜け', code: 'C', desc: 'M15 の調整 TL を抜けたら入る', keys: [['C@EURUSD', 'EURUSD', ''], ['C@USDJPY', 'USDJPY', ' 調整が長い時'], ['CA@AUDJPY', 'AUDJPY', ' H4ダウの向き']]},
    {id: 'J2', title: 'H1 ダウ転換', code: 'J2', desc: 'H1 の高値・安値の流れが変わったら入る', keys: [['J2@USDJPY', 'USDJPY', '']]},
    {id: 'S', title: 'H4MA押し目買い', code: 'S', desc: 'H4 の MA の向きに、押し目から入る（ゴールドは 11/9 から、直前 24 本で 1ATR 以上上がっていたら見送り）', keys: [['S@XAUUSD', 'XAUUSD', ''], ['S@BTCUSD', 'BTCUSD', ' 買い・平日']]},
    {id: 'Q', title: '静観後のブレイク', code: 'Q', desc: '値動きが小さい時間の後、直近 24 本の高値・安値を抜けた方に乗る（H1 MA75 の向き）。11/7 から金・銀・BTC で同じ設定、抜ける前の 24 本ですでに 3ATR 以上動いていたら見送り', keys: [['Q@XAUUSD', 'XAUUSD', ''], ['Q@XAGUSD', 'XAGUSD', ''], ['Q@BTCUSD', 'BTCUSD', ''], ['Q@AUDJPY', 'AUDJPY', ' H4ダウの向き']]},
    {id: 'DS', title: '右肩', code: 'DS', desc: 'ダブルトップ・ボトムの右肩で、反転を取る', keys: [['DS@JP225', 'JP225', ''], ['DS@US500', 'US500', ' 買い'], ['DS@XAUUSD', 'XAUUSD', ' 買い']]},
    {id: 'P', title: 'MAクロス後の押し目', code: 'P', desc: 'H1 MA20/75 のクロスで決めたトレンドの 1・2 回目の押しを、M15 ストキャスで入る（日足の向き・H4 が伸びきる前。11/3 から伸びきり・水平線の条件は外した）。+1R から H1 の山谷で追いかける', keys: [['P@XAUUSD', 'XAUUSD', ''], ['P@EURUSD', 'EURUSD', ''], ['P@USDJPY', 'USDJPY', ''], ['P@US500', 'US500', ''], ['P@US100', 'US100', '']]},
    {id: 'IX', title: '指数の H4 転換', code: 'IX', desc: 'H4 が下降トレンド（安値を 2 回切り下げ）になった後、H4 のダウが上に転換するか、ダブルボトムのネックを抜けた H4 の終値で買う。損切りは底の下、+2R から H1 の山谷で追い、+1R の後は H4 の押し安値割れ・日足の押し安値割れで決済。4 指数で 1 つの銘柄として見る', keys: [['IX@US30', 'US30', ' 買い'], ['IX@US500', 'US500', ' 買い'], ['IX@US100', 'US100', ' 買い'], ['IX@JP225', 'JP225', ' 買い']]},
    {id: 'DL', title: '日足ライン付近', code: 'DL', desc: '日足のトレンドライン（点線は確定前）から 0.5ATR(日足) 以内に来た時、H1 が SMA20 の順側で SMA20 が順向きなら、M15 のダウ転換でトレンドの向きに入る', keys: [['DL@EURUSD', 'EURUSD', ''], ['DL@USDJPY', 'USDJPY', '']]},
    {id: 'HL', title: 'H4 トレンドライン', code: 'HL', desc: 'H4 のトレンドラインから 1ATR(H4) 以内で、M15 の調整ラインを抜けたら入る（角度が急なライン・確定後の戻り・H4 ダウが逆の時は見送り）', keys: [['HL@EURUSD', 'EURUSD', '']]},
    {id: 'D', title: 'H4 の帯で M15 ダウ転換', code: 'D', desc: 'H4 の押し安値・戻り高値（またはダブルトップ・ボトムのネック）で M15 の山谷ができたら、線の点数（推進線・日足・H1 MA・M15 の線など）が 2 点以上の時だけ、M15 のダウ転換で入る。B（本転換後の最初の帯）は H4 の山谷、C（浅い押し）は M15 の山谷、11/16 から帯に H4 の山谷が 2 つ以上ある時だけ。B（本転換後の最初の帯）は H4 の山谷、C（浅い押し）は M15 の山谷、ダブルは H1 → +5R から M15 の山谷で損切りを追いかける。利確なし。ドル円はダブルだけ（11/18）。B は入りが帯から 2ATR 以上離れていたら見送る（反発から遅れた入り、11/20）。11/17 から、線は H4 の足 1 本が丸ごと（始値も終値も）抜けた時に消し、入りの時点でも線が生きていることを確かめる', keys: [['DB@EURUSD', 'EURUSD', ' B'], ['DC@EURUSD', 'EURUSD', ' C'], ['DW@EURUSD', 'EURUSD', ' ダブル'], ['DW@USDJPY', 'USDJPY', ' ダブル'], ['DB@AUDJPY', 'AUDJPY', ' B'], ['DC@AUDJPY', 'AUDJPY', ' C'], ['DW@AUDJPY', 'AUDJPY', ' ダブル'], ['DB@EURJPY', 'EURJPY', ' B'], ['DC@EURJPY', 'EURJPY', ' C'], ['DW@EURJPY', 'EURJPY', ' ダブル'], ['DB@GBPJPY', 'GBPJPY', ' B'], ['DC@GBPJPY', 'GBPJPY', ' C'], ['DW@GBPJPY', 'GBPJPY', ' ダブル'], ['DB@GBPUSD', 'GBPUSD', ' B'], ['DC@GBPUSD', 'GBPUSD', ' C'], ['DW@GBPUSD', 'GBPUSD', ' ダブル'], ['DB@AUDUSD', 'AUDUSD', ' B'], ['DC@AUDUSD', 'AUDUSD', ' C'], ['DW@AUDUSD', 'AUDUSD', ' ダブル']]},
    {id: 'R', title: 'H4 押し安値・戻り高値の反発', code: 'DR', desc: 'H4 の本転換でできた押し安値（売りは戻り高値）に、直近 90 日で H4 の山谷が 2 回以上重なっている線まで戻り、線の近くで M15 の山谷ができたら、3 日以内の M15 のダウ転換で入る。本転換から 30 日以内、H4 の推進線が割れていない、線ができてから H4 の終値で線を抜けていない、仮のダウが逆向きでない、ヒゲの抜けは 1ATR まで、反対向きの H4 推進線が生きていない時だけ。損切りは M15 の山谷の外、H4 の山谷 → +3R から H1 の山谷で追いかける。利確なし。17 銘柄（ドル円は除く）をまとめて使う前提：銘柄ごとの回数は 6〜23 回と少なく、良し悪しは偶然の範囲。D@ と重なる時は両方入る。11/18 追加', keys: [['DR@EURUSD', 'EURUSD', ''], ['DR@GBPUSD', 'GBPUSD', ''], ['DR@USDCHF', 'USDCHF', ''], ['DR@USDCAD', 'USDCAD', ''], ['DR@AUDUSD', 'AUDUSD', ''], ['DR@EURJPY', 'EURJPY', ''], ['DR@GBPJPY', 'GBPJPY', ''], ['DR@CADJPY', 'CADJPY', ''], ['DR@CHFJPY', 'CHFJPY', ''], ['DR@AUDJPY', 'AUDJPY', ''], ['DR@US30', 'US30', ''], ['DR@US500', 'US500', ''], ['DR@US100', 'US100', ''], ['DR@JP225', 'JP225', ''], ['DR@XAUUSD', 'XAUUSD', ''], ['DR@XAGUSD', 'XAGUSD', ''], ['DR@BTCUSD', 'BTCUSD', '']]},
    {id: 'X', title: 'H4 出入り口のリターンムーブ', code: 'DX', desc: 'H4 の本転換のあと、ブレイク後の最初の戻りが終わった所から、トレンドの続きに乗る形（出入り口での反発を取る形ではない。出入り口＝ブレイクされた最後の押し安値・戻り高値は、戻りの深さの目安と損切りの位置に使う）。ブレイク後の安値（高値）からの戻りで M15 がダウ転換したら入る。戻りの端が出入り口から 1ATR 以内・起点から出入り口まで 5ATR 未満・出入り口に H4 の山谷 2 回以上・H4 の終値で抜け返していない・仮のダウが逆でない・反対の推進線なし・D の点数 2 点以上・H1 の 75MA が順向きで値段がその向こう側・日足のダウが逆でない・日足の 75 日線が順向きで値段がその上（売りは下）の時だけ。ダブルボトム（トップ）からの転換は見送る（DW@ の方で入る）。損切りは出入り口の外、H4 の山谷 → +3R から H1 の山谷で追いかける。利確なし。同じ出入り口では決済されてから次。指数は買いだけ。13 銘柄をまとめて使う前提（1 銘柄 年 1 回未満、銘柄ごとの良し悪しは偶然の範囲）。11/18 追加', keys: [['DX@EURUSD', 'EURUSD', ''], ['DX@GBPUSD', 'GBPUSD', ''], ['DX@AUDUSD', 'AUDUSD', ''], ['DX@EURJPY', 'EURJPY', ''], ['DX@GBPJPY', 'GBPJPY', ''], ['DX@AUDJPY', 'AUDJPY', ''], ['DX@XAUUSD', 'XAUUSD', ''], ['DX@XAGUSD', 'XAGUSD', ''], ['DX@BTCUSD', 'BTCUSD', ''], ['DX@US30', 'US30', ' 買いだけ'], ['DX@US500', 'US500', ' 買いだけ'], ['DX@US100', 'US100', ' 買いだけ'], ['DX@JP225', 'JP225', ' 買いだけ']]},
    {id: 'M', title: '短い押し目', code: 'M', desc: '大きな流れの向きに、2〜3 本の押しで入る（RSI2・終値で入る）', keys: [['M@US30', 'US30', ''], ['M@US500', 'US500', '']]},
  ];
  const HALF = {'S@XAUUSD': 1, 'Q@XAUUSD': 1, 'P@US500': 1, 'P@US100': 1, 'P@USDJPY': 1, 'IX@US30': 1, 'IX@US500': 1, 'IX@US100': 1, 'IX@JP225': 1};   // half / full selectable
  const HALF_DEFAULT = {};                                      // half by default
  const LIVE_ON = ['T2@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'DS@JP225', 'S@BTCUSD', 'DS@US500'];
  const ALL_KEYS = CARDS.flatMap(c => c.keys.map(k => k[0]));
  const famCode = c => c.id === 'D' ? 'D@' : c.code;      // the family as the user writes it (2026-11-20)
  // ○△× (2026-11-20): z = (live average R - expected) / (family spread / sqrt(n)); >= -1 ○, -2..-1 △, < -2 ×; fewer than 10 trades: no mark.
  // Expected = the EA's own backtest average when it has >= 30 backtest trades, else the family average (per-EA backtests of 2-30 trades are noise).
  // Family average / spread of one trade's R from the backtest trades (research replay, D@ / DR / DX from the live module), 2026-11-20.
  const FAM_BT = {"C": {"avg": 0.29, "sd": 1.7}, "D": {"avg": 1.02, "sd": 3.41}, "DL": {"avg": 0.14, "sd": 1.19}, "DS": {"avg": 0.38, "sd": 1.71}, "HL": {"avg": 0.6, "sd": 3.77}, "IX": {"avg": 0.29, "sd": 1.09}, "J2": {"avg": 0.39, "sd": 2.58}, "M": {"avg": 0.15, "sd": 0.51}, "P": {"avg": 0.39, "sd": 2.23}, "Q": {"avg": 0.43, "sd": 2.67}, "R": {"avg": 1.01, "sd": 3.35}, "S": {"avg": 0.53, "sd": 3.52}, "T": {"avg": 0.28, "sd": 1.94}, "X": {"avg": 1.0, "sd": 3.14}};
  const famOfKey = k => (CARDS.find(c => c.keys.some(x => x[0] === k)) || {}).id;
  function expOf(k) { const b = (typeof BT !== 'undefined' && BT[k]) || {}, f = FAM_BT[famOfKey(k)] || {}; return b.n >= 30 && b.avgR != null ? b.avgR : f.avg; }
  function judge(n, avg, exp, sd) {
    if (n < 10 || avg == null || exp == null || !sd) return null;
    const z = (avg - exp) / (sd / Math.sqrt(n));
    return z >= -1 ? {m: '○', c: '#4ade80', z} : z >= -2 ? {m: '△', c: '#fbbf24', z} : {m: '×', c: '#f87171', z};
  }
  const REMOVED = ['L@EURUSD', 'L2@XAUUSD', 'Q@US30', 'R@EURUSD', 'A@EURUSD', 'RM@EURUSD', 'RM@XAUUSD', 'DB@USDJPY', 'DC@USDJPY', 'DA@EURUSD', 'DA@USDJPY', 'DA@AUDJPY', 'DA@EURJPY', 'DA@GBPJPY', 'DA@GBPUSD', 'DA@AUDUSD', 'DY@EURUSD', 'DY@USDJPY', 'DY@AUDJPY', 'DY@EURJPY', 'DY@GBPJPY', 'DY@GBPUSD', 'DY@AUDUSD'];   // 11/18: USDJPY keeps only DW@; DA@ / DY@ not used   // 2026-11-07: off for good, not shown
  let S = {acc: localStorage.getItem(ACC_LS) || 'demo', dash: null, sheet: null, saving: '', err: '', res: null};
  try { S.dash = JSON.parse(localStorage.getItem(CACHE_LS) || 'null'); } catch (e) {}

  function defaultConfig(acc) {
    const eas = {};
    ALL_KEYS.forEach(k => eas[k] = {mode: 'auto', on: true, weight: HALF_DEFAULT[k] ? 0.5 : 1});
    return {running: false, base_risk: 0.01, dd_half: true, notify: {notifyEntry: true, notifyExit: true, notifyError: true, notifySignal: true}, eas: eas};
  }
  function cfg() {
    S.dash = S.dash || {}; S.dash.config = S.dash.config || {};
    if (!S.dash.config[S.acc]) S.dash.config[S.acc] = defaultConfig(S.acc);      // keep it, so edits stick before the first save
    const c = S.dash.config[S.acc];
    // an EA added after this config was saved (e.g. P@ on 2026-11-02) starts OFF: it never trades until switched on here
    ALL_KEYS.forEach(k => { if (!c.eas[k]) c.eas[k] = Object.assign(defaultConfig(S.acc).eas[k], {mode: 'off'}); });
    // EAs removed from the app (still in the live registry for the magic numbers): always saved as off
    REMOVED.forEach(k => { c.eas[k] = {mode: 'off', on: false, weight: 1}; });
    return c;
  }
  const appKey = () => localStorage.getItem(KEY_LS) || '';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch]));
  const yen = v => (v === '' || v == null || isNaN(v)) ? '—' : (Number(v) < 0 ? '-¥' : '¥') + Math.abs(Math.round(Number(v))).toLocaleString();

  async function load() {
    if (!appKey()) return;
    try {
      const r = await fetch(GAS_URL + '?action=eaGetDashboard&key=' + encodeURIComponent(appKey()) + '&limit=200').then(x => x.json());
      if (r && r.success === false) { S.err = r.error || '読み込みに失敗'; render(); return; }
      S.dash = r; S.err = ''; try { localStorage.setItem(CACHE_LS, JSON.stringify(r)); } catch (e) {}
    } catch (e) { S.err = '通信できません（前回の表示）'; }
    render(); refreshViews();
  }
  let saveTimer = null;
  function save() {
    const c = cfg();
    S.saving = '保存中…'; render();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        const r = await fetch(GAS_URL, {method: 'POST', body: JSON.stringify({action: 'eaSaveConfig', key: appKey(), account: S.acc, config: c})}).then(x => x.json());
        S.saving = r && r.success ? '保存済み' : ('保存できませんでした: ' + ((r && r.error) || ''));
      } catch (e) { S.saving = '保存できませんでした（通信）'; }
      try { localStorage.setItem(CACHE_LS, JSON.stringify(S.dash)); } catch (e) {}
      render(); setTimeout(() => { if (S.saving === '保存済み') { S.saving = ''; render(); } }, 2500);
    }, 400);
  }

  // ---------- handlers
  window.eaLiveSetKey = function () { const v = (document.getElementById('eal-key') || {}).value || ''; if (v.trim()) { localStorage.setItem(KEY_LS, v.trim()); load(); } };
  window.eaLiveAcc = function (a) { S.acc = a; localStorage.setItem(ACC_LS, a); render(); };
  window.eaLiveRun = function (on) { const c = cfg(); c.running = on; save(); };
  window.eaLiveRisk = function (v) { const c = cfg(); c.base_risk = Number(v); save(); };     // keeps the lot mode: in 最小ロット it is the most one trade may lose
  // what the PC's EA code supports (heartbeat Caps): 最小ロット / シグナルのみ予約 are enabled only then (an older PC would ignore them)
  const caps = acc => String(((S.dash && S.dash.status && S.dash.status[acc]) || {}).Caps || '').split(',');
  window.eaLiveLotMode = function (v) {
    const c = cfg();
    if (v === 'min' && caps(S.acc).indexOf('min_lot') < 0) { S.err = 'PC の EA を更新すると使えます（「新EA 更新」のあと、数分で使えるようになります）'; render(); return; }
    c.lot_mode = v === 'min' ? 'min' : 'risk'; save();
  };
  window.eaLiveDDHalf = function () { const c = cfg(); c.dd_half = c.dd_half === false; save(); };
  window.eaLiveAllOn = function () { const c = cfg(); ALL_KEYS.forEach(k => { c.eas[k].on = true; if (c.eas[k].mode === 'off') c.eas[k].mode = 'auto'; }); save(); };
  window.eaLiveBT = function () { S.btOpen = !S.btOpen; render(); };
  window.eaLiveFT = function () { S.ftOpen = !S.ftOpen; render(); };
  window.eaLiveML = function () { S.mlOpen = !S.mlOpen; render(); };
  window.eaLiveNotify = function (k) { const c = cfg(); c.notify = c.notify || {}; c.notify[k] = c.notify[k] === false; save(); };
  window.eaLiveOpen = function (id) { S.sheet = id; render(); };
  window.eaLiveClose = function () { S.sheet = null; render(); };
  window.eaLiveMode = function (id, mode) { const c = cfg(); CARDS.find(x => x.id === id).keys.forEach(k => c.eas[k[0]].mode = mode); save(); };
  window.eaLiveSym = function (key) { const c = cfg(); c.eas[key].on = !c.eas[key].on; save(); };
  window.eaLiveWeight = function (key, w) { const c = cfg(); c.eas[key].weight = w; save(); };


  // ---------- reservation entries (予約): per monitored pair, M15 / H1 stochastic trigger on the EA account
  const LOT_JA = {pct: '口座の %', jpy: '最大損失（円）', lot: 'ロット'};
  const SL_JA = {stoch: 'ストキャス直下', m15ma200: 'M15 MA200', h1ma75: 'H1 MA75', h1ma200: 'H1 MA200'};
  function pairNames() {
    const ps = (typeof App !== 'undefined' && App.data && App.data.pairs) || [];
    return [...new Set(ps.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
  }
  const resAll = () => (S.dash && S.dash.reservations) || [];
  function resLine(r, withCancel) {
    const sig = String(r.Kind || '') === 'SIGNAL';
    const lot = sig ? 'Telegram に送るだけ' : r.LotMode === 'pct' ? r.LotValue + '%' : r.LotMode === 'jpy' ? yen(r.LotValue) : r.LotValue + ' lot';
    const st = {WAIT: ['待機中', '#22d3ee'], FILLED: ['約定', '#4ade80'], SIGNALED: ['送信済み', '#4ade80'], CANCEL: ['取消', '#94a3b8']}[r.Status] || [r.Status, '#94a3b8'];
    return `<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 2px;border-bottom:1px solid #1e293b;font-size:12px">
      <div><b>${esc(r.Symbol)}</b> ${String(r.Direction) === 'BUY' ? '<span style="color:#f87171">買い</span>' : '<span style="color:#38bdf8">売り</span>'} · ${esc(r.Trigger)} ${sig ? '<span style="color:#fbbf24">シグナルのみ</span>' : 'エントリー'}
        <div style="color:#94a3b8;font-size:11px">損切り ${esc(SL_JA[r.SLMode] || r.SLPrice || 'ストキャス直下')} · 利確 ${esc(r.TPPrice || 'なし')} · ${esc(lot)}${String(r.Account) === 'live' ? ' · <span style="color:#f87171">本番</span>' : ''}</div></div>
      <div style="display:flex;align-items:center;gap:6px"><span style="font-size:11px;font-weight:700;color:${st[1]}">${st[0]}</span>
        ${withCancel && r.Status === 'WAIT' ? `<button onclick="eaResCancel('${esc(r.ResID)}')" style="border:1px solid #f87171;color:#f87171;background:transparent;border-radius:6px;padding:3px 8px;font-size:11px">取消</button>` : ''}</div></div>`;
  }
  // ---------- 検証結果 (research, R after costs; min account = where the min lot risk is 1% or less, RESEARCH_LOG §107)
  // [from, to, trades, wins, losses, win %, avg R, PF, max DD (R), trades / year, R / year]
  const BTX = {"DX@AUDJPY": [2023, 2023, 2, 0, 2, 0.0, -1.027, 0.0, 2.1, 0.2, -0.2], "DX@AUDUSD": [2019, 2026, 5, 2, 3, 40.0, 0.202, 1.33, 3.0, 0.5, 0.1], "DX@BTCUSD": [2017, 2025, 6, 2, 4, 33.3, 0.335, 1.45, 4.0, 0.6, 0.2], "DX@EURJPY": [2008, 2025, 9, 1, 8, 11.1, -0.182, 0.72, 4.9, 0.5, -0.1], "DX@EURUSD": [2007, 2023, 17, 7, 10, 41.2, 1.213, 3.69, 3.2, 0.8, 1.0], "DX@GBPJPY": [2007, 2026, 15, 8, 7, 53.3, 0.509, 2.52, 3.1, 0.8, 0.4], "DX@GBPUSD": [2011, 2024, 8, 4, 4, 50.0, 0.888, 2.82, 2.9, 0.4, 0.4], "DX@XAUUSD": [2014, 2026, 13, 9, 4, 69.2, 2.829, 12.01, 2.1, 0.7, 1.8], "DX@JP225": [2017, 2026, 4, 1, 3, 25.0, 0.084, 1.12, 2.9, 0.4, 0.0], "DX@XAGUSD": [2019, 2026, 7, 2, 5, 28.6, 2.679, 4.09, 3.9, 0.7, 1.9], "DX@US100": [2018, 2026, 10, 3, 7, 30.0, 0.97, 2.5, 3.1, 1.0, 1.0], "DX@US30": [2017, 2021, 5, 2, 3, 40.0, 0.555, 1.88, 3.2, 0.5, 0.3], "DX@US500": [2019, 2025, 7, 3, 4, 42.9, 0.895, 2.6, 1.8, 0.7, 0.6], "DR@AUDJPY": [2019, 2025, 6, 4, 2, 66.7, 6.679, 19.13, 1.1, 0.6, 4.0], "DR@AUDUSD": [2019, 2026, 15, 7, 8, 46.7, 1.336, 3.61, 6.6, 1.5, 2.0], "DR@BTCUSD": [2021, 2026, 7, 4, 3, 57.1, 2.884, 7.61, 2.0, 0.7, 2.1], "DR@CADJPY": [2007, 2022, 14, 7, 7, 50.0, 0.918, 2.78, 3.5, 0.7, 0.6], "DR@CHFJPY": [2007, 2026, 14, 5, 9, 35.7, 0.365, 1.59, 5.1, 0.7, 0.3], "DR@EURJPY": [2007, 2022, 15, 5, 10, 33.3, 1.104, 2.74, 7.1, 0.8, 0.8], "DR@EURUSD": [2007, 2025, 14, 2, 12, 14.3, 0.171, 1.2, 6.7, 0.7, 0.1], "DR@GBPJPY": [2010, 2026, 21, 7, 14, 33.3, 0.707, 2.03, 4.2, 1.1, 0.7], "DR@GBPUSD": [2007, 2025, 23, 11, 12, 47.8, 0.913, 2.87, 3.9, 1.1, 1.1], "DR@XAUUSD": [2013, 2026, 12, 2, 10, 16.7, -0.333, 0.62, 6.9, 0.6, -0.2], "DR@JP225": [2017, 2026, 11, 2, 9, 18.2, -0.593, 0.32, 6.5, 1.1, -0.7], "DR@XAGUSD": [2018, 2022, 11, 4, 7, 36.4, 0.176, 1.23, 3.9, 1.1, 0.2], "DR@US100": [2019, 2025, 8, 5, 3, 62.5, 0.966, 3.5, 1.1, 0.8, 0.8], "DR@US30": [2019, 2026, 12, 8, 4, 66.7, 1.794, 6.28, 2.0, 1.2, 2.2], "DR@US500": [2019, 2025, 11, 6, 5, 54.5, 1.9, 5.63, 2.4, 1.1, 2.1], "DR@USDCAD": [2007, 2026, 15, 9, 6, 60.0, 1.715, 5.14, 3.1, 0.8, 1.3], "DR@USDCHF": [2007, 2026, 12, 4, 8, 33.3, 0.253, 1.36, 8.4, 0.6, 0.2], "DY@AUDJPY": [2018, 2026, 32, 11, 21, 34.4, 0.935, 2.44, 5.6, 3.2, 3.0], "DY@AUDUSD": [2018, 2026, 42, 14, 28, 33.3, 0.352, 1.52, 12.2, 4.2, 1.5], "DY@EURJPY": [2007, 2026, 74, 21, 53, 28.4, 0.453, 1.68, 9.2, 3.7, 1.7], "DY@EURUSD": [2007, 2026, 70, 27, 43, 38.6, 0.545, 1.9, 7.7, 3.5, 1.9], "DY@GBPJPY": [2006, 2026, 81, 33, 48, 40.7, 0.698, 2.2, 9.7, 4.0, 2.8], "DY@GBPUSD": [2007, 2026, 67, 27, 40, 40.3, 0.635, 2.04, 7.7, 3.4, 2.1], "DY@USDJPY": [2006, 2025, 63, 19, 44, 30.2, 0.395, 1.57, 14.9, 3.1, 1.2], "DC@AUDJPY": [2019, 2019, 4, 1, 3, 25.0, -0.473, 0.05, 2.0, 0.4, -0.2], "DC@AUDUSD": [2021, 2024, 3, 2, 1, 66.7, 0.215, 17.65, 0.0, 0.3, 0.1], "DC@EURJPY": [2010, 2025, 9, 5, 4, 55.6, 1.152, 4.51, 1.6, 0.5, 0.5], "DC@EURUSD": [2007, 2017, 7, 6, 1, 85.7, 2.068, 15.04, 1.0, 0.3, 0.7], "DC@GBPJPY": [2012, 2023, 5, 3, 2, 60.0, 0.673, 16.71, 0.2, 0.2, 0.2], "DC@GBPUSD": [2014, 2024, 6, 1, 5, 16.7, -0.626, 0.02, 3.8, 0.3, -0.2], "DC@USDJPY": [2007, 2024, 14, 8, 6, 57.1, 0.419, 3.57, 1.2, 0.7, 0.3], "DA@AUDJPY": [2019, 2026, 14, 5, 9, 35.7, 1.425, 3.21, 2.7, 1.9, 2.7], "DB@AUDJPY": [2020, 2025, 5, 2, 3, 40.0, 4.345, 7.89, 2.1, 0.5, 2.2], "DW@AUDJPY": [2019, 2026, 26, 11, 15, 42.3, 1.187, 3.42, 4.2, 2.6, 3.1], "DA@AUDUSD": [2018, 2026, 13, 3, 10, 23.1, -0.301, 0.64, 7.5, 1.6, -0.5], "DB@AUDUSD": [2019, 2026, 7, 4, 3, 57.1, 2.856, 7.2, 1.1, 0.7, 2.0], "DW@AUDUSD": [2018, 2026, 15, 5, 10, 33.3, 0.193, 1.28, 6.9, 1.5, 0.3], "DA@EURJPY": [2008, 2026, 25, 7, 18, 28.0, 0.11, 1.15, 6.7, 1.3, 0.1], "DB@EURJPY": [2007, 2026, 21, 7, 14, 33.3, 1.178, 2.84, 5.2, 1.1, 1.2], "DW@EURJPY": [2008, 2026, 45, 16, 29, 35.6, 0.528, 1.92, 6.5, 2.2, 1.2], "DA@EURUSD": [2007, 2026, 28, 8, 20, 28.6, 0.315, 1.51, 10.5, 1.4, 0.5], "DB@EURUSD": [2007, 2025, 20, 4, 16, 20.0, -0.395, 0.49, 8.1, 1.0, -0.4], "DW@EURUSD": [2008, 2026, 41, 15, 26, 36.6, 0.462, 1.83, 9.5, 2.0, 0.9], "DA@GBPJPY": [2007, 2026, 26, 12, 14, 46.2, 0.852, 2.54, 8.2, 1.3, 1.1], "DB@GBPJPY": [2008, 2026, 19, 6, 13, 31.6, 1.054, 2.54, 10.5, 0.9, 1.0], "DW@GBPJPY": [2008, 2026, 36, 21, 15, 58.3, 1.123, 4.07, 3.5, 1.8, 2.0], "DA@GBPUSD": [2007, 2026, 42, 18, 24, 42.9, 0.702, 2.24, 6.5, 2.1, 1.5], "DB@GBPUSD": [2007, 2025, 16, 6, 10, 37.5, 3.431, 6.77, 3.5, 0.8, 2.7], "DW@GBPUSD": [2008, 2026, 37, 19, 18, 51.4, 1.411, 3.86, 3.5, 1.9, 2.6], "DA@USDJPY": [2007, 2026, 29, 5, 24, 17.2, 0.012, 1.01, 19.0, 1.5, 0.0], "DB@USDJPY": [2007, 2026, 15, 4, 11, 26.7, 0.877, 2.13, 6.3, 0.8, 0.7], "DW@USDJPY": [2007, 2021, 28, 13, 15, 46.4, 1.08, 3.3, 3.6, 1.4, 1.5], "Q@AUDJPY":[2005,2026,111,49,62,44.1,0.683,2.21,9.2,5.3,3.6],"CA@AUDJPY":[2005,2026,231,112,119,48.5,0.248,1.49,7.4,10.7,2.7],"C@EURUSD":[2005,2026,199,109,90,54.8,0.461,2.1,8.7,9.3,4.3],"C@USDJPY":[2005,2026,224,104,120,46.4,0.373,1.75,11.1,10.4,3.9],"DS@JP225":[2017,2026,124,49,75,39.5,0.255,1.83,3.7,13.4,3.4],"DS@US500":[2017,2026,57,24,33,42.1,0.259,1.78,4.0,6.2,1.6],"DS@XAUUSD":[2005,2026,189,93,96,49.2,0.27,1.58,6.2,9.0,2.4],"J2@USDJPY":[2006,2026,234,97,137,41.5,0.565,2.01,13.6,11.5,6.5],"M@US30":[2017,2026,91,65,26,71.4,0.077,1.41,2.8,9.9,0.8],"M@US500":[2017,2026,89,68,21,76.4,0.132,1.85,3.9,9.7,1.3],"Q@XAGUSD":[2005,2026,254,103,151,40.6,0.512,1.92,7.8,12.2,6.2],"Q@XAUUSD":[2005,2026,457,204,253,44.6,0.545,2.04,14.3,21.0,11.4],"S@BTCUSD":[2017,2026,349,116,233,33.2,0.581,1.82,17.9,37.3,21.7],"S@XAUUSD":[2005,2026,410,146,264,35.6,0.498,1.78,11.8,19.0,9.5],"T2@EURUSD":[2005,2026,303,128,175,42.2,0.533,1.91,18.3,14.0,7.5],"T@US30":[2017,2026,101,41,60,40.6,0.304,1.49,15.7,10.9,3.3],"P@XAUUSD":[2005,2026,318,154,164,48.4,0.95,3.0,16.0,14.9,14.1],"P@EURUSD":[2005,2026,158,81,77,51.3,0.373,1.81,10.4,7.4,2.8],"P@USDJPY":[2005,2026,178,76,102,42.7,0.266,1.5,13.3,8.2,2.2],"P@US500":[2017,2026,128,63,65,49.2,0.254,1.53,11.6,13.9,3.5],"P@US100":[2017,2026,122,62,60,50.8,0.298,1.64,8.4,13.3,4.0],"DL@EURUSD":[2005,2026,44,26,18,59.1,0.249,1.59,3.8,2.0,0.5],"DL@USDJPY":[2005,2026,46,25,21,54.3,0.322,1.76,4.3,2.1,0.7],"HL@EURUSD":[2005,2026,89,47,42,52.8,1.32,4.19,4.4,4.2,5.5],"Q@BTCUSD":[2017,2026,332,125,207,37.7,0.728,2.19,16.6,36.2,26.4],"IX@US30":[2018,2026,48,25,23,52.1,0.143,1.35,4.0,5.5,0.8],"IX@US500":[2017,2026,50,28,22,56.0,0.144,1.43,3.9,5.4,0.8],"IX@US100":[2017,2026,52,31,21,59.6,0.331,1.97,6.6,5.6,1.9],"IX@JP225":[2017,2026,58,34,24,58.6,0.311,1.96,4.1,6.3,2.0]};
  const MIN_ACC = { 'DX@AUDJPY': 20, 'DX@AUDUSD': 20, 'DX@BTCUSD': 20, 'DX@EURJPY': 20, 'DX@EURUSD': 20, 'DX@GBPJPY': 20, 'DX@GBPUSD': 20, 'DX@XAUUSD': 60, 'DX@JP225': 20, 'DX@XAGUSD': 30, 'DX@US100': 30, 'DX@US30': 30, 'DX@US500': 20, 'DR@EURUSD': 20, 'DR@GBPUSD': 20, 'DR@USDCHF': 20, 'DR@USDCAD': 20, 'DR@AUDUSD': 20, 'DR@EURJPY': 20, 'DR@GBPJPY': 20, 'DR@CADJPY': 20, 'DR@CHFJPY': 20, 'DR@AUDJPY': 20, 'DR@US30': 40, 'DR@US500': 20, 'DR@US100': 50, 'DR@JP225': 20, 'DR@XAUUSD': 40, 'DR@XAGUSD': 40, 'DR@BTCUSD': 30, 'DY@EURUSD': 20, 'DY@USDJPY': 20, 'DY@AUDJPY': 20, 'DY@EURJPY': 20, 'DY@GBPJPY': 20, 'DY@GBPUSD': 20, 'DY@AUDUSD': 20, 'DA@EURUSD': 20, 'DA@USDJPY': 20, 'DA@AUDJPY': 20, 'DA@EURJPY': 20, 'DA@GBPJPY': 20, 'DA@GBPUSD': 20, 'DA@AUDUSD': 20, 'DB@EURUSD': 20, 'DC@EURUSD': 20, 'DW@EURUSD': 20, 'DB@USDJPY': 20, 'DC@USDJPY': 20, 'DW@USDJPY': 20, 'DB@AUDJPY': 20, 'DC@AUDJPY': 20, 'DW@AUDJPY': 20, 'DB@EURJPY': 20, 'DC@EURJPY': 20, 'DW@EURJPY': 20, 'DB@GBPJPY': 20, 'DC@GBPJPY': 20, 'DW@GBPJPY': 20, 'DB@GBPUSD': 20, 'DC@GBPUSD': 20, 'DW@GBPUSD': 20, 'DB@AUDUSD': 20, 'DC@AUDUSD': 20, 'DW@AUDUSD': 20, 'T2@EURUSD': 20, 'C@EURUSD': 20, 'C@USDJPY': 20, 'CA@AUDJPY': 20, 'Q@AUDJPY': 20, 'J2@USDJPY': 20, 'DS@JP225': 20, 'S@BTCUSD': 20,
    'DS@US500': 30, 'M@US500': 40, 'T@US30': 60, 'DS@XAUUSD': 60, 'Q@XAGUSD': 50, 'S@XAUUSD': 50, 'Q@XAUUSD': 40, 'M@US30': 220,
    'P@USDJPY': 20, 'P@EURUSD': 20, 'P@XAUUSD': 60, 'P@US500': 20, 'P@US100': 40,
    'DL@EURUSD': 20, 'DL@USDJPY': 20, 'HL@EURUSD': 20, 'Q@BTCUSD': 20, 'IX@JP225': 20, 'IX@US500': 40, 'IX@US30': 220, 'IX@US100': 140};   // IX (2026-11-08 recheck): median stop of 2023- trades x prices 2026-11 x 0.1 lot (Cash: 1 lot = 1 / point), 158.5 JPY/USD; US100 was 3x too high before
  const EA_DESC = {
    "T2@EURUSD": "日足と H4 がトレンドの時、H1 のダウの向きへの押し目を M15 ストキャスで拾う（H4 の 3 回目の押しは見送り。11/15 から、進む方向の 1R 以内に H4 の水平線＝転換の押し安値・戻り高値と起点の高値・安値があれば見送り）。伸びたら H1 の山谷で追う",
    "T@US30": "T2 と同じ入り方（H4 が伸びきった時・水平線で跳ねた直後は見送り）。伸びたら H1 の山谷で追う",
    "C@EURUSD": "M15 で大きく伸びた後の調整トレンドラインを抜けて、M15 が転換したら入る（日足の向きだけ。H1 で伸びきった後は見送り）。損切りは M15 の転換点の外、+1R から H1 の山谷で追う",
    "C@USDJPY": "C と同じ入り方で、調整が長く線が強い時だけ（H4 の MA が開きすぎ・三角持ち合いの中は見送り）。+1R から H1 の山谷で追う",
    "CA@AUDJPY": "C と同じ入り方で、H4 ダウの向き（1〜4 段目）と日足の向きの時だけ。損切りは M15 の転換点の外。+1.5R までは H4 の押し安値割れで決済、+1.5R から M15 の山谷で追う",
    "J2@USDJPY": "H1 のダウ転換の出だしに、M15 の仮の転換で乗る（週足と同じ向きだけ）。+1R の後に H1 の高値が切り下がったら決済、H4 の 4 段目以降は M15 の山谷で追う",
    "S@XAUUSD": "H4 と H1 の MA の向きがそろった時、押し目で M15 が転換したら買う（直前 24 本で 1ATR 以上上がっていたら見送り）。+2R から H1 の山谷で追う",
    "S@BTCUSD": "S と同じ入り方で、BTC の買いだけ（土日は入らない）。伸びたら H1 の山谷で追う",
    "Q@XAUUSD": "値動きが小さい時間の後、直近 24 本の H1 の高値・安値を終値で抜けた方に乗る（H1 MA75 の向き。直前に大きく動いていたら見送り）。損切りはレンジの真ん中の外、+1R から H1 の山谷で追う",
    "Q@XAGUSD": "ゴールドの Q と同じ入り方（損切りが遠すぎるブレイクは見送り）。+1R から H1 の山谷で追う",
    "Q@BTCUSD": "ゴールドの Q と同じ入り方。+1R から H1 の山谷で追う",
    "Q@AUDJPY": "Q と同じ入り方で、H4 ダウと日足の向きの時だけ（H4 の MA75 から離れすぎていたら見送り）。+1.5R までは H4 の押し安値割れで決済、+1.5R から H1 の山谷で追う",
    "DS@JP225": "H1 のダウ転換の後、ダブルトップ・ボトムの右肩で M15 が転換したら入る。損切りは左肩の外、H4 の山谷ができたら 1 段上げる。+1.5R から H1 の山谷で追う",
    "DS@US500": "日経の右肩と同じ入り方で、買いだけ。損切りは左肩の外。+1.5R から H1 の山谷で追う",
    "DS@XAUUSD": "右肩の入り方で、買いだけ。損切りは右肩の外。+1R から H1 の山谷で追う",
    "P@XAUUSD": "H1 の MA20 と MA75 のクロスで決めたトレンドの 1・2 回目の押しを、M15 ストキャスで入る（日足の向き・H4 が伸びきる前）。+1R から H1 の山谷で追う",
    "P@EURUSD": "ゴールドの P と同じ入り方。+1R から H1 の山谷で追う",
    "P@USDJPY": "ゴールドの P と同じ入り方。+1R から H1 の山谷で追う。+1R の後に H1 の高値が切り下がったら決済",
    "P@US500": "ゴールドの P と同じ入り方。+1R から H1 の山谷で追う",
    "P@US100": "ゴールドの P と同じ入り方。+1R から H1 の山谷で追う",
    "DL@EURUSD": "日足のトレンドラインから 0.5ATR(日足) 以内に来た時、H1 が SMA20 の順側なら、M15 のダウ転換でトレンドの向きに入る。損切りは M15 の転換点とラインの外、+1R から M15 の山谷で追う",
    "DL@USDJPY": "ユーロドルの DL と同じ入り方",
    "HL@EURUSD": "H4 のトレンドラインから 1ATR(H4) 以内で、M15 の調整ラインを抜けたら入る（H4 ダウが逆・急すぎる線は見送り）。損切りは M15 の転換点とラインの外、+1R から H1 の山谷で追う",
    "M@US30": "日足で 200 日線より上の時、RSI(2) が 10 未満の短い押し目を買い、5 日線を超えたら決済",
    "M@US500": "US30 の M と同じ入り方",
    "IX@US30": "H4 が下降トレンドになった後、H4 のダウが上に転換するか、ダブルボトムのネックを抜けた H4 の終値で買う。損切りは底の下。+1R の後は H4 の押し安値割れで決済、+2R から H1 の山谷で追う",
    "IX@US500": "US30 の IX と同じ入り方",
    "IX@US100": "US30 の IX と同じ入り方",
    "IX@JP225": "US30 の IX と同じ入り方"
    };

  // portfolio combinations (2026-11-08 later: + CA@AUDJPY and Q@AUDJPY in the FX tier, C@USDJPY with the triangle skip; same method gives 27 EAs 118/154/222/224/234%, the old table 119/155/224/227/238%) (2026-11-08: broker-time data 2017-07.., all 27 EAs in the app, live lot rules; earlier note 2026-11-03: live-code trades with all gates, R@EURUSD and A@EURUSD off, RM@ added, L / L2 daily side 4 ATR, P without the level / impulse conditions, J2 weekly trend, P@US500 / P@US100 full lot, RM off; same method as RESEARCH_LOG §107:
  // 1% risk, half at DD 10%, flat lots (no calendar x1.5 from 2026-11-08, D14), all full lot, backtest as is; trendlab/rm/combos.py)
  // 2026-11-14: T2@EURUSD with the H4-line skip (eas/h4lines.py) over its whole history: 375 -> 303 trades; table, totals and MC_MONTHS redone
  const COMBOS = [   // 2026-11-20: D@ B skips entries >= 2.0 ATR from the level; all 78 EAs, minimum accounts from the min-lot loss at 2026-11-04 prices
    ["20 万円", "56 本", "FX・日経・BTC・US500 などの最小ロットで 1% 以内の EA（D@ 19・DR 12・DX 9・P 3・C 2・DL 2・Q 2・T2 1・HL 1・S 1・J2 1・右肩 1・IX 1・CA 1）", "+207%", "-14%", "約 227 回"],
    ["30 万円", "61 本", "＋US500 右肩・BTC DR・銀 DX・US100 DX・US30 DX", "+234%", "-14%", "約 236 回"],
    ["50 万円", "71 本", "＋銀 Q・US100 P・ゴールド S・ゴールド Q・US500 短い押し目・US500 IX・ゴールド DR・銀 DR・US100 DR・US30 DR", "+332%", "-16%", "約 325 回"],
    ["100 万円", "75 本", "＋US30 トレンド・ゴールド 右肩・ゴールド P・ゴールド DX", "+369%", "-17%", "約 361 回"],
    ["150 万円", "76 本", "＋US100 IX", "+377%", "-18%", "約 366 回"],
    ["300 万円", "78 本（全部）", "＋US30 短い押し目・US30 IX", "+389%", "-17%", "約 381 回"],
  ];
  // 2026-11-16: D@ (18 EAs: B / C / W on EURUSD, AUDJPY, EURJPY, GBPJPY, GBPUSD, AUDUSD) added; [account, before %, before DD, after %, after DD]
  const D_CMP = [["20 万円", 128, 17, 207, 14], ["30 万円", 125, 19, 234, 14], ["50 万円", 178, 21, 332, 16], ["100 万円", 218, 21, 369, 17], ["150 万円", 223, 19, 377, 18], ["300 万円", 227, 19, 389, 17]];
  function comboTable() {
    const tr = c => `<tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px;white-space:nowrap">${c[0]}</td><td style="white-space:nowrap">${c[1]}</td><td style="color:#4ade80">${c[3]}</td><td style="color:#f87171">${c[4]}</td></tr>
      <tr><td colspan="4" style="text-align:left;padding:0 4px 6px;font-size:10px;color:#94a3b8">${c[2]}${c[5] ? ' · 年 ' + c[5] : ''}</td></tr>`;
    return `<div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:14px 0 4px">組み合わせの結果（口座の大きさごと）</div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right">
        <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">口座</th><th>EA</th><th>年利</th><th>最大 DD</th></tr>${COMBOS.map(tr).join('')}</table>

      <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:14px 0 4px">D 系（D@・DR@・DX@）を足した効果（11/18 更新）</div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right">
        <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">口座</th><th>前の年利</th><th>前の DD</th><th>足した後</th><th>DD</th></tr>${D_CMP.map(c => `<tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px;white-space:nowrap">${c[0]}</td><td>+${c[1]}%</td><td style="color:#f87171">-${c[2]}%</td><td style="color:#4ade80;font-weight:700">+${c[3]}%</td><td style="color:#f87171">-${c[4]}%</td></tr>`).join('')}</table>
      <div style="font-size:10px;color:#64748b;margin-top:4px;line-height:1.5">D 系 49 本だけ（D@ は FX6 の B・C・W とドル円の W、DR@ 17 本、DX@ 13 本）：404 回・勝率 43.1%・平均 +1.09R・年 +47R・最大 DD 10.5R、1 回 1% で年利 +54%・DD -10.0%。全体（1%）は +227% → +389%、DD -18.5% → -17.4%、年あたり +153R → +199R。口座ごとの表は、最低口座が足りる D 系だけ足した。</div>
      <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:14px 0 4px">全体（78 本すべて）</div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right">
        <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">リスク</th><th>年利</th><th>最大 DD</th></tr><tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px">0.5%</td><td style="color:#4ade80">+147%</td><td style="color:#f87171">-12.2%</td></tr><tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px">1%</td><td style="color:#4ade80">+389%</td><td style="color:#f87171">-17.4%</td></tr><tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px">1.5%</td><td style="color:#4ade80">+675%</td><td style="color:#f87171">-23.2%</td></tr><tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px">2%</td><td style="color:#4ade80">+1121%</td><td style="color:#f87171">-28.8%</td></tr></table>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:10px">${[['トレード数', '3,557 回'], ['勝ち・負け', '1,582 勝 1,975 敗'], ['勝率', '44.5%'], ['月のトレード', '約 32 回'], ['負けた月', '13%'], ['年あたり', '+199R'], ['平均', '+0.52R'], ['最大 DD', '24.9R']].map(([a, b]) => `<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:6px 8px"><div style="font-size:10px;color:#94a3b8">${a}</div><div style="font-size:12px;font-weight:700;color:#e2e8f0;margin-top:2px">${b}</div></div>`).join('')}</div>
      <div style="font-size:10px;color:#64748b;margin-top:6px">2017 年 7 月〜2026 年 10 月のバックテスト（コスト込み・1 回 1R）</div>`;
  }
  // money lost by one losing trade at the minimum lot (2026-11-19: median stop width of the trades since 2023 from the live code, XM KIWAMI specs, prices 2026-11-04, 1 USD = 158.4 JPY)
  // [EA, loss at the minimum lot, median stop width]. Live settings: gold 右肩 = above the right shoulder, buy only (§103);
  // US500 右肩 = buy only, above the left shoulder (§103). Checked against real XM trades 2026-10-25 (BTC 0.01 lot, UK100 1 lot = 1 GBP / point)
  const MINLOT_LOSS = [["FX：T2・C・DL・HL・J2・CA・Q（ユーロドル・ドル円・豪ドル円）", "約 348〜798 円", "約 33〜73 pips"], ["FX：P（MAクロス後の押し目、ユーロドル・ドル円）", "約 594〜909 円", "約 57〜59 pips"], ["FX：D@（H4 の帯、6 通貨＋ドル円のダブル）", "約 213〜695 円", "約 13〜70 pips"], ["FX：DR@（押し安値・戻り高値の反発、10 通貨）", "約 234〜653 円", "約 23〜65 pips"], ["FX：DX@（出入り口のリターンムーブ、6 通貨）", "約 305〜1,084 円", "約 19〜108 pips"], ["ゴールド DR（押し安値・戻り高値の反発）", "約 3,058 円", "約 19 ドル（0.5%）"], ["ゴールド Q（静観後のブレイク）", "約 3,507 円", "約 22 ドル（0.6%）"], ["ゴールド S（H4MA押し目）", "約 4,082 円", "約 26 ドル（0.7%）"], ["ゴールド DX（出入り口のリターンムーブ）", "約 5,064 円", "約 32 ドル（0.8%）"], ["ゴールド 右肩", "約 5,267 円", "約 33 ドル（0.8%）"], ["ゴールド P（MAクロス後の押し目）", "約 5,376 円", "約 34 ドル（0.9%）"], ["銀 DX（出入り口のリターンムーブ）", "約 2,029 円", "約 0.26 ドル"], ["銀 DR（押し安値・戻り高値の反発）", "約 3,451 円", "約 0.44 ドル"], ["銀 Q（静観後のブレイク）", "約 4,408 円", "約 0.56 ドル"], ["BTC Q（静観後のブレイク）", "約 1,255 円", "約 792 ドル（1.0%）"], ["BTC S（H4MA押し目）", "約 1,467 円", "約 926 ドル（1.2%）"], ["BTC DX（出入り口のリターンムーブ）", "約 1,859 円", "約 1,174 ドル（1.5%）"], ["BTC DR（押し安値・戻り高値の反発）", "約 2,352 円", "約 1,485 ドル（1.9%）"], ["日経 DX（出入り口のリターンムーブ）", "約 37 円", "約 371 円幅（0.6%）"], ["日経 DR（押し安値・戻り高値の反発）", "約 49 円", "約 493 円幅（0.8%）"], ["日経 右肩", "約 172 円", "約 1,721 円幅（2.7%）"], ["日経 IX（指数の H4 転換）", "約 218 円", "約 2,182 円幅（3.4%）"], ["US500 DR（押し安値・戻り高値の反発）", "約 531 円", "約 34 ポイント（0.4%）"], ["US500 P（MAクロス後の押し目）", "約 692 円", "約 44 ポイント（0.6%）"], ["US500 DX（出入り口のリターンムーブ）", "約 727 円", "約 46 ポイント（0.6%）"], ["US500 右肩", "約 2,383 円", "約 151 ポイント（2.0%）"], ["US500 M（短い押し目）", "約 3,175 円", "約 201 ポイント（2.6%）"], ["US500 IX（指数の H4 転換）", "約 3,502 円", "約 221 ポイント（2.9%）"], ["US100 DX（出入り口のリターンムーブ）", "約 2,806 円", "約 177 ポイント（0.6%）"], ["US100 P（MAクロス後の押し目）", "約 3,120 円", "約 197 ポイント（0.7%）"], ["US100 DR（押し安値・戻り高値の反発）", "約 4,704 円", "約 297 ポイント（1.0%）"], ["US100 IX（指数の H4 転換）", "約 1.3 万円", "約 851 ポイント（3.0%）"], ["US30 DX（出入り口のリターンムーブ）", "約 2,104 円", "約 133 ポイント（0.3%）"], ["US30 DR（押し安値・戻り高値の反発）", "約 3,114 円", "約 197 ポイント（0.4%）"], ["US30 T（トレンド）", "約 5,655 円", "約 357 ポイント（0.7%）"], ["US30 M（短い押し目）", "約 2.1 万円", "約 1,330 ポイント（2.5%）"], ["US30 IX（指数の H4 転換）", "約 2.1 万円", "約 1,338 ポイント（2.6%）"]];
  function minLotSection() {
    const rows = MINLOT_LOSS.map(([n, v, w]) => `<div style="padding:7px 0;border-bottom:1px solid #1e293b;font-size:12px"><div style="display:flex;justify-content:space-between;gap:10px"><span>${esc(n)}</span><b style="white-space:nowrap">${esc(v)}</b></div>
      <div style="font-size:10px;color:#64748b;margin-top:2px">損切り幅（真ん中）${esc(w)}</div></div>`).join('');
    return `<div class="ea-card" style="padding:8px 12px;margin-top:4px"><button onclick="eaLiveML()" style="width:100%;display:flex;justify-content:space-between;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:12px;padding:2px 0">
      <span>💴 最小ロットで 1 回負けた時の金額（目安）</span><span style="color:#94a3b8">${S.mlOpen ? '▲' : '▼'}</span></button>
      ${S.mlOpen ? `<div style="font-size:10px;color:#64748b;margin:6px 0 2px;line-height:1.5">損切りまで行った時の損失。損切り幅は過去のトレードの真ん中の値なので、これより大きい回も小さい回もある。最小ロットのリスク・1% のリスク・OFF を決める目安に。</div>${rows}
        <div style="font-size:10px;color:#94a3b8;margin-top:8px;line-height:1.6">前提：XM KIWAMI 口座の最小ロット（FX・ゴールド・銀・BTC 0.01、指数 0.1 ＝ 1 ポイントで 0.1 ドル）、2026-11-04 の値段、1 ドル 158.4 円（11/19 に全部の EA で計算し直し、損切り幅は 2023 年以降のトレードの真ん中）。実際の約定（BTC 0.01・UK100）と合うことを確認済み。金額が大きいのはロットではなく損切り幅が広いため。スタンダード・マイクロ口座や値段が変わると金額も変わる。<br>
        今の決まり：最小ロットでも損失が口座の「リスク」で選んだ % を超える回は自動で見送り（10 万円・1% なら 1,000 円まで、2% なら 2,000 円まで）。</div>` : ''}</div>`;
  }
  function featSection() {
    const rows = ALL_KEYS.slice().sort((a, b) => (MIN_ACC[a] - MIN_ACC[b]) || (BTX[b][7] - BTX[a][7])).map(k => {
      const x = BTX[k], weak = x[7] < 1.4;
      return `<div style="padding:8px 0;border-bottom:1px solid #1e293b">
        <div style="display:flex;justify-content:space-between;gap:8px;font-size:12px"><b>${esc(k)}</b><span style="color:#94a3b8;font-size:11px">${MIN_ACC[k]} 万円〜${weak ? ' · <span style="color:#f87171">外す候補</span>' : ''}</span></div>
        <div style="font-size:11px;color:#cbd5e1;margin-top:3px">${x[0]}〜${x[1]} · ${x[2]} 回（${x[3]} 勝 ${x[4]} 敗）· 勝率 ${x[5]}% · 平均 ${x[6]}R · PF ${x[7]} · 最大 DD ${x[8]}R · 年 +${x[10]}R</div>
        ${EA_DESC[k] ? `<div style="font-size:10px;color:#64748b;margin-top:3px;line-height:1.6">${esc(EA_DESC[k])}</div>` : ''}</div>`;
    }).join('');
    return `<div class="ea-card" style="padding:8px 12px;margin-top:4px"><button onclick="eaLiveFT()" style="width:100%;display:flex;justify-content:space-between;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:12px;padding:2px 0">
      <span>📘 EA の特徴</span><span style="color:#94a3b8">${S.ftOpen ? '▲' : '▼'}</span></button>
      ${S.ftOpen ? `<div style="font-size:10px;color:#64748b;margin:6px 0 2px;line-height:1.5">バックテスト（コスト込み・1 回 1R）。「◯万円〜」は最小ロットで 1 回負けても口座の 1% 以下になる額。</div>${rows}` : ''}</div>`;
  }
  function btSection() {
    return `<div class="ea-card" style="padding:8px 12px;margin-top:4px"><button onclick="eaLiveBT()" style="width:100%;display:flex;justify-content:space-between;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:12px;padding:2px 0">
      <span>📊 検証結果</span><span style="color:#94a3b8">${S.btOpen ? '▲' : '▼'}</span></button>
      ${S.btOpen ? comboTable() : ''}</div>`;
  }
  const MC_KEYS = ["C@EURUSD", "C@USDJPY", "CA@AUDJPY", "DB@AUDJPY", "DB@AUDUSD", "DB@EURJPY", "DB@EURUSD", "DB@GBPJPY", "DB@GBPUSD", "DC@AUDJPY", "DC@AUDUSD", "DC@EURJPY", "DC@EURUSD", "DC@GBPJPY", "DC@GBPUSD", "DL@EURUSD", "DL@USDJPY", "DS@JP225", "DS@US500", "DS@XAUUSD", "DW@AUDJPY", "DW@AUDUSD", "DW@EURJPY", "DW@EURUSD", "DW@GBPJPY", "DW@GBPUSD", "HL@EURUSD", "IX@JP225", "IX@US100", "IX@US30", "IX@US500", "J2@USDJPY", "M@US30", "M@US500", "P@EURUSD", "P@US100", "P@US500", "P@USDJPY", "P@XAUUSD", "Q@AUDJPY", "Q@BTCUSD", "Q@XAGUSD", "Q@XAUUSD", "S@BTCUSD", "S@XAUUSD", "T2@EURUSD", "T@US30"];
  // 2017-07..2026-10 の月ごとのトレード [EA の番号, R, ...]（決済順）
  const MC_MONTHS = [[38,0.6,45,-1.02,45,-1.12,17,-0.34,12,2.48,1,-1.02,45,2.65,45,1.83,28,1.8,46,-1.19,44,3.13,43,-1.02,46,1.62,45,1.25,46,1.71],[45,2.02,44,1.39,19,0.71,35,-1.04,36,-1.11,44,-1.02,36,-0.44,30,0.27,43,11.78,1,0.12,18,-0.99,38,0.68,17,2.16,45,3.12,38,-1.07,0,0.63,32,0.47,33,0.82,5,-1.04,45,-1.02,43,4.91,27,-0.15,45,8.56,46,-1.09,45,-1.06,17,-0.94,28,-1.04,45,6.94,43,-1.1,44,-1.04,44,-1.03,1,0.28,37,-0.37,32,0.51,33,0.54,1,-1.03,45,-1.06,44,-1.04,45,3.74,46,-1.19,46,-1.24,16,0.21,37,0.74,37,1.34,1,0.29,34,4.55,26,3.15,43,4.46,40,0.76],[2,-1.02,35,0.37,40,-1.17,1,0.76,43,-1.05,41,-0.39,44,0.36,19,0.14,32,0.69,36,1.53,35,-1.11,35,-1.14,36,0.59,35,-1.05,33,0.23,31,5.43,40,0.55],[31,0.87,18,1.5,36,4.64,36,5.31,43,2.21,43,-1.08,41,-0.0,43,7.48,44,-1.01,39,-1.05,43,1.78,35,-1.08,31,2.93,36,0.48,43,-1.06,36,-1.1,31,-0.05,43,-1.02,43,-1.09],[42,-1.03,28,1.5,36,-0.23,36,-0.34,7,-1.05,46,-1.14,18,-0.31,43,9.42,40,6.77,43,-1.03,36,-1.13,35,0.74,22,-0.31,43,-0.64,42,0.06,26,-1.09,44,-1.06,42,-1.03,45,4.8,1,-0.65,32,0.01,33,0.46,43,-1.03,46,-1.14,38,-1.03,44,-0.67,25,0.29,40,-1.04,41,-1.07,35,0.84,44,-0.03,38,0.23,44,-1.02,42,-1.03,46,1.57,43,2.58,38,-1.03,43,-1.01,31,-1.05],[18,1.81,36,2.08,46,2.21,0,-1.02,17,-0.49,43,4.93,40,8.05,17,-1.01,0,-1.05,36,0.35,2,0.96,42,-1.03,2,-1.05,22,-1.03,43,1.3,34,-1.02,31,-1.08,28,0.56,45,1.21,1,-1.06,16,-1.06,2,2.07,39,8.0,36,-1.15],[44,12.8,19,3.89,40,-1.02,40,-0.82,2,-1.04,7,-1.05,36,1.66,40,-1.02,0,3.55,26,10.6,44,-1.02,44,-1.02,27,1.17,44,4.22,0,2.53,26,7.75,44,-1.03],[38,-1.06,45,-1.03,44,-1.01,32,-1.01,33,-1.02,17,3.17,40,4.58,16,0.55,2,0.7,2,-1.03,40,-1.03,45,1.54,40,3.79,0,1.83,44,-1.03,43,2.6,40,0.87,43,-1.03,40,-1.01,1,-0.62],[2,1.68,42,-0.02,41,-1.08,40,0.2,43,1.68,40,-1.04,32,0.27,42,0.68,19,1.35,37,-1.06,36,4.51,36,-1.04,44,-1.07,40,1.21,44,-1.04,42,1.04,17,-0.39,42,-1.03,18,-0.23,29,-0.65,30,-0.5,27,-1.05,40,-1.02,33,-1.03,37,1.27,2,-1.02,37,-1.02,0,0.38,26,0.21,32,0.08],[40,1.28,31,-1.08,19,-0.96,31,-1.06,40,-1.05,34,-1.02,44,-1.03,26,1.26,34,-1.04,43,-1.04,40,7.27,1,-1.03,31,4.76,43,3.55,40,6.04,31,0.92,32,0.29,33,0.36,31,0.65],[31,0.4,41,1.36,42,1.1,17,-0.4,32,0.48,43,3.22,39,1.27,43,-1.07,35,0.93,16,3.14,40,-0.07,35,-1.16,17,1.23,27,0.93,45,1.75,45,1.65,41,-1.1,33,0.45,42,-1.03],[1,0.55,40,-1.06,32,0.3,6,1.81,0,-1.02,41,-1.07,35,0.41,27,0.41,45,-1.12,42,-1.04,26,-1.03,45,-1.06,18,1.08,37,0.16,0,-1.02,40,1.09,2,1.44,38,-1.03,31,-1.06,2,2.81,1,-1.03,45,-1.03,41,-1.09,37,-1.05,32,-1.03,38,1.11,38,0.66,3,5.04,18,-0.62,17,-0.42,45,-1.01,40,3.84,33,-1.06,34,-1.01,17,0.65,29,-0.71,40,1.55,33,0.2],[26,1.04,41,-1.09,26,0.36,17,1.0,2,-1.04,19,-0.16,38,1.57,38,2.26,40,-1.09,41,-1.12,40,5.24,31,-1.07,31,0.83,42,3.14,41,3.54,43,-1.16,27,0.76,35,-0.12,43,1.1,19,0.45,43,-1.06,23,-1.06,35,-1.06,18,1.38,36,1.54,36,1.39,34,-1.03,43,-1.07,38,0.11],[17,-0.62,38,0.21,0,2.58,36,1.68,16,-1.02,1,-0.78,26,26.13,32,0.63,33,0.26,9,-1.03,23,-1.09,36,-1.07,36,-1.07,38,-1.05,38,-1.06,31,-1.09,46,2.05,46,2.51,31,-1.05,19,3.97,35,7.38,17,1.69,43,3.79,40,3.04],[44,-1.03,30,1.01,28,1.08,43,-1.15,40,-0.19,19,-1.03,2,-1.04,29,-1.13,32,0.22,33,0.18,37,-1.05,40,-1.06,37,1.08,46,2.9,44,-1.03,21,1.12,43,-1.2,29,0.71,0,-0.78,35,-0.5,35,0.45,42,3.98,38,3.12,38,4.98,43,1.46],[46,0.55,0,1.72,43,-1.12,36,-1.06,36,-1.09,43,-1.07,31,1.98,31,-1.07,31,-1.05,40,-1.22,33,-1.07,38,-1.04,38,-1.03,28,-0.26,29,0.13,32,0.44,25,1.23,16,0.76,44,-1.02,0,1.74,18,-0.56,31,1.2,17,-0.74,21,-1.1,40,-1.24,40,-1.13,44,1.15,42,0.38,35,-0.27,27,0.11,35,-1.01,3,-1.04,40,-1.1],[41,-1.06,37,-1.03,17,-0.41,40,0.21,42,-1.03,19,-1.02,37,-0.36,40,0.99,43,-1.08,18,-0.31,31,-1.07,34,1.14,31,-1.08,2,-0.39,28,-1.06,35,1.51,17,-0.42,40,75.29,36,-1.0,35,-1.0,42,1.67,36,-1.0,46,-1.0,39,0.99],[28,1.75,34,-0.36,8,-0.69,29,-1.17,30,-1.12,22,-1.07,44,1.25,42,2.44,19,2.34,8,5.38,44,-1.03,1,0.27,31,0.36,30,-0.79,31,-1.12,34,-1.03,42,0.23,34,-1.02,16,1.83,35,0.68,35,0.04,36,2.05,36,1.21,41,-0.2,44,-1.02,43,1.43,17,2.0,40,-1.02,2,1.17],[44,2.79,19,1.18,36,-1.06,46,-1.02,27,-0.04,40,-1.04,43,-1.12,40,0.75,40,-1.02,41,-1.06,44,-1.02,38,-1.04,0,2.05,4,-1.08,42,1.94,41,1.08,40,-0.03,31,-1.07,40,-1.1,17,-0.57,31,-1.06,31,-1.06,40,1.61,41,4.31],[17,-0.97,38,1.0,38,1.07,44,3.82,42,6.68,40,-1.09,18,1.71,44,-1.05,31,-1.1,28,0.96,40,-1.1,31,-1.09,17,1.11,38,-1.05,41,-1.09,42,-1.03,16,3.52,0,4.0,41,-1.12,43,-1.06,31,6.46,46,-1.02,35,-1.05,35,-0.37,44,3.96,38,4.05,38,1.72,46,1.36,40,-1.29,29,1.43,30,1.44,0,-1.03],[2,-1.03,46,5.16,46,-1.03,0,2.62,32,-0.05,33,0.56,1,-1.04,46,-1.05,40,-1.12,19,0.08,35,0.73,31,-1.08,1,-1.09,40,2.54,8,-1.07,46,0.51,29,-0.25,1,0.81,44,2.13,8,-1.02],[17,-0.7,41,3.06,43,5.18,16,-1.1,35,0.7,35,0.87,1,0.48,36,0.78,18,-0.46,30,0.66,43,2.07,19,-1.03,26,0.27,17,1.27,42,-1.03,43,-1.14,43,6.07,43,-1.04,36,2.82,15,1.75,43,-1.11,37,-1.04,37,-1.09,41,-0.2,17,-0.75,27,0.67,34,1.37,34,2.25,42,-1.04],[5,4.76,44,-1.04,37,-0.34,28,0.56,18,-0.54,45,-1.11,40,3.18,43,-1.09,41,-1.09,26,-1.04,2,0.87,17,1.52,19,0.29,38,-1.09,23,-0.42,44,3.77,2,1.47,0,-0.98,32,-0.23,33,-0.27,43,22.87,29,0.21,9,0.1,4,-1.07,9,-0.27,31,2.22,42,-1.03,43,-1.05,4,-1.04,41,-1.11,30,-1.13,43,-1.09,1,-1.04,43,-0.46,0,0.74],[43,-1.1,33,-0.03,30,2.62,29,1.0,17,0.44,2,1.56,1,-1.03,44,-0.54,43,-1.03,40,5.25,2,1.99,43,-1.03,41,0.23,39,3.33,2,-1.06,44,9.06,38,13.23,28,0.96,43,10.26,40,14.62,1,-1.02],[26,-1.05,44,-1.03,19,-1.02,38,-1.04,43,-1.02,2,-1.12,27,0.65,44,-1.02,31,3.99,39,0.72,43,2.8,2,-1.06,26,-1.08,44,-1.03,46,1.16,38,-0.28,38,-0.28,33,0.34,35,0.37,35,0.39,46,-1.03,46,-1.04,2,1.31,42,-1.02,36,0.72,44,-1.02,39,0.48,46,-1.12,40,0.19,38,-0.24,46,-1.05],[18,-0.57,32,-1.05,33,-1.05,40,6.62,17,1.29,43,-1.05,43,-1.05,38,3.7,38,1.5,27,-0.01,32,1.04,40,-1.04,0,-1.05,43,-1.1,44,0.82,17,-0.44,40,7.6,44,-1.01,0,1.01,41,-1.06,42,-1.03,37,-1.02,44,-1.04,0,0.42,42,-0.59,19,-1.02],[38,0.07,38,-1.01,43,-1.09,40,-1.07,35,-1.09,40,0.27,26,-0.75,35,0.96,19,-1.02,36,1.18,31,-1.06,31,-1.08,43,-1.04,31,0.59,5,-0.25,1,0.71,34,0.47,34,0.81,41,3.23,30,0.36,42,-0.41,44,-1.02,32,0.08,40,13.75],[33,-0.13,45,1.72,34,0.75,42,2.4,45,-1.03,1,0.18,37,0.24,32,0.66,33,0.72,5,-1.03,44,-1.02,43,-1.06,26,0.62,20,6.73,27,1.61,40,-1.09,42,-1.02,42,-0.25,19,-1.02,38,-0.21,44,-1.04,35,3.2,43,-1.03,43,-1.03,23,-1.15,23,-1.07],[38,-1.03,38,-1.03,35,1.43,43,0.71,43,-1.08,44,-1.01,37,0.19,31,-1.05,9,-0.63,9,-1.09,42,3.55,41,-1.05,37,-1.02,2,1.62,17,0.55,25,-1.16,40,-0.15,2,-1.08,42,-1.02,19,-1.03,42,-1.02,41,-1.06,35,-1.03,25,5.05,36,0.27,30,1.04,42,-1.02,28,1.19,40,1.12,40,0.96,2,-0.78,35,0.63,1,2.25],[41,-1.09,42,-1.03,46,-1.17,35,-1.13,46,-1.29,29,0.66,42,-1.02,41,-1.05,42,1.31,41,-1.05,17,-0.5,33,0.05,32,0.4,43,-1.06,46,-1.06,35,-1.05,46,-1.03,35,-1.12,36,-1.05,1,0.46,37,-1.06,37,-1.11,38,-0.26,46,12.18,36,0.98,46,1.38,2,-1.06,31,1.11,42,-1.05,40,3.03,35,1.77,37,-1.08,38,-0.48,40,3.01,18,1.37,36,0.98,31,-1.08,43,-1.04,17,-0.27,40,-1.04,2,1.7,31,-1.12,41,4.79,40,-1.05],[7,-1.05,40,-0.27,18,-1.02,42,19.67,19,6.97,38,21.19,44,-1.02,43,0.23,3,-1.08,46,-1.02,46,-1.12,36,-1.04,34,-1.05,22,5.5,43,-1.06,40,2.2,46,2.27,43,-1.11,31,0.84,31,-1.12,42,-1.02,40,-1.04,40,1.14,38,3.38,17,2.45,43,1.63,1,-1.05,27,-1.07,2,0.75,32,-0.18,33,0.66,44,0.36,19,0.2,35,-1.03,30,-1.01],[38,-1.04,44,-1.03,2,-1.03,35,-1.11,36,-1.08,43,0.85,41,0.31,43,-1.15,35,1.14,43,-1.05,41,3.55,21,3.89,24,0.07,2,-1.03,37,5.56,27,-1.04,31,-1.04,44,3.63,42,13.27,38,19.14,32,-1.01,33,-1.01,22,-1.05,17,1.98,33,-1.01],[2,2.92,1,0.33,25,5.7,38,2.59,40,1.0,17,2.05,25,-1.02,46,1.6,46,1.79,35,1.45,29,-1.0,2,1.54,27,-0.37,35,-1.0,29,0.36,43,-1.04,30,0.06,28,-0.17,20,-0.67,43,-1.04,43,-1.21,44,-1.01],[6,-1.02,43,-1.02,0,1.23,43,2.11,31,-1.07,43,-1.04,16,-1.05,43,-1.04,41,-0.04,35,-0.08,40,0.35,42,4.66,38,7.92,43,-1.05,40,-1.06,42,-1.01,22,1.03,44,-1.01,1,1.2,42,-1.01,43,6.07,40,5.93,5,1.57],[43,-1.04,43,0.74,2,0.74,39,-1.03,1,0.59,46,-1.09,38,-1.05,43,-1.17,40,1.37,41,0.84,42,-1.02,41,-1.05,29,-0.73,20,-1.03,34,-1.04,44,2.84,42,1.46,38,2.55,43,-1.08,43,-1.06,41,6.46,42,-1.01,19,-1.01,31,-0.59,46,7.07,42,1.0,31,-0.26,40,-1.05,18,1.42,42,0.18,17,1.31],[43,6.36,41,2.24,42,-1.02,38,0.0,31,-1.06,40,-1.05,2,1.41,43,-1.08,43,-1.12,41,-1.04,42,-1.02,45,-0.28,43,-1.3,45,-0.86,18,-0.63,17,-0.45,45,-1.04,20,-1.02,33,0.69,45,1.53,42,-1.02,41,-1.05,46,-1.03,40,-0.17,46,-1.12,18,-0.29,36,-1.06,41,0.62,0,0.1,40,-1.09,42,3.18,38,0.53,35,-1.02,17,-0.37,38,-1.03,45,-1.02,45,-1.02,41,-1.04,26,0.35],[40,-1.16,42,-1.02,44,-1.01,41,-0.53,40,-1.14,35,1.37,40,-1.08,26,1.21,41,-1.04,38,-1.05,45,-1.03,34,-1.03,28,0.85,44,3.4,45,-1.03,40,-1.07,22,-1.03,1,1.79,22,-1.07,37,-1.03,42,-1.02,45,1.9,45,1.89,34,4.61,34,1.18,38,-1.08,6,4.55,40,0.31,42,-1.03,1,-1.05,18,1.1,36,0.73,37,-1.04,37,-1.04,0,1.07,30,0.62,37,4.61,44,21.77,42,13.44,38,2.84,38,2.61,43,41.65,40,8.26,39,-1.06,35,-1.05,24,2.22],[17,1.8,10,-1.05,2,1.03,39,0.22,45,-1.03,44,4.29,1,-1.03,43,1.24,31,-1.05,11,4.94,31,-0.37,45,-1.11,45,1.8,39,-1.05,35,0.51,43,-0.3,39,-1.05,2,-0.91,36,-1.09,32,0.23,40,-0.68,46,1.68,40,1.02,16,-1.02],[45,1.53,37,-1.03,0,0.22,34,0.61,41,-0.47,17,-0.86,45,-1.02,17,1.19,11,-0.34,46,-0.38,42,-1.02,4,0.96,41,-0.36,41,-0.35,17,-0.37,40,-1.12,33,0.24,40,0.93,41,0.49,42,0.33,38,-1.25,46,1.22,46,-1.06,41,-1.02,20,-0.76,40,-1.05,43,-0.39,40,-1.07,0,-1.02,29,-1.03,37,3.9,20,4.54,25,-0.16,42,5.09,41,12.83,40,-1.05,32,-0.01,33,0.04,43,-1.13],[40,-1.08,0,1.4,31,-1.05,17,-0.37,25,2.36,35,-0.43,42,-1.01,36,-1.02,36,-0.26,40,-1.11,43,2.03,38,-1.11,29,1.85,30,1.91,38,-1.03,20,-1.05,28,1.2,19,-0.28,41,-1.03,41,-1.06,41,-1.04,1,-1.04,42,-1.02,34,1.74,38,-1.03,32,0.06,33,0.08,44,-1.03,43,5.95,40,9.9,43,0.47,40,-0.2,26,-1.07,1,-1.04,43,-1.19,8,0.19,17,-0.52,43,-1.18,18,-0.45,32,-1.02,42,1.3,43,-1.06,41,2.49,37,0.24,33,-1.02],[17,-0.5,43,-1.07,32,0.41,33,0.2,7,-1.02,41,-1.04,28,1.71,43,4.25,37,1.34,0,2.83,2,2.25,30,1.2,29,2.11,2,-1.04,17,1.25,27,1.67,43,1.9,34,0.24,26,0.67,43,-1.03,1,4.24,2,1.39,43,1.11,41,2.11,43,-1.07,35,0.78,1,0.49,39,-1.07],[43,-1.1,41,-1.04,0,5.43,34,7.13,26,20.38,44,-1.03,43,-1.09,37,-1.03,2,2.09,39,4.85,44,-1.01,46,-1.12,46,-1.3,40,-1.06,33,0.41,46,1.47,43,17.38,40,4.82,42,2.43,35,2.84,36,-1.05,43,0.32,44,0.78,38,-1.02,38,-0.2,35,-1.1,12,-0.05,43,-1.03,43,5.14,38,-1.04,43,-1.03,45,1.88,18,1.28,38,-1.25,16,1.14,43,2.39,41,-1.04],[39,2.26,43,-1.03,40,2.24,1,0.89,44,2.13,42,5.46,38,5.38,0,-1.02,36,1.05,43,-1.05,41,6.78,35,-1.02,13,1.97,32,0.16,33,0.33,26,0.04,36,-1.04,44,-1.01,1,-1.06,19,-1.01,35,-1.07,28,0.11,41,-0.86,42,-1.02,27,-1.01,43,-1.03,43,-1.03],[17,0.82,33,0.22,8,-0.46,32,0.48,8,-1.04,38,2.0,43,5.33,40,2.44,43,-1.03,35,0.99,39,3.28,41,-1.03,43,-1.03,43,-1.04,43,0.75,40,-1.04,43,-1.08,19,-1.01,34,-0.2,34,-0.31,39,3.77,27,1.49,43,1.37,40,0.53,38,1.53,43,2.36,40,2.35,43,-1.05,40,-1.03,33,0.22,17,-0.35,36,-1.02,4,7.99,28,-1.08,37,0.2,6,-1.04,30,-0.29],[37,1.31,38,1.15,40,0.05,41,-0.23,1,2.51,17,0.58,43,1.38,40,0.58,31,-1.06,43,-1.05,31,-1.08,31,-1.05,43,1.61,43,-1.05,31,0.79,44,-1.04,42,-1.02,44,-1.02,19,1.25,41,-1.05,44,-1.01,43,-1.03,1,-1.03,43,-1.06,40,-0.43,33,0.22,29,0.82,17,-0.27,40,0.67,37,1.53],[10,0.6,40,-1.08,43,-1.06,45,0.09,40,-1.05,2,-1.04,39,-1.03,43,-1.07,40,-1.03,42,-0.03,40,0.92,5,-1.04,41,-0.42,42,-1.02,44,-1.04,44,-1.03,43,4.22,40,3.53,28,1.75,44,5.61,30,0.99,41,-1.05,42,-0.63,44,-1.04,42,-1.02,46,-1.12,35,-0.24,42,-0.19,36,0.27,36,0.15,2,0.66,31,0.67,39,-1.04],[43,-1.1,43,-1.08,2,-1.05,31,1.4,19,-1.02,1,-0.12,31,-1.08,40,-1.03,43,-1.13,36,-1.02,36,-1.02,44,3.49,42,2.96,27,-1.09,30,-1.04,45,-1.01,34,-1.01,32,0.87,33,1.01,28,-0.24,0,1.84,20,-1.04,26,-1.03,45,-1.04,17,-0.41,2,1.7,1,5.47,15,1.09],[39,-1.08,0,0.6,42,-1.03,41,-0.32,31,-1.06,31,2.44,2,-1.06,40,0.68,42,2.26,36,-0.34,35,0.23,42,-1.03,39,-1.05,44,-1.01,1,-1.06,35,0.98,36,0.36,36,-0.22,37,0.87,32,-1.05,29,-1.12,40,1.03,40,-1.03,31,-1.06,32,0.74,33,0.16,16,0.63,37,0.52,6,4.73,36,0.81],[43,-1.06,0,1.07,15,-1.04,43,-1.06,40,-1.03,44,-1.03,42,0.77,17,-0.7,30,0.54,44,-1.02,27,-0.61,40,0.98,44,-1.03,40,-1.03,44,-1.02,35,0.47,26,1.9,23,-0.3,41,-1.05,23,-1.13,45,-1.02,24,-0.48,23,-0.06,44,1.43,36,-1.13,27,-1.03,24,4.09,40,1.96,41,5.46,32,0.82,33,0.39,40,-1.04,45,-1.06,45,-1.06,34,-1.06,43,3.71,40,2.02,17,-0.32,42,-1.02,36,0.78,41,1.16,22,-1.04,43,1.34,24,-0.03,38,-1.03],[43,-1.05,38,-1.02,19,-0.55,44,-1.02,35,0.86,43,2.33,36,-1.12,38,1.62,46,1.78,43,1.0,35,-1.06,2,3.24,38,-1.01,27,-1.05,42,1.57,26,2.16,39,6.08,33,0.49,43,-1.06,32,0.55,43,-1.06,36,-1.09,37,-0.46,40,-1.05,43,-1.1,43,-1.14,36,0.87,1,-1.05,44,1.79],[44,-1.04,8,-1.03,44,-1.03,35,1.04,44,2.06,38,-1.03,43,0.53,40,0.24,42,-1.02,38,-1.02,30,0.67,28,1.19,31,2.61,38,-0.75,32,0.01,42,-1.03,17,3.0,27,2.63,33,-0.15,8,-1.04,28,-1.01,40,-1.11,43,-1.11,41,5.61,34,0.58,26,1.86,2,1.05,40,4.15,38,-1.01,38,-1.02,32,0.34,17,-0.44,33,0.8,38,-0.04,27,-1.02,38,0.62,1,0.94],[29,-1.06,43,-1.15,43,-1.06,40,-1.05,43,-1.04,32,0.35,33,0.2,44,-1.01,19,-1.01,42,-1.02,38,-1.12,43,1.77,43,0.89,0,-0.71,31,8.3,45,-1.07,2,1.55,43,1.85,43,-1.05,35,1.76,35,2.88,36,1.07,43,1.13,17,-0.33,23,-1.09,44,0.92,42,-0.76,23,-1.11,44,-1.02,40,-1.07],[41,-0.26,28,2.31,30,1.79,3,23.05,43,-1.09,37,-1.06,43,-1.05,34,-0.3,34,-0.34,40,-1.06,27,0.63,18,2.37,43,-1.07,43,-1.04,40,-1.07,31,-1.05,43,-1.07,16,-1.03,46,-1.11,38,2.06,46,0.9,45,1.87,45,2.43,31,3.65,35,1.55,27,0.21,42,-1.02,17,-0.46,44,-1.01,18,-0.42,32,0.21,31,1.08,37,0.91,1,0.4,46,-1.07,36,-1.06,45,-1.02,2,7.49,39,2.42,35,-1.04,35,-1.05],[22,-0.29,9,2.77,32,-0.08,33,-0.06,45,-1.05,22,0.14,45,2.42,27,0.6,0,0.22,1,0.21,38,-0.31,41,0.46,45,1.27,35,-1.03,45,-1.04,41,0.93,38,-0.2,38,-0.37,1,1.3,36,-1.02,22,-1.05,28,-1.07,38,-1.04,45,-1.03,32,0.5,41,1.9,43,4.16,1,0.1,40,0.2,43,-1.11,45,-1.09,45,1.53,38,0.1,38,-0.08,42,-1.03,44,-1.03],[38,-1.04,9,5.47,29,0.67,30,0.43,17,-0.62,19,-1.01,21,-0.62,26,-1.04,40,4.86,28,-1.04,40,-1.04,33,0.04,17,-0.11,0,-1.02,32,0.23,15,1.71,44,-1.03,17,-0.41,42,-1.03,40,0.05,27,-1.03,2,-1.04,44,-1.04,38,1.11,32,-1.04,33,-1.03,17,1.01,19,0.04,34,1.83,34,0.02,38,-1.02,30,-0.38,28,-0.47,2,0.89,27,0.4],[43,-1.06,42,-1.02,42,0.17,41,-1.08,36,-1.02,36,0.28,18,-0.21,43,-1.08,17,-0.31,44,1.05,38,-0.19,43,-1.12,1,-1.04,2,-1.02,19,2.23,36,0.69,1,-1.04,29,-1.12,35,2.99,36,4.45,44,-0.6,17,2.78,17,1.28,0,2.61,1,-1.02,37,-1.03],[17,-0.48,43,-1.03,45,2.89,1,-1.04,37,-1.03,45,2.7,27,-1.02,18,-0.37,44,5.41,40,-1.04,35,3.61,35,1.84,36,0.48,36,1.12,44,0.38,5,4.26,19,-1.01,45,-1.02,36,-1.01,37,6.01,26,-1.03,0,-1.01,1,8.87,40,-1.13,34,-1.03,43,1.54,41,0.89,31,3.92,2,1.21,45,-0.38,45,-1.07,27,1.8,43,11.63,40,4.26,41,-0.79,43,-1.07,31,-1.03,41,-1.05,43,-1.08],[40,0.31,43,-1.1,41,-1.04,40,-1.05,18,0.29,6,-1.05,40,1.94,22,2.56,44,-1.02,42,2.89,31,2.16,45,1.12,40,-0.53,44,-1.03,22,7.84,6,0.72,19,-0.42,40,-1.04,42,-1.02,30,-1.02,29,-0.33,17,-0.53,27,-1.03,41,4.26,36,2.0,34,4.56],[40,0.1,40,-1.05,41,-1.04,31,-1.01,28,-0.71,31,0.95,17,-0.45,29,-1.02,31,-1.03,1,-1.02,40,3.51,41,0.91,0,2.32,42,0.43,30,-1.01,28,-1.01,17,-0.76,15,-1.02,40,-1.06,46,-1.0,35,-1.03,44,-1.02,46,-1.0],[43,-1.04,29,0.54,2,1.47,0,-1.01,38,-1.02,40,-1.07,24,2.75,0,0.32,42,-1.02,30,0.62,1,12.67,26,0.48,19,1.06,27,1.69,38,-1.03,23,4.99,31,-1.02,6,-1.03,38,-1.02,41,-1.07,41,-1.05,40,-1.03,38,-1.05,0,-1.02,43,-1.07,42,-1.03,1,2.24,42,-1.02,0,1.69],[17,-0.43,40,0.29,34,1.81,42,6.2,38,0.66,37,-1.08,42,-1.03,40,0.66,43,-1.07,30,-0.19,18,-0.56,43,-1.05,40,-1.07,43,1.35,3,-1.03,42,-1.03,40,-1.03,0,-1.02,43,-1.08,44,-1.03,39,-1.03],[18,1.88,27,0.86,28,1.57,44,3.01,46,-1.02,46,-1.02,1,-0.22,42,-0.19,40,-1.04,40,-1.1,40,0.46,17,-1.02,2,1.35,29,1.7,40,-0.41,40,-1.07,39,0.29,44,-0.6,19,-0.61,17,1.54,6,-1.06,24,-1.01,23,3.98,43,-1.17,40,-1.07,42,1.14,31,-1.04,1,-1.03,40,7.2,41,3.85,0,3.11,39,-1.04,28,-1.02,46,1.91,2,-1.02,0,-1.02],[36,0.64,38,0.85,40,-1.11,40,-1.06,31,12.11,17,1.12,19,2.66,43,3.01,29,-1.06,31,-0.06,27,-0.9,42,3.0,38,2.04,38,2.55,1,0.2,1,-1.01,35,1.47,35,1.77,37,-1.03,17,1.23,34,1.69,29,-0.49,30,-0.62],[40,-1.07,37,-1.05,29,0.32,30,0.27,27,0.25,44,-1.03,46,2.21,46,3.25,40,-1.07,28,-1.02,40,0.08,43,-1.26,44,-1.02,35,0.22,40,-0.71,40,0.05,15,0.68,40,-1.05,15,-1.01,0,-1.01,19,-1.02,43,7.76,40,2.63,42,-1.01,43,-1.07],[38,-1.03,29,1.86,38,-1.03,28,-1.02,38,-1.03,0,1.64,17,-1.01,43,-1.14,42,1.15,44,3.89,17,1.21,17,-0.35,46,-1.1,45,-1.06,45,-1.07,44,-1.01,40,-1.09,46,0.74,42,-1.02,44,-1.02,42,-1.04,43,-1.21,40,-1.05,25,1.05,42,-1.02,1,-0.81],[44,3.73,7,-1.02,44,-1.03,0,0.61,19,-1.01,14,-1.01,40,-1.06,17,-0.27,27,-0.33,40,-1.29,40,-1.22,38,-0.33,38,-1.05,24,-1.04,40,-1.06,32,0.27,45,-1.12,1,0.31,26,4.67,40,-1.05,43,1.94,38,-1.03,38,-1.02,19,0.45,40,-1.15,36,0.88,35,0.78,35,0.5,32,0.35,44,-1.03,40,-1.1,29,-0.11,45,-0.18,45,-0.3,40,-1.22,40,-0.73,28,-0.82,19,0.53,17,-1.01,44,-1.05,42,-1.01,40,0.61],[39,-1.04,40,0.53,44,2.67,19,1.53,30,-0.51,2,1.85,1,-1.01,35,-1.04,35,-1.2,0,-1.02,36,-0.27,27,0.17,2,-1.01,41,-1.04,43,5.11,40,7.1,44,-1.03,34,-0.15,43,2.39,44,-1.05,42,-1.02,17,-0.22,1,3.28,44,-1.02,43,0.55,45,0.82,45,-1.04,43,-1.06,44,-1.02,43,-1.06,32,0.28,43,-1.13,8,0.4,0,-0.05,26,0.36,43,-1.13,43,-1.1,44,-1.03,36,0.46,36,0.74,43,-0.33,17,1.16,42,-0.9,41,-1.05],[38,-1.02,44,-1.01,37,-1.02,43,-1.12,18,1.42,40,0.16,16,-1.01,41,-1.06,24,2.57,43,2.23,40,-1.08,43,-1.08,41,-1.06,42,-0.44],[32,-0.21,33,-0.19,0,-1.03,40,-1.1,42,0.06,44,-1.04,0,0.0,17,1.42,3,-1.05,29,-1.05,30,-1.04,27,1.04,2,0.78,38,0.64,46,-1.03,46,-0.81,37,-0.33,43,4.58,31,3.27,43,-0.11,43,-1.05,40,-1.06,40,-1.1,26,1.11,19,1.13,26,-1.03],[41,0.73,40,-0.42,43,-1.15,18,1.83,38,4.0,1,2.07,21,1.1,2,-1.02,41,-1.04,40,3.29,43,-1.05,43,0.11,40,-0.58,36,-1.03,40,-1.11,40,0.44,26,-1.02,16,0.85,42,-0.68,29,1.01,26,0.22,18,-0.95,7,-1.01,1,0.37,11,0.44,32,0.63,33,0.48,0,-1.03,40,-1.05],[46,1.72,41,-0.78,46,-1.05,36,-1.04,29,-1.05,34,-1.02,19,-1.01,38,-1.02,32,0.58,33,0.59,43,-1.15,41,-1.07,7,11.52,44,-1.01,18,-0.44,36,-1.06,35,0.59,35,-1.04,36,-1.2,41,-1.05,40,-1.05,32,0.11,36,1.51,36,0.76,42,3.56,40,-1.07,35,5.32,28,1.56,42,-1.02,13,-0.14,13,-0.08,41,1.59,32,0.28,4,5.04,42,-1.04,41,-0.92,40,4.13,43,-1.07,45,-1.12,41,-1.04,36,-1.05],[43,-0.02,36,0.84,40,3.37,0,1.53,2,1.26,35,1.47,10,-0.04,2,-1.02,42,-1.03,1,2.3,19,-1.03,43,-1.09,18,-0.64,43,5.33,2,-1.02,41,6.58,43,-1.05,32,0.24,2,-1.02,43,-1.05,43,-1.07],[43,-1.25,43,-1.13,2,1.17,39,-1.04,30,0.57,44,-1.03,40,-1.18,32,0.44,33,0.35,40,-0.29,42,2.71,19,1.85,34,3.93,35,0.51,46,1.73,36,1.31,44,-1.03,40,-1.26,17,-0.52,38,0.13,38,-1.05,45,-1.03,29,0.87,17,-0.51,40,-1.1,40,-1.24,40,-1.22],[35,-0.11,36,-0.44,8,-1.02,1,0.41,42,0.03,8,-1.05,18,-0.59,27,-1.07,32,0.51,33,0.04,42,-0.29,39,0.09,24,2.55,40,-1.18,17,-0.48,27,-1.02,33,-0.1,0,-1.06,42,-1.03,2,-1.04,32,-0.54,39,-1.03,18,-0.37,40,-1.15,17,-1.01,1,-0.11,39,0.74,43,-1.08,42,1.41,19,0.71],[42,-1.03,38,0.09,39,-1.03,42,1.14,17,1.73,40,-1.12,8,7.12,32,0.21,33,0.13,44,-1.01,21,-1.05,35,-1.04,35,-1.02,21,-1.07,20,-1.07,43,-1.18,39,1.13,18,-0.85,27,0.61,16,-0.66,39,0.04,43,-1.39,42,-1.05,33,-1.05,45,2.68,0,0.85,32,-1.06,1,1.34],[43,3.51,40,0.71,17,1.35,43,-1.14,33,0.57,43,-1.19,43,-1.22,26,-1.03,18,-0.2,36,-1.04,40,9.67,45,-1.02,0,-1.03,44,7.0,17,1.31,43,12.41,20,-1.02,44,-1.04,43,-1.1,33,-1.05,46,2.61,43,-0.84,17,-0.5],[44,-1.02,43,-1.06,40,-1.07,44,-1.02,37,-1.01,40,-1.06,1,0.88,37,0.61,40,-1.12,37,1.12,2,3.44,5,7.3,2,-1.04,27,1.2,2,0.42,39,-1.07,44,2.61,42,1.03,19,1.26,43,1.01,35,-1.03,35,-1.05,29,1.81,43,-1.07,44,1.51,42,1.25,28,0.95],[42,-1.03,36,-1.2,26,-1.03,36,-1.03,31,0.66,44,-0.82,31,-1.03,43,14.63,40,11.44,36,-1.07,30,1.21,43,-1.05,31,13.24,35,-1.03,36,-1.05,43,-1.24,43,-1.28,31,0.92,42,-1.02,36,7.15,41,-1.06,40,-1.11,17,-0.43,19,1.32,31,0.09,28,2.02,45,-1.04,40,0.44,45,1.82,18,1.26,1,-1.02,44,2.23],[17,-0.21,17,-0.36,40,-1.06,43,-1.13,33,0.43,25,-1.05,43,1.26,42,-1.02,0,-1.03,43,-1.03,1,0.65,40,-1.12,17,3.17,26,1.99,32,0.24,33,0.34,19,-1.03,35,1.16,42,-1.03,31,-1.03,23,1.53,41,-1.06,39,-1.05,40,2.9,36,2.83,36,1.21,2,-1.05,17,-0.29],[31,0.93,21,-1.04,46,1.45,19,-1.03,43,4.91,40,-0.05,35,1.46,35,1.03,45,-1.05,18,1.19,34,1.01,37,1.32,37,1.6,43,3.24,43,-1.11,35,-1.05,45,-1.02,10,0.09,43,-1.07,42,0.21,42,-1.03,44,-1.04,39,2.96,2,-1.07,38,-1.07,44,-1.09,42,-1.03,2,-1.06,35,-1.13,38,-1.06,36,-1.08,7,3.03,41,-1.05],[37,-1.15,46,-0.36,46,-0.39,35,1.01,36,0.52,35,-1.03,43,1.96,40,15.88,1,-1.02,40,-0.5,28,0.27,32,0.18,38,11.53,44,-1.01,43,1.74,36,-1.05,36,2.24,19,-1.02,2,-1.04,43,-1.07,43,-1.03,27,0.33,43,-1.07,40,-1.09],[40,-1.23,43,-1.08,44,-0.4,38,5.77,34,0.39,40,1.75,0,2.63,26,2.13,17,1.22,33,0.46,40,1.33,40,-0.94,32,0.27,34,-1.08,44,1.92,17,-0.56,37,3.76,43,-1.04,40,1.29,44,-0.44,34,1.18,34,1.31,31,-1.05,31,-1.03,38,-1.05,32,-1.08,29,0.15,33,-0.33,44,-1.01,28,0.11,31,-0.16,40,0.39,43,-1.14,27,-0.16,40,0.55,45,1.02],[0,0.47,45,-1.04,40,-0.86,43,-1.06,40,-1.04,0,-1.03,42,0.76,38,-1.02,44,-1.04,41,2.2,1,1.48,44,0.82,19,0.95,2,-1.02,40,2.57,18,1.76,43,0.61,44,1.33,42,1.43,41,7.01,44,-1.02,43,7.08,43,-1.1,18,-1.01,30,0.79,43,-1.06,40,-1.13,2,0.79,32,-1.07,39,-1.04,17,0.82],[32,0.74,33,0.42,37,-1.08,45,6.37,2,-1.04,40,2.15,43,-1.08,45,-1.06,0,-1.03,40,-1.06,45,-1.03,43,-1.09,40,-1.24,34,-1.01,31,-1.04,40,-1.11,32,0.15,42,-1.01,42,-1.02,28,2.02,37,1.39,42,2.3,30,1.11,31,4.57,37,3.46,40,1.97,15,0.45,33,0.14,2,1.16,36,0.47,36,-0.55],[17,1.18,26,-1.03,42,0.95,41,-1.05,42,-1.04,35,2.25,18,2.42,36,0.87,36,1.57,27,1.86,44,6.19,42,2.54,19,1.96,38,1.55,43,-1.08,29,2.16,43,-1.07,41,-1.04,43,-1.06,33,0.36,0,-1.06,43,-1.06,40,-1.05,33,0.35,46,0.83],[0,-1.04,46,-1.06,30,-1.02,1,3.9,31,-1.01,32,-0.11,33,0.4,38,1.81,0,2.38,26,3.2,40,-1.1,43,-1.2,42,0.97,19,1.15,31,5.32,45,1.93,44,-0.49,42,-1.02,34,1.81,44,-1.01,43,1.03,45,2.03,28,0.7,42,-1.02,45,-1.05,19,-1.02,30,0.79,2,-0.39,31,-1.02,42,-1.02,38,-1.05],[40,-0.02,44,-1.02,36,-1.09,2,0.92,31,-0.48,39,-1.02,40,-1.06,0,-1.02,32,0.01,41,-1.05,33,-0.09,31,1.6,43,1.4,43,-1.11,44,2.8,42,4.38,19,3.65,2,-0.17,45,1.49,45,1.75,34,1.52,43,1.93,43,-1.32,34,-1.03,42,-1.02,38,0.54,40,-1.08,34,-1.02,43,-1.07,45,0.28,42,-1.03,45,-1.1,44,-0.6,45,3.39,27,0.41,40,0.84,43,-1.17,43,-1.29],[30,0.61,29,0.45,44,-1.03,42,-1.02,22,-0.18,36,-1.03,35,-1.02,40,-0.28,44,-1.03,44,-1.01,36,0.63,43,3.8,17,-0.26,42,-1.03,19,1.07,38,0.56,43,0.7,40,-0.88,22,-1.04,44,2.27,45,1.72,40,-0.55,22,1.21,43,-1.07,45,-1.12,32,-0.08,33,0.13,14,-0.05,14,-1.05,40,8.75,18,-0.59,42,1.02,30,-1.09,43,-1.11],[40,0.34,19,-1.02,17,-0.34,32,0.48,33,0.57,17,0.93,28,2.32,46,2.22,43,11.5,29,1.71,27,0.31,34,0.76,1,1.16,35,-1.1,34,1.02,20,-0.14,36,-1.14,20,-1.04,33,0.22,20,-1.05,41,-1.06,32,0.36,45,1.88,45,2.85,43,2.3,1,-1.02,46,1.86,17,-1.01,43,-1.07,40,-0.57],[43,-1.2,40,-1.08,2,-1.03,40,-1.18,17,-0.35,43,-1.1,31,-0.65,40,-1.04,46,0.2,35,5.89,35,1.25,44,-1.02,40,-1.09,43,-1.11,2,-0.8,38,2.15,38,2.33,43,-1.07,43,0.22,32,-1.08,43,4.07,40,2.65,15,1.45,41,3.88,42,1.31,29,-0.28,32,0.52,33,0.75,17,-0.41,41,-1.08,42,0.75,26,-1.04,40,-0.45,42,0.24],[41,1.52,32,0.17,33,0.2,19,-1.01,43,0.46,40,0.42,42,-1.02,1,0.43,17,-0.41,42,-1.03,18,-1.03,29,-1.04,30,-0.72,40,-1.11,40,-1.17,27,-1.06,28,-1.12,38,1.85,34,0.7,32,0.42,46,4.26,33,0.55,38,1.43,38,0.57,2,-1.02,42,1.67,44,-1.02,43,1.14,23,-0.06,43,-1.3,18,0.16,17,0.41,30,0.59,28,0.36,44,-1.02,40,2.85,2,1.1],[42,1.96,40,0.74,4,-1.06,19,2.17,36,-1.04,40,-1.07,40,-1.05,2,0.84,3,1.83,40,-1.08,34,-1.02,35,-1.13,40,-0.04,35,6.23,40,-1.1,36,0.24,36,-0.11,41,-1.04,27,-1.03,31,1.61,6,-1.05,33,-1.04,31,-1.04,44,-1.01,31,-1.02,17,1.43,40,13.36],[32,-0.4,11,-1.01,11,-0.57,2,-1.02,29,-1.01,3,-1.02,1,1.5,19,-1.01,40,4.88,17,0.7,42,-1.02,1,-1.01,30,-0.01,28,0.05,44,1.98,42,1.45,44,-1.02,31,-1.03,43,-1.15,27,0.15,18,-0.44,40,2.3],[31,-1.03,42,5.89,19,0.59,38,6.13,45,0.44,29,-1.01,45,6.07,24,1.69,20,6.58,40,3.27,15,0.52,45,-1.01,46,-1.0,37,-1.01,45,-1.1,45,1.46,37,0.75,38,1.27,43,-1.06,34,1.71,43,-1.08,40,-1.05,18,1.65,44,4.46,43,-1.14,40,-1.05,45,2.13,36,2.41,35,0.23,40,2.23,0,-1.03,40,-0.26,26,-0.22,40,-1.07],[44,-1.01,14,-1.05,43,1.53,40,0.36,43,-1.21,40,0.17,1,0.15,40,-1.08,25,-1.04,45,-1.06,44,-1.01,19,-1.01,43,-0.2,40,-1.1,43,-1.07,43,-1.15,42,1.24,40,-1.07,0,-1.02,43,-1.04,40,-0.93,43,-1.12,39,-1.05,2,0.97,43,3.38,33,0.33,31,1.71,42,-1.01,45,-1.07,21,-1.05,17,-0.38,34,-1.02,41,-0.68,43,-1.15,42,-1.02,41,-1.05,42,-1.02,41,-1.05,1,-1.02],[15,-1.02,42,1.13,19,-0.11,44,-1.02,38,-1.02,38,-1.02,40,-1.22,26,-0.5,43,-1.13,0,-1.04,41,6.32,43,-1.2,4,1.5,46,-1.16,40,-1.11,41,0.53,30,-1.03,28,-1.03,42,0.31,0,-1.03,0,-1.03,40,-0.12,24,1.55,45,8.12,35,1.35,42,1.07,17,1.67,27,2.62,43,-1.06],[43,-1.13,40,-1.14,41,-0.64,42,-1.02,40,0.6,43,-1.2,40,-1.34,41,-1.05,19,-1.01,29,2.11,36,1.74,36,4.55,30,0.96,42,-1.02,40,-1.09,42,-1.01,43,10.31,42,0.39,40,-0.43,46,-1.12,35,-1.05,43,-1.07,43,-1.16,39,-1.03,43,-1.2,17,-0.38,17,-0.32,38,3.8,41,1.74,1,1.24,31,-0.08,18,1.21,36,0.86,39,-1.05,40,-1.18,46,-1.14,35,0.35,35,0.58,28,1.59,46,-1.14],[41,5.67,32,0.11,33,0.71,41,1.07,31,-1.02,46,-1.03,37,-1.15,37,-1.08,46,-1.05,41,-0.69,31,0.09,42,-0.4,40,-1.09,31,-1.04,43,6.04,34,-1.02,43,0.63,43,-1.13,20,-1.07,42,-1.02,20,7.35,42,-1.03,33,0.39,34,-1.02,0,0.12],[37,-1.02,34,1.12,37,-1.03,18,-0.4,36,-1.16,39,0.11,44,7.78,42,4.31,32,0.34,17,-0.32,39,-1.05,36,-1.02,43,-1.15,44,4.49,43,-1.17,34,-1.02,34,-1.02,39,2.27,22,-0.01,40,-1.08,27,2.21,16,-1.01,15,1.34,44,-1.02,19,-1.03,0,2.35,37,5.05,37,0.47,22,5.5,43,1.11,8,-1.04,46,0.73,40,4.87,0,-1.03,44,1.99,28,1.48,37,1.19,32,0.25,46,1.33,46,-1.09],[35,-1.35,5,-1.03,35,-1.08,17,-1.01,35,-1.03,36,1.37,26,-1.03,46,-1.11,43,1.74,2,1.51,44,-1.02,35,-1.05,32,-1.03,33,0.93,35,-1.2,44,6.47,19,5.82,40,-1.14,44,-1.01,35,-1.04,2,1.29,43,1.07,40,1.63,1,-1.01,0,0.4,43,-1.18,16,1.68],[1,1.83,46,-1.13,36,-1.12,40,6.15,42,-1.01,41,-1.04,32,0.09,33,0.23,17,-0.39,1,-1.03,20,-1.05,15,-1.05,16,0.77,45,1.6,45,1.99,41,1.56,20,1.13,1,-1.03,20,-0.39,18,-0.89,29,-1.04,16,1.32,1,2.6,32,-0.26,33,0.09,42,-1.01,41,1.27,25,0.19,42,-1.02,20,4.39,43,-1.16],[39,-1.05,40,3.7,44,1.17,38,1.4,0,0.18,34,0.36,44,-1.01,42,-1.01,34,1.01,42,-1.01,38,-1.25,40,-1.05,41,-0.45,44,-1.03,39,3.02,2,2.82,1,2.15,37,-1.02,37,-1.02,41,4.0,36,-1.04,39,-1.03,40,-0.45,29,0.83,44,1.61,38,5.82,38,-0.05,0,2.82,33,0.61,40,-1.14,2,2.94,26,-1.03,44,2.38,42,2.85,40,-1.09,36,1.26,40,-1.06,43,-1.08,37,-1.06,43,-1.13],[37,-0.09,1,-1.02,32,0.65,33,0.26,43,7.48,40,2.3,35,-0.44,36,-1.08,44,-1.01,35,-1.04,16,2.02,40,-1.14,39,2.68,44,-1.01,36,-1.08,37,0.6,1,4.79,18,-0.44,26,1.87,27,1.51,40,-1.17,46,-1.1,46,-1.55,16,-1.02,21,-1.09,30,-0.17,28,-0.36,40,2.02,42,4.23,32,0.39,21,5.34,33,0.17,21,5.48,5,-1.03,40,-0.19,34,2.74,34,4.63,44,14.28,28,0.39,31,-1.02],[36,-1.02,30,-1.07,4,9.2,1,1.54,33,0.62,17,1.5,38,-1.09,46,-1.06,42,0.31,33,0.15,15,0.49,20,-1.04,1,-1.02,20,-1.04,41,2.47,44,1.59,19,0.75,15,-1.04,20,4.5,26,0.23,37,0.46],[16,-1.02,18,-1.05,42,1.23,41,-1.02,17,0.43,43,1.17,28,-1.04,32,-1.04,2,2.53,41,-1.02,19,-1.01,0,2.04,41,0.29,32,0.11,33,0.11,43,2.32,40,2.52,3,0.24,22,-1.04,40,-1.04,36,2.07,41,3.36,42,11.82,40,-1.07,17,-0.41,40,-1.06,16,-1.02,46,-1.01,35,1.16],[41,-1.03,40,-1.12,40,0.6,43,-1.07,2,2.66,43,2.14,42,-1.01,39,4.31,40,-1.17,41,-1.02,44,-1.01,19,-1.01,37,-1.03,43,0.78,34,1.27,2,3.0,41,1.02,43,-1.07,17,1.62,27,2.65,2,-1.06,43,-0.12,40,-0.56,44,-0.85,42,-1.01,38,-1.02,38,-1.25,16,-0.16,18,2.35,43,1.29,43,-1.05,2,-1.03,37,1.38,42,1.73,1,-1.02,43,-0.86,39,0.62,0,-1.05,42,2.62,41,1.46,37,-1.02],[32,0.77,42,-1.01,40,-1.12,43,4.29,46,-1.01,34,-1.03,44,-1.01,38,-1.13,26,-0.83,46,-1.09,41,5.92,43,-1.09,20,-1.04,23,-1.11,1,-1.03,44,-1.01,23,4.86,23,3.46,25,6.04,18,0.94,17,1.62,46,1.64,36,2.61,36,0.71,35,2.4,35,2.84,18,0.36],[27,1.6,41,-1.02,26,-1.08,20,-1.05,19,-1.01,42,-1.01,46,-1.02,17,-0.25,25,-1.05,1,0.85,32,0.57,33,0.14,45,-1.02,34,-1.02,43,0.62,2,-1.03,21,7.48,34,1.77,34,2.19,26,12.56,46,0.43,33,0.15],[45,-1.1,20,1.96,40,-1.05,43,-1.13,44,-1.02,1,-1.03,44,-1.12,40,-1.18,34,-1.03,0,-1.02,36,-1.04,2,-1.04,16,1.92,37,2.71,37,2.69,0,0.39,32,0.06,18,-0.56,34,-1.04,2,1.0,40,-1.06,2,-1.05,34,-0.29,42,0.26,41,-1.03,42,-1.02,38,-0.35,21,-1.08,31,-1.07,33,0.63,28,0.05],[40,-1.18,40,-1.08,44,-1.02,44,-1.03,44,4.49,42,4.94,41,0.22,40,-1.34,44,1.77,29,0.83,41,-1.03,40,-1.15,30,0.4,44,-1.01,2,-1.05,32,-0.17,43,3.79,40,18.93,17,-0.29,43,-0.03,20,4.91,7,-1.03,2,-1.04],[30,-1.11,43,-1.08,1,0.98,32,0.38,33,0.66,40,-1.24,17,-0.67,42,-1.02,41,-1.03,27,-0.68,38,-0.85,33,0.37,40,-1.11,28,-1.14,45,2.44,0,1.78,32,-1.07,4,-1.09,43,7.65,40,-1.2,17,-0.79],[1,-0.77,35,-1.03,1,-1.02,46,-1.03,43,1.0,40,0.38,32,0.23,46,8.08,17,1.19,27,1.69,36,-1.03,30,0.54,42,-0.51,41,-0.33,4,7.97,40,-1.13,45,5.6,19,-1.02,38,-1.02]];
  // ---------- モンテカルロ（破産率）：過去の月をランダムに並べ替えて、口座 % リスクの複利で回す ----------
  const MC_LS = 'eaLiveMC_v1';
  const MC_DEF = {cap: 300000, risk: 1, years: 1, ruin: 30, sims: 1000, set: 'acc', half: true};
  S.mc = (() => { try { return Object.assign({}, MC_DEF, JSON.parse(localStorage.getItem(MC_LS) || '{}')); } catch (e) { return Object.assign({}, MC_DEF); } })();
  function mcKeys(o) {
    if (o.set === 'all') return MC_KEYS.slice();
    if (o.set === 'on') { const c = cfg(); return MC_KEYS.filter(k => c.eas[k] && c.eas[k].on && c.eas[k].mode !== 'off'); }
    return MC_KEYS.filter(k => MIN_ACC[k] !== undefined && MIN_ACC[k] * 10000 <= o.cap);
  }
  function mcRun(o, risk, keys) {
    const use = MC_KEYS.map(k => keys.indexOf(k) >= 0), months = Math.round(o.years * 12), n = MC_MONTHS.length;
    const floor = 1 - o.ruin / 100, finals = [], dds = []; let ruined = 0;
    for (let s = 0; s < o.sims; s++) {
      let eq = 1, pk = 1, mdd = 0, dead = false;
      for (let m = 0; m < months && !dead; m++) {
        const t = MC_MONTHS[Math.floor(Math.random() * n)];
        for (let i = 0; i < t.length; i += 2) {
          if (!use[t[i]]) continue;
          eq *= 1 + risk / 100 * (o.half && eq < 0.9 * pk ? 0.5 : 1) * t[i + 1];
          if (eq > pk) pk = eq;
          if (1 - eq / pk > mdd) mdd = 1 - eq / pk;
          if (eq <= floor) { dead = true; break; }
        }
      }
      if (dead) ruined++;
      finals.push(eq); dds.push(mdd);
    }
    finals.sort((a, b) => a - b); dds.sort((a, b) => a - b);
    const q = (arr, p) => arr[Math.min(arr.length - 1, Math.floor(p * (arr.length - 1)))];
    return {risk, ruin: ruined / o.sims * 100, p5: q(finals, .05), p50: q(finals, .5), p95: q(finals, .95), dd50: q(dds, .5), dd95: q(dds, .95)};
  }
  window.eaLiveMCOpen = function () { S.mcOpen = !S.mcOpen; render(); };
  window.eaLiveMCSet = function (k, v) {
    S.mc[k] = k === 'set' ? v : k === 'half' ? !!v : Number(v);
    try { localStorage.setItem(MC_LS, JSON.stringify(S.mc)); } catch (e) {}
    if (k === 'set' || k === 'half') render();
  };
  window.eaLiveMCRun = function () {
    const o = Object.assign({}, S.mc);
    o.cap = Math.max(10000, o.cap || MC_DEF.cap); o.risk = Math.min(10, Math.max(0.1, o.risk || MC_DEF.risk));
    o.years = Math.min(10, Math.max(0.25, o.years || 1)); o.ruin = Math.min(99, Math.max(5, o.ruin || 30)); o.sims = Math.min(5000, Math.max(200, o.sims || 1000));
    const keys = mcKeys(o);
    if (!keys.length) { S.mcRes = {err: '対象の EA がありません'}; render(); return; }
    const risks = [0.5, 1, 1.5, 2, 3]; if (risks.indexOf(o.risk) < 0) risks.push(o.risk); risks.sort((a, b) => a - b);
    S.mcRes = {o, n: keys.length, rows: risks.map(r => mcRun(o, r, keys))};
    render();
  };
  function mcSection() {
    const o = S.mc, r = S.mcRes, yen = v => '¥' + Math.round(v).toLocaleString('ja-JP');
    const inp = (k, label, step) => `<div><div style="font-size:10px;color:#94a3b8;margin-bottom:3px">${label}</div><input type="number" step="${step}" inputmode="decimal" value="${esc(o[k])}" oninput="eaLiveMCSet('${k}',this.value)" class="ea-input" style="width:100%"></div>`;
    const setBtn = (v, l) => `<button onclick="eaLiveMCSet('set','${v}')" style="${btn};padding:7px 4px;font-size:11px;${o.set === v ? neon('#22d3ee', '34,211,238') : offBtn}">${l}</button>`;
    const col = p => p >= 5 ? '#f87171' : p >= 1 ? '#fbbf24' : '#4ade80';
    let res = '';
    if (r && r.err) res = `<div style="font-size:12px;color:#f87171;margin-top:10px">${r.err}</div>`;
    else if (r) {
      const me = r.rows.find(x => x.risk === r.o.risk), pc = v => (v >= 1 ? '+' : '') + ((v - 1) * 100).toFixed(0) + '%';
      res = `<div style="margin-top:12px;display:flex;justify-content:space-between;align-items:center;background:#0f172a;border:1.5px solid ${col(me.ruin)};border-radius:10px;padding:10px 12px">
          <div style="font-size:12px;color:#e2e8f0">破産確率（リスク ${r.o.risk}%）<div style="font-size:10px;color:#64748b">${r.o.years} 年の間に ${yen(r.o.cap * (1 - r.o.ruin / 100))} 以下になる</div></div>
          <div style="font-size:20px;font-weight:800;color:${col(me.ruin)}">${me.ruin.toFixed(1)}%</div></div>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-top:8px">${[['下位 5%', me.p5], ['真ん中', me.p50], ['上位 5%', me.p95]].map(([l, v]) =>
          `<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:6px 8px"><div style="font-size:10px;color:#94a3b8">${r.o.years} 年後 ${l}</div><div style="font-size:12px;font-weight:700;color:${v >= 1 ? '#4ade80' : '#f87171'};margin-top:2px">${yen(r.o.cap * v)}</div><div style="font-size:10px;color:#64748b">${pc(v)}</div></div>`).join('')}</div>
        <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:12px 0 4px">リスクごとの比較</div>
        <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right">
          <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">リスク</th><th>破産確率</th><th>真ん中</th><th>DD 真ん中</th><th>DD 悪い 5%</th></tr>
          ${r.rows.map(x => `<tr style="border-bottom:1px solid #1e293b;${x.risk === r.o.risk ? 'background:rgba(34,211,238,.08)' : ''}"><td style="text-align:left;padding:6px 4px">${x.risk}%</td><td style="color:${col(x.ruin)};font-weight:700">${x.ruin.toFixed(1)}%</td><td style="color:${x.p50 >= 1 ? '#4ade80' : '#f87171'}">${pc(x.p50)}</td><td style="color:#f87171">-${(x.dd50 * 100).toFixed(0)}%</td><td style="color:#f87171">-${(x.dd95 * 100).toFixed(0)}%</td></tr>`).join('')}
        </table>
        <div style="font-size:10px;color:#64748b;margin-top:6px;line-height:1.6">対象 ${r.n} 本 · ${r.o.sims} 回 · 2017 年 7 月〜2026 年 10 月の月をランダムに並べ替えて、口座の % で複利。同じ月のトレードはまとめて動かすので、一緒に負ける時期も入る。「DD 悪い 5%」は 20 回に 1 回はこれ以上の DD になる目安。</div>`;
    }
    return `<div class="ea-card" style="padding:8px 12px;margin-top:4px"><button onclick="eaLiveMCOpen()" style="width:100%;display:flex;justify-content:space-between;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:12px;padding:2px 0">
      <span>🎲 モンテカルロ（破産確率）</span><span style="color:#94a3b8">${S.mcOpen ? '▲' : '▼'}</span></button>
      ${S.mcOpen ? `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px">
          ${inp('cap', '資金（円）', 10000)}${inp('risk', 'リスク（%/回）', 0.1)}${inp('years', '期間（年）', 0.5)}
          ${inp('ruin', '破産定義（資金−%）', 5)}${inp('sims', '試行回数', 100)}
          <div><div style="font-size:10px;color:#94a3b8;margin-bottom:3px">DD10% で半分</div><button onclick="eaLiveMCSet('half',${o.half ? 0 : 1})" style="${btn};padding:8px 4px;font-size:11px;${o.half ? neon('#22d3ee', '34,211,238') : offBtn}">${o.half ? 'あり' : 'なし'}</button></div>
        </div>
        <div style="font-size:10px;color:#94a3b8;margin:10px 0 4px">対象の EA</div>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${setBtn('acc', '資金に合う EA')}${setBtn('on', '今 ON の EA')}${setBtn('all', '29 本すべて')}</div>
        <button onclick="eaLiveMCRun()" style="${btn};margin-top:10px;padding:11px;font-size:13px;${neon('#38bdf8', '56,189,248')}">▶ 実行</button>
        ${res}` : ''}</div>`;
  }
  function sigSection() {
    if (!(S.dash && S.dash.signals)) return '';
    const list = sigAll().filter(g => String(g.Account) === S.acc).slice(-15).reverse();
    const rows = list.map(g => `<div onclick="eaLiveSignal('${esc(g.SigID)}')" style="cursor:pointer;display:flex;justify-content:space-between;gap:8px;padding:8px 2px;border-bottom:1px solid #1e293b;font-size:12px">
        <div><b>${esc(g.EA)}</b> ${dirJa(g.Direction)}<div style="color:#94a3b8;font-size:11px">${esc(String(g.Time).slice(5, 16))} · ${esc(sigWhy(g.Status))}${markIcon(g) ? ' · ' + markIcon(g) : ''}</div></div>
        <div style="color:#64748b;font-size:11px;text-align:right">${esc(g.Symbol)}<br>${esc(g.Price)}</div></div>`).join('');
    return `<div style="font-size:12px;font-weight:700;color:#94a3b8;margin-top:8px">入らなかったシグナル（最近）</div>
      <div class="ea-card" style="padding:4px 12px">${rows || '<div style="font-size:12px;color:#94a3b8;padding:8px 0">ここ 60 日はありません</div>'}
        <div style="font-size:10px;color:#64748b;padding:6px 0">全体停止中・最小ロットで見送りなどで入らなかったもの。タップで判定を付けられる。</div></div>`;
  }
  function resSection() {
    const mine = resAll().filter(r => String(r.Account) === S.acc);
    const wait = mine.filter(r => r.Status === 'WAIT'), recent = mine.filter(r => r.Status !== 'WAIT').slice(-5).reverse();
    const chips = pairNames().map(p => `<button onclick="eaResOpen('${esc(p)}')" style="border:1px solid #334155;background:#0f172a;color:#cbd5e1;border-radius:999px;padding:7px 11px;font-size:12px;font-weight:700">${esc(p)} <span style="color:#22d3ee">＋予約</span></button>`).join('')
      || '<div style="font-size:12px;color:#94a3b8">通貨ペアタブの監視ペアがここに出ます</div>';
    return `<div style="font-size:12px;font-weight:700;color:#94a3b8;margin-top:8px">予約エントリー（${ACC_JA[S.acc]}口座）</div>
      <div class="ea-card" style="padding:10px 12px">
        ${wait.length ? wait.map(r => resLine(r, true)).join('') : '<div style="font-size:12px;color:#94a3b8;padding-bottom:6px">待機中の予約はありません</div>'}
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">${chips}</div>
        ${recent.length ? `<div style="font-size:11px;color:#64748b;margin-top:10px">最近の予約</div>${recent.map(r => resLine(r, false)).join('')}` : ''}
        <div style="font-size:10px;color:#64748b;margin-top:8px;line-height:1.5">M15 か H1 のストキャス（14,5,3）が 20 未満→%D を上抜け→20 を上抜けで買い（売りは逆）。予約した後の足だけ見る。損切り：ストキャス直下＝押しの安値（売りは戻りの高値）のすぐ外、MA＝エントリー時のその MA の位置（逆側にある時はストキャス直下）。期限なし（取り消すまで）。</div>
      </div>`;
  }
  function resSheet() {
    const f = S.res; if (!f) return '';
    const seg = (name, val, opts) => `<div style="display:grid;grid-template-columns:repeat(${opts.length === 4 ? 2 : opts.length},minmax(0,1fr));gap:6px">${opts.map(([v, l, col, rgb]) =>
      `<button onclick="eaResSet('${name}','${v}')" style="${btn};${f[name] === v ? neon(col || '#22d3ee', rgb || '34,211,238') : offBtn}">${l}</button>`).join('')}</div>`;
    const inp = (name, ph, step) => `<input type="number" step="${step || 'any'}" inputmode="decimal" value="${esc(f[name])}" oninput="eaResSet('${name}',this.value,1)" placeholder="${ph}" class="ea-input" style="width:100%">`;
    const lab = t => `<div style="font-size:11px;color:#94a3b8;font-weight:700;margin:2px 0 6px">${t}</div>`;
    return `<div onclick="if(event.target===this)eaResClose()" style="position:fixed;inset:0;background:rgba(2,6,23,.72);z-index:300;display:flex;align-items:flex-end">
      <div style="width:100%;max-height:88vh;overflow:auto;background:#111c31;border:1px solid #26364f;border-radius:16px 16px 0 0;padding:16px 16px calc(16px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:center"><div style="font-size:16px;font-weight:800">${esc(f.symbol)} を予約 <span style="font-size:11px;color:#94a3b8">${ACC_JA[S.acc]}口座</span></div>
          <button onclick="eaResClose()" aria-label="閉じる" style="width:36px;height:36px;border-radius:9px;border:1px solid #334155;background:#172033;color:#cbd5e1;font-size:18px">×</button></div>
        ${S.dash && S.dash.features && S.dash.features.resKind ? `<div>${lab('種類')}${seg('kind', f.kind, [['ENTRY', '実エントリー', '#4ade80', '74,222,128'], ['SIGNAL', 'シグナルのみ', '#fbbf24', '251,191,36']])}
          ${f.kind === 'SIGNAL' ? `<div style="font-size:10px;color:#94a3b8;margin-top:6px">条件がそろったら Telegram に 1 回送って終わり（注文はしない。通知の設定に関係なく送る）${caps(S.acc).indexOf('res_kind') < 0 ? '<br><span style="color:#fbbf24">PC の EA を更新するまでは待機のまま（注文もしません）</span>' : ''}</div>` : ''}</div>` : ''}
        <div>${lab('向き')}${seg('direction', f.direction, [['BUY', '買い', '#f87171', '248,113,113'], ['SELL', '売り', '#38bdf8', '56,189,248']])}</div>
        <div>${lab('エントリー')}${seg('trigger', f.trigger, [['M15', 'M15'], ['H1', 'H1']])}</div>
        <div>${lab('損切り')}${seg('slMode', f.slMode, [['stoch', 'ストキャス直下'], ['m15ma200', 'M15 MA200'], ['h1ma75', 'H1 MA75'], ['h1ma200', 'H1 MA200']])}</div>
        <div>${lab('利確の価格（空 = なし）')}${inp('tp', 'なし')}</div>
        ${f.kind === 'SIGNAL' ? '' : `<div>${lab('ロットの決め方')}${seg('lotMode', f.lotMode, [['pct', '口座の %'], ['jpy', '最大損失'], ['lot', 'ロット']])}
          <div style="margin-top:8px">${inp('lotValue', LOT_JA[f.lotMode])}</div></div>`}
        <div>${lab('メモ（任意）')}<input value="${esc(f.note)}" oninput="eaResSet('note',this.value,1)" class="ea-input" style="width:100%"></div>
        ${f.msg ? `<div style="font-size:12px;color:${/でき|失敗|通信|入れて/.test(f.msg) ? '#f87171' : '#94a3b8'}">${esc(f.msg)}</div>` : ''}
        <button onclick="eaResSubmit()" ${f.busy ? 'disabled' : ''} style="${btn};padding:13px;font-size:14px;${neon('#4ade80', '74,222,128')}">${f.busy ? '保存中…' : f.kind === 'SIGNAL' ? 'シグナルを予約する' : '予約する'}</button>
      </div></div>`;
  }
  window.eaResOpen = function (sym) { S.res = {symbol: sym, kind: 'ENTRY', direction: 'BUY', trigger: 'M15', slMode: 'stoch', tp: '', lotMode: 'pct', lotValue: '0.5', note: '', msg: ''}; render(); };
  window.eaResClose = function () { S.res = null; render(); };
  window.eaResSet = function (k, v, quiet) {
    if (!S.res) return; S.res[k] = v;
    if (k === 'lotMode') S.res.lotValue = v === 'pct' ? '0.5' : v === 'jpy' ? '3000' : '0.01';
    if (!quiet) render();
  };
  async function resPost(body) {
    return fetch(GAS_URL, {method: 'POST', body: JSON.stringify(Object.assign({action: 'eaResSave', key: appKey()}, body))}).then(x => x.json());
  }
  window.eaResSubmit = async function () {
    const f = S.res; if (!f || f.busy) return;
    const v = Number(f.lotValue);
    if (!(v > 0)) { f.msg = 'ロットの値を入れてください'; render(); return; }
    if (f.lotMode === 'pct' && v > 3) { f.msg = '口座の % は 3% までにしてください'; render(); return; }
    f.busy = true; f.msg = ''; render();
    try {
      const r = await resPost({op: 'create', account: S.acc, kind: f.kind, symbol: f.symbol, direction: f.direction, trigger: f.trigger, slMode: f.slMode, tp: f.tp, lotMode: f.lotMode, lotValue: v, note: f.note});
      if (!r || r.success === false) throw new Error((r && r.error) || '保存できませんでした');
      // safety: a signal-only reservation saved without its kind would become a real order -> take it back at once
      if (f.kind === 'SIGNAL' && String((r.reservation || {}).Kind) !== 'SIGNAL') {
        await resPost({op: 'cancel', resId: (r.reservation || {}).ResID}).catch(() => {});
        throw new Error('裏側（GAS）がシグナルのみに対応していないため取り消しました（GAS のデプロイ後に使えます）');
      }
      S.dash = S.dash || {}; S.dash.reservations = resAll().concat([r.reservation]);
      try { localStorage.setItem(CACHE_LS, JSON.stringify(S.dash)); } catch (e) {}
      S.res = null; S.saving = '予約しました（EA は 5 分以内に受け取ります）'; render(); refreshViews();
      setTimeout(() => { S.saving = ''; render(); }, 4000);
    } catch (e) { f.busy = false; f.msg = '保存できませんでした: ' + e.message; render(); }
  };
  window.eaResCancel = async function (id) {
    if (!confirm('この予約を取り消しますか？')) return;
    try {
      const r = await resPost({op: 'cancel', resId: id});
      if (!r || r.success === false) throw new Error((r && r.error) || '');
      resAll().forEach(x => { if (String(x.ResID) === String(id)) x.Status = r.status || 'CANCEL'; });
      render(); refreshViews();
    } catch (e) { alert('取り消せませんでした: ' + e.message); }
  };

  // ---------- view
  const neon = (col, rgb) => `border:1px solid ${col};background:rgba(${rgb},.10);color:${col};box-shadow:0 0 10px rgba(${rgb},.28)`;
  const offBtn = 'border:1px solid #334155;background:#172033;color:#94a3b8';
  const btn = 'border-radius:8px;padding:9px 4px;font-weight:700;font-size:12px;width:100%';
  const MODE = {auto: ['自動売買', '#4ade80', '74,222,128'], signal: ['シグナルのみ', '#22d3ee', '34,211,238'], off: ['停止', '#94a3b8', '148,163,184']};

  function cardMode(c, card) { const ms = card.keys.map(k => c.eas[k[0]].mode); return ms.every(m => m === ms[0]) ? ms[0] : 'auto'; }
  function onSyms(c, card) { return card.keys.filter(k => c.eas[k[0]].on).map(k => k[1]); }

  function render() {
    const root = document.getElementById('ea-root'); if (!root) return;
    if (!appKey()) {
      root.innerHTML = `<div class="section"><div class="ea-card"><div style="font-weight:800;margin-bottom:6px">EA の合言葉を入れてください</div>
        <div style="font-size:12px;color:#94a3b8;margin-bottom:8px">最初の 1 回だけ。この端末に保存されます。</div>
        <input id="eal-key" class="ea-input" style="width:100%" placeholder="合言葉"><button class="ea-save" style="margin-top:10px" onclick="eaLiveSetKey()">保存</button></div></div>`;
      return;
    }
    const c = cfg(), st = (S.dash && S.dash.status && S.dash.status[S.acc]) || {}, live = S.acc === 'live', minLot = c.lot_mode === 'min';
    const run = !!c.running, n = c.notify || {};
    const tab = on => `${btn};${on ? neon('#22d3ee', '34,211,238') : 'border:1px solid transparent;background:transparent;color:#94a3b8'};padding:10px;font-size:13px;font-weight:800`;
    const dd = st.DD !== undefined && st.DD !== '' ? (-(Number(st.DD) * 100)).toFixed(1) + '%' : '—';
    let onCount = 0; ALL_KEYS.forEach(k => { if (c.eas[k].on && c.eas[k].mode !== 'off') onCount++; });
    const cards = CARDS.map(card => {
      const m = cardMode(c, card), md = MODE[m], syms = onSyms(c, card), active = m !== 'off' && syms.length;
      const style = active && m === 'auto' ? 'border:1px solid #4ade80;box-shadow:0 0 10px rgba(74,222,128,.22)' : active ? 'border:1px solid #22d3ee;box-shadow:0 0 8px rgba(34,211,238,.14)' : 'border:1px solid #26364f;opacity:.7';
      return `<button onclick="eaLiveOpen('${card.id}')" style="text-align:left;color:inherit;border-radius:12px;padding:10px;min-height:86px;background:#111c31;${style}">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px"><span style="font-size:15px;font-weight:800">${famCode(card)}</span><span style="font-size:10px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${card.title}</span></div>
        <div style="font-size:11px;color:#cbd5e1;margin-top:5px;line-height:1.4;min-height:15px">${syms.length ? syms.join(' · ') : '銘柄なし'}</div>
        <div style="margin-top:6px"><span style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;color:${md[1]};background:rgba(${md[2]},.12)">${md[0]}</span></div></button>`;
    }).join('');
    const trades = ((S.dash && S.dash.trades) || []).filter(t => String(t.Account) === S.acc)
      .sort((x, y) => String(y.EntryTime || y.SignalTime).localeCompare(String(x.EntryTime || x.SignalTime))).slice(0, 15).map(t => {   // newest first
      const pr = Number(t.Profit), col = t.Status === 'OPEN' ? '#22d3ee' : pr > 0 ? '#4ade80' : pr < 0 ? '#f87171' : '#94a3b8';
      return `<div onclick="eaLiveTrade('${esc(t.TradeID)}')" style="cursor:pointer;display:flex;justify-content:space-between;gap:8px;padding:8px 2px;border-bottom:1px solid #1e293b;font-size:12px">
        <div><b>${esc(t.EA)}</b> ${t.Direction === 'BUY' ? '買い' : '売り'}<div style="color:#94a3b8;font-size:11px">${esc(String(t.EntryTime).slice(5, 16))} · ${esc(t.Lot)} lot${markIcon(t) ? ' · ' + markIcon(t) : ''}</div></div>
        <div style="text-align:right;color:${col};font-weight:700">${t.Status === 'OPEN' ? '保有中' : yen(t.Profit)}<div style="font-size:11px;color:#94a3b8">${t.R !== '' && t.R != null ? Number(t.R).toFixed(2) + 'R' : ''}</div></div></div>`;
    }).join('') || '<div style="color:#94a3b8;font-size:12px;padding:10px 0">まだ EA のトレードはありません</div>';
    let sheet = '';
    if (S.sheet) {
      const card = CARDS.find(x => x.id === S.sheet), m = cardMode(c, card);
      const modes = ['auto', 'signal', 'off'].map(v => `<button onclick="eaLiveMode('${card.id}','${v}')" style="${btn};${m === v ? neon(MODE[v][1], MODE[v][2]) : offBtn}">${MODE[v][0]}</button>`).join('');
      const chips = card.keys.map(([k, sym, note]) => { const on = c.eas[k].on;
        return `<button onclick="eaLiveSym('${k}')" style="${on ? neon('#4ade80', '74,222,128') : 'border:1px solid #334155;background:#0f172a;color:#94a3b8'};border-radius:999px;padding:8px 12px;font-size:12px;font-weight:700">${sym}<span style="font-size:10px;opacity:.85">${note}</span></button>`; }).join('');
      const weights = card.keys.filter(k => HALF[k[0]]).map(([k, sym]) => { const w = Number(c.eas[k].weight);
        return `<div style="display:flex;align-items:center;gap:8px;margin-top:6px"><span style="font-size:12px;color:#cbd5e1;flex:1">${sym} のロット</span>
          <button onclick="eaLiveWeight('${k}',0.5)" style="${btn};width:auto;padding:7px 12px;${w === 0.5 ? neon('#22d3ee', '34,211,238') : offBtn}">半分</button>
          <button onclick="eaLiveWeight('${k}',1)" style="${btn};width:auto;padding:7px 12px;${w === 1 ? neon('#22d3ee', '34,211,238') : offBtn}">全量</button></div>`; }).join('');
      sheet = `<div onclick="if(event.target===this)eaLiveClose()" style="position:fixed;inset:0;background:rgba(2,6,23,.72);z-index:300;display:flex;align-items:flex-end">
        <div style="width:100%;max-height:85vh;overflow:auto;background:#111c31;border:1px solid #26364f;border-radius:16px 16px 0 0;padding:16px 16px calc(16px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:14px">
          <div style="display:flex;justify-content:space-between;gap:10px"><div><div style="font-size:18px;font-weight:800">${famCode(card)} <span style="font-size:12px;color:#94a3b8;font-weight:600">${card.title}</span></div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px;line-height:1.5">${card.desc}</div></div>
            <button onclick="eaLiveClose()" aria-label="閉じる" style="flex:none;width:36px;height:36px;border-radius:9px;border:1px solid #334155;background:#172033;color:#cbd5e1;font-size:18px">×</button></div>
          <div><div style="font-size:11px;color:#94a3b8;font-weight:700;margin-bottom:6px">稼働モード</div><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${modes}</div></div>
          <div><div style="font-size:11px;color:#94a3b8;font-weight:700;margin-bottom:6px">使う銘柄</div><div style="display:flex;flex-wrap:wrap;gap:6px">${chips}</div>${weights}</div>
        </div></div>`;
    }
    root.innerHTML = `<div class="section" style="display:flex;flex-direction:column;gap:12px">
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;background:#111c31;border:1px solid #26364f;border-radius:12px;padding:5px">
        <button onclick="eaLiveAcc('demo')" style="${tab(!live)}">デモ口座</button><button onclick="eaLiveAcc('live')" style="${tab(live)}">本番口座</button></div>
      <div style="background:#111c31;border-radius:12px;padding:12px;display:flex;flex-direction:column;gap:10px;${run ? 'border:1px solid #4ade80;box-shadow:0 0 12px rgba(74,222,128,.30)' : 'border:1px solid #f87171;box-shadow:0 0 12px rgba(248,113,113,.18)'}">
        <div style="display:flex;justify-content:space-between;align-items:center"><div style="font-weight:800;font-size:14px">${live ? '本番口座（EA 用）' : 'デモ口座（EA 用）'}</div>
          <div style="font-size:11px;color:#94a3b8">${st.UpdatedAt ? '最終通信 ' + esc(String(st.UpdatedAt).slice(5, 16)) : '通信なし'}</div></div>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;font-size:11px;color:#94a3b8">
          <div>残高<div style="font-size:14px;color:#f8fafc;font-weight:700;margin-top:2px">${yen(st.Balance)}</div></div>
          <div>有効証拠金<div style="font-size:14px;color:#f8fafc;font-weight:700;margin-top:2px">${yen(st.Equity)}</div></div>
          <div>最高値から<div style="font-size:14px;color:#f87171;font-weight:700;margin-top:2px">${dd}</div></div></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">自動売買</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px">
            <button onclick="eaLiveRun(true)" style="${btn};${run ? neon('#4ade80', '74,222,128') : offBtn}">稼働</button>
            <button onclick="eaLiveRun(false)" style="${btn};${!run ? neon('#f87171', '248,113,113') : offBtn}">全体停止</button></div></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">ロット</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px">
            <button onclick="eaLiveLotMode('risk')" style="${btn};${minLot ? offBtn : neon('#22d3ee', '34,211,238')}">リスク %</button>
            <button onclick="eaLiveLotMode('min')" style="${btn};${minLot ? neon('#fbbf24', '251,191,36') : offBtn}${caps(S.acc).indexOf('min_lot') < 0 ? ';opacity:.5' : ''}">最小ロット</button></div></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">${minLot ? '最大リスク' : 'リスク'}</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px">${[0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02].map(v =>
            `<button onclick="eaLiveRisk(${v})" style="${btn};${Math.abs(c.base_risk - v) < 1e-9 ? neon(minLot ? '#fbbf24' : '#22d3ee', minLot ? '251,191,36' : '34,211,238') : offBtn}">${+(v * 100).toFixed(2)}%</button>`).join('')}</div></div>
        ${!minLot && c.base_risk >= 0.015 ? '<div style="font-size:10px;color:#fbbf24;margin-top:-4px">DD10% で半分を ON のままにしておくのがおすすめ</div>' : ''}
        ${minLot ? '<div style="font-size:10px;color:#fbbf24;margin-top:-4px">全 EA が銘柄の最小ロット（例 0.01）で入ります。最小ロットでも損失が口座の「最大リスク」を超える回は見送り</div>' : ''}
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">DD10%で半分</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px">
            <button onclick="${c.dd_half === false ? 'eaLiveDDHalf()' : ''}" style="${btn};${c.dd_half !== false ? neon('#22d3ee', '34,211,238') : offBtn}">ON</button>
            <button onclick="${c.dd_half !== false ? 'eaLiveDDHalf()' : ''}" style="${btn};${c.dd_half === false ? neon('#f87171', '248,113,113') : offBtn}">OFF</button></div></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">通知</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${[['notifyEntry', 'Entry'], ['notifyExit', 'Exit'], ['notifyError', 'Error']].map(([k, l]) =>
            `<button onclick="eaLiveNotify('${k}')" style="${btn};${n[k] !== false ? neon('#22d3ee', '34,211,238') : offBtn}">${l}</button>`).join('')}</div></div>
        ${S.saving || S.err ? `<div style="font-size:11px;color:${/でき|失敗|通信/.test(S.saving + S.err) ? '#f87171' : '#94a3b8'}">${esc(S.saving || S.err)}</div>` : ''}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px"><div style="font-size:12px;font-weight:700;color:#94a3b8">EA 一覧</div><div style="display:flex;align-items:center;gap:8px"><span style="font-size:11px;color:#94a3b8">${onCount} / ${ALL_KEYS.length} が ON</span>${onCount < ALL_KEYS.length ? `<button onclick="eaLiveAllOn()" style="${btn};${offBtn};padding:4px 9px;font-size:11px">すべて ON</button>` : ''}</div></div>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">${cards}</div>
      ${featSection()}
      ${btSection()}
      ${minLotSection()}
      ${mcSection()}
      ${resSection()}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-top:8px">EA のトレード（最近）</div>
      <div class="ea-card" style="padding:4px 12px">${trades}</div>
      ${sigSection()}
    </div>${sheet}${resSheet()}`;
  }


  // ---------- EA trades outside the EA tab: home (open), history (closed), analysis (per EA vs backtest), detail
  // Backtest per EA (research feat/final_trades.pkl, R after costs): trades, per year, win %, average R, PF, data from
  const BT = {"DX@AUDJPY": {"n": 2, "py": 0.2, "wr": 0.0, "avgR": -1.027, "pf": 0.0, "since": "2023"}, "DX@AUDUSD": {"n": 5, "py": 0.5, "wr": 40.0, "avgR": 0.202, "pf": 1.33, "since": "2019"}, "DX@BTCUSD": {"n": 6, "py": 0.6, "wr": 33.3, "avgR": 0.335, "pf": 1.45, "since": "2017"}, "DX@EURJPY": {"n": 9, "py": 0.5, "wr": 11.1, "avgR": -0.182, "pf": 0.72, "since": "2008"}, "DX@EURUSD": {"n": 17, "py": 0.8, "wr": 41.2, "avgR": 1.213, "pf": 3.69, "since": "2007"}, "DX@GBPJPY": {"n": 15, "py": 0.8, "wr": 53.3, "avgR": 0.509, "pf": 2.52, "since": "2007"}, "DX@GBPUSD": {"n": 8, "py": 0.4, "wr": 50.0, "avgR": 0.888, "pf": 2.82, "since": "2011"}, "DX@XAUUSD": {"n": 13, "py": 0.7, "wr": 69.2, "avgR": 2.829, "pf": 12.01, "since": "2014"}, "DX@JP225": {"n": 4, "py": 0.4, "wr": 25.0, "avgR": 0.084, "pf": 1.12, "since": "2017"}, "DX@XAGUSD": {"n": 7, "py": 0.7, "wr": 28.6, "avgR": 2.679, "pf": 4.09, "since": "2019"}, "DX@US100": {"n": 10, "py": 1.0, "wr": 30.0, "avgR": 0.97, "pf": 2.5, "since": "2018"}, "DX@US30": {"n": 5, "py": 0.5, "wr": 40.0, "avgR": 0.555, "pf": 1.88, "since": "2017"}, "DX@US500": {"n": 7, "py": 0.7, "wr": 42.9, "avgR": 0.895, "pf": 2.6, "since": "2019"}, "DR@AUDJPY": {"n": 6, "py": 0.6, "wr": 66.7, "avgR": 6.679, "pf": 19.13, "since": "2019"}, "DR@AUDUSD": {"n": 15, "py": 1.5, "wr": 46.7, "avgR": 1.336, "pf": 3.61, "since": "2019"}, "DR@BTCUSD": {"n": 7, "py": 0.7, "wr": 57.1, "avgR": 2.884, "pf": 7.61, "since": "2021"}, "DR@CADJPY": {"n": 14, "py": 0.7, "wr": 50.0, "avgR": 0.918, "pf": 2.78, "since": "2007"}, "DR@CHFJPY": {"n": 14, "py": 0.7, "wr": 35.7, "avgR": 0.365, "pf": 1.59, "since": "2007"}, "DR@EURJPY": {"n": 15, "py": 0.8, "wr": 33.3, "avgR": 1.104, "pf": 2.74, "since": "2007"}, "DR@EURUSD": {"n": 14, "py": 0.7, "wr": 14.3, "avgR": 0.171, "pf": 1.2, "since": "2007"}, "DR@GBPJPY": {"n": 21, "py": 1.1, "wr": 33.3, "avgR": 0.707, "pf": 2.03, "since": "2010"}, "DR@GBPUSD": {"n": 23, "py": 1.1, "wr": 47.8, "avgR": 0.913, "pf": 2.87, "since": "2007"}, "DR@XAUUSD": {"n": 12, "py": 0.6, "wr": 16.7, "avgR": -0.333, "pf": 0.62, "since": "2013"}, "DR@JP225": {"n": 11, "py": 1.1, "wr": 18.2, "avgR": -0.593, "pf": 0.32, "since": "2017"}, "DR@XAGUSD": {"n": 11, "py": 1.1, "wr": 36.4, "avgR": 0.176, "pf": 1.23, "since": "2018"}, "DR@US100": {"n": 8, "py": 0.8, "wr": 62.5, "avgR": 0.966, "pf": 3.5, "since": "2019"}, "DR@US30": {"n": 12, "py": 1.2, "wr": 66.7, "avgR": 1.794, "pf": 6.28, "since": "2019"}, "DR@US500": {"n": 11, "py": 1.1, "wr": 54.5, "avgR": 1.9, "pf": 5.63, "since": "2019"}, "DR@USDCAD": {"n": 15, "py": 0.8, "wr": 60.0, "avgR": 1.715, "pf": 5.14, "since": "2007"}, "DR@USDCHF": {"n": 12, "py": 0.6, "wr": 33.3, "avgR": 0.253, "pf": 1.36, "since": "2007"}, "DY@AUDJPY": {"n": 32, "py": 3.2, "wr": 34.4, "avgR": 0.935, "pf": 2.44, "since": "2018"}, "DY@AUDUSD": {"n": 42, "py": 4.2, "wr": 33.3, "avgR": 0.352, "pf": 1.52, "since": "2018"}, "DY@EURJPY": {"n": 74, "py": 3.7, "wr": 28.4, "avgR": 0.453, "pf": 1.68, "since": "2007"}, "DY@EURUSD": {"n": 70, "py": 3.5, "wr": 38.6, "avgR": 0.545, "pf": 1.9, "since": "2007"}, "DY@GBPJPY": {"n": 81, "py": 4.0, "wr": 40.7, "avgR": 0.698, "pf": 2.2, "since": "2006"}, "DY@GBPUSD": {"n": 67, "py": 3.4, "wr": 40.3, "avgR": 0.635, "pf": 2.04, "since": "2007"}, "DY@USDJPY": {"n": 63, "py": 3.1, "wr": 30.2, "avgR": 0.395, "pf": 1.57, "since": "2006"}, "DC@AUDJPY": {"n": 4, "py": 0.4, "wr": 25.0, "avgR": -0.473, "pf": 0.05, "since": "2019"}, "DC@AUDUSD": {"n": 3, "py": 0.3, "wr": 66.7, "avgR": 0.215, "pf": 17.65, "since": "2021"}, "DC@EURJPY": {"n": 9, "py": 0.5, "wr": 55.6, "avgR": 1.152, "pf": 4.51, "since": "2010"}, "DC@EURUSD": {"n": 7, "py": 0.3, "wr": 85.7, "avgR": 2.068, "pf": 15.04, "since": "2007"}, "DC@GBPJPY": {"n": 5, "py": 0.2, "wr": 60.0, "avgR": 0.673, "pf": 16.71, "since": "2012"}, "DC@GBPUSD": {"n": 6, "py": 0.3, "wr": 16.7, "avgR": -0.626, "pf": 0.02, "since": "2014"}, "DC@USDJPY": {"n": 14, "py": 0.7, "wr": 57.1, "avgR": 0.419, "pf": 3.57, "since": "2007"}, "DA@AUDJPY": {"n": 14, "py": 1.9, "wr": 35.7, "avgR": 1.425, "pf": 3.21, "since": "2019"}, "DB@AUDJPY": {"n": 5, "py": 0.5, "wr": 40.0, "avgR": 4.345, "pf": 7.89, "since": "2020"}, "DW@AUDJPY": {"n": 26, "py": 2.6, "wr": 42.3, "avgR": 1.187, "pf": 3.42, "since": "2019"}, "DA@AUDUSD": {"n": 13, "py": 1.6, "wr": 23.1, "avgR": -0.301, "pf": 0.64, "since": "2018"}, "DB@AUDUSD": {"n": 7, "py": 0.7, "wr": 57.1, "avgR": 2.856, "pf": 7.2, "since": "2019"}, "DW@AUDUSD": {"n": 15, "py": 1.5, "wr": 33.3, "avgR": 0.193, "pf": 1.28, "since": "2018"}, "DA@EURJPY": {"n": 25, "py": 1.3, "wr": 28.0, "avgR": 0.11, "pf": 1.15, "since": "2008"}, "DB@EURJPY": {"n": 21, "py": 1.1, "wr": 33.3, "avgR": 1.178, "pf": 2.84, "since": "2007"}, "DW@EURJPY": {"n": 45, "py": 2.2, "wr": 35.6, "avgR": 0.528, "pf": 1.92, "since": "2008"}, "DA@EURUSD": {"n": 28, "py": 1.4, "wr": 28.6, "avgR": 0.315, "pf": 1.51, "since": "2007"}, "DB@EURUSD": {"n": 20, "py": 1.0, "wr": 20.0, "avgR": -0.395, "pf": 0.49, "since": "2007"}, "DW@EURUSD": {"n": 41, "py": 2.0, "wr": 36.6, "avgR": 0.462, "pf": 1.83, "since": "2008"}, "DA@GBPJPY": {"n": 26, "py": 1.3, "wr": 46.2, "avgR": 0.852, "pf": 2.54, "since": "2007"}, "DB@GBPJPY": {"n": 19, "py": 0.9, "wr": 31.6, "avgR": 1.054, "pf": 2.54, "since": "2008"}, "DW@GBPJPY": {"n": 36, "py": 1.8, "wr": 58.3, "avgR": 1.123, "pf": 4.07, "since": "2008"}, "DA@GBPUSD": {"n": 42, "py": 2.1, "wr": 42.9, "avgR": 0.702, "pf": 2.24, "since": "2007"}, "DB@GBPUSD": {"n": 16, "py": 0.8, "wr": 37.5, "avgR": 3.431, "pf": 6.77, "since": "2007"}, "DW@GBPUSD": {"n": 37, "py": 1.9, "wr": 51.4, "avgR": 1.411, "pf": 3.86, "since": "2008"}, "DA@USDJPY": {"n": 29, "py": 1.5, "wr": 17.2, "avgR": 0.012, "pf": 1.01, "since": "2007"}, "DB@USDJPY": {"n": 15, "py": 0.8, "wr": 26.7, "avgR": 0.877, "pf": 2.13, "since": "2007"}, "DW@USDJPY": {"n": 28, "py": 1.4, "wr": 46.4, "avgR": 1.08, "pf": 3.3, "since": "2007"}, "Q@AUDJPY":{"n":111,"py":5.3,"wr":44.1,"avgR":0.683,"pf":2.21,"since":"2005"},"CA@AUDJPY":{"n":231,"py":10.7,"wr":48.5,"avgR":0.248,"pf":1.49,"since":"2005"},"C@EURUSD":{"n":199,"py":9.3,"wr":54.8,"avgR":0.461,"pf":2.1,"since":"2005"},"C@USDJPY":{"n":224,"py":10.4,"wr":46.4,"avgR":0.373,"pf":1.75,"since":"2005"},"DS@JP225":{"n":124,"py":13.4,"wr":39.5,"avgR":0.255,"pf":1.83,"since":"2017"},"DS@US500":{"n":57,"py":6.2,"wr":42.1,"avgR":0.259,"pf":1.78,"since":"2017"},"DS@XAUUSD":{"n":189,"py":9.0,"wr":49.2,"avgR":0.27,"pf":1.58,"since":"2005"},"J2@USDJPY":{"n":234,"py":11.5,"wr":41.5,"avgR":0.565,"pf":2.01,"since":"2006"},"M@US30":{"n":91,"py":9.9,"wr":71.4,"avgR":0.077,"pf":1.41,"since":"2017"},"M@US500":{"n":89,"py":9.7,"wr":76.4,"avgR":0.132,"pf":1.85,"since":"2017"},"Q@XAGUSD":{"n":254,"py":12.2,"wr":40.6,"avgR":0.512,"pf":1.92,"since":"2005"},"Q@XAUUSD":{"n":457,"py":21.0,"wr":44.6,"avgR":0.545,"pf":2.04,"since":"2005"},"S@BTCUSD":{"n":349,"py":37.3,"wr":33.2,"avgR":0.581,"pf":1.82,"since":"2017"},"S@XAUUSD":{"n":410,"py":19.0,"wr":35.6,"avgR":0.498,"pf":1.78,"since":"2005"},"T2@EURUSD":{"n":303,"py":14.0,"wr":42.2,"avgR":0.533,"pf":1.91,"since":"2005"},"T@US30":{"n":101,"py":10.9,"wr":40.6,"avgR":0.304,"pf":1.49,"since":"2017"},"P@XAUUSD":{"n":318,"py":14.9,"wr":48.4,"avgR":0.95,"pf":3.0,"since":"2005"},"P@EURUSD":{"n":158,"py":7.4,"wr":51.3,"avgR":0.373,"pf":1.81,"since":"2005"},"P@USDJPY":{"n":178,"py":8.2,"wr":42.7,"avgR":0.266,"pf":1.5,"since":"2005"},"P@US500":{"n":128,"py":13.9,"wr":49.2,"avgR":0.254,"pf":1.53,"since":"2017"},"P@US100":{"n":122,"py":13.3,"wr":50.8,"avgR":0.298,"pf":1.64,"since":"2017"},"DL@EURUSD":{"n":44,"py":2.0,"wr":59.1,"avgR":0.249,"pf":1.59,"since":"2005"},"DL@USDJPY":{"n":46,"py":2.1,"wr":54.3,"avgR":0.322,"pf":1.76,"since":"2005"},"HL@EURUSD":{"n":89,"py":4.2,"wr":52.8,"avgR":1.32,"pf":4.19,"since":"2005"},"Q@BTCUSD":{"n":332,"py":36.2,"wr":37.7,"avgR":0.728,"pf":2.19,"since":"2017"},"IX@US30":{"n":48,"py":5.5,"wr":52.1,"avgR":0.143,"pf":1.35,"since":"2018"},"IX@US500":{"n":50,"py":5.4,"wr":56.0,"avgR":0.144,"pf":1.43,"since":"2017"},"IX@US100":{"n":52,"py":5.6,"wr":59.6,"avgR":0.331,"pf":1.97,"since":"2017"},"IX@JP225":{"n":58,"py":6.3,"wr":58.6,"avgR":0.311,"pf":1.96,"since":"2017"}};
  const ACC_JA = {demo: 'デモ', live: '本番'};
  let V = {histAcc: 'demo', anAcc: 'demo'};
  function eaName(key) {
    if (/^RES:/.test(String(key || ''))) return '予約エントリー';
    const k = String(key || ''), card = CARDS.find(c => c.keys.some(x => x[0] === k));
    const sym = k.split('@')[1] || '';
    return k;                                   // 2026-11-20 (user): EAs are written as their code everywhere (P@EURUSD, DB@GBPUSD ...)
  }
  const rawTrades = () => ((S.dash && S.dash.trades) || []).filter(t => !/^RES:/.test(String(t.EA)));   // reservations are recorded as 裁量 trades (Trades)
  const isEx = t => !!String(t.Excluded || '').trim();      // 2026-11-20: left out of every result by the trader (wrong lot ...)
  const allTrades = () => rawTrades().filter(t => !isEx(t));
  const dirJa = d => String(d).toUpperCase() === 'BUY' ? '買い' : '売り';
  const jst = v => esc(String(v || '').replace(/\+09:00$/, '').slice(5, 16));
  function tradeRow(t, onclick) {
    const open = t.Status === 'OPEN', pr = Number(t.Profit), col = open ? '#22d3ee' : pr > 0 ? '#4ade80' : pr < 0 ? '#f87171' : '#94a3b8';
    const R = t.R !== '' && t.R != null && !isNaN(t.R) ? (Number(t.R) > 0 ? '+' : '') + Number(t.R).toFixed(2) + 'R' : '';
    const line = String(t.Direction).toUpperCase() === 'BUY' ? '#f43f5e' : '#3b82f6';   // buy red / sell blue (same as 裁量)
    return `<div class="list-card" onclick="${onclick}" style="cursor:pointer;border-left:4px solid ${line}${isEx(t) ? ';opacity:.45' : ''}">
      <div style="flex:1"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <div style="font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px">${esc(t.Symbol)}
          <span class="badge ${String(t.Direction).toUpperCase() === 'BUY' ? 'buy' : 'sell'}">${String(t.Direction).toUpperCase() === 'BUY' ? '▲ Buy' : '▼ Sell'}</span>
          ${/^RES:/.test(String(t.EA)) ? '<span class="badge" style="background:rgba(34,211,238,.12);color:#22d3ee">予約</span>' : '<span class="badge" style="background:rgba(74,222,128,.12);color:#4ade80">EA</span>'}${isEx(t) ? '<span class="badge" style="background:rgba(148,163,184,.15);color:#94a3b8">成績から外した</span>' : ''}${String(t.Account) === 'live' ? '<span class="badge" style="background:rgba(248,113,113,.12);color:#f87171">本番</span>' : ''}</div>
        <div style="font-weight:700;font-size:15px;color:${col}">${open ? '' : R}</div></div>
        <div style="font-size:11px;color:#94a3b8;display:flex;justify-content:space-between"><span>${esc(eaName(t.EA))} · ${jst(t.EntryTime)}${markIcon(t) ? ' · ' + markIcon(t) : ''}</span><span>${open ? esc(t.Lot) + ' lot' : yen(t.Profit)}</span></div></div>
      <div style="color:#94a3b8;font-size:16px;margin-left:12px">›</div></div>`;
  }
  const EA_PIP = sym => /JPY/.test(sym) ? 0.01 : /XAU/.test(sym) ? 0.1 : /XAG/.test(sym) ? 0.01 : /BTC|ETH|US30|US500|US100|JP225/.test(sym) ? 1 : 0.0001;
  /** EA trades as records shaped like the hand-written ones, so the 裁量 analysis (stats, charts, Monte Carlo) works on them. */
  function asEntries(acc) {
    return allTrades().filter(t => String(t.Account) === acc && t.Status === 'CLOSED').map(t => {
      const pip = EA_PIP(String(t.Symbol)), s = String(t.Direction).toUpperCase() === 'BUY' ? 1 : -1, en = String(t.EntryTime || '');
      const pips = (Number(t.ExitPrice) && Number(t.EntryPrice)) ? Math.round(s * (Number(t.ExitPrice) - Number(t.EntryPrice)) / pip * 10) / 10 : '';
      const slp = (Number(t.SLPrice) && Number(t.EntryPrice)) ? Math.abs(Number(t.EntryPrice) - Number(t.SLPrice)) / pip : '';
      return {EntryID: 'ea-' + t.TradeID, EntryDate: en.slice(0, 10).replace(/-/g, '/'), EntryTime: en.slice(11, 16), 'PairName（元）': String(t.Symbol),
        Direction: s === 1 ? 'Buy' : 'Sell', 'ステータス': '決済', '実取得pips': pips, StopLossPips: slp, '損益': t.Profit, Lot: t.Lot, R: t.R, '勝敗': Number(t.R) > 0.05 ? '勝ち' : Number(t.R) < -0.05 ? '負け' : '引き分け',
        Source: 'EA', EAKey: String(t.EA), ExitDate: String(t.ExitTime || '').slice(0, 10).replace(/-/g, '/'), ExitTime: String(t.ExitTime || '').slice(11, 16)};
    });
  }
  window.eaLive = {
    asEntries: asEntries,
    data: () => S.dash, load: load, name: eaName,
    openTrades: () => rawTrades().filter(t => t.Status === 'OPEN'),
    homeHtml: function () {
      const pos = rawTrades().filter(t => t.Status === 'OPEN').slice().reverse().map(t => tradeRow(t, `eaLiveTrade('${esc(t.TradeID)}')`)).join('');
      const wait = resAll().filter(r => r.Status === 'WAIT');
      const res = wait.length ? `<div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">予約中</div><div class="ea-card" style="padding:4px 12px;margin-bottom:8px">${wait.map(r => resLine(r, false)).join('')}</div>` : '';
      return pos + res;
    },
    waitingCount: () => resAll().filter(r => r.Status === 'WAIT').length,
    historyHtml: function (f) {
      if (!appKey()) return '<div style="color:#94a3b8;text-align:center;padding:20px">EA 設定タブで合言葉を入れると、EA のトレードが出ます</div>';
      const tab = a => `<button class="toggle-btn ${V.histAcc === a ? 'active' : ''}" onclick="eaLiveHistAcc('${a}')" style="flex:1">${ACC_JA[a]}口座</button>`;
      let xs = rawTrades().filter(t => String(t.Account) === V.histAcc && t.Status !== 'OPEN');
      const cardOf = k => /^RES:/.test(String(k)) ? 'RES' : ((CARDS.find(c => c.keys.some(x => x[0] === k)) || {}).id || '');
      // 2026-11-20: every EA family is a chip (with its count, dimmed when none yet) + 旧 EA (keys no longer in the app);
      // a family with several EAs gets a second row per symbol (D@: B / C / W x symbol)
      const cnt = {}; xs.forEach(t => { const c = cardOf(t.EA) || 'OLD'; cnt[c] = (cnt[c] || 0) + 1; });
      const chip = (id, label, n, on, fn) => `<button class="toggle-btn ${on ? 'active' : ''}" onclick="${fn}('${id}')" style="flex:none;font-size:11px;padding:5px 9px;white-space:nowrap${n ? '' : ';opacity:.4'}">${label}${n ? ' <span style="color:#94a3b8">' + n + '</span>' : ''}</button>`;
      let chips = `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">${chip('', 'すべて', xs.length, !V.histEA, 'eaLiveHistEA')}${CARDS.map(c => chip(c.id, famCode(c), cnt[c.id] || 0, V.histEA === c.id, 'eaLiveHistEA')).join('')}${cnt.OLD ? chip('OLD', '旧 EA', cnt.OLD, V.histEA === 'OLD', 'eaLiveHistEA') : ''}</div>`;
      const card = CARDS.find(c => c.id === V.histEA);
      if (V.histEA) xs = xs.filter(t => (cardOf(t.EA) || 'OLD') === V.histEA);
      if (card && card.keys.length > 1) {
        const kc = {}; xs.forEach(t => { kc[t.EA] = (kc[t.EA] || 0) + 1; });
        const keyLabel = k => { const [e, sym] = String(k).split('@'); return (card.id === 'D' ? e.slice(1) + ' ' : '') + sym; };
        chips += `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;padding-left:8px;border-left:2px solid #334155">${chip('', '銘柄すべて', xs.length, !V.histKey, 'eaLiveHistKey')}${card.keys.map(k => chip(k[0], keyLabel(k[0]), kc[k[0]] || 0, V.histKey === k[0], 'eaLiveHistKey')).join('')}</div>`;
        if (V.histKey) xs = xs.filter(t => String(t.EA) === V.histKey);
      }
      if (V.histEA === 'OLD') chips += `<div style="font-size:10px;color:#64748b;margin:-2px 0 8px">今はアプリに無い EA（外した・名前を変えた EA）のトレード</div>`;
      xs = xs.filter(t => { const d = String(t.EntryTime || '').slice(0, 10); if (f && f.fPeriod === 'custom') { if (f.dFrom && d < f.dFrom) return false; if (f.dTo && d > f.dTo) return false; } return true; });
      const exN = xs.filter(isEx).length, all = xs; xs = xs.filter(t => !isEx(t));
      const sumR = xs.reduce((a, t) => a + (Number(t.R) || 0), 0), sumP = xs.reduce((a, t) => a + (Number(t.Profit) || 0), 0), w = xs.filter(t => Number(t.R) > 0).length;
      const head = `<div style="display:flex;gap:6px;margin-bottom:10px">${tab('demo')}${tab('live')}</div>` + chips + (xs.length ? `<div style="font-size:12px;color:#94a3b8;margin-bottom:10px">${xs.length} 件 · 勝率 ${(w / xs.length * 100).toFixed(0)}% · 合計 ${(sumR > 0 ? '+' : '') + sumR.toFixed(1)}R · ${yen(sumP)}</div>` : '');
      return head + (exN ? `<div style="font-size:11px;color:#64748b;margin:-4px 0 8px">成績から外したトレード ${exN} 件（薄く表示・数字には入れていない）</div>` : '') + (all.slice().reverse().map(t => tradeRow(t, `eaLiveTrade('${esc(t.TradeID)}')`)).join('') || '<div style="color:#64748b;text-align:center;padding:20px">決済した EA のトレードはまだありません</div>');
    },
    analysisHtml: function (kind) {
      if (!appKey()) return '';
      V.anAcc = (document.getElementById('flt-acc') || {}).value || V.anAcc;
      const xs = allTrades().filter(t => String(t.Account) === V.anAcc && t.Status === 'CLOSED');
      const by = {}; xs.forEach(t => (by[t.EA] = by[t.EA] || []).push(t));
      const num = (v, d) => v == null || isNaN(v) ? '—' : Number(v).toFixed(d);
      const famOf = k => (CARDS.find(c => c.keys.some(x => x[0] === k)) || {}).id;
      const st = g => { const R = g.map(t => Number(t.R) || 0), n = R.length, w = R.filter(r => r > 0).length, pos = R.filter(r => r > 0).reduce((a, b) => a + b, 0),
        neg = -R.filter(r => r < 0).reduce((a, b) => a + b, 0), sum = R.reduce((a, b) => a + b, 0); return {n, w, sum, avg: n ? sum / n : null, pf: neg > 0 ? pos / neg : null}; };
      const mark = j => j ? `<span style="font-weight:800;color:${j.c}">${j.m}</span>` : '<span style="color:#64748b">—</span>';
      const famRows = CARDS.map(c => {
        const g = c.keys.flatMap(k => by[k[0]] || []), a = st(g), j = judge(a.n, a.avg, FAM_BT[c.id].avg, FAM_BT[c.id].sd);
        return `<tr style="border-bottom:1px solid #1e293b"><td style="padding:6px 4px;text-align:left;font-weight:700">${famCode(c)}</td><td>${mark(j)}</td><td>${a.n}</td>
          <td>${num(a.avg, 2)}<div style="color:#64748b">${num(FAM_BT[c.id].avg, 2)}</div></td><td>${a.n ? (a.sum > 0 ? '+' : '') + a.sum.toFixed(1) : '—'}</td></tr>`;
      }).join('');
      const rows = ALL_KEYS.map(k => {
        const a = st(by[k] || []), b = BT[k] || {}, f = FAM_BT[famOf(k)] || {}, exp = expOf(k), j = judge(a.n, a.avg, exp, f.sd);
        return `<tr style="border-bottom:1px solid #1e293b"><td style="padding:6px 4px;text-align:left">${esc(k)}</td><td>${mark(j)}</td><td>${a.n}</td>
          <td>${a.n ? (a.w / a.n * 100).toFixed(0) + '%' : '—'}<div style="color:#64748b">${num(b.wr, 0)}%</div></td>
          <td>${num(a.avg, 2)}<div style="color:#64748b">${num(exp, 2)}</div></td>
          <td>${a.pf != null ? a.pf.toFixed(2) : a.n ? '∞' : '—'}<div style="color:#64748b">${num(b.pf, 2)}</div></td>
          <td>${a.n ? (a.sum > 0 ? '+' : '') + a.sum.toFixed(1) : '—'}<div style="color:#64748b">${num(b.py, 0)}回/年</div></td></tr>`;
      }).join('');
      const th = '<tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">EA</th><th>判定</th><th>回数</th>';
      return `<div class="section" style="margin-bottom:14px"><div class="section-title" style="margin-bottom:8px">🤖 EA の成績（${ACC_JA[V.anAcc]}口座 · 実際 / <span style="color:#64748b">バックテスト</span>）</div>
        <div style="font-size:11px;color:#94a3b8;line-height:1.6;margin-bottom:6px">○ 範囲内 · △ 下振れ（バックテストの平均から、回数に応じたブレの 1〜2 倍下） · × 要確認（2 倍より下） · — 10 回未満は判定しない</div>
        <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:8px 0 4px">系統ごと</div>
        <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right;white-space:nowrap">${th}<th>平均R</th><th>合計R</th></tr>${famRows}</table></div>
        <div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:12px 0 4px">EA ごと</div>
        <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right;white-space:nowrap">${th}<th>勝率</th><th>平均R</th><th>PF</th><th>合計R</th></tr>${rows}</table></div>
        <div style="font-size:10px;color:#64748b;margin-top:6px;line-height:1.6">下の灰色がバックテスト。EA ごとの平均 R の目安は、バックテストが 30 回以上ならその EA の平均、少なければ系統の平均。ブレ＝系統の 1 回あたりのばらつき ÷ √回数。
          大勝ちで稼ぐ EA（D@・DR・DX・S・Q など）は、大勝ちが来るまで △ になりやすい。× が続く時に止めるか考える。</div></div>`;
    }
  };
  function refreshViews() {
    if (typeof renderPositions === 'function' && document.getElementById('positions-list')) try { renderPositions(); } catch (e) {}
    const an = document.getElementById('eal-analysis'); if (an && an.style.display !== 'none') an.innerHTML = window.eaLive.analysisHtml();
    if (V.anKind === 'ea' && typeof applyAnalysisFilters === 'function') try { applyAnalysisFilters(); } catch (e) {}
    if (document.getElementById('modal-history')?.classList.contains('active') && typeof renderHistoryList === 'function') renderHistoryList();
    // the monthly summary can open before the EA data has arrived: draw its EA box again
    const mb = document.getElementById('monthly-ea-stats');
    if (mb && mb.dataset.ym && document.getElementById('modal-monthly')?.classList.contains('active') && typeof renderMonthlyEAStats_ === 'function') renderMonthlyEAStats_(mb.dataset.ym);
  }
  window.eaLiveHistEA = id => { V.histEA = id; V.histKey = ''; if (typeof renderHistoryList === 'function') renderHistoryList(); };
  window.eaLiveHistKey = k => { V.histKey = k; if (typeof renderHistoryList === 'function') renderHistoryList(); };
  window.eaLiveHistAcc = a => { V.histAcc = a; if (typeof renderHistoryList === 'function') renderHistoryList(); };
  window.eaLiveAnAcc = a => { V.anAcc = a; const an = document.getElementById('eal-analysis'); if (an) an.innerHTML = window.eaLive.analysisHtml(V.anKind); };
  // entry / exit charts drawn by the EA PC (EA_Trades.EntryImage / ExitImage, Drive links); tap = large view
  function imgs(t) {
    const list = [['エントリー', t.EntryImage], ['決済', t.ExitImage]].filter(x => x[1]);
    if (!list.length || typeof getImageUrl !== 'function') return '';
    const big = list.map(x => getImageUrl(x[1], 1600));
    return `<div style="margin-top:14px;display:flex;flex-direction:column;gap:10px">${list.map((x, i) => `<div><div style="font-size:12px;font-weight:700;color:#94a3b8;margin-bottom:4px">📈 ${x[0]}</div>
      <img src="${esc(getImageUrl(x[1], 1000))}" referrerpolicy="no-referrer" loading="lazy" onclick='openLightbox(${JSON.stringify(big[i])}, ${JSON.stringify(big)}, ${i})' style="width:100%;border-radius:8px;border:1px solid #334155;cursor:zoom-in"></div>`).join('')}</div>`;
  }
  // ---------- the trader's mark on an EA trade or on a signal that was not traded (2026-11-12) ----------
  const VERDICTS = [['ok', 'OK', '#4ade80', '74,222,128'], ['ng', '入らない方がいい', '#f87171', '248,113,113'], ['maybe', '迷う', '#fbbf24', '251,191,36']];
  const MARK_TAGS = ['伸びすぎ', 'レンジの中', '上位足が逆', '指標の前後', '損切りが遠い', 'その他'];
  const VERDICT_ICON = {ok: '✅', ng: '⛔', maybe: '❔'};
  const markIcon = x => (VERDICT_ICON[x && x.Verdict] || '') + (x && (x.ExitVerdict || x.ExitTags || x.ExitWantImage) ? '🚪' : '') + (x && x.Comment ? '💬' : '');
  // the exit (closed trades only): how it went and where the exit should have been, plus a screenshot with the crosshair there
  const EXIT_VERDICTS = [['good', '良い決済', '#4ade80', '74,222,128'], ['early', '早すぎた', '#fbbf24', '251,191,36'], ['late', '遅すぎた', '#fb923c', '251,146,60'],
                         ['tight', '損切りが浅い', '#f87171', '248,113,113'], ['wide', '損切りが深い', '#c084fc', '192,132,252']];
  const EXIT_TAGS = ['M15 の押し安値割れ', 'H1 の押し安値割れ', 'H4 の押し安値割れ', '抵抗帯の手前', '前の高値・安値', 'H1 MA 割れ', 'ダウの転換', 'ライン割れ', 'その他'];
  function exitEditor(t) {
    const tags = String(t.ExitTags || '').split(',').filter(Boolean), img = t.ExitWantImage || '';
    const vb = ([v, l, col, rgb]) => `<button type="button" data-v="${v}" data-col="${col}" data-rgb="${rgb}" onclick="eaLiveExitV(this)" style="${btn};padding:8px 4px;font-size:12px;${t.ExitVerdict === v ? neon(col, rgb) : offBtn}">${l}</button>`;
    const tb = x => `<button type="button" data-t="${x}" data-on="${tags.indexOf(x) >= 0 ? 1 : 0}" onclick="eaLiveMarkT(this)" style="border-radius:999px;padding:6px 11px;font-size:12px;font-weight:700;${tags.indexOf(x) >= 0 ? neon('#22d3ee', '34,211,238') : offBtn}">${x}</button>`;
    return `<div id="eal-exit" data-verdict="${esc(t.ExitVerdict || '')}" data-img="${esc(img)}" style="margin-top:16px;padding-top:12px;border-top:1px solid #334155">
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-bottom:6px">🚪 決済の判定</div>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${EXIT_VERDICTS.map(vb).join('')}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">本当はどこで決済したかったか（いくつでも・売りは戻り高値超え）</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">${EXIT_TAGS.map(tb).join('')}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">決済したかった所のスクショ（十字線をその足に）</div>
      <div id="eal-exit-img">${exitImgHtml(img)}</div></div>`;
  }
  function exitImgHtml(img, busy) {
    const show = img && typeof getImageUrl === 'function' ? (String(img).startsWith('data:') ? img : getImageUrl(img, 800)) : img;
    return `${img ? `<div style="position:relative;margin-bottom:6px"><img src="${esc(show)}" referrerpolicy="no-referrer" style="width:100%;border-radius:8px;border:1px solid #334155">
        <button type="button" onclick="eaLiveExitImgRm()" style="position:absolute;top:6px;right:6px;border:0;border-radius:6px;background:rgba(15,23,42,.85);color:#f87171;font-size:12px;padding:4px 8px">✕ 外す</button></div>` : ''}
      <input type="file" id="eal-exit-file" accept="image/*" style="display:none" onchange="eaLiveExitImg(event)">
      <button type="button" ${busy ? 'disabled' : ''} onclick="document.getElementById('eal-exit-file').click()" style="${btn};padding:10px;${offBtn}">📷 ${img ? '画像を変える' : '画像を追加'}${busy ? ' ⏳' : ''}</button>`;
  }
  window.eaLiveExitV = function (el) {
    const box = document.getElementById('eal-exit'), v = box.dataset.verdict === el.dataset.v ? '' : el.dataset.v;
    box.dataset.verdict = v;
    box.querySelectorAll('button[data-v]').forEach(b => b.setAttribute('style', `${btn};padding:8px 4px;font-size:12px;${b.dataset.v === v ? neon(b.dataset.col, b.dataset.rgb) : offBtn}`));
  };
  window.eaLiveExitImgRm = function () { const box = document.getElementById('eal-exit'); box.dataset.img = ''; document.getElementById('eal-exit-img').innerHTML = exitImgHtml(''); };
  window.eaLiveExitImg = function (ev) {
    const f = ev.target.files && ev.target.files[0]; if (!f) return;
    const box = document.getElementById('eal-exit'), r = new FileReader();
    r.onload = async e => {
      box.dataset.busy = '1'; document.getElementById('eal-exit-img').innerHTML = exitImgHtml(e.target.result, true);
      let ref = '';
      try { ref = await uploadImageSmart(e.target.result, 'eaexit_' + Date.now() + '.jpg'); } catch (err) {}
      box.dataset.busy = '';
      if (ref && !String(ref).startsWith('data:')) { box.dataset.img = ref; document.getElementById('eal-exit-img').innerHTML = exitImgHtml(ref); }
      else { if (typeof showToast === 'function') showToast('⚠️ 画像のアップロードに失敗しました'); document.getElementById('eal-exit-img').innerHTML = exitImgHtml(box.dataset.img); }
    };
    r.readAsDataURL(f);
  };
  function markEditor(x, onSave, saved, extra) {
    const tags = String(x.Tags || '').split(',').filter(Boolean);
    const vb = ([v, l, col, rgb]) => `<button type="button" data-v="${v}" data-col="${col}" data-rgb="${rgb}" onclick="eaLiveMarkV(this)" style="${btn};padding:8px 4px;font-size:12px;${x.Verdict === v ? neon(col, rgb) : offBtn}">${l}</button>`;
    const tb = t => `<button type="button" data-t="${t}" data-on="${tags.indexOf(t) >= 0 ? 1 : 0}" onclick="eaLiveMarkT(this)" style="border-radius:999px;padding:6px 11px;font-size:12px;font-weight:700;${tags.indexOf(t) >= 0 ? neon('#22d3ee', '34,211,238') : offBtn}">${t}</button>`;
    return `<div id="eal-mark" data-verdict="${esc(x.Verdict || '')}" style="margin-top:14px">
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-bottom:6px">📝 判定</div>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${VERDICTS.map(vb).join('')}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">理由（いくつでも）</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">${MARK_TAGS.map(tb).join('')}</div>
      ${extra || ''}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">💬 コメント</div>
      <textarea id="eal-trade-comment" rows="3" maxlength="2000" class="form-input" style="width:100%;box-sizing:border-box;resize:vertical" placeholder="気付いたこと・入り方の良し悪しなど">${esc(x.Comment || '')}</textarea>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;gap:8px"><span id="eal-trade-comment-msg" style="font-size:11px;color:#64748b">${saved || ''}</span>
        <button onclick="${onSave}" style="${btn};width:auto;padding:8px 16px;${neon('#22d3ee', '34,211,238')}">保存</button></div></div>`;
  }
  window.eaLiveMarkV = function (el) {          // one verdict at a time; tapping the chosen one clears it
    const box = document.getElementById('eal-mark'), v = box.dataset.verdict === el.dataset.v ? '' : el.dataset.v;
    box.dataset.verdict = v;
    box.querySelectorAll('button[data-v]').forEach(b => b.setAttribute('style', `${btn};padding:8px 4px;font-size:12px;${b.dataset.v === v ? neon(b.dataset.col, b.dataset.rgb) : offBtn}`));
  };
  window.eaLiveMarkT = function (el) {
    const on = el.dataset.on !== '1'; el.dataset.on = on ? '1' : '0';
    el.setAttribute('style', `border-radius:999px;padding:6px 11px;font-size:12px;font-weight:700;${on ? neon('#22d3ee', '34,211,238') : offBtn}`);
  };
  function markValue() {
    const box = document.getElementById('eal-mark');
    const ex = document.getElementById('eal-exit'), on = el => [...el.querySelectorAll('button[data-t]')].filter(b => b.dataset.on === '1').map(b => b.dataset.t);
    return {verdict: box ? box.dataset.verdict || '' : '', tags: box ? [...box.querySelectorAll('button[data-t]')].filter(b => b.dataset.on === '1' && !(ex && ex.contains(b))).map(b => b.dataset.t).join(',') : '',
            exit: ex ? {verdict: ex.dataset.verdict || '', tags: on(ex).join(','), img: ex.dataset.img || '', busy: !!ex.dataset.busy} : null};
  }
  const sigAll = () => (S.dash && S.dash.signals) || [];
  window.eaLiveSignal = function (id) {
    const g = sigAll().find(x => String(x.SigID) === String(id)); if (!g) return;
    const row = (l, v) => `<div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid #1e293b;font-size:13px"><span style="color:#94a3b8">${l}</span><span style="text-align:right;word-break:break-all">${v === '' || v == null ? '—' : v}</span></div>`;
    const old = document.getElementById('eal-trade-modal'); if (old) old.remove();
    const m = document.createElement('div'); m.id = 'eal-trade-modal'; m.className = 'modal-overlay active';
    m.onclick = e => { if (e.target === m) m.remove(); };
    m.innerHTML = `<div class="modal-content"><div class="modal-header"><div class="modal-title">${esc(eaName(g.EA))}（入らなかったシグナル）</div><div class="modal-close" onclick="document.getElementById('eal-trade-modal').remove()">✕</div></div><div class="modal-body">
      ${row('口座', ACC_JA[g.Account] || esc(g.Account))}${row('時刻', jst(g.Time))}${row('銘柄・向き', esc(g.Symbol) + ' ' + dirJa(g.Direction))}
      ${row('値段', esc(g.Price))}${row('損切り', esc(Number(g.SL) ? Number(g.SL).toPrecision(6) : g.SL))}${row('入らなかった理由', esc(sigWhy(g.Status)))}
      ${markEditor(g, `eaLiveSaveSignal('${esc(g.SigID)}')`, '')}
      <div style="font-size:11px;color:#64748b;margin-top:10px">時刻は日本時間。チャートは MT5 で見る</div></div></div>`;
    document.body.appendChild(m);
  };
  function sigWhy(st) {
    st = String(st || '');
    if (/全体停止中/.test(st)) return '全体停止中';
    const m = st.match(/min lot risk ([\d.]+%) > ([\d.]+%)/); if (m) return `最小ロットでも ${m[1]}（上限 ${m[2]}）`;
    return st || '—';
  }
  window.eaLiveSaveSignal = async function (id) {
    const ta = document.getElementById('eal-trade-comment'), msg = document.getElementById('eal-trade-comment-msg'); if (!ta) return;
    const g = sigAll().find(x => String(x.SigID) === String(id)), mk = markValue();
    msg.textContent = '保存中…'; msg.style.color = '#94a3b8';
    try {
      const r = await fetch(GAS_URL, {method: 'POST', body: JSON.stringify({action: 'eaSignalMark', key: appKey(), sigId: id, signal: g, comment: ta.value, verdict: mk.verdict, tags: mk.tags})}).then(x => x.json());
      if (!r || r.success === false) throw new Error(/Unknown action|bad action|not allowed/.test(String(r && r.error)) ? 'GAS をデプロイすると使えます' : ((r && r.error) || '保存できませんでした'));
      if (g) { g.Comment = ta.value; g.Verdict = mk.verdict; g.Tags = mk.tags; }
      try { localStorage.setItem(CACHE_LS, JSON.stringify(S.dash)); } catch (e) {}
      msg.textContent = '保存しました'; msg.style.color = '#4ade80'; render();
    } catch (e) { msg.textContent = e.message; msg.style.color = '#f87171'; }
  };
  window.eaLiveTrade = function (id) {
    const t = rawTrades().find(x => String(x.TradeID) === String(id)); if (!t) return;
    const row = (l, v) => `<div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid #1e293b;font-size:13px"><span style="color:#94a3b8">${l}</span><span style="text-align:right;word-break:break-all">${v === '' || v == null ? '—' : v}</span></div>`;
    const old = document.getElementById('eal-trade-modal'); if (old) old.remove();
    const m = document.createElement('div'); m.id = 'eal-trade-modal'; m.className = 'modal-overlay active';
    m.onclick = e => { if (e.target === m) m.remove(); };
    m.innerHTML = `<div class="modal-content"><div class="modal-header"><div class="modal-title">${esc(eaName(t.EA))}</div><div class="modal-close" onclick="document.getElementById('eal-trade-modal').remove()">✕</div></div><div class="modal-body">
      ${row('口座', ACC_JA[t.Account] || esc(t.Account))}${row('銘柄・向き', esc(t.Symbol) + ' ' + dirJa(t.Direction))}${row('状態', t.Status === 'OPEN' ? '保有中' : '決済済み')}
      ${row('シグナルの足', jst(t.SignalTime))}${row('エントリー', jst(t.EntryTime) + ' @ ' + esc(t.EntryPrice))}${row('損切り', esc(t.SLPrice))}${row('利確', esc(t.TPPrice))}
      ${row('ロット', esc(t.Lot) + (t.LotMult && Number(t.LotMult) !== 1 ? '（倍率 ' + esc(t.LotMult) + '）' : '') + (t.Weight && Number(t.Weight) !== 1 ? '（重み ' + esc(t.Weight) + '）' : ''))}
      ${row('リスク', yen(t.RiskJPY))}${row('決済', t.ExitTime ? jst(t.ExitTime) + ' @ ' + esc(t.ExitPrice) : '')}${row('損益', t.Status === 'OPEN' ? '' : yen(t.Profit))}
      ${row('R', t.R !== '' && t.R != null ? Number(t.R).toFixed(2) : '')}${row('入った理由', esc(t.Reason))}${t.Note ? row('EA のメモ', esc(t.Note)) : ''}${row('チケット', esc(t.Ticket))}
      ${imgs(t)}
      ${markEditor(t, `eaLiveSaveComment('${esc(t.TradeID)}')`, t.CommentAt ? '保存 ' + jst(t.CommentAt) : '', t.Status === 'CLOSED' ? exitEditor(t) : '')}
      <div style="margin-top:14px;padding-top:10px;border-top:1px solid #1e293b">
        ${isEx(t) ? `<div style="font-size:12px;color:#94a3b8;margin-bottom:6px">成績から外しています（${esc(t.Excluded)}）</div>
          <button class="toggle-btn" style="width:100%" onclick="eaLiveExclude('${esc(t.TradeID)}', false)">成績に戻す</button>`
        : `<input id="eal-ex-reason" placeholder="外す理由（例：ロット間違い）" style="width:100%;box-sizing:border-box;margin-bottom:6px;padding:8px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:13px">
          <button class="toggle-btn" style="width:100%;color:#f87171" onclick="eaLiveExclude('${esc(t.TradeID)}', true)">このトレードを成績から外す</button>`}
        <div id="eal-ex-msg" style="font-size:11px;color:#64748b;margin-top:6px">消すのではなく印を付けるだけ（いつでも戻せる）。EA ごとの成績・履歴の合計・分析・週と月のまとめ・健康チェックから外れる。口座の残高と DD（MT5 の数字）はそのまま。</div></div>
      <div style="font-size:11px;color:#64748b;margin-top:10px">時刻は日本時間。チャートは MT5 で見る</div></div></div>`;
    document.body.appendChild(m);
  };
  // leave a trade out of every result / count it again (EA_Trades.Excluded, GAS eaTradeExclude, 2026-11-20)
  window.eaLiveExclude = async function (id, on) {
    const msg = document.getElementById('eal-ex-msg'), reason = ((document.getElementById('eal-ex-reason') || {}).value || '').trim();
    if (on && !reason) { msg.textContent = '外す理由を書いてください'; msg.style.color = '#fbbf24'; return; }
    msg.textContent = '保存中…'; msg.style.color = '#94a3b8';
    try {
      const r = await fetch(GAS_URL, {method: 'POST', body: JSON.stringify({action: 'eaTradeExclude', key: appKey(), tradeId: id, exclude: on, reason: reason})}).then(x => x.json());
      if (!r || r.success === false) throw new Error(/Unknown action/.test(String(r && r.error)) ? 'GAS を貼り直すと使えます' : ((r && r.error) || '保存できませんでした'));
      const t = rawTrades().find(x => String(x.TradeID) === String(id)); if (t) t.Excluded = r.excluded || '';
      try { localStorage.setItem(CACHE_LS, JSON.stringify(S.dash)); } catch (e) {}
      render(); refreshViews(); window.eaLiveTrade(id);
    } catch (e) { msg.textContent = e.message; msg.style.color = '#f87171'; }
  };
  // the trader's comment on an EA trade (EA_Trades.Comment, GAS eaTradeComment)
  window.eaLiveSaveComment = async function (id) {
    const ta = document.getElementById('eal-trade-comment'), msg = document.getElementById('eal-trade-comment-msg'); if (!ta) return;
    const mk = markValue();
    if (mk.exit && mk.exit.busy) { msg.textContent = '画像をアップロード中です'; msg.style.color = '#fbbf24'; return; }
    msg.textContent = '保存中…'; msg.style.color = '#94a3b8';
    try {
      const body = {action: 'eaTradeComment', key: appKey(), tradeId: id, comment: ta.value, verdict: mk.verdict, tags: mk.tags};
      if (mk.exit) Object.assign(body, {exitVerdict: mk.exit.verdict, exitTags: mk.exit.tags, exitImage: mk.exit.img});
      const r = await fetch(GAS_URL, {method: 'POST', body: JSON.stringify(body)}).then(x => x.json());
      if (!r || r.success === false) throw new Error(/Unknown action/.test(String(r && r.error)) ? 'GAS をデプロイすると使えます' : ((r && r.error) || '保存できませんでした'));
      const t = rawTrades().find(x => String(x.TradeID) === String(id)); if (t) { t.Comment = ta.value; t.Verdict = mk.verdict; t.Tags = mk.tags;
        if (mk.exit) Object.assign(t, {ExitVerdict: mk.exit.verdict, ExitTags: mk.exit.tags, ExitWantImage: mk.exit.img}); const j = new Date(Date.now() + 9 * 3600e3).toISOString(); t.CommentAt = j.slice(0, 10) + ' ' + j.slice(11, 16) + '+09:00'; }
      try { localStorage.setItem(CACHE_LS, JSON.stringify(S.dash)); } catch (e) {}
      msg.textContent = '保存しました'; msg.style.color = '#4ade80'; render(); refreshViews();
    } catch (e) { msg.textContent = e.message; msg.style.color = '#f87171'; }
  };
  // analysis: 裁量 / EA switch (the buttons are in index.html). EA shows its own panel and filters; the hand-written filters are hidden.
  const MANUAL_ONLY = ['flt-pair', 'flt-status', 'flt-timezone', 'flt-rule', 'flt-score', 'flt-entry-ref', 'flt-exit-ref', 'flt-manual-ma', 'flt-plan'];
  window._eaAnalysisType = 'manual';
  window.eaAnalysisType = function (b) {
    const v = (b && b.dataset && b.dataset.v) === 'ea' ? 'ea' : 'manual', on = v === 'ea';
    document.querySelectorAll('#trade-type-tabs button').forEach(x => x.classList.toggle('on', x.dataset.v === v));
    window._eaAnalysisType = v; V.anKind = v;
    const screen = document.getElementById('screen-analysis');
    let an = document.getElementById('eal-analysis');
    if (!an && screen) { an = document.createElement('div'); an.id = 'eal-analysis'; an.style.marginTop = '16px'; screen.appendChild(an); }
    const box = document.getElementById('flt-ea-box'); if (box) box.style.display = on ? 'grid' : 'none';
    MANUAL_ONLY.forEach(id => {
      const el = document.getElementById(id); if (!el) return;
      const w = el.parentNode && el.parentNode.classList && el.parentNode.classList.contains('analysis-multi-native') ? el.parentNode : el;
      w.style.display = on ? 'none' : '';
    });
    if (typeof updateAnalysisFilterVisibility === 'function') updateAnalysisFilterVisibility();   // MA filter: 裁量 only
    if (an) { an.style.display = on ? '' : 'none'; if (on) an.innerHTML = window.eaLive.analysisHtml(); }
    if (typeof applyAnalysisFilters === 'function') try { applyAnalysisFilters(); } catch (e) {}
    if (on && (!S._loadedAt || Date.now() - S._loadedAt > 60000)) { S._loadedAt = Date.now(); load(); }
  };
  function setupAnalysis() {
    const fe = document.getElementById('flt-ea'), fs = document.getElementById('flt-ea-sym');
    if (fe && fe.options.length <= 1) ALL_KEYS.forEach(k => fe.add(new Option(eaName(k), k)));
    if (fs && fs.options.length <= 1) [...new Set(ALL_KEYS.map(k => k.split('@')[1]))].sort().forEach(x => fs.add(new Option(x, x)));
    const fa = document.getElementById('flt-acc'); if (fa && !fa._eal) { fa._eal = 1; fa.addEventListener('change', () => { const an = document.getElementById('eal-analysis'); if (an && an.style.display !== 'none') an.innerHTML = window.eaLive.analysisHtml(); }); }
    if (typeof updateAnalysisFilterVisibility === 'function') updateAnalysisFilterVisibility();
  }
  document.addEventListener('DOMContentLoaded', () => { setupAnalysis(); setTimeout(() => { if (appKey()) { S._loadedAt = Date.now(); load(); } }, 1500); });

  window.renderEA = function () { render(); if (!S._loadedAt || Date.now() - S._loadedAt > 60000) { S._loadedAt = Date.now(); load(); } };
})();
