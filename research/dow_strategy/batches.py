import json, glob, os, sys
os.chdir(sys.argv[1])
fs = sorted(os.path.relpath(p) for p in glob.glob('data/*.json'))
yr = [f for f in fs if os.path.basename(f)[:4].isdigit()]; small = [f for f in fs if f not in yr]
B = [small[:]]; size = sum(os.path.getsize(f) for f in small)
for f in yr:
    s = os.path.getsize(f)
    if size + s > 55e6:
        B.append([]); size = 0
    B[-1].append(f); size += s
for b in B: print(json.dumps(b))
