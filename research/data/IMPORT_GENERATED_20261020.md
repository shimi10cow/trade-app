# 2026-10-20生成済みローソク足データ：GitHubへの取り込み

**現在の状態：生成済みの実データ34点はChatGPT添付ZIPとして存在するが、GitHub mainへはまだアップロードされていない。** 本ページは取り込み作業の入口。完了を偽らないこと。

## 入力（ダウンロードする5ファイル）
- `EA_cache_EURUSD_20261020.zip` 約53MB：EURUSD 2003年5月以降M1＋M5/M15/H1/H4/D1、MT5由来M5/M15/H1/H4/D1
- `EA_cache_USDJPY_20261020.zip` 約52MB：USDJPY 同上
- `EA_cache_JP225_20261020.zip` 約4MB：2015年以降M15/H1/H4/D1
- `EA_cache_UK100_20261020.zip` 約5MB：同上
- `EA_cache_US500_20261020.zip` 約5MB：同上

## 保存先
`research/data/cache/<SYMBOL>/<m1|mt5>/`。ファイル名は `<SYMBOL>_<source>_<timeframe>.csv.gz`、元M1 ZIPも `m1/` 内に保持。

## データ品質
- EURUSD M15 583,458本で過去の研究値と一致
- EURUSD/USDJPY: 2003-01-01〜2003-05-05は不足
- 指数3銘柄: 2003〜2014年が不足
- MT5スプレッドはbroker points。ゼロは実測0とは断定せず、非ゼロ値のmean/max、最終値、valid_countを保持
- ForexTester M1にヒストリカルスプレッド列はない。バックテスト用仮定値と混同しない
- H4/D1は元タイムゾーンのカレンダー境界で集約。TZ未確定なら時刻変換しない

## Windows/Claude Codeからアップロード
1. 上記5 ZIPをChatGPTからダウンロードし、リポジトリ直下の `incoming_caches/` に置く
2. `python research/data/import_generated_cache_zips.py --zip-dir incoming_caches`
3. `git lfs install`
4. `git lfs track 'research/data/cache/**/*.gz' 'research/data/cache/**/*.zip'`
5. `git add .gitattributes research/data/cache`
6. `git commit -m 'data: import 34 candle datasets (2003-2026 where available)'`
7. `git push origin main`

元ZIPと展開後のキャッシュのSHA256は、添付 `EA_candle_caches_20261020/MANIFEST.json` と照合。ZIP内にあるパスをそのまま利用し、同名の既存ファイルは上書きしない。
