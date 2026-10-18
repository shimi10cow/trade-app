# 検証結果 × 条件 × エンジン対応表（2026-10-18）

**目的:** Claude Codeが結果だけを見て別のエンジン・別のSL/トレーリング条件と混同しないこと。ここでの数値は既存レポートの転記であり、今回再実行していない。リンクはリポジトリ内の実在パスを優先。**推定でエンジンを確定しない**。

## まず守るルール
- 研究ごとに「期間/通貨/元データ/エントリー/SL/トレーリング/P段階/最大同時数/スプレッド/フィルター/エンジン/台帳/結果」を1セットとして扱う。
- エンジンのSHA、実行コマンド、入力データSHA、設定ファイル、取引台帳が欠けた結果は **再現未確認** と表示。
- retrospective subset（既存取引からの抽出）はフィルターONで全件再実行した結果ではない。
- +2R開始の旧EAと+1.5R開始の436件研究を同一のベースラインと呼ばない。
- GitHubのコードは存在しても実行可能性・現行仕様との一致を保証しない。

## 実測・報告の対応表

|ID|対象・期間|固定/変更した条件|報告結果|エンジン・再現コード|結果・根拠|信頼性|
|---|---|---|---|---|---|---|
|LEGACY-SIMPLE|複数銘柄 2015–2026|H1 SMA200/480、M15 Stoch、旧ZZ +2R、Simple|1,974件 +359.6R PF1.308 DD−42.3R|[旧版エンジン](../archive/legacy_scripts/full_backtest_engine_v1_20261014.py) は存在するが**数値との同一性未確認**|[現行仕様まとめ](EA_CURRENT_IMPLEMENTATION_SPEC_20261018.md)|過去報告、再現未確認|
|LEGACY-H4|複数銘柄 2015–2026|上記にH4 96h+25pt条件|1,681件 +327.41R PF1.332 DD−34.84R|旧版系統、実行版SHA未特定|[現行仕様まとめ](EA_CURRENT_IMPLEMENTATION_SPEC_20261018.md)|過去報告、再現未確認|
|FOREX-H4OFF|EURUSD/USDJPY 2003–2026|ForexTester M1→M15、H4水平線拒否OFF、**スプレッド/スリッページなし**|EURUSD 1,381件 +167.316R PF1.192 DD−35.023R / USDJPY 1,304件 +101.567R PF1.120 DD−59.939R|[再構築エンジン](../archive/backtest_recovery/full_backtest_engine_v1_recovered.py) + [実行スクリプト](../archive/forextester/2026-10-14_run_recovered_h4_absent.py)|[実測レポート](../archive/forextester/2026-10-14_BACKTEST_RESULTS.md)|報告された実行、コスト未反映|
|EUR436|EURUSD 2003–2026|M15 SMA200 SL、最低10pip、+1.5RからZZ、同時2件。細部は要台帳照合|436件、+64.70R、PF1.255（過去報告）|研究ZIP内の trail_variant_engine.py など。**GitHub上の完全な実行版・台帳未確認**|[EA研究引継ぎ](CLAUDE_EA_RESEARCH_20261018.md)、[研究ZIP手順](README_CLAUDE_MIGRATION_20261018.md)|入力アーカイブ未収録|
|WAVE-359|EURUSD 2003–2026、元1,117件の事後抽出|H4 impulse ratio ≥0.70、H1 ratio <0.75|359件 +100.531R PF1.451775 DD−17.561R|[特徴量生成の原版](../ea_shared/dd_causal_wave_maturity_20261015_original.py) + [集計再現](../ea_shared/reproduce_wave_subset_20261015.py)|[結果README](../results/2026-10-15_wave_maturity/README.md)、[CSV](../results/2026-10-15_wave_maturity/DD_wave_subset_performance_20261015.csv)|**未来参照リスク判明・暫定**|
|WAVE-284|EURUSD 2003–2026、同上|WAVE-359条件 + d480 <12（ATR単位）|284件 +105.664R PF1.613828 DD−14.412R|同上|[結果README](../results/2026-10-15_wave_maturity/README.md)、[年別CSV](../results/2026-10-15_wave_maturity/DD_wave_annual_284.csv)|**未来参照リスク判明・暫定**|
|FILTER-A-CAP2|EURUSD 2003–2026|H4 impulse≥0.70、H1 impulse<0.75、同時2件、2L/2R確定フラクタル、**コストなし**|547件 +92.703R PF1.269 DD−30.082R|[MA/wave研究エンジン](../studies/ma_wave_filter_research.py)（実行版照合要）|[ON実行レポート](../studies/notes/2026-10-15_MA_filter_ON_position_cap_results.md)|研究用再構築|
|FILTER-B-CAP2|EURUSD 2003–2026|FILTER-A + H1 SMA480距離 <12 ATR14、同時2件、**コストなし**|435件 +119.872R PF1.452 DD−17.383R|同上|[ON実行レポート](../studies/notes/2026-10-15_MA_filter_ON_position_cap_results.md)|研究用再構築|
|FILTER-B-CAP3|EURUSD 2003–2026|FILTER-B、同時3件、**コストなし**|447件 +127.664R PF1.468 DD−20.000R|同上|[ON実行レポート](../studies/notes/2026-10-15_MA_filter_ON_position_cap_results.md)|研究用再構築|
|P4-CAP|EURUSD 2003–2026|P3/P4許可と同時保有2/4件の比較、**コストなし**|P3 cap2: 1,398件 +162.956R PF1.183 DD−58.180R; P4 cap2: 1,652件 +79.523R PF1.073 DD−91.767R|[MA/wave研究エンジン](../studies/ma_wave_filter_research.py)（実行版照合要）|[実測レポート](../studies/notes/2026-10-15_P4_position_cap_executed_results.md)|フィルター抽出欄は事後抽出|
|RECENT-272|期間・銘柄未特定|条件・エンジン・取引台帳が不明|272件 +72.86R 平均+0.268R PF1.456 DD−11.12R|**未特定**|チャット上のユーザー報告のみ|再現不可、要照合|

