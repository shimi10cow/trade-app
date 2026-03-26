const GAS_URL = 'https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec';

const App = {
  data: {
    entries: [],
    pairs: [],
    ideas: []
  },
  state: {
    currentTab: 'positions',
    isOffline: !navigator.onLine,
    isMissedEntry: false,
    detailFromHistory: false,
    activeTradeIndex: null,
    modalOpenedAt: 0
  }
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initServiceWorker();
  setupEventListeners();
  setupModalInteractions();
  setupPullToRefresh();
  loadData();
  updateImgBBStatusBar();
});

// ── プルダウンリフレッシュ ──
function setupPullToRefresh() {
  let startY = 0;
  let pulling = false;
  let triggered = false;
  const THRESHOLD = 72; // リロード発火距離(px)

  // リフレッシュインジケーター（引っ張った空間に表示）
  const ind = document.createElement('div');
  ind.id = 'ptr-bar';
  ind.style.cssText = [
    'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:8888',
    'height:0', 'overflow:hidden', 'background:#0f172a',
    'display:flex', 'align-items:center', 'justify-content:center',
    'transition:height 0.15s ease', 'will-change:height'
  ].join(';');
  ind.innerHTML = `
    <div id="ptr-inner" style="display:flex;align-items:center;gap:8px;color:#38bdf8;font-size:12px;font-weight:600;opacity:0;transition:opacity 0.2s;">
      <span id="ptr-spinner" style="font-size:18px;display:inline-block;transition:transform 0.3s;">↓</span>
      <span id="ptr-label">引っ張ってリロード</span>
    </div>`;
  document.body.appendChild(ind);

  // ページ全体のスクロール量を取得（.screenはdisplay:blockのみでスクロールしない）
  function getScrollTop() {
    return document.documentElement.scrollTop || document.body.scrollTop;
  }

  document.addEventListener('touchstart', e => {
    if (document.querySelector('.modal-overlay.active')) return;
    if (getScrollTop() > 0) return; // 一番上でないなら無効
    startY = e.touches[0].clientY;
    pulling = true;
    triggered = false;
  }, { passive: true });

  document.addEventListener('touchmove', e => {
    if (!pulling) return;
    if (document.querySelector('.modal-overlay.active')) { pulling = false; return; }
    if (getScrollTop() > 0) { pulling = false; ind.style.height = '0'; return; }

    const dy = Math.max(0, e.touches[0].clientY - startY);
    if (dy < 8) return;

    // バーを引っ張り量に合わせて伸ばす（最大 THRESHOLD px）
    const barH = Math.min(dy * 0.6, THRESHOLD);
    ind.style.height = barH + 'px';
    ind.style.transition = 'none';

    const inner = document.getElementById('ptr-inner');
    const spinner = document.getElementById('ptr-spinner');
    const label = document.getElementById('ptr-label');
    if (inner) inner.style.opacity = Math.min(barH / 40, 1).toString();

    if (barH >= THRESHOLD - 4) {
      if (spinner) { spinner.textContent = '↻'; spinner.style.transform = 'rotate(180deg)'; }
      if (label) label.textContent = '離してリロード';
      triggered = true;
    } else {
      if (spinner) { spinner.textContent = '↓'; spinner.style.transform = `rotate(${Math.min(barH * 2.5, 170)}deg)`; }
      if (label) label.textContent = '引っ張ってリロード';
      triggered = false;
    }
  }, { passive: true });

  document.addEventListener('touchend', () => {
    if (!pulling) return;
    pulling = false;
    if (triggered) {
      // くるくるスピナーに切り替え
      const spinner = document.getElementById('ptr-spinner');
      const label = document.getElementById('ptr-label');
      if (spinner) spinner.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"/></path></svg>';
      if (label) label.textContent = '更新中...';
      ind.style.transition = '';
      ind.style.height = THRESHOLD + 'px';
      // 現在のタブをsessionStorageに保存してからリロード
      const activeTab = document.querySelector('.tab.active')?.dataset?.tab || '';
      if (activeTab) sessionStorage.setItem('ptr-active-tab', activeTab);
      setTimeout(() => window.location.reload(), 400);
    } else {
      // 元に戻す
      ind.style.transition = 'height 0.25s ease';
      ind.style.height = '0';
    }
  }, { passive: true });
}


function initServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js')
      .then(() => console.log('PWA Service Worker Registered'))
      .catch(err => console.error('SW Error:', err));
  }
  window.addEventListener('online', () => updateNetworkStatus(true));
  window.addEventListener('offline', () => updateNetworkStatus(false));
}

function updateNetworkStatus(isOnline) {
  App.state.isOffline = !isOnline;
  const badge = document.getElementById('network-status');
  if (isOnline) {
    badge.className = 'badge bg-green';
    badge.textContent = 'Online';
    setTimeout(() => badge.classList.add('hidden'), 2000);
  } else {
    badge.className = 'badge bg-red';
    badge.textContent = 'Offline';
    badge.classList.remove('hidden');
  }
}

// ==========================================
// UI Helpers
// ==========================================
function showLoader() {
  document.getElementById('app-loader').classList.add('active');
}

function hideLoader() {
  document.getElementById('app-loader').classList.remove('active');
}

// Sanitize Excel epoch dates (1899-12-30) that GAS emits for time-only values
function formatDateDisplay(dateStr) {
  if (!dateStr) return '';
  const s = String(dateStr);
  if (s.startsWith('1899') || s.startsWith('1900-01-0')) return '';
  return s.split('T')[0];
}

// Extract HH:MM from ISO string like '1899-12-30T14:30:00.000Z' or return as-is
function formatTimeDisplay(timeStr) {
  if (!timeStr) return '';
  const s = String(timeStr);
  const match = s.match(/T(\d{2}:\d{2})/);
  if (match) return match[1];
  if (/^\d{2}:\d{2}/.test(s)) return s.substring(0, 5);
  return '';
}

function openHistoryModal() {
  App.state.modalOpenedAt = Date.now();
  App.state.historyBaseFilter = null; // 通常オープン時はリセット
  const _hm = document.getElementById('modal-history');
  _hm.classList.add('active');
  requestAnimationFrame(() => { _hm.querySelector('.modal-body').scrollTop = 0; });
  document.getElementById('hist-period').value = 'all';
  toggleCustomHistDate();
  renderHistoryList();
}

function openHistoryForMonth(monthKey) {
  // monthKey: 'YYYY-MM' — 分析タブの絞り込み結果を引き継いで月フィルタで開く
  const [year, month] = monthKey.split('-').map(Number);
  const lastDay = new Date(year, month, 0).getDate();
  App.state.modalOpenedAt = Date.now();
  App.state.historyBaseFilter = App.state.analysisFiltered || null;
  const _hm = document.getElementById('modal-history');
  _hm.classList.add('active');
  requestAnimationFrame(() => { _hm.querySelector('.modal-body').scrollTop = 0; });
  document.getElementById('hist-period').value = 'custom';
  toggleCustomHistDate();
  document.getElementById('hist-date-from').value = `${monthKey}-01`;
  document.getElementById('hist-date-to').value = `${monthKey}-${String(lastDay).padStart(2, '0')}`;
  renderHistoryList();
}

function closeHistoryModal() {
  App.state.historyBaseFilter = null;
  document.getElementById('modal-history').classList.remove('active');
}

function toggleCustomHistDate() {
  const period = document.getElementById('hist-period').value;
  document.getElementById('hist-custom-date').style.display = period === 'custom' ? 'flex' : 'none';
}

function renderHistoryList() {
  const container = document.getElementById('history-list');
  if (!container) return;
  const fPeriod = document.getElementById('hist-period').value;
  const histStatus = document.getElementById('hist-status')?.value || 'all';
  const dFrom = document.getElementById('hist-date-from')?.value;
  const dTo = document.getElementById('hist-date-to')?.value;

  const now = new Date();
  const currentMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthStr = `${lastMonth.getFullYear()}-${String(lastMonth.getMonth() + 1).padStart(2, '0')}`;

  // チャートバークリック時は分析タブの絞り込み結果をベースにする
  const base = App.state.historyBaseFilter
    ? App.state.historyBaseFilter
    : App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');
  let filtered = base.slice();

  filtered = filtered.filter(t => {
    // ステータスフィルター
    if (histStatus === 'entry' && t['ステータス'] === '決済（見逃し）') return false;
    if (histStatus === 'missed' && t['ステータス'] !== '決済（見逃し）') return false;
    // 期間フィルター
    const dateStr = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
    if (fPeriod === 'this_month' && !dateStr.startsWith(currentMonthStr)) return false;
    if (fPeriod === 'last_month' && !dateStr.startsWith(lastMonthStr)) return false;
    if (fPeriod === 'custom') {
      const tDate = new Date(dateStr);
      if (dFrom && tDate < new Date(dFrom)) return false;
      if (dTo && tDate > new Date(dTo + 'T23:59:59')) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">履歴がありません</div>';
    return;
  }

  container.innerHTML = filtered.slice().sort((a, b) => {
    const da = String(a.EntryDate || '').split('T')[0].replace(/\//g, '-');
    const db = String(b.EntryDate || '').split('T')[0].replace(/\//g, '-');
    return db > da ? 1 : db < da ? -1 : 0;
  }).map((t) => {
    const index = App.data.entries.indexOf(t);
    const isMissed = t['ステータス'] === '決済（見逃し）';
    const badgeClass = t.Direction === 'Buy' ? 'buy' : 'sell';
    const dirArrow = t.Direction === 'Buy' ? '▲' : '▼';
    const pips = parseFloat(t['実取得pips']) || 0;
    const isWin = pips > 10;
    const isLoss = pips < -5;
    const pipsColor = isWin ? '#10b981' : (isLoss ? '#ef4444' : '#f59e0b');
    const pipsSign = pips > 0 ? '+' : '';
    const borderColor = isMissed ? '#f59e0b' : (isWin ? '#10b981' : (isLoss ? '#ef4444' : '#f59e0b'));

    return `
      <div class="list-card" onclick="closeHistoryModal(); openTradeDetail(${index}, false, true)" style="cursor:pointer; border-left: 4px solid ${borderColor}">
        <div style="flex:1;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <div style="font-weight:700; font-size:14px; display:flex; align-items:center; gap:8px;">
              ${t['PairName（元）'] || t.PairName || t.Pair || 'ペア不明'}
              <span class="badge ${badgeClass}">${dirArrow} ${t.Direction || ''}</span>
              ${isMissed ? '<span class="badge" style="background:rgba(245,158,11,0.2); color:#f59e0b;">見逃し</span>' : ''}
            </div>
            <div style="font-weight:700; font-size:15px; color:${pipsColor};">${pipsSign}${pips.toFixed(1)} <span style="font-size:10px;">pips</span></div>
          </div>
          <div style="font-size:11px; color:#94a3b8; display:flex; justify-content:space-between;">
            <span>${formatDateDisplay(t.EntryDate)} ${formatTimeDisplay(t.EntryTime)} · ｽｺｱ: ${t['エントリースコア'] || '-'}</span>
            <span>¥${(parseFloat(t['損益']) || 0).toLocaleString()}</span>
          </div>
        </div>
        <div style="color:#94a3b8; font-size:16px; margin-left:12px;">›</div>
      </div>
    `;
  }).join('');
}

// ==========================================
// Navigation
// ==========================================
function setupEventListeners() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      const target = e.currentTarget.dataset.tab;
      switchTab(target);
    });
  });
}

function setupModalInteractions() {
  // Close modals when clicking the overlay (outside the content)
  // Guard against ghost clicks on mobile (touch -> click delay ~300ms)
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        // Ignore clicks that arrive within 500ms of opening any modal
        if (Date.now() - (App.state.modalOpenedAt || 0) < 500) return;
        overlay.classList.remove('active');
      }
    });
  });

  // Swipe down to close logic for modal-content
  let touchStartY = 0;
  let touchCurrentY = 0;
  let isDragging = false;
  let targetModal = null;

  document.addEventListener('touchstart', (e) => {
    const header = e.target.closest('.modal-header');
    if (!header) return;

    targetModal = e.target.closest('.modal-content');
    if (!targetModal) return;

    touchStartY = e.touches[0].clientY;
    touchCurrentY = touchStartY; // ← 初期化（前回の値を引き継がないよう）
    isDragging = true;
    targetModal.style.transition = 'none';
  }, { passive: true });

  document.addEventListener('touchmove', (e) => {
    if (!isDragging || !targetModal) return;

    touchCurrentY = e.touches[0].clientY;
    const deltaY = touchCurrentY - touchStartY;

    if (deltaY > 0) {
      e.preventDefault();
      targetModal.style.transform = `translateY(${deltaY}px)`;
    }
  }, { passive: false });

  document.addEventListener('touchend', (e) => {
    if (!isDragging || !targetModal) return;

    isDragging = false;
    const deltaY = touchCurrentY - touchStartY;
    const closedModal = targetModal;
    targetModal = null; // 先にnullにして次のtouchと混在しないように

    closedModal.style.transition = 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)';

    if (deltaY > 100) {
      closedModal.style.transform = `translateY(100%)`;
      const overlay = closedModal.closest('.modal-overlay');
      setTimeout(() => {
        if (overlay) overlay.classList.remove('active');
        closedModal.style.transform = ''; // 次回open用にリセット
        // モーダルごとの状態クリーンアップ
        if (overlay?.id === 'modal-trade-detail') {
          App.state.detailFromHistory = false; // 履歴フラグをリセット
        }
      }, 300);
    } else {
      closedModal.style.transform = `translateY(0)`;
      setTimeout(() => {
        closedModal.style.transform = '';
      }, 300);
    }
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[data-tab="${tabId}"]`).classList.add('active');

  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${tabId}`).classList.add('active');

  App.state.currentTab = tabId;

  // Update view based on tab
  if (tabId === 'positions') renderPositions();
  if (tabId === 'pairs') renderPairs();
  if (tabId === 'analysis') renderAnalysis();
  if (tabId === 'gallery') renderGallery();
}

function renderAnalysis() {
  updateMonthlyStats();
  applyAnalysisFilters();
  // AI分析期間タブ：初回のみデフォルト1ヶ月を設定
  if (!document.getElementById('ai-date-from')?.value) {
    setAiTab('1m');
  }
}

function openEntryModal(isMissed = false) {
  App.state.isMissedEntry = isMissed;

  // CLEAR ALL FORM FIELDS
  const modal = document.getElementById('modal-entry');
  modal.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(el => {
    if (el.id !== 'ne-dow-rule') el.value = '';
  });
  modal.querySelectorAll('button.toggle-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('ne-dow-rule').value = '1';
  document.getElementById('ne-rr-display').textContent = 'RR: --';
  document.getElementById('ne-rr-display').className = 'calc-info';

  const sel = document.getElementById('ne-pair');
  sel.innerHTML = '<option value="">選択...</option>';

  const pairNames = [...new Set(App.data.pairs.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
  pairNames.forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });

  // Set current date/time
  const now = new Date();
  const dateStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
  const timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  document.getElementById('ne-date').value = dateStr;
  document.getElementById('ne-time').value = timeStr;

  document.getElementById('ne-pre-memo').textContent = '(ペアを選択すると表示されます)';
  document.getElementById('ne-judgement-text').textContent = '--';
  document.getElementById('ne-judgement-text').style.color = '#f8fafc';

  document.getElementById('ne-image-preview').style.display = 'none';
  document.getElementById('ne-image-preview').src = '';
  document.getElementById('image-preview-container').style.display = 'none';

  const _ra = document.getElementById('ne-recent-analysis-section');
  if (_ra) _ra.style.display = 'none';
  const _rad = document.getElementById('ne-revenge-alert');
  if (_rad) _rad.innerHTML = '';

  const titleDiv = document.querySelector('#modal-entry .modal-title');
  if (isMissed) {
    titleDiv.textContent = '見逃しエントリー記録';
    titleDiv.style.color = '#f59e0b';
  } else {
    titleDiv.textContent = '新規エントリー記録';
    titleDiv.style.color = '#38bdf8';
  }

  analyzeMentalMode();
  showEntryRevengeAlert(); // ← エントリー前警告チェック
  document.getElementById('ne-similar-summary').textContent = '類似トレードを計算中...';
  document.getElementById('ne-similar-list').innerHTML = '';

  calculateEntryScore();

  App.state.modalOpenedAt = Date.now();
  const _em = document.getElementById('modal-entry');
  _em.classList.add('active');
  requestAnimationFrame(() => { _em.querySelector('.modal-body').scrollTop = 0; });
}

function closeEntryModal() {
  document.getElementById('modal-entry').classList.remove('active');
}

function autoLoadPairInfo(prefix = 'ne', resetDir = true) {
  const sel = document.getElementById(`${prefix}-pair`);
  if (!sel) return;
  const pairName = sel.value;
  const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);

  if (prefix === 'ne') {
    // Reset direction buttons only when pair changes (not when direction button is clicked)
    if (resetDir) {
      document.querySelectorAll('#ne-dir button').forEach(b => b.classList.remove('active'));
    }

    const preMemoBox = document.getElementById('ne-pre-memo');
    if (!p) {
      preMemoBox.textContent = '(ペアを選択すると表示されます)';
    } else {
      preMemoBox.textContent = p['事前メモ'] || p['環境認識メモ'] || p['メモ'] || '(事前メモなし)';
    }
  }

  // --- Auto populate Trend Direction ---
  if (p) {
    const tfGroups = document.querySelectorAll(prefix === 'ne' ? '#modal-entry .tf-group' : '#modal-trade-detail .tf-group');
    if (tfGroups.length >= 5) {
      const keys = ['M1', 'W1', 'D1', 'H4', 'H1'];
      tfGroups.forEach((grp, i) => {
        if (!keys[i]) return;
        const val = p[keys[i]];
        if (val) {
          grp.querySelectorAll('button').forEach(b => {
            b.classList.remove('active');
            if (b.textContent.trim() === val) b.classList.add('active');
          });
        }
      });
    }
  }

  // Auto populate MA Conditions only if both Pair and Direction are selected
  let dirActive;
  if (prefix === 'ne') {
    dirActive = document.querySelector(`#ne-dir .active`);
  } else {
    dirActive = document.querySelector(`#td-dir .active`);
  }

  if (p && dirActive) {
    const dir = dirActive.textContent.includes('Buy') || dirActive.textContent.includes('▲') ? 'Buy' : 'Sell';

    const getMAKairi = (cDir, cVal) => {
      if (!cVal) return '✕';
      if (cDir === 'Buy' && cVal === '下アリ') return '◎';
      if (cDir === 'Buy' && cVal === '上アリ') return 'NG';
      if (cDir === 'Sell' && cVal === '上アリ') return '◎';
      if (cDir === 'Sell' && cVal === '下アリ') return 'NG';
      return '✕';
    };

    const setMA = (idx, status) => {
      // index: 0=480, 1=kairi, 2=H1_20, 3=H4_20
      const modalId = prefix === 'ne' ? '#modal-entry' : '#modal-trade-detail';
      const mapGrp = document.querySelectorAll(`${modalId} .ma-group`)[idx];
      if (!mapGrp) return;
      mapGrp.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      if (status === '◎') mapGrp.querySelector('.cond-ok')?.classList.add('active');
      else if (status === '✕' || status === 'NG') mapGrp.querySelector('.cond-ng')?.classList.add('active');
    };

    setMA(0, (dir === 'Buy' && p['H4MA480.1200'] === '↑') || (dir === 'Sell' && p['H4MA480.1200'] === '↓') ? '◎' : '✕');
    setMA(1, getMAKairi(dir, p['H4MA乖離']));
    setMA(2, (dir === 'Buy' && p['H1MA20.80'] === '↑') || (dir === 'Sell' && p['H1MA20.80'] === '↓') ? '◎' : '✕');
    setMA(3, (dir === 'Buy' && p['H4MA20.80'] === '↑') || (dir === 'Sell' && p['H4MA20.80'] === '↓') ? '◎' : '✕');
  }

  if (prefix === 'ne') calculateEntryScore();
  else calculateEntryScoreTD();
}

