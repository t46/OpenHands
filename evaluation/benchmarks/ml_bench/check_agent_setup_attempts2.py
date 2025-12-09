#!/usr/bin/env python3
import json

output_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_v0.62.0/output.jsonl"

# Check instances 272 and 264 (Grounded-Segment-Anything)
target_instances = [("272", "Grounded-Segment-Anything"), ("264", "Grounded-Segment-Anything")]

with open(output_file, 'r') as f:
    for line in f:
        record = json.loads(line)
        instance_id = record['instance_id']
        instruction = record['instruction']

        # Check if this is one of our target instances
        is_target = False
        for tid, repo in target_instances:
            if instance_id == tid and repo in instruction:
                is_target = True
                target_repo = repo
                break

        if not is_target:
            continue

        print(f"\n{'='*80}")
        print(f"Instance {instance_id}: {target_repo}")
        print(f"{'='*80}")

        # Check the actual script content
        script_content = record['test_result'].get('eval_script_content', '')
        print(f"\nScript length: {len(script_content)} characters")

        if script_content:
            print("\n=== Script content (first 50 lines) ===\n")
            for i, line in enumerate(script_content.split('\n')[:50], 1):
                print(f"{i:3}: {line}")
        else:
            print("\n❌ No script content found")
