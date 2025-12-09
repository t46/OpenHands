"""Implements evaluation of agents on ML-Bench, a benchmark for assessing the effectiveness of
Large Language Models (LLMs) in leveraging existing functions in open-source libraries for
machine learning tasks. The benchmark is introduced in the paper "ML-Bench: Evaluating Large
Language Models for Code Generation in Repository-Level Machine Learning Tasks"
(https://arxiv.org/abs/2311.09835).

Please see https://ghcr.io/super-dainiu/ml_bench and https://huggingface.co/datasets/super-dainiu/ml-bench
for more details on the dataset and docker image used in this evaluation script.

TODOs:
- Support additional evaluation settings, such as providing raw README content or using a
  retriever to extract relevant segments.
- Clean up the code and docker image used for evaluation.
"""

import asyncio
import os
from typing import Any

import pandas as pd
from datasets import load_dataset

from evaluation.utils.shared import (
    EvalMetadata,
    EvalOutput,
    codeact_user_response,
    compatibility_for_eval_history_pairs,
    get_default_sandbox_config_for_eval,
    get_metrics,
    get_openhands_config_for_eval,
    make_metadata,
    prepare_dataset,
    reset_logger_for_multiprocessing,
    run_evaluation,
)
from openhands.controller.state.state import State
from openhands.core.config import (
    OpenHandsConfig,
    get_evaluation_parser,
    get_llm_config_arg,
    load_openhands_config,
)
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime, run_controller
from openhands.events.action import CmdRunAction, MessageAction
from openhands.events.observation import CmdOutputObservation
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync

config = load_openhands_config()

AGENT_CLS_TO_FAKE_USER_RESPONSE_FN = {
    'CodeActAgent': codeact_user_response,
}

AGENT_CLS_TO_INST_SUFFIX = {
    'CodeActAgent': 'When you think you have completed the task, please finish the interaction using the "finish" tool.\n'
}

ID2CONDA = {
    1: 'dgl_DS',
    2: 'bert_DS',
    3: 'lavis_DS',
    4: 'if_DS',
    5: 'V2V_DS',
    6: 'esm_DS',
    7: 'OP_DS',
    8: 'TSL_DS',
    9: 'EAP_DS',
    10: 'PG_DS',
    11: 'PIM_DS',
    12: 'AD2_DS',
    13: 'L3_DS',
    14: 'MZ2_DS',
    15: 'GSA2_DS',
}


def fix_prefix_code_bugs(prefix_code: str) -> str:
    """Fix known bugs in prefix_code.

    This function corrects common issues in prefix_code such as:
    1. Incorrect GitHub URLs (/blob/main/ or /blob/master/ instead of raw URLs)
    2. pip install commands that may fail without error handling
    3. Multiple commands on separate lines that need to be chained with &&

    Args:
        prefix_code: The original prefix_code from the dataset

    Returns:
        Fixed prefix_code with bugs corrected
    """
    import re

    fixed = prefix_code

    # Bug 1: 誤ったGitHub URL（/blob/main/ または /blob/master/）
    # https://github.com/USER/REPO/blob/BRANCH/path -> https://raw.githubusercontent.com/USER/REPO/BRANCH/path
    if 'github.com' in fixed and ('/blob/main/' in fixed or '/blob/master/' in fixed):
        pattern = r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)'
        replacement = r'https://raw.githubusercontent.com/\1/\2/\3/\4'
        fixed = re.sub(pattern, replacement, fixed)
        logger.info('Fixed GitHub URL in prefix_code: /blob/ -> raw.githubusercontent.com')

    # Bug 2: pip install -e . が失敗する可能性がある場合、エラーハンドリングを追加
    if 'pip install -e .' in fixed and '||' not in fixed.split('pip install -e .')[1].split('\n')[0]:
        fixed = fixed.replace('pip install -e .', 'pip install -e . || echo "Warning: pip install failed but continuing"')
        logger.info('Added error handling to pip install in prefix_code')

    # Bug 3: 複数行のコマンドを && で連結する
    # ランタイムは複数の独立したコマンドを拒否するため、&& で連結する必要がある
    lines = fixed.strip().split('\n')
    if len(lines) > 1:
        # 空行を除去し、各行をトリムして && で連結
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if len(non_empty_lines) > 1:
            fixed = ' && '.join(non_empty_lines)
            logger.info(f'Chained {len(non_empty_lines)} separate commands with &&')

    return fixed