// ==========================================
// API & Data
// ==========================================
async function loadData() {
  showLoader();
  try {
    const [pairsRes, entriesRes, ideasRes] = await Promise.all([
      fetch(`${GAS_URL}?action=getPairs`).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
      fetch(`${GAS_URL}?action=getEntries`).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
      fetch(`${GAS_URL}?action=getIdeas`).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
    ]);
    App.data.pairs = pairsRes.data || [];
    App.data.entries = entriesRes.data || [];
    App.data.ideas = ideasRes.data || [];

    populateFilterPairs();

    // Initial renders
    renderPositions();
    renderPairs();
    renderAnalysis();
    renderGallery();
    renderIdeas();

    // プルダウンリフレッシュ後のタブ復元
    const ptrTab = sessionStorage.getItem('ptr-active-tab');
    if (ptrTab) {
      sessionStorage.removeItem('ptr-active-tab');
      switchTab(ptrTab);
    }
  } catch (err) {
    console.error('Failed to load data:', err);
    alert('データの読み込みに失敗しました: ' + err.message + '\n\nGASのURLを確認するか、再度デプロイしてください。');
  } finally {
    hideLoader();
  }
}

// ==========================================
// Setup Helpers
// ==========================================
function populateFilterPairs() {
  const sel = document.getElementById('flt-pair');
  if (!sel) return;
  const pairs = [...new Set(App.data.pairs.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
  pairs.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    sel.appendChild(opt);
  });

  // エントリー振り返り・決済振り返りの選択肢を動的に構築
  const closedTrades = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');

  const entryRefSel = document.getElementById('flt-entry-ref');
  if (entryRefSel) {
    const entryRefVals = [...new Set(closedTrades.map(t => t['エントリー振り返り'] || '').filter(Boolean))].sort();
    entryRefVals.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      entryRefSel.appendChild(opt);
    });
  }

  const exitRefSel = document.getElementById('flt-exit-ref');
  if (exitRefSel) {
    const exitRefVals = [...new Set(closedTrades.map(t => t['決済振り返り'] || '').filter(Boolean))].sort();
    exitRefVals.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      exitRefSel.appendChild(opt);
    });
  }
}

function toggleCustomDate() {
  const period = document.getElementById('flt-period').value;
  const customDiv = document.getElementById('flt-custom-date');
  if (period === 'custom') {
    customDiv.style.display = 'flex';
  } else {
    customDiv.style.display = 'none';
  }
}

// ==========================================
// Renders
// ==========================================
function renderPositions() {
  const container = document.getElementById('positions-list');

  // Filter for active positions (保有中 or 保有中（見逃し）)
  const activeTrades = App.data.entries.filter(t => t['ステータス'] === '保有中' || t['ステータス'] === '保有中（見逃し）');

  if (activeTrades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">現在保有中のポジションはありません</div>';
    return;
  }

  container.innerHTML = activeTrades.slice().sort((a, b) => {
    const da = String(a.EntryDate || '').split('T')[0].replace(/\//g, '-');
    const db = String(b.EntryDate || '').split('T')[0].replace(/\//g, '-');
    return db > da ? 1 : db < da ? -1 : 0;
  }).map((t) => {
    // Find absolute index in full array since we filtered
    const index = App.data.entries.indexOf(t);
    const isMissed = t['ステータス'] === '保有中（見逃し）';
    const badgeClass = t.Direction === 'Buy' ? 'buy' : 'sell';
    const dirArrow = t.Direction === 'Buy' ? '▲' : '▼';

    return `
      <div class="list-card" onclick="openTradeDetail(${index})" style="cursor:pointer; border-left: 4px solid ${isMissed ? '#f59e0b' : '#3b82f6'}">
        <div>
          <div style="font-weight:700; font-size:14px; margin-bottom:4px; display:flex; align-items:center; gap:8px;">
            ${t['PairName（元）'] || t.PairName || t.Pair || 'ペア不明'} 
            <span class="badge ${badgeClass}">${dirArrow} ${t.Direction || ''}</span>
            ${isMissed ? '<span class="badge" style="background:rgba(245,158,11,0.2); color:#f59e0b;">見逃し</span>' : ''}
          </div>
          <div style="font-size:11px; color:#94a3b8;">${formatDateDisplay(t.EntryDate)} ${formatTimeDisplay(t.EntryTime)} · ｽｺｱ: ${t['エントリースコア'] || '-'}</div>
        </div>
        <div style="color:#94a3b8; font-size:16px;">›</div>
      </div>
    `;
  }).join('');
}

function renderPairs() {
  const container = document.getElementById('pairs-list');
  if (App.data.pairs.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">ペアデータがありません</div>';
    return;
  }

  // Group by Flag (フラグ)
  const flags = ['待機', '狙い目', '注目', '様子見', 'その他'];
  let groups = {};
  flags.forEach(f => groups[f] = []);

  App.data.pairs.forEach(p => {
    let flag = p['フラグ'] || p['Flag'];
    if (!flag) flag = '様子見';
    if (!groups[flag]) flag = 'その他';
    groups[flag].push(p);
  });

  let html = '';
  flags.forEach(f => {
    if (groups[f].length === 0) return;

    // Assign color based on flag
    let color = '#94a3b8'; // default grey
    if (f === '待機') color = '#ef4444'; // Red
    if (f === '狙い目') color = '#3b82f6'; // Blue
    if (f === '注目') color = '#10b981'; // Green
    if (f === '様子見') color = '#e2e8f0'; // White/LightGrey

    html += `<div style="font-size:12px; font-weight:700; color:${color}; margin: 16px 0 8px 0; border-bottom:1px solid #334155; padding-bottom:4px;">■ ${f}</div>`;

    groups[f].forEach(p => {
      const pairName = p['PairName（元）'] || p['PairName'] || '';

      // Extract arrow from matching W1, D1, H4
      const w1 = p['W1'], d1 = p['D1'], h4 = p['H4'];
      let arrowHtml = '';
      if (w1 === '↑' && d1 === '↑' && h4 === '↑') {
        arrowHtml = `<span style="background:#ef4444; color:white; border-radius:2px; padding:0px 4px; font-size:10px; margin-left:6px;">↗</span>`;
      } else if (w1 === '↓' && d1 === '↓' && h4 === '↓') {
        arrowHtml = `<span style="background:#3b82f6; color:white; border-radius:2px; padding:0px 4px; font-size:10px; margin-left:6px;">↘</span>`;
      }

      html += `
        <div class="list-card" onclick="openPairEdit('${pairName}')" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center; padding:12px 16px; margin-bottom:4px; border-radius:8px; border:1px solid #1e293b;">
          <div style="font-weight:700; font-size:15px; display:flex; align-items:center; color:${color};">
            ${pairName} ${arrowHtml}
          </div>
          <div style="color:#64748b; font-size:18px;">›</div>
        </div>
      `;
    });
  });

  container.innerHTML = html;
}


// 画像URLキャッシュ（パスベース → base64 data URL）
const _imgUrlCache = {};

// 画像をアップロード前に圧縮する（max 800px, quality 0.75）
function compressImageForUpload(dataUrl, maxWidth = 800, quality = 0.75) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const ratio = Math.min(maxWidth / img.width, 1);
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * ratio);
      canvas.height = Math.round(img.height * ratio);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL('image/jpeg', quality));
    };
    img.onerror = () => resolve(dataUrl);
    img.src = dataUrl;
  });
}

// スプシ保存用：セル上限(50,000字)に収まるまで段階的に圧縮（フォールバック用）
async function compressForSpreadsheet(dataUrl) {
  const attempts = [[550, 0.70], [420, 0.65], [320, 0.60], [240, 0.55]];
  for (const [w, q] of attempts) {
    const result = await compressImageForUpload(dataUrl, w, q);
    if (result.length <= 45000) return result;
  }
  return compressImageForUpload(dataUrl, 200, 0.50);
}

// ImgBB に直接アップロード（高画質・無圧縮）
async function uploadToImgBB(dataUrl) {
  // キーはGASスクリプトプロパティから取得（メモリキャッシュ）
  if (!App.state.imgbbKey) {
    try {
      const res = await fetch(GAS_URL, { method: 'POST', body: JSON.stringify({ action: 'getImgBBKey' }) }).then(r => r.json());
      App.state.imgbbKey = res.key || '';
    } catch(e) { App.state.imgbbKey = ''; }
  }
  const apiKey = App.state.imgbbKey;
  if (!apiKey) return null;
  const base64 = dataUrl.replace(/^data:image\/\w+;base64,/, '');
  const formData = new FormData();
  formData.append('key', apiKey);
  formData.append('image', base64);
  const res = await fetch('https://api.imgbb.com/1/upload', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.success) return data.data.url;
  throw new Error(data.error?.message || 'ImgBB upload failed');
}

// ImgBB優先アップロード：失敗時はDrive→base64の順でフォールバック
async function uploadImageSmart(dataUrl, filename) {
  // 1) ImgBB（高画質・ブラウザから直接）
  try {
    const url = await uploadToImgBB(dataUrl);
    if (url) { console.log('ImgBB upload OK:', url); return url; }
  } catch (e) {
    console.warn('ImgBB upload failed:', e.message);
  }
  // 2) Drive経由（GAS）
  try {
    const compressed = await compressImageForUpload(dataUrl, 1200, 0.88);
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'uploadImage', base64Data: compressed, filename })
    }).then(r => r.json());
    if (res.success && res.fileId) {
      return 'drive_images/' + res.fileId + '.jpg';
    }
  } catch (e) {
    console.warn('Drive upload failed, fallback to base64:', e.message);
  }
  // 3) 最終フォールバック：base64をスプシに直接保存（低画質）
  return compressForSpreadsheet(dataUrl);
}

async function updateImgBBStatusBar() {
  const bar = document.getElementById('imgbb-status-bar');
  if (!bar) return;
  if (!App.state.imgbbKey) {
    try {
      const res = await fetch(GAS_URL, { method: 'POST', body: JSON.stringify({ action: 'getImgBBKey' }) }).then(r => r.json());
      App.state.imgbbKey = res.key || '';
    } catch(e) { App.state.imgbbKey = ''; }
  }
  if (App.state.imgbbKey) {
    bar.innerHTML = '✅ ImgBB 有効（高画質アップロード）';
    bar.style.color = '#10b981';
  } else {
    bar.innerHTML = '⚠️ ImgBB未設定　GASスクリプトプロパティに IMGBB_API_KEY を設定してください';
    bar.style.color = '#f59e0b';
  }
}

// エントリー写真専用（アプリアップロード or AppSheetエントリーチャート）
function findEntryImageField(t) {
  const entryKeys = ['ChartImage', 'EntryImage', 'エントリー画像', 'エントリーチャート', 'EntryChart', 'entry_image'];
  for (const k of entryKeys) {
    const v = t[k];
    if (v && String(v).trim() && String(v).trim() !== 'undefined') return String(v).trim();
  }
  return '';
}

// 決済写真専用（AppSheetの決済チャート列 etc.）
function findExitImageField(t) {
  const exitKeys = ['決済チャート', 'ExitImage', 'ExitChartImage', '決済画像', 'ExitChart', 'exit_image', 'CloseImage', 'ExitImg'];
  for (const k of exitKeys) {
    const v = t[k];
    if (v && String(v).trim() && String(v).trim() !== 'undefined') return String(v).trim();
  }
  return '';
}

// ギャラリー用：エントリー→決済の順で最初に見つかったものを返す
function findImageField(t) {
  const entry = findEntryImageField(t);
  if (entry) return entry;
  const exit = findExitImageField(t);
  if (exit) return exit;
  // フォールバック：画像/Image/Chart を含む任意カラム
  for (const [k, v] of Object.entries(t)) {
    if (!v || !String(v).trim()) continue;
    const kl = k.toLowerCase();
    if (kl.includes('image') || k.includes('画像') || kl.includes('chart') || k.includes('チャート')) {
      const sv = String(v).trim();
      if (sv && sv !== 'undefined' && sv !== '0') return sv;
    }
  }
  return '';
}

function getImageUrl(rawUrl) {
  if (!rawUrl) return '';
  const s = String(rawUrl).trim();
  if (!s || s === 'undefined' || s === 'null') return '';
  // Base64 data URL (アプリからアップロードした画像)
  if (s.startsWith('data:image')) return s;
  // lh3 / ggpht CDN
  if (s.startsWith('https://lh') || s.startsWith('https://ggpht')) return s;
  // Google Drive URL → thumbnail
  const m = s.match(/(?:id=|\/d\/|open\?id=)([a-zA-Z0-9_-]{15,})/);
  if (m) {
    const id = m[1].replace(/[^a-zA-Z0-9_-]/g, '');
    return `https://drive.google.com/thumbnail?id=${id}&sz=w800`;
  }
  // drive_images/xxxxxx.jpg 形式 → Google Drive サムネイルURL に変換
  if (s.startsWith('drive_images/')) {
    const fileId = s.replace('drive_images/', '').replace(/\.jpg$/i, '');
    return `https://drive.google.com/thumbnail?id=${fileId}&sz=w800`;
  }
  // AppSheet パス形式 (e.g. "Entries_Images/xxx.jpg")
  // キャッシュ済みなら返す
  if (s.includes('/') && !s.startsWith('http')) {
    return _imgUrlCache[s] || '';  // 空文字 → カメラ表示、非同期で解決
  }
  return s;
}

// AppSheetパス → base64 data URLをGASから取得してimgのsrcを更新する
// GASの同時実行制限を避けるため順番にfetchし、解決した画像から即時表示する
async function resolvePathImages(container) {
  const imgs = Array.from(container.querySelectorAll('img[data-path]'));
  if (!imgs.length) return;

  // 未キャッシュのパスを順番に処理（重複除去）
  const seen = new Set();
  const todo = imgs.filter(el => {
    const p = el.dataset.path;
    if (!p || seen.has(p)) return false;
    seen.add(p);
    // キャッシュ済み（data URL）はスキップ
    if (_imgUrlCache[p] && _imgUrlCache[p].startsWith('data:')) return false;
    return true;
  });

  for (const el of todo) {
    const path = el.dataset.path;
    try {
      const res = await fetch(`${GAS_URL}?action=getImageUrl&path=${encodeURIComponent(path)}`);
      const json = await res.json();
      const url = json?.data?.url || '';
      _imgUrlCache[path] = url;
    } catch (e) {
      _imgUrlCache[path] = '';
    }

    // このpathを持つ全imgを即時更新（解決次第すぐ表示）
    const url = _imgUrlCache[path] || '';
    if (url) {
      container.querySelectorAll(`img[data-path="${CSS.escape(path)}"]`).forEach(imgEl => {
        imgEl.src = url;
        imgEl.style.display = '';
        const cam = imgEl.closest('div')?.querySelector('.no-img-cam');
        if (cam) cam.style.display = 'none';
        makeTappable(imgEl); // ← 解決後にタップ拡大を有効化
      });
    }
  }
}

