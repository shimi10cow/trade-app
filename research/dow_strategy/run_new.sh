#!/bin/bash
# usage: run_new.sh SYM DT_START   (workspace from make_ws2.py)
P=$1; W=/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad/ws_$P
cd $W/research
export DT_CACHE=$W/cache DT_START=$2 EA_M15_CACHE=$W/M15_broker.csv M5_SYM=$P NPROC=2
t0=$(date +%s); ts(){ echo "[$P $(( ($(date +%s)-t0)/60 ))min] $1"; }
ts "1 dow"; python -c "import sys; sys.path.insert(0,'dow_strategy'); import dow_turn_ea" 2>&1 | tail -1
ts "2 range/tri"; python dow_strategy/gen_range_score.py 2>&1 | tail -1; python dow_strategy/gen_tri_intervals.py 2>&1 | tail -1
ts "3 character"; python dow_strategy/character2.py 2>&1 | grep -v prep > $W/character2.txt; python dow_strategy/fingerprint.py 2>&1 | grep -v prep > $W/fingerprint.txt; python dow_strategy/session_study.py 2>&1 | grep -v prep > $W/session_study.txt
ts "4 R/T"; python dow_strategy/regime_ea2.py R2c T1t 2>&1 | grep "^\["
ts "5 L"; python dow_strategy/tl_ea.py N2 2>&1 | grep -E "^N2|全体" | head -3
ts "6 A"; python dow_strategy/retest_ea.py N1 2>&1 | grep -E "^N1|全体" | head -3
ts "7 C"; python dow_strategy/step2b_cl15.py 2>&1 | grep md4tri
ts "8 J2"; python dow_strategy/turn_tune2.py 2>&1 | grep -v prep | head -5
ts "9 J3"; python dow_strategy/j3_ea.py $P 2>&1 | grep -v prep | head -5
ts "10 EV"; python dow_strategy/session_ea.py 2>&1 | grep -v prep | head -8
ts "11 P"; python dow_strategy/pb_ea.py P4 2>&1 | grep "^P4"
ts DONE