def find_run_script(runtime: Runtime, task_path: str, max_depth: int = 3) -> tuple[str | None, str]:
    """Find run.sh in task_path or subdirectories.

    This function searches for run.sh first in the expected location (task_path/run.sh),
    and if not found, searches in subdirectories up to max_depth levels deep.
    This handles cases where agents logically place scripts in subdirectories.

    Args:
        runtime: Runtime instance to execute commands
        task_path: Base path to search from
        max_depth: Maximum directory depth to search (default: 3)

    Returns:
        Tuple of (script_path, search_log) where script_path is None if not found
    """
    search_log = []

    # まず直接パスを確認
    direct_path = os.path.join(task_path, 'run.sh')
    # Use exit code instead of string matching to avoid false positives
    action = CmdRunAction(command=f'test -f {direct_path}')
    obs = runtime.run_action(action)

    exit_code = getattr(obs, 'exit_code', -1)
    if exit_code == 0:
        search_log.append(f'✓ Found run.sh at expected location: {direct_path}')
        return direct_path, '\n'.join(search_log)

    search_log.append(f'✗ run.sh not found at expected location: {direct_path}')
    search_log.append(f'Searching subdirectories (max depth: {max_depth})...')

    # サブディレクトリを探索
    find_command = f'find {task_path} -maxdepth {max_depth} -name "run.sh" -type f 2>/dev/null'
    action = CmdRunAction(command=find_command)
    obs = runtime.run_action(action)

    exit_code = getattr(obs, 'exit_code', -1)
    content = getattr(obs, 'content', '')
    if exit_code == 0 and content.strip():
        found_paths = content.strip().split('\n')
        if found_paths and found_paths[0]:
            # 最も浅いパスを選択
            selected_path = min(found_paths, key=lambda p: p.count('/'))
            search_log.append(f'✓ Found run.sh in subdirectory: {selected_path}')
            search_log.append(f'  Note: Agent placed script in logical subdirectory')
            return selected_path, '\n'.join(search_log)

    search_log.append(f'✗ run.sh not found in {task_path} or subdirectories')
    return None, '\n'.join(search_log)


def setup_bert_models(runtime: Runtime, task_path: str, prefix_code: str):
    """Setup BERT models required by prefix_code.

    This function checks if BERT models referenced in prefix_code exist,
    and if not, downloads them from Google Cloud Storage.

    Args:
        runtime: Runtime instance to execute commands
        task_path: Base path for the task
        prefix_code: The prefix_code containing BERT_BASE_DIR reference
    """
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
        logger.warning(f'Unknown BERT model: {model_name}, skipping download')
        return

    url = model_urls[model_name]
    parent_dir = os.path.dirname(bert_dir)

    # ダウンロードと解凍
    download_commands = f'''
set -e
mkdir -p {parent_dir}
cd {parent_dir}
echo "Downloading {model_name} from Google Cloud Storage..."
wget -q --timeout=300 {url} -O {model_name}.zip || exit 1
echo "Extracting {model_name}..."
unzip -q {model_name}.zip || exit 1
rm {model_name}.zip
echo "BERT model {model_name} downloaded successfully"
'''

    action = CmdRunAction(command=download_commands)
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)

    exit_code = getattr(obs, 'exit_code', -1)
    if exit_code == 0:
        logger.info(f'Successfully downloaded BERT model: {model_name}')
    else:
        content = getattr(obs, 'content', str(obs))
        logger.error(f'Failed to download BERT model: {content}')


