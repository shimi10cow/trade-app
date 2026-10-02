(function(){
'use strict';
var S={rows:[],status:null,groups:[],manualEntries:[],selected:null};
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(x){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]});}
function n(v){return Number(v)||0;}
function t(r){return new Date(r.DealTime||r.EntryTime||0).getTime()||0;}
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
    return {key:k,rows:a,server:a[0].Server,account:a[0].Account,pair:a[0].Pair,dir:dir,start:start,end:end,open:openVol};
  }).filter(Boolean).sort(function(a,b){return a.start-b.start;});
  var groups=[];
  pos.forEach(function(p){
    var g=groups.length?groups[groups.length-1]:null;
    var same=g&&g.server===p.server&&g.account===p.account&&g.pair===p.pair&&g.dir===p.dir;
    var overlap=same&&p.start<=g.end&&g.open>0;
    var splitBatch=same&&Math.abs(p.start-g.start)<=5*60*1000;
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
  setTimeout(function(){var key=kind==='memo'?'g-memo':'g-gallery',el=document.querySelector('[data-collapse-key="'+key+'"]');if(el)el.scrollIntoView({behavior:'smooth',block:'start'});},50);
};
window.renderMT5Import=async function(){
  ensureUI();var root=document.getElementById('mt5-import-root');if(!root)return;
  root.innerHTML='<div class="section"><div class="section-title">🔄 MT5同期</div><div style="color:#64748b;font-size:12px;padding:16px 0;">読み込み中...</div></div>';
  try{
    var rs=await Promise.all([gasGet('getMT5ImportDashboard')]);
    var d=rs[0].data||{};S.rows=d.executions||[];S.status=d.status||{};S.manualEntries=d.manualEntries||[];S.groups=buildGroups(S.rows);
  }catch(e){root.innerHTML='<div class="section"><div style="color:#ef4444;padding:16px;">'+esc(e.message)+'</div></div>';return;}
  var st=S.status||{},acct=st.Account?('口座 '+esc(st.Account)+(st.Server?' · '+esc(st.Server):'')):'MT5接続待ち';
  var pending=S.groups.filter(function(g){return g.pending&&g.rows.some(function(r){return r.ImportStatus!=='除外'&&r.ImportStatus!=='保留';});});
  var hold=S.groups.filter(function(g){return g.rows.some(function(r){return r.ImportStatus==='保留';});}).length;var excluded=S.groups.filter(function(g){return g.rows.some(function(r){return r.ImportStatus==='除外';});}).length;
  var cards=pending.map(function(g,idx){
    var entries=g.rows.filter(isIn),exits=g.rows.filter(isOut);
    var vol=entries.reduce(function(s,r){return s+n(r.DealVolume)},0)||g.rows.reduce(function(s,r){return s+n(r.Lot)},0);
    var sw=g.rows.reduce(function(s,r){return s+n(r.Swap)},0);
    return '<div class="ea-card" style="margin-bottom:9px"><div style="display:flex;justify-content:space-between;gap:8px"><b>'+esc(g.pair)+' '+esc(g.dir)+'</b><span class="badge">'+(g.open>0?'保有中':'決済')+'</span></div>'+
      '<div style="font-size:11px;color:#94a3b8;margin-top:6px">'+vol.toFixed(2)+' lot · 約定 '+(entries.length+exits.length)+'件'+(sw?' · Swap '+sw.toFixed(0):'')+'</div>'+
      (g.reentry?'<div style="font-size:11px;color:#f59e0b;margin-top:5px">↩ 24時間以内の再エントリー候補</div>':'')+
      '<div style="display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:6px;margin-top:10px"><button class="ea-btn on" onclick="mt5Adopt('+idx+')">記録する</button><button class="ea-btn" onclick="mt5Hold('+idx+')">保留</button><button class="ea-btn" onclick="mt5Exclude('+idx+')">除外</button></div>'+(g.prevEntryId?'<button class="ea-btn" style="width:100%;margin-top:6px;border-color:#f59e0b;color:#f59e0b" onclick="mt5AdoptToPrevious('+idx+')">↩ 前のTradeに追加</button>':'')+'<button class="ea-btn" style="width:100%;margin-top:6px" onclick="mt5ChooseExisting('+idx+')">既存の手入力Tradeに紐付け</button><button class="ea-btn" style="width:100%;margin-top:6px" onclick="mt5ShowExecutions('+idx+')">約定 '+g.ids.length+'件を見る</button></div>';
  }).join('');
  root.innerHTML='<div class="section"><div class="section-title">🔄 MT5同期</div>'+
    '<div class="ea-card"><div style="font-weight:800">'+acct+'</div><div style="font-size:11px;color:#64748b;margin-top:4px">最終同期: '+esc(st.UpdatedAt||'未同期')+'</div>'+
    '<button class="ea-save" style="margin-top:12px" onclick="requestMT5Import(30)">MT5から取得</button>'+
    '<div style="display:flex;gap:6px;margin-top:7px"><button class="ea-btn" style="flex:1" onclick="requestMT5Import(7)">7日再取得</button><button class="ea-btn" style="flex:1" onclick="requestMT5Import(90)">90日再取得</button></div></div>'+
    '<div style="display:flex;gap:8px;margin:12px 0;font-size:11px;color:#94a3b8"><span>新規 '+pending.length+'</span><span>保留 '+hold+'</span></div>'+
    (cards||'<div style="text-align:center;color:#64748b;padding:28px 8px;">確認が必要な新規Tradeはありません</div>')+'<div style="margin-top:16px"><button class="ea-btn" style="width:100%" onclick="mt5ShowArchived()">保留 '+hold+' / 除外 '+excluded+' を確認</button></div></div><div id="mt5-sheet" class="modal-overlay" onclick="if(event.target===this)this.classList.remove(\'active\')"><div class="modal-content" style="max-height:82vh"><div class="modal-header"><div class="modal-title" id="mt5-sheet-title">MT5</div><button class="modal-close" onclick="document.getElementById(\'mt5-sheet\').classList.remove(\'active\')">×</button></div><div class="modal-body" id="mt5-sheet-body"></div></div></div>';
};
window.requestMT5Import=async function(days){
  try{showLoader();var r=await gasPost({action:'requestMT5Import',data:{Days:days}});showToast('MT5取得を依頼しました');hideLoader();
    var tries=0,timer=setInterval(async function(){tries++;try{var s=await gasGet('getMT5ImportStatus'),d=s.data||{};if(d.Status==='DONE'||d.Status==='ERROR'||tries>40){clearInterval(timer);if(d.Status==='ERROR')showToast('⚠️ '+(d.Message||'MT5取得エラー'));renderMT5Import();}}catch(e){}},1500);
  }catch(e){hideLoader();showToast('⚠️ '+e.message);}
};
function visiblePending(){return S.groups.filter(function(x){return x.pending&&x.rows.some(function(r){return r.ImportStatus!=='除外'&&r.ImportStatus!=='保留';});});}\nwindow.mt5Adopt=async function(i){var g=visiblePending()[i];if(!g)return;try{showLoader();await gasPost({action:'adoptMT5Trade',executionIds:g.ids,options:{}});hideLoader();showToast('記録しました');renderMT5Import();}catch(e){hideLoader();showToast('⚠️ '+e.message);}};\nwindow.mt5ChooseExisting=function(i){var g=visiblePending()[i];if(!g)return;S.selected=g;var pair=String(g.pair||'').toUpperCase(),dir=g.dir==='BUY'?'Buy':'Sell';var cand=S.manualEntries.filter(function(e){return String(e.Pair||'').toUpperCase()===pair&&String(e.Direction||'').indexOf(dir)>=0;}).slice().reverse().slice(0,30);openSheet('既存Tradeに紐付け',cand.length?cand.map(function(e){return '<button class="ea-btn" style="width:100%;text-align:left;margin-bottom:7px;padding:10px" onclick="mt5LinkExisting(\''+esc(e.EntryID)+'\')"><b>'+esc(e.Pair)+' '+esc(e.Direction)+'</b><br><span style="font-size:11px;color:#94a3b8">'+esc(e.EntryDate)+' '+esc(e.EntryTime)+' · Score '+esc(e.Score||'-')+' · '+esc(e.Status)+'</span></button>';}).join(''):'<div style="color:#64748b;padding:20px;text-align:center">同じ通貨・方向の未同期手入力Tradeがありません</div>');};
window.mt5LinkExisting=async function(entryId){if(!S.selected)return;try{showLoader();await gasPost({action:'linkMT5ToEntry',executionIds:S.selected.ids,entryId:entryId});hideLoader();document.getElementById('mt5-sheet').classList.remove('active');showToast('既存Tradeに紐付けました');renderMT5Import();}catch(e){hideLoader();showToast('⚠️ '+e.message);}};
function openSheet(title,html){var x=document.getElementById('mt5-sheet');document.getElementById('mt5-sheet-title').textContent=title;document.getElementById('mt5-sheet-body').innerHTML=html;x.classList.add('active');}
window.mt5ShowExecutions=function(i){var g=visiblePending()[i];if(!g)return;openSheet(g.pair+' '+g.dir+' 約定',g.rows.slice().sort(function(a,b){return t(a)-t(b)}).map(function(r){return '<div style="border-bottom:1px solid #1e293b;padding:9px 2px"><b>'+esc(r.Deal?'Deal '+r.Deal:'Position '+r.Ticket)+'</b><div style="font-size:11px;color:#94a3b8;margin-top:3px">'+esc(r.DealTime||r.EntryTime)+' · '+esc(r.Direction)+' · '+esc(r.DealVolume||r.Lot)+' lot · '+esc(r.DealPrice||r.EntryPrice)+(r.Swap?' · Swap '+esc(r.Swap):'')+'</div></div>';}).join(''))};
window.mt5ShowArchived=function(){var gs=S.groups.filter(function(g){return g.rows.some(function(r){return r.ImportStatus==='保留'||r.ImportStatus==='除外';});});openSheet('保留・除外',gs.length?gs.map(function(g,i){var st=(g.rows.find(function(r){return r.ImportStatus==='除外'})?'除外':'保留');return '<div class="ea-card" style="margin-bottom:8px"><b>'+esc(g.pair)+' '+esc(g.dir)+'</b><span style="float:right;font-size:11px">'+st+'</span><button class="ea-btn" style="width:100%;margin-top:8px" onclick="mt5RestoreArchived('+i+')">未確認に戻す</button></div>';}).join(''):'<div style="color:#64748b;text-align:center;padding:20px">ありません</div>');window._mt5Archived=gs;};
window.mt5RestoreArchived=async function(i){var g=(window._mt5Archived||[])[i];if(!g)return;try{await gasPost({action:'restoreMT5Import',executionIds:g.ids});document.getElementById('mt5-sheet').classList.remove('active');showToast('未確認に戻しました');renderMT5Import();}catch(e){showToast('⚠️ '+e.message);}};
window.mt5AdoptToPrevious=async function(i){var g=visiblePending()[i];if(!g||!g.prevEntryId)return;try{showLoader();await gasPost({action:'adoptMT5Trade',executionIds:g.ids,options:{entryId:g.prevEntryId,tradeGroupId:g.prevGroupId}});hideLoader();showToast('前のTradeに追加しました');renderMT5Import();}catch(e){hideLoader();showToast('⚠️ '+e.message);}};
async function status(i,s){var a=visiblePending()[i];if(!a)return;try{await gasPost({action:'setMT5ImportStatus',executionIds:a.ids,status:s});showToast(s+'にしました');renderMT5Import();}catch(e){showToast('⚠️ '+e.message);}}
window.mt5Hold=function(i){status(i,'保留')};window.mt5Exclude=function(i){status(i,'除外')};
document.addEventListener('DOMContentLoaded',function(){ensureUI();});
})();