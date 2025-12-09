# ML-Bench Evaluation Results Visualization

このディレクトリには、ML-Benchの評価結果を可視化したファイルが含まれています。

## 📊 生成されたファイル

### 1. インタラクティブHTMLレポート
**ファイル:** `visualizations/report.html`

美しくデザインされたインタラクティブなHTMLレポートです。以下の情報が含まれています：
- 📈 成功率の統計情報（カード形式）
- 📊 プログレスバーによる成功率の可視化
- 🔢 終了コード分布（ASCIIチャート）
- 📋 各タスクの成功/失敗状況の詳細テーブル
- ℹ️ 評価のメタデータ

**開き方:**
```bash
# ブラウザで開く
open visualizations/report.html

# または
xdg-open visualizations/report.html

# または直接パスを指定
firefox /mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations/report.html
```

### 2. テキストサマリー
**ファイル:** `visualizations/summary.txt`

ターミナルで読みやすいテキスト形式のサマリーです。

```bash
cat visualizations/summary.txt
```

### 3. JSON分析サマリー
**ファイル:** `analysis_summary.json`

プログラムで読み込み可能なJSON形式の詳細な分析データです。

```bash
cat analysis_summary.json | python3 -m json.tool
```

### 4. ⭐ Trajectory 可視化（改善版）
**ファイル:** `visualizations/trajectory_enhanced.html`

全68タスクの実行履歴（conversation history）を構造化して表示します。

**主な機能:**
- 🎨 **構造化された表示**: Tools が折りたたみ可能なカード形式
- 🎯 **視覚的改善**: メッセージタイプごとにアイコンと色分け
- 📊 **タイムラインビュー**: 時系列で実行履歴を表示
- 🔍 **フィルタリング**: 成功/失敗のみ表示、全展開/折りたたみ
- 📝 **JSON 構造化**: 長いJSONを見やすく階層表示

**含まれる情報:**
- 各タスクの詳細な実行履歴（1,114メッセージ）
- 使用された Tools の定義と呼び出し
- 各アクションのタイムスタンプ
- コマンド実行結果
- Agent の思考プロセス（thought）
- Model のレスポンス詳細

**開き方:**
```bash
# ブラウザで開く
open visualizations/trajectory_enhanced.html

# または直接パスを指定
firefox /mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations/trajectory_enhanced.html
```

**従来版との比較:**
- `trajectory_full.html` (5.7MB) - 元の生データ表示
- `trajectory_enhanced.html` (22MB) - 構造化された見やすい表示 ⭐ 推奨

## 📈 評価結果サマリー

### 全体統計
- **総タスク数:** 68
- **成功:** 28 タスク ✓
- **失敗:** 40 タスク ✗
- **成功率:** 41.18%

### 終了コード分布
| 終了コード | 件数 | 割合 | 説明 |
|-----------|------|------|------|
| -1 | 10 | 14.7% | 内部エラーまたは例外 |
| 0 | 22 | 32.4% | 正常終了 |
| 1 | 25 | 36.8% | 一般的なエラー |
| 2 | 5 | 7.4% | シェルコマンドの誤用 |
| 124 | 6 | 8.8% | タイムアウト |

### 主要な洞察
1. 成功率は41.18%（68タスク中28タスク）
2. 最も一般的な失敗モードは終了コード1（全タスクの36.8%）
3. タイムアウト問題（終了コード124）は8.8%のタスクに影響
4. 内部エラー（終了コード-1）は14.7%のケースで発生
5. 22タスク（32.4%）は終了コード0で正常完了

### 推奨事項
1. 終了コード1のタスクを調査し、共通の失敗パターンを特定
2. タイムアウトケースをレビューし、パフォーマンスを最適化またはタイムアウト制限を増加
3. 内部エラー（終了コード-1）を分析し、エラー処理を改善
4. 成功したタスクのパターンを文書化し、再現性を確保

## 🛠️ 可視化スクリプト

### スクリプトファイル
- `visualize_results_simple.py` - 外部依存なしの可視化スクリプト（標準ライブラリのみ）
- `visualize_results.py` - pandas/matplotlib/seaborn を使用する高度な可視化スクリプト（※要インストール）
- `visualize_trajectory_enhanced.py` - Trajectory 可視化スクリプト（構造化表示）⭐

### 再実行方法
```bash
# 結果サマリーの可視化（簡易版 - 推奨）
python3 visualize_results_simple.py

# 結果サマリーの可視化（高度版 - pandas等が必要）
python3 visualize_results.py

# Trajectory の構造化可視化
python3 visualize_trajectory_enhanced.py
```

## 📁 ディレクトリ構造
```
ml_bench/
├── visualizations/
│   ├── report.html                # 結果サマリーHTMLレポート
│   ├── summary.txt                # テキストサマリー
│   └── trajectory_enhanced.html   # Trajectory 可視化（構造化表示）⭐
├── visualize_results_simple.py        # 結果サマリー可視化（簡易版）
├── visualize_results.py               # 結果サマリー可視化（高度版）
├── visualize_trajectory_enhanced.py   # Trajectory 可視化スクリプト⭐
├── analysis_summary.json              # JSON形式の分析データ
├── trajectory_full.html               # 元の Trajectory HTML（参考用）
└── VISUALIZATION_README.md            # このファイル
```

## 💡 使用例

### HTMLレポートをブラウザで開く
```bash
cd /mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench
open visualizations/report.html
```

### サマリーをターミナルで表示
```bash
cat visualizations/summary.txt
```

### JSON データをパース
```python
import json

with open('analysis_summary.json', 'r') as f:
    data = json.load(f)
    print(f"Success Rate: {data['overall_statistics']['success_rate_percent']}%")
```

## 📝 注意事項

- HTMLレポートはスタンドアロンで動作し、外部リソースへの依存はありません
- すべての可視化はレスポンシブデザインで、モバイルデバイスでも表示可能
- 生成されたファイルは静的で、元のJSONLファイルを変更しません

---

**生成日時:** 2025-11-19 15:38:28
**評価モデル:** GPT-5
**最大イテレーション:** 50
**エージェントクラス:** CodeActAgent
