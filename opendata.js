/* 📊 オープンデータ（OANDA のオープンオーダー・オープンポジションのスクショをためる）2026-11-22
 * OANDA's order / position book has no history and may not be fetched automatically, so the trader saves screenshots when there is
 * time. Pick one or many images: each is saved as its own row, nothing else to fill in (pair and time are read from the image later;
 * reader prototype: research/studies/orderbook/ob_read.py).
 * Stored in the Ideas sheet, category 'オープンデータ', through the existing saveIdea / deleteIdea (no GAS change).
 * Images are uploaded larger than usual (long side up to 2600 px, JPEG 0.92) so the bar lengths stay measurable.
 */
(function () {
  const CAT = 'オープンデータ';
  const st = {q: [], running: 0, delAsk: '', ok: 0, ng: 0};      // q: screenshots waiting / being saved in the background (2026-11-22)
  const WORKERS = 2;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const rows = () => ((typeof App !== 'undefined' && App.data && App.data.ideas) || []).filter(i => i['カテゴリ'] === CAT)
    .slice().sort((a, b) => String(b['日付'] || '').localeCompare(String(a['日付'] || '')) || String(b.id).localeCompare(String(a.id)));
  const jst = () => { const d = new Date(Date.now() + 9 * 3600e3), p = n => String(n).padStart(2, '0');
    return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`; };
  const src = (u, w) => (typeof getImageUrl === 'function' && !String(u).startsWith('data:')) ? getImageUrl(u, w) : u;

  function body() {
    const xs = rows();
    const wait = st.q.map(w => `<div style="position:relative"><img src="${esc(w.data)}" style="width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:8px;border:1px dashed #f59e0b;opacity:.55;display:block">
        <div style="font-size:10px;color:${w.err ? '#f87171' : '#fbbf24'};margin-top:2px">${w.err ? '⚠️ 保存できず' : w.busy ? '⏳ 保存中' : '⏳ 待ち'}</div>
        ${w.err ? `<button type="button" onclick="odRetry('${w.id}')" style="position:absolute;top:3px;right:3px;border:0;border-radius:6px;padding:2px 6px;font-size:11px;background:#7f1d1d;color:#fff">もう一度</button>` : ''}</div>`).join('');
    const grid = xs.map(x => {
      const u = x['画像URL'], ask = st.delAsk === String(x.id);
      return `<div style="position:relative">
        <img src="${esc(src(u, 400))}" referrerpolicy="no-referrer" loading="lazy" onclick="odOpen('${esc(x.id)}')"
          style="width:100%;aspect-ratio:3/4;object-fit:cover;border-radius:8px;border:1px solid #334155;cursor:zoom-in;display:block">
        <div style="font-size:10px;color:#94a3b8;margin-top:2px">${esc(String(x['日付'] || '').replace(/^\d{4}-/, ''))}</div>
        <button type="button" onclick="odDelete('${esc(x.id)}')" style="position:absolute;top:3px;right:3px;border:0;border-radius:6px;padding:2px 6px;font-size:11px;
          background:${ask ? '#7f1d1d' : 'rgba(15,23,42,.8)'};color:#f87171">${ask ? 'もう一度で削除' : '✕'}</button></div>`;
    }).join('');
    return `<div style="font-size:12px;color:#94a3b8;line-height:1.6;margin-bottom:10px">OANDA のオープンオーダー・オープンポジションの画面のスクショを選ぶだけで保存します（何枚でもまとめて選べます）。通貨や時刻はあとで画像から読み取ります。</div>
      <input type="file" id="od-file" accept="image/*" multiple style="display:none" onchange="odAdd(event)">
      <button type="button" class="btn-primary" onclick="document.getElementById('od-file').click()" style="width:100%;padding:14px;font-size:15px">📷 スクショを選ぶ</button>
      ${st.q.length ? `<div style="font-size:12px;color:#fbbf24;margin-top:8px">⏳ 裏で保存中：のこり ${st.q.filter(w => !w.err).length} 枚。この画面を閉じても、ほかのページに移っても続きます（アプリ自体は閉じないでください）</div>` : ''}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:16px 0 6px">ためたもの（${xs.length} 枚${st.q.length ? ` ＋ 保存中 ${st.q.length} 枚` : ''}）</div>
      ${xs.length || st.q.length ? `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">${wait}${grid}</div>` : '<div style="font-size:12px;color:#64748b;padding:8px 0">まだありません</div>'}`;
  }
  function paint() { const b = document.getElementById('od-body'); if (b) b.innerHTML = body(); }

  window.openOpenData = function () {
    let m = document.getElementById('modal-opendata');
    if (!m) {
      m = document.createElement('div'); m.id = 'modal-opendata'; m.className = 'modal-overlay active';
      m.onclick = e => { if (e.target === m) closeOpenData(); };
      m.innerHTML = `<div class="modal-content" style="max-height:92vh;overflow-y:auto"><div class="modal-header"><div class="modal-title">📊 オープンデータ</div>
        <div class="modal-close" onclick="closeOpenData()">✕</div></div><div class="modal-body" id="od-body"></div></div>`;
      document.body.appendChild(m);
    }
    m.style.display = 'flex'; m.classList.add('active'); st.delAsk = ''; paint();
  };
  window.closeOpenData = function () { const m = document.getElementById('modal-opendata'); if (m) m.remove(); };

  const read = f => new Promise((ok, ng) => { const r = new FileReader(); r.onload = e => ok(e.target.result); r.onerror = ng; r.readAsDataURL(f); });
  // background saving: pick -> the screenshots go into a queue at once and are uploaded 2 at a time; the modal can be closed
  function badge() { const el = document.querySelector('span[title^="オープンデータ"]'); if (el) el.textContent = st.q.filter(w => !w.err).length ? '📊⏳' : '📊'; }
  async function work(w) {
    w.busy = 1; w.err = 0; paint();
    try {
      const ref = await uploadImageSmart(w.data, 'opendata_' + Date.now() + '.jpg', 2600, 0.9);
      if (!ref || String(ref).startsWith('data:')) throw new Error('upload');
      const data = {'日付': w.at, '本文': '', 'カテゴリ': CAT, '画像URL': ref, '画像URL2': '', '画像URL3': '', 'ステータス': '未解決', 'お気に入り': ''};
      const res = await gasPostQueued({action: 'saveIdea', data: data}, 'オープンデータの保存');
      if (!res || !res.success) throw new Error((res && res.error) || 'save');
      if (!res.queued) App.data.ideas.push(Object.assign({id: res.id}, data));
      st.q = st.q.filter(x => x !== w); st.ok++;
    } catch (e) { console.warn('opendata', e); w.busy = 0; w.err = 1; st.ng++; }
    paint(); badge();
  }
  async function pump() {
    while (st.running < WORKERS) {
      const w = st.q.find(x => !x.busy && !x.err); if (!w) break;
      st.running++; work(w).finally(() => { st.running--; pump(); });
    }
    if (!st.running && !st.q.some(x => !x.err) && (st.ok || st.ng)) {
      showToast(st.ng ? `⚠️ オープンデータ：${st.ok} 枚保存、${st.ng} 枚は保存できず（📊 から「もう一度」）` : `✅ オープンデータ ${st.ok} 枚を保存しました`); st.ok = 0; st.ng = 0;
    }
  }
  window.odAdd = async function (ev) {
    const files = Array.from((ev.target.files || [])).filter(f => String(f.type || '').startsWith('image/')); ev.target.value = '';
    if (!files.length) return;
    const at = jst();
    for (const f of files) st.q.push({id: String(Date.now()) + Math.random().toString(36).slice(2, 6), at, data: await read(f)});
    paint(); badge(); showToast(`📊 ${files.length} 枚を裏で保存します（閉じても大丈夫）`); pump();
  };
  window.odRetry = function (id) { const w = st.q.find(x => x.id === id); if (w) { w.err = 0; pump(); paint(); } };
  addEventListener('beforeunload', e => { if (st.q.some(x => !x.err)) { e.preventDefault(); e.returnValue = ''; } });
  window.odOpen = function (id) {
    const xs = rows(), big = xs.map(x => src(x['画像URL'], 1600)), i = xs.findIndex(x => String(x.id) === String(id));
    if (i >= 0 && typeof openLightbox === 'function') openLightbox(big[i], big, i);
  };
  window.odDelete = async function (id) {
    if (st.delAsk !== String(id)) { st.delAsk = String(id); paint(); return; }      // confirm in the page (no confirm() dialog)
    st.delAsk = ''; showLoader();
    try {
      const res = await gasPostQueued({action: 'deleteIdea', ideaId: id}, 'オープンデータの削除');
      if (res && res.success) { App.data.ideas = App.data.ideas.filter(i => String(i.id) !== String(id)); showToast('削除しました'); }
      else showToast('⚠️ 削除できませんでした');
    } catch (e) { showToast('⚠️ 削除エラー: ' + e.message); }
    hideLoader(); paint();
  };
})();