function renderGallery() {
  const container = document.getElementById('gallery-grid');
  // 画像があるトレードを日付降順（新しい順）で最大20件（決済画像優先）
  const galleryTrades = App.data.entries
    .filter(t => {
      const img = findExitImageField(t) || findEntryImageField(t);
      return img && img.trim() !== '';
    })
    .slice()
    .sort((a, b) => {
      const da = String(a.EntryDate || '').replace(/\//g, '-');
      const db = String(b.EntryDate || '').replace(/\//g, '-');
      return da < db ? 1 : -1;
    })
    .slice(0, 20);

  if (galleryTrades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;grid-column:1/-1;">画像がありません</div>';
    return;
  }

  let html = '';
  galleryTrades.forEach(t => {
    const index = App.data.entries.indexOf(t);
    const rawUrl = findExitImageField(t) || findEntryImageField(t);
    const isPath = rawUrl && rawUrl.includes('/') && !rawUrl.startsWith('http') && !rawUrl.startsWith('data:');
    const imgUrl = getImageUrl(rawUrl);
    const pips = parseFloat(t['実取得pips']) || 0;
    const isWin = pips > 10;
    const isEven = pips >= -5 && pips <= 10;
    const color = isWin ? '#10b981' : (isEven ? '#f59e0b' : '#ef4444');

    const imgTag = (imgUrl || isPath)
      ? `<img src="${imgUrl}" ${isPath ? `data-path="${rawUrl}"` : ''} style="width:100%;height:100%;object-fit:cover;${imgUrl ? '' : 'display:none;'}" referrerpolicy="no-referrer" onerror="this.style.display='none'; this.parentNode.querySelector('.no-img-cam').style.display='flex';">`
      : '';

    html += `
      <div onclick="openTradeDetail(${index})" style="background:#1e293b; border-radius:12px; overflow:hidden; border:1px solid #334155; cursor:pointer;">
        <div style="width:100%; height:120px; background:#0f172a; display:flex; align-items:center; justify-content:center; position:relative;">
          ${imgTag}
          <div class="no-img-cam" style="display:${imgUrl ? 'none' : 'flex'}; position:absolute; inset:0; align-items:center; justify-content:center; flex-direction:column; color:#334155; font-size:32px; pointer-events:none;">📷</div>
          <div style="position:absolute; top:4px; right:4px; background:rgba(15,23,42,0.8); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700; color:${color};">
            ${isWin ? '+' : ''}${pips.toFixed(1)}
          </div>
        </div>
        <div style="padding:8px;">
          <div style="font-weight:700; font-size:12px;">${t['PairName（元）'] || t.PairName || t.Pair || ''} ${t.Direction || ''}</div>
          <div style="font-size:10px; color:#94a3b8;">ｽｺｱ: ${t['エントリースコア'] || '-'} · ${formatDateDisplay(t.EntryDate)}</div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
  // パスベース画像を非同期で解決（解決後にmakeTappableが呼ばれる）
  resolvePathImages(container);
  // URL直接表示の画像にもタップ拡大を付ける
  container.querySelectorAll('img[src]:not([data-path])').forEach(makeTappable);
}

function renderRecentTrades() {
  const container = document.getElementById('recent-trades-list');
  if (!container) return;

  // 全決済（実トレード + 見逃し）を日付降順で最新20件
  const trades = App.data.entries
    .filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）')
    .slice()
    .sort((a, b) => {
      const da = String(a.EntryDate || '').replace(/\//g, '-');
      const db = String(b.EntryDate || '').replace(/\//g, '-');
      return da < db ? 1 : -1;
    })
    .slice(0, 20);

  if (trades.length === 0) {
    container.innerHTML = '<div style="color:#64748b; text-align:center; padding:12px;">データがありません</div>';
    return;
  }

  const fmtDate = (d) => {
    const s = String(d || '').split('T')[0].replace(/\//g, '-');
    if (!s) return '-';
    const parts = s.split('-');
    return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : s;
  };

  const rows = trades.map(t => {
    const pips = parseFloat(t['実取得pips']) || 0;
    const profit = parseFloat(t['損益']) || 0;
    const pair = t['PairName（元）'] || t['PairName'] || t['Pair'] || '-';
    const dir = t['Direction'] || t['方向'] || '';
    const isMissed = (t['ステータス'] || '').includes('見逃し');
    const pipsColor = pips > 0 ? '#10b981' : pips < 0 ? '#ef4444' : '#94a3b8';
    const pipsSign = pips > 0 ? '+' : '';
    const profitSign = profit > 0 ? '+' : '';
    const profitStr = profit !== 0
      ? `${profitSign}${new Intl.NumberFormat('ja-JP').format(profit)}円`
      : '-';
    const dirBadge = dir === 'Buy'
      ? `<span style="color:#10b981; font-size:10px;">▲Buy</span>`
      : dir === 'Sell'
        ? `<span style="color:#ef4444; font-size:10px;">▼Sell</span>`
        : '';
    const missedBadge = isMissed
      ? `<span style="color:#f59e0b; font-size:10px; margin-left:4px;">見逃し</span>`
      : '';

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:9px 12px; background:#1e293b; border-radius:8px; margin-bottom:6px; border:1px solid #334155;">
        <div style="min-width:34px; color:#94a3b8; font-size:11px;">${fmtDate(t.EntryDate)}</div>
        <div style="flex:1; padding:0 8px; font-size:13px; font-weight:700; color:#e2e8f0;">${pair} ${dirBadge}${missedBadge}</div>
        <div style="text-align:right; min-width:80px;">
          <div style="font-size:13px; font-weight:700; color:${pipsColor};">${pipsSign}${pips.toFixed(1)}<span style="font-size:10px;">pips</span></div>
          <div style="font-size:10px; color:${pipsColor}; opacity:0.85;">${profitStr}</div>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = rows;
}

// データの最新月と前月を返す（カレンダー月でなくデータ基準）
function getDataMonthRange() {
  const months = App.data.entries
    .filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）')
    .map(t => t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-').substring(0, 7) : '')
    .filter(Boolean).sort();
  const now = new Date();
  const nowStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const latest = months.length ? months[months.length - 1] : nowStr;
  const [y, m] = latest.split('-').map(Number);
  const prevDate = new Date(y, m - 2, 1);
  const prev = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;
  return { current: latest, last: prev };
}

// Monthly top stats: current month REAL trades only (独立・見逃し除外)
function updateMonthlyStats() {
  const { current: currentMonthStr } = getDataMonthRange();
  const monthTrades = App.data.entries.filter(t => {
    if (t['ステータス'] !== '決済') return false;
    const dateStr = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
    return dateStr.startsWith(currentMonthStr);
  });
  let totalProfit = 0, totalPips = 0, totalRR = 0;
  let entryPerfect = 0, exitPerfect = 0;
  monthTrades.forEach(t => {
    totalProfit += parseFloat(t['損益']) || 0;
    totalPips += parseFloat(t['実取得pips']) || 0;
    const pips = parseFloat(t['実取得pips']) || 0;
    const sl = parseFloat(t['StopLossPips']) || parseFloat(t['SL']) || 0;
    if (sl > 0) totalRR += pips / sl;
    if ((t['エントリー振り返り'] || '') === '完璧！') entryPerfect++;
    const exitRef = t['決済振り返り'] || '';
    if (exitRef === '完璧利確' || exitRef === '適切損切り') exitPerfect++;
  });
  const total = monthTrades.length;
  const fmtCur = (v) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(v);
  const cls = (v) => v > 0 ? 'pos' : (v < 0 ? 'neg' : '');
  const clsRate = (v) => v >= 70 ? 'pos' : (v >= 50 ? '' : 'neg');
  document.getElementById('top-profit').textContent = fmtCur(totalProfit);
  document.getElementById('top-profit').className = 'val ' + cls(totalProfit);
  document.getElementById('top-pips').textContent = Math.round(totalPips) + ' pips';
  document.getElementById('top-pips').className = 'val ' + cls(totalPips);
  const entryRate = total > 0 ? (entryPerfect / total * 100).toFixed(1) : '--';
  const exitRate = total > 0 ? (exitPerfect / total * 100).toFixed(1) : '--';
  document.getElementById('top-entry-rate').textContent = entryRate !== '--' ? entryRate + '%' : '--';
  document.getElementById('top-entry-rate').className = 'val ' + (entryRate !== '--' ? clsRate(parseFloat(entryRate)) : '');
  document.getElementById('top-exit-rate').textContent = exitRate !== '--' ? exitRate + '%' : '--';
  document.getElementById('top-exit-rate').className = 'val ' + (exitRate !== '--' ? clsRate(parseFloat(exitRate)) : '');
  document.getElementById('top-rr').textContent = totalRR.toFixed(2);
  document.getElementById('top-rr').className = 'val ' + cls(totalRR);
}

// ==========================================
// Analysis Logic
// ==========================================
function applyAnalysisFilters() {
  const fPeriod = document.getElementById('flt-period').value;
  const fPair = document.getElementById('flt-pair').value;
  const fStatus = document.getElementById('flt-status').value;
  const fTimezone = document.getElementById('flt-timezone').value;
  const fRule = document.getElementById('flt-rule').value;
  const fScore = document.getElementById('flt-score').value;
  const fEntryRef = document.getElementById('flt-entry-ref')?.value || 'all';
  const fExitRef = document.getElementById('flt-exit-ref')?.value || 'all';
  const dFrom = document.getElementById('flt-date-from').value;
  const dTo = document.getElementById('flt-date-to').value;

  // 1. Base filter: Closed trades only
  let filtered = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');

  // 2. Apply advanced filters
  const { current: currentMonthStr, last: lastMonthStr } = getDataMonthRange();

  // 属性フィルター（期間を除く）→ エクイティカーブが独自期間で使用
  filtered = filtered.filter(t => {
    if (fStatus === 'entry' && (t['ステータス'] || '').includes('見逃し')) return false;
    if (fStatus === 'missed' && !(t['ステータス'] || '').includes('見逃し')) return false;
    if (fPair !== 'all' && (t['PairName（元）'] || t.PairName || t.Pair) !== fPair) return false;
    if (fTimezone !== 'all' && t['時間帯'] !== fTimezone) return false;
    if (fRule !== 'all' && t.DowRule != fRule) return false;
    const score = parseInt(t['エントリースコア']) || 0;
    if (fScore === 'high' && score < 4) return false;
    if (fScore !== 'all' && fScore !== 'high' && score.toString() !== fScore) return false;
    if (fEntryRef !== 'all' && (t['エントリー振り返り'] || '') !== fEntryRef) return false;
    if (fExitRef !== 'all' && (t['決済振り返り'] || '') !== fExitRef) return false;
    return true;
  });
  App.state.analysisFilteredNoPeriod = filtered.slice(); // エクイティカーブ用（期間フィルタ前）

  // 期間フィルター（分析タブ用）
  filtered = filtered.filter(t => {
    const dateStr = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
    if (fPeriod === 'this_month' && !dateStr.startsWith(currentMonthStr)) return false;
    if (fPeriod === 'last_month' && !dateStr.startsWith(lastMonthStr)) return false;
    if (fPeriod === 'custom') {
      const tDate = new Date(dateStr);
      if (dFrom && tDate < new Date(dFrom)) return false;
      if (dTo && tDate > new Date(dTo + "T23:59:59")) return false;
    }
    return true;
  });

  let totalTrades = 0, wins = 0, losses = 0, evens = 0;
  let totalPips = 0, winPips = 0, lossPips = 0;
  let totalProfit = 0, winProfit = 0, lossProfit = 0;
  let totalLot = 0;
  let avgRRSum = 0, validRRCount = 0;
  // 理論値: ルール準拠pips/損益の合計（全トレード）
  let theoryPipsTotal = 0, theoryProfitTotal = 0;
  // ルール遵守率: エントリー・決済別
  let entryPerfectCount = 0, exitPerfectCount = 0;

  filtered.forEach(t => {
    totalTrades++;
    const pips = parseFloat(t['実取得pips']) || 0;
    const profit = parseFloat(t['損益']) || 0;
    const lot = parseFloat(t['Lot']) || 0;
    const entryRef = t['エントリー振り返り'] || '';
    const exitRef = t['決済振り返り'] || '';

    totalPips += pips;
    totalProfit += profit;
    totalLot += lot;

    // 勝敗判定: ±10pips閾値
    // 勝ち: pips > 10 / 負け: pips < -10 / 引き分け: -10 <= pips <= 10
    if (pips > 10) {
      wins++;
      winPips += pips;
      winProfit += profit;
    } else if (pips < -10) {
      losses++;
      lossPips += pips;
      lossProfit += profit;
    } else {
      evens++;
    }

    // RR: 実取得pips / StopLossPips
    const sl = parseFloat(t['StopLossPips']) || parseFloat(t['SL']) || 0;
    if (sl > 0) {
      avgRRSum += (pips / sl);
      validRRCount++;
    }

    // 理論pips: ルール準拠pips列の合計（全トレード）
    const rawRulePips = t['ルール準拠pips'] ?? t['ルール準拠Pips'];
    if (rawRulePips !== undefined && rawRulePips !== '' && rawRulePips !== null) {
      const rp = parseFloat(rawRulePips);
      if (!isNaN(rp)) theoryPipsTotal += rp;
    }
    // 理論損益: ルール準拠損益列の合計（手入力値）
    const rawRuleProfit = t['ルール準拠損益'];
    if (rawRuleProfit !== undefined && rawRuleProfit !== '' && rawRuleProfit !== null) {
      const rpProfit = parseFloat(rawRuleProfit);
      if (!isNaN(rpProfit)) theoryProfitTotal += rpProfit;
    }

    // エントリールール遵守率: エントリー振り返り = "完璧！"
    if (entryRef === '完璧！') entryPerfectCount++;
    // 決済ルール遵守率: 決済振り返り = "完璧利確" or "適切損切り"
    if (exitRef === '完璧利確' || exitRef === '適切損切り') exitPerfectCount++;
  });

  const winRate = totalTrades ? (wins / totalTrades * 100).toFixed(1) : 0;

  const avgWinPips = wins ? (winPips / wins).toFixed(1) : 0;
  const avgLossPips = losses ? (lossPips / losses).toFixed(1) : 0;
  const avgWinProfit = wins ? (winProfit / wins).toFixed(0) : 0;
  const avgLossProfit = losses ? (lossProfit / losses).toFixed(0) : 0;

  const avgTradePips = totalTrades ? (totalPips / totalTrades).toFixed(1) : 0;
  const avgTradeProfit = totalTrades ? (totalProfit / totalTrades).toFixed(0) : 0;
  const avgLot = totalTrades ? (totalLot / totalTrades).toFixed(2) : '0.00';

  const avgRR = validRRCount ? (avgRRSum / validRRCount).toFixed(2) : '--';
  const totalRR = avgRRSum.toFixed(2);

  // エントリー・決済ルール遵守率
  const entryComplianceRate = totalTrades > 0 ? (entryPerfectCount / totalTrades * 100).toFixed(1) : '--';
  const exitComplianceRate = totalTrades > 0 ? (exitPerfectCount / totalTrades * 100).toFixed(1) : '--';

  // 理論値 / ルール外乖離
  const theoryPips = theoryPipsTotal;
  const theoryProfit = theoryProfitTotal;
  const deviationPips = totalPips - theoryPips;
  const deviationProfit = totalProfit - theoryProfit;

  // Top banner is calculated independently by updateMonthlyStats()
  const fmtCurrency = (val) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(val);
  const classForNum = (val) => val > 0 ? 'pos' : (val < 0 ? 'neg' : '');

  const tbody = document.getElementById('analysis-tbody');
  tbody.innerHTML = `
    <div class="metrics-section-header">📊 基本統計</div>
    <div class="metric-card">
      <div class="metric-label">エントリー数</div>
      <div class="metric-value">${totalTrades}<span class="metric-unit">回</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝ち数</div>
      <div class="metric-value pos">${wins}<span class="metric-unit">回</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">負け数</div>
      <div class="metric-value neg">${losses}<span class="metric-unit">回</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">建値数</div>
      <div class="metric-value">${evens}<span class="metric-unit">回</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝率</div>
      <div class="metric-value ${classForNum(parseFloat(winRate) - 50)}">${winRate}<span class="metric-unit">%</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">平均Lot</div>
      <div class="metric-value">${avgLot}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">平均実RR</div>
      <div class="metric-value ${classForNum(parseFloat(avgRR))}">${avgRR}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">合計実RR</div>
      <div class="metric-value ${classForNum(parseFloat(totalRR))}">${totalRR}</div>
    </div>

    <div class="metrics-section-header">📋 ルール遵守</div>
    <div class="metric-card">
      <div class="metric-label">エントリールール遵守率</div>
      <div class="metric-value ${entryComplianceRate !== '--' ? classForNum(parseFloat(entryComplianceRate) - 70) : ''}">${entryComplianceRate}${entryComplianceRate !== '--' ? '<span class="metric-unit">%</span>' : ''}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">決済ルール遵守率</div>
      <div class="metric-value ${exitComplianceRate !== '--' ? classForNum(parseFloat(exitComplianceRate) - 70) : ''}">${exitComplianceRate}${exitComplianceRate !== '--' ? '<span class="metric-unit">%</span>' : ''}</div>
    </div>

    <div class="metrics-section-header">📈 pips統計</div>
    <div class="metric-card">
      <div class="metric-label">総取得pips</div>
      <div class="metric-value ${classForNum(totalPips)}">${totalPips.toFixed(1)}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">1トレード平均pips</div>
      <div class="metric-value ${classForNum(parseFloat(avgTradePips))}">${avgTradePips}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝ち合計pips</div>
      <div class="metric-value pos">${winPips.toFixed(1)}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝ち平均pips</div>
      <div class="metric-value pos">+${avgWinPips}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">負け合計pips</div>
      <div class="metric-value neg">${lossPips.toFixed(1)}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">負け平均pips</div>
      <div class="metric-value neg">${avgLossPips}<span class="metric-unit">pips</span></div>
    </div>

    <div class="metrics-section-header">💴 収支統計</div>
    <div class="metric-card">
      <div class="metric-label">総収支</div>
      <div class="metric-value ${classForNum(totalProfit)}" style="font-size:16px;">${fmtCurrency(totalProfit)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">1トレード平均損益</div>
      <div class="metric-value ${classForNum(parseFloat(avgTradeProfit))}" style="font-size:15px;">${fmtCurrency(parseInt(avgTradeProfit))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝ち合計損益</div>
      <div class="metric-value pos" style="font-size:15px;">${fmtCurrency(winProfit)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">勝ち平均損益</div>
      <div class="metric-value pos" style="font-size:15px;">${fmtCurrency(parseInt(avgWinProfit))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">負け合計損益</div>
      <div class="metric-value neg" style="font-size:15px;">${fmtCurrency(lossProfit)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">負け平均損益</div>
      <div class="metric-value neg" style="font-size:15px;">${fmtCurrency(parseInt(avgLossProfit))}</div>
    </div>

    <div class="metrics-section-header">🔮 理論値</div>
    <div class="metric-card">
      <div class="metric-label">理論pips</div>
      <div class="metric-value ${classForNum(theoryPips)}">${theoryPips.toFixed(1)}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">理論損益</div>
      <div class="metric-value ${classForNum(theoryProfit)}" style="font-size:15px;">${fmtCurrency(Math.round(theoryProfit))}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">ルール外乖離pips</div>
      <div class="metric-value ${classForNum(deviationPips)}">${deviationPips > 0 ? '+' : ''}${deviationPips.toFixed(1)}<span class="metric-unit">pips</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">ルール外乖離額</div>
      <div class="metric-value ${classForNum(deviationProfit)}" style="font-size:15px;">${deviationProfit >= 0 ? '+' : ''}${fmtCurrency(Math.round(deviationProfit))}</div>
    </div>
  `;

  renderDrawdown(filtered);
  App.state.analysisFiltered = filtered; // チャートバークリック時の絞り込みに使用
  renderHeatmap(filtered);
  renderGrowthChart(filtered);
  renderEquityCurve();
}

function renderDrawdown(trades) {
  const container = document.getElementById('drawdown-section');
  if (!container) return;
  const fmtCurrency = (val) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(val);

  if (trades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;grid-column:1/-1;">データがありません</div>';
    return;
  }

  // 日付昇順でソート
  const sorted = trades.slice().sort((a, b) => {
    const da = String(a.EntryDate || '').split('T')[0].replace(/\//g, '-');
    const db = String(b.EntryDate || '').split('T')[0].replace(/\//g, '-');
    return da < db ? -1 : da > db ? 1 : 0;
  });

  // 累計損益・ドローダウン計算
  let cumulative = 0, peak = 0, maxDD = 0, currentDD = 0;
  let maxStreak = 0, currentStreak = 0;
  let peakCumulative = 0;

  sorted.forEach(t => {
    const profit = parseFloat(t['損益']) || 0;
    const wl = t['勝敗'] || '';
    cumulative += profit;

    if (cumulative > peak) {
      peak = cumulative;
      peakCumulative = cumulative;
    }

    const dd = peak - cumulative;
    if (dd > maxDD) maxDD = dd;
    currentDD = dd;

    // 連敗カウント
    if (wl === '負け') {
      currentStreak++;
      if (currentStreak > maxStreak) maxStreak = currentStreak;
    } else if (wl === '勝ち') {
      currentStreak = 0;
    }
  });

  // 回復係数 = 総利益 / 最大DD（総利益がプラスの場合のみ）
  const totalProfit = cumulative;
  const recoveryFactor = (maxDD > 0 && totalProfit > 0) ? (totalProfit / maxDD) : null;

  const ddColor = currentDD > 0 ? '#f87171' : '#10b981';
  const ddLabel = currentDD <= 0 ? '✅ 最高益更新中' : '-' + fmtCurrency(Math.round(currentDD));
  const rfColor = recoveryFactor === null ? '#64748b' : (recoveryFactor >= 2 ? '#10b981' : recoveryFactor >= 1 ? '#f59e0b' : '#f87171');
  const rfText = recoveryFactor === null ? '—' : recoveryFactor.toFixed(2);

  container.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">最大ドローダウン</div>
      <div class="metric-value neg">-${fmtCurrency(Math.round(maxDD))}</div>
      <div class="metric-sub">ピークから最大落差</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">現在のドローダウン</div>
      <div class="metric-value" style="color:${ddColor};">${ddLabel}</div>
      <div class="metric-sub">直近ピークから</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">最大連敗数</div>
      <div class="metric-value neg">${maxStreak}<span class="metric-unit">連敗</span></div>
    </div>
    <div class="metric-card">
      <div class="metric-label">回復係数</div>
      <div class="metric-value" style="color:${rfColor};">${rfText}</div>
      <div class="metric-sub">総利益 ÷ 最大DD（2以上が健全）</div>
    </div>
  `;
}

function renderHeatmap(trades) {
  const container = document.getElementById('chart-heatmap');
  if (trades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">データがありません</div>';
    return;
  }

  // Aggregate by hour (0-23) and weekday (0=Mon..4=Fri)
  const grid = {};
  let plottedCount = 0;
  for (let h = 0; h < 24; h++) for (let d = 0; d < 5; d++) grid[`${h}-${d}`] = { count: 0, pips: 0 };

  trades.forEach(t => {
    // EntryTime: GASはtime cellを'1899/12/30'等で返す場合がある → HH:MMのみ受け付ける
    let timeStr = '';
    const rawTime = String(t.EntryTime || t['EntryTime'] || '').trim();
    if (/^\d{1,2}:\d{2}/.test(rawTime)) {
      timeStr = rawTime.substring(0, 5);
    } else {
      // EntryDateがISO datetime形式なら時刻を抽出 (例: 2025-10-12T15:00:00.000Z)
      timeStr = formatTimeDisplay(t.EntryDate) || '';
    }
    // 日付: スラッシュをダッシュに統一
    const dateStr = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
    if (!timeStr || !dateStr) return;
    const hour = parseInt(timeStr.split(':')[0]);
    if (isNaN(hour) || hour < 0 || hour > 23) return;
    const dow = new Date(dateStr + 'T00:00:00').getDay(); // ローカル時刻で曜日取得
    if (dow < 1 || dow > 5) return;
    const key = `${hour}-${dow - 1}`;
    grid[key].count++;
    grid[key].pips += parseFloat(t['実取得pips']) || 0;
    plottedCount++;
  });

  // 時刻データが1件もない場合はメッセージ表示
  if (plottedCount === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;font-size:13px;">時刻データがありません<br><span style="font-size:11px;">EntryTimeカラム(HH:MM形式)が必要です</span></div>';
    return;
  }

  const maxCount = Math.max(...Object.values(grid).map(c => c.count), 1);
  const days = ['月', '火', '水', '木', '金'];

  let html = '<div style="display:grid; grid-template-columns: 28px repeat(5, 1fr); gap:2px; width:100%; text-align:center;">';
  html += '<div></div>';
  days.forEach(d => html += `<div style="font-size:10px; color:#94a3b8; padding-bottom:4px;">${d}</div>`);

  for (let h = 0; h < 24; h++) {
    html += `<div style="font-size:9px; color:#64748b; text-align:right; padding-right:3px; display:flex; align-items:center; justify-content:flex-end;">${String(h).padStart(2, '0')}</div>`;
    for (let d = 0; d < 5; d++) {
      const cell = grid[`${h}-${d}`];
      let color = 'transparent';
      if (cell.count > 0) {
        const intensity = Math.min(cell.count / maxCount, 1) * 0.6 + 0.25;
        color = cell.pips >= 0 ? `rgba(16,185,129,${intensity})` : `rgba(239,68,68,${intensity})`;
      }
      html += `<div style="background:${color}; border-radius:2px; min-height:7px; border:1px solid #1e293b;"></div>`;
    }
  }
  html += '</div>';
  container.innerHTML = html;
  container.style.height = 'auto';
}

let activeChartType = 'profit';

function toggleChartType(type) {
  activeChartType = type;
  document.querySelectorAll('#chart-type-toggle .toggle-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`#chart-type-toggle .toggle-btn[onclick="toggleChartType('${type}')"]`).classList.add('active');
  applyAnalysisFilters(); // Re-apply filters which will call renderGrowthChart with filtered data
}

function renderGrowthChart(allTrades) {
  const container = document.getElementById('chart-growth');

  // Base it on CLOSED trades only for the chart
  const history = allTrades.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');
  if (history.length === 0) {
    container.innerHTML = 'データがありません';
    return;
  }

  // Aggregate by Month
  const monthly = {}; // { 'YYYY-MM': { profit: 0, pips: 0, rrSum: 0, rrCount: 0 } }
  history.forEach(t => {
    const d = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
    if (!d) return;
    const monthKey = d.substring(0, 7); // YYYY-MM
    if (!monthly[monthKey]) monthly[monthKey] = { profit: 0, pips: 0, rrSum: 0, rrCount: 0 };

    monthly[monthKey].profit += (parseFloat(t['損益']) || 0);
    monthly[monthKey].pips += (parseFloat(t['実取得pips']) || 0);

    const sl = parseFloat(t['StopLossPips']) || parseFloat(t['SL']) || 0;
    const pps = parseFloat(t['実取得pips']) || 0;
    if (sl > 0) {
      monthly[monthKey].rrSum += (pps / sl);
      monthly[monthKey].rrCount++;
    }
  });

  // Build last 6 calendar months (fixed range, fills 0 for empty months)
  const now2 = new Date();
  const last6 = [];
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now2.getFullYear(), now2.getMonth() - i, 1);
    last6.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }

  // Extract Data Series
  const labels = last6.map(m => m.substring(5, 7) + '月');
  let dataPoints = [];

  if (activeChartType === 'profit') {
    dataPoints = last6.map(m => monthly[m] ? monthly[m].profit : 0);
  } else if (activeChartType === 'pips') {
    dataPoints = last6.map(m => monthly[m] ? monthly[m].pips : 0);
  } else if (activeChartType === 'rr') {
    dataPoints = last6.map(m => monthly[m] ? monthly[m].rrSum : 0); // Sum of RR
  }

  if (dataPoints.every(v => v === 0)) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:40px;">データがありません</div>';
    return;
  }

  const maxVal = Math.max(...dataPoints, 0);
  const minVal = Math.min(...dataPoints, 0);
  const range = (maxVal - minVal) || 1;
  const zeroY = 100 - ((0 - minVal) / range * 80); // Calculate Y position for 0-line in SVG (20-100 range)

  const barWidth = 100 / Math.max(labels.length, 5); // % width

  let barsHTML = '';
  labels.forEach((lbl, i) => {
    const val = dataPoints[i];
    const isPos = val >= 0;
    const heightPct = Math.abs(val) / range * 80;

    // Y coordinate (SVG 0 is at top)
    const y = isPos ? (zeroY - heightPct) : zeroY;
    const color = isPos ? '#10b981' : '#ef4444';
    const x = (i * (100 / labels.length)) + (50 / labels.length);

    let dispVal = val;
    if (activeChartType === 'profit') {
      // Show as integers with comma (e.g. 12,500 or -3,200), no k abbreviation
      dispVal = Math.round(val).toLocaleString('ja-JP');
    } else if (activeChartType === 'rr') {
      dispVal = val.toFixed(2);
    } else {
      dispVal = Math.round(val).toLocaleString('ja-JP');
    }

    barsHTML += `
      <g onclick="openHistoryForMonth('${last6[i]}')" style="cursor:pointer;">
        <rect x="${x - (barWidth * 0.48)}%" y="8%" width="${barWidth * 0.96}%" height="89%" fill="transparent" />
        <rect x="${x - (barWidth * 0.38)}%" y="${y}%" width="${barWidth * 0.76}%" height="${Math.max(heightPct, 0.5)}%" fill="${color}" rx="1.5" />
        <text x="${x}%" y="${isPos ? Math.max(y - 1.5, 2) : y + heightPct + 4.5}%" fill="${color}" font-size="3.8" text-anchor="middle" font-weight="bold">${dispVal}</text>
        <text x="${x}%" y="97%" fill="#94a3b8" font-size="4.5" text-anchor="middle">${lbl}</text>
      </g>
    `;
  });

  // Y-axis unit label
  const unitLabel = activeChartType === 'profit' ? '円' : activeChartType === 'rr' ? 'RR' : 'pips';

  const svg = `
    <svg width="100%" height="100%" viewBox="0 0 100 110" preserveAspectRatio="none" style="overflow:visible;">
      <style>@keyframes fadeIn { to { opacity: 1; } }</style>
      <!-- Unit label top-left -->
      <text x="1" y="5" fill="#64748b" font-size="4.5" text-anchor="start">(${unitLabel})</text>
      <!-- Zero Line -->
      <line x1="0" y1="${zeroY}%" x2="100%" y2="${zeroY}%" stroke="#475569" stroke-width="0.8" stroke-dasharray="2,1.5" />
      ${barsHTML}
    </svg>
  `;
  container.innerHTML = svg;
}

// ==========================================
// Equity Curve
// ==========================================
let activeEquityPeriod = 'all';

function setEquityPeriod(period) {
  activeEquityPeriod = period;
  document.querySelectorAll('#equity-period-toggle .toggle-btn').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`#equity-period-toggle .toggle-btn[onclick="setEquityPeriod('${period}')"]`);
  if (btn) btn.classList.add('active');
  const customDiv = document.getElementById('equity-custom-date');
  if (customDiv) customDiv.style.display = period === 'custom' ? 'flex' : 'none';
  // カスタム選択時：デフォルトで1ヶ月を入力
  if (period === 'custom') {
    const to = new Date();
    const from = new Date();
    from.setMonth(from.getMonth() - 1);
    const fromEl = document.getElementById('equity-date-from');
    const toEl = document.getElementById('equity-date-to');
    if (fromEl && !fromEl.value) fromEl.value = from.toISOString().split('T')[0];
    if (toEl && !toEl.value) toEl.value = to.toISOString().split('T')[0];
  }
  renderEquityCurve();
}

function renderEquityCurve() {
  const container = document.getElementById('chart-equity');
  if (!container) return;
  const fmt = (val) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(Math.round(val));

  let trades = (App.state.analysisFilteredNoPeriod || []).slice();

  // エクイティカーブ独自の期間フィルター
  const now = new Date();
  const eFrom = document.getElementById('equity-date-from')?.value;
  const eTo = document.getElementById('equity-date-to')?.value;
  if (activeEquityPeriod !== 'all') {
    trades = trades.filter(t => {
      const dateStr = t.EntryDate ? String(t.EntryDate).split('T')[0].replace(/\//g, '-') : '';
      const tDate = new Date(dateStr);
      if (activeEquityPeriod === '6m') return tDate >= new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
      if (activeEquityPeriod === '3m') return tDate >= new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
      if (activeEquityPeriod === 'custom') {
        if (eFrom && tDate < new Date(eFrom)) return false;
        if (eTo && tDate > new Date(eTo + 'T23:59:59')) return false;
      }
      return true;
    });
  }

  if (trades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:40px;">データがありません</div>';
    return;
  }

  // 日付昇順ソート
  trades.sort((a, b) => {
    const da = String(a.EntryDate || '').split('T')[0].replace(/\//g, '-');
    const db = String(b.EntryDate || '').split('T')[0].replace(/\//g, '-');
    return da < db ? -1 : da > db ? 1 : 0;
  });

  // 累計損益を計算
  let cum = 0;
  const points = trades.map(t => {
    cum += parseFloat(t['損益']) || 0;
    return { cum, trade: t };
  });

  // 座標計算
  const allCums = [0, ...points.map(p => p.cum)];
  const maxVal = Math.max(...allCums);
  const minVal = Math.min(...allCums);
  const range = (maxVal - minVal) || 1;
  const pL = 12, pR = 99, pT = 6, pB = 72;
  const n = points.length;
  const toX = (i) => pL + (i / n) * (pR - pL);
  const toY = (v) => pB - ((v - minVal) / range) * (pB - pT);

  // 座標配列（原点 + 各トレード）
  const coords = [{ x: pL, y: toY(0), cum: 0 }];
  points.forEach((p, i) => coords.push({ x: toX(i + 1), y: toY(p.cum), cum: p.cum, trade: p.trade }));

  // ラインパス
  const pathD = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(2)},${c.y.toFixed(2)}`).join(' ');

  // ドローダウン塗りつぶし
  let ddPaths = '';
  let peak = 0, inDD = false, ddStart = 0;
  for (let i = 0; i < coords.length; i++) {
    const c = coords[i];
    if (c.cum > peak) {
      if (inDD) {
        const seg = coords.slice(ddStart, i + 1);
        const peakY = toY(peak).toFixed(2);
        const fwd = seg.map(s => `${s.x.toFixed(2)},${s.y.toFixed(2)}`).join(' ');
        const bwd = seg.slice().reverse().map(s => `${s.x.toFixed(2)},${peakY}`).join(' ');
        ddPaths += `<polygon points="${fwd} ${bwd}" fill="rgba(239,68,68,0.18)" />`;
        inDD = false;
      }
      peak = c.cum;
    } else if (c.cum < peak && !inDD) {
      inDD = true; ddStart = i - 1;
    }
  }
  if (inDD) {
    const seg = coords.slice(ddStart);
    const peakY = toY(peak).toFixed(2);
    const fwd = seg.map(s => `${s.x.toFixed(2)},${s.y.toFixed(2)}`).join(' ');
    const bwd = seg.slice().reverse().map(s => `${s.x.toFixed(2)},${peakY}`).join(' ');
    ddPaths += `<polygon points="${fwd} ${bwd}" fill="rgba(239,68,68,0.18)" />`;
  }

  // データ点（クリック可能）
  window._equityPoints = points;
  let circles = '';
  points.forEach((p, i) => {
    const c = coords[i + 1];
    const col = (parseFloat(p.trade['損益']) || 0) >= 0 ? '#10b981' : '#ef4444';
    circles += `<circle cx="${c.x.toFixed(2)}" cy="${c.y.toFixed(2)}" r="1.8" fill="${col}" stroke="#0f172a" stroke-width="0.4" style="cursor:pointer;" onclick="showEquityTooltip(event,${i})" />`;
  });

  // Y軸ラベル
  let yLabels = '';
  for (let i = 0; i <= 4; i++) {
    const v = minVal + (range * i / 4);
    const y = toY(v);
    const lbl = Math.abs(v) >= 10000 ? (v / 10000).toFixed(1) + '万' : Math.round(v).toLocaleString();
    yLabels += `<text x="${pL - 1}" y="${y.toFixed(2)}" fill="#64748b" font-size="3" text-anchor="end" dominant-baseline="middle">${lbl}</text>`;
  }

  // ゼロライン
  const zeroY = toY(0);
  const zeroLine = (minVal < 0 && maxVal > 0)
    ? `<line x1="${pL}" y1="${zeroY.toFixed(2)}" x2="${pR}" y2="${zeroY.toFixed(2)}" stroke="#475569" stroke-width="0.6" stroke-dasharray="2,1.5" />`
    : '';

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 100 80" preserveAspectRatio="none" style="overflow:visible;">
      <text x="${pL}" y="3.5" fill="#64748b" font-size="2.8" text-anchor="start">(円)</text>
      ${yLabels}
      ${zeroLine}
      ${ddPaths}
      <path d="${pathD}" fill="none" stroke="#38bdf8" stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round" />
      ${circles}
    </svg>`;
}

function showEquityTooltip(event, index) {
  const p = window._equityPoints?.[index];
  if (!p) return;
  const tooltip = document.getElementById('equity-tooltip');
  if (!tooltip) return;
  const fmt = (val) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(Math.round(val));
  const profit = parseFloat(p.trade['損益']) || 0;
  const pips = parseFloat(p.trade['実取得pips']) || 0;
  const pair = p.trade['PairName（元）'] || p.trade.PairName || p.trade.Pair || '';
  const dir = p.trade.Direction || '';
  const dateStr = p.trade.EntryDate ? String(p.trade.EntryDate).split('T')[0].replace(/\//g, '-') : '';
  const pc = profit >= 0 ? '#10b981' : '#ef4444';
  const cc = p.cum >= 0 ? '#10b981' : '#ef4444';
  tooltip.innerHTML = `
    <div style="font-size:10px;color:#64748b;margin-bottom:2px;">${dateStr}</div>
    <div style="font-weight:700;margin-bottom:3px;">${pair} ${dir}</div>
    <div style="color:${pc};">${fmt(profit)} / ${pips >= 0 ? '+' : ''}${pips.toFixed(1)}pips</div>
    <div style="color:${cc};font-size:10px;margin-top:2px;">累計: ${fmt(p.cum)}</div>`;
  tooltip.style.display = 'block';
  const rect = document.getElementById('chart-equity').getBoundingClientRect();
  const cx = (event.touches?.[0] || event).clientX;
  const cy = (event.touches?.[0] || event).clientY;
  let left = cx - rect.left + 12;
  let top = cy - rect.top - 70;
  if (left + 150 > rect.width) left = cx - rect.left - 155;
  if (top < 0) top = cy - rect.top + 12;
  tooltip.style.left = left + 'px';
  tooltip.style.top = top + 'px';
  clearTimeout(window._eqTipTimer);
  window._eqTipTimer = setTimeout(() => { tooltip.style.display = 'none'; }, 3000);
  event.stopPropagation();
}

// ==========================================
// Pair Edit
// ==========================================
function openPairEdit(pairName) {
  const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);
  if (!p) return;

  document.getElementById('pe-pair-name').value = pairName;
  document.getElementById('pe-title').textContent = pairName;
  document.getElementById('pe-flag').value = p['フラグ'] || '様子見';
  document.getElementById('pe-memo').value = p['環境認識メモ'] || p['メモ'] || '';

  const setBtn = (groupId, val) => {
    const btns = document.querySelectorAll(`#${groupId} .toggle-btn`);
    btns.forEach(b => {
      b.classList.remove('active');
      if (val && b.textContent.trim() === val) b.classList.add('active');
    });
  };

  setBtn('pe-tf-m1', p['M1']);
  setBtn('pe-tf-w1', p['W1']);
  setBtn('pe-tf-d1', p['D1']);
  setBtn('pe-tf-h4', p['H4']);
  setBtn('pe-tf-h1', p['H1']);

  setBtn('pe-ma-kairi', p['H4MA乖離']);
  setBtn('pe-ma-480', p['H4MA480.1200']);
  setBtn('pe-ma-h1-20', p['H1MA20.80']);
  setBtn('pe-ma-h4-20', p['H4MA20.80']);

  App.state.modalOpenedAt = Date.now();
  const _pm = document.getElementById('modal-pair-edit');
  _pm.classList.add('active');
  requestAnimationFrame(() => { _pm.querySelector('.modal-body').scrollTop = 0; });
}

function closePairEdit() {
  document.getElementById('modal-pair-edit').classList.remove('active');
}

async function savePairEdit() {
  showLoader();
  try {
    const pairName = document.getElementById('pe-pair-name').value;
    const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);
    if (!p) throw new Error('ペアが見つかりません');

    const getBtnVal = (groupId) => {
      const btn = document.querySelector(`#${groupId} .toggle-btn.active`);
      return btn ? btn.textContent.trim() : '';
    };

    const updateData = {
      'フラグ':        document.getElementById('pe-flag').value,
      '環境認識メモ':  document.getElementById('pe-memo').value,
      'メモ':          document.getElementById('pe-memo').value,
      'M1':            getBtnVal('pe-tf-m1'),
      'W1':            getBtnVal('pe-tf-w1'),
      'D1':            getBtnVal('pe-tf-d1'),
      'H4':            getBtnVal('pe-tf-h4'),
      'H1':            getBtnVal('pe-tf-h1'),
      'H4MA乖離':      getBtnVal('pe-ma-kairi'),
      'H4MA480.1200':  getBtnVal('pe-ma-480'),
      'H1MA20.80':     getBtnVal('pe-ma-h1-20'),
      'H4MA20.80':     getBtnVal('pe-ma-h4-20'),
    };

    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'updatePair', pairName, data: updateData })
    }).then(r => r.json());
    if (!res.success) throw new Error(res.error || '保存失敗');

    // ローカルにも反映
    Object.assign(p, updateData);

    closePairEdit();
    renderPairs();
    showToast('ペア情報を更新しました');
  } catch (e) {
    alert('エラーが発生しました: ' + e.message);
  } finally {
    hideLoader();
  }
}

// ==========================================
// Entry Logic
// ==========================================
function toggleBtn(btn, siblingSelector = '') {
  const parent = btn.parentElement;

  // If the button is already active, UNSELECT it and return
  if (btn.classList.contains('active')) {
    btn.classList.remove('active');

    // If we are unselecting a direction button, we don't necessarily need to trigger auto MA updates since there is no direction anymore
    if (btn.closest('#modal-entry')) calculateEntryScore();
    if (btn.closest('#modal-trade-detail')) calculateEntryScoreTD();
    return;
  }

  // Otherwise, behave normally: unselect others and select this one
  if (!siblingSelector) {
    Array.from(parent.children).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  } else {
    document.querySelectorAll(siblingSelector).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  }

  // If direction was changed, automatically update MAs (but do NOT reset direction buttons)
  if (btn.classList.contains('dir-up') || btn.classList.contains('dir-down') ||
    btn.classList.contains('dir-buy') || btn.classList.contains('dir-sell') ||
    btn.textContent.includes('Buy') || btn.textContent.includes('Sell')) {
    if (btn.closest('#ne-dir')) autoLoadPairInfo('ne', false);
    if (btn.closest('#td-dir')) autoLoadPairInfo('td', false);
  }

  // Recalculate score on any click inside entry or detail
  if (btn.closest('#modal-entry')) calculateEntryScore();
  if (btn.closest('#modal-trade-detail')) calculateEntryScoreTD();
}

// ==========================================
// 新規エントリーモーダル用リベンジトレード警告
// ==========================================
function showEntryRevengeAlert() {
  const alertDiv = document.getElementById('ne-revenge-alert');
  if (!alertDiv) return;

  const alerts = [];

  // ── ① 直近損失警告（実トレードのみ：見逃し除外） ──
  const realTrades = App.data.entries
    .filter(t => t['ステータス'] === '決済')
    .slice()
    .sort((a, b) => {
      const da = String(a.EntryDate || '').replace(/\//g, '-');
      const db = String(b.EntryDate || '').replace(/\//g, '-');
      return da < db ? 1 : -1;
    });
  if (realTrades.length > 0) {
    const last = realTrades[0];
    const pips = parseFloat(last['実取得pips']) || 0;
    if (pips < 0) {
      const pair = last['PairName（元）'] || last['PairName'] || last['Pair'] || '不明';
      const profit = parseFloat(last['損益']) || 0;
      const fmtProfit = new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(profit);
      alerts.push({
        icon: '🔴',
        bg: 'rgba(239,68,68,0.12)',
        border: '#ef4444',
        color: '#fca5a5',
        msg: `<strong>直近トレードが損失です。</strong><br>📌 ${pair}：${pips.toFixed(1)}pips　${fmtProfit}<br>冷静に、このエントリーがルールに合致しているか確認してください。`
      });
    }
  }

  // ── ② 連勝 / 連敗カウント（実トレードのみ：見逃し除外） ──
  // pipsが空/0の場合は損益(円)で勝ち負けを判定（フォールバック）
  function tradeSign(t) {
    const pip = parseFloat(t['実取得pips']);
    if (!isNaN(pip) && pip !== 0) return pip > 0 ? 1 : -1;
    const profit = parseFloat(t['損益']);
    if (!isNaN(profit) && profit !== 0) return profit > 0 ? 1 : -1;
    return 0; // 判定不能
  }
  let streak = 0, isWinStreak = false, isLossStreak = false;
  for (const t of realTrades) {
    const sign = tradeSign(t);
    if (streak === 0) {
      if (sign < 0) { isLossStreak = true; streak = 1; }
      else if (sign > 0) { isWinStreak = true; streak = 1; }
      else continue; // 判定不能トレードはスキップ
    } else {
      if (isLossStreak && sign < 0) streak++;
      else if (isWinStreak && sign > 0) streak++;
      else break;
    }
  }
  if (isLossStreak && streak >= 2) {
    alerts.push({
      icon: '⚠️',
      bg: 'rgba(220,38,38,0.15)',
      border: '#ef4444',
      color: '#fca5a5',
      msg: `<strong>${streak}連敗中です。</strong><br>焦って取り返そうとするリベンジトレードになっていませんか？<br>深呼吸して、このエントリーがルールに合致しているか再確認してください。`
    });
  } else if (isWinStreak && streak >= 2) {
    alerts.push({
      icon: '🎉',
      bg: 'rgba(16,185,129,0.15)',
      border: '#10b981',
      color: '#6ee7b7',
      msg: `<strong>${streak}連勝中です。</strong><br>調子が良いときほど慢心に注意。ロットを上げたり、雑なエントリーになっていませんか？<br>引き続きルール通りに丁寧にトレードしましょう。`
    });
  }

  // ── ③ ポジポジ病（直近2週間の実トレード数：見逃し除外） ──
  const twoWeeksAgo = new Date();
  twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14);
  const recentCount = App.data.entries.filter(t => {
    const st = t['ステータス'] || '';
    if (st === '決済（見逃し）' || st === '保有中（見逃し）') return false;
    const d = String(t.EntryDate || '').split('T')[0].replace(/\//g, '-');
    return d && new Date(d) >= twoWeeksAgo;
  }).length;
  if (recentCount >= 5) {
    alerts.push({
      icon: '💡',
      bg: 'rgba(245,158,11,0.15)',
      border: '#f59e0b',
      color: '#fcd34d',
      msg: `<strong>直近2週間で ${recentCount}回 のエントリーになります。</strong><br>ポジポジ病になっていませんか？優位性の高いポイントだけを厳選しましょう。`
    });
  }

  // ── ④ 直近トレードのルール遵守チェック（実トレードのみ・最後に表示） ──
  if (realTrades.length > 0) {
    const last = realTrades[0];
    const entryRef = last['エントリー振り返り'] || '';
    const exitRef = last['決済振り返り'] || '';
    const pair = last['PairName（元）'] || last['PairName'] || last['Pair'] || '前回';
    const isPerfectEntry = entryRef === '完璧！';
    const isPerfectExit = exitRef === '完璧利確';

    if (!isPerfectEntry || !isPerfectExit) {
      const parts = [];
      if (!isPerfectEntry && entryRef) parts.push(`エントリーが「${entryRef}」`);
      if (!isPerfectExit && exitRef) parts.push(`決済が「${exitRef}」`);
      const detail = parts.length > 0
        ? `${pair} のトレードで${parts.join('、')}でした。`
        : `${pair} のトレードはルール遵守が確認できません。`;
      alerts.push({
        icon: '📋',
        bg: 'rgba(100,116,139,0.15)',
        border: '#64748b',
        color: '#cbd5e1',
        msg: `<strong>直近トレードのルール振り返り</strong><br>${detail}<br>同じ失敗を繰り返さないよう、今回のエントリー条件を再確認しましょう。`
      });
    }
  }

  // ── 描画 ──
  const sectionDiv = document.getElementById('ne-recent-analysis-section');
  if (alerts.length > 0) {
    if (sectionDiv) sectionDiv.style.display = 'block';
    alertDiv.innerHTML = alerts.map(a => `
      <div style="display:flex; gap:10px; align-items:flex-start; background:${a.bg}; border:1px solid ${a.border}; border-radius:10px; padding:10px 12px; margin-bottom:8px;">
        <span style="font-size:20px; line-height:1.4;">${a.icon}</span>
        <div style="font-size:12px; color:${a.color}; line-height:1.6;">${a.msg}</div>
      </div>
    `).join('');
  } else {
    if (sectionDiv) sectionDiv.style.display = 'none';
    alertDiv.innerHTML = '';
  }
}

function analyzeMentalMode() {
  const alertBox = document.getElementById('ne-mental-alert');
  if (!alertBox) return;

  const history = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）').slice().reverse();
  if (history.length === 0) {
    alertBox.style.display = 'none';
    return;
  }

  let streak = 0;
  let isWinStreak = false;
  let isLossStreak = false;

  for (let i = 0; i < history.length; i++) {
    const pips = parseFloat(history[i]['実取得pips']) || 0;
    const isWin = pips > 10;
    const isLoss = pips < -5;

    if (i === 0) {
      if (isWin) isWinStreak = true;
      else if (isLoss) isLossStreak = true;
      streak = 1;
      continue;
    }

    if (isWinStreak && isWin) streak++;
    else if (isLossStreak && isLoss) streak++;
    else break;
  }

  const now = new Date();
  const currentMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const thisMonthTrades = history.filter(t => {
    const d = t.EntryDate ? String(t.EntryDate).split('T')[0] : '';
    return d.startsWith(currentMonthStr);
  });
  let monthlyProfit = 0;
  thisMonthTrades.forEach(t => monthlyProfit += (parseFloat(t['損益']) || 0));

  let msg = '';
  let color = '#f8fafc';
  let bg = '#334155';
  let border = '#475569';

  if (isLossStreak && streak >= 2) {
    msg = `⚠️ 現在 ${streak}連敗中 です。焦って取り返そうとするリベンジトレードになっていませんか？深呼吸して、ルールに合致しているか再度確認しましょう。`;
    color = '#fca5a5'; bg = 'rgba(220, 38, 38, 0.2)'; border = '#ef4444';
  } else if (isWinStreak && streak >= 3) {
    msg = `🎉 現在 ${streak}連勝中 です！調子が良さそうですが、気が大きくなってロットを上げたり、雑なエントリーになっていませんか？兜の緒を締めましょう！`;
    color = '#6ee7b7'; bg = 'rgba(16, 185, 129, 0.2)'; border = '#10b981';
  } else if (thisMonthTrades.length >= 10) {
    msg = `💡 今月はすでに ${thisMonthTrades.length}回 のトレードを消化しています。エントリー回数が多すぎないか（ポジポジ病）見直してみてください。優位性のある場所だけを厳選しましょう。`;
    color = '#fbbf24'; bg = 'rgba(245, 158, 11, 0.2)'; border = '#f59e0b';
  } else if (monthlyProfit >= 100000) {
    msg = `💰 今月はすでに +${monthlyProfit.toLocaleString()}円 の利益が出ています！無理なトレードは控え、勝ち逃げを意識しても良いかもしれません。`;
    color = '#38bdf8'; bg = 'rgba(56, 189, 248, 0.2)'; border = '#0284c7';
  } else if (thisMonthTrades.length > 0 && thisMonthTrades.length <= 3) {
    msg = `🎯 今月のエントリーは ${thisMonthTrades.length}回 です。慎重に相場を選別できていて素晴らしいです！その調子で確実なポイントを狙いましょう。`;
    color = '#cbd5e1'; bg = 'rgba(71, 81, 105, 0.2)'; border = '#64748b';
  } else {
    msg = `💡 冷静な分析ができていますか？感情に流されず、あなたの売買ルールを満たしているか丁寧に確認してください。`;
    color = '#cbd5e1'; bg = 'rgba(71, 81, 105, 0.2)'; border = '#64748b';
  }

  alertBox.textContent = msg;
  alertBox.style.color = color;
  alertBox.style.background = bg;
  alertBox.style.borderColor = border;
  alertBox.style.display = 'block';
}

function updateEntryJudgementText(prefix) {
  const modalId = prefix === 'ne' ? '#modal-entry' : '#modal-trade-detail';
  const getAct = (selector) => {
    const el = document.querySelector(`${modalId} ${selector} .active`);
    return el ? el.textContent : '';
  };
  const getGroupAct = (cls, idx) => {
    const grps = document.querySelectorAll(`${modalId} ${cls}`);
    if (!grps[idx]) return '';
    const el = grps[idx].querySelector('.active');
    return el ? el.textContent : '';
  };

  const v480 = getGroupAct('.ma-group', 0);
  const vKairi = getGroupAct('.ma-group', 1);
  const vH1_20 = getGroupAct('.ma-group', 2);
  const vH4_20 = getGroupAct('.ma-group', 3);

  const w1 = getGroupAct('.tf-group', 1);
  const d1 = getGroupAct('.tf-group', 2);
  const h4 = getGroupAct('.tf-group', 3);

  const outBox = prefix === 'ne' ? document.getElementById('ne-judgement-text') : null;
  if (!outBox) return; // Only exists on ne for now.

  if (!v480 || !vKairi || !vH1_20 || !vH4_20 || !w1 || !d1 || !h4) {
    outBox.textContent = '--';
    outBox.style.color = '#f8fafc';
    return;
  }

  // "✕" covers both "NG" and "✕" as text content could be just "✕" in the UI for failure modes.
  // Wait, the UI has ◎ and ✕. NG is not visually distinct from ✕ unless we look at the raw data.
  // Ah, the user formula uses "NG". If H4MA乖離 is "NG" (which mapped to ✕ visually!).
  // Wait, if it mapped to ✕, how do we know if it was NG or just a blank ✕?
  // Let's assume if the active button is 'cond-ng' (✕) then it's considered "NG/✕" in logic.
  const isOkKairi = vKairi === '◎';

  let resText = "🚫 エントリーNG！ 🚫";
  let resColor = "#ef4444";

  if (!isOkKairi) { // Treated as "NG" per user formula logic
    const hasAnyOk = (v480 === '◎' || vH1_20 === '◎' || vH4_20 === '◎');
    const alignUp = (w1 === '↑' && d1 === '↑' && h4 === '↑');
    const alignDn = (w1 === '↓' && d1 === '↓' && h4 === '↓');
    if (hasAnyOk && (alignUp || alignDn)) {
      resText = "✅ エントリーOK！（特例）✅";
      resColor = "#f59e0b"; // Orange/Yellow
    }
  } else {
    if (v480 === '◎' || vH1_20 === '◎' || vH4_20 === '◎' || isOkKairi) {
      resText = "✅ エントリーOK！ ✅";
      resColor = "#10b981"; // Green
    }
  }

  outBox.textContent = resText;
  outBox.style.color = resColor;
}

function calculateSimilarTrades(prefix) {
  const modalId = prefix === 'ne' ? '#modal-entry' : '#modal-trade-detail';
  const outSum = prefix === 'ne' ? document.getElementById('ne-similar-summary') : null;
  const outList = prefix === 'ne' ? document.getElementById('ne-similar-list') : null;

  if (!outSum || !outList) return;

  // Require pair AND direction to be selected before calculating
  const pairVal = document.querySelector(`${modalId} select[id$="-pair"]`)?.value;
  const dirActive = document.querySelector(`${modalId} #ne-dir .active, ${modalId} #td-dir .active`);
  if (!pairVal || !dirActive) {
    outSum.textContent = 'ペアと方向を選択すると類似トレードを表示します。';
    outList.innerHTML = '';
    return;
  }

  // Extract current input features
  let curDow = document.querySelector(`${modalId} select[id$="-dow-rule"]`)?.value || '';

  const getAct = (cls, idx) => {
    const el = document.querySelectorAll(`${modalId} ${cls}`)[idx]?.querySelector('.active');
    return el ? el.textContent : '';
  };

  const curDir = getAct('.btn-group', 0)?.includes('Buy') ? 'Buy' : 'Sell'; // first group is Direction
  const w1 = getAct('.tf-group', 1);
  const ma1 = getAct('.ma-group', 0);
  const ma2 = getAct('.ma-group', 1);
  const ma3 = getAct('.ma-group', 2);
  const ma4 = getAct('.ma-group', 3);
  const gr1 = getAct('.score-group', 0);
  const gr2 = getAct('.score-group', 1);
  const gr3 = getAct('.score-group', 2);
  const gr4 = getAct('.score-group', 3);
  const gr5 = getAct('.score-group', 4);
  const gr6 = getAct('.score-group', 5);
  const gr7 = getAct('.score-group', 6);
  const gr8 = getAct('.score-group', 7);

  // 実トレードのみ（見逃し除外）
  const history = App.data.entries.filter(t => t['ステータス'] === '決済');
  let similars = [];

  // MA正規化ヘルパー
  const normMA = v => {
    const s = String(v || '').trim();
    if (s === '◎' || s === '〇' || s === '○') return '◎';
    if (s === '✕' || s === 'NG' || s === 'ng') return '✕';
    return '';
  };

  history.forEach(t => {
    if (t.DowRule != curDow) return; // DowRule一致が必須条件

    let score = 0;

    // W1トレンド一致: +10
    const tW1 = t['W1'] || '';
    if (w1 && tW1 && w1 === tW1) score += 10;

    // MA条件 各10点（4条件 × 10 = 40点）
    const maKeys = ['H4MA480.1200', 'H4MA乖離', 'H1MA20.80', 'H4MA20.80'];
    const curMAs = [ma1, ma2, ma3, ma4];
    let maMatchCount = 0;
    maKeys.forEach((k, i) => {
      const cur = normMA(curMAs[i]);
      const hist = normMA(t[k + '_J'] || t[k]);
      if (cur && hist && cur === hist) { score += 10; maMatchCount++; }
    });
    // 全MA一致ボーナス: +5
    if (maMatchCount === 4 && curMAs.every(m => m)) score += 5;

    // エントリー根拠 各5点（8項目 × 5 = 40点）
    const grKeys = ['水平線D1.H4', 'H1MAエリア', 'TL推進', 'TL逆トレ', 'TL(M15)', '直近波理論', 'H4の5波以降', '上位足リスク'];
    const grAliases = { 'TL推進': 'トレンドライン（推進）', 'TL逆トレ': 'トレンドライン（逆トレ）', 'TL(M15)': 'トレンドライン（M15）' };
    const curGrs = [gr1, gr2, gr3, gr4, gr5, gr6, gr7, gr8];
    let grMatchCount = 0;
    grKeys.forEach((k, i) => {
      const cur = curGrs[i];
      const hist = String(t[k] || t[grAliases[k]] || '').trim();
      if (cur && hist && cur === hist) { score += 5; grMatchCount++; }
    });
    // 全根拠一致ボーナス: +5
    if (grMatchCount === 8 && curGrs.every(g => g)) score += 5;

    // 50点以上を類似トレードとして採用（100点満点）
    if (score >= 50) {
      const dateStr = String(t.EntryDate || '').replace(/\//g, '-').split('T')[0];
      similars.push({ trade: t, score, pips: parseFloat(t['実取得pips']) || 0, dateStr });
    }
  });

  // スコア降順、同スコアは日付降順（直近優先）
  similars.sort((a, b) => b.score - a.score || b.dateStr.localeCompare(a.dateStr));

  if (similars.length === 0) {
    outSum.textContent = '条件に一致する過去の類似トレードは見つかりませんでした。';
    outList.innerHTML = '';
    return;
  }

  let totalWin = 0;
  let totalPips = 0;
  let totalRR = 0;
  let countRR = 0;

  similars.forEach(s => {
    totalPips += s.pips;
    if (s.pips > 0) totalWin++;
    const sl = parseFloat(s.trade['StopLossPips']) || parseFloat(s.trade['SL']) || 0;
    if (sl > 0) {
      totalRR += (s.pips / sl);
      countRR++;
    }
  });

  const winRate = (totalWin / similars.length * 100).toFixed(1);
  const avgRR = countRR > 0 ? (totalRR / countRR).toFixed(2) : '--';
  const avgPips = (totalPips / similars.length).toFixed(1);

  outSum.innerHTML = `
    対象: ${similars.length}件 <br>
    勝率: <strong style="color:#10b981;">${winRate}%</strong> ｜ 平均: <strong>${avgPips}pips</strong> ｜ 平均RR: <strong>${avgRR}</strong>
  `;

  // Render Top 5
  outList.innerHTML = similars.slice(0, 5).map(s => {
    const t = s.trade;
    const isWin = s.pips > 10;
    const index = App.data.entries.indexOf(t);
    const tz = t['時間帯'] ? `<span style="color:#64748b; font-size:10px;"> · ${t['時間帯']}</span>` : '';
    return `
      <div onclick="openTradeDetail(${index}, true)" style="background:#0f172a; padding:8px 12px; border-radius:4px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; font-size:12px; border:1px solid #334155;">
        <div>
           <strong style="color:#38bdf8;">${t['PairName（元）'] || t.Pair || 'ペア不明'}</strong>
           <span style="color:#94a3b8;">(${Math.round(s.score)}点)</span>${tz}
        </div>
        <div style="color:${isWin ? '#10b981' : '#ef4444'}; font-weight:bold;">
           ${isWin ? '+' : ''}${s.pips.toFixed(1)}p
        </div>
      </div>
    `;
  }).join('');
}

function calculateEntryScore() {
  let score = 0;
  let conditionsMet = 0;
  const groups = document.querySelectorAll('#modal-entry .score-group');

  groups.forEach(group => {
    const active = group.querySelector('.active');
    if (active) {
      const val = parseInt(group.dataset.val);
      const isInverse = group.dataset.inverse === "true";

      if (val === 1) {
        // Positive condition: +1 if 〇(cond-ok) selected
        if (active.classList.contains('cond-ok')) score += 1;
      } else if (val === -1) {
        // Negative condition: -1 if the "bad" option is selected
        // H4の5波以降 (no data-inverse): cond-ok(〇) = bad → -1
        // 上位足リスク (data-inverse=true): cond-ng(アリ) = bad → -1
        if (!isInverse && active.classList.contains('cond-ok')) score -= 1;
        if (isInverse && active.classList.contains('cond-ng')) score -= 1;
      }
      conditionsMet++;
    }
  });

  document.getElementById('checker-score-val').innerHTML = `${score}<span style="font-size:12px; color:#94a3b8;">/6</span>`;

  const box = document.getElementById('checker-status');
  const title = document.getElementById('checker-title');
  const msg = document.getElementById('checker-msg');

  if (conditionsMet < 8) {
    box.className = 'checker-box';
    title.textContent = '判定待ち';
    msg.textContent = 'すべての根拠を入力してください';
  } else if (score >= 4) {
    box.className = 'checker-box pass';
    title.textContent = '✅ エントリースコア: 良好';
    msg.textContent = '優位性が確認されました。ルール通りに実行してください。';
  } else {
    box.className = 'checker-box fail';
    title.textContent = '🚫 エントリー見送り推奨';
    msg.textContent = 'スコア不足です。エントリーの見直しを検討しましょう。';
  }

  updateEntryJudgementText('ne');
  calculateSimilarTrades('ne');
}

function calculateEntryScoreTD() {
  // Similar math but updates the TD score box without triggering side effects
  let score = 0;
  const groups = document.querySelectorAll('#modal-trade-detail .score-group');
  groups.forEach(group => {
    const active = group.querySelector('.active');
    if (active) {
      const val = parseInt(group.dataset.val);
      const isInverse = group.dataset.inverse === "true";
      if (val === 1) {
        if (active.classList.contains('cond-ok')) score += 1;
      } else if (val === -1) {
        if (!isInverse && active.classList.contains('cond-ok')) score -= 1;
        if (isInverse && active.classList.contains('cond-ng')) score -= 1;
      }
    }
  });

  document.getElementById('td-checker-score-val').innerHTML = `${score}<span style="font-size:12px; color:#94a3b8;">/6</span>`;
  // 画面上の表示スコアも更新
  const scoreDisplay = document.getElementById('td-score-display');
  if (scoreDisplay) scoreDisplay.innerHTML = `${score}<span style="font-size:12px; color:#94a3b8;">/6</span>`;
  const box = document.getElementById('td-checker-status');
  const msg = document.getElementById('td-checker-msg');
  if (score >= 4) {
    box.className = 'checker-box pass';
    msg.textContent = '良好';
  } else {
    box.className = 'checker-box fail';
    msg.textContent = 'スコア不足';
  }
}

function calculateRR() {
  const tp = parseFloat(document.getElementById('ne-tp').value);
  const sl = parseFloat(document.getElementById('ne-sl').value);
  const disp = document.getElementById('ne-rr-display');

  if (!isNaN(tp) && !isNaN(sl) && sl > 0) {
    const rr = (tp / sl).toFixed(2);
    disp.textContent = `RR: 1 : ${rr}`;
    disp.className = rr >= 2.0 ? 'calc-info text-green' : 'calc-info text-red';
  } else {
    disp.textContent = `RR: --`;
    disp.className = 'calc-info';
  }
}

function calculateRRTD() {
  const pips = parseFloat(document.getElementById('td-pips').value);
  const sl = parseFloat(document.getElementById('td-sl').value);
  const disp = document.getElementById('td-rr-display');

  if (!isNaN(pips) && !isNaN(sl) && sl > 0) {
    const rr = (pips / sl).toFixed(1);
    disp.textContent = `1 : ${rr}`;
    disp.style.color = rr >= 2.0 ? '#10b981' : (rr >= 0 ? '#f8fafc' : '#ef4444');
  } else {
    disp.textContent = `--`;
    disp.style.color = '#f8fafc';
  }
}

function calculateRuleMetrics() {
  const pips = parseFloat(document.getElementById('td-pips').value);
  const profit = parseFloat(document.getElementById('td-profit').value);
  const rPipsEl = document.getElementById('td-rule-pips');
  const rPips = parseFloat(rPipsEl.value);
  const prDisp = document.getElementById('td-rule-profit');

  // Formula: ルール準拠損益 = 損益 × (ルール準拠pips / 実取得pips)
  if (!isNaN(profit) && !isNaN(pips) && pips !== 0 && !isNaN(rPips)) {
    const rProfit = Math.round(profit * (rPips / pips));
    prDisp.textContent = `¥${rProfit.toLocaleString()}`;
    prDisp.style.color = '#f8fafc';
  } else {
    prDisp.textContent = `--`;
    prDisp.style.color = '#94a3b8';
  }
}

function openChecklistModal() {
  // Check if everything is filled
  const pair = document.getElementById('ne-pair').value;
  if (!pair) {
    alert("ペアを選択してください");
    return;
  }
  App.state.modalOpenedAt = Date.now();
  document.getElementById('modal-checklist').classList.add('active');
  const btn = document.getElementById('btn-final-execute');
  btn.classList.add('disabled');
  btn.style.pointerEvents = 'none';
  // reset checks
  document.querySelectorAll('.checklist-item').forEach(cb => cb.checked = false);
}

function closeChecklistModal() {
  document.getElementById('modal-checklist').classList.remove('active');
}

function validateChecklist() {
  const checkboxes = Array.from(document.querySelectorAll('.checklist-item'));
  const allChecked = checkboxes.every(cb => cb.checked);
  const btn = document.getElementById('btn-final-execute');
  if (allChecked) {
    btn.removeAttribute('disabled');
    btn.classList.remove('disabled');
    btn.style.pointerEvents = 'auto';
    btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
    btn.style.color = '#fff';
  } else {
    btn.setAttribute('disabled', '');
    btn.classList.add('disabled');
    btn.style.pointerEvents = 'none';
    btn.style.background = '#334155';
    btn.style.color = '#64748b';
  }
}

function executeEntrySubmit() {
  closeChecklistModal();
  submitEntryData();
}

async function submitEntryData() {
  showLoader();
  try {
    const modal = document.getElementById('modal-entry');

    // アクティブなトグルボタンのテキストを取得
    const getActiveBtn = (selector) => {
      const el = modal.querySelector(selector + ' button.active');
      return el ? el.textContent.trim() : '';
    };

    // 方向ボタン (▲ Buy / ▼ Sell → "Buy" / "Sell")
    const dirRaw = getActiveBtn('#ne-dir');
    const direction = dirRaw.replace('▲ ', '').replace('▼ ', '');

    const pairName = document.getElementById('ne-pair').value;
    const entryData = {
      'EntryDate': document.getElementById('ne-date').value,
      'EntryTime': document.getElementById('ne-time').value,
      '時間帯': document.getElementById('ne-time').value,
      'PairName': pairName,
      'PairName（元）': pairName, // AppSheetのLOOKUP列に直接書き込む
      'Direction': direction,
      'DowRule': document.getElementById('ne-dow-rule').value,
      'TakeProfitPips': document.getElementById('ne-tp').value,
      'StopLossPips': document.getElementById('ne-sl').value,
      'Lot': document.getElementById('ne-lot').value,
      'エントリーメモ': document.getElementById('ne-memo').value,
      '事前メモ': document.getElementById('ne-pre-memo')?.textContent?.replace('(ペアを選択すると表示されます)', '').replace('(事前メモなし)', '').trim() || '',
      'ステータス': App.state.isMissedEntry ? '保有中（見逃し）' : '保有中',
    };

    // グリッドボタン（トレンド方向/MA条件/エントリー根拠）
    // grid-item ごとに label → active button テキストをマップ
    modal.querySelectorAll('.grid-item').forEach(item => {
      const label = item.querySelector('.grid-label')?.textContent.trim();
      const activeBtn = item.querySelector('button.active');
      if (label && activeBtn) {
        entryData[label] = activeBtn.textContent.trim();
      }
    });

    // グリッドラベルのエイリアス変換（スプレッドシートの列名に合わせる）
    const gridLabelAliases = {
      'TL推進': 'トレンドライン（推進）',
      'TL逆トレ': 'トレンドライン（逆トレ）',
      'TL(M15)': 'トレンドライン（M15）',
    };
    Object.entries(gridLabelAliases).forEach(([short, full]) => {
      if (entryData[short] !== undefined) entryData[full] = entryData[short];
    });

    // エントリースコア
    const scoreText = document.getElementById('checker-score-val')?.textContent || '';
    const scoreMatch = scoreText.match(/(\d+)/);
    if (scoreMatch) entryData['エントリースコア'] = scoreMatch[1];

    // 画像保存：Drive優先、失敗時はbase64フォールバック
    const imgPreview = document.getElementById('ne-image-preview');
    if (imgPreview && imgPreview.src && imgPreview.src.startsWith('data:image')) {
      entryData['ChartImage'] = await uploadImageSmart(imgPreview.src, 'entry_' + Date.now() + '.jpg');
    }

    // GAS に saveEntry POST
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'saveEntry', data: entryData })
    }).then(r => r.json());

    if (!res.success) throw new Error(res.error || '保存に失敗しました');

    closeEntryModal();
    await loadData(); // データ再読み込みで即反映
    showToast('エントリーを記録しました ✅');
  } catch (e) {
    alert('エラー: ' + e.message);
  } finally {
    hideLoader();
  }
}

// ==========================================
// Chart Image & Canvas Markup
// ==========================================
function previewUploadImage(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = document.getElementById('ne-image-preview');
      img.src = e.target.result;
      img.style.display = 'block'; // display:none が設定されている場合に強制表示
      document.getElementById('image-preview-container').style.display = 'block';
      makeTappable(img);
      const labelText = document.getElementById('ne-image-label-text');
      if (labelText) labelText.textContent = '✅ 画像選択済み（タップで変更）';
      const label = document.getElementById('ne-image-label');
      if (label) label.style.borderColor = '#10b981';
    };
    reader.readAsDataURL(input.files[0]);
  }
}

