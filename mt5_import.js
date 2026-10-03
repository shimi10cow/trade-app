(function(){
'use strict';
var S={rows:[],status:null,groups:[],manualEntries:[],selected:null,settings:{splitEntryHours:6},syncing:null,accountSyncing:false};
var MT5_CACHE_KEY='mt5ImportFast_v1';
function readCache(){try{return JSON.parse(localStorage.getItem(MT5_CACHE_KEY)||'null');}catch(e){return null;}}
function writeCache(d){try{localStorage.setItem(MT5_CACHE_KEY,JSON.stringify({at:Date.now(),data:d}));}catch(e){}}
function applyDash(d){d=d||{};S.rows=d.executions||[];S.status=d.status||{};S.manualEntries=d.manualEntries||[];S.accountInfo=d.accountInfo||S.accountInfo;S.lastSyncByAccount=d.lastSyncByAccount||S.lastSyncByAccount||{};S.settings=d.settings||S.settings||{splitEntryHours:6};S.groups=buildGroups(S.rows);S.loaded=true;}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(x){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]});}
function n(v){return Number(v)||0;}
function t(r){return new Date(r.DealTime||r.EntryTime||0).getTime()||0;}
function fmtDT(v,tz){if(!v)return '';var d=new Date(v);if(isNaN(d.getTime()))return String(v);var opt={year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false};if(tz)opt.timeZone=tz;var parts=new Intl.DateTimeFormat('ja-JP',opt).formatToParts(d),o={};parts.forEach(function(x){o[x.type]=x.value;});return o.year+'/'+o.month+'/'+o.day+' '+o.hour+':'+o.minute;}function localDT(v){return fmtDT(v,'Asia/Tokyo')}function deviceDT(v){return fmtDT(v,null)}
function rawSymbol(pair){return String(pair||'').toUpperCase().replace(/#/g,'').replace(/\s+/g,'');}
function isFxPair(pair){var p=rawSymbol(pair).replace(/CASH$/,'');return /^(EUR|USD|JPY|GBP|AUD|NZD|CAD|CHF)(EUR|USD|JPY|GBP|AUD|NZD|CAD|CHF)$/.test(p);}
function appPairName(pair){var p=rawSymbol(pair).replace(/CASH$/,'');var map={XAUUSD:'GOLD',GOLD:'GOLD',XAGUSD:'SILVER',SILVER:'SILVER',NGAS:'NATGAS',NATGAS:'NATGAS',NATURALGAS:'NATGAS',US500:'US500',US30:'US30',UK100:'UK100',EU50:'EU50'};return map[p]||p;}
function digits(pair){var p=rawSymbol(pair);if(/BTC|ETH|LTC|XRP/.test(p))return p.indexOf('JPY')>=0?0:2;if(isFxPair(p))return p.indexOf('JPY')>=0?2:4;if(/XAU|GOLD|XAG|SILVER/.test(p))return 2;return 2;}
function price(v,pair){var x=Number(v);return Number.isFinite(x)&&x?x.toFixed(digits(pair)):'';}
function pipValue(pair){var p=rawSymbol(pair);if(/BTC|ETH|LTC|XRP/.test(p))return p.indexOf('JPY')>=0?1000:10;if(!isFxPair(p))return 1;return p.indexOf('JPY')>=0?0.01:0.0001;}
function calcPips(pair,dir,en,ex){en=Number(en);ex=Number(ex);if(!en||!ex)return '';var p=(String(dir).toUpperCase()==='SELL'?en-ex:ex-en)/pipValue(pair);return Math.round(p*10)/10;}
function appLot(pair,lot){return isFxPair(pair)?lot:'';}
function groupSummary(g){
 var entries=g.rows.filter(isIn),exits=g.rows.filter(isOut);
 var ev=entries.reduce(function(s,r){return s+n(r.DealVolume)},0)||g.rows.reduce(function(s,r){return s+n(r.Lot)},0);
 var wavg=function(rows,pk,vk){var v=rows.reduce(function(s,r){return s+n(r[vk])},0);return v?rows.reduce(function(s,r){return s+n(r[pk])*n(r[vk])},0)/v:0;};
 var ep=wavg(entries,'DealPrice','DealVolume')||wavg(g.rows.filter(function(r){return n(r.EntryPrice)>0&&n(r.DealVolume)>0;}),'EntryPrice','DealVolume')||wavg(g.rows.filter(function(r){return r.Status==='OPEN'&&!r.Deal;}),'EntryPrice','Lot')||n((g.rows.find(function(r){return n(r.EntryPrice)>0;})||{}).EntryPrice);
 var xp=wavg(exits,'DealPrice','DealVolume');
 var exitVol=exits.reduce(function(s,r){return s+n(r.DealVolume)},0);
 var weightedPips=exitVol?exits.reduce(function(s,r){return s+calcPips(g.pair,g.dir,ep,n(r.DealPrice))*n(r.DealVolume)},0)/exitVol:'';
 var profit=g.rows.filter(function(r){return r.Deal;}).reduce(function(s,r){return s+n(r.Profit)+n(r.Swap)},0);
 var et=(entries.slice().sort(function(a,b){return t(a)-t(b)})[0]||g.rows[0]||{}).DealTime||g.rows[0]?.EntryTime||'';
 var xt=(exits.slice().sort(function(a,b){return t(a)-t(b)}).slice(-1)[0]||{}).DealTime||'';
 return {lot:ev,entryPrice:ep,exitPrice:xp,profit:profit,entryTime:et,exitTime:xt,pips:weightedPips===''?'':Math.round(weightedPips*10)/10,closed:g.open<=0};
}

function isIn(r){return String(r.DealEntry)==='0'||String(r.DealEntry)==='2';}
function isOut(r){return String(r.DealEntry)==='1'||String(r.DealEntry)==='3';}
function tradeDirectionForPosition(rows){
  var e=rows.filter(isIn).sort(function(a,b){return t(a)-t(b)})[0];
  return e?String(e.Direction||'').toUpperCase():String((rows.find(function(x){return x.Status==='OPEN'})||{}).Direction||'').toUpperCase();
}
function buildGroups(rows){
  var usable=rows.filter(function(r){return r.Source==='MT5-MANUAL'&&r.Pair&&r.Account;});
  var byPos={};
  usable.forEach(function(r){var k=[r.Server,r.Account,r.PositionID||r.Ticket].join('|');(byPos[k]||(byPos[k]=[])).push(r);});
  var pos=Object.keys(byPos).map(function(k){
    var a=byPos[k],dir=tradeDirectionForPosition(a),ent=a.filter(isIn),ex=a.filter(isOut),open=a.filter(function(x){return x.Status==='OPEN'&&!x.Deal;});
    if(!dir)return null;
    var ev=[];
    ent.forEach(function(x){ev.push({time:t(x),delta:n(x.DealVolume),row:x});});
    ex.forEach(function(x){ev.push({time:t(x),delta:-n(x.DealVolume),row:x});});
    if(!ev.length&&open.length)ev.push({time:t(open[0]),delta:n(open[0].Lot),row:open[0]});
    ev.sort(function(a,b){return a.time-b.time;});
    var start=ev.length?ev[0].time:0,end=ev.length?ev[ev.length-1].time:0,net=ev.reduce(function(s,x){return s+x.delta},0);
    var openVol=open.length?open.reduce(function(s,x){return s+n(x.Lot)},0):Math.max(0,net);
    return {key:k,rows:a,server:a[0].Server,account:a[0].Account,pair:appPairName(a[0].Pair),rawPair:a[0].Pair,dir:dir,start:start,end:end,open:openVol};
  }).filter(Boolean).sort(function(a,b){return a.start-b.start;});
  var groups=[];
  pos.forEach(function(p){
    var g=groups.length?groups[groups.length-1]:null;
    var same=g&&g.server===p.server&&g.account===p.account&&g.pair===p.pair&&g.dir===p.dir;
    var overlap=same&&p.start<=g.end&&g.open>0;
    var splitHours=Number((S.settings||{}).splitEntryHours);if(!Number.isFinite(splitHours))splitHours=6;
    var splitBatch=same&&Math.abs(p.start-g.start)<=splitHours*3600*1000;
    if(overlap||splitBatch){g.parts.push(p);g.rows=g.rows.concat(p.rows);g.end=Math.max(g.end,p.end);g.open+=p.open;}
    else groups.push({server:p.server,account:p.account,pair:p.pair,dir:p.dir,start:p.start,end:p.end,open:p.open,parts:[p],rows:p.rows.slice()});
  });
  groups.forEach(function(g,i){
    g.ids=Array.from(new Set(g.rows.map(function(r){return r.ExecutionID}).filter(Boolean)));
    g.pending=g.rows.some(function(r){return !r.ImportStatus||r.ImportStatus==='未確認';});
    g.adoptedEntry=(g.rows.find(function(r){return r.EntryID;})||{}).EntryID||'';
    g.groupId=(g.rows.find(function(r){return r.TradeGroupID;})||{}).TradeGroupID||'';
    var prev=groups.slice(0,i).reverse().find(function(x){return x.account===g.account&&x.server===g.server&&x.pair===g.pair&&x.dir===g.dir&&x.end<=g.start;});
    g.reentry=!!(prev&&g.start-prev.end<=24*3600*1000);
    g.prevEntryId=g.reentry?(prev.adoptedEntry||''):'';
    g.prevGroupId=g.reentry?(prev.groupId||''):'';
  });
  return groups;
}
function ensureUI(){
  var nav=document.querySelector('.tabs');
  var old=nav&&nav.querySelector('[data-tab="gallery"]');
  if(old){old.dataset.tab='mt5';old.innerHTML='<span class="tab-icon">🔄</span>MT5';}
  var main=document.querySelector('main.content');
  if(main&&!document.getElementById('screen-mt5')){var sc=document.createElement('div');sc.id='screen-mt5';sc.className='screen';sc.innerHTML='<div id="mt5-import-root"></div>';var gal=document.getElementById('screen-gallery');main.insertBefore(sc,gal||null);}
}
window.openRecordShortcut=function(kind){
  document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
  document.querySelectorAll('.screen').forEach(function(x){x.classList.remove('active')});
  var s=document.getElementById('screen-gallery');if(!s)return;s.classList.add('active');
  if(typeof renderGallery==='function')renderGallery();
  if(typeof renderIdeas==='function')renderIdeas();
  var memo=s.querySelector('[data-collapse-key="g-memo"]'),gallery=s.querySelector('[data-collapse-key="g-gallery"]');
  var target=kind==='memo'?memo:gallery,other=kind==='memo'?gallery:memo;
  if(target)target.style.display='block';
  if(other)other.style.display='none';
  if(target)target.classList.remove('collapsed');
  window.scrollTo({top:0,behavior:'auto'});
  requestAnimationFrame(function(){window.scrollTo({top:0,behavior:'auto'});setTimeout(function(){window.scrollTo({top:0,behavior:'auto'});},80);});
};
function paintMT5(root){
  var st=S.status||{},account=S.accountInfo&&S.accountInfo.Account?String(S.accountInfo.Account):'',acct=account?('口座 '+esc(account)+(S.accountInfo.Server?' · '+esc(S.accountInfo.Server):'')):'口座情報未取得',lastSync=account&&S.lastSyncByAccount?S.lastSyncByAccount[account]:'';
  var pending=S.groups.filter(function(g){return g.pending&&g.rows.some(function(r){return r.ImportStatus!=='除外'&&r.ImportStatus!=='保留';});});
  var hold=S.groups.filter(function(g){return g.rows.some(function(r){return r.ImportStatus==='保留';});}).length;
  var cards=pending.map(function(g,idx){
    var entries=g.rows.filter(isIn),exits=g.rows.filter(isOut),sum=groupSummary(g); var vol=sum.lot; var lotText=isFxPair(g.pair)?' · '+vol.toFixed(2)+' lot':''; var sw=g.rows.reduce(function(s,r){return s+n(r.Swap)},0);
    return '<div class="ea-card" style="margin-bottom:9px"><div style="display:flex;justify-content:space-between;gap:8px"><b>'+esc(g.pair)+' '+esc(g.dir)+'</b><span class="badge">'+(g.open>0?'保有中':'決済')+'</span></div>'+
      '<div style="font-size:12px;color:#cbd5e1;margin-top:6px">'+localDT(sum.entryTime)+' · '+esc(g.dir)+lotText+'</div><div style="font-size:12px;margin-top:4px;color:'+(sum.profit>0?'#10b981':sum.profit<0?'#ef4444':'#94a3b8')+'">'+(sum.closed?(sum.profit>0?'勝ち ':'負け '):'保有中 ')+'損益 '+(sum.profit>=0?'+':'')+Math.round(sum.profit).toLocaleString()+'円 · '+(sum.pips!==''?(sum.pips>=0?'+':'')+sum.pips+' pips · ':'')+'約定 '+(entries.length+exits.length)+'件'+(sw?' · Swap '+sw.toFixed(0):'')+'</div>'+
      (g.reentry?'<div style="font-size:11px;color:#f59e0b;margin-top:5px">↩ 24時間以内の再エントリー候補</div>':'')+
      '<div style="display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:6px;margin-top:10px"><button class="ea-btn on" onclick="mt5Review('+idx+')">記録する</button><button class="ea-btn" onclick="mt5Hold('+idx+')">保留</button><button class="ea-btn" style="border-color:#ef4444;color:#fca5a5" onclick="mt5DeletePending('+idx+')">削除</button></div>'+'<button class="ea-btn" style="width:100%;margin-top:6px" onclick="mt5ChooseExisting('+idx+')">既存の手入力Tradeに紐付け</button><button class="ea-btn" style="width:100%;margin-top:6px" onclick="mt5ShowExecutions('+idx+')">約定 '+g.ids.length+'件を見る</button></div>';
  }).join('');
  root.innerHTML='<div class="section"><div class="section-title">🔄 MT5同期</div>'+
    '<div class="ea-card"><div style="font-weight:800">'+acct+'</div><button id="mt5-account-btn" class="ea-btn" style="width:100%;margin-top:9px" onclick="getMT5AccountInfo()" '+(S.accountSyncing?'disabled':'')+'>'+(S.accountSyncing?'<span class="mt5-spin">◌</span> 取得中...':'口座情報を取得')+'</button><div style="font-size:11px;color:#64748b;margin-top:7px">最終同期: '+esc(lastSync?deviceDT(lastSync):'未同期')+'</div>'+
    '<button id="mt5-sync-latest" class="ea-save" style="margin-top:12px" onclick="requestMT5Import(&quot;latest&quot;)">'+(S.syncing==='latest'?'<span class="mt5-spin">◌</span> 取得中...':'最終同期以降を取得')+'</button>'+
    '<div style="display:flex;gap:6px;margin-top:7px"><button id="mt5-sync-7" class="ea-btn" style="flex:1" onclick="requestMT5Import(7)">'+(S.syncing===7?'<span class="mt5-spin">◌</span> 取得中...':'過去7日を再取得')+'</button><button id="mt5-sync-90" class="ea-btn" style="flex:1" onclick="requestMT5Import(90)">'+(S.syncing===90?'<span class="mt5-spin">◌</span> 取得中...':'過去90日を再取得')+'</button></div><details style="margin-top:10px;border-top:1px solid #1e293b;padding-top:9px"><summary style="font-size:12px;color:#94a3b8;cursor:pointer">同期設定</summary><div style="display:flex;align-items:center;gap:8px;margin-top:9px"><span style="font-size:11px;color:#cbd5e1;flex:1">分割エントリーを同一Tradeにまとめる時間</span><input id="mt5-split-hours" type="number" min="0" max="48" step="0.5" value="'+esc((S.settings&&S.settings.splitEntryHours)!=null?S.settings.splitEntryHours:6)+'" class="form-input" style="width:74px;text-align:center"><span style="font-size:11px;color:#94a3b8">時間</span></div><button class="ea-btn" style="width:100%;margin-top:8px" onclick="saveMT5Settings()">設定を保存</button></details></div>'+
    '<div style="display:flex;gap:8px;margin:12px 0;font-size:11px;color:#94a3b8"><span>新規 '+pending.length+'</span><span>保留 '+hold+'</span></div>'+
    (cards||'<div style="text-align:center;color:#64748b;padding:28px 8px;">確認が必要な新規Tradeはありません</div>')+'<div style="margin-top:16px"><button class="ea-btn" style="width:100%" onclick="mt5ShowArchived()">保留 '+hold+' を確認</button></div></div><div id="mt5-sheet" class="modal-overlay" onclick="if(event.target===this)this.classList.remove(\'active\')"><div class="modal-content" style="max-height:82vh"><div class="modal-header"><div class="modal-title" id="mt5-sheet-title">MT5</div><button class="modal-close" onclick="document.getElementById(\'mt5-sheet\').classList.remove(\'active\')">×</button></div><div class="modal-body" id="mt5-sheet-body"></div></div></div>';

}
window.mt5CommitLocal=function(ids){localStatus(ids,'採用済み');};
window.refreshMT5AfterUnlink=function(){
  try{localStorage.removeItem(MT5_CACHE_KEY);}catch(e){}
  S.loaded=false;
  return window.renderMT5Import(true);
};
window.renderMT5Import=async function(force){
  ensureUI();var root=document.getElementById('mt5-import-root');if(!root)return;
  if(S.loaded&&!force){paintMT5(root);return;}
  var cached=readCache();if(cached&&cached.data){applyDash(cached.data);paintMT5(root);}
  else root.innerHTML='<div class="section"><div class="section-title">🔄 MT5同期</div><div style="color:#64748b;font-size:12px;padding:12px 0;">同期状況を読み込み中...</div></div>';
  await new Promise(function(resolve){requestAnimationFrame(resolve);});
  try{
    var rs=await Promise.all([gasGet('getMT5ImportDashboard')]),d=rs[0].data||{};
    applyDash(d);writeCache(d);paintMT5(root);
  }catch(e){if(!S.loaded)root.innerHTML='<div class="section"><div style="color:#ef4444;padding:16px;">'+esc(e.message)+'</div></div>';}
};
window.getMT5AccountInfo=async function(){
  if(S.accountSyncing){showToast('口座情報を取得中です');return;}
  var started=performance.now(),requestDone=0,workerDone=0;
  S.accountSyncing=true;paintMT5(document.getElementById('mt5-import-root'));
  try{
    var r=await gasPost({action:'requestMT5Import',data:{Mode:'ACCOUNT',Days:1}});requestDone=performance.now();
    if(!r.success)throw new Error(r.error||'口座情報取得を開始できません');
    console.info('[MT5 timing] account request accepted '+((requestDone-started)/1000).toFixed(2)+'s');
    for(var tries=1;tries<=4;tries++){
      var ps=performance.now(),x=await gasGet('waitMT5ImportStatus&requestId='+encodeURIComponent(r.requestId)+'&timeoutMs=8000'),pe=performance.now(),st=x.data||x||{};
      console.info('[MT5 timing] account wait '+tries+' gas='+((pe-ps)/1000).toFixed(2)+'s status='+(st.Status||'')+' elapsed='+((pe-started)/1000).toFixed(2)+'s');
      if(st.RequestID!==r.requestId)continue;
      if(st.Status==='DONE'){
        workerDone=performance.now();
        S.accountInfo={Account:String(st.Account||''),Server:String(st.Server||'')};S.loaded=true;
        var cached=readCache(),cd=cached&&cached.data?cached.data:{};cd.accountInfo=S.accountInfo;cd.lastSyncByAccount=S.lastSyncByAccount||cd.lastSyncByAccount||{};cd.settings=S.settings||cd.settings;cd.executions=S.rows||cd.executions||[];cd.manualEntries=S.manualEntries||cd.manualEntries||[];writeCache(cd);
        paintMT5(document.getElementById('mt5-import-root'));showToast('口座情報を取得しました');
        console.info('[MT5 timing] account DONE total='+((workerDone-started)/1000).toFixed(2)+'s request='+((requestDone-started)/1000).toFixed(2)+'s afterRequest='+((workerDone-requestDone)/1000).toFixed(2)+'s');
        return;
      }
      if(st.Status==='ERROR')throw new Error(st.Message||'口座情報を取得できません');
    }
    throw new Error('PC側のMT5連携から応答がありません');
  }catch(e){showToast('⚠️ '+e.message);}
  finally{S.accountSyncing=false;paintMT5(document.getElementById('mt5-import-root'));}
};
window.saveMT5Settings=async function(){var el=document.getElementById('mt5-split-hours'),h=Number(el&&el.value);if(!Number.isFinite(h)||h<0||h>48){showToast('⚠️ 0〜48時間で入力してください');return;}try{showLoader();var r=await gasPost({action:'saveMT5ImportSettings',data:{splitEntryHours:h}});if(!r.success)throw new Error(r.error||'設定を保存できません');S.settings={splitEntryHours:h};S.groups=buildGroups(S.rows);paintMT5(document.getElementById('mt5-import-root'));showToast('MT5同期設定を保存しました');}catch(e){showToast('⚠️ '+e.message);}finally{hideLoader();}};
window.requestMT5Import=async function(days){
  if(S.syncing!==null){showToast('MT5取得はすでに実行中です');return;}
  var id=days==='latest'?'mt5-sync-latest':days===7?'mt5-sync-7':'mt5-sync-90',btn=document.getElementById(id),old=btn?btn.innerHTML:'';
  if(!(S.accountInfo&&S.accountInfo.Account)){var cached=readCache(),ca=cached&&cached.data&&cached.data.accountInfo;if(ca&&ca.Account)S.accountInfo=ca;}
  if(!(S.accountInfo&&S.accountInfo.Account)){try{var dash=await gasGet('getMT5ImportDashboard'),dd=dash.data||dash||{};if(dd.accountInfo&&dd.accountInfo.Account){applyDash(dd);writeCache(dd);paintMT5(document.getElementById('mt5-import-root'));}}catch(e){}}
  if(!(S.accountInfo&&S.accountInfo.Account)){showToast('⚠️ 先に口座情報を取得してください');return;}
  try{S.syncing=days;if(btn){btn.disabled=true;btn.innerHTML='<span class="mt5-spin">◌</span> 取得中...';}
    // Count only trades that newly appear in the 未確認 list during this fetch.
    var beforePending=new Set(visiblePending().map(function(g){return g.ids.slice().sort().join('|');}));
    var timingStart=performance.now(),latest=days==='latest',acct=S.accountInfo&&S.accountInfo.Account?String(S.accountInfo.Account):'',since=acct&&S.lastSyncByAccount?S.lastSyncByAccount[acct]||'':'',payload=latest?(since?{Days:30,Since:since}:{Days:7}):{Days:days};var r=await gasPost({action:'requestMT5Import',data:payload}),timingRequest=performance.now();if(!r.success)throw new Error(r.error||'MT5取得を開始できません');
    console.info('[MT5 timing] import '+days+' request accepted '+((timingRequest-timingStart)/1000).toFixed(2)+'s');
    for(var tries=1;tries<=4;tries++){var ps=performance.now(),s=await gasGet('waitMT5ImportStatus&requestId='+encodeURIComponent(r.requestId)+'&timeoutMs=8000'),pe=performance.now(),d=s.data||s||{};console.info('[MT5 timing] import '+days+' wait '+tries+' gas='+((pe-ps)/1000).toFixed(2)+'s status='+(d.Status||'')+' elapsed='+((pe-timingStart)/1000).toFixed(2)+'s');if(d.RequestID!==r.requestId)continue;if(d.Status==='DONE'){var doneAt=performance.now(),rr=await gasGet('getMT5ImportResult'),rd=rr.data||rr||{},usedDelta=false;if(String(rd.RequestID||'')===String(r.requestId)&&!rd.TooLarge){mergeMT5ResultRows(rd.Rows||[]);paintMT5(document.getElementById('mt5-import-root'));usedDelta=true;}else{await renderMT5Import(true);}var renderedAt=performance.now(),newCount=visiblePending().filter(function(g){return !beforePending.has(g.ids.slice().sort().join('|'));}).length;showToast(newCount>0?('新規 '+newCount+'トレードを取得しました'):'新しいトレードはありません');console.info('[MT5 timing] import '+days+' DONE total='+((renderedAt-timingStart)/1000).toFixed(2)+'s request='+((timingRequest-timingStart)/1000).toFixed(2)+'s wait='+((doneAt-timingRequest)/1000).toFixed(2)+'s result='+((renderedAt-doneAt)/1000).toFixed(2)+'s mode='+(usedDelta?'delta':'dashboard'));return;}if(d.Status==='ERROR')throw new Error(d.Message||'MT5取得エラー');}
    throw new Error('MT5取得がタイムアウトしました');
  }catch(e){showToast('⚠️ '+e.message);}finally{S.syncing=null;var b=document.getElementById(id);if(b){b.disabled=false;b.innerHTML=old;}}
};
function mergeMT5ResultRows(rows){
  rows=Array.isArray(rows)?rows:[];if(!rows.length)return;
  var map={};S.rows.forEach(function(r,i){map[String(r.ExecutionID||'')]=i;});
  rows.forEach(function(r){var k=String(r&&r.ExecutionID||'');if(!k)return;if(map[k]===undefined){map[k]=S.rows.length;S.rows.push(r);}else{var old=S.rows[map[k]]||{},keepStatus=old.ImportStatus&&old.ImportStatus!=='未確認'?old.ImportStatus:null,keepEntry=old.EntryID||'',keepGroup=old.TradeGroupID||'';S.rows[map[k]]=Object.assign({},old,r);if(keepStatus){S.rows[map[k]].ImportStatus=keepStatus;if(keepEntry)S.rows[map[k]].EntryID=keepEntry;if(keepGroup)S.rows[map[k]].TradeGroupID=keepGroup;}}});
  S.groups=buildGroups(S.rows);
  var cached=readCache(),cd=cached&&cached.data?cached.data:{};cd.executions=S.rows;cd.status=S.status||cd.status||{};cd.manualEntries=S.manualEntries||cd.manualEntries||[];cd.accountInfo=S.accountInfo||cd.accountInfo||{};cd.lastSyncByAccount=S.lastSyncByAccount||cd.lastSyncByAccount||{};cd.settings=S.settings||cd.settings||{splitEntryHours:6};writeCache(cd);
}
function visiblePending(){return S.groups.filter(function(x){return x.pending&&x.rows.some(function(r){return r.ImportStatus!=='除外'&&r.ImportStatus!=='保留';});});}
window.mt5Review=function(i){var x=visiblePending()[i];if(!x)return;var s=groupSummary(x),fmt=function(raw){var d=new Date(raw||'');if(isNaN(d))return {date:'',time:''};var p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(d),o={};p.forEach(function(v){o[v.type]=v.value;});return {date:o.year+'/'+o.month+'/'+o.day,time:o.hour+':'+o.minute};},en=fmt(s.entryTime),ex=fmt(s.exitTime),draft={'EntryID':'MT5-DRAFT-'+Date.now(),'PairName（元）':x.pair,'PairName':x.pair,'Direction':x.dir==='BUY'?'Buy':'Sell','EntryDate':en.date,'EntryTime':en.time,'EntryPrice':s.entryPrice||'','Lot':appLot(x.pair,s.lot),'ステータス':s.closed?'決済':'保有中','ExitDate':ex.date,'ExitTime':ex.time,'ExitPrice':s.exitPrice||'','Profit':s.profit||'','損益':s.profit||'','実取得pips':s.pips===''?'':s.pips,'Swap':x.rows.reduce(function(v,r){return v+n(r.Swap)},0),'Source':'MT5-MANUAL','_mt5Draft':true,'_mt5ExecutionIds':x.ids.slice()};App.data.entries.push(draft);openTradeDetail(App.data.entries.length-1,false,false);showToast('MT5実績を読み込みました');};
window.mt5Adopt=async function(i){var g=visiblePending()[i];if(!g)return;try{showLoader();await gasPost({action:'adoptMT5Trade',executionIds:g.ids,options:{confirmCreate:'MT5_REVIEW_SAVE'}});hideLoader();showToast('記録しました');renderMT5Import(true);}catch(e){hideLoader();showToast('⚠️ '+e.message);}};
window.mt5ChooseExisting=function(i){var g=visiblePending()[i];if(!g)return;S.selected=g;var sum=groupSummary(g),base=new Date(sum.entryTime||0).getTime(),windowMs=7*24*3600*1000,targetPair=appPairName(g.pair),targetDir=String(g.dir||'').toUpperCase();function entryMs(e){var ds=String(e.EntryDate||'').replace(/\//g,'-'),ts=String(e.EntryTime||'00:00');if(/^\d{1,2}:\d{2}:\d{2}$/.test(ts))ts=ts.slice(0,5);var x=new Date(ds+'T'+ts+':00+09:00').getTime();return Number.isFinite(x)?x:0;}var cand=S.manualEntries.filter(function(e){var x=entryMs(e),pair=appPairName(e.Pair||''),dir=String(e.Direction||'').replace(/[▲▼]/g,'').trim().toUpperCase();return pair===targetPair&&dir===targetDir&&x&&base&&Math.abs(x-base)<=windowMs;}).sort(function(a,b){return Math.abs(entryMs(a)-base)-Math.abs(entryMs(b)-base);}).slice(0,20);openSheet('既存Tradeに紐付け',cand.length?cand.map(function(e){return '<button class="ea-btn" style="width:100%;text-align:left;margin-bottom:7px;padding:10px" onclick="mt5LinkExisting(\''+esc(e.EntryID)+'\')"><b>'+esc(e.Pair)+' '+esc(e.Direction)+'</b>'+(e.MT5Linked?' <span style="font-size:10px;color:#94a3b8">MT5紐付済</span>':'')+'<br><span style="font-size:11px;color:#94a3b8">'+esc(e.EntryDate)+' '+esc(e.EntryTime)+' · Score '+esc(e.Score||'-')+' · '+esc(e.Status)+'</span></button>';}).join(''):'<div style="color:#64748b;padding:20px;text-align:center">同一通貨・同一方向でエントリー日時の前後1週間以内に候補Tradeがありません</div>');};
window.mt5LinkExisting=async function(entryId){if(!S.selected)return;try{showLoader();var r=await gasPost({action:'linkMT5ToEntry',executionIds:S.selected.ids,entryId:entryId});if(!r||r.success===false)throw new Error(r&&r.error||'紐付けに失敗しました');document.getElementById('mt5-sheet').classList.remove('active');await loadData();showToast('既存Tradeに紐付けました');renderMT5Import(true);}catch(e){showToast('⚠️ '+e.message);}finally{hideLoader();}};
function openSheet(title,html){var x=document.getElementById('mt5-sheet');document.getElementById('mt5-sheet-title').textContent=title;document.getElementById('mt5-sheet-body').innerHTML=html;x.classList.add('active');}
window.mt5ShowExecutions=function(i){var g=visiblePending()[i];if(!g)return;var by={};g.rows.forEach(function(r){var k=String(r.PositionID||r.Ticket||r.ExecutionID);(by[k]||(by[k]=[])).push(r);});var html=Object.keys(by).map(function(k){var rows=by[k],x={rows:rows,pair:g.pair,dir:g.dir,open:rows.some(function(r){return r.Status==='OPEN'&&!r.Deal;})?1:0},s=groupSummary(x);return '<div style="border-bottom:1px solid #1e293b;padding:11px 2px"><b>'+esc(g.pair)+' '+esc(g.dir)+(isFxPair(g.pair)?' · '+Number(s.lot||0).toFixed(2)+' lot':'')+'</b><div style="font-size:12px;color:#cbd5e1;margin-top:5px">Entry '+esc(localDT(s.entryTime))+' · '+esc(price(s.entryPrice,g.pair))+'</div>'+(s.exitTime?'<div style="font-size:12px;color:#cbd5e1;margin-top:3px">Exit '+esc(localDT(s.exitTime))+' · '+esc(price(s.exitPrice,g.pair))+'</div>':'<div style="font-size:12px;color:#f59e0b;margin-top:3px">保有中</div>')+'<div style="font-size:11px;color:#94a3b8;margin-top:4px">損益 '+(s.profit>=0?'+':'')+Math.round(s.profit).toLocaleString()+'円'+(s.pips!==''?' · '+(s.pips>=0?'+':'')+s.pips+' pips':'')+'</div></div>';}).join('');openSheet(g.pair+' '+g.dir+' 約定',html)};
window.mt5ShowArchived=function(){var gs=S.groups.filter(function(g){return g.rows.some(function(r){return r.ImportStatus==='保留';});});openSheet('保留',gs.length?gs.map(function(g,i){return '<div class="ea-card" style="margin-bottom:8px"><b>'+esc(g.pair)+' '+esc(g.dir)+'</b><span style="float:right;font-size:11px">保留</span><div style="display:flex;gap:6px;margin-top:8px"><button class="ea-btn" style="flex:1" onclick="mt5RestoreArchived('+i+')">未確認に戻す</button><button class="ea-btn" style="flex:1;border-color:#ef4444;color:#fca5a5" onclick="mt5DeleteArchived('+i+')">削除</button></div></div>';}).join(''):'<div style="color:#64748b;text-align:center;padding:20px">ありません</div>');window._mt5Archived=gs;};
function localStatus(ids,status){var set=new Set((ids||[]).map(String));S.rows.forEach(function(r){if(set.has(String(r.ExecutionID)))r.ImportStatus=status;});S.groups=buildGroups(S.rows);writeCache({executions:S.rows,status:S.status||{},manualEntries:S.manualEntries||[],accountInfo:S.accountInfo||{},lastSyncByAccount:S.lastSyncByAccount||{},settings:S.settings||{splitEntryHours:6}});paintMT5(document.getElementById('mt5-import-root'));}
function localRemove(ids){var set=new Set((ids||[]).map(String));S.rows=S.rows.filter(function(r){return !set.has(String(r.ExecutionID));});S.groups=buildGroups(S.rows);writeCache({executions:S.rows,status:S.status||{},manualEntries:S.manualEntries||[],accountInfo:S.accountInfo||{},lastSyncByAccount:S.lastSyncByAccount||{},settings:S.settings||{splitEntryHours:6}});paintMT5(document.getElementById('mt5-import-root'));}
window.mt5DeleteArchived=function(i){var x=(window._mt5Archived||[])[i];if(!x)return;if(!confirm('このMT5取込データを一覧から削除しますか？\nMT5本体の履歴は消えないため、期間を指定して再取得すれば再び取り込めます。'))return;var backup=S.rows.slice();localRemove(x.ids);document.getElementById('mt5-sheet').classList.remove('active');showToast('取込データを削除しました');gasPost({action:'deleteMT5ImportRows',executionIds:x.ids}).then(function(r){if(!r.success)throw new Error();}).catch(function(){S.rows=backup;S.groups=buildGroups(S.rows);paintMT5(document.getElementById('mt5-import-root'));showToast('⚠️ 削除を保存できなかったため元に戻しました');});};
window.mt5RestoreArchived=function(i){var x=(window._mt5Archived||[])[i];if(!x)return;var backup=S.rows.map(function(r){return Object.assign({},r);});localStatus(x.ids,'未確認');document.getElementById('mt5-sheet').classList.remove('active');showToast('未確認に戻しました');gasPost({action:'restoreMT5Import',executionIds:x.ids}).then(function(r){if(!r.success)throw new Error();}).catch(function(){S.rows=backup;S.groups=buildGroups(S.rows);paintMT5(document.getElementById('mt5-import-root'));showToast('⚠️ 変更を保存できなかったため元に戻しました');});};
function status(i,s){var x=visiblePending()[i];if(!x)return;var backup=S.rows.map(function(r){return Object.assign({},r);});localStatus(x.ids,s);showToast(s+'にしました');gasPost({action:'setMT5ImportStatus',executionIds:x.ids,status:s}).then(function(r){if(!r.success)throw new Error();}).catch(function(){S.rows=backup;S.groups=buildGroups(S.rows);paintMT5(document.getElementById('mt5-import-root'));showToast('⚠️ 変更を保存できなかったため元に戻しました');});}
window.mt5Hold=function(i){status(i,'保留')};
window.mt5DeletePending=function(i){var x=visiblePending()[i];if(!x)return;if(!confirm('このMT5取込データを一覧から削除しますか？\n再取得すれば再び表示できます。'))return;var ids=new Set(x.ids.map(String)),backup=S.rows.slice();S.rows=S.rows.filter(function(r){return !ids.has(String(r.ExecutionID));});S.groups=buildGroups(S.rows);writeCache({executions:S.rows,status:S.status||{},manualEntries:S.manualEntries||[],accountInfo:S.accountInfo||{},lastSyncByAccount:S.lastSyncByAccount||{},settings:S.settings||{splitEntryHours:6}});paintMT5(document.getElementById('mt5-import-root'));showToast('削除しました');gasPost({action:'deleteMT5ImportRows',executionIds:x.ids}).then(function(r){if(!r.success)throw new Error(r.error||'削除できません');}).catch(function(){S.rows=backup;S.groups=buildGroups(S.rows);writeCache({executions:S.rows,status:S.status||{},manualEntries:S.manualEntries||[],accountInfo:S.accountInfo||{},lastSyncByAccount:S.lastSyncByAccount||{},settings:S.settings||{splitEntryHours:6}});paintMT5(document.getElementById('mt5-import-root'));showToast('⚠️ 削除を保存できなかったため元に戻しました');});};
document.addEventListener('DOMContentLoaded',function(){ensureUI();});
})();