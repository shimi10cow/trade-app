// MT5 tab (2026-10-24, docs/EA_SYSTEM_PLAN.md "MT5 の取り込み"). Replaces the old import screen (mt5_import.js keeps its other helpers).
// One button asks the EA PC to import (picked up with its next 5-minute heartbeat); the PC reads every account's MT5 copy,
// merges split positions and sends the result. Trades without a hand-written match come back as drafts to check here.
// Backend: GAS Trades.gs through EA_Live.gs (eaImport*), app key from the EA tab.
(function () {
  const KEY_LS = 'eaLiveAppKey_v1', CACHE_LS = 'mt5TabCache_v1', OPEN_LS = 'mt5TabOpen_v1';
  let S = {d: null, busy: '', msg: '', sel: {}, open: {}};
  try { S.d = JSON.parse(localStorage.getItem(CACHE_LS) || 'null'); } catch (e) {}
  try { S.open = JSON.parse(localStorage.getItem(OPEN_LS) || '{}'); } catch (e) {}
  const key = () => localStorage.getItem(KEY_LS) || '';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const yen = v => (v === '' || v == null || isNaN(v)) ? '—' : (Number(v) < 0 ? '-¥' : '¥') + Math.abs(Math.round(Number(v))).toLocaleString();
  const neon = (c, rgb) => `border:1px solid ${c};background:rgba(${rgb},.10);color:${c};box-shadow:0 0 10px rgba(${rgb},.25)`;
  const off = 'border:1px solid #334155;background:#172033;color:#94a3b8';
  const btn = 'border-radius:8px;padding:9px 10px;font-weight:700;font-size:12px';

  async function call(action, body) {
    return fetch(GAS_URL, {method: 'POST', body: JSON.stringify(Object.assign({action: action, key: key()}, body || {}))}).then(x => x.json());
  }
  async function load() {
    if (!key()) return render();
    try {
      const r = await fetch(GAS_URL + '?action=eaImportStatus&key=' + encodeURIComponent(key())).then(x => x.json());
      if (r && r.success !== false) { S.d = r; S.msg = ''; try { localStorage.setItem(CACHE_LS, JSON.stringify(r)); } catch (e) {} }
      else S.msg = (r && r.error) || '読み込めませんでした';
    } catch (e) { S.msg = '通信できません（前回の表示）'; }
    render();
  }
  async function act(label, action, body, after) {
    S.busy = label; render();
    try {
      const r = await call(action, body);
      if (!r || r.success === false) throw new Error((r && r.error) || '失敗');
      S.msg = after ? after(r) : '';
      if (typeof loadData === 'function') try { loadData(); } catch (e) {}
    } catch (e) { S.msg = 'できませんでした: ' + e.message; }
    S.busy = ''; await load();
  }

  window.mt5Toggle = function (k) { S.open[k] = !S.open[k]; try { localStorage.setItem(OPEN_LS, JSON.stringify(S.open)); } catch (e) {} render(); };
  window.mt5Set = function (k, v) {
    S.d = S.d || {}; S.d.settings = Object.assign({groupHours: 24, mergeAcross: true}, S.d.settings || {}, {[k]: v});
    act('保存中…', 'eaImportSaveSettings', S.d.settings, () => '設定を保存しました（次の取り込みから使われます）');
  };
  window.mt5Adopt = id => act('保存中…', 'eaImportAdopt', {entryId: id}, r => r.status === '決済' ? '記録にしました（決済）' : '記録にしました（保有中）');
  window.mt5Link = (d, e) => act('紐付け中…', 'eaImportLink', {draftId: d, entryId: e}, () => '手入力のトレードに紐付けました');
  window.mt5Split = id => act('分けています…', 'eaImportSplit', {draftId: id}, r => r.parts ? r.parts + ' つに分けました' : '分けるものがありません');
  window.mt5Discard = function (id) { if (confirm('この下書きを消しますか？（同じ約定は次から出ません）')) act('削除中…', 'eaImportDiscard', {draftId: id}, () => '消しました'); };
  window.mt5Sel = function (id) { S.sel[id] = !S.sel[id]; render(); };
  window.mt5Merge = function () {
    const ids = Object.keys(S.sel).filter(k => S.sel[k]);
    if (ids.length < 2) { S.msg = '2 つ以上選んでください'; return render(); }
    S.sel = {}; act('まとめています…', 'eaImportMerge', {ids: ids}, () => ids.length + ' つを 1 つにまとめました');
  };

  function section(k, title, body, extra) {
    const o = !!S.open[k];
    return `<div class="ea-card" style="padding:10px 12px"><button onclick="mt5Toggle('${k}')" style="width:100%;display:flex;justify-content:space-between;align-items:center;background:none;border:0;color:#cbd5e1;font-weight:700;font-size:13px;padding:2px 0">
      <span>${title}</span><span style="color:#94a3b8;font-size:11px">${extra || ''} ${o ? '▲' : '▼'}</span></button>${o ? `<div style="margin-top:8px">${body}</div>` : ''}</div>`;
  }
  function draftCard(x) {
    const t = x.trade, buy = String(t.Direction) === 'Buy', id = esc(t.EntryID), pr = Number(t['損益']);
    const accs = String(t.Accounts || '').split(',').filter(String);
    const cands = (x.candidates || []).map(c => `<button onclick="mt5Link('${id}','${esc(c.EntryID)}')" style="${btn};${neon('#22d3ee', '34,211,238')};padding:6px 9px;font-size:11px">${esc(String(c.EntryDate).slice(5))} ${esc(String(c.EntryTime).slice(0, 5))} ${c.Lot ? esc(c.Lot) + 'lot' : ''} に紐付け</button>`).join('');
    return `<div style="border:1px solid ${S.sel[t.EntryID] ? '#22d3ee' : '#26364f'};border-radius:12px;padding:10px;background:#0f172a;display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <label style="display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px"><input type="checkbox" ${S.sel[t.EntryID] ? 'checked' : ''} onchange="mt5Sel('${id}')">
          ${esc(t['PairName（元）'])} <span class="badge ${buy ? 'buy' : 'sell'}">${buy ? '▲ Buy' : '▼ Sell'}</span></label>
        <div style="text-align:right;font-weight:800;color:${t.ExitDate ? (pr >= 0 ? '#4ade80' : '#f87171') : '#22d3ee'}">${t.ExitDate ? yen(pr) : '保有中'}<div style="font-size:11px;color:#94a3b8;font-weight:600">${t['実取得pips'] !== '' ? esc(t['実取得pips']) + ' pips' : ''}</div></div></div>
      <div style="font-size:11px;color:#94a3b8;line-height:1.6">${esc(String(t.EntryDate).slice(5))} ${esc(t.EntryTime)} @ ${esc(Number(t.EntryPrice).toPrecision(6))}${t.ExitDate ? ` → ${esc(String(t.ExitDate).slice(5))} ${esc(t.ExitTime)} @ ${esc(Number(t.ExitPrice).toPrecision(6))}` : ''}
        <br>${esc(t.Lot)} lot · ${accs.length} 口座 · ${x.positions} ポジション${String(t.MergeMode) === 'manual' ? ' · 手で直した' : ''}</div>
      ${cands ? `<div style="display:flex;flex-wrap:wrap;gap:6px"><span style="font-size:11px;color:#94a3b8;align-self:center">手入力の候補:</span>${cands}</div>` : ''}
      <div style="display:flex;gap:6px;justify-content:flex-end">
        ${x.positions > 1 ? `<button onclick="mt5Split('${id}')" style="${btn};${off}">分ける</button>` : ''}
        <button onclick="mt5Discard('${id}')" aria-label="消す" style="${btn};border:1px solid rgba(248,113,113,.5);background:transparent;color:#f87171;padding:9px">🗑️</button>
        <button onclick="mt5Adopt('${id}')" style="${btn};${neon('#4ade80', '74,222,128')}">記録にする</button></div></div>`;
  }
  function render() {
    const root = document.getElementById('mt5-import-root'); if (!root) return;
    if (!key()) {
      root.innerHTML = `<div class="section"><div class="ea-card" style="font-size:13px;color:#cbd5e1">EA 設定タブで合言葉を入れると使えます。</div></div>`;
      return;
    }
    const d = S.d || {}, st = d.settings || {groupHours: 24, mergeAcross: true}, last = (d.status && d.status.last) || null, req = d.request;
    const accs = Object.entries((d.status && d.status.accounts) || {});
    const drafts = d.drafts || [];
    const tile = (label, val, col) => `<div style="background:#0f172a;border:1px solid #1e293b;border-radius:10px;padding:10px 6px;text-align:center"><div style="font-size:10px;color:#94a3b8">${label}</div><div style="font-size:16px;font-weight:800;margin-top:4px;color:${col || '#f8fafc'}">${val}</div></div>`;
    const tiles = `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">${tile('前回', last ? esc(String(last.at).slice(5, 16)) : '—')}${tile('新しい約定', last ? last.executionsNew : '—')}${tile('確認待ち', drafts.length, drafts.length ? '#22d3ee' : '')}</div>`;
    const lastLine = last ? `更新 ${last.updated} · 紐付け ${last.linked} · 下書き ${last.drafts}` : 'まだ取り込んでいません';
    const errs = last && last.errors && last.errors.length ? `<div style="font-size:11px;color:#f87171">${last.errors.map(esc).join('<br>')}</div>` : '';
    const settings = `<div style="display:flex;flex-direction:column;gap:10px;font-size:12px;color:#cbd5e1">
      <div style="display:flex;align-items:center;gap:8px"><span style="flex:1">まとめる時間（同じ銘柄・向き）</span>
        <input type="number" min="1" max="168" value="${esc(st.groupHours)}" onchange="mt5Set('groupHours',Number(this.value)||24)" class="ea-input" style="width:72px;text-align:center"> 時間</div>
      <div style="display:flex;align-items:center;gap:8px"><span style="flex:1">口座をまたいでまとめる</span>
        <button onclick="mt5Set('mergeAcross',${st.mergeAcross === false})" style="${btn};${st.mergeAcross !== false ? neon('#22d3ee', '34,211,238') : off}">${st.mergeAcross !== false ? 'ON' : 'OFF'}</button></div>
      <div style="font-size:10px;color:#64748b">設定は次の取り込みから使われます。過去 90 日を読み直す時は PC で「--reread90」を付けて実行。EA 用の口座は自動で記録するので対象外です。</div></div>`;
    const accBody = accs.length ? accs.map(([login, a]) => `<div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #1e293b">
      <span>${esc(a.label || login)}<span style="color:#64748b;font-size:10px"> ${esc(login)}</span></span><span style="color:#94a3b8">${esc(String(a.last || '').slice(5, 16)) || '—'} · ${esc(a.deals)} 件</span></div>`).join('')
      : '<div style="font-size:12px;color:#94a3b8">まだありません（PC の import_accounts.json に口座を書きます）</div>';
    const ea = d.eaStatus || {};
    root.innerHTML = `<div class="section" style="display:flex;flex-direction:column;gap:10px">
      <div class="ea-card" style="padding:16px;display:flex;flex-direction:column;gap:14px">
        <div><div style="font-size:15px;font-weight:800">🖥️ MT5 の取り込み</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:4px;line-height:1.6">裁量の口座の約定を読み、手入力のトレードに紐付けます。合わないものは下の「確認が必要なトレード」で確認します。</div></div>
        ${tiles}
        <div style="font-size:12px;color:#cbd5e1;background:#0f172a;border:1px solid #26364f;border-radius:10px;padding:10px 12px;line-height:1.6">
          取り込みは <b>PC のデスクトップの「取り込み」ボタン</b>で動かします（EA を止めていても動きます）。終わったらこの画面を開き直すと結果が出ます。</div>
        <div style="font-size:11px;color:#64748b">${lastLine}</div>${errs}
        ${S.msg ? `<div style="font-size:12px;color:${/でき|失敗|通信/.test(S.msg) ? '#f87171' : '#cbd5e1'}">${esc(S.msg)}</div>` : ''}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:12px;font-weight:700;color:#94a3b8">確認が必要なトレード（${drafts.length}）</div>
        ${drafts.length > 1 ? `<button onclick="mt5Merge()" style="${btn};${off};padding:6px 10px">選んだものをまとめる</button>` : ''}</div>
      ${drafts.length ? drafts.map(draftCard).join('') : '<div class="ea-card" style="font-size:12px;color:#94a3b8;text-align:center;padding:18px">確認が必要なトレードはありません ✅</div>'}
      ${section('acc', '口座ごとの取り込み', accBody, accs.length + ' 口座')}
      ${section('set', '取り込みの設定', settings)}
      <div class="ea-card" style="padding:10px 12px;font-size:12px;color:#94a3b8;display:flex;justify-content:space-between"><span>EA 口座の最後の記録</span>
        <span>デモ ${ea.demo ? esc(String(ea.demo).slice(5, 16)) : '—'} · 本番 ${ea.live ? esc(String(ea.live).slice(5, 16)) : '—'}</span></div>
    </div>`;
  }
  window.renderMT5Import = function () { render(); load(); };
  window.mt5TabReload = load;
})();
