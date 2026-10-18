# EA研究データ案内 / Claude Code 引き継ぎ索引
更新: 2026-10-18

> **最初に読むファイル**。このリポジトリにはトレードアプリ本体とEA研究が混在するため、研究の入口をここに統一する。

## 0. 保存状態（誤認防止）
| 保存先 | 中身 | 状態 |
|---|---|---|
| `research/handoffs/CLAUDE_EA_RESEARCH_20261018.md` | 研究目的、基本仕様、既知の結果、注意点 | **GitHub保存済み** |
| `research/handoffs/README_CLAUDE_MIGRATION_20261018.md` | 移行方法、欠落事項 | **GitHub保存済み** |
| `research/handoffs/import_claude_bundle_20261018.py` | ZIP展開・ハッシュ一覧生成 | **GitHub保存済み** |
| `research/handoffs/RESEARCH_INDEX_20261018.md` | **この索引** | **GitHub保存済み** |
| `EA_Claude_handoff_research_20261018.zip` | 研究成果物100件 | **ChatGPT会話内のダウンロード添付**。GitHubへの本体反映は未確認 |
| `research/handoffs/ea_bundle_20261018/` | ZIP展開後の100件とMANIFEST.json | **取り込みスクリプト実行後に作成**。現時点では存在を保証しない |
| `EURUSD2003.M1.zip`, `USDJPY2003.M1.zip` | M1元データ | ChatGPT添付/別保管。研究ZIPに含まれない |

**重要**：GitHub上にあると断言できるのは、この索引などの引き継ぎ文書・取り込みスクリプトだけ。ZIP内の100件はローカルで取り込む必要がある。

## 1. 研究の全体像
1. M1履歴をM15に変換し、H1トレンド＋M15ストキャスのエントリーを検証。
2. P1/P2/P3、MA/環境フィルター、スプレッド、最大同時保有数を比較。
3. 初期SL（M15 SMA200・波の安値/高値・ハイブリッド）とZigZagトレーリングを比較。
4. EURUSD 2003–2026の**436件**を起点に、押し目の形成時間・反発率・逆行足・底の再テスト・H4ダウとの関係を探索。
5. H4逆行44件、突破有無、H4混在を含む構造突破後の押し目を探索。
6. 日本時間別成績を集計。ただし元データのUTC仮定は未検証。
7. **エントリー除外フィルターは未採用**。探索集計をEA再実行の確定結果と混同しない。

## 2. ZIP展開後の保存先・用途
以下は全て `research/handoffs/ea_bundle_20261018/` を起点とする**予定パス**。

