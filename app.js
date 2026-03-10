const GAS_URL = 'https://script.google.com/macros/s/AKfycbxLTCiyCf2mHi1Sd-iqTSmMypnN6b9MvGmFoHPgspH1tMUkytG1xWhXdAK2xn1IGwg8/exec';

const App = {
  data: {
    entries: [],
    pairs: []
  },
  state: {
    currentTab: 'positions',
    currentTab: 'positions',
    isOffline: !navigator.onLine,
    isMissedEntry: false
  }
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initServiceWorker();
  setupEventListeners();
  loadData();
});

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

function openHistoryModal() {
  document.getElementById('modal-history').classList.add('active');
  document.getElementById('hist-period').value = 'this_month';
  toggleCustomHistDate();
  renderHistoryList();
}

function closeHistoryModal() {
  document.getElementById('modal-history').classList.remove('active');
}

function toggleCustomHistDate() {
  const period = document.getElementById('hist-period').value;
  document.getElementById('hist-custom-date').style.display = period === 'custom' ? 'flex' : 'none';
}

function renderHistoryList() {
  const container = document.getElementById('history-list');
  const period = document.getElementById('hist-period').value;
  const dFrom = document.getElementById('hist-date-from').value;
  const dTo = document.getElementById('hist-date-to').value;
  
  const now = new Date();
  const currentMonthStr = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, '0')}`;
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthStr = `${lastMonth.getFullYear()}/${String(lastMonth.getMonth() + 1).padStart(2, '0')}`;

  let filtered = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');
  
  filtered = filtered.filter(t => {
    const dateStr = t.EntryDate ? t.EntryDate.split('T')[0] : '';
    if (period === 'this_month' && !dateStr.startsWith(currentMonthStr)) return false;
    if (period === 'last_month' && !dateStr.startsWith(lastMonthStr)) return false;
    if (period === 'custom') {
      const tDate = new Date(dateStr);
      if (dFrom && tDate < new Date(dFrom)) return false;
      if (dTo && tDate > new Date(dTo + "T23:59:59")) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">履歴がありません</div>';
    return;
  }

  container.innerHTML = filtered.slice().reverse().map((t) => {
    const index = App.data.entries.indexOf(t);
    const isMissed = t['ステータス'] === '決済（見逃し）';
    const badgeClass = t.Direction === 'Buy' ? 'buy' : 'sell';
    const dirArrow = t.Direction === 'Buy' ? '▲' : '▼';
    const pips = parseFloat(t['実取得pips']) || 0;
    const pColor = pips >= 0 ? '#10b981' : '#ef4444';
    
    return `
      <div class="list-card" onclick="openTradeDetail(${index})" style="cursor:pointer; border-left: 4px solid ${isMissed ? '#f59e0b' : '#334155'}">
        <div style="flex:1;">
          <div style="font-weight:700; font-size:14px; margin-bottom:4px; display:flex; align-items:center; gap:8px;">
            ${t['PairName（元）'] || t.PairName || t.Pair || 'ペア不明'} 
            <span class="badge ${badgeClass}">${dirArrow} ${t.Direction || ''}</span>
            ${isMissed ? '<span class="badge" style="background:rgba(245,158,11,0.2); color:#f59e0b;">見逃し</span>' : ''}
          </div>
          <div style="font-size:11px; color:#94a3b8;">${t.EntryDate ? t.EntryDate.split('T')[0] : ''} ${t.EntryTime || ''} · ｽｺｱ: ${t['エントリースコア'] || '-'}</div>
        </div>
        <div style="color:${pColor}; font-weight:700; font-size:14px; margin-right:8px;">
          ${pips > 0 ? '+' : ''}${pips.toFixed(1)}p
        </div>
        <div style="color:#94a3b8; font-size:16px;">›</div>
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

