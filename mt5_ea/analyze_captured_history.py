"""Analyze histories previously accumulated by capture_current_mt5_history.py."""
import json,sys
from pathlib import Path
import trade_history_analysis as a
def main():
 p=a.ROOT/"analysis_input"/"mt5_deals.json"
 if not p.exists():raise SystemExit("No captured history. First run: py capture_current_mt5_history.py")
 deals=json.loads(p.read_text(encoding="utf-8"))
 pos=a.positions_from_deals(deals);groups=a.group_positions(pos,24);apps=a.fetch_app();groups=a.match_app(groups,apps)
 class Args:abort_hours=.25;abort_pips=3.;abort_money=1000.
 groups=[a.classify_no_move(g,Args) for g in groups];report=a.analyze(groups,5)
 accounts=sorted({(d["server"],d["account"]) for d in deals})
 report["meta"]={"captured_accounts":len(accounts),"accounts":accounts,"deals":len(deals),"positions":len(pos),"trade_groups":len(groups),"app_real_trades":len(apps),"app_matched":sum(1 for g in groups if g["app_entry_id"]),"features":"not reconstructed in captured mode yet"}
 out=a.ROOT/"analysis_output";out.mkdir(exist_ok=True)
 (out/"trade_analysis.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 import csv
 rows=[a.flat(g) for g in groups]
 if rows:
  fields=sorted(set().union(*(r.keys() for r in rows)))
  with open(out/"master_trades.csv","w",newline="",encoding="utf-8-sig") as fh:
   w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows(rows)
 print(json.dumps({"meta":report["meta"],"overall":report["overall"]},ensure_ascii=False,indent=2))
 print("\nSend these two files to ChatGPT for the full analysis:")
 print(out/"master_trades.csv");print(out/"trade_analysis.json")
if __name__=="__main__":main()