let canvasParams = { isDrawing: false, ctx: null, color: '#ef4444' };

function openCanvasEditor() {
  const img = document.getElementById('ne-image-preview');
  if (!img.src) return;

  const canvas = document.getElementById('markup-canvas');
  const ctx = canvas.getContext('2d');

  // Set real dimensions preserving aspect ratio
  canvas.width = img.naturalWidth || 800;
  canvas.height = img.naturalHeight || 450;

  // Draw base image
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  canvasParams.ctx = ctx;
  ctx.strokeStyle = canvasParams.color;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.lineWidth = 4;

  document.getElementById('modal-canvas-editor').classList.add('active');

  // Events
  canvas.onmousedown = startDrawing;
  canvas.onmousemove = draw;
  canvas.onmouseup = stopDrawing;
  canvas.onmouseout = stopDrawing;

  // Touch
  canvas.ontouchstart = (e) => { e.preventDefault(); startDrawing(e.touches[0]); };
  canvas.ontouchmove = (e) => { e.preventDefault(); draw(e.touches[0]); };
  canvas.ontouchend = stopDrawing;
}

function closeCanvasEditor() {
  document.getElementById('modal-canvas-editor').classList.remove('active');
}

function startDrawing(e) {
  canvasParams.isDrawing = true;
  draw(e);
}

