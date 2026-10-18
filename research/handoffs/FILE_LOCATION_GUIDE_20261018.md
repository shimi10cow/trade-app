# 研究ファイルの保存場所と読み方（Claude Code用）

更新: 2026-10-18。GitHub main の実在ファイルを確認して作成。**リンクは現在のGitHub上の保存先**。既存のファイルを移動・削除していない。

## 最初に読む順番
1. [統合引継ぎ](../CLAUDE_CODE_HANDOFF_20261018.md) — ダウ/水平帯/トレンドラインの仕様・注意点
2. [研究マスター](CLAUDE_CODE_MASTER_INDEX_20261018.md) — EA系と構造認識系の区別
3. [研究の旧INDEX](../INDEX.md) — 過去の研究経緯。**記載された保存状況は古い場合がある**
4. このファイルの分類別一覧で実ファイルを探す

## ステータスの意味
- **仕様**: 合意ルール。コード実装や実測完了を保証しない。
- **コード**: GitHub上に存在。実行成功を保証しない。
- **結果**: 記録された分析結果。再現性・因果性を別途検証する。
- **旧版**: 過去の記録。最新仕様より優先しない。

## 01 Dow・ダウ構造（6ファイル）
- [DOW_RULES_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/DOW_RULES_20261018.md) — 資料、5701 bytes
- [DOW_RULES_AND_ENGINE.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/DOW_RULES_AND_ENGINE.md) — 資料、2574 bytes
- [README.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/README.md) — 資料、723 bytes
- [build_dow_final.py](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/build_dow_final.py) — コード、1608 bytes
- [dow_final_counts.csv](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/dow_final_counts.csv) — 結果/データ、344 bytes
- [dow_final_engine.py](https://github.com/shimi10cow/trade-app/blob/main/research/dow_frozen_v1/dow_final_engine.py) — コード、2358 bytes

## 02 ダウ移行・D1再構築（4ファイル）
- [ARTIFACT_MANIFEST.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_migration_20261018/ARTIFACT_MANIFEST.md) — 資料、1929 bytes
- [CLAUDE_CODE_HANDOFF.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_migration_20261018/CLAUDE_CODE_HANDOFF.md) — 資料、7918 bytes
- [UPLOAD_STATUS_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/dow_migration_20261018/UPLOAD_STATUS_20261018.md) — 資料、1437 bytes
- [artifacts/d1_rebuild.py](https://github.com/shimi10cow/trade-app/blob/main/research/dow_migration_20261018/artifacts/d1_rebuild.py) — コード、3994 bytes

## 03 チャート・水平帯・トレンドライン（12ファイル）
- [COMPLETE_HTML_STATUS.md](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/COMPLETE_HTML_STATUS.md) — 資料、1297 bytes
- [FEATURE_MAP.md](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/FEATURE_MAP.md) — 資料、3258 bytes
- [TRENDLINE_RULES.md](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/TRENDLINE_RULES.md) — 資料、6319 bytes
- [TRENDLINE_RULES_REVIEW_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/TRENDLINE_RULES_REVIEW_20261018.md) — 資料、4329 bytes
- [apply_auto_objects_20261018.py](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/apply_auto_objects_20261018.py) — コード、4542 bytes
- [eurusd_chart_lab_complete.html](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/eurusd_chart_lab_complete.html) — 表示、5482448 bytes
- [eurusd_trendline_asof_lab_20261018.html](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/eurusd_trendline_asof_lab_20261018.html) — 表示、10318 bytes
- [refine_auto_objects_20261018.py](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/refine_auto_objects_20261018.py) — コード、1514 bytes
- [specs/2026-10-18_dow_horizontal_zones_rules.md](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/specs/2026-10-18_dow_horizontal_zones_rules.md) — 資料、6450 bytes
- [stop_auto_lines_at_retirement_20261018.py](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/stop_auto_lines_at_retirement_20261018.py) — コード、1344 bytes
- [test_trendline_causal_engine.py](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/test_trendline_causal_engine.py) — コード、1659 bytes
- [trendline_causal_engine.py](https://github.com/shimi10cow/trade-app/blob/main/research/chart_lab/trendline_causal_engine.py) — コード、8227 bytes

## 04 EA共通エンジン（7ファイル）
- [ENGINE_README.md](https://github.com/shimi10cow/trade-app/blob/main/research/core/ENGINE_README.md) — 資料、1268 bytes
- [NEW_EA_RULES_2026-10-15.md](https://github.com/shimi10cow/trade-app/blob/main/research/core/NEW_EA_RULES_2026-10-15.md) — 資料、4082 bytes
- [README.md](https://github.com/shimi10cow/trade-app/blob/main/research/core/README.md) — 資料、2074 bytes
- [cache_m15.py](https://github.com/shimi10cow/trade-app/blob/main/research/core/cache_m15.py) — コード、2305 bytes
- [calc_wave_subset_dd_20261015.py](https://github.com/shimi10cow/trade-app/blob/main/research/core/calc_wave_subset_dd_20261015.py) — コード、2102 bytes
- [engine_m15.py](https://github.com/shimi10cow/trade-app/blob/main/research/core/engine_m15.py) — コード、21779 bytes
- [run_compare.py](https://github.com/shimi10cow/trade-app/blob/main/research/core/run_compare.py) — コード、2394 bytes

## 05 EA補助・分析（2ファイル）
- [dd_causal_wave_maturity_20261015_original.py](https://github.com/shimi10cow/trade-app/blob/main/research/ea_shared/dd_causal_wave_maturity_20261015_original.py) — コード、3817 bytes
- [reproduce_wave_subset_20261015.py](https://github.com/shimi10cow/trade-app/blob/main/research/ea_shared/reproduce_wave_subset_20261015.py) — コード、2521 bytes

## 06 個別研究・実験（16ファイル）
- [experiments/02_expansion/run_comparison.py](https://github.com/shimi10cow/trade-app/blob/main/research/studies/experiments/02_expansion/run_comparison.py) — コード、2282 bytes
- [experiments/03_h4_rsi/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/experiments/03_h4_rsi/README.md) — 資料、999 bytes
- [experiments/03_h4_rsi/compare.py](https://github.com/shimi10cow/trade-app/blob/main/research/studies/experiments/03_h4_rsi/compare.py) — コード、1128 bytes
- [ma_wave_filter_research.py](https://github.com/shimi10cow/trade-app/blob/main/research/studies/ma_wave_filter_research.py) — コード、1467 bytes
- [notes/2026-10-15_D1_Dow_ZigZag_v0.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_D1_Dow_ZigZag_v0.md) — 資料、2289 bytes
- [notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_EURUSD_DD_wave_maturity_reference.md) — 資料、3735 bytes
- [notes/2026-10-15_EURUSD_price_structure_research_plan.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_EURUSD_price_structure_research_plan.md) — 資料、2985 bytes
- [notes/2026-10-15_H4_confirmed_pivot_empirical_check.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_H4_confirmed_pivot_empirical_check.md) — 資料、2246 bytes
- [notes/2026-10-15_H4_reversal_M15_P1P2.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_H4_reversal_M15_P1P2.md) — 資料、2205 bytes
- [notes/2026-10-15_MA_filter_ON_position_cap_results.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_MA_filter_ON_position_cap_results.md) — 資料、1570 bytes
- [notes/2026-10-15_MA_wave_filters_P4_position_cap_plan.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_MA_wave_filters_P4_position_cap_plan.md) — 資料、1987 bytes
- [notes/2026-10-15_P4_position_cap_executed_results.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_P4_position_cap_executed_results.md) — 資料、1220 bytes
- [notes/2026-10-15_wave_P1_P2_recovery_audit.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-15_wave_P1_P2_recovery_audit.md) — 資料、1661 bytes
- [notes/2026-10-18_CLAUDE_CODE_MIGRATION_HANDOFF.md](https://github.com/shimi10cow/trade-app/blob/main/research/studies/notes/2026-10-18_CLAUDE_CODE_MIGRATION_HANDOFF.md) — 資料、7255 bytes
- [scripts/h4_reversal_m15_p12_signals.py](https://github.com/shimi10cow/trade-app/blob/main/research/studies/scripts/h4_reversal_m15_p12_signals.py) — コード、3108 bytes
- [scripts/structure_study_20261015.py](https://github.com/shimi10cow/trade-app/blob/main/research/studies/scripts/structure_study_20261015.py) — コード、2205 bytes

## 07 結果（5ファイル）
- [2026-10-15_wave_maturity/DD_wave_annual_284.csv](https://github.com/shimi10cow/trade-app/blob/main/research/results/2026-10-15_wave_maturity/DD_wave_annual_284.csv) — 結果/データ、643 bytes
- [2026-10-15_wave_maturity/DD_wave_annual_359.csv](https://github.com/shimi10cow/trade-app/blob/main/research/results/2026-10-15_wave_maturity/DD_wave_annual_359.csv) — 結果/データ、642 bytes
- [2026-10-15_wave_maturity/DD_wave_h1_h4_interaction.csv](https://github.com/shimi10cow/trade-app/blob/main/research/results/2026-10-15_wave_maturity/DD_wave_h1_h4_interaction.csv) — 結果/データ、414 bytes
- [2026-10-15_wave_maturity/DD_wave_subset_performance_20261015.csv](https://github.com/shimi10cow/trade-app/blob/main/research/results/2026-10-15_wave_maturity/DD_wave_subset_performance_20261015.csv) — 結果/データ、711 bytes
- [2026-10-15_wave_maturity/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/results/2026-10-15_wave_maturity/README.md) — 資料、4709 bytes

## 08 データ（5ファイル）
- [derived/eurusd_d1_structure/2026-10-15/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/datasets/derived/eurusd_d1_structure/2026-10-15/README.md) — 資料、1466 bytes
- [derived/eurusd_h4_structure/2026-10-15/h4_annual_structure_summary.csv](https://github.com/shimi10cow/trade-app/blob/main/research/datasets/derived/eurusd_h4_structure/2026-10-15/h4_annual_structure_summary.csv) — 結果/データ、1178 bytes
- [derived/eurusd_h4_structure/2026-10-15/h4_confirmed_pivots.csv](https://github.com/shimi10cow/trade-app/blob/main/research/datasets/derived/eurusd_h4_structure/2026-10-15/h4_confirmed_pivots.csv) — 結果/データ、554480 bytes
- [derived/eurusd_h4_structure/2026-10-15/h4_structure_bars.csv](https://github.com/shimi10cow/trade-app/blob/main/research/datasets/derived/eurusd_h4_structure/2026-10-15/h4_structure_bars.csv) — 結果/データ、5048367 bytes
- [derived/eurusd_m15/2026-10-15/MANIFEST.md](https://github.com/shimi10cow/trade-app/blob/main/research/datasets/derived/eurusd_m15/2026-10-15/MANIFEST.md) — 資料、1408 bytes

## 09 引継ぎ（5ファイル）
- [CLAUDE_CODE_MASTER_INDEX_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/handoffs/CLAUDE_CODE_MASTER_INDEX_20261018.md) — 資料、4683 bytes
- [CLAUDE_EA_RESEARCH_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/handoffs/CLAUDE_EA_RESEARCH_20261018.md) — 資料、2810 bytes
- [README_CLAUDE_MIGRATION_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/handoffs/README_CLAUDE_MIGRATION_20261018.md) — 資料、2797 bytes
- [RESEARCH_INDEX_20261018.md](https://github.com/shimi10cow/trade-app/blob/main/research/handoffs/RESEARCH_INDEX_20261018.md) — 資料、7182 bytes
- [import_claude_bundle_20261018.py](https://github.com/shimi10cow/trade-app/blob/main/research/handoffs/import_claude_bundle_20261018.py) — コード、2234 bytes

## 10 旧版（22ファイル）
- [RESEARCH_MAP_20261015.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/RESEARCH_MAP_20261015.md) — 資料、2491 bytes
- [backtest_recovery/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/backtest_recovery/README.md) — 資料、2188 bytes
- [backtest_recovery/REPRO_AUDIT_2026-10-14.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/backtest_recovery/REPRO_AUDIT_2026-10-14.md) — 資料、1741 bytes
- [backtest_recovery/SL_WIDTH_AUDIT_2026-10-14.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/backtest_recovery/SL_WIDTH_AUDIT_2026-10-14.md) — 資料、1658 bytes
- [backtest_recovery/full_backtest_engine_v1_recovered.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/backtest_recovery/full_backtest_engine_v1_recovered.py) — コード、19956 bytes
- [forextester/2026-10-14_BACKTEST_RESULTS.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/2026-10-14_BACKTEST_RESULTS.md) — 資料、3534 bytes
- [forextester/2026-10-14_H4_STRUCTURE_DESIGN.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/2026-10-14_H4_STRUCTURE_DESIGN.md) — 資料、3562 bytes
- [forextester/2026-10-14_run_recovered_h4_absent.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/2026-10-14_run_recovered_h4_absent.py) — コード、2319 bytes
- [forextester/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/README.md) — 資料、2235 bytes
- [forextester/RECOVERED_ENGINE_ABLATION_23Y_2026-10-14.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/RECOVERED_ENGINE_ABLATION_23Y_2026-10-14.md) — 資料、2482 bytes
- [forextester/prepare_mtf.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/forextester/prepare_mtf.py) — コード、2863 bytes
- [legacy_scripts/BASELINE_EURUSD_USDJPY_2003_2026_20261014.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/BASELINE_EURUSD_USDJPY_2003_2026_20261014.md) — 資料、2638 bytes
- [legacy_scripts/EURUSD_H4_2003_2026_RESULTS_20261014.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/EURUSD_H4_2003_2026_RESULTS_20261014.md) — 資料、2968 bytes
- [legacy_scripts/eurusd_2003_2026_run.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/eurusd_2003_2026_run.py) — コード、527 bytes
- [legacy_scripts/eurusd_h4_backtest_20261014.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/eurusd_h4_backtest_20261014.py) — コード、471 bytes
- [legacy_scripts/eurusd_precompute_20261014.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/eurusd_precompute_20261014.py) — コード、1556 bytes
- [legacy_scripts/full_backtest_engine_v1_20261014.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/full_backtest_engine_v1_20261014.py) — コード、19956 bytes
- [legacy_scripts/usdjpy_2003_2026_run.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/legacy_scripts/usdjpy_2003_2026_run.py) — コード、527 bytes
- [shared_backtest_20261014/README.md](https://github.com/shimi10cow/trade-app/blob/main/research/archive/shared_backtest_20261014/README.md) — 資料、3580 bytes
- [shared_backtest_20261014/engine.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/shared_backtest_20261014/engine.py) — コード、20182 bytes
- [shared_backtest_20261014/fastpivot_patch.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/shared_backtest_20261014/fastpivot_patch.py) — コード、1465 bytes
- [shared_backtest_20261014/runner.py](https://github.com/shimi10cow/trade-app/blob/main/research/archive/shared_backtest_20261014/runner.py) — コード、5206 bytes

## 11 MT5運用（36ファイル）
- [.env.example](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/.env.example) — その他、283 bytes
- [EA_START.bat](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/EA_START.bat) — その他、381 bytes
- [EA_STOP.bat](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/EA_STOP.bat) — その他、629 bytes
- [MT5_IMPORT_START.bat](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/MT5_IMPORT_START.bat) — その他、130 bytes
- [MT5_LINK_START.bat](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/MT5_LINK_START.bat) — その他、128 bytes
- [MT5_LINK_STOP.bat](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/MT5_LINK_STOP.bat) — その他、127 bytes
- [README.md](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/README.md) — 資料、3356 bytes
- [SETUP_MT5_LINK_DESKTOP.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/SETUP_MT5_LINK_DESKTOP.ps1) — その他、692 bytes
- [configure_live_lock.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/configure_live_lock.ps1) — その他、622 bytes
- [configure_telegram.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/configure_telegram.ps1) — その他、914 bytes
- [connection_test.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/connection_test.py) — コード、4079 bytes
- [execution_path_test.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/execution_path_test.py) — コード、3110 bytes
- [final_pre_live_check.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/final_pre_live_check.ps1) — その他、1003 bytes
- [h1_strategy.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/h1_strategy.py) — コード、7992 bytes
- [live_safety_test.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/live_safety_test.py) — コード、2516 bytes
- [m15_strategy.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/m15_strategy.py) — コード、16485 bytes
- [main.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/main.py) — コード、45189 bytes
- [mt5_account_worker.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/mt5_account_worker.py) — コード、1497 bytes
- [mt5_accounts.example.json](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/mt5_accounts.example.json) — その他、294 bytes
- [mt5_import_worker.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/mt5_import_worker.py) — コード、8005 bytes
- [mt5_position_sync.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/mt5_position_sync.py) — コード、5633 bytes
- [preflight.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/preflight.py) — コード、7377 bytes
- [replay_signals.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/replay_signals.py) — コード、7286 bytes
- [requirements.txt](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/requirements.txt) — その他、21 bytes
- [runtime_check.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/runtime_check.py) — コード、2365 bytes
- [setup_desktop_shortcuts.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/setup_desktop_shortcuts.ps1) — その他、629 bytes
- [setup_mt5_accounts.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/setup_mt5_accounts.ps1) — その他、2063 bytes
- [start_dry_run.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/start_dry_run.ps1) — その他、565 bytes
- [start_live.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/start_live.ps1) — その他、1835 bytes
- [start_mt5_import.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/start_mt5_import.ps1) — その他、656 bytes
- [stop_mt5_import.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/stop_mt5_import.ps1) — その他、336 bytes
- [strategy_tests.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/strategy_tests.py) — コード、3957 bytes
- [telegram_notify.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/telegram_notify.py) — コード、2819 bytes
- [telegram_test.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/telegram_test.py) — コード、2170 bytes
- [verify_dry_run.ps1](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/verify_dry_run.ps1) — その他、648 bytes
- [verify_mt5_accounts.py](https://github.com/shimi10cow/trade-app/blob/main/mt5_ea/verify_mt5_accounts.py) — コード、1033 bytes

## データの欠落・注意
- EURUSD M1 ZIP、583,458本のM15 PKLキャッシュは**このGitHub一覧には存在しない**。元データは別途持ち込む。
- 100ファイルの研究ZIPは引継ぎ資料に記録されているが、このリポジトリに全件アップロード済みとは言えない。
- 一部のREADMEには『未アップロード』と記されているCSVが現時点では存在する。**保存有無は本一覧とGitHub実体を優先し、正しさは別途検証**。
- 同名の engine_m15.py / run_compare.py は別ディレクトリの異なる研究版。SHAと設定を照合せず混ぜない。
- 272件 +72.86R の最新報告値は取引台帳・エンジンとの対応未確認。

## 検証結果とエンジンの対応（最重要）
**[検証条件・使用エンジン・結果の対応表](EXPERIMENT_ENGINE_MATRIX_20261018.md)** を必ず参照。各研究の期間、通貨、フィルター、SL、トレーリング、最大同時保有数、報告値、コード・結果ファイル、再現性ステータスを掲載。実行エンジンが確定していないものは未特定と明記。