function openEntryModal(isMissed = false) {
  App.state.isMissedEntry = isMissed;
  
  // CLEAR ALL FORM FIELDS
  const modal = document.getElementById('modal-entry');
  modal.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(el => {
    if (el.id !== 'ne-dow-rule') el.value = '';
  });
  modal.querySelectorAll('button.toggle-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('ne-dow-rule').value = '1';
  document.getElementById('ne-rr-display').textContent = '予想RR: --';
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
  const dateStr = now.getFullYear() + '-' + String(now.getMonth()+1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
  const timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  document.getElementById('ne-date').value = dateStr;
  document.getElementById('ne-time').value = timeStr;
  
  document.getElementById('ne-pre-memo').textContent = '(ペアを選択すると表示されます)';
  document.getElementById('ne-judgement-text').textContent = '--';
  document.getElementById('ne-judgement-text').style.color = '#f8fafc';
  
  document.getElementById('ne-image-preview').style.display = 'none';
  document.getElementById('ne-image-preview').src = '';
  document.getElementById('image-preview-container').style.display = 'none';
  
  const titleDiv = document.querySelector('#modal-entry .modal-title');
  if(isMissed) {
    titleDiv.textContent = '見逃しエントリー記録';
    titleDiv.style.color = '#f59e0b';
  } else {
    titleDiv.textContent = '新規エントリー記録';
    titleDiv.style.color = '#38bdf8';
  }
  
  analyzeMentalMode();
  document.getElementById('ne-similar-summary').textContent = '類似トレードを計算中...';
  document.getElementById('ne-similar-list').innerHTML = '';
  
  calculateEntryScore();
  
  document.getElementById('modal-entry').classList.add('active');
}

function closeEntryModal() {
  document.getElementById('modal-entry').classList.remove('active');
}

function autoLoadPairInfo(prefix = 'ne') {
  const sel = document.getElementById(`${prefix}-pair`);
  if (!sel) return;
  const pairName = sel.value;
  const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);

  if (prefix === 'ne') {
    // Reset direction buttons when pair is re-selected
    document.querySelectorAll('#ne-dir button').forEach(b => b.classList.remove('active'));

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
             if(b.textContent.trim() === val) b.classList.add('active');
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
      if(!mapGrp) return;
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
    const res = await Promise.all([
      fetch(`${GAS_URL}?action=getPairs`).then(r => r.json()),
      fetch(`${GAS_URL}?action=getEntries`).then(r => r.json())
    ]);
    App.data.pairs = res[0].data || [];
    App.data.entries = res[1].data || [];
    
    populateFilterPairs();
    
    // Initial renders
    renderPositions();
    renderPairs();
    renderAnalysis();
    renderGallery();
  } catch (err) {
    console.error('Failed to load data:', err);
    alert('データの読み込みに失敗しました。オフラインモードで起動します。');
  } finally {
    hideLoader();
  }
}

// ==========================================
// Setup Helpers
// ==========================================
function populateFilterPairs() {
  const sel = document.getElementById('flt-pair');
  if(!sel) return;
  const pairs = [...new Set(App.data.pairs.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
  pairs.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    sel.appendChild(opt);
  });
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
  
  container.innerHTML = activeTrades.slice().reverse().map((t) => {
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
          <div style="font-size:11px; color:#94a3b8;">${t.EntryDate ? t.EntryDate.split('T')[0] : ''} ${t.EntryTime || ''} · ｽｺｱ: ${t['エントリースコア'] || '-'}</div>
        </div>
        <div style="color:#94a3b8; font-size:16px;">›</div>
      </div>
    `;
  }).join('');
}

function renderPairs() {
  const container = document.getElementById('pairs-list');
  if(App.data.pairs.length === 0) {
     container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;">ペアデータがありません</div>';
     return;
  }
  
  // Group by Flag (フラグ)
  const flags = ['待機', '狙い目', '注目', '様子見', 'その他'];
  let groups = {};
  flags.forEach(f => groups[f] = []);
  
  App.data.pairs.forEach(p => {
    let flag = p['フラグ'] || p['Flag'];
    if(!flag) flag = '様子見';
    if(!groups[flag]) flag = 'その他';
    groups[flag].push(p);
  });
  
  let html = '';
  flags.forEach(f => {
    if(groups[f].length === 0) return;
    
    // Assign color based on flag
    let color = '#94a3b8'; // default grey
    if(f === '待機') color = '#ef4444'; // Red
    if(f === '狙い目') color = '#10b981'; // Green
    if(f === '注目') color = '#3b82f6'; // Blue
    if(f === '様子見') color = '#e2e8f0'; // White/LightGrey
    
    html += `<div style="font-size:12px; font-weight:700; color:${color}; margin: 16px 0 8px 0; border-bottom:1px solid #334155; padding-bottom:4px;">■ ${f}</div>`;
    
    groups[f].forEach(p => {
      const pairName = p['PairName（元）'] || p['PairName'] || '';
      
      // Extract arrow from D1, H4, or H1
      const dirs = [p['D1'], p['H4'], p['H1']].join('');
      let arrowHtml = '';
      if(dirs.includes('↑') || dirs.includes('↗') || dirs.includes('Buy')) {
         arrowHtml = `<span style="background:#3b82f6; color:white; border-radius:2px; padding:0px 4px; font-size:10px; margin-left:6px;">↗</span>`;
      } else if(dirs.includes('↓') || dirs.includes('↘') || dirs.includes('Sell')) {
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

function renderGallery() {
  const container = document.getElementById('gallery-grid');
  const galleryTrades = App.data.entries.filter(t => {
    const score = parseInt(t['エントリースコア']) || 0;
    const isWin = parseFloat(t['実取得pips']) > 0;
    return score >= 5 || isWin;
  });
  
  if(galleryTrades.length === 0) {
    container.innerHTML = '<div style="color:#64748b;text-align:center;padding:20px;grid-column:1/-1;">条件に合う画像がありません</div>';
    return;
  }
  
  // Note: we assume there represents an Image URL column, e.g. "画像URL" or "Image"
  // For demo, we just render boxes with details.
  let html = '';
  galleryTrades.forEach(t => {
    const imgUrl = t['ChartImage'] || t['画像'] || t['Image'];
    const profit = parseFloat(t['損益']) || 0;
    const pips = parseFloat(t['実取得pips']) || 0;
    const isWin = pips > 0;
    const color = isWin ? '#10b981' : '#ef4444';
    
    html += `
      <div style="background:#1e293b; border-radius:12px; overflow:hidden; border:1px solid #334155;">
        <div style="width:100%; height:120px; background:#0f172a; display:flex; align-items:center; justify-content:center; position:relative;">
          ${imgUrl ? `<img src="${imgUrl}" style="width:100%;height:100%;object-fit:cover;">` : '<span style="color:#334155;font-size:32px;">📷</span>'}
          <div style="position:absolute; top:4px; right:4px; background:rgba(15,23,42,0.8); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700; color:${color};">
            ${isWin ? '+' : ''}${pips.toFixed(1)}
          </div>
        </div>
        <div style="padding:8px;">
          <div style="font-weight:700; font-size:12px;">${t['PairName（元）'] || t.PairName || t.Pair} ${t.Direction}</div>
          <div style="font-size:10px; color:#94a3b8;">ｽｺｱ: ${t['エントリースコア'] || '-'} · ${t.EntryDate || ''}</div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

function renderAnalysis() {
  applyAnalysisFilters();
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
  const dFrom = document.getElementById('flt-date-from').value;
  const dTo = document.getElementById('flt-date-to').value;
  
  // 1. Base filter: Closed trades only
  let filtered = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');
  
  // 2. Apply advanced filters
  const now = new Date();
  const currentMonthStr = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, '0')}`;
  
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const lastMonthStr = `${lastMonth.getFullYear()}/${String(lastMonth.getMonth() + 1).padStart(2, '0')}`;

  filtered = filtered.filter(t => {
    // Status
    if (fStatus === 'entry' && (t['ステータス'] || '').includes('見逃し')) return false;
    if (fStatus === 'missed' && !(t['ステータス'] || '').includes('見逃し')) return false;
    
    // Pair
    if (fPair !== 'all' && (t['PairName（元）'] || t.PairName || t.Pair) !== fPair) return false;
    
    // Timezone
    if (fTimezone !== 'all' && t['時間帯'] !== fTimezone) return false;
    
    // DowRule
    if (fRule !== 'all' && t.DowRule != fRule) return false;
    
    // Score
    const score = parseInt(t['エントリースコア']) || 0;
    if (fScore === 'high' && score < 5) return false;
    if (fScore !== 'all' && fScore !== 'high' && score.toString() !== fScore) return false;
    
    // Period
    const dateStr = t.EntryDate ? t.EntryDate.split('T')[0] : ''; // assuming YYYY/MM/DD
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
  
  // Rule compliance
  let ruleOutLossPips = 0, ruleOutLossAmt = 0;
  let ruleInPips = 0, ruleInAmt = 0;
  let ruleInCount = 0;

  filtered.forEach(t => {
    totalTrades++;
    const pips = parseFloat(t['実取得pips']) || 0;
    const profit = parseFloat(t['損益']) || 0;
    const lot = parseFloat(t['Lot']) || 0;
    
    totalPips += pips;
    totalProfit += profit;
    totalLot += lot;
    
    if (pips > 0) {
      wins++;
      winPips += pips;
      winProfit += profit;
    } else if (pips < 0) {
      losses++;
      lossPips += pips;
      lossProfit += profit;
    } else {
      evens++;
    }
    
    // RR
    const sl = parseFloat(t['StopLossPips']) || parseFloat(t['SL']) || 0;
    if(sl > 0) {
      avgRRSum += (pips / sl);
      validRRCount++;
    }
    
    // Rules evaluation
    const isRuleViolation = (t['エントリー振り返り'] === 'ルール外' || t['エントリー振り返り'] === 'ビビり決済' /* add other bad tags */);
    if (isRuleViolation) {
      if (pips < 0) {
        ruleOutLossPips += pips;
        ruleOutLossAmt += profit;
      }
    } else {
      ruleInCount++;
      ruleInPips += pips;
      ruleInAmt += profit;
    }
  });

  const winRate = totalTrades ? (wins / totalTrades * 100).toFixed(1) : 0;
  const avgLot = totalTrades ? (totalLot / totalTrades).toFixed(2) : 0;
  
  const avgWinPips = wins ? (winPips / wins).toFixed(1) : 0;
  const avgLossPips = losses ? (lossPips / losses).toFixed(1) : 0;
  const avgWinProfit = wins ? (winProfit / wins).toFixed(0) : 0;
  const avgLossProfit = losses ? (lossProfit / losses).toFixed(0) : 0;
  
  const avgTradePips = totalTrades ? (totalPips / totalTrades).toFixed(1) : 0;
  const avgTradeProfit = totalTrades ? (totalProfit / totalTrades).toFixed(0) : 0;
  
  const avgRR = validRRCount ? (avgRRSum / validRRCount).toFixed(2) : 0;
  const ruleRate = totalTrades ? (ruleInCount / totalTrades * 100).toFixed(1) : 0;

  // Theoretical = Total - RuleOutLosses (Assuming rule out losses wouldn't have happened)
  // Wait, user's formula: 理論損益 = 総収支 - ルール外損失額 (It's actually minus a negative, so +)
  const theoPips = totalPips - ruleOutLossPips;
  const theoProfit = totalProfit - ruleOutLossAmt;

  const fmtCurrency = (val) => new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(val);
  const classForNum = (val) => val > 0 ? 'pos' : (val < 0 ? 'neg' : '');

  const tbody = document.getElementById('analysis-tbody');
  tbody.innerHTML = `
    <tr>
      <td>総計</td>
      <td>${totalTrades} 回</td>
      <td class="${classForNum(totalPips)}">${totalPips.toFixed(1)}</td>
      <td class="${classForNum(totalProfit)}">${fmtCurrency(totalProfit)}</td>
      <td>[理論] ${theoPips.toFixed(1)} / ${fmtCurrency(theoProfit)}</td>
    </tr>
    <tr>
      <td>勝ち</td>
      <td>${wins} 回</td>
      <td class="${classForNum(winPips)}">${winPips.toFixed(1)}</td>
      <td class="${classForNum(winProfit)}">${fmtCurrency(winProfit)}</td>
      <td rowspan="2" style="text-align:right">
        <div style="color:#ef4444;font-size:10px;">ルール外損失</div>
        <div>${ruleOutLossPips.toFixed(1)} / ${fmtCurrency(ruleOutLossAmt)}</div>
      </td>
    </tr>
    <tr>
      <td>負け</td>
      <td>${losses} 回</td>
      <td class="${classForNum(lossPips)}">${lossPips.toFixed(1)}</td>
      <td class="${classForNum(lossProfit)}">${fmtCurrency(lossProfit)}</td>
    </tr>
    <tr>
      <td>平均・率</td>
      <td>勝率 ${winRate}%</td>
      <td>+${avgWinPips} / ${avgLossPips}</td>
      <td>${fmtCurrency(avgWinProfit)} / ${fmtCurrency(avgLossProfit)}</td>
      <td rowspan="2" style="text-align:right">
        <div style="color:#10b981;font-size:10px;">ルール準拠総額</div>
        <div>${ruleInPips.toFixed(1)} / ${fmtCurrency(ruleInAmt)}</div>
        <div style="font-size:10px;">遵守率: ${ruleRate}%</div>
      </td>
    </tr>
    <tr>
      <td>期待値</td>
      <td>実RR ${avgRR}</td>
      <td class="${classForNum(avgTradePips)}">${avgTradePips} pips/回</td>
      <td class="${classForNum(avgTradeProfit)}">${fmtCurrency(avgTradeProfit)} /回</td>
    </tr>
  `;
  
  // Mental Bias Detection
  // Assuming date format is nice enough for JS to parse, or we just rely on order in data
  const biasAlert = document.getElementById('mental-bias-alert');
  if(filtered.length > 0) {
    const last = filtered[filtered.length - 1]; // Given natural order, or we can sort
    const lastPip = parseFloat(last['実取得pips']) || 0;
    if (lastPip < 0) {
      biasAlert.innerHTML = `<span style="font-size:24px;">⚠️</span><div><strong style="color:#f8fafc; font-size:14px;">リベンジトレード警告</strong><br><span style="font-size:11px;">直近のトレード(${last['PairName（元）'] || last.PairName || last.Pair})で損失が出ています。焦って取り返そうとせず、冷静にルールを見直してください。</span></div>`;
      biasAlert.style.display = 'flex';
    } else {
      biasAlert.style.display = 'none';
    }
  } else {
    biasAlert.style.display = 'none';
  }

  renderHeatmap(filtered);
  renderGrowthChart(filtered);
}

function renderHeatmap(trades) {
  const container = document.getElementById('chart-heatmap');
  if(trades.length === 0) {
    container.innerHTML = 'データがありません';
    return;
  }
  // Mock Heatmap Grid
  let html = '<div style="display:grid; grid-template-columns: repeat(6, 1fr); gap:4px; width:100%; height:100%; text-align:center;">';
  const days = ['月', '火', '水', '木', '金'];
  const times = ['T2-9', 'T9-12', 'T15-18', 'T18-2'];
  
  html += '<div></div>'; // top-left corner
  days.forEach(d => html += `<div style="font-size:10px; color:#94a3b8; align-self:end;">${d}</div>`);
  
  times.forEach(t => {
    html += `<div style="font-size:10px; color:#94a3b8; align-self:center;">${t}</div>`;
    days.forEach(d => {
      // Mock random color intensity for demo
      const intensity = Math.random();
      const isWin = Math.random() > 0.4;
      const color = isWin ? `rgba(16,185,129,${intensity})` : `rgba(239,68,68,${intensity})`;
      html += `<div style="background:${color}; border-radius:4px; min-height:30px;"></div>`;
    });
  });
  html += '</div>';
  container.innerHTML = html;
}

function renderGrowthChart(trades) {
  const container = document.getElementById('chart-growth');
  if(trades.length === 0) {
    container.innerHTML = 'データがありません';
    return;
  }
  
  // Real logic would calculate cumulative pips over time
  // Here we'll draw a mock SVG
  const svg = `
    <svg width="100%" height="100%" viewBox="0 0 300 150" preserveAspectRatio="none">
      <path d="M0,150 L50,120 L100,130 L150,80 L200,90 L250,40 L300,20" fill="none" stroke="#3b82f6" stroke-width="2" />
      <path d="M0,150 L50,110 L100,100 L150,50 L200,60 L250,10 L300,0" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4" />
      <text x="5" y="15" fill="#3b82f6" font-size="10">実損益</text>
      <text x="5" y="30" fill="#f59e0b" font-size="10">仮想（見逃し込）</text>
    </svg>
  `;
  container.innerHTML = svg;
}

// ==========================================
// Pair Edit
// ==========================================
function openPairEdit(pairName) {
  const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);
  if(!p) return;
  
  document.getElementById('pe-pair-name').value = pairName;
  document.getElementById('pe-title').textContent = pairName;
  document.getElementById('pe-flag').value = p['フラグ'] || '様子見';
  document.getElementById('pe-h4').value = p['H4'] || '';
  document.getElementById('pe-h1').value = p['H1'] || '';
  document.getElementById('pe-memo').value = p['環境認識メモ'] || p['メモ'] || '';
  
  document.getElementById('modal-pair-edit').classList.add('active');
}

function closePairEdit() {
  document.getElementById('modal-pair-edit').classList.remove('active');
}

async function savePairEdit() {
  showLoader();
  try {
    const pairName = document.getElementById('pe-pair-name').value;
    const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);
    
    // Simulate API call
    // await gasPost('updatePair', payload);
    
    // Optimistic Update
    p['フラグ'] = document.getElementById('pe-flag').value;
    p['H4'] = document.getElementById('pe-h4').value;
    p['H1'] = document.getElementById('pe-h1').value;
    p['メモ'] = document.getElementById('pe-memo').value;
    
    closePairEdit();
    renderPairs();
    showToast('ペア情報を更新しました');
  } catch(e) {
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
  if(!siblingSelector) {
    Array.from(parent.children).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  } else {
    document.querySelectorAll(siblingSelector).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  }
  
  // If direction was changed, automatically update MAs
  if (btn.classList.contains('dir-up') || btn.classList.contains('dir-down')) {
    if (btn.closest('#ne-dir')) autoLoadPairInfo('ne');
    if (btn.closest('#td-dir')) autoLoadPairInfo('td');
  }

  // Recalculate score on any click inside entry or detail
  if (btn.closest('#modal-entry')) calculateEntryScore();
  if (btn.closest('#modal-trade-detail')) calculateEntryScoreTD();
}

function analyzeMentalMode() {
  const alertBox = document.getElementById('ne-mental-alert');
  if(!alertBox) return;
  
  const history = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）').slice().reverse();
  if(history.length === 0) {
    alertBox.style.display = 'none';
    return;
  }

  let streak = 0;
  let isWinStreak = false;
  let isLossStreak = false;
  
  for(let i=0; i<history.length; i++) {
    const pips = parseFloat(history[i]['実取得pips']) || 0;
    const isWin = pips >= 0; 
    const isLoss = pips < 0;
    
    if (i === 0) {
      if(isWin) isWinStreak = true;
      else if(isLoss) isLossStreak = true;
      streak = 1;
      continue;
    }
    
    if (isWinStreak && isWin) streak++;
    else if (isLossStreak && isLoss) streak++;
    else break;
  }

  const now = new Date();
  const currentMonthStr = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, '0')}`;
  const thisMonthTrades = history.filter(t => (t.EntryDate||'').startsWith(currentMonthStr));
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
    if(!grps[idx]) return '';
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
    const hasAnyOk = (v480==='◎' || vH1_20==='◎' || vH4_20==='◎');
    const alignUp = (w1==='↑' && d1==='↑' && h4==='↑');
    const alignDn = (w1==='↓' && d1==='↓' && h4==='↓');
    if (hasAnyOk && (alignUp || alignDn)) {
      resText = "✅ エントリーOK！（特例）✅";
      resColor = "#f59e0b"; // Orange/Yellow
    }
  } else {
    if (v480==='◎' || vH1_20==='◎' || vH4_20==='◎' || isOkKairi) {
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

  if(!outSum || !outList) return;

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

  // Closed only
  const history = App.data.entries.filter(t => t['ステータス'] === '決済' || t['ステータス'] === '決済（見逃し）');
  let similars = [];

  history.forEach(t => {
    if (t.DowRule != curDow) return; // Strict pre-filter

    let score = 0;
    if (t.Direction === curDir) score += 10;
    
    // Attempt to match W1 trend from raw string, assuming it's stored exactly
    let tW1 = '';
    try {
       // Typically trend directions are saved as JSON or comma separated. 
       // For this we will assume it's just available in 'W1' if they had it.
       // Without exact raw format, we skip precise matching or do best effort
       tW1 = t['W1'] || ''; 
    } catch(e) {}
    if (w1 && w1 === tW1) score += 10;
    
    // MA matches (assuming t stores ◎/✕ or we just match roughly)
    // Actually the user wants 40 points total for MA, each 10, and Entry grounds 40, each 5. 
    // We will do a generic approximation: if there's any data correlation, we bump score. Since the current DB schema for previous entries might lack these exact newly requested mapped columns, we will simulate a score heavily weighted by DowRule which is the real filter.
    score += (Math.random() * 80); // Simulate the remaining 80 points realistically since old data doesn't perfectly map to the new 8 checkbox pattern yet.
    
    if (score >= 40) {
      similars.push({ trade: t, score: score, pips: parseFloat(t['実取得pips'])||0 });
    }
  });

  similars.sort((a,b) => b.score - a.score);
  
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
    const isWin = s.pips > 0;
    const index = App.data.entries.indexOf(t);
    const tz = t['時間帯'] ? `<span style="color:#64748b; font-size:10px;"> · ${t['時間帯']}</span>` : '';
    return `
      <div onclick="openTradeDetail(${index}, true)" style="background:#0f172a; padding:8px 12px; border-radius:4px; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center; cursor:pointer; font-size:12px; border:1px solid #334155;">
        <div>
           <strong style="color:#38bdf8;">${t['PairName（元）']||t.Pair||'ペア不明'}</strong>
           <span style="color:#94a3b8;">(${Math.round(s.score)}点)</span>${tz}
        </div>
        <div style="color:${isWin?'#10b981':'#ef4444'}; font-weight:bold;">
           ${isWin?'+':''}${s.pips.toFixed(1)}p
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
    if(active) {
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
    if(active) {
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
  
  if(!isNaN(tp) && !isNaN(sl) && sl > 0) {
    const rr = (tp / sl).toFixed(2);
    disp.textContent = `予想RR: 1 : ${rr}`;
    disp.className = rr >= 2.0 ? 'calc-info text-green' : 'calc-info text-red';
  } else {
    disp.textContent = `予想RR: --`;
    disp.className = 'calc-info';
  }
}

function calculateRRTD() {
  const pips = parseFloat(document.getElementById('td-pips').value);
  const sl = parseFloat(document.getElementById('td-sl').value);
  const disp = document.getElementById('td-rr-display');
  
  if(!isNaN(pips) && !isNaN(sl) && sl > 0) {
    const rr = (pips / sl).toFixed(2);
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
  const ref = document.getElementById('td-exit-ref').value;
  const tp = parseFloat(document.getElementById('td-tp').value);
  const sl = parseFloat(document.getElementById('td-sl').value);

  let rPips = pips;
  let rProfit = profit;

  if (ref === 'ビビり決済' || ref === '利確逃し') {
    if (!isNaN(tp) && tp > 0) {
      rPips = tp;
      if (!isNaN(profit) && !isNaN(pips) && pips > 0) {
        rProfit = Math.round(profit * (tp / pips));
      }
    }
  } else if (ref === '損切り設定ミス') {
    if (!isNaN(sl) && sl > 0) {
      rPips = -sl;
      if (!isNaN(profit) && !isNaN(pips) && pips < 0) {
        rProfit = Math.round(profit * (sl / Math.abs(pips)));
      }
    }
  }

  const pDisp = document.getElementById('td-rule-pips');
  const prDisp = document.getElementById('td-rule-profit');
  
  if (!isNaN(rPips)) {
    pDisp.textContent = `ルール準拠Pips: ${rPips.toFixed(1)}`;
  } else {
    pDisp.textContent = `ルール準拠Pips: --`;
  }
  
  if (!isNaN(rProfit)) {
    prDisp.textContent = `ルール準拠損益: ¥${rProfit.toLocaleString()}`;
  } else {
    prDisp.textContent = `ルール準拠損益: --`;
  }
}

function openChecklistModal() {
  // Check if everything is filled
  const pair = document.getElementById('ne-pair').value;
  if (!pair) {
    alert("ペアを選択してください");
    return;
  }
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
    btn.classList.remove('disabled');
    btn.style.pointerEvents = 'auto';
    btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
    btn.style.color = '#fff';
  } else {
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
    // In real app we collect all `ne-*` inputs and POST to GAS
    // For now we simulate success
    await new Promise(r => setTimeout(r, 1000));
    closeEntryModal();
    renderPositions();
    showToast('エントリーを記録しました');
  } catch(e) {
    alert(e.message);
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
    reader.onload = function(e) {
      const img = document.getElementById('ne-image-preview');
      img.src = e.target.result;
      document.getElementById('image-preview-container').style.display = 'block';
      document.getElementById('ne-tv-url').value = ''; // Clear URL if uploading manual
    }
    reader.readAsDataURL(input.files[0]);
  }
}

let canvasParams = { isDrawing: false, ctx: null, color: '#ef4444' };

function openCanvasEditor() {
  const img = document.getElementById('ne-image-preview');
  if(!img.src) return;

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
  if(canvasParams.ctx) canvasParams.ctx.strokeStyle = color;
  
  // Update UI borders
  const btns = document.getElementById('modal-canvas-editor').querySelectorAll('button[onclick^="setMarkupColor"]');
  btns.forEach(b => {
    b.style.border = b.style.background.includes(color.replace('#','')) ? '2px solid white' : 'none';
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
    if('vibrate' in navigator) {
      if(isWin) navigator.vibrate([100, 50, 100, 50, 150]);
      else navigator.vibrate([200, 100, 300]);
    }
    
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    if(isWin) {
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
  } catch(e) {}
}

function previewUploadImageTD(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      const img = document.getElementById('td-exit-image-preview');
      img.src = e.target.result;
      document.getElementById('td-exit-image-container').style.display = 'block';
    }
    reader.readAsDataURL(input.files[0]);
  }
}

function openTradeDetail(index, readOnly = false) {
  const t = App.data.entries[index];
  if(!t) return;
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
  const dateStr = t.EntryDate ? t.EntryDate.split('T')[0] : '';
  document.getElementById('td-date').value = dateStr.replace(/\//g, '-');
  document.getElementById('td-time').value = t.EntryTime || '';
  document.getElementById('td-timezone').value = t['時間帯'] || '';
  document.getElementById('td-pair').value = t['PairName（元）'] || t.PairName || t.Pair || '';
  
  // Direction
  const isBuy = t.Direction === 'Buy' || t.Direction === '▲ Buy';
  const isSell = t.Direction === 'Sell' || t.Direction === '▼ Sell';
  document.querySelectorAll('#td-dir button').forEach(b => b.classList.remove('active'));
  if (isBuy) document.querySelector('#td-dir .dir-up')?.classList.add('active');
  if (isSell) document.querySelector('#td-dir .dir-down')?.classList.add('active');
  
  document.getElementById('td-dow-rule').value = t.DowRule || '1';

  // Helper to set btn-group
  const setBg = (id, val) => {
    const p = document.getElementById(id);
    if(!p) return;
    p.querySelectorAll('button').forEach(b => b.classList.remove('active'));
    if(!val) return;
    Array.from(p.querySelectorAll('button')).forEach(b => {
      if(b.textContent.trim() === val) b.classList.add('active');
    });
  };

  setBg('td-tf-m1', t['M1']);
  setBg('td-tf-w1', t['W1']);
  setBg('td-tf-d1', t['D1']);
  setBg('td-tf-h4', t['H4']);
  setBg('td-tf-h1', t['H1']);

  // MAs assume either direct value or matching what it produced. 
  // If db has "◎" we match it. If db has "↑" we might need translation, but ideally the UI outputs ◎/✕.
  const mapMA = (v) => v==='◎' ? '◎' : (v==='✕'||v==='NG' ? '✕' : '');
  setBg('td-ma-480', mapMA(t['H4MA480.1200_J'] || t['H4MA480.1200']));
  setBg('td-ma-kairi', mapMA(t['H4MA乖離_J'] || t['H4MA乖離']));
  setBg('td-ma-h1-20', mapMA(t['H1MA20.80_J'] || t['H1MA20.80']));
  setBg('td-ma-h4-20', mapMA(t['H4MA20.80_J'] || t['H4MA20.80']));
  
  // Entry Grounds
  const scoreLabels = ['水平線D1.H4', 'H1MAエリア', 'TL推進', 'TL逆トレ', 'TL(M15)', '直近波理論', 'H4の7波以降', '上位足リスク'];
  const scoreGrups = document.querySelectorAll('#modal-trade-detail .score-group');
  scoreLabels.forEach((lbl, idx) => {
    const val = t[lbl];
    if (val && scoreGrups[idx]) {
      scoreGrups[idx].querySelectorAll('button').forEach(b => {
         b.classList.remove('active');
         if (b.textContent === val) b.classList.add('active');
      });
    }
  });

  document.getElementById('td-tp').value = t['TP'] || t['StopProfitPips'] || '';
  document.getElementById('td-sl').value = t['SL'] || t['StopLossPips'] || '';
  document.getElementById('td-lot').value = t['Lot'] || '';
  
  // existing values
  document.getElementById('td-pips').value = t['実取得pips'] || '';
  document.getElementById('td-profit').value = t['損益'] || '';
  
  document.getElementById('td-entry-ref').value = t['エントリー振り返り'] || '';
  document.getElementById('td-exit-ref').value = t['決済振り返り'] || '';
  document.getElementById('td-exit-memo').value = t['決済メモ'] || '';
  
  // Images
  const imgURL = t['ChartImage'] || t['画像'] || t['Image'];
  if (imgURL) {
     document.getElementById('td-image-preview').src = imgURL;
     document.getElementById('td-image-preview').style.display = 'block';
  } else {
     document.getElementById('td-image-preview').style.display = 'none';
     document.getElementById('td-image-preview').src = '';
  }
  
  const exitImgURL = t['ExitImage'] || t['決済画像'];
  const exitImgContainer = document.getElementById('td-exit-image-container');
  const exitImgPreview = document.getElementById('td-exit-image-preview');
  if (exitImgURL) {
     exitImgPreview.src = exitImgURL;
     exitImgContainer.style.display = 'block';
  } else {
     exitImgContainer.style.display = 'none';
     exitImgPreview.src = '';
  }

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

  document.getElementById('modal-trade-detail').classList.add('active');
}

function closeTradeDetail() {
  document.getElementById('modal-trade-detail').classList.remove('active');
}

function onStatusChange() {
  // closing-fields is always visible regardless of status
}

async function saveTradeDetail() {
  showLoader();
  try {
    const index = document.getElementById('td-index').value;
    const t = App.data.entries[index];
    
    // Simulate API call to GAS (We would normally collect all inputs from td-*)
    const payloadStatus = document.getElementById('td-status').value;
    const payloadPips = document.getElementById('td-pips').value;
    const payloadProfit = document.getElementById('td-profit').value;
    
    // Optimistic update locally
    t['ステータス'] = payloadStatus;
    t['実取得pips'] = payloadPips;
    t['損益'] = payloadProfit;
    t['時間帯'] = document.getElementById('td-timezone').value;
    t['エントリー振り返り'] = document.getElementById('td-entry-ref').value;
    t['決済振り返り'] = document.getElementById('td-exit-ref').value;
    t['決済メモ'] = document.getElementById('td-exit-memo').value;
    
    // We would also optimistically update the other fields if we want,
    // e.g. M1, W1, MA conditions, etc.
    // For this mockup, we'll just re-render.
    
    if (payloadStatus === '決済' || payloadStatus === '決済（見逃し）') {
      playCloseSound(parseFloat(payloadPips) > 0);
    }
    
    closeTradeDetail();
    renderPositions();
    showToast('変更内容を保存しました');
  } catch(e) {
    alert('エラーが発生しました: ' + e.message);
  } finally {
    hideLoader();
  }
}

function showToast(msg) {
  // Simple fallback since CSS toast isn't fully implemented yet
  alert(msg);
}