function draw(e) {
  if (!canvasParams.isDrawing) return;
  const canvas = document.getElementById('markup-canvas');
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  const x = (e.clientX - rect.left) * scaleX;
  const y = (e.clientY - rect.top) * scaleY;

  canvasParams.ctx.lineTo(x, y);
  canvasParams.ctx.stroke();
  canvasParams.ctx.beginPath();
  canvasParams.ctx.moveTo(x, y);
}

function stopDrawing() {
  canvasParams.isDrawing = false;
  canvasParams.ctx.beginPath();
}

function setMarkupColor(color) {
  canvasParams.color = color;
  if (canvasParams.ctx) canvasParams.ctx.strokeStyle = color;

  // Update UI borders
  const btns = document.getElementById('modal-canvas-editor').querySelectorAll('button[onclick^="setMarkupColor"]');
  btns.forEach(b => {
    b.style.border = b.style.background.includes(color.replace('#', '')) ? '2px solid white' : 'none';
  });
}

function clearCanvas() {
  const img = document.getElementById('ne-image-preview');
  const canvas = document.getElementById('markup-canvas');
  if (canvasParams.ctx) {
    canvasParams.ctx.clearRect(0, 0, canvas.width, canvas.height);
    canvasParams.ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  }
}

function saveCanvasMarkup() {
  const canvas = document.getElementById('markup-canvas');
  const imgURL = canvas.toDataURL('image/jpeg', 0.8);

  // Set preview to new marked-up image
  document.getElementById('ne-image-preview').src = imgURL;
  closeCanvasEditor();
}

