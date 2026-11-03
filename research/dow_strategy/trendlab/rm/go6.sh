cd /home/user/trendlab/rm
for s in EURUSD USDJPY XAUUSD GBPUSD AUDUSD USDCAD USDCHF EURJPY AUDJPY CADJPY CHFJPY; do echo $s; done | xargs -P 4 -I{} sh -c "timeout 2500 python3 run6.py {} > log6_{}.txt 2>&1"
