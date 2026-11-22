/* 📊 オープンデータ（OANDA のオープンオーダー・オープンポジションのスクショをためる）2026-11-22
 * OANDA's order / position book has no history and may not be fetched automatically, so the trader saves screenshots when there is
 * time. Pick one or many images: each is saved as its own row, nothing else to fill in (pair and time are read from the image later;
 * reader prototype: research/studies/orderbook/ob_read.py).
 * Stored in the Ideas sheet, category 'オープンデータ', through the existing saveIdea / deleteIdea (no GAS change).
 * Images are uploaded larger than usual (long side up to 2600 px, JPEG 0.92) so the bar lengths stay measurable.
 */
(function () {
  const CAT = 'オープンデータ';
  const st = {busy: 0, done: 0, total: 0, delAsk: ''};
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const rows = () => ((typeof App !== 'undefined' && App.data && App.data.ideas) || []).filter(i => i['カテゴリ'] === CAT)
    .slice().sort((a, b) => String(b['日付'] || '').localeCompare(String(a['日付'] || '')) || String(b.id).localeCompare(String(a.id)));
  const jst = () => { const d = new Date(Date.now() + 9 * 3600e3), p = n => String(n).padStart(2, '0');
    return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`; };
  const src = (u, w) => (typeof getImageUrl === 'function' && !String(u).startsWith('data:')) ? getImageUrl(u, w) : u;

  function body() {
    const xs = rows();
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
      <button type="button" class="btn-primary" ${st.busy ? 'disabled' : ''} onclick="document.getElementById('od-file').click()" style="width:100%;padding:14px;font-size:15px">
        ${st.busy ? `⏳ 保存中 ${st.done}/${st.total}` : '📷 スクショを選ぶ'}</button>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:16px 0 6px">ためたもの（${xs.length} 枚）</div>
      ${xs.length ? `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">${grid}</div>` : '<div style="font-size:12px;color:#64748b;padding:8px 0">まだありません</div>'}`;
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
  window.odAdd = async function (ev) {
    const files = Array.from((ev.target.files || [])).filter(f => String(f.type || '').startsWith('image/')); ev.target.value = '';
    if (!files.length) return;
    st.busy = 1; st.done = 0; st.total = files.length; paint();
    let ok = 0, queued = 0;
    for (const f of files) {
      try {
        const ref = await uploadImageSmart(await read(f), 'opendata_' + Date.now() + '.jpg', 2600, 0.92);
        const data = {'日付': jst(), '本文': '', 'カテゴリ': CAT, '画像URL': ref || '', '画像URL2': '', '画像URL3': '', 'ステータス': '未解決', 'お気に入り': ''};
        const res = await gasPostQueued({action: 'saveIdea', data: data}, 'オープンデータの保存');
        if (res && res.success) { ok++; if (res.queued) queued++; else App.data.ideas.push(Object.assign({id: res.id}, data)); }
      } catch (e) { console.warn('opendata', e); }
      st.done++; paint();
    }
    st.busy = 0; paint();
    showToast(ok === files.length ? (queued ? `📥 ${ok} 枚を保存待ちに入れました` : `✅ ${ok} 枚を保存しました`) : `⚠️ ${files.length - ok} 枚は保存できませんでした`);
  };
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
