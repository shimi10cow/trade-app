// EA settings tab for the new live EAs (2026-10-24, docs/EA_SYSTEM_PLAN.md, mockup artifact 1SGsxraBBzz7PbVN9npFTB).
// Also owns the 裁量 / EA switch of the analysis tab (the old ea.js was removed 2026-10-25).
// Backend: GAS EA_Live.gs (eaGetDashboard / eaSaveConfig) with the app key (asked once, kept on this phone).
(function () {
  const KEY_LS = 'eaLiveAppKey_v1', ACC_LS = 'eaLiveAccount_v1', CACHE_LS = 'eaLiveDash_v1';
  const CARDS = [
    {id: 'R', title: 'レンジ', code: 'R', desc: 'H4 がもみ合いの時だけ、ダウの高値・安値の更新で入る', keys: [['R@EURUSD', 'EURUSD', '']]},
    {id: 'T', title: 'トレンド・ダウ', code: 'T2・T', desc: '日足 MA の向きに H4 がトレンドの時、H1 ダウの向きに M15 で入る（H4 が三角持ち合いの時は見送り）', keys: [['T2@EURUSD', 'EURUSD', ' T2'], ['T@US30', 'US30', ' T']]},
    {id: 'L', title: '推進TL反発', code: 'L・L2', desc: 'H4・H1 の推進 TL に 3〜4 回目に触れて、M15 が転換したら入る（ゴールドの L2 は伸びる先に壁がある時も見送り）', keys: [['L@EURUSD', 'EURUSD', ' L'], ['L2@XAUUSD', 'XAUUSD', ' L2']]},
    {id: 'A', title: 'リターンムーブ', code: 'A', desc: 'ブレイクした後、戻ってきた所で入る（伸びすぎは見送り）', keys: [['A@EURUSD', 'EURUSD', '']]},
    {id: 'C', title: 'M15調整TL抜け', code: 'C', desc: 'M15 の調整 TL を抜けたら入る', keys: [['C@EURUSD', 'EURUSD', ''], ['C@USDJPY', 'USDJPY', ' 調整が長い時']]},
    {id: 'J2', title: 'H1 ダウ転換', code: 'J2', desc: 'H1 の高値・安値の流れが変わったら入る', keys: [['J2@USDJPY', 'USDJPY', '']]},
    {id: 'S', title: 'H4MA押し目買い', code: 'S', desc: 'H4 の MA の向きに、押し目から入る', keys: [['S@XAUUSD', 'XAUUSD', ''], ['S@BTCUSD', 'BTCUSD', ' 買い・平日']]},
    {id: 'Q', title: '静観後のブレイク', code: 'Q', desc: '値動きが小さい時間の後、抜けた方に乗る', keys: [['Q@XAUUSD', 'XAUUSD', ''], ['Q@XAGUSD', 'XAGUSD', ''], ['Q@US30', 'US30', '']]},
    {id: 'DS', title: '右肩', code: 'DS', desc: 'ダブルトップ・ボトムの右肩で、反転を取る', keys: [['DS@JP225', 'JP225', ''], ['DS@US500', 'US500', ' 買い'], ['DS@XAUUSD', 'XAUUSD', ' 買い']]},
    {id: 'M', title: '短い押し目', code: 'M', desc: '大きな流れの向きに、2〜3 本の押しで入る（RSI2・終値で入る）', keys: [['M@US30', 'US30', ''], ['M@US500', 'US500', '']]},
  ];
  const HALF = {'S@XAUUSD': 1, 'Q@XAUUSD': 1};
  const LIVE_ON = ['R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'DS@JP225', 'S@BTCUSD', 'DS@US500'];
  const ALL_KEYS = CARDS.flatMap(c => c.keys.map(k => k[0]));
  let S = {acc: localStorage.getItem(ACC_LS) || 'demo', dash: null, sheet: null, saving: '', err: '', res: null};
  try { S.dash = JSON.parse(localStorage.getItem(CACHE_LS) || 'null'); } catch (e) {}

  function defaultConfig(acc) {
    const eas = {};
    ALL_KEYS.forEach(k => eas[k] = {mode: 'auto', on: true, weight: HALF[k] ? 0.5 : 1});
    return {running: false, base_risk: 0.01, dd_half: true, notify: {notifyEntry: true, notifyExit: true, notifyError: true, notifySignal: true}, eas: eas};
  }
  function cfg() {
    S.dash = S.dash || {}; S.dash.config = S.dash.config || {};
    if (!S.dash.config[S.acc]) S.dash.config[S.acc] = defaultConfig(S.acc);      // keep it, so edits stick before the first save
    const c = S.dash.config[S.acc];
    ALL_KEYS.forEach(k => { if (!c.eas[k]) c.eas[k] = defaultConfig(S.acc).eas[k]; });
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
  window.eaLiveRisk = function (v) { const c = cfg(); c.base_risk = Number(v); c.lot_mode = 'risk'; save(); };
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
  const BTX = {"A@EURUSD":[2005,2026,153,66,87,43.1,0.2,1.38,8.1,7.1,1.4],"C@EURUSD":[2005,2026,321,145,176,45.2,0.22,1.43,12.5,14.8,3.2],"C@USDJPY":[2005,2026,274,118,156,43.1,0.32,1.63,11.3,12.6,4.0],"DS@JP225":[2017,2026,111,45,66,40.5,0.18,1.29,6.9,11.4,2.0],"DS@US500":[2017,2026,46,23,23,50.0,0.29,1.51,4.7,4.8,1.4],"DS@XAUUSD":[2005,2026,189,93,96,49.2,0.27,1.58,6.2,9.0,2.4],"J2@USDJPY":[2005,2026,239,93,146,38.9,0.49,1.8,17.7,11.0,5.4],"L2@XAUUSD":[2005,2026,218,94,124,43.1,0.36,1.68,13.2,10.3,3.7],"L@EURUSD":[2005,2026,297,124,173,41.8,0.28,1.53,12.2,13.8,3.8],"M@US30":[2015,2026,107,79,28,73.8,0.12,1.73,2.6,9.9,1.1],"M@US500":[2017,2026,88,67,21,76.1,0.12,1.76,4.0,9.7,1.2],"Q@US30":[2015,2026,109,47,62,43.1,0.29,1.55,10.5,9.4,2.8],"Q@XAGUSD":[2005,2026,112,40,72,35.7,0.91,2.49,14.5,5.4,5.0],"Q@XAUUSD":[2005,2026,727,321,406,44.2,0.19,1.72,14.0,33.4,6.3],"R@EURUSD":[2005,2026,133,63,70,47.4,0.71,2.26,9.6,6.3,4.5],"S@BTCUSD":[2017,2026,280,98,182,35.0,0.69,2.0,17.9,30.3,20.8],"S@XAUUSD":[2005,2026,626,236,390,37.7,0.14,1.48,16.0,29.0,4.1],"T2@EURUSD":[2005,2026,377,155,222,41.1,0.4,1.67,17.6,17.4,6.9],"T@US30":[2015,2026,237,87,150,36.7,0.13,1.2,23.6,21.4,2.7]};
  const MIN_ACC = {'R@EURUSD': 20, 'T2@EURUSD': 20, 'L@EURUSD': 20, 'A@EURUSD': 20, 'C@EURUSD': 20, 'C@USDJPY': 20, 'J2@USDJPY': 20, 'DS@JP225': 20, 'S@BTCUSD': 20,
    'DS@US500': 30, 'M@US500': 50, 'T@US30': 50, 'L2@XAUUSD': 50, 'DS@XAUUSD': 60, 'Q@XAGUSD': 60, 'Q@US30': 60, 'S@XAUUSD': 100, 'Q@XAUUSD': 100, 'M@US30': 300};
  const BT_NOTE = {
    'T@US30': '外す候補：PF 1.20・最大 DD 23.6R と 19 本で一番弱い',
    'DS@JP225': '外す候補：PF 1.29 と弱め（ただし 20 万円から使える数少ない株価指数）',
    'A@EURUSD': '外す候補：PF 1.38・年 +1.4R と小さい',
    'C@EURUSD': 'PF 1.43 とやや弱いが回数が多く安定',
    'S@XAUUSD': 'ロット半分：ゴールドに 4 本（L2・S・Q・右肩）が集まるので、崩れた時にまとめて負けないように（全量なら年利 79→90%、DD は -19% のまま）',
    'Q@XAUUSD': 'ロット半分：S と同じ理由（ゴールドの集中を抑える）',
    'M@US30': '最小ロットのリスクが大きく、300 万円未満では見送りが多い',
    'R@EURUSD': '本番の最初のうちは研究と判定が少しずれることがある（過去の分布の準備中）',
    'DS@US500': '買いだけ（左肩の上に損切り・2R で利確）', 'DS@XAUUSD': '買いだけ・右肩の上に損切り（最小ロットのリスクを小さく）', 'S@BTCUSD': '買いだけ・土日は入らない',
    'C@USDJPY': '調整が長く傾きが強い時だけ', 'L2@XAUUSD': '伸びる先に壁がある時は見送り'};
  // portfolio combinations (RESEARCH_LOG §107 / §106: 1% risk, half at DD 10%, calendar x1.5, backtest as is)
  const COMBOS = [
    ['20 万円', '9 本', 'FX 7 本（ユーロドル R・T2・L・A・C、ドル円 C・J2）＋日経右肩＋BTC S', '+43%', '-18%', '約 100 回'],
    ['30 万円', '10 本', '上の 9 本＋US500 右肩', '+45%', '-17%', '約 102 回'],
    ['50 万円', '13 本', '＋US500 短い押し目・US30 トレンド・ゴールド L2', '+55%', '-19%', ''],
    ['60 万円', '16 本', '＋ゴールド右肩・銀 Q・US30 Q', '+69%', '-21%', ''],
    ['100 万円', '18 本', '＋ゴールド S・Q（ロット半分）', '+79%', '-19%', ''],
    ['300 万円', '19 本（全部）', '＋US30 短い押し目', '+80%', '-19%', ''],
  ];
  function comboTable() {
    const tr = c => `<tr style="border-bottom:1px solid #1e293b"><td style="text-align:left;padding:6px 4px;white-space:nowrap">${c[0]}</td><td style="white-space:nowrap">${c[1]}</td><td style="color:#4ade80">${c[3]}</td><td style="color:#f87171">${c[4]}</td></tr>
      <tr><td colspan="4" style="text-align:left;padding:0 4px 6px;font-size:10px;color:#94a3b8">${c[2]}${c[5] ? ' · 年 ' + c[5] : ''}</td></tr>`;
    return `<div style="font-size:12px;font-weight:700;color:#cbd5e1;margin:14px 0 4px">組み合わせの結果（口座の大きさごと）</div>
      <table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right">
        <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">口座</th><th>EA</th><th>年利</th><th>最大 DD</th></tr>${COMBOS.map(tr).join('')}</table>
      <div style="font-size:11px;color:#cbd5e1;margin-top:10px;line-height:1.6;background:#0f172a;border:1px solid #26364f;border-radius:8px;padding:8px 10px">
        <b>合計（19 本すべて・ゴールド S と Q は半分）</b>：年利 +79%・最大 DD -19%<br>ゴールド S・Q を全量にすると年利 +90%・最大 DD -19%（リスク 0.75% なら +58%・-16% ／ 全量 +65%・-17%）</div>
      <div style="font-size:10px;color:#64748b;margin-top:6px">条件：リスク 1%・DD10% で半分・月初 3 日とゴールドの金曜の買いは 1.5 倍。本番の目減り（滑りなど）は入っていない</div>`;
  }
  function btSection() {
    const rows = ALL_KEYS.slice().sort((a, b) => (MIN_ACC[a] - MIN_ACC[b]) || (BTX[b][7] - BTX[a][7])).map(k => {
      const x = BTX[k], weak = x[7] < 1.4;
      return `<div style="padding:8px 0;border-bottom:1px solid #1e293b">
        <div style="display:flex;justify-content:space-between;gap:8px;font-size:12px"><b>${esc(eaName(k))}</b><span style="color:#94a3b8;font-size:11px">${MIN_ACC[k]} 万円〜${weak ? ' · <span style="color:#f87171">外す候補</span>' : ''}</span></div>
        <div style="font-size:11px;color:#cbd5e1;margin-top:3px">${x[0]}〜${x[1]} · ${x[2]} 回（${x[3]} 勝 ${x[4]} 敗）· 勝率 ${x[5]}% · 平均 ${x[6]}R · PF ${x[7]} · 最大 DD ${x[8]}R · 年 ${x[9]} 回 / +${x[10]}R</div>
        ${BT_NOTE[k] ? `<div style="font-size:11px;color:#94a3b8;margin-top:2px">${esc(BT_NOTE[k])}</div>` : ''}</div>`;
    }).join('');
    return `<div class="ea-card" style="padding:8px 12px;margin-top:4px"><button onclick="eaLiveBT()" style="width:100%;display:flex;justify-content:space-between;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:12px;padding:2px 0">
      <span>📊 検証結果（どれを外すかの目安）</span><span style="color:#94a3b8">${S.btOpen ? '▲' : '▼'}</span></button>
      ${S.btOpen ? `<div style="font-size:10px;color:#64748b;margin:6px 0 2px;line-height:1.5">バックテスト（コスト込み・1 回 1R）。「◯万円〜」は最小ロットのリスクが口座の 1% 以下になる額。それより小さい口座では、最小ロットのリスクが 1.5% を超える回は自動で見送り。</div>${rows}${comboTable()}` : ''}</div>`;
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
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px"><span style="font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${card.title}</span><span style="font-size:10px;color:#94a3b8">${card.code}</span></div>
        <div style="font-size:11px;color:#cbd5e1;margin-top:5px;line-height:1.4;min-height:15px">${syms.length ? syms.join(' · ') : '銘柄なし'}</div>
        <div style="margin-top:6px"><span style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;color:${md[1]};background:rgba(${md[2]},.12)">${md[0]}</span></div></button>`;
    }).join('');
    const trades = ((S.dash && S.dash.trades) || []).filter(t => String(t.Account) === S.acc)
      .sort((x, y) => String(y.EntryTime || y.SignalTime).localeCompare(String(x.EntryTime || x.SignalTime))).slice(0, 15).map(t => {   // newest first
      const pr = Number(t.Profit), col = t.Status === 'OPEN' ? '#22d3ee' : pr > 0 ? '#4ade80' : pr < 0 ? '#f87171' : '#94a3b8';
      return `<div style="display:flex;justify-content:space-between;gap:8px;padding:8px 2px;border-bottom:1px solid #1e293b;font-size:12px">
        <div><b>${esc(t.EA)}</b> ${t.Direction === 'BUY' ? '買い' : '売り'}<div style="color:#94a3b8;font-size:11px">${esc(String(t.EntryTime).slice(5, 16))} · ${esc(t.Lot)} lot</div></div>
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
          <div style="display:flex;justify-content:space-between;gap:10px"><div><div style="font-size:16px;font-weight:800">${card.title} <span style="font-size:11px;color:#94a3b8">${card.code}</span></div>
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
        <div style="display:flex;align-items:center;gap:8px;${minLot ? 'opacity:.4' : ''}"><div style="min-width:80px;font-size:12px;color:#94a3b8">リスク</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px">${[0.005, 0.0075, 0.01, 0.0125].map(v =>
            `<button onclick="eaLiveRisk(${v})" style="${btn};${!minLot && Math.abs(c.base_risk - v) < 1e-9 ? neon('#22d3ee', '34,211,238') : offBtn}">${+(v * 100).toFixed(2)}%</button>`).join('')}</div></div>
        ${minLot ? '<div style="font-size:10px;color:#fbbf24;margin-top:-4px">全 EA が銘柄の最小ロット（例 0.01）で入ります。最小ロットでも損失が口座の 1.5% を超える回は見送り</div>' : ''}
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">DD10%で半分</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px">
            <button onclick="${c.dd_half === false ? 'eaLiveDDHalf()' : ''}" style="${btn};${c.dd_half !== false ? neon('#22d3ee', '34,211,238') : offBtn}">ON</button>
            <button onclick="${c.dd_half !== false ? 'eaLiveDDHalf()' : ''}" style="${btn};${c.dd_half === false ? neon('#f87171', '248,113,113') : offBtn}">OFF</button></div></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">通知</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${[['notifyEntry', 'Entry'], ['notifyExit', 'Exit'], ['notifyError', 'Error']].map(([k, l]) =>
            `<button onclick="eaLiveNotify('${k}')" style="${btn};${n[k] !== false ? neon('#22d3ee', '34,211,238') : offBtn}">${l}</button>`).join('')}</div></div>
        ${S.saving || S.err ? `<div style="font-size:11px;color:${/でき|失敗|通信/.test(S.saving + S.err) ? '#f87171' : '#94a3b8'}">${esc(S.saving || S.err)}</div>` : ''}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px"><div style="font-size:12px;font-weight:700;color:#94a3b8">EA 一覧</div><div style="display:flex;align-items:center;gap:8px"><span style="font-size:11px;color:#94a3b8">${onCount} / 19 が ON</span>${onCount < 19 ? `<button onclick="eaLiveAllOn()" style="${btn};${offBtn};padding:4px 9px;font-size:11px">すべて ON</button>` : ''}</div></div>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">${cards}</div>
      ${btSection()}
      ${resSection()}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-top:8px">EA のトレード（最近）</div>
      <div class="ea-card" style="padding:4px 12px">${trades}</div>
    </div>${sheet}${resSheet()}`;
  }


  // ---------- EA trades outside the EA tab: home (open), history (closed), analysis (per EA vs backtest), detail
  // Backtest per EA (research feat/final_trades.pkl, R after costs): trades, per year, win %, average R, PF, data from
  const BT = {"A@EURUSD":{"n":153,"py":7.1,"wr":43.1,"avgR":0.202,"pf":1.38,"since":"2005"},"C@EURUSD":{"n":321,"py":14.8,"wr":45.2,"avgR":0.218,"pf":1.43,"since":"2005"},"C@USDJPY":{"n":274,"py":12.6,"wr":43.1,"avgR":0.319,"pf":1.63,"since":"2005"},"DS@JP225":{"n":111,"py":11.4,"wr":40.5,"avgR":0.179,"pf":1.29,"since":"2017"},"DS@US500":{"n":46,"py":4.8,"wr":50.0,"avgR":0.293,"pf":1.51,"since":"2017"},"DS@XAUUSD":{"n":189,"py":9.0,"wr":49.2,"avgR":0.27,"pf":1.58,"since":"2005"},"J2@USDJPY":{"n":239,"py":11.0,"wr":38.9,"avgR":0.491,"pf":1.8,"since":"2005"},"L2@XAUUSD":{"n":218,"py":10.3,"wr":43.1,"avgR":0.355,"pf":1.68,"since":"2005"},"L@EURUSD":{"n":297,"py":13.8,"wr":41.8,"avgR":0.279,"pf":1.53,"since":"2005"},"M@US30":{"n":107,"py":9.9,"wr":73.8,"avgR":0.116,"pf":1.73,"since":"2015"},"M@US500":{"n":88,"py":9.7,"wr":76.1,"avgR":0.119,"pf":1.76,"since":"2017"},"Q@US30":{"n":109,"py":9.4,"wr":43.1,"avgR":0.295,"pf":1.55,"since":"2015"},"Q@XAGUSD":{"n":112,"py":5.4,"wr":35.7,"avgR":0.913,"pf":2.49,"since":"2005"},"Q@XAUUSD":{"n":727,"py":33.4,"wr":44.2,"avgR":0.189,"pf":1.72,"since":"2005"},"R@EURUSD":{"n":133,"py":6.3,"wr":47.4,"avgR":0.71,"pf":2.26,"since":"2005"},"S@BTCUSD":{"n":280,"py":30.3,"wr":35.0,"avgR":0.686,"pf":2.0,"since":"2017"},"S@XAUUSD":{"n":626,"py":29.0,"wr":37.7,"avgR":0.143,"pf":1.48,"since":"2005"},"T2@EURUSD":{"n":377,"py":17.4,"wr":41.1,"avgR":0.397,"pf":1.67,"since":"2005"},"T@US30":{"n":237,"py":21.4,"wr":36.7,"avgR":0.127,"pf":1.2,"since":"2015"}};
  const ACC_JA = {demo: 'デモ', live: '本番'};
  let V = {histAcc: 'demo', anAcc: 'demo'};
  function eaName(key) {
    if (/^RES:/.test(String(key || ''))) return '予約エントリー';
    const k = String(key || ''), card = CARDS.find(c => c.keys.some(x => x[0] === k));
    const sym = k.split('@')[1] || '';
    return card ? card.title + ' ' + sym : k;
  }
  const allTrades = () => ((S.dash && S.dash.trades) || []).filter(t => !/^RES:/.test(String(t.EA)));   // reservations are recorded as 裁量 trades (Trades)
  const dirJa = d => String(d).toUpperCase() === 'BUY' ? '買い' : '売り';
  const jst = v => esc(String(v || '').replace(/\+09:00$/, '').slice(5, 16));
  function tradeRow(t, onclick) {
    const open = t.Status === 'OPEN', pr = Number(t.Profit), col = open ? '#22d3ee' : pr > 0 ? '#4ade80' : pr < 0 ? '#f87171' : '#94a3b8';
    const R = t.R !== '' && t.R != null && !isNaN(t.R) ? (Number(t.R) > 0 ? '+' : '') + Number(t.R).toFixed(2) + 'R' : '';
    const line = String(t.Direction).toUpperCase() === 'BUY' ? '#f43f5e' : '#3b82f6';   // buy red / sell blue (same as 裁量)
    return `<div class="list-card" onclick="${onclick}" style="cursor:pointer;border-left:4px solid ${line}">
      <div style="flex:1"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <div style="font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px">${esc(t.Symbol)}
          <span class="badge ${String(t.Direction).toUpperCase() === 'BUY' ? 'buy' : 'sell'}">${String(t.Direction).toUpperCase() === 'BUY' ? '▲ Buy' : '▼ Sell'}</span>
          ${/^RES:/.test(String(t.EA)) ? '<span class="badge" style="background:rgba(34,211,238,.12);color:#22d3ee">予約</span>' : '<span class="badge" style="background:rgba(74,222,128,.12);color:#4ade80">EA</span>'}${String(t.Account) === 'live' ? '<span class="badge" style="background:rgba(248,113,113,.12);color:#f87171">本番</span>' : ''}</div>
        <div style="font-weight:700;font-size:15px;color:${col}">${open ? '' : R}</div></div>
        <div style="font-size:11px;color:#94a3b8;display:flex;justify-content:space-between"><span>${esc(eaName(t.EA))} · ${jst(t.EntryTime)}</span><span>${open ? esc(t.Lot) + ' lot' : yen(t.Profit)}</span></div></div>
      <div style="color:#94a3b8;font-size:16px;margin-left:12px">›</div></div>`;
  }
  const EA_PIP = sym => /JPY/.test(sym) ? 0.01 : /XAU/.test(sym) ? 0.1 : /XAG/.test(sym) ? 0.01 : /BTC|ETH|US30|US500|JP225/.test(sym) ? 1 : 0.0001;
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
    openTrades: () => allTrades().filter(t => t.Status === 'OPEN'),
    homeHtml: function () {
      const pos = allTrades().filter(t => t.Status === 'OPEN').slice().reverse().map(t => tradeRow(t, `eaLiveTrade('${esc(t.TradeID)}')`)).join('');
      const wait = resAll().filter(r => r.Status === 'WAIT');
      const res = wait.length ? `<div style="font-size:12px;font-weight:700;color:#94a3b8;margin:12px 0 6px">予約中</div><div class="ea-card" style="padding:4px 12px;margin-bottom:8px">${wait.map(r => resLine(r, false)).join('')}</div>` : '';
      return pos + res;
    },
    waitingCount: () => resAll().filter(r => r.Status === 'WAIT').length,
    historyHtml: function (f) {
      if (!appKey()) return '<div style="color:#94a3b8;text-align:center;padding:20px">EA 設定タブで合言葉を入れると、EA のトレードが出ます</div>';
      const tab = a => `<button class="toggle-btn ${V.histAcc === a ? 'active' : ''}" onclick="eaLiveHistAcc('${a}')" style="flex:1">${ACC_JA[a]}口座</button>`;
      let xs = allTrades().filter(t => String(t.Account) === V.histAcc && t.Status !== 'OPEN');
      const cardOf = k => /^RES:/.test(String(k)) ? 'RES' : ((CARDS.find(c => c.keys.some(x => x[0] === k)) || {}).id || '');
      const have = [...new Set(xs.map(t => cardOf(t.EA)))];
      const chip = (id, label) => `<button class="toggle-btn ${(V.histEA || '') === id ? 'active' : ''}" onclick="eaLiveHistEA('${id}')" style="flex:none;font-size:11px;padding:6px 10px;white-space:nowrap">${label}</button>`;
      const chips = `<div style="display:flex;gap:6px;overflow-x:auto;margin-bottom:10px;padding-bottom:2px">${chip('', 'すべて')}${CARDS.filter(c => have.includes(c.id)).map(c => chip(c.id, c.title)).join('')}${have.includes('RES') ? chip('RES', '予約') : ''}</div>`;
      if (V.histEA) xs = xs.filter(t => cardOf(t.EA) === V.histEA);
      xs = xs.filter(t => { const d = String(t.EntryTime || '').slice(0, 10); if (f && f.fPeriod === 'custom') { if (f.dFrom && d < f.dFrom) return false; if (f.dTo && d > f.dTo) return false; } return true; });
      const sumR = xs.reduce((a, t) => a + (Number(t.R) || 0), 0), sumP = xs.reduce((a, t) => a + (Number(t.Profit) || 0), 0), w = xs.filter(t => Number(t.R) > 0).length;
      const head = `<div style="display:flex;gap:6px;margin-bottom:10px">${tab('demo')}${tab('live')}</div>` + chips + (xs.length ? `<div style="font-size:12px;color:#94a3b8;margin-bottom:10px">${xs.length} 件 · 勝率 ${(w / xs.length * 100).toFixed(0)}% · 合計 ${(sumR > 0 ? '+' : '') + sumR.toFixed(1)}R · ${yen(sumP)}</div>` : '');
      return head + (xs.slice().reverse().map(t => tradeRow(t, `eaLiveTrade('${esc(t.TradeID)}')`)).join('') || '<div style="color:#64748b;text-align:center;padding:20px">決済した EA のトレードはまだありません</div>');
    },
    analysisHtml: function (kind) {
      if (!appKey()) return '';
      V.anAcc = (document.getElementById('flt-acc') || {}).value || V.anAcc;
      const xs = allTrades().filter(t => String(t.Account) === V.anAcc && t.Status === 'CLOSED');
      const by = {}; xs.forEach(t => (by[t.EA] = by[t.EA] || []).push(t));
      Object.keys(by).filter(k => /^RES:/.test(k)).forEach(k => delete by[k]);          // reservations have their own tab
      const keys = ALL_KEYS.slice();
      const num = (v, d) => v == null || isNaN(v) ? '—' : Number(v).toFixed(d);
      const rows = keys.map(k => {
        const g = by[k] || [], R = g.map(t => Number(t.R) || 0), n = g.length, w = R.filter(r => r > 0).length;
        const pos = R.filter(r => r > 0).reduce((a, b) => a + b, 0), neg = -R.filter(r => r < 0).reduce((a, b) => a + b, 0), b = BT[k] || {};
        const avg = n ? R.reduce((a, b) => a + b, 0) / n : null, low = n >= 10 && avg != null && b.avgR != null && avg < b.avgR - 0.5;
        return `<tr style="border-bottom:1px solid #1e293b"><td style="padding:6px 4px;text-align:left">${k === 'RES' ? '予約エントリー' : esc(eaName(k))}</td><td>${n}</td>
          <td>${n ? (w / n * 100).toFixed(0) + '%' : '—'}<div style="color:#64748b">${num(b.wr, 0)}%</div></td>
          <td style="color:${low ? '#f87171' : 'inherit'}">${num(avg, 2)}<div style="color:#64748b">${num(b.avgR, 2)}</div></td>
          <td>${neg > 0 ? (pos / neg).toFixed(2) : n ? '∞' : '—'}<div style="color:#64748b">${num(b.pf, 2)}</div></td>
          <td>${n ? (R.reduce((a, b) => a + b, 0) > 0 ? '+' : '') + R.reduce((a, b) => a + b, 0).toFixed(1) : '—'}<div style="color:#64748b">${num(b.py, 0)}回/年</div></td></tr>`;
      }).join('');
      return `<div class="section" style="margin-bottom:14px"><div class="section-title" style="margin-bottom:8px">🤖 EA ごとの成績（${ACC_JA[V.anAcc]}口座 · 実際 / <span style="color:#64748b">バックテスト</span>）</div>
        <div style="overflow-x:auto;margin-top:10px"><table style="width:100%;border-collapse:collapse;font-size:11px;text-align:right;white-space:nowrap">
          <tr style="color:#94a3b8;border-bottom:1px solid #334155"><th style="text-align:left;padding:4px">EA</th><th>回数</th><th>勝率</th><th>平均R</th><th>PF</th><th>合計R</th></tr>${rows}</table></div>
        <div style="font-size:10px;color:#64748b;margin-top:6px">下の灰色がバックテスト。10 回以上で平均 R がバックテストより 0.5R 以上低いと赤</div></div>`;
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
  window.eaLiveHistEA = id => { V.histEA = id; if (typeof renderHistoryList === 'function') renderHistoryList(); };
  window.eaLiveHistAcc = a => { V.histAcc = a; if (typeof renderHistoryList === 'function') renderHistoryList(); };
  window.eaLiveAnAcc = a => { V.anAcc = a; const an = document.getElementById('eal-analysis'); if (an) an.innerHTML = window.eaLive.analysisHtml(V.anKind); };
  window.eaLiveTrade = function (id) {
    const t = allTrades().find(x => String(x.TradeID) === String(id)); if (!t) return;
    const row = (l, v) => `<div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px solid #1e293b;font-size:13px"><span style="color:#94a3b8">${l}</span><span style="text-align:right;word-break:break-all">${v === '' || v == null ? '—' : v}</span></div>`;
    const old = document.getElementById('eal-trade-modal'); if (old) old.remove();
    const m = document.createElement('div'); m.id = 'eal-trade-modal'; m.className = 'modal-overlay active';
    m.onclick = e => { if (e.target === m) m.remove(); };
    m.innerHTML = `<div class="modal-content"><div class="modal-header"><div class="modal-title">${esc(eaName(t.EA))}</div><div class="modal-close" onclick="document.getElementById('eal-trade-modal').remove()">✕</div></div><div class="modal-body">
      ${row('口座', ACC_JA[t.Account] || esc(t.Account))}${row('銘柄・向き', esc(t.Symbol) + ' ' + dirJa(t.Direction))}${row('状態', t.Status === 'OPEN' ? '保有中' : '決済済み')}
      ${row('シグナルの足', jst(t.SignalTime))}${row('エントリー', jst(t.EntryTime) + ' @ ' + esc(t.EntryPrice))}${row('損切り', esc(t.SLPrice))}${row('利確', esc(t.TPPrice))}
      ${row('ロット', esc(t.Lot) + (t.LotMult && Number(t.LotMult) !== 1 ? '（倍率 ' + esc(t.LotMult) + '）' : '') + (t.Weight && Number(t.Weight) !== 1 ? '（重み ' + esc(t.Weight) + '）' : ''))}
      ${row('リスク', yen(t.RiskJPY))}${row('決済', t.ExitTime ? jst(t.ExitTime) + ' @ ' + esc(t.ExitPrice) : '')}${row('損益', t.Status === 'OPEN' ? '' : yen(t.Profit))}
      ${row('R', t.R !== '' && t.R != null ? Number(t.R).toFixed(2) : '')}${row('入った理由', esc(t.Reason))}${t.Note ? row('メモ', esc(t.Note)) : ''}${row('チケット', esc(t.Ticket))}
      <div style="font-size:11px;color:#64748b;margin-top:10px">時刻は日本時間。チャートは MT5 で見る</div></div></div>`;
    document.body.appendChild(m);
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
