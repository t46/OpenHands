#!/usr/bin/env python3
import json

env_task_ids = ["3", "33", "37", "41", "45", "49", "53", "93", "105", "113", "151", "204", "234", "240", "244", "264", "272"]

output_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_v0.62.0/output.jsonl"

with open(output_file, 'r') as f:
    for line in f:
        record = json.loads(line)
        if record['instance_id'] in env_task_ids:
            instruction = record['instruction']

            # Check if has prefix code
            has_prefix = 'prefix code' in instruction.lower()

            # Extract repo name
            repo_line = [l for l in instruction.split('\n') if 'repository:' in l]
            repo = repo_line[0].split('repository:')[1].strip() if repo_line else 'Unknown'

            # Extract prefix code if exists
            prefix_code = ''
            if has_prefix:
                parts = instruction.split('```bash')
                if len(parts) > 1:
                    prefix_code = parts[1].split('```')[0].strip()

            print(f"\n{'='*80}")
            print(f"Instance {record['instance_id']}: {repo}")
            print(f"Has Prefix Code: {has_prefix}")
            if prefix_code:
                print(f"\nPrefix Code:")
                for line in prefix_code.split('\n')[:10]:  # First 10 lines
                    print(f"  {line}")
                if len(prefix_code.split('\n')) > 10:
                    print(f"  ... ({len(prefix_code.split('\n')) - 10} more lines)")
