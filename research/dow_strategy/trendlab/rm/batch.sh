cd /home/user/trendlab
run() { python3 rm/mkframes.py $1 && python3 rm/run4.py $1; }
for s in "$@"; do run $s > rm/log4_$s.txt 2>&1 & done; wait
