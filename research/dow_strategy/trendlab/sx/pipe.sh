cd /home/user/trendlab/sx
s=$1
timeout 1500 python3 run.py $s newall > log_${s}_newall.txt 2>&1
timeout 5000 python3 feat.py $s newall > logfa_$s.txt 2>&1
timeout 3000 python3 exits.py $s > loge_$s.txt 2>&1
echo "PIPE $s done"
