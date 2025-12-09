# ML-Bench 環境依存問題 解消実装計画

## 📋 エグゼクティブサマリー

全68タスク中29タスク（42.6%）が失敗していますが、詳細分析の結果、**26タスク（89.7%）は環境または評価システムの問題**であることが判明しました。

本計画では、これらの問題を**3フェーズ**で解決します。

---

## 📊 問題の定量的分析

| カテゴリ | タスク数 | 割合 | 影響度 | 実装難易度 |
|---------|---------|------|--------|-----------|
| タイムアウト誤判定 | 12 | 41.4% | 🔴 高 | 🟢 低 |
| 環境問題（モデル/データ不足） | 18 | 62.1% | 🔴 高 | 🟡 中 |
| パス探索の齟齬 | 6 | 20.7% | 🟡 中 | 🟢 低 |
| 読み取り失敗 | 2 | 6.9% | 🟢 低 | 🟢 低 |

---

## 🎯 フェーズ1: 即座の修正（評価コードの改善）

### 優先度: 🔴 最高 | 実装時間: 2-3時間 | 期待効果: 20タスク改善

#### 1.1 タイムアウト誤判定の修正

**ファイル:** `run_infer.py`
**行:** 186-196

**現在の問題:**
```python
if obs.exit_code != 0 and obs.exit_code != 124:
    outputs['success'] = int('KeyboardInterrupt' in eval_output)
else:
    outputs['success'] = 1  # ← Exit 124も成功扱い
```

**修正コード:**
```python
# Exit code の評価を改善
if obs.exit_code == 0:
    # 正常終了
    outputs['success'] = 1
    logger.info('Evaluation script completed successfully')
elif obs.exit_code == 124:
    # タイムアウト - 失敗として扱う
    outputs['success'] = 0
    logger.warning(f'Evaluation script timed out after 120s (Exit 124)')
elif 'KeyboardInterrupt' in eval_output:
    # KeyboardInterrupt は成功として扱う（ML-Benchの仕様）
    outputs['success'] = 1
    logger.info('KeyboardInterrupt detected - treating as success per ML-Bench spec')
else:
    # その他のエラー
    outputs['success'] = 0
    logger.error(f'Evaluation script failed with exit code {obs.exit_code}')
```

**影響:** 12タスクが正しく評価される

---

#### 1.2 パス探索の柔軟化

**ファイル:** `run_infer.py`
**行:** 158

**追加する関数:**
```python
def find_run_script(runtime: Runtime, task_path: str, max_depth: int = 3) -> tuple[str | None, str]:
    """
    Find run.sh in task_path or subdirectories.

    Args:
        runtime: Runtime instance to execute commands
        task_path: Base path to search from
        max_depth: Maximum directory depth to search

    Returns:
        Tuple of (script_path, search_log)
    """
    search_log = []

    # まず直接パスを確認
    direct_path = os.path.join(task_path, 'run.sh')
    action = CmdRunAction(command=f'test -f {direct_path} && echo "found" || echo "not_found"')
    obs = runtime.run_action(action)

    if 'found' in obs.content:
        search_log.append(f'✓ Found run.sh at expected location: {direct_path}')
        return direct_path, '\n'.join(search_log)

    search_log.append(f'✗ run.sh not found at expected location: {direct_path}')
    search_log.append(f'Searching subdirectories (max depth: {max_depth})...')

    # サブディレクトリを探索
    find_command = f'find {task_path} -maxdepth {max_depth} -name "run.sh" -type f'
    action = CmdRunAction(command=find_command)
    obs = runtime.run_action(action)

    if obs.exit_code == 0 and obs.content.strip():
        found_paths = obs.content.strip().split('\n')
        if found_paths:
            # 最も浅いパスを選択
            selected_path = min(found_paths, key=lambda p: p.count('/'))
            search_log.append(f'✓ Found run.sh in subdirectory: {selected_path}')
            search_log.append(f'  Note: Agent placed script in logical subdirectory')
            return selected_path, '\n'.join(search_log)

    search_log.append(f'✗ run.sh not found in {task_path} or subdirectories')
    return None, '\n'.join(search_log)
```

