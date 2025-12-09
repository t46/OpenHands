#!/usr/bin/env python3
"""
Detailed regression analysis across all four evaluations.
Identifies tasks that regressed and analyzes exit code changes.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_evaluation(jsonl_path):
    """Load evaluation results and return dict of instance_id -> result"""
    results = {}

    if not jsonl_path.exists():
        return results

    with open(jsonl_path) as f:
        for line in f:
            data = json.loads(line)
            instance_id = data['instance_id']
            test_result = data.get('test_result', {})

            results[instance_id] = {
                'success': test_result.get('success', 0),
                'exit_code': test_result.get('eval_exit_code', 'unknown'),
                'eval_output': test_result.get('eval_output', '')[:500],  # First 500 chars
                'instruction': data.get('instruction', '')[:200],
            }

    return results

def main():
    base_path = Path('/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent')

    # Load all evaluations
    evals = {
        'dec2': base_path / 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_env_fixed_20251202' / 'output.jsonl',
        'dec4_pre': base_path / 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_env_fixed_20251203' / 'output.jsonl',
        'dec4_post': base_path / 'claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_20251204' / 'output.jsonl',
    }

    print("📖 Loading evaluation results...")
    data = {}
    for name, path in evals.items():
        data[name] = load_evaluation(path)
        print(f"   {name}: {len(data[name])} tasks loaded")

    # Get all instance IDs
    all_ids = set()
    for results in data.values():
        all_ids.update(results.keys())
    all_ids = sorted(all_ids, key=lambda x: int(x))

    print(f"\n📊 Total unique tasks: {len(all_ids)}")

    # Analyze each task across evaluations
    print("\n" + "="*100)
    print("DETAILED TASK-BY-TASK COMPARISON")
    print("="*100)

    regression_categories = defaultdict(list)

    for instance_id in all_ids:
        dec2 = data['dec2'].get(instance_id, {})
        dec4_pre = data['dec4_pre'].get(instance_id, {})
        dec4_post = data['dec4_post'].get(instance_id, {})

        dec2_success = dec2.get('success', 0)
        dec4_pre_success = dec4_pre.get('success', 0)
        dec4_post_success = dec4_post.get('success', 0)

        dec2_exit = dec2.get('exit_code', '?')
        dec4_pre_exit = dec4_pre.get('exit_code', '?')
        dec4_post_exit = dec4_post.get('exit_code', '?')

        # Categorize the task
        if dec2_success and not dec4_post_success:
            # Regressed from Dec 2 to Dec 4 (post)
            regression_categories['dec2_to_dec4post'].append({
                'id': instance_id,
                'dec2_exit': dec2_exit,
                'dec4_pre_exit': dec4_pre_exit,
                'dec4_post_exit': dec4_post_exit,
                'instruction': dec2.get('instruction', ''),
                'output': dec4_post.get('eval_output', ''),
            })
        elif dec4_pre_success and not dec4_post_success:
            # Regressed from Dec 4 (pre) to Dec 4 (post) - instruction change broke it
            regression_categories['dec4pre_to_dec4post'].append({
                'id': instance_id,
                'dec2_exit': dec2_exit,
                'dec4_pre_exit': dec4_pre_exit,
                'dec4_post_exit': dec4_post_exit,
                'instruction': dec4_pre.get('instruction', ''),
                'output': dec4_post.get('eval_output', ''),
            })
        elif not dec2_success and dec4_post_success:
            # Improved from Dec 2 to Dec 4 (post)
            regression_categories['improved_from_dec2'].append({
                'id': instance_id,
                'dec2_exit': dec2_exit,
                'dec4_pre_exit': dec4_pre_exit,
                'dec4_post_exit': dec4_post_exit,
                'instruction': dec2.get('instruction', ''),
            })
        elif not dec4_pre_success and dec4_post_success:
            # Fixed by instruction change
            regression_categories['fixed_by_instruction'].append({
                'id': instance_id,
                'dec2_exit': dec2_exit,
                'dec4_pre_exit': dec4_pre_exit,
                'dec4_post_exit': dec4_post_exit,
                'instruction': dec4_pre.get('instruction', ''),
            })

    # Print detailed analysis
    print("\n" + "="*100)
    print("1. Dec 2で成功 → Dec 4 (修正後)で失敗したタスク")
    print("="*100)

    if regression_categories['dec2_to_dec4post']:
        print(f"\n合計: {len(regression_categories['dec2_to_dec4post'])}件\n")

        for task in regression_categories['dec2_to_dec4post']:
            print(f"\n{'─'*100}")
            print(f"タスク ID: {task['id']}")
            print(f"Exit Code変化: Dec 2 ({task['dec2_exit']}) → Dec 4前 ({task['dec4_pre_exit']}) → Dec 4後 ({task['dec4_post_exit']})")
            print(f"\nInstruction (抜粋):")
            print(f"  {task['instruction'][:150]}...")
            print(f"\nError Output (抜粋):")
            output_lines = task['output'].split('\n')
            for line in output_lines[-5:]:  # Last 5 lines
                if line.strip():
                    print(f"  {line[:200]}")
    else:
        print("\n該当なし")

    print("\n" + "="*100)
    print("2. Dec 4 (修正前)で成功 → Dec 4 (修正後)で失敗したタスク（インストラクション変更の悪影響）")
    print("="*100)

    if regression_categories['dec4pre_to_dec4post']:
        print(f"\n合計: {len(regression_categories['dec4pre_to_dec4post'])}件\n")

        for task in regression_categories['dec4pre_to_dec4post']:
            print(f"\n{'─'*100}")
            print(f"タスク ID: {task['id']}")
            print(f"Exit Code変化: Dec 2 ({task['dec2_exit']}) → Dec 4前 ({task['dec4_pre_exit']}) → Dec 4後 ({task['dec4_post_exit']})")
            print(f"\nInstruction (抜粋):")
            print(f"  {task['instruction'][:150]}...")
            print(f"\nError Output (抜粋):")
            output_lines = task['output'].split('\n')
            for line in output_lines[-5:]:  # Last 5 lines
                if line.strip():
                    print(f"  {line[:200]}")
    else:
        print("\n該当なし")

    print("\n" + "="*100)
    print("3. インストラクション修正で改善されたタスク")
    print("="*100)

    if regression_categories['fixed_by_instruction']:
        print(f"\n合計: {len(regression_categories['fixed_by_instruction'])}件\n")

        for task in regression_categories['fixed_by_instruction']:
            print(f"  Task {task['id']}: Exit {task['dec4_pre_exit']} → Exit {task['dec4_post_exit']}")
    else:
        print("\n該当なし")

    print("\n" + "="*100)
    print("4. Dec 2から改善されたタスク")
    print("="*100)

    if regression_categories['improved_from_dec2']:
        print(f"\n合計: {len(regression_categories['improved_from_dec2'])}件\n")

        for task in regression_categories['improved_from_dec2']:
            print(f"  Task {task['id']}: Exit {task['dec2_exit']} → Exit {task['dec4_post_exit']}")
    else:
        print("\n該当なし")

    # Exit code transition analysis
    print("\n" + "="*100)
    print("EXIT CODE TRANSITION ANALYSIS")
    print("="*100)

    transitions = defaultdict(lambda: defaultdict(int))

    for instance_id in all_ids:
        dec2_exit = data['dec2'].get(instance_id, {}).get('exit_code', '?')
        dec4_post_exit = data['dec4_post'].get(instance_id, {}).get('exit_code', '?')

        if dec2_exit != '?' and dec4_post_exit != '?':
            transitions[f"{dec2_exit} → {dec4_post_exit}"][instance_id] = 1

    print("\nDec 2 → Dec 4 (修正後) のExit Code変化:")
    for transition, tasks in sorted(transitions.items(), key=lambda x: -len(x[1])):
        count = len(tasks)
        print(f"  {transition}: {count}件")
        if count <= 5:
            print(f"    Tasks: {sorted(tasks.keys())}")

    # Generate summary statistics
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)

    print("\n成功率の推移:")
    for name in ['dec2', 'dec4_pre', 'dec4_post']:
        success_count = sum(1 for r in data[name].values() if r.get('success', 0) == 1)
        total = len(data[name])
        rate = (success_count / total * 100) if total > 0 else 0
        print(f"  {name:12s}: {success_count:2d}/{total} = {rate:5.1f}%")

    print("\nExit Code分布:")
    print(f"{'Exit Code':<12} {'Dec 2':<10} {'Dec 4前':<10} {'Dec 4後':<10}")
    print("─" * 50)

    all_exit_codes = set()
    for results in data.values():
        for r in results.values():
            all_exit_codes.add(r.get('exit_code', 'unknown'))

    for exit_code in sorted(all_exit_codes, key=lambda x: (isinstance(x, str), x)):
        dec2_count = sum(1 for r in data['dec2'].values() if r.get('exit_code') == exit_code)
        dec4_pre_count = sum(1 for r in data['dec4_pre'].values() if r.get('exit_code') == exit_code)
        dec4_post_count = sum(1 for r in data['dec4_post'].values() if r.get('exit_code') == exit_code)
        print(f"Exit {exit_code:<7} {dec2_count:<10} {dec4_pre_count:<10} {dec4_post_count:<10}")

    # Save detailed results to JSON
    output_data = {
        'regressions': {
            'dec2_to_dec4post': regression_categories['dec2_to_dec4post'],
            'dec4pre_to_dec4post': regression_categories['dec4pre_to_dec4post'],
        },
        'improvements': {
            'fixed_by_instruction': regression_categories['fixed_by_instruction'],
            'improved_from_dec2': regression_categories['improved_from_dec2'],
        },
        'statistics': {
            'dec2': {
                'total': len(data['dec2']),
                'success': sum(1 for r in data['dec2'].values() if r.get('success', 0) == 1),
            },
            'dec4_pre': {
                'total': len(data['dec4_pre']),
                'success': sum(1 for r in data['dec4_pre'].values() if r.get('success', 0) == 1),
            },
            'dec4_post': {
                'total': len(data['dec4_post']),
                'success': sum(1 for r in data['dec4_post'].values() if r.get('success', 0) == 1),
            },
        },
    }

    output_path = Path('/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/regression_analysis_detailed.json')
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_path}")

if __name__ == '__main__':
    main()