## その他の検証（実装と採否を混同しない）
- q75、MA ABCD、H1逆トレンド、H4 RSI、H4水平線、MA expansion、240h遅延ZZ： [現行実装仕様](EA_CURRENT_IMPLEMENTATION_SPEC_20261018.md)、[coreルール](../core/NEW_EA_RULES_2026-10-15.md)、[旧バックテスト](../archive/forextester/RECOVERED_ENGINE_ABLATION_23Y_2026-10-14.md) を参照。各比較の元台帳・同一エンジン検証を確認するまで横並びの改善効果を断定しない。
- [core/engine_m15.py](../core/engine_m15.py) と [core/run_compare.py](../core/run_compare.py) は存在するが、[ENGINE_README](../core/ENGINE_README.md) 自身が完全な583k本検証未完了と明記。上表の実測値の出所として自動採用しない。
- [ダウ固定エンジン](../dow_frozen_v1/dow_final_engine.py) はピボット・構造認識研究用であり、上表の損益バックテストエンジンではない。
- [トレンドラインエンジン](../chart_lab/trendline_causal_engine.py) は研究用で、リアルタイムEAとして認証済みではない。

## Claude Codeでの引継ぎ時の最初の実務
1. 各結果の元トレードCSV、設定、実行エンジンのGit SHA、入力データのSHA256を探し、結果行ごとにリンクを補完。
2. 未発見なら MISSING と記録。類似コードで再実行しても同一結果と偽らない。
3. すべてのエンジンの依存関係・起動コマンドを実行して、成功/失敗を記録。
4. 未来参照疑義のある WAVE-359/284 は採用判断から除外して、時系列イベント再生で再構築。
5. フィルター比較は約定順・同時保有制限を含むフルバックテストを行う。
