# EAバックテスト条件・実行エンジン対応表（2026-10-18）

## 重要：実行可能なコードと結果CSVを分ける
**今回GitHubへ保存したのは検証条件・エンジン対応表。エンジン本体のGitHubへのアップロードは未完了。**
エンジンの原本は会話添付 `EA_Claude_handoff_research_20261018.zip` 内の `ea_shared/trail_variant_engine.py`（実在を確認済み）。ZIPの取り込み後は `research/handoffs/ea_bundle_20261018/ea_shared/trail_variant_engine.py` になる。GitHubにあると断言しない。

## 1. 実エンジン `trail_variant_engine.py` の読解結果
実ファイル先頭〜注文ロジックを確認して抽出した条件（**会話上の仕様書より実コード優先**）：

| 項目 | 実コードの内容 |
|---|---|
| コマンド引数 | `python trail_variant_engine.py <maxpoint> <cap> <filt> <spread_pips> [trail_mode]` |
| 入力価格 | `/mnt/data/EURUSD2003_M15_research.pkl`、time/open/high/low/close |
| 依存特徴量 | `/mnt/data/ea_shared/causal_wave_features_m15.pkl`（H4_ratio_1, H4_ratio_-1, H1_ratio_1, H1_ratio_-1, H1_distance） |
| M15 ATR | 14本のTrue Range単純平均 |
| M15 SMA | 200本 |
| M15 Stoch | %K=14本HH/LLによるrawを3本平均、%D=%Kを5本平均 |
| H1 | M15からOHLC再集約、H1確定後の `avail_time` を `merge_asof` |
| H1 SMA | 20/75/200/480 |
| H1 slope | SMA200, SMA480を**12本前**と比率比較（旧仕様の24時間と不一致の可能性） |
| レジーム方向 | H1 SMA20とSMA75の大小 |
| Stoch完成 | Kが20以下からD上抜け、20超えをBUY完成。SELLは80側の鏡像 |
| ポイント番号 | レジームごと、方向ごとの完成回数 `point` |
| P制限 | `point > maxpoint` を除外 |
| H1方向 | H1 SMA200/480の順序とSMA200傾き |
| q75 | strength履歴100件以上で75%分位を超えたら拒否 |
| MA ABCD相当 | P、SMA20、SMA200、SMA480の複合位置で拒否 |
| filter OFF | 追加波フィルターなし |
| filter A | H4 ratio >=0.7、H1 ratio <0.75 |
| filter B | A条件に加えて H1_distance <12 |
| 同時保有 | `len(positions) >= cap` で新規拒否 |
| スプレッド | 固定 `spread_pips * 0.0001` |
| entry | BUY=当該M15 close+spread、SELL=close |
| 初期SL | M15 SMA200 ±10pips、最低10pips。SELLにspread補正 |
| ZigZagピボット | M15 ATR14 ×1.5 の価格反転で因果確定 |
| trail_mode | `zig1`=+1R、`zig15`=+1.5R、その他は+2R。さらに**240時間経過でトレール開始** |
| 建値移動 | `be1`=+1R、`be15`=+1.5Rで建値移動 |
| SL処理順序 | 足の高安で既存SL決済→既存ポジションのトレール→ピボット更新→新規エントリー |
| データ期間 | ファイル名では2003–2026。実際の開始・終了と件数は入力pklを読み確認すること |

### 仕様上の重大な差分候補
- 旧EA仕様のSMA480 slope **24時間**に対して、この研究エンジンは `shift(12)`、つまりH1 12本。
- 旧EA仕様の `Stoch 14,3,3` と研究エンジンの `raw rolling(3) / D rolling(5)` は必ずしも同じ。
- 研究エンジンは `+2R` のほか **240hでトレール強制開始**。旧仕様との差分を明記する。
- q75閾値は全過去の `strength` 履歴を使用。将来データは直接参照しないが、母集団や初期100件の扱いに注意。
- 現行ライブEAに上記エンジンをそのまま適用してよいとは限らない。

## 2. 結果CSVとエンジンの対応（ファイル名から読み取れる範囲）
すべて `ea_bundle_20261018/ea_shared/` 配下（ZIP取込後）。

