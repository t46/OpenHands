# ML-Bench 環境修正クイックリファレンス

**最終更新**: 2025年12月3日

---

## 📁 ファイル構成

```
evaluation/benchmarks/ml_bench/
├── run_infer.py                    ← 修正済みファイル（メイン）
├── scripts/
│   └── run_infer.sh
├── README.md
│
├── 📚 ドキュメント（新規作成）
│   ├── ENVIRONMENT_FIXES_MASTER.md           ← ★ マスタードキュメント
│   ├── FIXES_QUICK_REFERENCE.md              ← このファイル
│   ├── FINAL_FIXES_REPORT.md                 ← 初回修正レポート
│   ├── IMPLEMENTATION_SUMMARY.md             ← 実装サマリー
│   ├── PATH_SEARCH_BUG_FIX.md               ← パス探索バグ修正
│   └── ULTRATHINK_ENV_FIXED_20251202_分析レポート.md ← 詳細分析
```

---

## 🔧 修正済みコード（run_infer.py）

### 関数一覧

| 関数名 | 行番号 | 目的 | 状態 |
|-------|--------|------|------|
| `fix_prefix_code_bugs()` | 79-120 | prefix_codeのバグ自動修正 | ✅ 動作中 |
| `find_run_script()` | 123-169 | run.shの柔軟な探索 | ✅ 修正完了 |
| `setup_bert_models()` | 172-233 | BERTモデル自動準備 | ✅ 動作中 |
| `setup_glue_data()` | 236-278 | GLUEデータ自動準備 | ✅ 動作中 |
| `initialize_runtime()` | 297-386 | ランタイム初期化（修正統合） | ✅ 動作中 |
| `complete_runtime()` | 389-482 | ランタイム完了処理（修正統合） | ✅ 動作中 |

---

## 🚀 使用方法

### 1. 評価の実行

```bash
cd /mnt/home/t46/OpenHands

# 全68タスクで評価
python evaluation/benchmarks/ml_bench/run_infer.py \
  --eval-split quarter \
  --agent-cls CodeActAgent \
  --llm-config claude-sonnet-4-5 \
  --max-iterations 100
```

### 2. ログの確認

```bash
# 最新の評価結果を確認
ls -lt evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/

# 特定のインスタンスのログを確認
tail -100 evaluation/evaluation_outputs/outputs/.../infer_logs/instance_164.log

# 修正の動作を確認
grep -i "prefix.*fix\|path search\|bert.*setup" evaluation/evaluation_outputs/outputs/.../infer_logs/*.log
```

### 3. 結果の分析

```bash
# 成功率の計算
cat output.jsonl | jq -s '[.[] | select(.test_result) | .test_result.success] | {total: length, success: (map(select(. == 1)) | length), rate: ((map(select(. == 1)) | length) * 100.0 / length)}'

# 失敗したタスクのリスト
cat output.jsonl | jq 'select(.test_result.success == 0) | .instance_id'
```

---

## 📊 期待される結果

### 修正の効果

| 修正内容 | 対象タスク | 期待される効果 |
|---------|----------|--------------|
| prefix_codeバグ修正 | 2 | 1タスク成功済み |
| パス探索バグ修正 | 6 | 評価の正確性向上 |
| BERTモデル準備 | 6 | 環境は正常（エージェント問題） |
| GLUEデータ準備 | 1 | 環境は正常（エージェント問題） |

### 成功率の推移

```
修正前（2025-11-25）: 39/68 = 57.4%
　↓
第1回修正後（2025-12-02）: 40/68 = 58.8% (+1.4%)
　↓
パス探索修正後（2025-12-03）: 再評価待ち（正確性向上）
```

---

## 🐛 既知の問題

### ✅ 解決済み
- [x] prefix_codeのGitHub URL誤り → 自動修正実装
- [x] パス探索の誤判定 → exit code判定に変更

### ⚠️ 調査中
- [ ] Instance 17の回帰（成功→失敗）
- [ ] Instance 272の後続エラー（prefix_code成功後）

### ℹ️ エージェント側の問題（修正対象外）
- BERTタスク6件の実装エラー（環境は正常）
- run.sh未作成タスク5件

---

## 📞 トラブルシューティング

### Q: 評価が失敗する
**A**: ログを確認してください
```bash
tail -100 evaluation/evaluation_outputs/outputs/.../infer_logs/instance_XXX.log
```

### Q: prefix_code修正が動作しているか確認したい
**A**: ログで以下を検索
```bash
grep "Fixed GitHub URL\|prefix_code was automatically fixed" infer_logs/*.log
```

### Q: パス探索が正しく動作しているか確認したい
**A**: ログで以下を検索
```bash
grep "Path search result\|Found run.sh\|run.sh not found" infer_logs/*.log
```

### Q: BERTモデルがダウンロードされたか確認したい
**A**: ログで以下を検索
```bash
grep "BERT model\|Setting up BERT" infer_logs/*.log
```

---

## 📚 詳細ドキュメント

各トピックの詳細は以下のドキュメントを参照:

| トピック | ドキュメント |
|---------|------------|
| **全体像・一元管理** | `ENVIRONMENT_FIXES_MASTER.md` ← ★推奨 |
| 初回修正の詳細 | `FINAL_FIXES_REPORT.md` |
| 実装手順 | `IMPLEMENTATION_SUMMARY.md` |
| 評価結果分析 | `ULTRATHINK_ENV_FIXED_20251202_分析レポート.md` |
| パス探索バグ | `PATH_SEARCH_BUG_FIX.md` |
| クイックリファレンス | `FIXES_QUICK_REFERENCE.md` ← このファイル |

---

## 🎯 チェックリスト

### 評価を実行する前
- [ ] `run_infer.py` が最新版（2025-12-03以降）
- [ ] LLM設定が正しい
- [ ] ディスク容量が十分

### 評価実行中
- [ ] ログを定期的に確認
- [ ] エラーが出ていないか確認
- [ ] 進捗状況を確認

### 評価完了後
- [ ] output.jsonlが生成されている
- [ ] 成功率を計算
- [ ] ログで修正の動作を確認
- [ ] 結果を `ENVIRONMENT_FIXES_MASTER.md` に反映

---

**クイックリンク**:
- 📂 メインファイル: `run_infer.py`
- 📖 マスタードキュメント: `ENVIRONMENT_FIXES_MASTER.md`
- 📊 最新評価結果: `evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/`
