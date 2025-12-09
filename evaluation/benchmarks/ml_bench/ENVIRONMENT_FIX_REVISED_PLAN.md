# ML-Bench 環境問題 修正計画（改訂版）

## 📋 エグゼクティブサマリー

ベンチマークの設計意図を理解した上で、**環境側の責任として修正すべき問題のみ**を対象とします。

### 責任分界点

| 責任 | 対象 | 修正方針 |
|------|------|---------|
| **環境側** | ベンチマークの明らかなエラー、環境準備 | ✅ 修正する |
| **エージェント側** | prefix_codeなしのタスク | ❌ 修正しない（エージェントの能力を評価） |

---

## 📊 修正対象の分類

### **修正対象：14タスク**

| カテゴリ | タスク数 | タスクID | 修正内容 |
|---------|---------|---------|---------|
| **パス探索の問題** | 6 | 164, 145, 230, 129, 260, 172 | サブディレクトリ探索の実装 |
| **BERTモデル不足** | 6 | 49, 33, 41, 45, 37, 53 | モデルの事前準備 |
| **prefix_codeのバグ** | 2 | 272, 264 | 誤ったURLとpip installの修正 |

### **修正対象外：15タスク**

| カテゴリ | タスク数 | タスクID | 理由 |
|---------|---------|---------|------|
| **エージェントの責任** | 10 | 244, 93, 113, 151, 204, 248, 240, 105, 3, 234 | prefix_codeなし。エージェントが自律的に解決すべき |
| **評価時の読み取り失敗** | 2 | 15, 238 | 原因不明。要詳細調査 |
| **実行時エラー** | 2 | 77, 28 | 環境と実装の混合問題 |
| **スクリプト不完全** | 1 | 25 | エージェントの責任 |

---

## 🎯 修正計画（タイムアウト誤判定以外）

### **フェーズ1: 評価コードの修正（即座に実装可能）**

#### 1.1 パス探索の柔軟化（6タスク改善）

**対象タスク:** 164, 145, 230, 129, 260, 172

**問題:**
- 評価が厳密に `task_path/run.sh` のみを探索
- エージェントはタスクに応じた論理的なサブディレクトリに配置

**修正内容:**

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

    # Exit code の評価（タイムアウト誤判定は別途修正）
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

**影響:** 6タスク改善

---

### **フェーズ2: 環境の適切な準備**

#### 2.1 BERTモデルの事前準備（6タスク改善）

**対象タスク:** 49, 33, 41, 45, 37, 53

**問題:**
- prefix_codeで `export BERT_BASE_DIR=./model/...` を設定
- しかしモデルが存在しない

**必要なBERTモデル:**
1. `uncased_L-12_H-768_A-12` (BERT-Base, Uncased)
2. `cased_L-12_H-768_A-12` (BERT-Base, Cased)
3. `wwm_uncased_L-24_H-1024_A-16` (BERT-Large, Uncased, Whole Word Masking)
4. `uncased_L-24_H-1024_A-16` (BERT-Large, Uncased)

**GLUEデータ:**
- `./data/glue_data` (Instance 33で必要)

**修正方法A: initialize_runtime でモデルをダウンロード（推奨）**