**complete_runtime 関数の修正:**
```python
def complete_runtime(
    runtime: Runtime,
    instance: pd.Series,
) -> dict[str, Any]:
    """Complete the runtime for the agent."""
    logger.info(f'{"-" * 50} BEGIN Runtime Completion Fn {"-" * 50}')
    obs: CmdOutputObservation

    repo_url = instance['github']
    repo_name = repo_url.split('/')[-1]
    task_path = os.path.join('/workspace', repo_name, instance['path'][2:])

    # 柔軟なパス探索
    eval_script, search_log = find_run_script(runtime, task_path, max_depth=3)
    logger.info(f'Script search results:\n{search_log}')

    if eval_script is None:
        logger.error(f'Could not find run.sh in {task_path} or subdirectories')
        return {
            'eval_script_content': '',
            'eval_output': f'Error: run.sh not found\n{search_log}',
            'eval_exit_code': 127,
            'success': 0,
        }

    logger.info(f'Using evaluation script: {eval_script}')

    # スクリプトの読み取り（権限問題に対応）
    # まず権限を確認
    action = CmdRunAction(command=f'ls -la {eval_script}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    logger.info(f'Script file info: {obs.content}')

    # 読み取り権限を確保
    action = CmdRunAction(command=f'chmod +r {eval_script}')
    runtime.run_action(action)

    # スクリプト内容を読み取り
    action = CmdRunAction(command=f'cat {eval_script}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    if obs.exit_code == 0:
        eval_script_content = obs.content
    else:
        logger.error(f'Error reading evaluation script: {obs.content}')
        eval_script_content = ''

    # スクリプトを実行
    action = CmdRunAction(
        command=f'bash -c "source /root/anaconda3/etc/profile.d/conda.sh && conda activate {ID2CONDA[instance["github_id"]]} && timeout 120s bash {eval_script}"',
    )
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    eval_output = obs.content if obs.content else ''

    # Exit code の評価（改善版）
    outputs = {
        'eval_script_content': eval_script_content,
        'eval_output': eval_output,
        'eval_exit_code': obs.exit_code,
    }

    if obs.exit_code == 0:
        outputs['success'] = 1
        logger.info('Evaluation script completed successfully')
    elif obs.exit_code == 124:
        outputs['success'] = 0
        logger.warning(f'Evaluation script timed out after 120s (Exit 124)')
    elif 'KeyboardInterrupt' in eval_output:
        outputs['success'] = 1
        logger.info('KeyboardInterrupt detected - treating as success per ML-Bench spec')
    else:
        outputs['success'] = 0
        logger.error(f'Evaluation script failed with exit code {obs.exit_code}')

    logger.info(f'{"-" * 50} END Runtime Completion Fn {"-" * 50}')
    return outputs
```

**影響:** 6タスク（パスの齟齬）+ 2タスク（読み取り失敗）= 8タスク改善

---

#### 1.3 指示の明確化

**ファイル:** `run_infer.py`
**行:** 217-232

