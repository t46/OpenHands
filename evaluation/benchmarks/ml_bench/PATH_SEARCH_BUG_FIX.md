# パス探索バグ修正レポート

**修正日時**: 2025年12月3日
**修正ファイル**: `/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/run_infer.py`

---

## 🐛 発見されたバグ

### 問題の概要
`find_run_script()` 関数で、ファイル存在チェックに文字列の部分一致を使用していたため、**ファイルが存在しないのに「見つかった」と誤判定**していました。

### 影響
- **5タスクが誤判定により失敗**: Instance 164, 230, 129, 260, 172
- これらのタスクでは、エージェントが`run.sh`を作成していないにもかかわらず、評価システムが「ファイルが見つかった」と誤判定
- 実行時に「No such file or directory」エラーが発生

---

## 🔧 実施した修正

### 修正前のコード (run_infer.py:142-147)

```python
action = CmdRunAction(command=f'test -f {direct_path} && echo "found" || echo "not_found"')
obs = runtime.run_action(action)

if 'found' in obs.content:  # ❌ 部分一致で判定
    search_log.append(f'✓ Found run.sh at expected location: {direct_path}')
    return direct_path, '\n'.join(search_log)
```

**問題点**:
- `'found' in obs.content` は文字列の部分一致をチェック
- 出力に「found」という文字列が**どこかに含まれている**だけで真と判定
- エラーメッセージや他の出力に「found」が含まれていても誤判定
- 例: "file not found" というエラーメッセージでも真と判定される

### 修正後のコード

```python
# Use exit code instead of string matching to avoid false positives
action = CmdRunAction(command=f'test -f {direct_path}')
obs = runtime.run_action(action)

exit_code = getattr(obs, 'exit_code', -1)
if exit_code == 0:  # ✅ exit codeで正確に判定
    search_log.append(f'✓ Found run.sh at expected location: {direct_path}')
    return direct_path, '\n'.join(search_log)
```

**改善点**:
- `test -f` コマンドのexit codeを直接チェック
- ファイルが存在する場合: exit code = 0
- ファイルが存在しない場合: exit code = 1
- **誤判定の可能性を完全に排除**

---

## 🎯 期待される効果

### 直接的な効果

| Instance | 状態 | 修正後の期待 |
|----------|------|------------|
| 164 | 誤判定で失敗 | 正しく「ファイルなし」と判定 → エージェントの責任 |
| 230 | 誤判定で失敗 | 正しく「ファイルなし」と判定 → エージェントの責任 |
| 129 | 誤判定で失敗 | 正しく「ファイルなし」と判定 → エージェントの責任 |
| 260 | 誤判定で失敗 | 正しく「ファイルなし」と判定 → エージェントの責任 |
| 172 | 誤判定で失敗 | 正しく「ファイルなし」と判定 → エージェントの責任 |

**注意**: この修正により、これらのタスクが**成功するわけではありません**。正しく「失敗」と判定されるようになります。

### 評価の正確性

**修正前**:
- エージェントが`run.sh`を作成していない
- 評価システムが「ファイルが見つかった」と誤判定
- 実行時に「No such file or directory」エラー
- **環境側の問題と誤認される**

**修正後**:
- エージェントが`run.sh`を作成していない
- 評価システムが「ファイルが見つからない」と正しく判定
- **エージェント側の問題と正しく認識される**

---

## 📊 責任の明確化

### この修正が明確にすること

| タスク | 実際の問題 | 修正前の誤解 | 修正後の正しい認識 |
|-------|----------|------------|----------------|
| 164, 230, 129, 260, 172 | エージェントが`run.sh`を作成しなかった | 環境側の問題？ | エージェント側の問題 |

### 環境vs.エージェントの責任分界点

**環境側の責任**:
- ✅ `run.sh`が存在するか正しく判定する
- ✅ 存在する場合は実行する
- ✅ 存在しない場合は適切なエラーを返す

**エージェント側の責任**:
- ❌ タスクを実装する
- ❌ `run.sh`を正しい場所に作成する
- ❌ コードにバグがないようにする

---

## 🔍 他の環境問題との関係

### 修正済みの環境問題

1. **prefix_codeバグ** ✅
   - GitHub URLの自動修正
   - Instance 264で効果確認

2. **パス探索バグ** ✅ **← 今回修正**
   - exit codeによる正確な判定

### 未修正（修正不要）の項目

3. **BERTタスクの失敗** (49, 33, 41, 45, 37, 53)
   - **環境は正常**: モデル存在、prefix_code成功、run.sh作成成功
   - **失敗原因**: エージェントが書いたコードにバグ (exit code 1)
   - **分類**: エージェント側の問題

---

## 🚀 次のステップ

### 1. 再評価の実行

修正後、同じ設定で再評価を実行:

```bash
cd /mnt/home/t46/OpenHands

python evaluation/benchmarks/ml_bench/run_infer.py \
  --eval-split quarter \
  --agent-cls CodeActAgent \
  --llm-config claude-sonnet-4-5 \
  --max-iterations 100
```

### 2. 期待される結果

**評価の正確性が向上**:
- 誤判定がなくなる
- 環境問題とエージェント問題の区別が明確になる
- 今後の改善方向が正しく見える

**成功率の変化**:
- 数値的にはほぼ変わらない見込み（これらのタスクはエージェント側の問題）
- ただし、**評価の信頼性が大幅に向上**

### 3. ログでの確認ポイント

Instance 164のログで以下を確認:

**修正前**:
```
✓ Found run.sh at expected location: /workspace/esm/run.sh
↓
ls: cannot access '/workspace/esm/run.sh': No such file or directory
```

**修正後**:
```
✗ run.sh not found at expected location: /workspace/esm/run.sh
Searching subdirectories (max depth: 3)...
✗ run.sh not found in /workspace/esm or subdirectories
```

---

## ✅ まとめ

### 修正内容
- **ファイル**: `run_infer.py:142-149`
- **変更**: 文字列マッチング → exit codeチェック
- **目的**: 誤判定の排除

### 効果
- ✅ 評価の正確性向上
- ✅ 環境/エージェント問題の明確な区別
- ✅ 今後の改善方向の明確化

### 重要な理解
この修正は**成功率を上げるものではなく、評価を正確にするもの**です。Instance 164, 230, 129, 260, 172 は、エージェントが`run.sh`を作成していないため、正しく失敗と判定されるべきタスクです。

---

**修正者**: Claude Sonnet 4.5
**検証方法**: ログ詳細分析
**修正の性質**: 環境側のバグ修正（評価システムの改善）