```python
def initialize_runtime(
    runtime: Runtime,
    instance: pd.Series,
):
    """Initialize the runtime for the agent."""
    logger.info(f'{"-" * 50} BEGIN Runtime Initialization Fn {"-" * 50}')
    obs: CmdOutputObservation

    # ... 既存のコード（mkdir, conda activate, git clone, chmod）...

    repo_url = instance['github']
    repo_name = repo_url.split('/')[-1]
    task_path = os.path.join('/workspace', repo_name, instance['path'][2:])

    # Navigate to the task's code path
    action = CmdRunAction(command=f'cd {task_path}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    # prefix_codeを実行（環境準備）
    prefix_code = instance.get('prefix_code', '').strip()
    if prefix_code:
        logger.info('Executing prefix_code for environment setup...')

        # prefix_codeの誤りを修正
        fixed_prefix_code = fix_prefix_code_bugs(prefix_code)
        if fixed_prefix_code != prefix_code:
            logger.warning('Detected and fixed bugs in prefix_code')
            logger.info(f'Original: {prefix_code[:200]}...')
            logger.info(f'Fixed: {fixed_prefix_code[:200]}...')

        # prefix_codeを実行
        action = CmdRunAction(command=f'cd {task_path} && {fixed_prefix_code}')
        logger.info(action, extra={'msg_type': 'ACTION'})
        obs = runtime.run_action(action)

        if obs.exit_code != 0:
            logger.error(f'prefix_code execution failed: {obs.content}')
        else:
            logger.info('prefix_code executed successfully')

    # BERTモデルが必要な場合はダウンロード
    if 'BERT_BASE_DIR' in prefix_code:
        setup_bert_models(runtime, task_path, prefix_code)

    # GLUEデータが必要な場合はダウンロード
    if 'GLUE_DIR' in prefix_code:
        setup_glue_data(runtime, task_path)

    logger.info(f'{"-" * 50} END Runtime Initialization Fn {"-" * 50}')


def fix_prefix_code_bugs(prefix_code: str) -> str:
    """Fix known bugs in prefix_code."""
    fixed = prefix_code

    # Bug 1: 誤ったGitHub URL（/blob/main/ または /blob/master/）
    if 'github.com' in fixed and ('/blob/main/' in fixed or '/blob/master/' in fixed):
        # https://github.com/USER/REPO/blob/BRANCH/path -> https://raw.githubusercontent.com/USER/REPO/BRANCH/path
        import re
        pattern = r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)'
        replacement = r'https://raw.githubusercontent.com/\1/\2/\3/\4'
        fixed = re.sub(pattern, replacement, fixed)

    # Bug 2: pip install -e . が失敗する可能性がある場合、エラーハンドリングを追加
    if 'pip install -e .' in fixed and '||' not in fixed:
        fixed = fixed.replace('pip install -e .', 'pip install -e . || echo "Warning: pip install failed"')

    return fixed


def setup_bert_models(runtime: Runtime, task_path: str, prefix_code: str):
    """Setup BERT models required by prefix_code."""
    import re

    # prefix_codeからBERT_BASE_DIRを抽出
    match = re.search(r'BERT_BASE_DIR=([^\s]+)', prefix_code)
    if not match:
        return

    bert_dir = match.group(1)

    # 絶対パスに変換
    if not bert_dir.startswith('/'):
        bert_dir = os.path.join(task_path, bert_dir)

    logger.info(f'Checking BERT model: {bert_dir}')

    # モデルが存在するかチェック
    action = CmdRunAction(command=f'test -d {bert_dir} && echo "exists" || echo "not_exists"')
    obs = runtime.run_action(action)

    if 'exists' in obs.content:
        logger.info(f'BERT model already exists: {bert_dir}')
        return

    logger.info(f'BERT model not found, downloading: {bert_dir}')

    # モデル名を特定
    model_name = os.path.basename(bert_dir)

    # モデルのマッピング（Google Research BERTからダウンロード）
    model_urls = {
        'uncased_L-12_H-768_A-12': 'https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-12_H-768_A-12.zip',
        'cased_L-12_H-768_A-12': 'https://storage.googleapis.com/bert_models/2018_10_18/cased_L-12_H-768_A-12.zip',
        'uncased_L-24_H-1024_A-16': 'https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-24_H-1024_A-16.zip',
        'wwm_uncased_L-24_H-1024_A-16': 'https://storage.googleapis.com/bert_models/2019_05_30/wwm_uncased_L-24_H-1024_A-16.zip',
    }

    if model_name not in model_urls:
        logger.warning(f'Unknown BERT model: {model_name}')
        return

    url = model_urls[model_name]
    parent_dir = os.path.dirname(bert_dir)

    # ダウンロードと解凍
    download_commands = f'''
    mkdir -p {parent_dir}
    cd {parent_dir}
    wget -q {url} -O {model_name}.zip
    unzip -q {model_name}.zip
    rm {model_name}.zip
    '''

    action = CmdRunAction(command=download_commands)
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)

    if obs.exit_code == 0:
        logger.info(f'Successfully downloaded BERT model: {model_name}')
    else:
        logger.error(f'Failed to download BERT model: {obs.content}')


def setup_glue_data(runtime: Runtime, task_path: str):
    """Setup GLUE data."""
    glue_dir = os.path.join(task_path, 'data', 'glue_data')

    logger.info(f'Checking GLUE data: {glue_dir}')

    # GLUEデータが存在するかチェック
    action = CmdRunAction(command=f'test -d {glue_dir} && echo "exists" || echo "not_exists"')
    obs = runtime.run_action(action)

    if 'exists' in obs.content:
        logger.info(f'GLUE data already exists: {glue_dir}')
        return

    logger.info(f'GLUE data not found, downloading: {glue_dir}')

    # GLUEデータのダウンロード（BERTリポジトリのスクリプトを使用）
    download_commands = f'''
    mkdir -p {os.path.dirname(glue_dir)}
    cd {os.path.dirname(glue_dir)}
    wget -q https://gist.githubusercontent.com/W4ngatang/60c2bdb54d156a41194446737ce03e2e/raw/download_glue_data.py
    python download_glue_data.py --data_dir glue_data --tasks all
    '''

    action = CmdRunAction(command=download_commands)
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)

    if obs.exit_code == 0:
        logger.info('Successfully downloaded GLUE data')
    else:
        logger.error(f'Failed to download GLUE data: {obs.content}')
```

**修正方法B: Dockerイメージに事前準備（より推奨）**

Dockerfileまたは初期化スクリプトに以下を追加：