| パス / パターン | 用途 | 主な注意 |
|---|---|---|
| `ea_shared/sl_sma_trail_zig15_spread_1.2_filter_B_P3_cap2.csv` | **436件ベースライン**、R・時刻・初期SL等 | まず取引数と合計Rを照合 |
| `EURUSD_SL_wave_vs_SMA_matched_436.csv` | 436件のSL方式ペア比較 | ポジション占有を反映した再テストではない |
| `ea_shared/sl_wave_*.csv`, `ea_shared/sl_hybrid_*.csv` | 波SL、ハイブリッドSLの取引履歴 | 別々の実行結果 |
| `EURUSD_fullperiod_pullback_SL_features_436.csv` | 全期間の押し目・SL特徴量 | 時間窓の定義を確認 |
| `EURUSD_2003_2026_pullback_duration_ratio_H4_436.csv` | 形成時間・反発率・H4ダウ | 極値からの経過時間と形成時間は別 |
| `EURUSD_2003_2026_pullback_deepdive_436.csv` | 急落/急騰実体・再テスト回数 | 後付け分類・定義検証必要 |
| `EURUSD_H4_opposed_break_split_44.csv` | H4逆行44件の突破有無 | H4スイングは確定時刻を厳守 |
| `EURUSD_H4_break_pullback_all436.csv` | 436件のH4突破・押し目分類 | 2pips暫定判定、厳密W1ではない |
| `EURUSD_entry_hour_JST_2003_2026.csv` | JST 1時間別成績 | UTC仮定未検証 |
| `EURUSD_entry_daypart_JST_2003_2026.csv` | JST 時間帯別成績 | 同上 |
| `EURUSD_entry_year_daypart_JST_2003_2026.csv` | 年別・時間帯別件数 | 同上 |
| `EURUSD_initial_SL_structure_diagnostics.csv` | 初期SL構造 | 診断データ |
| `EURUSD_SL_alternative_structure_feature_comparison.csv` | H1/H4/D1環境とSLの関係 | H4/D1は近似ラベルの可能性 |
| `EURUSD_SL3_profitable_survival_longterm_comparison.csv` | SL別利益生存 | 条件差を確認 |
| `ea_shared/trail_variant_engine.py` | トレーリング比較のPythonコード | **完全な独立エンジンではない**。依存ファイルを確認 |
| `ea_shared/trail_*.csv` | ZigZag、建値移動などの比較 | ファイル名に実験条件 |
| `ea_shared/spread_*.csv`, `EURUSD_spread*.csv` | スプレッド条件・MFE・トレーリング | 1.0/1.2pip等を混ぜない |
| `ea_shared/filter_*.csv` | A/Bフィルター比較 | P3/capを揃えて比較 |
| `ea_shared/EURUSD_P*.csv`, `EURUSD_P*.csv` | P1/P2/P3/P4、トレンド段階、波の成熟度 | 異なる母集団あり |
| `ea_shared/*wave_features.csv` | 波・段階の特徴量 | 後付け特徴量の可能性 |
| `d1_study_20261015/` | D1/H4のダウ・確定ピボット・イベント検証（11件） | スイング確定の未来参照に注意 |
| `ea_research/` | H4構造バー・確定ピボット・年間要約（4件） | スイング定義を確認 |
| `EURUSD_M5_*.csv`, `ea_shared/M5_*.csv` | M5による補助分析 | M15歴史データと価格基準の不一致疑い |
| `JP225_M15_MT5.csv`, `UK100_M15_MT5.csv`, `US500_M15_MT5.csv` | 指数M15元データ | EURUSDの436件分析とは別 |

## 3. Claudeが最初に読む順序
1. この索引と `CLAUDE_EA_RESEARCH_20261018.md`
2. `ea_bundle_20261018/MANIFEST.json`（取り込み後、100件を完全列挙）
3. `ea_bundle_20261018/ea_shared/sl_sma_trail_zig15_spread_1.2_filter_B_P3_cap2.csv`
4. `ea_bundle_20261018/EURUSD_2003_2026_pullback_deepdive_436.csv`
5. `ea_bundle_20261018/EURUSD_H4_opposed_break_split_44.csv`
6. `ea_bundle_20261018/EURUSD_H4_break_pullback_all436.csv`
7. `ea_bundle_20261018/ea_shared/trail_variant_engine.py` と既存GitHubのEA共通エンジンを照合

## 4. 未検証・再現性の問題
- 過去の数値は会話中の集計報告を含む。**全結果を再実行して再現できたとは主張しない**。
- H4「逆行」「混在」は確定スイング2点による暫定分類で、裁量ダウ転換ロジックと同一とは限らない。
- H4構造突破後の「押し目」は簡易的な逆行・反発検出で、W1そのものではない。
- 2003–2026の全期間をデフォルトにし、2015年以降は追加比較とする。
- 取引除外は元の436件からRを引くだけではなく、最大2ポジション等を含め**全エンジンを再実行**する。
- ベースラインのR、PF、DD、勝率はCSVと実行コードで独立に照合する。
- M1生データ・キャッシュ・共通エンジンの一部は100ファイルのZIP外にある。ZIPだけで完全再現可能とは断言しない。

## 5. ZIP取り込み
```powershell
python research/handoffs/import_claude_bundle_20261018.py "$env:USERPROFILE\Downloads\EA_Claude_handoff_research_20261018.zip"
git add research/handoffs/
git commit -m "data: import 2026-10-18 EA research bundle and manifest"
git push origin main
```
`MANIFEST.json` の `file_count=100` と各SHA-256を確認すること。元ZIPは改変せず、分類は索引と表で行い、元ファイル名を維持する。
