from pathlib import Path
p=Path("research/chart_lab/eurusd_chart_lab_complete.html")
s=p.read_text(encoding="utf-8")
marker="// AUTO_LINE_STOP_AT_RETIRE_20261018"
if marker in s: raise SystemExit("already patched")
assert "AUTO_OBJECTS_20261018" in s
# A retired object stays visible in history, but is drawn only until its retirement time.
old="return o.autoCreated<=cutoff&&(o.autoRetired===null||cutoff<o.autoRetired)&&o.pts.every(q=>q.t<=cutoff)"
new="return o.autoCreated<=cutoff&&o.pts.every(q=>q.t<=cutoff)"
assert old in s
s=s.replace(old,new)
old="let A=a[0],B=a[1],dx=B.x-A.x,dy=B.y-A.y,rx=geom.w-geom.right;"
new="let A=a[0],B=a[1],dx=B.x-A.x,dy=B.y-A.y,rx=o.auto?xTime(Math.min(ms(tf,geom.stop),o.autoRetired===null?Infinity:o.autoRetired)):geom.w-geom.right;"
assert old in s
s=s.replace(old,new)
# Align mouse hit-testing with the actually rendered, terminated segment.
old="rx=geom.w-geom.right,ext="
new="rx=o.auto?xTime(Math.min(ms(tf,geom.stop),o.autoRetired===null?Infinity:o.autoRetired)):geom.w-geom.right,ext="
assert old in s
s=s.replace(old,new)
# Prevent future invalidation from hiding the line before its time.
s=s.replace("installAutoTrendObjects();evaluateAutoRetire();",marker+"\ninstallAutoTrendObjects();evaluateAutoRetire();")
p.write_text(s,encoding="utf-8")
print("Retirement-end rendering installed",len(s))