// ==========================================
// Trade Detail & Clossing
// ==========================================
function playCloseSound(isWin) {
  try {
    if ('vibrate' in navigator) {
      if (isWin) navigator.vibrate([100, 50, 100, 50, 150]);
      else navigator.vibrate([200, 100, 300]);
    }

    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    if (isWin) {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.5, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } else {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(150, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(100, ctx.currentTime + 0.3);
      gain.gain.setValueAtTime(0.5, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    }
  } catch (e) { }
}

// 新規エントリー画像をクリア
function clearNewEntryImage() {
  const img = document.getElementById('ne-image-preview');
  img.src = '';
  document.getElementById('image-preview-container').style.display = 'none';
  document.getElementById('ne-image-upload').value = '';
  const labelText = document.getElementById('ne-image-label-text');
  if (labelText) labelText.textContent = '📷 エントリー画像を追加';
  const label = document.getElementById('ne-image-label');
  if (label) label.style.borderColor = '#38bdf8';
}

// 詳細モーダルの画像削除（UIのみ変更・GAS保存は「変更内容を保存」ボタン時）
function deleteTradeImage(slot) {
  if (!confirm('この画像を削除しますか？\n※「変更内容を保存」で確定されます')) return;
  const index = parseInt(document.getElementById('td-index').value);
  const t = App.data.entries[index];
  const fromHistory = App.state.detailFromHistory;

  if (slot === 'top') {
    const targetField = findEntryImageFieldName(t);
    document.getElementById('td-image-preview').src = '';
    document.getElementById('td-top-image-area').style.display = 'none';
    if (!fromHistory) {
      App.state.pendingEntryImgDelete = targetField || 'ChartImage';
      const ea = document.getElementById('td-entry-upload-area');
      if (ea) {
        ea.style.display = 'block';
        const lt = document.getElementById('td-entry-upload-label-text');
        if (lt) { lt.textContent = 'エントリー画像を添付'; lt.style.color = '#94a3b8'; }
        const lbl = ea.querySelector('label');
        if (lbl) lbl.style.borderColor = '#334155';
        const inp = document.getElementById('td-entry-image-upload');
        if (inp) inp.value = '';
      }
    }
  } else {
    const targetField = findExitImageFieldName(t);
    document.getElementById('td-exit-image-preview').src = '';
    document.getElementById('td-exit-image-container').style.display = 'none';
    if (!fromHistory) {
      App.state.pendingExitImgDelete = targetField || '決済チャート';
      const ea = document.getElementById('td-exit-upload-area');
      if (ea) {
        ea.style.display = 'block';
        const lt = document.getElementById('td-exit-upload-label-text');
        if (lt) { lt.textContent = '決済画像を添付'; lt.style.color = '#94a3b8'; }
        const lbl = ea.querySelector('label');
        if (lbl) lbl.style.borderColor = '#334155';
        const inp = document.getElementById('td-exit-image-upload');
        if (inp) inp.value = '';
      }
    }
  }
  showToast('🗑️ 保存ボタンで確定されます');
}

// カラム名（最初に値があるもの）を返す
function findEntryImageFieldName(t) {
  const keys = ['ChartImage', 'EntryImage', 'エントリー画像', 'エントリーチャート', 'EntryChart', 'entry_image'];
  return keys.find(k => t[k] && String(t[k]).trim()) || '';
}
function findExitImageFieldName(t) {
  const keys = ['決済チャート', 'ExitImage', 'ExitChartImage', '決済画像', 'ExitChart', 'exit_image', 'CloseImage', 'ExitImg'];
  return keys.find(k => t[k] && String(t[k]).trim()) || '';
}

function previewUploadEntryImageTD(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = document.getElementById('td-image-preview');
      img.style.display = 'block';
      img.src = e.target.result;
      document.getElementById('td-top-image-area').style.display = 'block';
      // アップロードエリアは非表示にせず「選択済み」表示に更新（決済写真と同じ動作）
      const labelText = document.getElementById('td-entry-upload-label-text');
      if (labelText) { labelText.textContent = '✅ 画像選択済み（タップで変更）'; labelText.style.color = '#10b981'; }
      const label = input.closest('label');
      if (label) label.style.borderColor = '#10b981';
      makeTappable(img);
    };
    reader.readAsDataURL(input.files[0]);
  }
}

