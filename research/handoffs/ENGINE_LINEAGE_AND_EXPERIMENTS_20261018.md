# 過去EAエンジン系譜・差分・実験対応表
更新: 2026-10-18

## 最初に
**エンジンを1本の最新版とみなさないこと。** 過去のチャットで複数の研究系統を作成し、同じ名前の「エンジン」でもルール・データ・母集団・SL・トレール・P3の扱いが異なる。これは過去会話の仕様と研究ZIPの実在ファイルを突き合わせた**来歴カタログ**であり、全ソースを取得してdiffしたという意味ではない。

状態表記:
- **ZIP内原本確認**: 2026-10-18の100ファイルZIP内にPython原本が存在。
- **過去会話にパス/実装記録**: 過去チャットにパスやコミットの記録あり。2026-10-18のGitHub mainで取得できたとは限らない。
- **原本未回収**: 会話記録にあるが、今回の100ファイルZIPにはPython原本なし。アップロード済みと扱わない。

## 1. エンジン一覧（目的と差分）

| 系統 | エンジン / 関連ファイル | 何をしたものか | 他との重要な違い | 保存・検証状態 |
|---|---|---|---|---|
| A: 旧フルバックテスト | `research/full_backtest_engine_v1_20261014.py` | 2026-10-14以前のEAフル検証。旧エントリー/環境フィルターのベース | 後の共通基盤に移行したため**新規研究では使わない** | 過去会話にパス記録、原本未回収 |
| B: 復旧版 | `research/backtest_recovery/full_backtest_engine_v1_recovered.py` | Aを実行できない場合の復元版 | 元版と同等かソースdiff未確認 | 過去会話にパス記録、原本未回収 |
| C: 2026-10-14共通基盤 | `research/shared_backtest_20261014/engine.py`, `runner.py`, `fastpivot_patch.py` | EURUSD M15、ON/OFFフィルター比較。7条件切替、年別/期間別/取引CSV出力 | 共通コードを使用する想定。M15キャッシュ583,458本、P3実取引→P1/P2集計の研究が中心 | 過去会話にコミット `c06fd68`, `9ffe7de`, `e3e9ee62` の記録。現main取得未確認 |
| D: 新しい共通基盤 | `research/ea_shared/engine_m15.py`, `run_compare.py` | 旧フルエンジンの使用を止めて共通エンジン＋比較ランナーへ切替 | q75 ON、MA expansion exception OFF、H4 RSI OFF、H4水平線OFF、P3エントリー禁止、MA ABCD ON、H1逆トレンド拒否OFFなどの固定条件。**CのP3実取引→集計除外と異なる** | 過去チャットで保存報告あり。ただし2026-10-18 `fetch_file` は404、原本未回収 |
| E: 各実験の独立再構築 | `/mnt/data/exp02/run.py`, `ea08_engine.py` など | 共通基盤を直接動かせない環境で、特定のフィルターだけON/OFFして完走 | 公式共通基盤との全トレード一致が未確認。比較は**各実験内**でのみ有効 | 過去チャットに実行記録、原本未回収 |
| F: トレーリング・SL研究 | `ea_shared/trail_variant_engine.py` | EURUSD 2003–2026、フィルターB、spread1.2pip、P3、cap2等でトレール/SL比較 | SMA SL、+1R/+1.5R/+2R、BE、240h条件等を比較。436件研究の母集団と関係 | **ZIP内原本確認**。GitHubへのZIP取り込みは未確認 |
| G: H4/D1 ZigZag/Dow研究 | `d1_study_20261015/zigzag_dow_reanalysis.py` | ZigZag確定とダウ転換の再解析 | 売買EA本体でなく構造解析用 | **ZIP内原本確認** |
| H: H4イベント研究 | `d1_study_20261015/h4_environment_event_study.py` | H4環境イベントと売買の関係 | ポストホック/イベント研究であり、エントリーEAではない | **ZIP内原本確認** |
| I: H4構造研究 | `ea_research/structure_study_20261015.py` | H4構造・ピボット・相場局面の研究 | フル約定エンジンではなく特徴量研究 | **ZIP内原本確認** |
| J: ライブMT5 EA | ローカル `mt5_ea/`、`start_dry_run.ps1` 等 | XMTrading-MT5への接続、M15/H1シグナル判定、通知・安全ゲート | バックテストではなく実運用用。DRY_RUN / LIVE_ARMEDと注文処理を持つ | 過去チャットにWindows上の実行記録。原本未回収 |

**混同厳禁**：`engine_m15.py` と `trail_variant_engine.py` は別物。`shared_backtest_20261014/engine.py` と `ea_shared/engine_m15.py` も同じパス/版ではない。研究用のH4/D1スクリプトをライブEAと呼ばない。

## 2. 過去のON/OFF研究とエンジンの対応

以下の数値は**過去チャットで報告されたもの**であり、今回の環境で再実行した結果ではない。

