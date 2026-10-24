"""Final set with / without the two EAs whose neighbouring settings mostly fail (A@EURUSD, Q@US30), same-risk."""
import pandas as pd, pfx
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
X = pd.read_pickle(f'{S}/feat/final_trades.pkl').assign(R=lambda d: d.Rm)
for lab, drop in (('最終セット', []), ('A@EURUSD を外す', ['A@EURUSD']), ('Q@US30 を外す', ['Q@US30']), ('両方外す', ['A@EURUSD', 'Q@US30'])):
    Y = X[~X.key.isin(drop)]; pfx.ev(Y, list(Y.key.unique()), label=lab)
