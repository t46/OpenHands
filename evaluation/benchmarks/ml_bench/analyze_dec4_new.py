#!/usr/bin/env python3
"""Analyze claude_sonnet_20251204 results and compare with previous evaluations."""

import json
from pathlib import Path
from collections import defaultdict

def analyze_output(jsonl_path):
    """Analyze a single output.jsonl file."""
    results = {
        'total': 0,
        'success': 0,
        'failure': 0,
        'exit_codes': defaultdict(int),
        'successes': [],
        'failures': [],
    }

    with open(jsonl_path) as f:
        for line in f:
            data = json.loads(line)
            results['total'] += 1

            instance_id = data.get('instance_id', 'unknown')
            test_result = data.get('test_result', {})
            success = test_result.get('success', 0)
            exit_code = test_result.get('eval_exit_code', 'unknown')

            results['exit_codes'][exit_code] += 1

            if success:
                results['success'] += 1
                results['successes'].append(instance_id)
            else:
                results['failure'] += 1
                results['failures'].append(instance_id)

    return results

def main():
    base_path = Path('/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent')

    # All four evaluations
    evals = {
        'Nov 19 (10 iter)': 'claude-sonnet-4-5-20250929_maxiter_10_N_v0.62.0',
        'Dec 2 (env_fixed)': 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_env_fixed_20251202',
        'Dec 4 (before fix)': 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_env_fixed_20251203',
        'Dec 4 (after fix)': 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_20251204',
    }

    all_results = {}

    for name, dirname in evals.items():
        jsonl_path = base_path / dirname / 'output.jsonl'
        if jsonl_path.exists():
            print(f"\n{'='*60}")
            print(f"Analyzing: {name}")
            print(f"Path: {dirname}")
            print(f"{'='*60}")

            results = analyze_output(jsonl_path)
            all_results[name] = results

            success_rate = (results['success'] / results['total'] * 100) if results['total'] > 0 else 0

            print(f"\nOverall Results:")
            print(f"  Total: {results['total']}")
            print(f"  Success: {results['success']} ({success_rate:.1f}%)")
            print(f"  Failure: {results['failure']}")

            print(f"\nExit Code Distribution:")
            for exit_code in sorted(results['exit_codes'].keys(), key=lambda x: (isinstance(x, str), x)):
                count = results['exit_codes'][exit_code]
                pct = (count / results['total'] * 100) if results['total'] > 0 else 0
                print(f"  Exit {exit_code}: {count} ({pct:.1f}%)")
        else:
            print(f"\nWARNING: {name} not found at {jsonl_path}")

    # Comparison table
    print(f"\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Metric':<30} {'Nov 19':<15} {'Dec 2':<15} {'Dec 4 (pre)':<15} {'Dec 4 (post)':<15}")
    print(f"{'-'*80}")

    metrics = [
        ('Total tasks', 'total'),
        ('Success', 'success'),
        ('Failure', 'failure'),
    ]

    for metric_name, metric_key in metrics:
        row = f"{metric_name:<30}"
        for eval_name in ['Nov 19 (10 iter)', 'Dec 2 (env_fixed)', 'Dec 4 (before fix)', 'Dec 4 (after fix)']:
            if eval_name in all_results:
                val = all_results[eval_name].get(metric_key, 0)
                if metric_key in ['success', 'failure']:
                    total = all_results[eval_name]['total']
                    pct = (val / total * 100) if total > 0 else 0
                    row += f"{val} ({pct:.1f}%)"
                else:
                    row += f"{val}"
                row += " " * (15 - len(row.split()[-1]))
            else:
                row += "N/A            "
        print(row)

    # Exit code comparison
    print(f"\n{'='*80}")
    print("EXIT CODE COMPARISON")
    print(f"{'='*80}")

    all_exit_codes = set()
    for results in all_results.values():
        all_exit_codes.update(results['exit_codes'].keys())

    print(f"{'Exit Code':<15} {'Nov 19':<15} {'Dec 2':<15} {'Dec 4 (pre)':<15} {'Dec 4 (post)':<15}")
    print(f"{'-'*80}")

    for exit_code in sorted(all_exit_codes, key=lambda x: (isinstance(x, str), x)):
        row = f"Exit {exit_code:<10}"
        for eval_name in ['Nov 19 (10 iter)', 'Dec 2 (env_fixed)', 'Dec 4 (before fix)', 'Dec 4 (after fix)']:
            if eval_name in all_results:
                count = all_results[eval_name]['exit_codes'].get(exit_code, 0)
                row += f"{count:<15}"
            else:
                row += "N/A            "
        print(row)

    # Task-by-task comparison between Dec 2, Dec 4 (pre), and Dec 4 (post)
    if 'Dec 2 (env_fixed)' in all_results and 'Dec 4 (before fix)' in all_results and 'Dec 4 (after fix)' in all_results:
        print(f"\n{'='*80}")
        print("TASK-BY-TASK CHANGES")
        print(f"{'='*80}")

        dec2_success = set(all_results['Dec 2 (env_fixed)']['successes'])
        dec4_pre_success = set(all_results['Dec 4 (before fix)']['successes'])
        dec4_post_success = set(all_results['Dec 4 (after fix)']['successes'])

        # Dec 2 → Dec 4 (pre)
        regressed_to_pre = dec2_success - dec4_pre_success
        improved_from_dec2 = dec4_pre_success - dec2_success

        # Dec 4 (pre) → Dec 4 (post)
        fixed_by_instruction = dec4_post_success - dec4_pre_success
        broken_by_instruction = dec4_pre_success - dec4_post_success

        # Net changes
        net_from_dec2 = dec4_post_success - dec2_success
        regressed_from_dec2 = dec2_success - dec4_post_success

        print(f"\nDec 2 → Dec 4 (before instruction fix):")
        print(f"  Regressed: {len(regressed_to_pre)} tasks")
        if regressed_to_pre:
            print(f"    {sorted(regressed_to_pre)[:5]}{'...' if len(regressed_to_pre) > 5 else ''}")
        print(f"  Improved: {len(improved_from_dec2)} tasks")
        if improved_from_dec2:
            print(f"    {sorted(improved_from_dec2)[:5]}{'...' if len(improved_from_dec2) > 5 else ''}")

        print(f"\nDec 4 (before fix) → Dec 4 (after instruction fix):")
        print(f"  Fixed by instruction change: {len(fixed_by_instruction)} tasks")
        if fixed_by_instruction:
            for task in sorted(fixed_by_instruction):
                print(f"    ✓ {task}")
        print(f"  Broken by instruction change: {len(broken_by_instruction)} tasks")
        if broken_by_instruction:
            for task in sorted(broken_by_instruction):
                print(f"    ✗ {task}")

        print(f"\nNet change from Dec 2 to Dec 4 (after fix):")
        print(f"  New successes: {len(net_from_dec2)} tasks")
        if net_from_dec2:
            for task in sorted(net_from_dec2):
                print(f"    ✓ {task}")
        print(f"  New failures: {len(regressed_from_dec2)} tasks")
        if regressed_from_dec2:
            for task in sorted(regressed_from_dec2)[:10]:
                print(f"    ✗ {task}")
            if len(regressed_from_dec2) > 10:
                print(f"    ... and {len(regressed_from_dec2) - 10} more")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    if 'Dec 4 (after fix)' in all_results:
        dec4_post = all_results['Dec 4 (after fix)']
        success_rate = (dec4_post['success'] / dec4_post['total'] * 100)
        print(f"\nDec 4 (after instruction fix):")
        print(f"  Success rate: {dec4_post['success']}/{dec4_post['total']} = {success_rate:.1f}%")

        if 'Dec 4 (before fix)' in all_results:
            dec4_pre = all_results['Dec 4 (before fix)']
            pre_rate = (dec4_pre['success'] / dec4_pre['total'] * 100)
            delta = success_rate - pre_rate
            print(f"  Change from before fix: {delta:+.1f}% ({dec4_post['success'] - dec4_pre['success']:+d} tasks)")

        if 'Dec 2 (env_fixed)' in all_results:
            dec2 = all_results['Dec 2 (env_fixed)']
            dec2_rate = (dec2['success'] / dec2['total'] * 100)
            delta = success_rate - dec2_rate
            print(f"  Change from Dec 2: {delta:+.1f}% ({dec4_post['success'] - dec2['success']:+d} tasks)")

        # Exit 2 analysis
        exit2_count = dec4_post['exit_codes'].get(2, 0)
        print(f"\nExit 2 errors (Bash syntax - our target):")
        print(f"  Dec 4 (after fix): {exit2_count}")
        if 'Dec 4 (before fix)' in all_results:
            exit2_pre = all_results['Dec 4 (before fix)']['exit_codes'].get(2, 0)
            print(f"  Dec 4 (before fix): {exit2_pre}")
            print(f"  Reduction: {exit2_pre - exit2_count} ({((exit2_pre - exit2_count) / exit2_pre * 100) if exit2_pre > 0 else 0:.1f}%)")

if __name__ == '__main__':
    main()
