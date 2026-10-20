# ローソク足キャッシュ生成・保存方針（2026-10-20）

## 入力ファイル（今回のChatGPT作業環境で実在確認）
| 銘柄 | 元データ | 期間・品質 |
|---|---|---|
| EURUSD | `EURUSD2003.M1.zip`、`EURUSD_M5_MT5.csv` | ForexTester M1は2003年開始。MT5 M5は2015年開始 |
| USDJPY | `USDJPY2003.M1.zip`、`USDJPY_M5_MT5.csv` | 同上 |
| JP225 | `JP225_M15_MT5.csv` | MT5 M15、2015年開始 |
| UK100 | `UK100_M15_MT5.csv` | MT5 M15、2015年開始 |
| US500 | `US500_M15_MT5.csv` | MT5 M15、2015年開始 |

これ以外のEURJPY、AUDJPY、XAUUSD、GBPUSD、AUDUSD、GBPJPYなどは、**この作業環境で元OHLCファイル未確認**。データを捏造しない。

## 生成スクリプト
`research/data/build_candle_cache.py`

```bash
pip install pandas pyarrow
python research/data/build_candle_cache.py --input-dir /path/to/source-files --output-dir research/data/cache --format parquet
```

出力は銘柄/元データ系列/時間足で分離:
```text
research/data/cache/
  EURUSD/m1/{M1,M5,M15,H1,H4,D1}/EURUSD_m1_*.parquet
  EURUSD/mt5/{M5,M15,H1,H4,D1}/EURUSD_mt5_*.parquet
  USDJPY/m1/{M1,M5,M15,H1,H4,D1}/USDJPY_m1_*.parquet
  USDJPY/mt5/{M5,M15,H1,H4,D1}/USDJPY_mt5_*.parquet
  JP225/mt5/{M15,H1,H4,D1}/JP225_mt5_*.parquet
  UK100/mt5/{M15,H1,H4,D1}/UK100_mt5_*.parquet
  US500/mt5/{M15,H1,H4,D1}/US500_mt5_*.parquet
  MANIFEST.json
```
計34データセット（EURUSD/USDJPY各11、指数各4）。

## スプレッドの保存・使用
- ForexTester M1 ZIP: OHLC・VOLのみ。**ヒストリカルスプレッドなし**。
- MT5 CSV: `spread` 列あり。確認した先頭行は0。これは「約定コストがゼロ」の証拠ではない。
- MT5のspreadは一般にブローカーの**points**単位であり、pip換算には銘柄ごとのpoint_sizeが必要。
- OHLCへの再集約でspreadを勝手に平均したり、0を有効スプレッドとみなしたりしない。
- `MANIFEST.json` にソース別のspread列有無、0/非0件数、元データSHA256、出力SHA256、行数、開始/終了、タイムゾーン扱いを記録。
- バックテストの**仮定スプレッド**はデータ列とは分離。例: EURUSDの研究では1.0pip、1.2pip等を比較したが、USDJPY・指数に同じ値を流用しない。
- 元データのタイムゾーンが明示されない場合は `SOURCE_UNSPECIFIED_NO_CONVERSION`。勝手にUTC/JSTへ変換しない。H4/D1の区切りは元タイムゾーンに依存。

## 生成上の注意
- OHLC: open=最初、high=最大、low=最小、close=最後、volume=合計。
- カレンダー境界に揃え、欠損時間帯に架空の足は生成しない。
- 最終未確定足は出力に含むため、バックテストではエントリー判定時に**確定足のみ**使う。
- 元のM1系列とMT5系列は時刻・配信元が異なるので結合しない。
- 大量M1の読込にはメモリが必要。必要なら年単位のチャンク集約に改善する。

## GitHubアップロードの状態
**2026-10-20時点でこのGitHubへ保存したのは生成スクリプトと説明書のみ。実データ・生成キャッシュのGitHubアップロードは未実施。**
この環境のGitHubコネクタはGitHubへのテキストファイル書き込みができる一方、約200MBのZIPや数十MBのParquetをローカルから直接転送する機能がないため。ファイル本体のアップロードが完了したかのような記述は禁止。

大容量のキャッシュをアップロードする場合:
```bash
git lfs install
git lfs track "research/data/cache/**/*.parquet"
git add .gitattributes research/data/cache
git commit -m "data: add multi-timeframe OHLC caches with provenance"
git push origin main
```
※Git LFSの容量・帯域枠とデータライセンスを事前確認すること。生データZIPをGitに追加する場合もLFSを使う。

## 検証に必要な次のステップ
1. 元CSV/ZIPをClaude Code実行マシンへ配置。
2. スクリプトで全時間足生成、`MANIFEST.json` の行数・SHA256・期間を検証。
3. EURUSD M15の過去キャッシュ583,458本との一致を確認（M1再集約のルール差に注意）。
4. 実測spreadの有無を確認し、バックテスト用spread仮定を独立の設定ファイルへ記録。
5. Git LFS経由でデータをコミットしてpush。