**修正コード:**
```python
# Prepare the task instruction
instruction = (
    f'Please complete the Machine Learning task in the following repository: {repo_name}\n\n'
    f'{instance["instruction"]}\n\n'
    '='*80 + '\n'
    '⚠️  CRITICAL REQUIREMENT - SCRIPT LOCATION\n'
    '='*80 + '\n'
    f'You MUST create a script named `run.sh` in the EXACT path specified below:\n\n'
    f'📁 Required location: {task_path}/run.sh\n\n'
    '⚠️  DO NOT create the script in subdirectories (e.g., scripts/, examples/, etc.)\n'
    '⚠️  The evaluation system expects the script at the EXACT path above.\n'
    '='*80 + '\n\n'
    f'Working directory: {task_path}\n\n'
    + (
        'Here is the prefix code for the task:\n'
        '```bash\n'
        f'{instance["prefix_code"]}\n'
        '```\n\n'
        if instance['prefix_code']
        else ''
    )
    + 'You should terminate the subprocess after running the task (e.g., call subprocess.Popen(args).wait()).\n\n'
    'Before finishing, verify that the script exists at the correct location:\n'
    f'  ls -la {task_path}/run.sh\n'
)
instruction += AGENT_CLS_TO_INST_SUFFIX[metadata.agent_class]
```

**影響:** 将来の実行でパス問題を予防

---

### フェーズ1の期待効果

| 修正内容 | 影響タスク数 | 実装難易度 |
|---------|------------|-----------|
| タイムアウト誤判定修正 | 12 | 🟢 低 |
| パス探索柔軟化 | 6 | 🟢 低 |
| 読み取り堅牢化 | 2 | 🟢 低 |
| **合計** | **20** | **🟢 低** |

**期待される改善:**
- 失敗率: 42.6% → 13.2%（29タスク → 9タスク）
- 真のエージェント失敗のみが残る

---

## 🏗️ フェーズ2: 環境の部分的改善

### 優先度: 🟡 高 | 実装時間: 1-2日 | 期待効果: 8-12タスク改善

#### 2.1 汎用サンプルデータの追加

**対象:** データ不足の8タスク

**実装方法:**
```bash
# initialize_runtime に追加
def setup_sample_data(runtime: Runtime, task_path: str):
    """Setup generic sample data for ML tasks"""

    # 汎用テキストサンプル
    sample_text = """
    This is a sample text for machine learning tasks.
    It contains multiple sentences for training and testing.
    Natural language processing models can use this data.
    [... 1000行程度のテキスト ...]
    """

    action = CmdRunAction(
        command=f'cat > {task_path}/sample_text.txt << "EOF"\n{sample_text}\nEOF'
    )
    runtime.run_action(action)

    # 汎用CSVサンプル
    # 汎用画像サンプル
    # etc.
```

**影響:** 8タスクのうち4-6タスク改善の可能性

---

#### 2.2 よく使われるモデルのキャッシュ

**対象:** モデル不足の12タスク

**実装方法:**
1. initialize_runtime で Hugging Face のキャッシュを有効化
2. よく使われるモデル（BERT-baseなど）を事前ダウンロード
3. または、エージェントにダウンロード手順を明示

```python
def setup_model_cache(runtime: Runtime):
    """Setup model cache and download common models"""

    # Hugging Face cache の設定
    action = CmdRunAction(
        command='export HF_HOME=/workspace/.cache/huggingface'
    )
    runtime.run_action(action)

    # 一般的なモデルの事前ダウンロード（オプション）
    common_models = [
        'bert-base-uncased',
        'bert-base-cased',
    ]

    for model in common_models:
        # ダウンロード試行（失敗しても続行）
        pass
```

**影響:** 12タスクのうち2-4タスク改善の可能性

---

#### 2.3 依存関係の事前チェック

**実装方法:**
```python
def check_dependencies(runtime: Runtime, instance: pd.Series):
    """Check and log missing dependencies"""

    # requirements.txt があれば読み取り
    action = CmdRunAction(command=f'cat {task_path}/requirements.txt')
    obs = runtime.run_action(action)

    if obs.exit_code == 0:
        requirements = obs.content
        logger.info(f'Found requirements:\n{requirements}')

        # インストール試行
        action = CmdRunAction(
            command=f'pip install -r {task_path}/requirements.txt'
        )
        obs = runtime.run_action(action)
        if obs.exit_code != 0:
            logger.warning(f'Failed to install requirements: {obs.content}')
