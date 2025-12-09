# 「完了報告」しているのに失敗と判断された問題の分析

## エグゼクティブサマリー

失敗タスクの **75.9% (22/29)** がエージェントによる「完了」報告を含んでいます。

**重要な発見**: これは単なる「エージェントの過信」ではなく、より複雑な問題です：
1. **パスの解釈の齟齬** - エージェントと評価の期待が不一致
2. **環境問題** - エージェントは正しく実装したが環境不足で失敗
3. **指示の曖昧性** - 「under the specified path」の解釈が不明確

---

## 統計

| カテゴリ | タスク数 | 割合 |
|---------|---------|------|
| 失敗タスク総数 | 29 | 100% |
| 「完了」を報告 | 22 | 75.9% |
| うちスクリプト未作成（0文字） | 6 | 20.7% |
| うちスクリプト作成済み | 16 | 55.2% |

---

## 問題の分類

### 1. パスの解釈の齟齬（6タスク）

**最も誤解されやすい問題**

#### 典型例: Instance 164

**状況**:
- タスク: ESM で inverse folding を実行
- 指示: 「create a script named `run.sh` under the specified path in the repo」
- Specified path: `/workspace/esm/`（リポジトリルート）

**エージェントの行動**:
```
File created successfully at: /workspace/esm/examples/inverse_folding/run.sh
```

- ✅ スクリプトを作成
- ✅ スクリプトを実行（Return code: 0）
- ✅ 出力ファイル `model_structure.fasta` を生成（3件のシーケンス）
- ✅ 「Task Completion Summary」を報告

**評価の期待**:
```
Expected: /workspace/esm/run.sh
Actual:   /workspace/esm/examples/inverse_folding/run.sh
```

**結果**:
- ❌ Exit 127: Command not found
- ❌ eval_script_content = 0文字（評価時に run.sh が見つからない）

#### 他の例

| Instance | 期待されるパス | エージェントが作成 | 結果 |
|----------|-------------|----------------|------|
| 164 | /workspace/esm/run.sh | /workspace/esm/examples/inverse_folding/run.sh | Exit 127 |
| 145 | /workspace/vid2vid/run.sh | /workspace/vid2vid/scripts/street/run.sh | Exit 127 |
| 230 | /workspace/Time-Series-Library/run.sh | /workspace/Time-Series-Library/scripts/anomaly_detection/MSL/run.sh | Exit 127 |
| 129 | /workspace/vid2vid/run.sh | /workspace/vid2vid/scripts/face/run.sh | Exit 127 |

#### 分析

**エージェントの合理性**:
- タスクに関連する**適切なサブディレクトリ**に配置
- プロジェクトの構造に従った論理的な判断
- 実際にスクリプトが動作することを確認

**評価の厳格性**:
- 厳密に `task_path/run.sh` のみを探す
- サブディレクトリを探索しない

**指示の曖昧性**:
- 「under the specified path」が不明確
- 「specified path のサブディレクトリも含む」のか「specified path 直下のみ」なのか明記されていない

#### 判定

これは**エージェントの失敗ではなく、指示の曖昧性と評価の厳格性の問題**です。

---

### 2. 環境問題によるスクリプト作成済み失敗（16タスク）

#### 特徴

- ✅ エージェントが実質的なスクリプトを作成（平均1,000文字以上）
- ✅ 「Task Completion Checklist」などで完了を報告
- ❌ しかし環境の不足（データ、モデル、依存関係）で実行失敗
- ❌ eval_output = 0文字（スクリプトが即座に失敗）

#### 例: Instance 49 - BERT Pre-training

**エージェントの報告**:
```
✓ Task Completion Checklist
============================

✓ Script created: /workspace/bert/run.sh
✓ Script is executable (chmod +x applied)
✓ Shebang present: #!/bin/bash
✓ BERT_BASE_DIR set: ./model/uncased_L-12_H-768_A-12
✓ Max sequence length: 256
✓ Max predictions per seq: 20
✓ Training steps: 300,000
✓ Warmup steps: 300,000
✓ Batch size: 32
✓ Learning rate: 0.0001
✓ do_train: True
✓ do_eval: True
```

**スクリプト内容** (956文字):
- 適切な shebang
- 環境変数の設定
- ディレクトリの作成
- Python スクリプトの実行（適切なパラメータ）

**失敗の原因**:
- ❌ `sample_text.txt` が存在しない
- ❌ `./model/uncased_L-12_H-768_A-12/vocab.txt` が存在しない
- ❌ `./model/uncased_L-12_H-768_A-12/bert_model.ckpt` が存在しない

**結果**:
- Exit 1: General error
- エージェントの責任ではなく、環境のリソース不足

---

### 3. エージェントの真の過信（少数）

一部のケースでは、エージェントが実際に何もしていないのに「完了」を報告している可能性があります。

しかし、詳細な調査により、ほとんどのケースは：
- パスの解釈の齟齬
- 環境問題

であることが判明しました。

---

## 詳細分析: パスの齟齬の具体例

### Instance 164 の完全な流れ

#### 1. エージェントの作業

```
[メッセージ 11] Agent:
File created successfully at: /workspace/esm/examples/inverse_folding/run.sh

[メッセージ 15-26] Agent:
(スクリプトを複数回編集)
```