```dockerfile
# BERTモデルの事前ダウンロード
RUN mkdir -p /workspace/models && \
    cd /workspace/models && \
    wget https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-12_H-768_A-12.zip && \
    unzip uncased_L-12_H-768_A-12.zip && \
    wget https://storage.googleapis.com/bert_models/2018_10_18/cased_L-12_H-768_A-12.zip && \
    unzip cased_L-12_H-768_A-12.zip && \
    wget https://storage.googleapis.com/bert_models/2018_10_18/uncased_L-24_H-1024_A-16.zip && \
    unzip uncased_L-24_H-1024_A-16.zip && \
    wget https://storage.googleapis.com/bert_models/2019_05_30/wwm_uncased_L-24_H-1024_A-16.zip && \
    unzip wwm_uncased_L-24_H-1024_A-16.zip && \
    rm *.zip

# その後、initialize_runtimeで適切な場所にシンボリックリンクを作成
```

**影響:** 6タスク改善

---

#### 2.2 prefix_codeのバグ修正（2タスク改善）

**対象タスク:** 272, 264

**問題:**
1. 誤ったGitHub URL: `https://github.com/.../blob/main/...`
2. `pip install -e .` の実行失敗

**修正内容:**

上記の `fix_prefix_code_bugs()` 関数で自動修正します。

**影響:** 2タスク改善

---

## 📊 期待される改善効果

| 修正内容 | 影響タスク数 | 実装難易度 | 期待効果 |
|---------|------------|-----------|---------|
| パス探索の柔軟化 | 6 | 🟢 低 | 即座に改善 |
| BERTモデルの準備 | 6 | 🟡 中 | 環境依存問題の根本解決 |
| prefix_codeバグ修正 | 2 | 🟢 低 | 即座に改善 |
| **合計** | **14タスク** | - | **失敗率 42.6% → 22.1%** |

---

## 🚫 修正対象外とその理由

### **エージェントの責任（10タスク）**

**タスクID:** 244, 93, 113, 151, 204, 248, 240, 105, 3, 234

**理由:**
- prefix_codeが存在しない
- タスクの指示のみでエージェントがモデル/データの取得方法を考えるべき
- これらを修正すると**ベンチマークの評価対象が変わってしまう**

**例: Instance 93**
```
指示: "Could you assist me in generating four visuals of dogs utilizing the
IF-II-L-v1.0 model? I'd like the 'guidance_scale' parameter to be adjusted to 5.0."
prefix_code: (なし)
```

→ エージェントがIF-II-L-v1.0モデルの取得方法を自分で考えるべき

---

### **その他の問題（5タスク）**

| タスクID | 問題 | 理由 |
|---------|------|------|
| 15, 238 | 評価時の読み取り失敗 | 原因不明。要詳細調査 |
| 77, 28 | 実行時エラー | 環境と実装の混合問題 |
| 25 | スクリプト不完全 | エージェントの責任 |

---

## 🚀 実装優先順位

### **優先度1: パス探索の柔軟化（即座に実装）**
- 実装時間: 1-2時間
- 期待効果: 6タスク改善

### **優先度2: prefix_codeバグ修正（即座に実装）**
- 実装時間: 30分
- 期待効果: 2タスク改善

### **優先度3: BERTモデルの準備**
- **方法A**: initialize_runtimeで動的ダウンロード
  - 実装時間: 2-3時間
  - メリット: すぐに実装可能
  - デメリット: 毎回ダウンロード（遅い）

- **方法B**: Dockerイメージに事前準備（推奨）
  - 実装時間: 1日（Dockerビルドとテスト含む）
  - メリット: 評価が高速、他の評価でも利用可能
  - デメリット: Dockerイメージの変更が必要

---

## 📝 実装チェックリスト

### フェーズ1: 評価コードの修正
- [ ] `find_run_script()` 関数の実装
- [ ] `complete_runtime()` 関数の修正
- [ ] `fix_prefix_code_bugs()` 関数の実装
- [ ] テストケースで動作確認（Instance 164, 272など）

### フェーズ2: 環境の準備
- [ ] `setup_bert_models()` 関数の実装
- [ ] `setup_glue_data()` 関数の実装
- [ ] `initialize_runtime()` 関数の修正
- [ ] BERTモデルのダウンロードテスト
- [ ] または、Dockerイメージの拡張

### 検証
- [ ] 修正対象14タスクで再評価
- [ ] 既存の成功タスクが影響を受けないことを確認
- [ ] 修正対象外10タスクが変わらないことを確認

---

## 🎯 最終目標

### 修正前
- 総タスク数: 68
- 成功: 27（39.7%）← タイムアウト誤判定を除く
- 失敗: 29（42.6%）
  - うち環境の責任: 14（20.6%）
  - うちエージェントの責任: 15（22.1%）

### 修正後（期待値）
- 総タスク数: 68
- 成功: 41（60.3%）
- 失敗: 15（22.1%）
  - うち環境の責任: 0-2（0-3%）← 残るのは調査が必要な問題のみ
  - うちエージェントの責任: 13-15（19-22%）← 本来の評価対象

**改善効果:** 失敗率 42.6% → 22.1%（14タスク改善）

---

生成日時: 2025-12-02
対象: ML-Bench 評価システム（タイムアウト誤判定以外）
修正対象: 14タスク（環境の責任のみ）
修正対象外: 15タスク（エージェントの責任）
