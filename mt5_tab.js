// MT5 tab (2026-10-24, docs/EA_SYSTEM_PLAN.md "MT5 の取り込み"). Replaced the old import screen (mt5_import.js, removed 2026-10-25).
// The import runs from the PC's desktop button. Every imported trade comes here as a draft to check (2026-10-25): see what
// positions it holds, link it to a hand-written trade (candidates within the set hours) or record it, after a confirmation.
// 🗑️ moves a draft to the trash (restore / delete for good / empty the trash); recorded or linked trades can go back.
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
  const feat = () => (S.d && S.d.features) || {};          // what the deployed GAS can do (older GAS: no trash / undo)
  window.mt5Adopt = id => act('保存中…', 'eaImportAdopt', {entryId: id}, r => r.status === '決済' ? '記録にしました（決済）' : '記録にしました（保有中）');
  window.mt5Link = (d, e) => act('紐付け中…', 'eaImportLink', {draftId: d, entryId: e}, () => '手入力のトレードに紐付けました');
  window.mt5Split = id => act('分けています…', 'eaImportSplit', {draftId: id}, r => r.parts ? r.parts + ' つに分けました' : '分けるものがありません');
  window.mt5Discard = function (id) {
    if (feat().trash) return act('移しています…', 'eaImportDiscard', {draftId: id}, () => 'ゴミ箱に移しました（下の「ゴミ箱」から戻せます）');
    if (confirm('今の裏側（GAS）ではゴミ箱がまだ使えないため、消すと戻せず、同じ約定は次から出ません。消しますか？\n（次の GAS のデプロイからゴミ箱になります）'))
      act('削除中…', 'eaImportDiscard', {draftId: id}, () => '消しました');
  };
  window.mt5Restore = id => act('戻しています…', 'eaImportRestore', {ids: [id]}, () => '確認が必要なトレードに戻しました');
  window.mt5Purge = function (id) { if (confirm('このトレードを完全に消しますか？（戻せません。同じ約定は次の取り込みでも出ません）')) act('消しています…', 'eaImportPurge', {ids: [id]}, () => '完全に消しました'); };
  window.mt5PurgeAll = function () {
    const n = ((S.d && S.d.trash) || []).length; if (!n) return;
    if (confirm(`ゴミ箱の ${n} 件を全部、完全に消しますか？（戻せません）`)) act('消しています…', 'eaImportPurge', {all: true}, r => (r.purged || 0) + ' 件を完全に消しました');
  };
  window.mt5Unadopt = function (id) {
    const x = ((S.d && S.d.recent) || []).find(r => String(r.trade.EntryID) === String(id)), linked = x && x.trade.linked;
    if (confirm(linked ? 'この紐付けを外して、MT5 の分を「確認が必要なトレード」に戻しますか？（手入力のトレードは紐付ける前の値に戻ります）'
                       : 'このトレードを履歴から外して「確認が必要なトレード」に戻しますか？'))
      act('戻しています…', 'eaImportUnadopt', {entryId: id}, () => '確認が必要なトレードに戻しました');
  };
  // trade detail (app.js): any trade recorded or linked from the MT5 tab can go back, no time limit
  window.mt5UnadoptFromDetail = async function (id, linked) {
    if (!key()) { if (typeof showToast === 'function') showToast('EA 設定タブで合言葉を入れると使えます'); return false; }
    if (!confirm(linked ? 'この紐付けを外して、MT5 の分を「確認が必要なトレード」に戻しますか？（このトレードは紐付ける前の値に戻ります）'
                        : 'このトレードを履歴から外して、MT5 タブの「確認が必要なトレード」に戻しますか？')) return false;
    try {
      const r = await call('eaImportUnadopt', {entryId: id});
      if (!r || r.success === false) throw new Error((r && r.error) || '失敗');
      if (typeof showToast === 'function') showToast('確認が必要なトレードに戻しました');
      if (typeof loadData === 'function') try { loadData(); } catch (e) {}
      load(); return true;
    } catch (e) { if (typeof showToast === 'function') showToast('⚠️ できませんでした: ' + e.message); return false; }
  };
  window.mt5Exp = function (id) { S.exp = S.exp || {}; S.exp[id] = !S.exp[id]; render(); };

  // ---- confirmation sheet before 記録にする / 紐付け (shows what will be recorded, positions included)
  const findDraft = id => ((S.d && S.d.drafts) || []).find(x => String(x.trade.EntryID) === String(id));
  function confirmSheet(html, okLabel, onOk) {
    let el = document.getElementById('mt5-confirm');
    if (!el) { el = document.createElement('div'); el.id = 'mt5-confirm'; document.body.appendChild(el); }
    S.pending = onOk;
    el.innerHTML = `<div onclick="if(event.target===this)mt5ConfirmClose()" style="position:fixed;inset:0;z-index:400;background:rgba(2,6,23,.7);display:flex;align-items:flex-end;justify-content:center">
      <div style="width:100%;max-width:500px;max-height:80dvh;display:flex;flex-direction:column;background:#0f172a;border-radius:20px 20px 0 0;border-top:1px solid #26364f">
        <div style="padding:16px 16px 8px;overflow-y:auto;flex:1">${html}</div>
        <div style="display:flex;gap:8px;padding:10px 16px calc(12px + env(safe-area-inset-bottom));border-top:1px solid #1e293b">
          ${onOk ? `<button onclick="mt5ConfirmClose()" style="${btn};${off};flex:1;padding:12px">やめる</button>
          <button onclick="mt5ConfirmOk()" style="${btn};${neon('#4ade80', '74,222,128')};flex:2;padding:12px">${okLabel}</button>`
          : `<button onclick="mt5ConfirmClose()" style="${btn};${off};flex:1;padding:12px">${okLabel}</button>`}</div></div></div>`;
  }
  window.mt5ConfirmClose = function () { const el = document.getElementById('mt5-confirm'); if (el) el.innerHTML = ''; S.pending = null; };
  window.mt5ConfirmOk = function () { const f = S.pending; mt5ConfirmClose(); if (f) f(); };
  window.mt5AskAdopt = function (id) {
    const x = findDraft(id); if (!x) return;
    confirmSheet(`<div style="font-size:15px;font-weight:800;margin-bottom:8px">この内容で記録にしますか？</div>${summary(x.trade)}
      <div style="font-size:11px;color:#94a3b8;margin:10px 0 4px">まとめたポジション（${x.positions}）</div>${posList(x.executions)}
      <div style="font-size:11px;color:#64748b;margin-top:8px">記録にすると履歴に入ります。違っていたら MT5 タブの「最近記録にしたもの」から戻せます。</div>`,
      '記録にする', () => mt5Adopt(id));
  };
  window.mt5AskLink = function (d, e) {
    const x = findDraft(d); if (!x) return; const c = (x.candidates || []).find(k => String(k.EntryID) === String(e)) || appTrades().find(k => String(k.EntryID) === String(e)) || {};
    confirmSheet(`<div style="font-size:15px;font-weight:800;margin-bottom:8px">この手入力のトレードに紐付けますか？</div>
      <div style="font-size:12px;color:#cbd5e1;background:#111c30;border:1px solid #26364f;border-radius:10px;padding:8px 10px;margin-bottom:8px">手入力：${esc(String(c.EntryDate || '').slice(5))} ${esc(String(c.EntryTime || '').slice(0, 5))} ${c.Lot ? esc(c.Lot) + ' lot' : ''} ${c['損益'] !== '' && c['損益'] != null ? esc(yen(c['損益'])) : ''} ${c['ステータス'] === '保有中' ? '（保有中）' : ''}</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">MT5 の取引</div>${summary(x.trade)}
      <div style="font-size:11px;color:#94a3b8;margin:10px 0 4px">まとめたポジション（${x.positions}）</div>${posList(x.executions)}
      <div style="font-size:11px;color:#64748b;margin-top:8px">建値・ロット・決済・損益（空欄のみ）が MT5 の値になります。手で入れた損益・pips は上書きしません。違っていたら「最近記録にしたもの」から外せます。</div>`,
      '紐付ける', () => mt5Link(d, e));
  };

  // ---- pick any hand-written trade to link (2026-10-25): same pair and direction, the whole history, closest entry first
  const pairKey = p => { const s = String(p || '').toUpperCase().replace(/#|\.|CASH|MICRO/g, '').trim(); return {XAUUSD: 'GOLD', XAGUSD: 'SILVER'}[s] || s; };
  const appTrades = () => ((window.TradeApp && window.TradeApp.data && window.TradeApp.data.entries) || []);
  const entryMs = t => { const d = String(t.EntryDate || '').replace(/\//g, '-').slice(0, 10), m = String(t.EntryTime || '00:00').slice(0, 5); const x = new Date(d + 'T' + m + ':00+09:00'); return isNaN(x) ? 0 : x.getTime(); };
  function linkTargets(t) {
    const ms = entryMs(t), pk = pairKey(t['PairName（元）'] || t.PairName);
    return appTrades().filter(c => !c.Accounts && !c.LinkBackup && ['下書き', 'ゴミ箱', '決済（見逃し）', '保有中（見逃し）'].indexOf(String(c['ステータス'])) < 0
        && String(c.Source || '') !== '予約' && String(c.Direction) === String(t.Direction) && pairKey(c['PairName（元）'] || c.PairName) === pk)
      .sort((a, b) => Math.abs(entryMs(a) - ms) - Math.abs(entryMs(b) - ms));
  }
  window.mt5PickLink = function (id) {
    const x = findDraft(id); if (!x) return;
    const xs = linkTargets(x.trade), ms = entryMs(x.trade);
    const gap = c => { const h = Math.abs(entryMs(c) - ms) / 3600e3; return h < 48 ? Math.round(h) + ' 時間' : Math.round(h / 24) + ' 日'; };
    const rows = xs.map(c => { const cp = Number(c['損益']), money = c['損益'] !== '' && c['損益'] != null && !isNaN(cp) ? yen(cp) : '';
      return `<button onclick="mt5ConfirmClose();mt5AskLink('${esc(id)}','${esc(c.EntryID)}')" style="width:100%;text-align:left;background:#0b1424;border:1px solid #1e293b;border-radius:10px;padding:9px 10px;color:#e2e8f0;display:flex;justify-content:space-between;gap:8px;font-size:12px">
        <span>${esc(String(c.EntryDate || '').slice(0, 10))} ${esc(String(c.EntryTime || '').slice(0, 5))}${c.Lot ? ' · ' + esc(c.Lot) + ' lot' : ''}${c['ステータス'] === '保有中' ? ' · 保有中' : ''}<br><span style="color:#64748b;font-size:10px">エントリーの差 ${gap(c)}</span></span>
        <span style="color:${cp >= 0 ? '#4ade80' : '#f87171'};font-weight:700;white-space:nowrap">${esc(money)}</span></button>`; }).join('');
    confirmSheet(`<div style="font-size:15px;font-weight:800;margin-bottom:4px">紐付ける手入力のトレードを選ぶ</div>
      <div style="font-size:11px;color:#94a3b8;margin-bottom:10px">${esc(x.trade['PairName（元）'])} ${String(x.trade.Direction) === 'Buy' ? '買い' : '売り'} の手入力トレード（全期間・エントリーが近い順）。MT5 とまだ紐付いていないものだけ出ます</div>
      <div style="display:flex;flex-direction:column;gap:6px">${rows || '<div style="font-size:12px;color:#64748b">同じ通貨・向きの手入力トレードはありません</div>'}</div>`, '閉じる', null);
  };

  // ---- the positions inside a trade (from its MT5 executions)
  const fmtT = s => { s = String(s || ''); if (/T.*Z$/.test(s)) { const d = new Date(s); if (!isNaN(d)) return d.toLocaleString('ja-JP', {timeZone: 'Asia/Tokyo', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'}); } return s.replace(/\+09:00$/, '').slice(5, 16); };
  function positionsOf(ex) {
    const by = {};
    (ex || []).forEach(r => { const k = r.Account + ':' + r.PositionID; (by[k] = by[k] || []).push(r); });
    return Object.keys(by).map(k => {
      const rs = by[k], ins = rs.filter(r => r.InOut === 'IN' || r.InOut === 'INOUT'), outs = rs.filter(r => r.InOut === 'OUT' || r.InOut === 'OUT_BY');
      const vol = xs => xs.reduce((a, r) => a + Number(r.Volume || 0), 0), wavg = xs => vol(xs) ? xs.reduce((a, r) => a + Number(r.DealPrice) * Number(r.Volume), 0) / vol(xs) : null;
      const byT = (a, b) => String(a.DealTime) < String(b.DealTime) ? -1 : 1;
      return {account: rs[0].Account, pos: rs[0].PositionID, lot: Math.round(vol(ins) * 1e4) / 1e4, inT: (ins.slice().sort(byT)[0] || {}).DealTime, inP: wavg(ins),
              outT: (outs.slice().sort(byT).pop() || {}).DealTime, outP: wavg(outs), open: !(vol(ins) > 0 && vol(outs) >= vol(ins) - 1e-9),
              profit: rs.reduce((a, r) => a + Number(r.Profit || 0) + Number(r.Swap || 0) + Number(r.Commission || 0), 0)};
    }).sort((a, b) => String(a.inT) < String(b.inT) ? -1 : 1);
  }
  const px = v => v == null || v === '' || isNaN(v) ? '—' : Math.abs(Number(v)) >= 1e5 ? Math.round(Number(v)).toLocaleString() : String(Number(Number(v).toPrecision(6)));
  function posList(ex) {
    const ps = positionsOf(ex);
    if (!ps.length) return '<div style="font-size:11px;color:#64748b">約定がありません</div>';
    return `<div style="display:flex;flex-direction:column;gap:4px">${ps.map(p => `<div style="font-size:11px;color:#cbd5e1;background:#0b1424;border:1px solid #1e293b;border-radius:8px;padding:6px 8px;line-height:1.55">
      <div style="display:flex;justify-content:space-between"><span>口座 ${esc(p.account)} <span style="color:#64748b">#${esc(p.pos)}</span></span>
        <b style="color:${p.open ? '#22d3ee' : (p.profit >= 0 ? '#4ade80' : '#f87171')}">${p.open ? '保有中' : esc(yen(p.profit))}</b></div>
      <div style="color:#94a3b8">${esc(p.lot)} lot · ${esc(fmtT(p.inT))} @ ${esc(px(p.inP))}${p.open ? '' : ` → ${esc(fmtT(p.outT))} @ ${esc(px(p.outP))}`}</div></div>`).join('')}</div>`;
  }
  function summary(t) {
    const buy = String(t.Direction) === 'Buy', pr = Number(t['損益']);
    return `<div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;font-weight:800">
        <span>${esc(t['PairName（元）'])} <span class="badge ${buy ? 'buy' : 'sell'}">${buy ? '▲ Buy' : '▼ Sell'}</span></span>
        <span style="color:${t.ExitDate ? (pr >= 0 ? '#4ade80' : '#f87171') : '#22d3ee'}">${t.ExitDate ? esc(yen(pr)) : '保有中'}</span></div>
      <div style="font-size:11px;color:#94a3b8;margin-top:2px">${esc(String(t.EntryDate || '').slice(5))} ${esc(t.EntryTime || '')}${t.ExitDate ? ` → ${esc(String(t.ExitDate).slice(5))} ${esc(t.ExitTime || '')}` : ''} · ${esc(t.Lot)} lot${t['実取得pips'] !== '' && t['実取得pips'] != null ? ' · ' + esc(t['実取得pips']) + ' pips' : ''}</div>`;
  }
  window.mt5Sel = function (id) { S.sel[id] = !S.sel[id]; render(); };
  window.mt5Merge = function () {
    const ids = Object.keys(S.sel).filter(k => S.sel[k]);
    if (ids.length < 2) { S.msg = '2 つ以上選んでください'; return render(); }
    const kinds = new Set(ids.map(i => { const x = findDraft(i); return x ? pairKey(x.trade['PairName（元）']) + ' ' + x.trade.Direction : i; }));
    if (kinds.size > 1) { S.msg = '通貨か向きが違うものはまとめられません（' + [...kinds].join(' / ') + '）'; return render(); }
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
    const cands = (x.candidates || []).map(c => {
      const cp = Number(c['損益']), money = c['損益'] !== '' && c['損益'] != null && !isNaN(cp) ? ` ${yen(cp)}` : '';
      const st = c['ステータス'] === '保有中' ? ' 保有中' : '';
      return `<button onclick="mt5AskLink('${id}','${esc(c.EntryID)}')" style="${btn};${neon('#22d3ee', '34,211,238')};padding:6px 9px;font-size:11px">${esc(String(c.EntryDate).slice(5))} ${esc(String(c.EntryTime).slice(0, 5))} ${c.Lot ? esc(c.Lot) + 'lot' : ''}${esc(money)}${st} に紐付け</button>`;
    }).join('');
    const lh = (S.d && S.d.settings && S.d.settings.linkHours) || 3, exp = !!(S.exp && S.exp[t.EntryID]);
    return `<div style="border:1px solid ${S.sel[t.EntryID] ? '#22d3ee' : '#26364f'};border-radius:12px;padding:10px;background:#0f172a;display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <label style="display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px"><input type="checkbox" ${S.sel[t.EntryID] ? 'checked' : ''} onchange="mt5Sel('${id}')">
          ${esc(t['PairName（元）'])} <span class="badge ${buy ? 'buy' : 'sell'}">${buy ? '▲ Buy' : '▼ Sell'}</span></label>
        <div style="text-align:right;font-weight:800;color:${t.ExitDate ? (pr >= 0 ? '#4ade80' : '#f87171') : '#22d3ee'}">${t.ExitDate ? yen(pr) : '保有中'}<div style="font-size:11px;color:#94a3b8;font-weight:600">${t['実取得pips'] !== '' ? esc(t['実取得pips']) + ' pips' : ''}</div></div></div>
      <div style="font-size:11px;color:#94a3b8;line-height:1.6">${esc(String(t.EntryDate).slice(5))} ${esc(t.EntryTime)} @ ${esc(px(t.EntryPrice))}${t.ExitDate ? ` → ${esc(String(t.ExitDate).slice(5))} ${esc(t.ExitTime)} @ ${esc(px(t.ExitPrice))}` : ''}
        <br>${esc(t.Lot)} lot · ${accs.length} 口座 · ${x.positions} ポジション${String(t.MergeMode) === 'manual' ? ' · 手で直した' : ''}</div>
      <button onclick="mt5Exp('${id}')" style="align-self:flex-start;background:none;border:0;color:#22d3ee;font-size:11px;font-weight:700;padding:0">${exp ? '▲ 中身を閉じる' : `▼ 中身を見る（${x.positions} ポジション）`}</button>
      ${exp ? posList(x.executions) : ''}
      ${cands ? `<div style="display:flex;flex-wrap:wrap;gap:6px"><span style="font-size:11px;color:#94a3b8;align-self:center">手入力の候補（${esc(lh)} 時間以内）:</span>${cands}</div>`
              : `<div style="font-size:11px;color:#64748b">${esc(lh)} 時間以内の手入力のトレードはありません</div>`}
      <button onclick="mt5PickLink('${id}')" style="align-self:flex-start;background:none;border:0;color:#22d3ee;font-size:11px;font-weight:700;padding:0">ほかの手入力トレードを選んで紐付け ›</button>
      <div style="display:flex;gap:6px;justify-content:flex-end">
        ${x.positions > 1 ? `<button onclick="mt5Split('${id}')" style="${btn};${off}">分ける</button>` : ''}
        <button onclick="mt5Discard('${id}')" aria-label="ゴミ箱へ" style="${btn};border:1px solid rgba(248,113,113,.5);background:transparent;color:#f87171;padding:9px">🗑️</button>
        <button onclick="mt5AskAdopt('${id}')" style="${btn};${neon('#4ade80', '74,222,128')}">記録にする</button></div></div>`;
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
    const lastLine = last ? `${last.period ? '期間 ' + esc(last.period) + ' · ' : ''}更新 ${last.updated} · 下書き ${last.drafts}` : 'まだ取り込んでいません';
    const errs = last && last.errors && last.errors.length ? `<div style="font-size:11px;color:#f87171">${last.errors.map(esc).join('<br>')}</div>` : '';
    // read period (2026-10-25): the PC's importer reads it when its button is pressed
    const periodRow = () => {
      const m = st.readMode || 'continue', pb = (v, l) => `<button onclick="mt5Set('readMode','${v}')" style="${btn};flex:1;padding:8px 4px;font-size:11px;${m === v ? neon('#22d3ee', '34,211,238') : off}">${l}</button>`;
      const date = (k, v) => `<input type="date" value="${esc(v || '')}" onchange="mt5Set('${k}',this.value)" class="ea-input" style="flex:1;min-width:0;padding:7px 6px">`;
      return `<div style="display:flex;flex-direction:column;gap:6px"><span>読む期間（全口座）</span>
        <div style="display:flex;gap:6px">${pb('continue', '前回の続き')}${pb('days', '直近 N 日')}${pb('range', '日付を指定')}</div>
        ${m === 'days' ? `<div style="display:flex;align-items:center;gap:8px"><span style="flex:1">直近</span>
          <input type="number" min="1" max="365" value="${esc(st.readDays || 30)}" onchange="mt5Set('readDays',Math.min(365,Math.max(1,Math.round(Number(this.value))||30)))" class="ea-input" style="width:72px;text-align:center"> 日</div>` : ''}
        ${m === 'range' ? `<div style="display:flex;align-items:center;gap:6px">${date('readFrom', st.readFrom)}<span>〜</span>${date('readTo', st.readTo)}</div>
          <div style="font-size:10px;color:${st.readFrom ? '#64748b' : '#f87171'}">${st.readFrom ? '終了日を空にすると今日まで。終了日がある時は「前回の続き」の位置は進みません' : '開始日を入れてください（空のままだと前回の続きから読みます）'}</div>` : ''}
        ${m === 'continue' ? '<div style="font-size:10px;color:#64748b">口座ごとに前回の続きから（初めての口座は 90 日）</div>' : ''}</div>`;
    };
    const settings = `<div style="display:flex;flex-direction:column;gap:10px;font-size:12px;color:#cbd5e1">
      <div style="display:flex;align-items:center;gap:8px"><span style="flex:1">まとめる時間（同じ銘柄・向き）</span>
        <input type="number" min="1" max="168" value="${esc(st.groupHours)}" onchange="mt5Set('groupHours',Number(this.value)||24)" class="ea-input" style="width:72px;text-align:center"> 時間</div>
      <div style="display:flex;align-items:center;gap:8px"><span style="flex:1">口座をまたいでまとめる</span>
        <button onclick="mt5Set('mergeAcross',${st.mergeAcross === false})" style="${btn};${st.mergeAcross !== false ? neon('#22d3ee', '34,211,238') : off}">${st.mergeAcross !== false ? 'ON' : 'OFF'}</button></div>
      ${feat().linkHours ? `<div style="display:flex;align-items:center;gap:8px"><span style="flex:1">紐付けの候補にする時間（エントリーの差）</span>
        <input type="number" min="1" max="72" value="${esc(st.linkHours || 3)}" onchange="mt5Set('linkHours',Math.min(72,Math.max(1,Number(this.value)||3)))" class="ea-input" style="width:72px;text-align:center"> 時間</div>` : ''}
      ${feat().readPeriod ? periodRow() : ''}
      <div style="font-size:10px;color:#64748b">設定は次の取り込みから使われます。過去 90 日を読み直す時は PC の「MT5 取り込み 90日読み直し」ボタン（同じ約定は増えません）。EA 用の口座は自動で記録するので対象外です。</div></div>`;
    const accBody = accs.length ? accs.map(([login, a]) => `<div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #1e293b">
      <span>${esc(a.label || login)}<span style="color:#64748b;font-size:10px"> ${esc(login)}</span></span><span style="color:#94a3b8">${esc(String(a.last || '').slice(5, 16)) || '—'} · ${esc(a.deals)} 件</span></div>`).join('')
      : '<div style="font-size:12px;color:#94a3b8">まだありません（PC の import_accounts.json に口座を書きます）</div>';
    const ea = d.eaStatus || {};
    const trash = d.trash || [], recent = d.recent || [];
    const miniRow = (x, buttons) => `<div style="border-bottom:1px solid #1e293b;padding:8px 0;display:flex;flex-direction:column;gap:6px">${summary(x.trade)}
      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px"><span style="font-size:10px;color:#64748b">${x.positions} ポジション${x.trade.Accounts ? ' · ' + esc(String(x.trade.Accounts).split(',').length) + ' 口座' : ''}</span>
        <span style="display:flex;gap:6px">${buttons}</span></div></div>`;
    const trashBody = trash.length ? `<div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#94a3b8;margin-bottom:4px">
        <span>完全に消すと戻せません（同じ約定は次の取り込みでも出ません）</span>
        <button onclick="mt5PurgeAll()" style="${btn};border:1px solid rgba(248,113,113,.5);background:transparent;color:#f87171;padding:6px 9px;font-size:11px;white-space:nowrap">ゴミ箱を空にする</button></div>`
        + trash.map(x => { const i = esc(x.trade.EntryID); return miniRow(x, `<button onclick="mt5Restore('${i}')" style="${btn};${neon('#22d3ee', '34,211,238')};padding:6px 9px;font-size:11px">戻す</button>
          <button onclick="mt5Purge('${i}')" style="${btn};border:1px solid rgba(248,113,113,.5);background:transparent;color:#f87171;padding:6px 9px;font-size:11px">完全に消す</button>`); }).join('')
      : '<div style="font-size:12px;color:#94a3b8">ゴミ箱は空です</div>';
    const recentBody = recent.length ? recent.map(x => { const i = esc(x.trade.EntryID);
        return miniRow(x, `<span style="font-size:10px;color:#94a3b8;align-self:center">${x.trade.linked ? '紐付け' : '記録'} ${esc(String(x.trade.linked ? x.trade.LinkedAt : x.trade.AdoptedAt).slice(5, 16))}</span>
          <button onclick="mt5Unadopt('${i}')" style="${btn};${off};padding:6px 9px;font-size:11px">確認待ちに戻す</button>`); }).join('')
      : '<div style="font-size:12px;color:#94a3b8">ありません</div>';
    root.innerHTML =`<div class="section" style="display:flex;flex-direction:column;gap:10px">
      <div class="ea-card" style="padding:16px;display:flex;flex-direction:column;gap:14px">
        <div><div style="font-size:15px;font-weight:800">🖥️ MT5 の取り込み</div>
          <div style="font-size:11px;color:#94a3b8;margin-top:4px;line-height:1.6">裁量の口座の約定を読みます。取り込んだトレードは全部、下の「確認が必要なトレード」に入ります。同じペア・向きでエントリーが 3 時間以内の手入力のトレード（保有中・決済済みとも）が候補に出るので、紐付けるか、そのまま記録にします。</div></div>
        ${tiles}
        <div style="font-size:12px;color:#cbd5e1;background:#0f172a;border:1px solid #26364f;border-radius:10px;padding:10px 12px;line-height:1.6">
          取り込みは <b>PC のデスクトップの「取り込み」ボタン</b>で動かします（EA を止めていても動きます）。終わったらこの画面を開き直すと結果が出ます。</div>
        <div style="font-size:11px;color:#64748b">${lastLine}</div>${errs}
        ${S.msg ? `<div style="font-size:12px;color:${/でき|失敗|通信/.test(S.msg) ? '#f87171' : '#cbd5e1'}">${esc(S.msg)}</div>` : ''}
      </div>
      <div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:12px;font-weight:700;color:#94a3b8">確認が必要なトレード（${drafts.length}）</div>
        ${drafts.length > 1 ? `<button onclick="mt5Merge()" style="${btn};${off};padding:6px 10px">選んだものをまとめる</button>` : ''}</div>
      ${drafts.length ? drafts.map(draftCard).join('') : '<div class="ea-card" style="font-size:12px;color:#94a3b8;text-align:center;padding:18px">確認が必要なトレードはありません ✅</div>'}
      ${feat().unadopt ? section('recent', `最近記録にしたもの（${14} 日）`, recentBody, recent.length + ' 件') : ''}
      ${feat().trash ? section('trash', '🗑️ ゴミ箱', trashBody, trash.length + ' 件') : ''}
      ${section('acc', '口座ごとの取り込み', accBody, accs.length + ' 口座')}
      ${section('set', '取り込みの設定', settings)}
      <div class="ea-card" style="padding:10px 12px;font-size:12px;color:#94a3b8;display:flex;justify-content:space-between"><span>EA 口座の最後の記録</span>
        <span>デモ ${ea.demo ? esc(String(ea.demo).slice(5, 16)) : '—'} · 本番 ${ea.live ? esc(String(ea.live).slice(5, 16)) : '—'}</span></div>
    </div>`;
  }
  window.renderMT5Import = function () { render(); load(); };
  window.mt5TabReload = load;
})();