| 実験 | 比較対象 | 条件・対象 | 過去の結果 / 結論 | エンジン |
|---|---|---|---|---|
| ② | MA expansion exception ON/OFF | EURUSD 2003–2026、H4水平線OFF、cap2、P3取引後に集計除外 | OFFで追加8件、合計−2.33R。例外撤廃候補 | Cを参照した独立再構築E、`exp02/run.py` |
| ③ | H4 RSI拒否 ON/OFF | 同系統の固定条件 | OFFで全期間+181.35R、PF1.222（過去報告） | C参照のE、`exp03/` |
| ⑤ | 240時間遅延ZigZag ON/OFF | EURUSD M15、+2R ZigZagは維持 | 過去チャットで検証報告あり。**このカタログでは数値未再確認** | C系/E。ZIP/実行ログ照合が必要 |
| ⑥ | MA ABCD拒否 ON/OFF | H4水平線OFF、cap2、P3事後除外 | 2015+はOFFで合計−14.20R、PF1.440→1.379、DD悪化（過去報告）。ON維持候補 | C系/E。ある会話ではM15生成までで実測未完了、別会話の結果と区別 |
| ⑦ | H1逆トレンド拒否 ON/OFF | 同上 | 全期間ON 1,296件/+177.10R、OFF 1,301件/+176.70R。追加5件−0.40R、差小 | C参照のE、`exp07` |
| ⑧ | H1 SMA200 slope閾値 0.00002 vs 0 | 同上 | ON 992件/+118.05R、OFF 997件/+118.31R、差小 | C参照のE、`ea08_engine.py` |
| ⑨ | q75 ON/OFF | 同系統の比較 | ON 992件/+118.05R、OFF 965件/+119.41R（過去報告）。2015+ ON499件/+76.15R、OFF480件/+73.36R | D使用指示後、独立再構築Eで完走との記録 |
| P3 MFE | MFE条件 ON/OFF | P3は実取引後に集計除外、P1/P2の結果 | ON 1,213件/+173.72R、OFF 1,212件/+171.55R（過去報告） | C参照のE |
| 436件SL比較 | SMA200 / 波SL / ハイブリッド | EURUSD全期間、spread1.2、B、P3、cap2、ZigZag+1.5R | 436件を母集団に詳細分析。波SLは同一エントリー比較の可能性があるため再テストと区別 | F系 |
| H4逆行44件 | H4方向・突破・押し目 | 436件の事後分類、直近6 H4本、M15 2pip閾値 | 44件を抽出。厳密なダウW1ではない | G/H/I + 事後分類スクリプト。フルEA再実行ではない |

**実験番号と実装の対応が曖昧なものは、各実験のCSV・ログ・実行コードを回収して確定する。** 数値を「現行EAの成績」として使わない。

## 3. エンジン別の設計差（再現性チェックリスト）

| 比較軸 | 旧/共通EA研究（A–E） | SL・トレール研究（F） | H4/D1構造（G–I） | ライブ（J） |
|---|---|---|---|---|
| 主目的 | フィルターON/OFFの因果比較 | SL・トレールとエントリー品質 | ダウ・ピボット・環境の特徴量 | リアルタイム監視と注文 |
| データ | M1→M15 583,458本 | M15研究キャッシュ＋波特徴量 | M15/H4/D1派生 | MT5リアルタイム |
| P3 | 事後除外 / Dでは禁止 | P3まで含む436件等 | 分析対象に依存 | 実装照合が必要 |
| トレール | 原則+2R ZZ、240h比較 | +1/+1.5/+2R ZZ、BE比較 | 売買しない解析あり | コード照合が必要 |
| フィルター | q75、MA ABCD、H4 RSI、H1逆トレンド等 | A/B、波比率等 | H4/D1スイング・突破 | 実装照合が必要 |
| 約定処理 | cap2等を含むバックテスト | 独立の約定処理 | 該当なしの場合あり | ブローカー実注文・安全ゲート |
| 相互比較 | 同一エンジン/同一入力なら可 | F内なら可 | 事後特徴量のみ | バックテストと直結不可 |

## 4. GitHub/ZIPでの実際の所在
- **この文書（GitHub保存済み）**: `research/handoffs/ENGINE_LINEAGE_AND_EXPERIMENTS_20261018.md`
- **現行仕様書（GitHub保存済み）**: `research/handoffs/EA_CURRENT_IMPLEMENTATION_SPEC_20261018.md`
- **実験条件表（GitHub保存済み）**: `research/handoffs/BACKTEST_ENGINE_AND_CONDITIONS_20261018.md`
- **データ索引（GitHub保存済み）**: `research/handoffs/RESEARCH_INDEX_20261018.md`
- **ZIP原本4スクリプト（GitHub未取り込み）**: `ea_shared/trail_variant_engine.py`, `d1_study_20261015/zigzag_dow_reanalysis.py`, `d1_study_20261015/h4_environment_event_study.py`, `ea_research/structure_study_20261015.py`
- **原本未回収の過去エンジン**: A/B/C/D/E/J。過去コミット/ローカル `mt5_ea/` / 会話添付を探索し、見つかれば原本を**別名・別パスで保存**。差分検証前に上書きしない。
- ZIP取込後は `research/handoffs/ea_bundle_20261018/` 以下に原本が入り、`MANIFEST.json` で100件とSHA-256を照合する。

## 5. Claude Codeがやるべき原本回収と検証
1. `git log --all --oneline -- research/` と `git ls-tree -r --name-only HEAD`、`git branch -a` で過去コミット・ブランチを探索。
2. 上記A/B/C/D/E/Jの実在ソースを確認し、`research/handoffs/engines_archive/<engine-family>/` に原本を保存（既存ソースを破壊しない）。各ファイルのSHA256と由来コミットを記録。
3. C対D、A対C、D対F、F対Jをdiffし、時間足・SMA/stoch・H1傾き・SL・トレール・P3・spread・cap・未来参照防止の違いを**ソース行番号つき**で表にする。
4. 各実験の入力キャッシュ、エンジン版、CLI引数、取引CSV、集計CSV、ログを `experiments_manifest.csv` で紐づける。
5. 436件ベースラインと共通EA研究を**別系統**として再現。取引単位で差分照合後にのみ、横断的な性能比較を行う。
6. 実口座への発注は行わず、`DRY_RUN` と `LIVE_ARMED` を安全側に維持。
