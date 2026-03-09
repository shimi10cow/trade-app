const GAS_URL = 'https://script.google.com/macros/s/AKfycbxLTCiyCf2mHi1Sd-iqTSmMypnN6b9MvGmFoHPgspH1tMUkytG1xWhXdAK2xn1IGwg8/exec';

const App = {
  data: {
    entries: [],
    pairs: []
  },
  state: {
    currentTab: 'positions',
    isOffline: !navigator.onLine
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

function openEntryModal() {
  const sel = document.getElementById('ne-pair');
  sel.innerHTML = '<option value="">選択...</option>';
  
  const pairNames = [...new Set(App.data.pairs.map(p => p['PairName（元）'] || p['PairName'] || '').filter(Boolean))].sort();
  pairNames.forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });
  
  document.getElementById('modal-entry').classList.add('active');
}

function closeEntryModal() {
  document.getElementById('modal-entry').classList.remove('active');
  clearTimeout(cooldownTimer);
  const btn = document.getElementById('btn-submit-entry');
  btn.textContent = '📝 エントリー開始';
  btn.style.background = '';
}

function autoLoadPairInfo() {
  const pairName = document.getElementById('ne-pair').value;
  const p = App.data.pairs.find(x => (x['PairName（元）'] || x['PairName']) === pairName);
  if(!p) return;
  
  // We would normally auto-toggle buttons here based on data in `p`
  // e.g. if p['H4'] === '↑', find the H4 group and click the '↑' button.
  // For now, logging to console.
  console.log('Loaded pair info:', p);
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
  
  container.innerHTML = activeTrades.map((t) => {
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
  // If we just want to toggle within the direct parent container
  const parent = btn.parentElement;
  if(!siblingSelector) {
    Array.from(parent.children).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  } else {
    // If we want to toggle within a specific selector (like buy/sell buttons globally)
    document.querySelectorAll(siblingSelector).forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
  }
}

function calculateEntryScore() {
  let score = 0;
  let conditionsMet = 0;
  const groups = document.querySelectorAll('.score-group');
  
  groups.forEach(group => {
    const active = group.querySelector('.active');
    if(active) {
      const isOk = active.classList.contains('cond-ok');
      const isInverse = group.dataset.inverse === "true";
      const val = parseInt(group.dataset.val); // 1 or -1
      
      // if (val == 1) ok gets +1. if (val == -1) meaning penalty, then ok means penalty triggered so -1.
      // Wait, let's keep it simple: 
      // If the rule is good (〇), we want it to be checked as 'cond-ok'.
      // If the rule is bad (H4の5波以降), we check if 'cond-ng' (✕) to avoid penalty.
      
      let givesPoints = false;
      if (val === 1 && isOk) givesPoints = true;
      if (val === -1 && !isOk && !isInverse) givesPoints = true; // wait, H4の5波以降="✕" is good
      if (val === -1 && isOk && isInverse) givesPoints = true; // wait, 上位足リスク="ナシ" is good, which is cond-ok
      
      if(val === 1 && isOk) score += 1;
      if(val === -1 && active.textContent === "✕") score += 1; // H4の5波以降=✕ is +1
      if(val === -1 && active.textContent === "ナシ") score += 1; // 上位足リスク=ナシ is +1

      conditionsMet++;
    }
  });

  document.getElementById('checker-score-val').innerHTML = `${score}<span style="font-size:12px; color:#94a3b8;">/8</span>`;
  
  const box = document.getElementById('checker-status');
  const title = document.getElementById('checker-title');
  const msg = document.getElementById('checker-msg');
  const btn = document.getElementById('btn-submit-entry');
  
  if (conditionsMet < 8) {
    box.className = 'checker-box';
    title.textContent = '判定待ち';
    msg.textContent = 'すべての根拠を入力してください';
    btn.disabled = true;
  } else if (score >= 6) {
    box.className = 'checker-box pass';
    title.textContent = '✅ エントリー可能';
    msg.textContent = '優位性が確認されました。ルール通りに実行してください。';
    btn.disabled = false;
  } else {
    box.className = 'checker-box fail';
    title.textContent = '🚫 エントリー見送り推奨';
    msg.textContent = 'スコア不足です。ルール外の無駄なトレードになります。';
    // User can still submit if they really want, but let's make it a scary warning
    btn.disabled = false;
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

let cooldownTimer = null;
function startSubmitCooldown() {
  const btn = document.getElementById('btn-submit-entry');
  
  if (btn.textContent.includes('クールダウン')) return;
  if (btn.textContent.includes('記録を確定する')) {
    submitEntryData();
    return;
  }

  // 3 second cooldown
  let seconds = 3;
  btn.style.background = '#ef4444'; // Red warning
  
  cooldownTimer = setInterval(() => {
    btn.textContent = `冷や汗を拭いてください... (${seconds})クールダウン`;
    if (seconds <= 0) {
      clearInterval(cooldownTimer);
      btn.style.background = 'linear-gradient(135deg, #10b981, #059669)'; // Green GO
      btn.textContent = '✅ 記録を確定する';
    }
    seconds--;
  }, 1000);
  
  // fire immediately the first time
  btn.textContent = `深呼吸してください... (3)クールダウン`;
}

async function submitEntryData() {
  showLoader();
  try {
    // Collect all data
    // (mock implementation)
    await new Promise(r => setTimeout(r, 1000));
    closeEntryModal();
    renderPositions();
    showToast('エントリーを記録しました');
    
    // Reset state
    document.getElementById('btn-submit-entry').textContent = '📝 エントリー開始';
    document.getElementById('btn-submit-entry').style.background = '';
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

function openTradeDetail(index) {
  const t = App.data.entries[index];
  if(!t) return;
  
  document.getElementById('td-index').value = index;
  document.getElementById('td-title').textContent = `${t['PairName（元）'] || t.PairName || t.Pair} ${t.Direction}`;
  document.getElementById('td-status').value = t['ステータス'] || '保有中';
  
  // existing values if partial save
  document.getElementById('td-pips').value = t['実取得pips'] || '';
  document.getElementById('td-profit').value = t['損益'] || '';
  document.getElementById('td-entry-ref').value = t['エントリー振り返り'] || '';
  document.getElementById('td-exit-ref').value = t['決済振り返り'] || '';
  document.getElementById('td-exit-memo').value = t['決済メモ'] || '';
  
  onStatusChange(); // toggle fields
  
  document.getElementById('modal-trade-detail').classList.add('active');
}

function closeTradeDetail() {
  document.getElementById('modal-trade-detail').classList.remove('active');
}

function onStatusChange() {
  const status = document.getElementById('td-status').value;
  const cf = document.getElementById('closing-fields');
  if(status === '決済' || status === '決済（見逃し）') {
    cf.classList.remove('hidden');
  } else {
    cf.classList.add('hidden');
  }
}

async function saveTradeDetail() {
  showLoader();
  try {
    const index = document.getElementById('td-index').value;
    const t = App.data.entries[index];
    
    const payload = {
      Id: t.Id, // Original Row ID or timestamp depending on AppSheet logic
      RowIndex: Number(index) + 2, // Assuming headers are row 1
      Status: document.getElementById('td-status').value,
      Pips: document.getElementById('td-pips').value,
      Profit: document.getElementById('td-profit').value,
      EntryRef: document.getElementById('td-entry-ref').value,
      ExitRef: document.getElementById('td-exit-ref').value,
      ExitMemo: document.getElementById('td-exit-memo').value
    };
    
    // Simulate API call to GAS
    // const res = await gasPost('updateTrade', payload);
    
    // Optimistic update locally
    t['ステータス'] = payload.Status;
    t['実取得pips'] = payload.Pips;
    t['損益'] = payload.Profit;
    t['エントリー振り返り'] = payload.EntryRef;
    t['決済振り返り'] = payload.ExitRef;
    t['決済メモ'] = payload.ExitMemo;
    
    if (payload.Status === '決済' || payload.Status === '決済（見逃し）') {
      playCloseSound(parseFloat(payload.Pips) > 0);
    }
    
    closeTradeDetail();
    renderPositions();
    showToast('更新を保存しました');
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
