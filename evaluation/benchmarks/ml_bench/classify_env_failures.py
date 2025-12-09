#!/usr/bin/env python3
import json

env_task_ids = ["3", "33", "37", "41", "45", "49", "53", "93", "105", "113", "151", "204", "234", "240", "244", "264", "272"]

output_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_v0.62.0/output.jsonl"

tasks_with_setup = []
tasks_without_setup = []

with open(output_file, 'r') as f:
    for line in f:
        record = json.loads(line)
        if record['instance_id'] in env_task_ids:
            instruction = record['instruction']

            # Extract repo name
            first_line = instruction.split('\n')[0]
            repo = first_line.split('repository:')[1].strip() if 'repository:' in first_line else 'Unknown'

            # Check if has prefix code with actual setup commands
            has_setup = False
            if 'prefix code' in instruction.lower():
                parts = instruction.split('```bash')
                if len(parts) > 1:
                    prefix_code = parts[1].split('```')[0].strip()
                    # Check if it's more than just environment variables
                    lines = [l.strip() for l in prefix_code.split('\n') if l.strip()]
                    # Has setup if it contains commands beyond just 'export'
                    has_setup = any(not line.startswith('export') for line in lines)

            if has_setup:
                tasks_with_setup.append({
                    'id': record['instance_id'],
                    'repo': repo
                })
            else:
                tasks_without_setup.append({
                    'id': record['instance_id'],
                    'repo': repo
                })

print("=" * 80)
print("タスクの分類結果")
print("=" * 80)

print(f"\n【エージェントの責任】セットアップ手順が提供されている: {len(tasks_with_setup)}タスク")
print("-" * 80)
for task in tasks_with_setup:
    print(f"  Instance {task['id']}: {task['repo']}")

print(f"\n【タスク側の不備】リソースが既に存在すると仮定: {len(tasks_without_setup)}タスク")
print("-" * 80)
for task in tasks_without_setup:
    print(f"  Instance {task['id']}: {task['repo']}")

print(f"\n総計: {len(tasks_with_setup) + len(tasks_without_setup)}タスク")