function previewUploadImageTD(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const img = document.getElementById('td-exit-image-preview');
      img.src = e.target.result;
      document.getElementById('td-exit-image-container').style.display = 'block';
      makeTappable(img);
      const labelText = document.getElementById('td-exit-upload-label-text');
      if (labelText) { labelText.textContent = '✅ 画像選択済み（タップで変更）'; labelText.style.color = '#10b981'; }
      const label = input.closest('label');
      if (label) label.style.borderColor = '#10b981';
    }
    reader.readAsDataURL(input.files[0]);
  }
}

function openTradeDetail(index, readOnly = false, fromHistory = false) {
  App.state.detailFromHistory = fromHistory;
  App.state.pendingEntryImgDelete = null;
  App.state.pendingExitImgDelete = null;
  const t = App.data.entries[index];
  if (!t) return;
  App.state.activeTradeIndex = index;

  // Reset read-only state before populating
  const modal = document.getElementById('modal-trade-detail');
  modal.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = false; });
  modal.querySelectorAll('button.toggle-btn').forEach(b => { b.disabled = false; });
  const saveBtn = modal.querySelector('button[onclick="saveTradeDetail()"]');
  if (saveBtn) saveBtn.style.display = '';

  // Set pairs up
  const sel = document.getElementById('td-pair');
  if (sel.options.length <= 1) { // Populate only if not populated
    sel.innerHTML = '<option value="">選択...</option>';
    const pairNames = [...new Set(App.data.pairs.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
    pairNames.forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      sel.appendChild(opt);
    });
  }

  document.getElementById('td-index').value = index;
  document.getElementById('td-title').textContent = `${t['PairName（元）'] || t.PairName || t.Pair} ${t.Direction}`;
  document.getElementById('td-status').value = t['ステータス'] || '保有中';

  // Basic info
  const dateStr = formatDateDisplay(t.EntryDate);
  document.getElementById('td-date').value = dateStr.replace(/\//g, '-');
  document.getElementById('td-time').value = formatTimeDisplay(t.EntryTime);
  document.getElementById('td-pair').value = t['PairName（元）'] || t.PairName || t.Pair || '';

  // Score display
  const scoreDisp = document.getElementById('td-score-display');
  if (scoreDisp) {
    const sc = t['エントリースコア'];
    scoreDisp.textContent = (sc !== undefined && sc !== '') ? `${sc}/6` : '--';
  }

  // Direction
  const isBuy = t.Direction === 'Buy' || t.Direction === '▲ Buy';
  const isSell = t.Direction === 'Sell' || t.Direction === '▼ Sell';
  document.querySelectorAll('#td-dir button').forEach(b => b.classList.remove('active'));
  if (isBuy) document.querySelector('#td-dir .dir-buy')?.classList.add('active');
  if (isSell) document.querySelector('#td-dir .dir-sell')?.classList.add('active');

  document.getElementById('td-dow-rule').value = t.DowRule || '1';

  // Helper to set btn-group
  const setBg = (id, val) => {
    const p = document.getElementById(id);
    if (!p) return;
    p.querySelectorAll('button').forEach(b => b.classList.remove('active'));
    if (!val) return;
    Array.from(p.querySelectorAll('button')).forEach(b => {
      if (b.textContent.trim() === val) b.classList.add('active');
    });
  };

  setBg('td-tf-m1', t['M1']);
  setBg('td-tf-w1', t['W1']);
  setBg('td-tf-d1', t['D1']);
  setBg('td-tf-h4', t['H4']);
  setBg('td-tf-h1', t['H1']);

  // MAs assume either direct value or matching what it produced. 
  // If db has "◎" we match it. If db has "↑" we might need translation, but ideally the UI outputs ◎/✕.
  const mapMA = (v) => v === '◎' ? '◎' : (v === '✕' || v === 'NG' ? '✕' : '');
  setBg('td-ma-480', mapMA(t['H4MA480.1200_J'] || t['H4MA480.1200']));
  setBg('td-ma-kairi', mapMA(t['H4MA乖離_J'] || t['H4MA乖離']));
  setBg('td-ma-h1-20', mapMA(t['H1MA20.80_J'] || t['H1MA20.80']));
  setBg('td-ma-h4-20', mapMA(t['H4MA20.80_J'] || t['H4MA20.80']));

  // Entry Grounds
  // カラム名の別名対応（スプレッドシートの列名が異なる場合のフォールバック）
  const scoreLabelAliases = {
    'TL推進':  'トレンドライン（推進）',
    'TL逆トレ': 'トレンドライン（逆トレ）',
    'TL(M15)': 'トレンドライン（M15）',
  };
  const scoreLabels = ['水平線D1.H4', 'H1MAエリア', 'TL推進', 'TL逆トレ', 'TL(M15)', '直近波理論', 'H4の5波以降', '上位足リスク'];
  const scoreGrups = document.querySelectorAll('#modal-trade-detail .score-group');
  scoreLabels.forEach((lbl, idx) => {
    if (!scoreGrups[idx]) return;
    const val = t[lbl] || t[scoreLabelAliases[lbl]];
    // 常に全ボタンをリセット（前のトレードのDOM状態を引き継がないように）
    scoreGrups[idx].querySelectorAll('button').forEach(b => b.classList.remove('active'));
    // 値があれば該当ボタンをアクティブに
    if (val) {
      scoreGrups[idx].querySelectorAll('button').forEach(b => {
        if (b.textContent.trim() === val.trim()) b.classList.add('active');
      });
    }
  });

  document.getElementById('td-tp').value = t['TP'] || t['StopProfitPips'] || '';
  document.getElementById('td-sl').value = t['SL'] || t['StopLossPips'] || '';
  document.getElementById('td-lot').value = t['Lot'] || '';

  // existing values
  document.getElementById('td-pips').value = t['実取得pips'] || '';
  document.getElementById('td-profit').value = t['損益'] || '';
  document.getElementById('td-rule-pips').value = t['ルール準拠pips'] || t['ルール準拠Pips'] || '';

  document.getElementById('td-entry-ref').value = t['エントリー振り返り'] || '';
  document.getElementById('td-exit-ref').value = t['決済振り返り'] || '';
  document.getElementById('td-exit-memo').value = t['決済メモ'] || '';
  const tdEntryMemo = document.getElementById('td-entry-memo');
  if (tdEntryMemo) tdEntryMemo.value = t['エントリーメモ'] || '';

  // Images ──────────────────────────────────────────
  // 保有中：上=エントリー写真、下=決済写真
  // 履歴  ：上=決済写真、  下=エントリー写真
  const rawEntryImg = findEntryImageField(t);
  const rawExitImg = findExitImageField(t);

  // 常にエントリー画像=上スロット、決済画像=下スロット
  const topRaw = rawEntryImg;
  const botRaw = rawExitImg;

  // 上部スロット（メイン写真）
  const topArea = document.getElementById('td-top-image-area');
  const topImgEl = document.getElementById('td-image-preview');
  const topImgURL = getImageUrl(topRaw);
  const topIsPath = topRaw && topRaw.includes('/') && !topRaw.startsWith('http') && !topRaw.startsWith('data:');
  topImgEl.removeAttribute('data-path');
  if (topImgURL) {
    topImgEl.src = topImgURL;
    topArea.style.display = 'block';
    makeTappable(topImgEl);
  } else if (topIsPath) {
    topImgEl.src = '';
    topImgEl.dataset.path = topRaw;
    topArea.style.display = 'block';
    // パス解決後にmakeTappableが呼ばれる
  } else {
    topImgEl.src = '';
    topArea.style.display = 'none';
  }
  // 上部スロットのラベル
  const topLabel = topArea.querySelector('button');
  if (topLabel) topLabel.dataset.imgType = 'entry';

  // 下部スロット（決済画像）
  const botContainer = document.getElementById('td-exit-image-container');
  const botImgEl = document.getElementById('td-exit-image-preview');
  const botImgURL = getImageUrl(botRaw);
  const botIsPath = botRaw && botRaw.includes('/') && !botRaw.startsWith('http') && !botRaw.startsWith('data:');
  botImgEl.removeAttribute('data-path');
  if (botImgURL) {
    botImgEl.src = botImgURL;
    botContainer.style.display = 'block';
    makeTappable(botImgEl);
  } else if (botIsPath) {
    botImgEl.src = '';
    botImgEl.dataset.path = botRaw;
    botContainer.style.display = 'block';
    // パス解決後にmakeTappableが呼ばれる
  } else {
    botImgEl.src = '';
    botContainer.style.display = 'none';
  }

  // パスベース画像を非同期で解決
  if (topIsPath || botIsPath) {
    resolvePathImages(document.getElementById('modal-trade-detail'));
  }

  // アップロードエリア共通セット関数
  function setupUploadArea(areaId, inputId, labelId, hasImage) {
    const area = document.getElementById(areaId);
    const input = document.getElementById(inputId);
    const lt = document.getElementById(labelId);
    if (!area) return;
    if (fromHistory) { area.style.display = 'none'; return; }
    area.style.display = 'block';
    if (input) input.value = '';
    const lbl = area.querySelector('label');
    if (hasImage) {
      if (lt) { lt.textContent = '✅ 画像選択済み（タップで変更）'; lt.style.color = '#10b981'; }
      if (lbl) lbl.style.borderColor = '#10b981';
    } else {
      if (lt) { lt.textContent = lt.id === 'td-entry-upload-label-text' ? 'エントリー画像を添付' : '決済画像を添付'; lt.style.color = '#94a3b8'; }
      if (lbl) lbl.style.borderColor = '#334155';
    }
  }
  setupUploadArea('td-entry-upload-area', 'td-entry-image-upload', 'td-entry-upload-label-text', !!rawEntryImg);
  setupUploadArea('td-exit-upload-area', 'td-exit-image-upload', 'td-exit-upload-label-text', !!rawExitImg);

  onStatusChange(); // toggle fields
  calculateEntryScoreTD(); // update score UI
  calculateRRTD(); // Update RR display
  calculateRuleMetrics(); // Update Rule pips/profit

  // Apply read-only mode if requested (e.g. opened from similar trades)
  if (readOnly) {
    modal.querySelectorAll('input, select, textarea').forEach(el => { el.disabled = true; });
    modal.querySelectorAll('button.toggle-btn').forEach(b => { b.disabled = true; });
    if (saveBtn) saveBtn.style.display = 'none';
    document.getElementById('td-title').textContent += ' 【参照】';
  }

  App.state.modalOpenedAt = Date.now();
  const _tdm = document.getElementById('modal-trade-detail');
  _tdm.classList.add('active');
  requestAnimationFrame(() => { _tdm.querySelector('.modal-body').scrollTop = 0; });
}

function closeTradeDetail() {
  document.getElementById('modal-trade-detail').classList.remove('active');
  App.state.pendingEntryImgDelete = null;
  App.state.pendingExitImgDelete = null;
  if (App.state.detailFromHistory) {
    App.state.detailFromHistory = false;
    openHistoryModal();
  }
}

function onStatusChange() {
  // closing-fields is always visible regardless of status
}

async function saveTradeDetail() {
  showLoader();
  try {
    const index = parseInt(document.getElementById('td-index').value);
    const t = App.data.entries[index];
    if (!t) throw new Error('エントリーが見つかりません');

    const entryId = t['EntryID'];
    if (!entryId) throw new Error('EntryIDが見つかりません（スプレッドシートにEntryID列が必要です）');

    // アクティブなトグルボタンの値を取得するヘルパー
    const getActiveBtn = (id) => {
      const el = document.getElementById(id);
      if (!el) return '';
      const btn = el.querySelector('button.active');
      return btn ? btn.textContent.trim() : '';
    };

    const updateData = {
      'EntryDate': document.getElementById('td-date').value.replace(/-/g, '/'),
      'EntryTime': document.getElementById('td-time').value,
      'PairName（元）': document.getElementById('td-pair').value,
      'PairName': document.getElementById('td-pair').value,
      'ステータス': document.getElementById('td-status').value,
      '実取得pips': document.getElementById('td-pips').value,
      '勝敗': (() => {
        const _p = parseFloat(document.getElementById('td-pips').value);
        if (isNaN(_p) || document.getElementById('td-pips').value === '') return '';
        return _p > 10 ? '勝ち' : (_p < -10 ? '負け' : '引き分け');
      })(),
      '損益': document.getElementById('td-profit').value,
      'ルール準拠pips': document.getElementById('td-rule-pips').value,
      'ルール準拠Pips': document.getElementById('td-rule-pips').value,
      'ルール準拠損益': (() => {
        const _pips = parseFloat(document.getElementById('td-pips').value);
        const _profit = parseFloat(document.getElementById('td-profit').value);
        const _rPips = parseFloat(document.getElementById('td-rule-pips').value);
        if (!isNaN(_profit) && !isNaN(_pips) && _pips !== 0 && !isNaN(_rPips)) {
          return String(Math.round(_profit * (_rPips / _pips)));
        }
        return '';
      })(),
      '実リスクリワード': (() => {
        const _pips = parseFloat(document.getElementById('td-pips').value);
        const _sl = parseFloat(document.getElementById('td-sl')?.value);
        if (!isNaN(_pips) && !isNaN(_sl) && _sl > 0) {
          return (_pips / _sl).toFixed(2);
        }
        return '';
      })(),
      'エントリー振り返り': document.getElementById('td-entry-ref').value,
      'エントリーメモ': document.getElementById('td-entry-memo')?.value || '',
      '決済振り返り': document.getElementById('td-exit-ref').value,
      '決済メモ': document.getElementById('td-exit-memo').value,
      'TakeProfitPips': document.getElementById('td-tp')?.value || '',
      'StopLossPips': document.getElementById('td-sl')?.value || '',
      'Lot': document.getElementById('td-lot')?.value || '',
      'DowRule': document.getElementById('td-dow-rule')?.value || '',
      'M1': getActiveBtn('td-tf-m1'),
      'W1': getActiveBtn('td-tf-w1'),
      'D1': getActiveBtn('td-tf-d1'),
      'H4': getActiveBtn('td-tf-h4'),
      'H1': getActiveBtn('td-tf-h1'),
      'H4MA480.1200_J': getActiveBtn('td-ma-480'),
      'H4MA乖離_J': getActiveBtn('td-ma-kairi'),
      'H1MA20.80_J': getActiveBtn('td-ma-h1-20'),
      'H4MA20.80_J': getActiveBtn('td-ma-h4-20'),
    };

    // 方向ボタン
    const dirBtn = document.querySelector('#td-dir button.active');
    if (dirBtn) updateData['Direction'] = dirBtn.textContent.replace('▲ ', '').replace('▼ ', '').trim();

    // エントリー根拠スコアボタン
    const scoreLabelAliases = {
      'TL推進':  'トレンドライン（推進）',
      'TL逆トレ': 'トレンドライン（逆トレ）',
      'TL(M15)': 'トレンドライン（M15）',
    };
    const scoreLabels = ['水平線D1.H4', 'H1MAエリア', 'TL推進', 'TL逆トレ', 'TL(M15)', '直近波理論', 'H4の5波以降', '上位足リスク'];
    const scoreGroups = document.querySelectorAll('#modal-trade-detail .score-group');
    scoreLabels.forEach((lbl, idx) => {
      const btn = scoreGroups[idx]?.querySelector('button.active');
      if (btn) {
        const v = btn.textContent.trim();
        updateData[lbl] = v;
        // スプレッドシートの別名カラムにも同時保存
        if (scoreLabelAliases[lbl]) updateData[scoreLabelAliases[lbl]] = v;
      }
    });

    // エントリースコアを再計算して保存
    let calcScore = 0;
    scoreGroups.forEach(group => {
      const active = group.querySelector('button.active');
      if (active) {
        const val = parseInt(group.dataset.val);
        const isInverse = group.dataset.inverse === 'true';
        if (val === 1 && active.classList.contains('cond-ok')) calcScore += 1;
        else if (val === -1) {
          if (!isInverse && active.classList.contains('cond-ok')) calcScore -= 1;
          if (isInverse && active.classList.contains('cond-ng')) calcScore -= 1;
        }
      }
    });
    updateData['エントリースコア'] = String(calcScore);

    // 画像保存（保留中の削除 & 新規アップロード）
    const fromHistory = App.state.detailFromHistory;
    if (!fromHistory) {
      // 保留中の削除を適用
      if (App.state.pendingEntryImgDelete) {
        updateData[App.state.pendingEntryImgDelete] = '';
      }
      if (App.state.pendingExitImgDelete) {
        updateData[App.state.pendingExitImgDelete] = '';
      }
      // 新規選択ファイルのアップロード（fileInputにファイルがある場合のみ）
      const entryFileInput = document.getElementById('td-entry-image-upload');
      if (entryFileInput && entryFileInput.files && entryFileInput.files[0]) {
        const entryImgPreview = document.getElementById('td-image-preview');
        const entryField = findEntryImageFieldName(t) || 'ChartImage';
        updateData[entryField] = await uploadImageSmart(entryImgPreview.src, 'entry_' + Date.now() + '.jpg');
      }
      const exitFileInput = document.getElementById('td-exit-image-upload');
      if (exitFileInput && exitFileInput.files && exitFileInput.files[0]) {
        const exitImgPreview = document.getElementById('td-exit-image-preview');
        updateData['決済チャート'] = await uploadImageSmart(exitImgPreview.src, 'exit_' + Date.now() + '.jpg');
      }
    }

    // GAS updateEntry を呼び出す
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'updateEntry', entryId: entryId, data: updateData })
    }).then(r => r.json());

    if (!res.success) throw new Error(res.error || '保存に失敗しました');

    // ローカルにも反映（即時表示用）
    Object.assign(t, updateData);

    const payloadStatus = updateData['ステータス'];
    const payloadPips = updateData['実取得pips'];
    if (payloadStatus === '決済' || payloadStatus === '決済（見逃し）') {
      playCloseSound(parseFloat(payloadPips) > 0);
    }

    closeTradeDetail();
    renderPositions();
    showToast('保存しました ✅');
  } catch (e) {
    alert('エラー: ' + e.message);
  } finally {
    hideLoader();
  }
}

async function deleteEntry() {
  const index = parseInt(document.getElementById('td-index').value);
  const t = App.data.entries[index];
  if (!t) return;

  const pairName = t['PairName（元）'] || t.PairName || t.Pair || 'このエントリー';
  if (!confirm(`「${pairName}」を削除しますか？\nこの操作は取り消せません。`)) return;

  const entryId = t['EntryID'];
  if (!entryId) {
    alert('EntryIDが見つかりません。スプレッドシートを直接編集してください。');
    return;
  }

  showLoader();
  try {
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'deleteEntry', entryId: entryId })
    }).then(r => r.json());

    if (!res.success) throw new Error(res.error || '削除に失敗しました');

    closeTradeDetail();
    await loadData();
    showToast('削除しました 🗑️');
  } catch (e) {
    alert('エラー: ' + e.message);
  } finally {
    hideLoader();
  }
}