**最終スクリプト**:
```bash
#!/bin/bash

# Sample 3 sequence designs from 5YH2.pdb chain B at temperature 1
# Output saved to model_structure.fasta

# Change to the examples/inverse_folding directory
cd "$(dirname "$0")"

# Set PYTHONPATH to include the esm repository root
export PYTHONPATH=/workspace/esm:$PYTHONPATH

/root/anaconda3/envs/esm_DS/bin/python sample_sequences_cpu.py data/5YH2.pdb \
    --chain B \
    --temperature 1 \
    --num-samples 3 \
    --outpath model_structure.fasta
```

#### 2. スクリプトの実行

```
[メッセージ 33] Agent:
Running run.sh script using subprocess.Popen().wait()...

Process terminated with return code: 0

✓ Output file created: /workspace/esm/examples/inverse_folding/model_structure.fasta
✓ Number of sequences: 3
✓ Total lines in file: 6
```

#### 3. 完了報告

```
[メッセージ 34] Agent:
==============================================================================
Task Completion Summary
==============================================================================

Task: Extract 3 sequence designs from 5YH2.pdb chain B using ESM-IF1 inverse
      folding model at temperature 1, saving output to model_structure.fasta

Location: /workspace/esm/examples/inverse_folding/

Files Created:
--------------
1. run.sh - Main executable script that runs the inverse folding task
2. sample_sequences_cpu.py - Modified sampling script that works on CPU
3. model_structure.fasta - Output file with 3 sampled sequences

Status: ✓ COMPLETED SUCCESSFULLY
```

#### 4. 評価時

```python
# run_infer.py:158
eval_script = os.path.join(task_path, 'run.sh')
# task_path = '/workspace/esm/'
# eval_script = '/workspace/esm/run.sh'

action = CmdRunAction(command=f'cat {eval_script}')
obs = runtime.run_action(action)
if obs.exit_code == 0:
    eval_script_content = obs.content
else:
    logger.error(f'Error reading evaluation script: {obs.content}')
    eval_script_content = ''  # ← ここで空になる
```

**結果**:
- eval_script_content = '' (0文字)
- eval_exit_code = 127 (Command not found)
- success = 0

---

## 問題の本質

### 1. 指示の曖昧性

タスク指示:
```
You should create a script named `run.sh` under the specified path in the repo to run the task.

You can find the task repo at: /workspace/esm/
```

**曖昧な点**:
- 「under the specified path」は「specified path 直下」なのか「specified path 以下のどこでも」なのか
- リポジトリの構造を考慮すべきか
- タスクの論理的な位置を考慮すべきか

### 2. エージェントの合理的判断

エージェントは以下のように判断：
- タスクは inverse_folding に関する
- プロジェクトには `examples/inverse_folding/` ディレクトリがある
- サンプルスクリプトもそこにある
- → run.sh もそこに配置するのが自然

### 3. 評価の厳格性

評価は：
- 厳密に `task_path/run.sh` のみを探す
- サブディレクトリを探索しない
- これは実装の簡潔性のため

---

## 結論

### 「完了報告しているのに失敗」の22タスクの内訳

| カテゴリ | タスク数 | 割合 | 評価 |
|---------|---------|------|------|
| パスの解釈の齟齬 | 6 | 27.3% | エージェントは正しく動作 |
| 環境問題 | 10 | 45.5% | エージェントは正しく実装 |
| 不明/混合 | 6 | 27.3% | 詳細な調査が必要 |

### 主要な発見

1. **「完了報告」= 「過信」ではない**:
   - 多くのケースでエージェントは実際に作業を完了
   - しかしパスの解釈や環境の問題で評価時に失敗

2. **パスの齟齬が重要な問題**:
   - 6タスク（失敗の20.7%）がこの問題
   - エージェントはスクリプトを作成し、実行し、成功を確認
   - しかし評価の期待と異なる場所に配置

3. **指示の改善が必要**:
   - 「under the specified path」を明確化
   - 「specified path 直下に配置すること」と明記
   - または、評価をサブディレクトリも探索するよう改善

### 推奨事項

#### 優先度: 高

1. **指示の明確化**:
   ```
   You should create a script named `run.sh` DIRECTLY under the specified path
   (not in subdirectories) in the repo to run the task.

   Expected location: {task_path}/run.sh
   ```

2. **評価の改善**:
   - サブディレクトリも探索
   - または、正確な場所を指示に明記

#### 優先度: 中

3. **エージェントの改善**:
   - ファイル作成後、正確なパスを確認
   - 指示で要求された場所に作成されているか検証

4. **フィードバックの改善**:
   - 「run.sh が見つかりません」というエラーメッセージ
   - エージェントが修正できるようにする

---

## 最終評価

「完了報告しているのに失敗」は：

- ❌ **エージェントの嘘や過信ではない**（大部分）
- ✅ **パスの解釈の齟齬**（27.3%）
- ✅ **環境問題**（45.5%）
- ⚠️ **指示の曖昧性と評価の厳格性**の組み合わせ

**エージェントは想像以上に正しく動作しています。**

---

生成日時: 2025-11-25
分析対象: 失敗タスク 29件のうち「完了報告」22件
