// EA settings tab for the new live EAs (2026-10-24, docs/EA_SYSTEM_PLAN.md, mockup artifact 1SGsxraBBzz7PbVN9npFTB).
// Replaces only window.renderEA from ea.js (the old per-pair screen); everything else in ea.js keeps working.
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
  let S = {acc: localStorage.getItem(ACC_LS) || 'demo', dash: null, sheet: null, saving: '', err: ''};
  try { S.dash = JSON.parse(localStorage.getItem(CACHE_LS) || 'null'); } catch (e) {}

  function defaultConfig(acc) {
    const eas = {};
    ALL_KEYS.forEach(k => eas[k] = {mode: 'auto', on: acc === 'demo' ? true : LIVE_ON.includes(k), weight: HALF[k] ? 0.5 : 1});
    return {running: false, base_risk: 0.01, notify: {notifyEntry: true, notifyExit: true, notifyError: true, notifySignal: true}, eas: eas};
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
  const yen = v => (v === '' || v == null || isNaN(v)) ? '—' : '¥' + Math.round(Number(v)).toLocaleString();

  async function load() {
    if (!appKey()) return;
    try {
      const r = await fetch(GAS_URL + '?action=eaGetDashboard&key=' + encodeURIComponent(appKey()) + '&limit=200').then(x => x.json());
      if (r && r.success === false) { S.err = r.error || '読み込みに失敗'; render(); return; }
      S.dash = r; S.err = ''; try { localStorage.setItem(CACHE_LS, JSON.stringify(r)); } catch (e) {}
    } catch (e) { S.err = '通信できません（前回の表示）'; }
    render();
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
  window.eaLiveRisk = function (v) { const c = cfg(); c.base_risk = Number(v); save(); };
  window.eaLiveNotify = function (k) { const c = cfg(); c.notify = c.notify || {}; c.notify[k] = c.notify[k] === false; save(); };
  window.eaLiveOpen = function (id) { S.sheet = id; render(); };
  window.eaLiveClose = function () { S.sheet = null; render(); };
  window.eaLiveMode = function (id, mode) { const c = cfg(); CARDS.find(x => x.id === id).keys.forEach(k => c.eas[k[0]].mode = mode); save(); };
  window.eaLiveSym = function (key) { const c = cfg(); c.eas[key].on = !c.eas[key].on; save(); };
  window.eaLiveWeight = function (key, w) { const c = cfg(); c.eas[key].weight = w; save(); };

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
    const c = cfg(), st = (S.dash && S.dash.status && S.dash.status[S.acc]) || {}, live = S.acc === 'live';
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
    const trades = ((S.dash && S.dash.trades) || []).filter(t => String(t.Account) === S.acc).slice(-15).reverse().map(t => {
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
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">普段のリスク</div>
          <select onchange="eaLiveRisk(this.value)" class="ea-input" style="flex:1">${[0.005, 0.0075, 0.01, 0.0125].map(v => `<option value="${v}" ${Math.abs(c.base_risk - v) < 1e-9 ? 'selected' : ''}>${(v * 100).toFixed(v === 0.0075 ? 2 : v === 0.0125 ? 2 : 1)} %（DD 10% で半分）</option>`).join('')}</select></div>
        <div style="display:flex;align-items:center;gap:8px"><div style="min-width:80px;font-size:12px;color:#94a3b8">通知</div>
          <div style="flex:1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${[['notifyEntry', 'Entry'], ['notifyExit', 'Exit'], ['notifyError', 'Error']].map(([k, l]) =>
            `<button onclick="eaLiveNotify('${k}')" style="${btn};${n[k] !== false ? neon('#22d3ee', '34,211,238') : offBtn}">${l}</button>`).join('')}</div></div>
        ${S.saving || S.err ? `<div style="font-size:11px;color:${/でき|失敗|通信/.test(S.saving + S.err) ? '#f87171' : '#94a3b8'}">${esc(S.saving || S.err)}</div>` : ''}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px"><div style="font-size:12px;font-weight:700;color:#94a3b8">EA 一覧</div><div style="font-size:11px;color:#94a3b8">${onCount} / 19 が ON</div></div>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px">${cards}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-top:8px">EA のトレード（最近）</div>
      <div class="ea-card" style="padding:4px 12px">${trades}</div>
    </div>${sheet}`;
  }

  const prev = window.renderEA;
  window.renderEA = function () { render(); if (!S._loadedAt || Date.now() - S._loadedAt > 60000) { S._loadedAt = Date.now(); load(); } };
  window.renderEALegacy = prev;          // the old per-pair screen stays reachable for comparison
})();
