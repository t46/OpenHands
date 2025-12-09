# ML-Bench Instruction 修正提案

## 問題の特定

**現在のinstruction（run_infer.py:515-529）:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a script named `run.sh` under the specified path in the repo to run the task.\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
    + 'You should terminate the subprocess after running the task (e.g., call subprocess.Popen(args).wait()).'  # ← 問題の行
)
```

### 問題点

**528行目の指示が混乱を引き起こしている:**
```python
'You should terminate the subprocess after running the task (e.g., call subprocess.Popen(args).wait()).'
```

**影響:**
- `subprocess.Popen()` = **Pythonコード**の例
- `run.sh` = **Bashスクリプト**であるべき
- エージェントが混乱 → Pythonコードを.shファイルに記述

### 実際の失敗例

**Instance 164（Exit code 2）:**
```bash
/workspace/esm/examples/inverse_folding/run.sh: line 5: import: command not found
/workspace/esm/examples/inverse_folding/run.sh: line 6: import: command not found
/workspace/esm/examples/inverse_folding/run.sh: line 10: script_dir = os.path.dirname(os.path.abspath(__file__))
```
→ エージェントがPythonコードを.shファイルに記述

**影響範囲:**
- Exit 2（Bash構文エラー）: 5件（直接的影響）
- Exit 127（run.sh未作成）: 5件（間接的影響の可能性）
- **合計**: 最大10件（27.8%の失敗）

---

## 修正案

### オプション1: subprocess指示を削除（推奨）

**修正後:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a script named `run.sh` under the specified path in the repo to run the task.\n\n'
    '**Important**: `run.sh` must be a valid Bash script, not a Python script.\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
)
```

**変更点:**
1. ✅ subprocess.Popen()の指示を削除
2. ✅ 「run.shはBashスクリプトである」ことを明確化
3. ✅ Pythonコードの例を含まない

**メリット:**
- 混乱を完全に排除
- シンプルで明確
- Pythonコードの例を含まない

---

### オプション2: Bashの例に置き換え

**修正後:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a Bash script named `run.sh` under the specified path in the repo to run the task.\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
    + 'Example `run.sh` structure:\n'
    + '```bash\n'
    + '#!/bin/bash\n'
    + '# Your task commands here\n'
    + 'python your_script.py --arg1 value1 --arg2 value2\n'
    + '```\n\n'
)
```

**変更点:**
1. ✅ subprocess.Popen()の指示を削除
2. ✅ 「Bashスクリプト」であることを明確化
3. ✅ Bashスクリプトの例を提供

**メリット:**
- 明確なBashの例を提供
- エージェントに正しい形式を示す

---

### オプション3: より詳細な指示（最も安全）

**修正後:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a Bash script named `run.sh` under the specified path in the repo to run the task.\n\n'
    '**Critical Requirements for `run.sh`:**\n'
    '1. It must be a valid Bash script (not Python)\n'
    '2. It should start with `#!/bin/bash`\n'
    '3. Use `python script.py` to call Python code if needed\n'
    '4. The script should run the task and complete within the timeout\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
    + 'Example `run.sh`:\n'
    + '```bash\n'
    + '#!/bin/bash\n'
    + 'python train.py --epochs 10 --lr 0.001\n'
    + '```\n\n'
)
```

**変更点:**
1. ✅ subprocess.Popen()の指示を削除
2. ✅ 重要な要件をリスト化
3. ✅ Bashスクリプトの例を提供
4. ✅ PythonとBashの関係を明確化

**メリット:**
- 最も詳細で明確
- エージェントの誤解を最小化
- 正しい形式を複数の方法で示す

---

## 推奨事項

### 第1段階: オプション1を実装（最優先）

**理由:**
- 最もシンプルで効果的
- 混乱の原因を完全に排除
- 実装が簡単

**期待される改善:**
- Exit 2（Bash構文エラー）: 5件 → 0件
- Exit 127（run.sh未作成）: 部分的改善
- **合計改善予測**: 5-10タスク（+7.4%〜14.7%の成功率向上）

### 第2段階: 評価と改善

1. オプション1で評価を実行
2. 結果を分析
3. 必要に応じてオプション2または3に移行

---

## 実装方法

### ファイル: evaluation/benchmarks/ml_bench/run_infer.py

**現在（515-529行）:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a script named `run.sh` under the specified path in the repo to run the task.\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
    + 'You should terminate the subprocess after running the task (e.g., call subprocess.Popen(args).wait()).'
)
```

**修正後（オプション1）:**
```python
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    'You should create a script named `run.sh` under the specified path in the repo to run the task.\n\n'
    '**Important**: `run.sh` must be a valid Bash script, not a Python script.\n\n'
    f'You can find the task repo at: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
)
```

---

## まとめ

### 問題の本質

**環境ではなく、instructionが失敗の主要因でした。**

- subprocess.Popen()というPythonコードの例が混乱を引き起こしている
- エージェントがPythonコードを.shファイルに記述
- 最大10タスク（27.8%の失敗）に影響

### 解決策

**問題の指示を削除し、Bashスクリプトであることを明確化**

- 実装が簡単
- 即座に効果が期待できる
- 5-10タスクの改善予測（+7.4%〜14.7%）

### 次のステップ

1. オプション1を実装
2. 評価を再実行
3. 結果を分析
4. 成功率が60%以上に達することを確認

---

**作成日**: 2025年12月4日
**作成者**: Claude Sonnet 4.5
**優先度**: 🔴 **Critical**（即座の対応を推奨）