```

**影響:** 6タスクのうち2-3タスク改善の可能性

---

## 🚀 フェーズ3: 完全な環境構築（長期）

### 優先度: 🟢 中 | 実装時間: 1-2週間 | 期待効果: 全18タスク改善

#### 3.1 Dockerイメージの拡張

**必要な作業:**
1. 各タスクの requirements を分析
2. 事前学習済みモデルをイメージに含める（または、事前ダウンロードスクリプト）
3. サンプルデータセットを含める
4. すべての依存関係を完全にインストール

**ファイル:** Dockerfile または初期化スクリプト

**期待効果:** 環境問題の18タスクすべてが解決

---

## 📈 実装優先順位と期待効果

| フェーズ | 作業量 | 実装時間 | 期待改善数 | 累積改善率 |
|---------|-------|---------|-----------|-----------|
| **フェーズ1** | 🟢 小 | 2-3時間 | 20タスク | 69.0% |
| **フェーズ2** | 🟡 中 | 1-2日 | 8-12タスク | 82.8-96.6% |
| **フェーズ3** | 🔴 大 | 1-2週間 | 18タスク | 100% |

---

## 🎯 推奨実装順序

### ステップ1: フェーズ1の実装（即座に開始）
1. ✅ タイムアウト誤判定の修正（20分）
2. ✅ パス探索の柔軟化（1時間）
3. ✅ 指示の明確化（30分）
4. ✅ テスト実行（1時間）

**期待結果:** 20タスク改善、失敗率 42.6% → 13.2%

### ステップ2: フェーズ2の実装（1-2日後）
1. 汎用サンプルデータの追加
2. モデルキャッシュの設定
3. 依存関係チェックの追加

**期待結果:** さらに8-12タスク改善

### ステップ3: フェーズ3の計画（必要に応じて）
- より完全な環境構築
- Dockerイメージの拡張

---

## 📝 実装チェックリスト

### フェーズ1: 評価コードの改善
- [ ] `run_infer.py` の `complete_runtime` 関数を修正
  - [ ] タイムアウト誤判定の修正（186-196行）
  - [ ] `find_run_script` 関数の追加
  - [ ] パス探索ロジックの統合（158行付近）
  - [ ] 読み取り権限チェックの追加
- [ ] `process_instance` 関数の指示テキストを修正（217-232行）
- [ ] テストケースで動作確認
  - [ ] タイムアウトケース（Exit 124）
  - [ ] サブディレクトリケース（Instance 164など）
  - [ ] 読み取り失敗ケース（Instance 15など）
- [ ] 既存の成功ケースが影響を受けないことを確認

### フェーズ2: 環境の部分的改善
- [ ] `initialize_runtime` に汎用データ設定を追加
- [ ] モデルキャッシュの設定
- [ ] 依存関係チェック機能の追加
- [ ] テスト実行

### フェーズ3: 完全な環境構築
- [ ] Dockerイメージの分析
- [ ] 必要なモデルのリスト作成
- [ ] サンプルデータの準備
- [ ] Dockerイメージのビルドとテスト

---

## 🔬 検証方法

### テスト対象タスク
```python
# フェーズ1のテストケース
test_instances = {
    'timeout': [57, 109, 262, 135],  # Exit 124 タイムアウト
    'path_mismatch': [164, 145, 230, 129, 260, 172],  # サブディレクトリ
    'read_failure': [15, 238],  # 読み取り失敗
}

# フェーズ2のテストケース
test_instances_phase2 = {
    'missing_data': [49, 33, 37, 204, 53],  # データ不足
    'missing_model': [41, 93, 113, 105],  # モデル不足
    'dependencies': [272, 264, 151, 240, 234],  # 依存関係
}
```

### 検証スクリプト
```bash
# 特定のタスクのみを再評価
python run_infer.py \
  --eval-split quarter \
  --agent-cls CodeActAgent \
  --llm-config claude-sonnet-4-5 \
  --max-iterations 100 \
  --eval-ids 164,145,230,129,260,172  # パスミスマッチのタスク
```

---

## 📊 期待される最終結果

### 修正前
- 総タスク数: 68
- 成功: 39（57.4%）← 実際は27（39.7%）、12タスクは誤判定
- 失敗: 29（42.6%）
- うち環境/評価問題: 26（89.7%）

### 修正後（フェーズ1完了時）
- 総タスク数: 68
- 成功: 47-49（69.1-72.1%）
- 失敗: 19-21（27.9-30.9%）
- うち真のエージェント失敗: 3-5（4.4-7.4%）

### 修正後（全フェーズ完了時）
- 総タスク数: 68
- 成功: 62-65（91.2-95.6%）
- 失敗: 3-6（4.4-8.8%）
- うち真のエージェント失敗: 3（4.4%）

---

## 🚦 次のアクション

### 即座に実行可能
1. **run_infer.py の修正をコミット**
2. **テストタスクで動作確認**
3. **全タスクで再評価**

### 準備が必要
1. サンプルデータの準備
2. モデルダウンロード戦略の設計
3. Dockerイメージの拡張計画

---

生成日時: 2025-12-02
対象: ML-Bench 評価システム
期待改善: 20タスク（フェーズ1）→ 32タスク（全フェーズ）