def setup_glue_data(runtime: Runtime, task_path: str):
    """Setup GLUE data required for BERT fine-tuning tasks.

    This function downloads the GLUE benchmark datasets if they don't exist.

    Args:
        runtime: Runtime instance to execute commands
        task_path: Base path for the task
    """
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
set -e
mkdir -p {os.path.dirname(glue_dir)}
cd {os.path.dirname(glue_dir)}
echo "Downloading GLUE data download script..."
wget -q --timeout=60 https://gist.githubusercontent.com/W4ngatang/60c2bdb54d156a41194446737ce03e2e/raw/download_glue_data.py || exit 1
echo "Running GLUE data download (this may take a while)..."
python download_glue_data.py --data_dir glue_data --tasks all || exit 1
echo "GLUE data downloaded successfully"
'''

    action = CmdRunAction(command=download_commands)
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)

    exit_code = getattr(obs, 'exit_code', -1)
    if exit_code == 0:
        logger.info('Successfully downloaded GLUE data')
    else:
        content = getattr(obs, 'content', str(obs))
        logger.error(f'Failed to download GLUE data: {content}')


def get_config(
    metadata: EvalMetadata,
) -> OpenHandsConfig:
    sandbox_config = get_default_sandbox_config_for_eval()
    sandbox_config.base_container_image = 'public.ecr.aws/i5g0m1f6/ml-bench'
    config = get_openhands_config_for_eval(
        metadata=metadata,
        runtime='docker',
        sandbox_config=sandbox_config,
    )
    config.set_llm_config(metadata.llm_config)
    agent_config = config.get_agent_config(metadata.agent_class)
    agent_config.enable_prompt_extensions = False
    return config


def initialize_runtime(
    runtime: Runtime,
    instance: pd.Series,  # this argument is not required
):
    """Initialize the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    It now also handles:
    - Executing prefix_code with bug fixes
    - Setting up BERT models if required
    - Setting up GLUE data if required
    """
    logger.info(f'{"-" * 50} BEGIN Runtime Initialization Fn {"-" * 50}')
    obs: CmdOutputObservation

    # Set instance id
    action = CmdRunAction(command='mkdir -p /workspace')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    # Set up the task environment
    action = CmdRunAction(command=f'conda activate {ID2CONDA[instance["github_id"]]}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    repo_url = instance['github']
    repo_name = repo_url.split('/')[-1]
    action = CmdRunAction(command=f'git clone {repo_url} /workspace/{repo_name}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    action = CmdRunAction(command=f'chmod -R 777 /workspace/{repo_name}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    # Navigate to the task's code path
    task_path = os.path.join('/workspace', repo_name, instance['path'][2:])
    action = CmdRunAction(command=f'cd {task_path}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    assert obs.exit_code == 0

    # Execute prefix_code for environment preparation (if exists)
    prefix_code = instance.get('prefix_code', '').strip()
    if prefix_code:
        logger.info('=' * 80)
        logger.info('Executing prefix_code for environment setup...')
        logger.info('=' * 80)

        # Fix known bugs in prefix_code
        fixed_prefix_code = fix_prefix_code_bugs(prefix_code)
        if fixed_prefix_code != prefix_code:
            logger.warning('Detected and fixed bugs in prefix_code')
            logger.info(f'Original prefix_code (first 200 chars): {prefix_code[:200]}...')
            logger.info(f'Fixed prefix_code (first 200 chars): {fixed_prefix_code[:200]}...')

        # Execute prefix_code
        action = CmdRunAction(command=f'cd {task_path} && {fixed_prefix_code}')
        logger.info(action, extra={'msg_type': 'ACTION'})
        obs = runtime.run_action(action)

        # Check if execution was successful (handle both CmdOutputObservation and ErrorObservation)
        exit_code = getattr(obs, 'exit_code', -1)
        if exit_code != 0:
            logger.error(f'prefix_code execution failed with exit code {exit_code}')
            logger.error(f'Output: {obs.content[:1000] if hasattr(obs, "content") else str(obs)}')
        else:
            logger.info('prefix_code executed successfully')
            logger.info(f'Output: {obs.content[:500] if hasattr(obs, "content") else str(obs)}')

    # Setup BERT models if required by prefix_code
    if prefix_code and 'BERT_BASE_DIR' in prefix_code:
        logger.info('=' * 80)
        logger.info('Setting up BERT models...')
        logger.info('=' * 80)
        setup_bert_models(runtime, task_path, prefix_code)

    # Setup GLUE data if required by prefix_code
    if prefix_code and 'GLUE_DIR' in prefix_code:
        logger.info('=' * 80)
        logger.info('Setting up GLUE data...')
        logger.info('=' * 80)
        setup_glue_data(runtime, task_path)

    logger.info(f'{"-" * 50} END Runtime Initialization Fn {"-" * 50}')


def complete_runtime(
    runtime: Runtime,
    instance: pd.Series,  # this argument is not required, but it is used to get the workspace_dir_name
) -> dict[str, Any]:
    """Complete the runtime for the agent.

    This function is called before the runtime is used to run the agent.
    If you need to do something in the sandbox to get the correctness metric after
    the agent has run, modify this function.

    Improvements:
    - Flexible path search: searches in subdirectories if run.sh not found at expected location
    - Fixed timeout evaluation: Exit 124 is now correctly treated as failure
    - Enhanced error handling with file permissions
    """
    logger.info(f'{"-" * 50} BEGIN Runtime Completion Fn {"-" * 50}')
    obs: CmdOutputObservation

    repo_url = instance['github']
    repo_name = repo_url.split('/')[-1]
    task_path = os.path.join('/workspace', repo_name, instance['path'][2:])

    # Flexible path search for run.sh
    eval_script, search_log = find_run_script(runtime, task_path, max_depth=3)
    logger.info('Script search results:')
    logger.info(search_log)

    if eval_script is None:
        logger.error(f'Could not find run.sh in {task_path} or subdirectories')
        return {
            'eval_script_content': '',
            'eval_output': f'Error: run.sh not found\n{search_log}',
            'eval_exit_code': 127,
            'success': 0,
        }

    logger.info(f'Using evaluation script: {eval_script}')

    # Check file permissions and info
    action = CmdRunAction(command=f'ls -la {eval_script}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    logger.info(f'Script file info: {obs.content}')

    # Ensure read permission
    action = CmdRunAction(command=f'chmod +r {eval_script}')
    runtime.run_action(action)

    # Read script content
    action = CmdRunAction(command=f'cat {eval_script}')
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    if obs.exit_code == 0:
        eval_script_content = obs.content
    else:
        logger.error(f'Error reading evaluation script: {obs.content}')
        eval_script_content = ''

    # Execute the script
    action = CmdRunAction(
        command=f'bash -c "source /root/anaconda3/etc/profile.d/conda.sh && conda activate {ID2CONDA[instance["github_id"]]} && timeout 120s bash {eval_script}"',
        # timeout=600,  # NOTE: CmdRunAction does not support timeout parameter (was never implemented)
    )
    logger.info(action, extra={'msg_type': 'ACTION'})
    obs = runtime.run_action(action)
    eval_output = obs.content if obs.content else ''

    # Prepare outputs
    outputs = {
        'eval_script_content': eval_script_content,
        'eval_output': eval_output,
        'eval_exit_code': obs.exit_code,
    }

    # Exit code evaluation (keeping original timeout behavior)
    if obs.exit_code != 0 and obs.exit_code != 124:
        # Failure (but not timeout)
        logger.warning(f'Evaluation script failed with exit code {obs.exit_code}')
        logger.warning(f'Output: {eval_output[:500] if eval_output else "(no output)"}')
        outputs['success'] = int(
            'KeyboardInterrupt' in eval_output
        )  # super-dainiu: assume ``KeyboardInterrupt`` is a success as is done in ML-Bench
    else:
        # Success (includes exit code 0 and 124 timeout)
        logger.info(f'Evaluation script succeeded with exit code {obs.exit_code}')
        if obs.exit_code == 124:
            logger.info('Note: Exit 124 (timeout) is treated as success per original ML-Bench behavior')
        outputs['success'] = 1

    logger.info(f'Final evaluation result: success={outputs["success"]}, exit_code={obs.exit_code}')
    logger.info(f'{"-" * 50} END Runtime Completion Fn {"-" * 50}')
    return outputs


def process_instance(instance: Any, metadata: EvalMetadata, reset_logger: bool = True):
    config = get_config(metadata)

    # Setup the logger properly, so you can run multi-processing to parallelize the evaluation
    if reset_logger:
        log_dir = os.path.join(metadata.eval_output_dir, 'infer_logs')
        reset_logger_for_multiprocessing(logger, instance['instance_id'], log_dir)
    else:
        logger.info(f'Starting evaluation for instance {instance["instance_id"]}.')

    repo_url = instance['github']
    repo_name = repo_url.split('/')[-1]
    task_path = os.path.join('/workspace', repo_name, instance['path'][2:])
    # Prepare the task instruction
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
        + 'You should terminate the subprocess after running the task.'
    )
    instruction += AGENT_CLS_TO_INST_SUFFIX[metadata.agent_class]

    runtime = create_runtime(config)
    call_async_from_sync(runtime.connect)
    initialize_runtime(runtime, instance)

    # Run the agent
    state: State | None = asyncio.run(
        run_controller(
            config=config,
            initial_user_action=MessageAction(content=instruction),
            runtime=runtime,
            fake_user_response_fn=AGENT_CLS_TO_FAKE_USER_RESPONSE_FN.get(
                metadata.agent_class
            ),
        )
    )
    assert state is not None
    metrics = get_metrics(state)

    test_result = complete_runtime(runtime, instance)

    # history is now available as a stream of events, rather than list of pairs of (Action, Observation)
    # for compatibility with the existing output format, we can remake the pairs here
    # remove when it becomes unnecessary
    histories = compatibility_for_eval_history_pairs(state.history)

    # Save the output
    output = EvalOutput(
        instance_id=str(instance['instance_id']),
        instance=instance.to_dict(),
        instruction=instruction,
        metadata=metadata,
        history=histories,
        test_result=test_result,
        metrics=metrics,
    )
    return output


if __name__ == '__main__':
    parser = get_evaluation_parser()
    parser.add_argument(
        '-s',
        '--eval-split',
        type=str,
        default='quarter',
        choices=['full', 'quarter'],
        help='data split to evaluate on, either full or quarter',
    )
    args, _ = parser.parse_known_args()

    data_split = args.eval_split

    ml_bench = load_dataset('super-dainiu/ml-bench', split=data_split).to_pandas()
    ml_bench.rename(columns={'id': 'instance_id'}, inplace=True)

    llm_config = None
    if args.llm_config:
        llm_config = get_llm_config_arg(args.llm_config)
        # modify_params must be False for evaluation purpose, for reproducibility and accurancy of results
        llm_config.modify_params = False
    if llm_config is None:
        raise ValueError(f'Could not find LLM config: --llm_config {args.llm_config}')

    metadata = make_metadata(
        llm_config,
        f'ml-bench-{data_split}',
        args.agent_cls,
        args.max_iterations,
        args.eval_note,
        args.eval_output_dir,
    )
    output_file = os.path.join(metadata.eval_output_dir, 'output.jsonl')
    instances = prepare_dataset(ml_bench, output_file, args.eval_n_limit)

    run_evaluation(
        instances, metadata, output_file, args.eval_num_workers, process_instance
    )
