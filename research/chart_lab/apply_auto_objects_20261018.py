from pathlib import Path
p=Path("research/chart_lab/eurusd_chart_lab_complete.html")
s=p.read_text(encoding="utf-8")
assert "const AUTO_LINES=" in s and "function drawAutoLines(){" in s
if "AUTO_OBJECTS_20261018" in s:
    print("already patched");raise SystemExit(0)
addon=r"""
// AUTO_OBJECTS_20261018: Generated lines are normal editable trend objects.
// Preserve the original UI, panning, zooming, drawing tools, and JSON format.
const autoLineRecords=[];
function installAutoTrendObjects(){
 for(const srcTF of TF)for(const typ of ['two','three']){
  const rows=AUTO_LINES[srcTF][typ],times=timestamps[srcTF];
  for(const row of rows){
   const [i,j,p1,p2,kind]=row;
   if(i<0||j<=i||j>=times.length)continue;
   const obj={kind:'trend',tf:srcTF,pts:[{t:times[i],p:p1},{t:times[j],p:p2}],auto:true,autoType:typ,autoSide:kind,autoCreated:times[j],autoRetired:null};
   objects.push(obj);autoLineRecords.push(obj);
  }
 }
}
// Replay visibility and line termination are calculated from the same source bars.
// After a confirmed structural reversal, all old lines on that side retire.
function evaluateAutoRetire(){
 for(const srcTF of TF){
  const b=SERIES[srcTF],arr=autoLineRecords.filter(o=>o.tf===srcTF);
  const lo=[],hi=[];let dir=0,ext=60,price=b[60]?.[4],atr=0;
  const threshold=new Float64Array(b.length),k={W1:1.9,D1:1.9,H4:2,H1:2.4,M15:2.1}[srcTF];
  for(let i=0;i<b.length;i++){
   let v=b[i],prev=i?b[i-1][4]:v[4],tr=Math.max(v[2]-v[3],Math.abs(v[2]-prev),Math.abs(v[3]-prev));
   atr=i?atr+(tr-atr)/7:tr;threshold[i]=k*atr;
  }
  let last=-1;
  for(let i=61;i<b.length;i++){
   let v=b[i];
   if(!dir){if(v[2]>b[60][4]+threshold[i]){dir=1;ext=i;price=v[2]}else if(v[3]<b[60][4]-threshold[i]){dir=-1;ext=i;price=v[3]}continue}
   let pivot=null;
   if(dir===1){if(v[2]>=price){ext=i;price=v[2]}if(i>ext&&price-v[3]>=threshold[i]&&ext>last){pivot={kind:'hi',idx:ext};last=ext;dir=-1;ext=i;price=v[3]}}
   else{if(v[3]<=price){ext=i;price=v[3]}if(i>ext&&v[2]-price>=threshold[i]&&ext>last){pivot={kind:'lo',idx:ext};last=ext;dir=1;ext=i;price=v[2]}}
   if(pivot)(pivot.kind==='lo'?lo:hi).push(pivot.idx);
   for(const o of arr){
    if(o.autoRetired!==null||timesafe(o.autoCreated)>btime(srcTF,i))continue;
    let a=idxAtTime(srcTF,o.pts[0].t),z=idxAtTime(srcTF,o.pts[1].t);
    if(i<=z)continue;
    let y=o.pts[0].p+(o.pts[1].p-o.pts[0].p)*(i-a)/(z-a);
    if(o.autoBroken===undefined&&((o.autoSide==='lo'&&v[4]<y)||(o.autoSide==='hi'&&v[4]>y)))o.autoBroken=i;
    if(o.autoBroken!==undefined&&pivot&&pivot.kind===(o.autoSide==='lo'?'hi':'lo')&&i>o.autoBroken){
      (o.autoAfterBreak??=[]).push(b[pivot.idx][pivot.kind==='hi'?2:3]);
      const t=o.autoAfterBreak;
      if(t.length>=3){const q=t.slice(-3);if(o.autoSide==='lo'?(q[0]>q[1]&&q[1]>q[2]):(q[0]<q[1]&&q[1]<q[2]))o.autoRetired=btime(srcTF,i)}
    }
    // Current protected swing violation retires the old line without waiting for a retest.
    const sw=o.autoSide==='lo'?lo:hi;
    if(sw.length&&i>sw.at(-1)&&((o.autoSide==='lo'&&v[3]<b[sw.at(-1)][3])||(o.autoSide==='hi'&&v[2]>b[sw.at(-1)][2])))o.autoRetired=btime(srcTF,i);
   }
  }
 }
}
function btime(t,i){return timestamps[t][i]}
function timesafe(t){return t}
"""
# Make auto objects behave as ordinary objects, with time-aware display and replay clipping.
s=s.replace("function visibleObject(o){return replayEnd===null||o.pts.every(q=>q.t<=ms(tf,replayEnd))}",
"""function visibleObject(o){if(o.auto){let cutoff=ms(tf,replayEnd===null?D.length-1:replayEnd);return o.autoCreated<=cutoff&&(o.autoRetired===null||cutoff<o.autoRetired)&&o.pts.every(q=>q.t<=cutoff)}return replayEnd===null||o.pts.every(q=>q.t<=ms(tf,replayEnd))}""")
s=s.replace("let rx=geom.w-geom.right;","let rx=o.auto?xTime(ms(tf,geom.stop)):geom.w-geom.right;")
s=s.replace("rx=geom.w-geom.right,ext=","rx=o.auto?xTime(ms(tf,geom.stop)):geom.w-geom.right,ext=")
s=s.replace("drawAutoLines();for(let j=0;j<objects.length;j++)","for(let j=0;j<objects.length;j++)")
s=s.replace("function drawAutoLines(){",addon+"\nfunction drawAutoLines(){")
s=s.replace("refreshAutoPanel();\n\nrenderMA();resize();update();","refreshAutoPanel();\ninstallAutoTrendObjects();evaluateAutoRetire();\nrenderMA();resize();update();")
# The previous auto-lines panel toggles must apply to the actual editable objects.
s=s.replace("if(o.auto){let cutoff=", "if(o.auto){if(!autoTF[o.tf]||(o.autoType==='two'&&!autoShowTwo)||(o.autoType==='three'&&!autoShowThree))return false;let cutoff=")
p.write_text(s,encoding="utf-8")
print("Patched Complete HTML",len(s))