| 結果ファイル | 主要条件（名称・コードから判明する範囲） | 検証目的 |
|---|---|---|
| `sl_sma_trail_zig15_spread_1.2_filter_B_P3_cap2.csv` | EURUSD / SMA SL / ZigZag +1.5R / spread 1.2pip / filter B / 最大P3 / cap2 | 436件ベースライン |
| `sl_wave_trail_zig15_spread_1.2_filter_B_P3_cap2.csv` | 上記のSLを波SLへ変更 | SL比較 |
| `sl_hybrid_trail_zig15_spread_1.2_filter_B_P3_cap2.csv` | 上記のSLをハイブリッドへ変更 | SL比較 |
| `trail_zig15_spread_1.2_filter_B_P3_cap2.csv` | ZigZag +1.5R / spread 1.2 / B / P3 / cap2 | トレール比較 |
| `trail_be15_spread_1.2_filter_B_P3_cap2.csv` | 建値 +1.5R / spread 1.2 / B / P3 / cap2 | 建値移動比較 |
| `spread_1_filter_B_P3_cap2.csv` | spread 1pip / B / P3 / cap2 | スプレッド感度 |
| `spread_1.2_filter_A_P3_cap2.csv` | spread 1.2pip / A / P3 / cap2 | A/Bフィルター比較 |
| `filter_A_P3_cap2.csv`, `filter_B_P3_cap2.csv` | P3 / cap2 / filter A vs B | フィルター比較 |
| `EURUSD_P1_P2_P3_all_trades.csv` | P1/P2/P3全取引 | ポイント別比較 |
| `EURUSD_P4_cap2_all_trades.csv`, `EURUSD_P4_cap4_all_trades.csv` | P4まで / cap2 vs cap4 | エントリー許可範囲と占有影響 |
| `EURUSD_P3_cap4_all_trades.csv` | P3まで / cap4 | 同時保有数感度 |

**注意**：名前が同じ条件でも、異なる時点のスクリプトで生成された可能性がある。全CSVがこの一つの `trail_variant_engine.py` から生成されたとは未確認。実行ログ・コードバージョン・CSV列を照合してから対応確定する。

## 3. エンジン実行の例（依存データ配置後）
```bash
python research/handoffs/ea_bundle_20261018/ea_shared/trail_variant_engine.py 3 2 B 1.2 zig15
```
**このコードは現在 `/mnt/data` の絶対パスに依存する。** Claude Codeではまず入出力パスをCLI引数または環境変数に置換し、取引ロジックを変えずに移植する。入力 `EURUSD2003_M15_research.pkl` と `causal_wave_features_m15.pkl` は100ファイルZIPに含まれていない可能性が高く、存在確認必須。

## 4. 検証結果を再現するための標準記録
各比較ごとに次を必ず残す：
- 研究ID、目的、エンジンパスとgit SHA、実行コマンド、実行日時
- 入力データのパス、開始/終了、行数、タイムゾーン、SHA256
- 全パラメータ：時間足、P上限、filter A/B/OFF、cap、spread、SL、トレール開始R、240h条件、q75、MA、H4/D1判定
- 約定処理、同一足のSL/トレール優先順序、手数料/スリッページ、未来参照防止
- 取引数、勝率、合計R、平均R、PF、最大DD、年別、2003–2014/2015–2026
- 取引履歴CSV、集計CSV、比較CSV、実行ログ、SHA256
- 探索的事後分類か、実際にEAを再実行した比較か

## 5. Claudeの最初の作業
1. ZIPの100件を取り込み、`MANIFEST.json` で完全性を確認。
2. GitHub既存の共通エンジンとこの `trail_variant_engine.py` をdiff。
3. 欠けている2つのpklを特定・生成する手順を復元。生M1を使う場合は元データのタイムゾーンを検証。
4. 436件のベースライン再現。取引ごとにエントリー時刻、方向、SL、ExitTime、Rを比較。
5. 再現後にだけ、H4構造フィルターのON/OFFを本当のバックテストで検証。
