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

        # Check agent messages for setup attempts
        history = record.get('history', [])

        setup_keywords = ['pip install', 'wget', 'download', 'git clone', 'mkdir model']

        agent_messages = [msg for msg in history if msg.get('source') == 'agent']

        print(f"\nTotal agent messages: {len(agent_messages)}")
        print(f"\nChecking for setup attempts (pip install, wget, etc.)...\n")

        found_setup = False
        for i, msg in enumerate(agent_messages):
            message_text = msg.get('message', '')
            if any(keyword in message_text.lower() for keyword in setup_keywords):
                found_setup = True
                print(f"Message {i+1}: Found setup attempt")
                # Print relevant snippet
                lines = message_text.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in setup_keywords):
                        print(f"  {line[:100]}")

        if not found_setup:
            print("❌ No setup attempts found in agent messages")
        else:
            print("\n✅ Agent attempted setup")

        # Check the actual script content
        script_content = record['test_result'].get('eval_script_content', '')
        print(f"\nScript length: {len(script_content)} characters")

        if script_content:
            print("\nScript contains setup commands:")
            for line in script_content.split('\n')[:30]:  # First 30 lines
                if any(keyword in line.lower() for keyword in setup_keywords):
                    print(f"  {line}")
