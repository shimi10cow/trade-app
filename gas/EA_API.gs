/**
 * Hybrid EA API add-on for the existing Trade Tracker GAS.
 * Add the two router lines shown at the bottom to the existing doGet/doPost.
 */
const EA_SHEETS_ = {
  settings:'EA_Settings', signals:'EA_Signals', executions:'MT5_Executions',
  trades:'EA_Trades', app:'App_Settings', errors:'EA_Errors'
};
const EA_HEADERS_ = {
  EA_Settings:['Pair','稼働方法','許可方向','M15','H1','Lot方式','Lot値','Risk上限ON','Risk上限%','決済方法','通知Signal','通知Entry','通知Exit','通知Error','UpdatedAt'],
  EA_Signals:['SignalID','SignalTime','Pair','Direction','TF','Pattern','EntryPrice','InitialSL','TP','Decision','Reason','EnvironmentSnapshot','SettingsSnapshot','ExitTime','VirtualExitPrice','VirtualPips','VirtualR','VirtualProfit','CreatedAt','UpdatedAt'],
  MT5_Executions:['ExecutionID','SignalID','Time','Pair','Direction','AccountID','Server','OrderID','DealID','Volume','Price','SL','TP','DryRun','RawJSON'],
  EA_Trades:['TradeGroupID','Source','Pair','Direction','FirstEntryTime','LastExitTime','EntryPrice','ExitPrice','TotalLot','Pips','R','Profit','Status','AccountIDs','TicketIDs','DealIDs','CreatedAt','UpdatedAt'],
  App_Settings:['Key','Value','UpdatedAt'],
  EA_Errors:['Time','Pair','Type','Message','RawJSON']
};
function eaSS_(){return SpreadsheetApp.getActiveSpreadsheet();}
function eaSheet_(name){
  const ss=eaSS_();let sh=ss.getSheetByName(name);if(!sh)sh=ss.insertSheet(name);
  const h=EA_HEADERS_[name]||[];if(h.length){
    if(sh.getLastRow()===0)sh.getRange(1,1,1,h.length).setValues([h]);
    else{const cur=sh.getRange(1,1,1,Math.max(sh.getLastColumn(),1)).getValues()[0];h.forEach(x=>{if(cur.indexOf(x)<0){sh.getRange(1,sh.getLastColumn()+1).setValue(x);cur.push(x);}});}
  } return sh;
}
function eaObjRows_(sh){
  if(sh.getLastRow()<2)return [];const v=sh.getDataRange().getValues(),h=v.shift();
  return v.filter(r=>r.some(x=>x!==''&&x!=null)).map(r=>Object.fromEntries(h.map((x,i)=>[x,r[i]])));
}
function eaAppend_(name,obj){
  const sh=eaSheet_(name),h=sh.getRange(1,1,1,sh.getLastColumn()).getValues()[0];
  sh.appendRow(h.map(k=>{const v=obj[k];return typeof v==='object'&&v!==null?JSON.stringify(v):v??'';}));
}
function eaUpsert_(name,key,keyVal,obj){
  const sh=eaSheet_(name),h=sh.getRange(1,1,1,sh.getLastColumn()).getValues()[0],ki=h.indexOf(key);
  let row=0;if(ki>=0&&sh.getLastRow()>1){const vals=sh.getRange(2,ki+1,sh.getLastRow()-1,1).getValues();for(let i=0;i<vals.length;i++)if(String(vals[i][0])===String(keyVal)){row=i+2;break;}}
  const out=h.map(k=>{const v=obj[k];return typeof v==='object'&&v!==null?JSON.stringify(v):v??'';});
  if(row)sh.getRange(row,1,1,h.length).setValues([out]);else sh.appendRow(out);
}
function eaOn_(v){return /^(ON|TRUE|1|YES|自動売買)$/i.test(String(v||''));}
function eaGetSettings_(){
  const pairs={};eaObjRows_(eaSheet_('EA_Settings')).forEach(r=>{
    const p=String(r.Pair||'').trim();if(!p)return;
    const dir=String(r['許可方向']||'両方').toUpperCase();
    const riskType=r['Lot方式']==='固定Lot'?'fixedLot':r['Lot方式']==='固定損失額'?'fixedLoss':'riskPercent';
    pairs[p]={mode:r['稼働方法']==='自動売買'?'auto':r['稼働方法']==='シグナルのみ'?'signal':'stop',
      direction:dir,m15:eaOn_(r.M15),h1:eaOn_(r.H1),riskType:riskType,riskValue:Number(r['Lot値']||0),
      riskCapEnabled:eaOn_(r['Risk上限ON']),riskCap:Number(r['Risk上限%']||1),eaExit:r['決済方法']!=='手動決済',
      notifySignal:eaOn_(r['通知Signal']),notifyEntry:eaOn_(r['通知Entry']),notifyExit:eaOn_(r['通知Exit']),notifyError:eaOn_(r['通知Error'])};
  });
  const app={};eaObjRows_(eaSheet_('App_Settings')).forEach(r=>app[String(r.Key)]=r.Value);
  return {globalEntry:eaOn_(app.globalEntry),envRefreshMin:Number(app.envRefreshMin||60),settingsRefreshMin:Number(app.settingsRefreshMin||5),
    groupHours:Number(app.groupHours||24),totalRiskCapEnabled:eaOn_(app.totalRiskCapEnabled),totalRiskCap:Number(app.totalRiskCap||0),pairs:pairs};
}
function eaSavePairSetting_(d){
  const row=Object.assign({},d,{UpdatedAt:new Date()});eaUpsert_('EA_Settings','Pair',d.Pair,row);return {ok:true};
}
function eaSaveAppSettings_(d){
  Object.keys(d||{}).forEach(k=>eaUpsert_('App_Settings','Key',k,{Key:k,Value:d[k],UpdatedAt:new Date()}));return {ok:true};
}
function eaSignalId_(){return 'SIG-'+Utilities.getUuid();}
function eaSaveSignal_(b){
  const s=b.signal||{},id=s.signalId||eaSignalId_(),now=new Date();
  eaAppend_('EA_Signals',{SignalID:id,SignalTime:s.time||now,Pair:s.symbol||s.Pair||'',Direction:s.direction||'',TF:s.tf||'M15',Pattern:s.pattern||'',
    EntryPrice:s.entry??'',InitialSL:s.sl??'',TP:s.tp??'',Decision:b.decision||'',Reason:b.reason||'',
    EnvironmentSnapshot:b.environmentSnapshot||{},SettingsSnapshot:b.settingsSnapshot||{},CreatedAt:now,UpdatedAt:now});
  return {ok:true,signalId:id};
}
function eaSaveExecution_(b){
  const x=b.execution||{},s=b.signal||{},a=x.account||{};
  eaAppend_('MT5_Executions',{ExecutionID:'EXE-'+Utilities.getUuid(),SignalID:s.signalId||'',Time:new Date(),Pair:s.symbol||'',Direction:s.direction||'',
    AccountID:a.login||x.accountId||'',Server:a.server||x.server||'',OrderID:x.order||'',DealID:x.deal||'',Volume:x.volume||x.request?.volume||'',
    Price:x.price||x.request?.price||'',SL:x.request?.sl||s.sl||'',TP:x.request?.tp||s.tp||'',DryRun:x.dry_run?'YES':'NO',RawJSON:b});
  return {ok:true};
}
function eaSaveError_(b){eaAppend_('EA_Errors',{Time:new Date(),Pair:b.symbol||'',Type:b.type||'RUNTIME',Message:b.error||'',RawJSON:b});return {ok:true};}
function eaEnsure_(){Object.values(EA_SHEETS_).forEach(eaSheet_);return {ok:true};}

/* Call from existing doGet:
   if (action === 'getEASettings') return jsonResponse({success:true,data:eaGetSettings_()});
   if (action === 'ensureEASheets') return jsonResponse({success:true,data:eaEnsure_()});
*/

/* Call from existing doPost after parsing body:
   if (body.action === 'saveEASettings') return jsonResponse({success:true,data:eaSavePairSetting_(body.data||{})});
   if (body.action === 'saveAppSettings') return jsonResponse({success:true,data:eaSaveAppSettings_(body.data||{})});
   if (body.action === 'saveEASignal') return jsonResponse({success:true,data:eaSaveSignal_(body)});
   if (body.action === 'saveMT5Execution') return jsonResponse({success:true,data:eaSaveExecution_(body)});
   if (body.action === 'saveEAError') return jsonResponse({success:true,data:eaSaveError_(body)});
*/
