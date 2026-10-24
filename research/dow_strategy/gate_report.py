"""Apply the fixed environment gates (defined on the existing EA) to other EAs' trades. No new thresholds."""
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sweep import show, B
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
h4 = load('H4', 'long').reset_index(drop=True); c = pd.Series(h4.c.to_numpy(float)); A = atr(h4); C4 = list(pd.to_datetime(h4.t) + TF_LEN['H4'])
S200 = c.rolling(200).mean().to_numpy(); S1200 = c.rolling(1200).mean().to_numpy()
ER = (c.diff(200).abs() / c.diff().abs().rolling(200).sum()).to_numpy()


def ctx(tr, tcol, scol='side'):
    k = np.array([bisect.bisect_right(C4, t) - 1 for t in pd.to_datetime(tr[tcol])]); s = tr[scol].to_numpy()
    tr = tr.copy(); tr['er'] = ER[k]; tr['sh'] = s * (c.to_numpy()[k] - S200[k]) / A[k]; tr['sd'] = s * (c.to_numpy()[k] - S1200[k]) / A[k]
    return tr


if __name__ == '__main__':
    for f in sys.argv[1:]:
        tr = pd.read_csv(f); R = 'Rc' if 'Rc' in tr else 'R'; T = 't' if 't' in tr else 'time'
        tr = ctx(tr, T); tr['_R'] = tr[R]; tr['_y'] = pd.to_datetime(tr[T]).dt.year
        nm = Path(f).stem; print('###', nm)
        show(tr, ' 全部', tr._R == tr._R)
        show(tr, ' T環境 sd>0 er>0.1', (tr.sd > 0) & (tr.er > 0.1))
        show(tr, ' R環境 er<0.08 sh<3', (tr.er < 0.08) & (tr.sh < 3))
        show(tr, ' 日足側 sd>0', tr.sd > 0)
        show(tr, ' 日足逆 sd<0', tr.sd < 0)
        show(tr, ' 残り', ~(((tr.sd > 0) & (tr.er > 0.1)) | ((tr.er < 0.08) & (tr.sh < 3))))
