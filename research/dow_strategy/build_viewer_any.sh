#!/bin/bash
# usage: build_viewer_any.sh SYM DT_START Y0 Y1 FIXMODE DECIMALS [PF_S]
P=$1; ST=$2; Y0=$3; Y1=$4; FIX=$5; ND=$6; PFS=$7
S=/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad; W=$S/ws_$P; OUT=$S/viewer_$P
R=/home/user/trade-app/research/dow_strategy
for f in build_stage_viewer.py m15_corr_lines.py triangles.py build_pf_trades.py gen_pbcount.py viewer_price_fix.py stage_viewer_template.html ea_core.py; do cp $R/$f $W/research/dow_strategy/; done
[ -f $W/research/dow_strategy/results/long_features_1.csv ] || cp $S/ws_USDJPY/research/dow_strategy/results/long_features_1.csv $W/research/dow_strategy/results/
cd $W/research; export DT_CACHE=$W/cache DT_START=$ST EA_M15_CACHE=$W/M15_broker.csv
mkdir -p $OUT/data; YRS=$(seq $Y0 $Y1)
t0=$(date +%s); ts(){ echo "[$P $(( ($(date +%s)-t0)/60 ))min] $1"; }
ts "1 stage"; python dow_strategy/build_stage_viewer.py $OUT $YRS 2>&1 | tail -2
ts "2 corr lines"; python dow_strategy/m15_corr_lines.py $OUT/data $YRS 2>&1 | tail -1
ts "3 triangles"; python dow_strategy/triangles.py v2 $OUT/data $YRS 2>&1 | tail -1
ts "4 EA trades"; PF_RESULTS=$W/research/dow_strategy/results PF_S=$PFS python dow_strategy/build_pf_trades.py $OUT/data $YRS 2>&1 | tail -1
ts "5 pb count"; python dow_strategy/gen_pbcount.py $OUT/data 2>&1 | tail -2
if [ "$FIX" != "none" ]; then ts "6 price fix"; python dow_strategy/viewer_price_fix.py $OUT/data $FIX $ND; fi
du -sh $OUT/data; ts VIEWER_DONE
