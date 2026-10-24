"""Why does EA-T skip some trend legs? Log every completed stochastic signal with each gate's verdict."""
import sys, types, pandas as pd
sys.path.insert(0, '/home/user/trade-app/research/dow_strategy')
import regime_ea2 as R2
RE, LV, EC = R2.RE, R2.LV, R2.EC
E = LV.E
src = open(E.__file__).read()
hook = "            if cfg.p_count_mode=='signal': pcount[side]+=1; point=pcount[side]\n            else: point=None\n"
assert hook in src
src = src.replace(hook, hook + "            SIGLOG.append(dict(t=t,side=side,point=point,regime_id=regime_id,regside=regime_side,close=float(r.close)))\n")
hook2 = "            if cfg.extra_filter is not None and not cfg.extra_filter(t,side): continue\n"
assert hook2 in src
src = src.replace(hook2, "            SIGLOG[-1]['reached_filter']=True\n" + hook2 + "            SIGLOG[-1]['passed_filter']=True\n            if len(positions)>=cfg.max_positions: SIGLOG[-1]['full']=True\n")
M = types.ModuleType('eng_diag'); M.__file__ = E.__file__; M.SIGLOG = []
exec(compile(src, E.__file__, 'exec'), M.__dict__)
def filt(t, s):
    x = RE.feat(t, s); h1 = LV.h1_ok(t, s); tri = EC.env_ok({'notri': 'H4'}, t + pd.Timedelta(minutes=15), s)
    M.SIGLOG[-1].update(h1=h1, side_d=x['side_d'], er=x['er'], notri=tri)
    return h1 and x['side_d'] > 0 and x['er'] > 0.10 and tri
tr = M.run_pair('EURUSD', M.Config(use_long_ma=False, extra_filter=filt))
L = pd.DataFrame(M.SIGLOG)
out = '/tmp/tdiag/'
L.to_csv(out + 'siglog.csv', index=False); tr.to_csv(out + 'trades.csv', index=False)
print(len(L), len(tr))