// ==========================================
// 画像ライトボックス（タップで拡大・全画面）
// ==========================================
function openLightbox(src) {
  if (!src || src.length < 5) return;
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  img.src = src;
  img.style.transform = 'translate(0px,0px) scale(1)';
  lb.style.display = 'flex';

  // ── ピンチズーム＆パン ──
  let scale = 1, tx = 0, ty = 0;
  let lastScale = 1, lastTx = 0, lastTy = 0;
  let startDist = 0, startMx = 0, startMy = 0;
  let panStartX = 0, panStartY = 0;
  let swipeStartY = 0;

  function getDist(t) {
    const dx = t[0].clientX - t[1].clientX, dy = t[0].clientY - t[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }
  function applyTransform() {
    img.style.transform = `translate(${tx}px,${ty}px) scale(${scale})`;
  }

  lb.ontouchstart = (e) => {
    if (e.touches.length === 2) {
      startDist = getDist(e.touches);
      lastScale = scale; lastTx = tx; lastTy = ty;
      startMx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      startMy = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    } else if (e.touches.length === 1) {
      panStartX = e.touches[0].clientX - tx;
      panStartY = e.touches[0].clientY - ty;
      swipeStartY = e.touches[0].clientY;
    }
  };
  lb.ontouchmove = (e) => {
    e.preventDefault();
    if (e.touches.length === 2) {
      const newDist = getDist(e.touches);
      scale = Math.min(Math.max(lastScale * (newDist / startDist), 1), 6);
      const mx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const my = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      tx = lastTx + (mx - startMx);
      ty = lastTy + (my - startMy);
    } else if (e.touches.length === 1) {
      if (scale > 1) {
        tx = e.touches[0].clientX - panStartX;
        ty = e.touches[0].clientY - panStartY;
      }
    }
    applyTransform();
  };
  lb.ontouchend = (e) => {
    if (scale <= 1) {
      tx = 0; ty = 0; scale = 1;
      applyTransform();
      // ズームなしのスワイプで閉じる
      if (Math.abs(e.changedTouches[0].clientY - swipeStartY) > 70) closeLightbox();
    }
  };
  // タップで閉じる（ズームなし時のみ）
  lb.onclick = (e) => {
    if (e.target === lb && scale <= 1) closeLightbox();
  };
}

function closeLightbox() {
  const lb = document.getElementById('lightbox');
  lb.style.display = 'none';
  const img = document.getElementById('lightbox-img');
  img.src = '';
  img.style.transform = 'translate(0px,0px) scale(1)';
  lb.ontouchstart = lb.ontouchmove = lb.ontouchend = lb.onclick = null;
}

// img要素にライトボックス用タップを登録（二重登録防止）
function makeTappable(imgEl) {
  if (!imgEl || imgEl._lightboxBound) return;
  imgEl._lightboxBound = true;
  imgEl.style.cursor = 'zoom-in';
  imgEl.addEventListener('click', (e) => {
    const src = imgEl.src;
    if (!src || src === window.location.href || src.endsWith('#') || src.endsWith('/')) return;
    e.stopPropagation();
    openLightbox(src);
  });
}

function showToast(msg) {
  let toast = document.getElementById('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#10b981;color:#fff;padding:10px 20px;border-radius:20px;font-size:14px;font-weight:600;z-index:9999;opacity:0;transition:opacity 0.3s;pointer-events:none;';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, 2500);
}

// ════════════════════════════════════════
// 🤖 AI トレード分析（Groq）
// ════════════════════════════════════════

function setAiTab(tab) {
  ['1m','3m','custom'].forEach(t => {
    const btn = document.getElementById('ai-tab-' + t);
    if (btn) btn.classList.toggle('active', t === tab);
  });
  const customDiv = document.getElementById('ai-custom-date');
  if (customDiv) customDiv.style.display = tab === 'custom' ? 'flex' : 'none';
  const to = new Date();
  const from = new Date();
  if (tab === '1m') {
    from.setMonth(from.getMonth() - 1);
    document.getElementById('ai-date-from').value = from.toISOString().split('T')[0];
    document.getElementById('ai-date-to').value = to.toISOString().split('T')[0];
  } else if (tab === '3m') {
    from.setMonth(from.getMonth() - 3);
    document.getElementById('ai-date-from').value = from.toISOString().split('T')[0];
    document.getElementById('ai-date-to').value = to.toISOString().split('T')[0];
  } else if (tab === 'custom') {
    // カスタム：デフォルトで1ヶ月
    from.setMonth(from.getMonth() - 1);
    document.getElementById('ai-date-from').value = from.toISOString().split('T')[0];
    document.getElementById('ai-date-to').value = to.toISOString().split('T')[0];
  }
}

async function runGeminiAnalysis() {
  const btn = document.getElementById('ai-analyze-btn');
  const resultDiv = document.getElementById('ai-result');

  // 期間フィルター（デフォルト: 直近1ヶ月）
  let fromVal = document.getElementById('ai-date-from').value;
  let toVal = document.getElementById('ai-date-to').value;
  if (!fromVal && !toVal) { setAiTab('1m'); fromVal = document.getElementById('ai-date-from').value; toVal = document.getElementById('ai-date-to').value; }

  const fromDate = fromVal ? new Date(fromVal) : null;
  const toDate = toVal ? new Date(toVal + 'T23:59:59') : null;

  const sorted = App.data.entries
    .filter(t => t['ステータス'] === '決済')
    .filter(t => {
      const d = new Date(String(t.EntryDate || '').split('T')[0].replace(/\//g, '-'));
      if (fromDate && d < fromDate) return false;
      if (toDate && d > toDate) return false;
      return true;
    })
    .slice().sort((a, b) => {
      const da = String(a.EntryDate || '').split('T')[0].replace(/\//g, '-');
      const db = String(b.EntryDate || '').split('T')[0].replace(/\//g, '-');
      return db > da ? 1 : db < da ? -1 : 0;
    });

  resultDiv.style.display = 'block';
  if (sorted.length === 0) {
    resultDiv.innerHTML = '<div style="color:#64748b;font-size:13px;">指定期間に決済済みトレードがありません。</div>';
    return;
  }

  // 送信データを整形（感情・心理分析に必要なフィールドのみ）
  const tradeData = sorted.map((t, i) => {
    const date = String(t.EntryDate || '').split('T')[0].replace(/\//g, '-');
    const pips = parseFloat(t['実取得pips']) || 0;
    const profit = parseFloat(t['損益']) || 0;
    const entryScore = parseInt(t['エントリースコア']) || 0;
    return {
      no: i + 1,
      日付: date,
      結果: pips > 10 ? '勝ち' : (pips < -10 ? '負け' : '引き分け'),
      pips: pips.toFixed(1),
      損益: Math.round(profit),
      スコア: entryScore,
      エントリー前のメモ: t['エントリーメモ'] || '',
      決済後のメモ: t['決済メモ'] || '',
      エントリーのルール記録: t['エントリー振り返り'] || '',
      決済のルール記録: t['決済振り返り'] || '',
      ルール準拠pips: parseFloat(t['ルール準拠pips'] ?? t['ルール準拠Pips']) || 0
    };
  });

  // 直近10件（期間内）
  const recent10 = tradeData.slice(0, 10);
  const wins = tradeData.filter(t => t['結果'] === '勝ち').length;
  const losses = tradeData.filter(t => t['結果'] === '負け').length;

  const prompt = buildAiUserPrompt(tradeData, recent10, fromVal, toVal, wins, losses);

  // ローディング表示
  btn.disabled = true;
  btn.textContent = '分析中...';
  resultDiv.style.display = 'block';
  resultDiv.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;color:#38bdf8;font-size:13px;padding:8px 0;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
          <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"/>
        </path>
      </svg>
      AIが${tradeData.length}件を分析中...
    </div>`;

  try {
    // GASからGroq APIキーを取得
    const keyRes = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'getGroqKey' })
    }).then(r => r.json());
    const apiKey = keyRes.key || '';
    if (!apiKey) throw new Error('Groq APIキーがGASに設定されていません（Script PropertiesにGROQ_API_KEYを設定してください）');

    const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: [
          {
            role: 'system',
            content: AI_SYSTEM_PROMPT
          },
          { role: 'user', content: prompt }
        ],
        temperature: 0.7,
        max_tokens: 1024
      })
    }).then(r => r.json());

    if (groqRes.error) throw new Error(groqRes.error.message || 'Groq APIエラー');

    const text = groqRes.choices?.[0]?.message?.content || '分析結果を取得できませんでした。';

    // Markdown → 簡易HTML変換
    const html = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/^(#{1,3}\s|[①②③④⑤⑥]【.+?】)/gm, m =>
        `<div style="font-weight:700;color:#38bdf8;margin-top:14px;margin-bottom:6px;">${m}</div>`)
      .replace(/^[\-\*・]\s*(.+)$/gm, '<div style="padding-left:14px;margin-bottom:4px;color:#cbd5e1;">• $1</div>')
      .replace(/\n+/g, '<br>');

    resultDiv.innerHTML = `
      <div style="font-size:11px;color:#64748b;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #334155;">
        対象: 直近${tradeData.length}件（${wins}勝${losses}敗）／ ${new Date().toLocaleString('ja-JP')}
      </div>
      <div style="font-size:13px;line-height:1.8;">${html}</div>`;

  } catch (e) {
    resultDiv.innerHTML = `
      <div style="color:#ef4444;font-size:12px;">
        ❌ ${e.message}
      </div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🤖 AI分析';
  }
}

// ==========================================
// Ideas (アイデアメモ)
// ==========================================

function renderIdeas() {
  const active = App.data.ideas.filter(i => i['ステータス'] !== '解決済み');
  const done   = App.data.ideas.filter(i => i['ステータス'] === '解決済み');

  const list = document.getElementById('idea-list');
  if (list) {
    if (active.length === 0) {
      list.innerHTML = '<div style="color:#64748b; font-size:13px; text-align:center; padding:20px;">メモがありません</div>';
    } else {
      list.innerHTML = active
        .sort((a, b) => (b['日付'] > a['日付'] ? 1 : -1))
        .map(idea => ideaCard(idea))
        .join('');
    }
  }

}

function ideaCard(idea) {
  const text = idea['本文'] || '';
  const preview = text.slice(0, 100) + (text.length > 100 ? '…' : '');
  const dateStr = (idea['日付'] || '').replace(/-/g, '/');
  const imgHtml = idea['画像URL'] ? `
    <div style="margin-top:8px; background:#0f172a; border-radius:6px; overflow:hidden;">
      <img src="${idea['画像URL']}" style="width:100%; max-height:140px; object-fit:contain; display:block;" onerror="this.parentElement.style.display='none'">
    </div>` : '';
  return `
    <div onclick="openIdeaDetail('${idea.id}')" style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:12px; margin-bottom:8px; cursor:pointer;">
      <div style="font-size:11px; color:#64748b; margin-bottom:6px;">${dateStr}</div>
      <div style="font-size:13px; color:#e2e8f0; line-height:1.6; white-space:pre-wrap;">${preview}</div>
      ${imgHtml}
    </div>`;
}

function openIdeaHistoryModal() {
  const done = App.data.ideas.filter(i => i['ステータス'] === '解決済み');
  const modal = document.getElementById('modal-idea-history');
  const list  = document.getElementById('idea-history-modal-list');
  if (!modal || !list) return;
  if (done.length === 0) {
    list.innerHTML = '<div style="color:#64748b; font-size:13px; text-align:center; padding:20px;">解決済みのメモはありません</div>';
  } else {
    list.innerHTML = done
      .sort((a, b) => (b['日付'] > a['日付'] ? 1 : -1))
      .map(idea => ideaCard(idea))
      .join('');
  }
  modal.style.display = 'flex';
}
function closeIdeaHistoryModal() {
  const modal = document.getElementById('modal-idea-history');
  if (modal) modal.style.display = 'none';
}

// ---- 新規メモ ----
function openNewIdeaModal() {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('idea-date').value = today;
  document.getElementById('idea-text').value = '';
  document.getElementById('idea-image-preview').style.display = 'none';
  document.getElementById('idea-image-thumb').src = '';
  App.state.ideaNewImageUrl = '';
  document.getElementById('modal-new-idea').style.display = 'flex';
}

function closeNewIdeaModal() {
  document.getElementById('modal-new-idea').style.display = 'none';
}

async function onIdeaImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (e) => {
    // ローカルプレビューを即時表示
    document.getElementById('idea-image-thumb').src = e.target.result;
    document.getElementById('idea-image-preview').style.display = 'block';
    App.state.ideaNewImageUrl = '';
    App.state.ideaImageUploading = true;
    // バックグラウンドでImgBBにアップロード
    const base64 = e.target.result.split(',')[1];
    try {
      const keyRes = await fetch(GAS_URL, { method: 'POST', body: JSON.stringify({ action: 'getImgBBKey' }) }).then(r => r.json());
      const apiKey = keyRes.key || '';
      if (!apiKey) { showToast('⚠️ ImgBB APIキー未設定'); App.state.ideaImageUploading = false; return; }
      const form = new FormData();
      form.append('key', apiKey);
      form.append('image', base64);
      const res = await fetch('https://api.imgbb.com/1/upload', { method: 'POST', body: form }).then(r => r.json());
      if (res.success) {
        App.state.ideaNewImageUrl = res.data.url;
        document.getElementById('idea-image-thumb').src = res.data.url;
      } else {
        showToast('⚠️ 画像アップロード失敗（プレビューのみ表示）');
      }
    } catch(err) {
      showToast('⚠️ 画像アップロードエラー（プレビューのみ表示）');
    }
    App.state.ideaImageUploading = false;
  };
  reader.readAsDataURL(file);
}

function removeIdeaImage() {
  App.state.ideaNewImageUrl = '';
  document.getElementById('idea-image-thumb').src = '';
  document.getElementById('idea-image-preview').style.display = 'none';
  document.getElementById('idea-image-input').value = '';
}

async function saveNewIdea() {
  if (App.state.ideaImageUploading) { showToast('⏳ 画像アップロード中...少し待ってください'); return; }
  const data = {
    '日付': document.getElementById('idea-date').value,
    '本文': document.getElementById('idea-text').value,
    '画像URL': App.state.ideaNewImageUrl || '',
    'ステータス': '未解決'
  };
  showLoader();
  try {
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'saveIdea', data: data })
    }).then(r => r.json());
    if (res.success) {
      App.data.ideas.push(Object.assign({ id: res.id }, data));
      renderIdeas();
      closeNewIdeaModal();
      showToast('保存しました ✅');
    } else {
      showToast('⚠️ 保存失敗: ' + (res.error || ''));
    }
  } catch (e) {
    showToast('⚠️ 保存エラー: ' + e.message);
  }
  hideLoader();
}

// ---- 詳細モーダル ----
function openIdeaDetail(id) {
  closeIdeaHistoryModal(); // 履歴モーダルが開いていれば閉じる
  const idea = App.data.ideas.find(function(i) { return i.id === id; });
  if (!idea) return;
  App.state.currentIdeaId = id;
  App.state.ideaDetailImageUrl = idea['画像URL'] || '';
  document.getElementById('idea-detail-date').value = idea['日付'] || '';
  document.getElementById('idea-detail-text').value = idea['本文'] || '';
  document.getElementById('idea-detail-status').value = idea['ステータス'] || '未解決';
  const preview = document.getElementById('idea-detail-image-preview');
  const thumb = document.getElementById('idea-detail-image-thumb');
  if (idea['画像URL']) {
    thumb.src = idea['画像URL'];
    preview.style.display = 'block';
  } else {
    thumb.src = '';
    preview.style.display = 'none';
  }
  document.getElementById('modal-idea-detail').style.display = 'flex';
}

function closeIdeaDetail() {
  document.getElementById('modal-idea-detail').style.display = 'none';
}

async function onIdeaDetailImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (e) => {
    // ローカルプレビューを即時表示
    document.getElementById('idea-detail-image-thumb').src = e.target.result;
    document.getElementById('idea-detail-image-preview').style.display = 'block';
    App.state.ideaDetailImageUrl = '';
    App.state.ideaDetailImageUploading = true;
    // バックグラウンドでImgBBにアップロード
    const base64 = e.target.result.split(',')[1];
    try {
      const keyRes = await fetch(GAS_URL, { method: 'POST', body: JSON.stringify({ action: 'getImgBBKey' }) }).then(r => r.json());
      const apiKey = keyRes.key || '';
      if (!apiKey) { showToast('⚠️ ImgBB APIキー未設定'); App.state.ideaDetailImageUploading = false; return; }
      const form = new FormData();
      form.append('key', apiKey);
      form.append('image', base64);
      const res = await fetch('https://api.imgbb.com/1/upload', { method: 'POST', body: form }).then(r => r.json());
      if (res.success) {
        App.state.ideaDetailImageUrl = res.data.url;
        document.getElementById('idea-detail-image-thumb').src = res.data.url;
      } else {
        showToast('⚠️ 画像アップロード失敗（プレビューのみ表示）');
      }
    } catch(err) {
      showToast('⚠️ 画像アップロードエラー（プレビューのみ表示）');
    }
    App.state.ideaDetailImageUploading = false;
  };
  reader.readAsDataURL(file);
}

function removeIdeaDetailImage() {
  App.state.ideaDetailImageUrl = '';
  document.getElementById('idea-detail-image-thumb').src = '';
  document.getElementById('idea-detail-image-preview').style.display = 'none';
  document.getElementById('idea-detail-image-input').value = '';
}

async function saveIdeaDetail() {
  if (App.state.ideaDetailImageUploading) { showToast('⏳ 画像アップロード中...少し待ってください'); return; }
  const id = App.state.currentIdeaId;
  const data = {
    '日付': document.getElementById('idea-detail-date').value,
    '本文': document.getElementById('idea-detail-text').value,
    '画像URL': App.state.ideaDetailImageUrl || '',
    'ステータス': document.getElementById('idea-detail-status').value
  };
  showLoader();
  try {
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'updateIdea', ideaId: id, data: data })
    }).then(r => r.json());
    if (res.success) {
      const idx = App.data.ideas.findIndex(function(i) { return i.id === id; });
      if (idx !== -1) App.data.ideas[idx] = Object.assign({ id: id }, data);
      renderIdeas();
      closeIdeaDetail();
      showToast('保存しました ✅');
    } else {
      showToast('⚠️ 保存失敗: ' + (res.error || ''));
    }
  } catch (e) {
    showToast('⚠️ 保存エラー: ' + e.message);
  }
  hideLoader();
}

async function deleteIdeaDetail() {
  if (!confirm('このメモを削除しますか？')) return;
  const id = App.state.currentIdeaId;
  showLoader();
  try {
    const res = await fetch(GAS_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'deleteIdea', ideaId: id })
    }).then(r => r.json());
    if (res.success) {
      App.data.ideas = App.data.ideas.filter(function(i) { return i.id !== id; });
      renderIdeas();
      closeIdeaDetail();
      showToast('削除しました 🗑️');
    } else {
      showToast('⚠️ 削除失敗: ' + (res.error || ''));
    }
  } catch (e) {
    showToast('⚠️ 削除エラー: ' + e.message);
  }
  hideLoader();
}
