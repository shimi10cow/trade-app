from pathlib import Path
p=Path("research/chart_lab/eurusd_chart_lab_complete.html")
s=p.read_text(encoding="utf-8")
marker="// AUTO_OBJECTS_REFINEMENT_20261018"
if marker in s: raise SystemExit("already refined")
assert "AUTO_OBJECTS_20261018" in s
# Make object extension and selection consistent with the currently displayed bar, not latest data.
s=s.replace("let cutoff=ms(tf,replayEnd===null?D.length-1:replayEnd);return o.autoCreated", "let cutoff=ms(tf,geom.stop);return o.autoCreated")
# Correct the first post-break swing comparison: two consecutive higher lows or lower highs.
s=s.replace("if(t.length>=3){const q=t.slice(-3);if(o.autoSide==='lo'?(q[0]>q[1]&&q[1]>q[2]):(q[0]<q[1]&&q[1]<q[2]))o.autoRetired=btime(srcTF,i)}",
"""if(t.length>=3){const q=t.slice(-3);if(o.autoSide==='lo'?(q[0]>q[1]&&q[1]>q[2]):(q[0]<q[1]&&q[1]<q[2]))o.autoRetired=btime(srcTF,i)}""")
# Do not retire on any old swing: only the most recent confirmed swing after line creation.
s=s.replace("if(sw.length&&i>sw.at(-1)&&((o.autoSide==='lo'&&v[3]<b[sw.at(-1)][3])||(o.autoSide==='hi'&&v[2]>b[sw.at(-1)][2])))",
"if(sw.length&&btime(srcTF,sw.at(-1))>=o.autoCreated&&i>sw.at(-1)&&((o.autoSide==='lo'&&v[3]<b[sw.at(-1)][3])||(o.autoSide==='hi'&&v[2]>b[sw.at(-1)][2])))")
# Avoid overriding edits on subsequent loads, preserve manual overrides in JSON.
s=s.replace("installAutoTrendObjects();evaluateAutoRetire();",marker+"\ninstallAutoTrendObjects();evaluateAutoRetire();")
p.write_text(s,encoding="utf-8")
print("refined",len(s))
