/* 📌 取りたい所（EA のネタ帳）2026-11-12
 * Spots on the chart an EA should take, saved while looking at the phone's MT5: direction + shape buttons, up to 3 screenshots
 * (the crosshair on the bar gives symbol / time / price for the later analysis) and a short note.
 * Stored in the Ideas sheet (category 'EAのネタ') through the existing saveIdea / deleteIdea, so no GAS change is needed.
 * 本文 holds "向き: …\n形: …" and then the note; the hand-written idea list leaves this category out.
 */
(function () {
  const CAT = 'EAのネタ';
  const DIRS = ['買い', '売り'];
  const SHAPES = ['抵抗帯反発', '推進トレンドライン', '調整ライン抜け', 'H1MAあり', 'M15ダウ転換', 'M15ライン抜け', 'レンジ抜け', 'ダブルボトム・トップ', '伸びの途中'];   // several can be chosen (2026-11-12)
  const st = {dir: '', shapes: [], imgs: [], busy: 0, view: null, editId: ''};   // editId: the saved entry being edited
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const ideas = () => ((typeof App !== 'undefined' && App.data && App.data.ideas) || []).filter(i => i['カテゴリ'] === CAT);   // App is a top-level const in app.js (not on window)
  const parse = t => {
    const s = String(t || ''), dir = (s.match(/^向き: (.*)$/m) || [])[1] || '', shape = (s.match(/^形: (.*)$/m) || [])[1] || '';
    return {dir, shape, note: s.replace(/^向き: .*\n?/m, '').replace(/^形: .*\n?/m, '').replace(/^\n+/, '')};
  };
  const chip = (on, col) => `border-radius:999px;padding:8px 13px;font-size:13px;font-weight:700;border:1px solid ${on ? col : '#334155'};background:${on ? 'rgba(34,211,238,.10)' : '#172033'};color:${on ? col : '#94a3b8'}`;

  function body() {
    const d = DIRS.map(x => `<button type="button" onclick="eaIdeaSet('dir','${x}')" style="${chip(st.dir === x, x === '買い' ? '#f87171' : '#38bdf8')};flex:1">${x}</button>`).join('');
    const s = SHAPES.map(x => `<button type="button" onclick="eaIdeaShape('${x}')" style="${chip(st.shapes.indexOf(x) >= 0, '#22d3ee')}">${x}</button>`).join('');
    const im = st.imgs.map((u, i) => `<div style="position:relative"><img src="${esc(typeof getImageUrl === 'function' && !String(u).startsWith('data:') ? getImageUrl(u, 400) : u)}" referrerpolicy="no-referrer" style="width:84px;height:84px;object-fit:cover;border-radius:8px;border:1px solid #334155">
        <button type="button" onclick="eaIdeaRmImg(${i})" style="position:absolute;top:2px;right:2px;border:0;border-radius:6px;background:rgba(15,23,42,.8);color:#f87171;font-size:12px;padding:2px 5px">✕</button></div>`).join('');
    const list = ideas().slice().sort((a, b) => String(b['日付'] || '').localeCompare(String(a['日付'] || '')) || String(b.id).localeCompare(String(a.id))).map(x => {
      const p = parse(x['本文']), u = x['画像URL'];
      return `<div onclick="eaIdeaOpen('${esc(x.id)}')" style="cursor:pointer;display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid #1e293b">
        ${u ? `<img src="${esc(typeof getImageUrl === 'function' ? getImageUrl(u, 200) : u)}" referrerpolicy="no-referrer" loading="lazy" style="width:52px;height:52px;object-fit:cover;border-radius:6px;border:1px solid #334155;flex:none">` : '<div style="width:52px;height:52px;border-radius:6px;background:#172033;flex:none"></div>'}
        <div style="min-width:0;flex:1"><div style="font-size:13px;font-weight:700">${esc([p.dir, p.shape].filter(Boolean).join(' · ') || '（未選択）')}</div>
          <div style="font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(String(x['日付'] || '').slice(0, 10))}${p.note ? ' · ' + esc(p.note) : ''}</div></div></div>`;
    }).join('');
    const ed = st.editId ? ideas().find(i => String(i.id) === String(st.editId)) : null;
    return `${ed ? `<div style="font-size:13px;font-weight:800;color:#fbbf24;margin-bottom:10px">✏️ 編集中（${esc(String(ed['日付'] || '').slice(0, 10))} の分）</div>` : ''}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin-bottom:6px">向き</div><div style="display:flex;gap:8px">${d}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:14px 0 6px">形（いくつでも）</div><div style="display:flex;flex-wrap:wrap;gap:6px">${s}</div>
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:14px 0 6px">画像（MT5 のスクショ・十字線を入りたい足に）</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">${im}</div>
      ${st.imgs.length < 3 ? `<input type="file" id="ea-idea-file" accept="image/*" style="display:none" onchange="eaIdeaImg(event)">
        <button type="button" class="btn-secondary" ${st.busy ? 'disabled' : ''} onclick="document.getElementById('ea-idea-file').click()" style="width:100%;margin-top:8px;padding:12px;font-size:14px">📷 画像を追加${st.busy ? ' ⏳' : ''}</button>` : ''}
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:14px 0 6px">一言（任意）</div>
      <input id="ea-idea-note" class="form-input" style="width:100%;box-sizing:border-box" maxlength="300" placeholder="例：ここ入りたかった" value="${esc(st.note || '')}" oninput="eaIdeaNote(this.value)">
      <button type="button" class="btn-primary" onclick="eaIdeaSave()" style="width:100%;margin-top:14px;padding:14px;font-size:15px">${ed ? '更新する' : '保存'}</button>
      ${ed ? `<button type="button" class="btn-secondary" onclick="eaIdeaCancelEdit()" style="width:100%;margin-top:8px;padding:12px;font-size:14px">やめる</button>` : `
      <div style="font-size:12px;font-weight:700;color:#94a3b8;margin:20px 0 4px">ためたもの（${ideas().length}）</div>
      ${list || '<div style="font-size:12px;color:#64748b;padding:8px 0">まだありません</div>'}`}`;
  }
  function paint() { const b = document.getElementById('ea-idea-body'); if (b) b.innerHTML = body(); }

  window.openEAIdeas = function () {
    let m = document.getElementById('modal-ea-ideas');
    if (!m) {
      m = document.createElement('div'); m.id = 'modal-ea-ideas'; m.className = 'modal-overlay active';
      m.onclick = e => { if (e.target === m) closeEAIdeas(); };
      m.innerHTML = `<div class="modal-content" style="max-height:92vh;overflow-y:auto"><div class="modal-header"><div class="modal-title">📌 取りたい所</div>
        <div class="modal-close" onclick="closeEAIdeas()">✕</div></div><div class="modal-body" id="ea-idea-body"></div></div>`;
      document.body.appendChild(m);
    }
    m.style.display = 'flex'; m.classList.add('active'); paint();
  };
  window.closeEAIdeas = function () { const m = document.getElementById('modal-ea-ideas'); if (m) m.remove(); };
  window.eaIdeaSet = function (k, v) { st[k] = st[k] === v ? '' : v; paint(); };
  window.eaIdeaNote = function (v) { st.note = v; };
  window.eaIdeaShape = function (v) { const i = st.shapes.indexOf(v); if (i >= 0) st.shapes.splice(i, 1); else st.shapes.push(v); paint(); };
  window.eaIdeaRmImg = function (i) { st.imgs.splice(i, 1); paint(); };
  window.eaIdeaImg = function (ev) {
    const f = ev.target.files && ev.target.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = async e => {
      const i = st.imgs.length; st.imgs.push(e.target.result); st.busy++; paint();
      try {
        const ref = await uploadImageSmart(e.target.result, 'eaidea_' + Date.now() + '.jpg');
        if (ref && !String(ref).startsWith('data:')) st.imgs[i] = ref; else showToast('⚠️ 画像のアップロードに失敗しました');
      } catch (err) { showToast('⚠️ 画像のアップロードエラー'); }
      st.busy--; paint();
    };
    r.readAsDataURL(f);
  };
  window.eaIdeaSave = async function () {
    if (st.busy) { showToast('⏳ 画像をアップロード中です'); return; }
    if (!st.imgs.length && !st.dir && !st.shapes.length && !(st.note || '').trim()) { showToast('何か 1 つ入れてください'); return; }
    const imgs = st.imgs.filter(u => !String(u).startsWith('data:'));
    const now = new Date(), pad = n => String(n).padStart(2, '0');
    const ed = st.editId ? ideas().find(i => String(i.id) === String(st.editId)) : null;
    const data = {
      '日付': ed ? ed['日付'] : `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
      '本文': `向き: ${st.dir}\n形: ${SHAPES.filter(x => st.shapes.indexOf(x) >= 0).concat(st.shapes.filter(x => SHAPES.indexOf(x) < 0)).join('・')}\n${(st.note || '').trim()}`,   // shapes from an older button list are kept
      'カテゴリ': CAT, '画像URL': imgs[0] || '', '画像URL2': imgs[1] || '', '画像URL3': imgs[2] || '', 'ステータス': (ed && ed['ステータス']) || '未解決', 'お気に入り': (ed && ed['お気に入り']) || ''
    };
    showLoader();
    try {
      const res = ed ? await gasPostQueued({action: 'updateIdea', ideaId: ed.id, data: data}, '取りたい所の更新')
                     : await gasPostQueued({action: 'saveIdea', data: data}, '取りたい所の保存');
      if (res && res.success) {
        if (ed) Object.assign(ed, data);
        else if (!res.queued) App.data.ideas.push(Object.assign({id: res.id}, data));
        Object.assign(st, {dir: '', shapes: [], imgs: [], note: '', editId: ''}); paint();
        showToast(res.queued ? '📥 オフラインのため保存待ちに追加しました' : ed ? '更新しました ✅' : '保存しました ✅');
      } else showToast('⚠️ 保存できませんでした: ' + ((res && res.error) || ''));
    } catch (e) { showToast('⚠️ 保存エラー: ' + e.message); }
    hideLoader();
  };
  window.eaIdeaOpen = function (id) {
    const x = ideas().find(i => String(i.id) === String(id)); if (!x) return;
    const p = parse(x['本文']), urls = [x['画像URL'], x['画像URL2'], x['画像URL3']].filter(Boolean);
    const big = urls.map(u => typeof getImageUrl === 'function' ? getImageUrl(u, 1600) : u);
    const b = document.getElementById('ea-idea-body'); if (!b) return;
    b.innerHTML = `<button type="button" onclick="eaIdeaBack()" style="border:0;background:none;color:#22d3ee;font-size:13px;font-weight:700;padding:0 0 10px">← もどる</button>
      <div style="font-size:15px;font-weight:800">${esc([p.dir, p.shape].filter(Boolean).join(' · ') || '（未選択）')}</div>
      <div style="font-size:12px;color:#94a3b8;margin:4px 0 10px">${esc(String(x['日付'] || '').slice(0, 10))}</div>
      ${p.note ? `<div style="font-size:13px;line-height:1.6;margin-bottom:10px;white-space:pre-wrap">${esc(p.note)}</div>` : ''}
      <div style="display:flex;flex-direction:column;gap:10px">${urls.map((u, i) => `<img src="${esc(typeof getImageUrl === 'function' ? getImageUrl(u, 1000) : u)}" referrerpolicy="no-referrer" onclick='openLightbox(${JSON.stringify(big[i])}, ${JSON.stringify(big)}, ${i})' style="width:100%;border-radius:8px;border:1px solid #334155;cursor:zoom-in">`).join('')}</div>
      <button type="button" class="btn-primary" onclick="eaIdeaEdit('${esc(x.id)}')" style="width:100%;margin-top:16px;padding:12px;font-size:14px">✏️ 編集</button>
      <button type="button" onclick="eaIdeaDelete('${esc(x.id)}')" style="width:100%;margin-top:8px;padding:12px;border-radius:8px;border:1px solid #7f1d1d;background:#1f1315;color:#f87171;font-weight:700">🗑️ 削除</button>
      <div id="ea-idea-del-ask"></div>`;
  };
  window.eaIdeaBack = function () { paint(); };
  window.eaIdeaEdit = function (id) {                     // load a saved entry into the form (direction / shapes / images / note)
    const x = ideas().find(i => String(i.id) === String(id)); if (!x) return;
    const p = parse(x['本文']);
    Object.assign(st, {editId: x.id, dir: p.dir, shapes: p.shape ? p.shape.split('・').filter(Boolean) : [],
                       imgs: [x['画像URL'], x['画像URL2'], x['画像URL3']].filter(Boolean), note: p.note});
    paint(); const b = document.getElementById('modal-ea-ideas'); if (b && b.firstChild) b.firstChild.scrollTop = 0;
  };
  window.eaIdeaCancelEdit = function () { Object.assign(st, {dir: '', shapes: [], imgs: [], note: '', editId: ''}); paint(); };
  window.eaIdeaDelete = async function (id) {
    const ask = document.getElementById('ea-idea-del-ask');
    if (ask && !ask.dataset.ok) {                          // confirm in the page (no confirm() dialog)
      ask.dataset.ok = '1';
      ask.innerHTML = `<div style="font-size:12px;color:#fca5a5;margin-top:8px">もう一度「🗑️ 削除」を押すと消えます</div>`;
      return;
    }
    showLoader();
    try {
      const res = await gasPostQueued({action: 'deleteIdea', ideaId: id}, '取りたい所の削除');
      if (res && res.success) { App.data.ideas = App.data.ideas.filter(i => String(i.id) !== String(id)); showToast('削除しました'); paint(); }
      else showToast('⚠️ 削除できませんでした');
    } catch (e) { showToast('⚠️ 削除エラー: ' + e.message); }
    hideLoader();
  };
})();
