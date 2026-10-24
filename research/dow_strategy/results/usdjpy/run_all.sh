#!/bin/bash
J=/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad/jpy
cd $J/research
export DT_CACHE=$J/cache DT_START=2005-01-01 EA_M15_CACHE=$J/USDJPY_M15_long_broker.csv
mkdir -p $DT_CACHE
echo "[1] dow cache"; python -c "import sys; sys.path.insert(0,'dow_strategy'); import dow_turn_ea" 2>&1 | tail -2
echo "[2] range score"; python dow_strategy/gen_range_score.py 2>&1 | tail -1
echo "[3] triangles"; python dow_strategy/gen_tri_intervals.py 2>&1 | tail -1
echo "[4] R/T"; python dow_strategy/regime_ea2.py R2c T1t 2>&1 | grep "^\["
echo "[5] L"; python dow_strategy/tl_ea.py N2 2>&1 | tail -3
echo "[6] A"; python dow_strategy/retest_ea.py N1 2>&1 | tail -3
echo "[7] C"; python dow_strategy/step2b_cl15.py 2>&1 | grep -v prep
echo "[8] existing EA"; python dow_strategy/long_validation.py 1 2>&1 | tail -4
echo "[9] F/S candidates"; python dow_strategy/fail_ea2.py 2>&1 | grep -v prep; python dow_strategy/hsdeny_ea.py 2>&1 | grep -v prep
echo DONE
