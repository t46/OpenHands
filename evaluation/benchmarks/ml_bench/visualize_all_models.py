#!/usr/bin/env python3
"""
Multi-Model ML-Bench Results Visualization Script
Creates visualizations for GPT-4o and GPT-5 results
"""

import json
import subprocess
from pathlib import Path

# Configuration
CONFIGS = [
    {
        'name': 'Claude Sonnet 4.5 (maxiter=100)',
        'input_file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_v0.62.0/output.jsonl',
        'output_dir': '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_claude_sonnet_iter100',
        'short_name': 'claude-sonnet-100'
    },
    {
        'name': 'GPT-4o (maxiter=50)',
        'input_file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-4o_maxiter_50_N_v0.62.0-iter50-gpt5codex/output.jsonl',
        'output_dir': '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_gpt4o_iter50',
        'short_name': 'gpt4o-50'
    },
    {
        'name': 'GPT-4o (maxiter=10)',
        'input_file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-4o_maxiter_10_N_v0.62.0/output.jsonl',
        'output_dir': '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_gpt4o_iter10',
        'short_name': 'gpt4o-10'
    },
    {
        'name': 'GPT-5 (maxiter=50)',
        'input_file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-5_maxiter_50_N_v0.62.0-iter50-gpt5/output.jsonl',
        'output_dir': '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_gpt5_iter50',
        'short_name': 'gpt5-50'
    }
]

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    return records

def create_visualizations_for_model(config):
    """Create all visualizations for a single model"""
    print(f"\n{'='*60}")
    print(f"Processing: {config['name']}")
    print(f"{'='*60}")

    input_file = config['input_file']
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(exist_ok=True, parents=True)

    # Check if input file exists
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        return False

    print(f"📖 Loading data from: {input_file}")
    records = load_jsonl(input_file)
    print(f"   ✓ Loaded {len(records)} tasks")

    # Create simple results visualization
    print(f"\n📊 Creating results summary...")
    create_simple_summary(records, output_dir, config['name'])

    # Create trajectory visualization
    print(f"\n🎨 Creating trajectory visualization...")
    create_trajectory_viz(records, output_dir, config['name'])

    print(f"\n✅ Completed: {config['name']}")
    print(f"   Output directory: {output_dir}")

    return True

def create_simple_summary(records, output_dir, model_name):
    """Create simple summary HTML"""
    from datetime import datetime
    from collections import Counter
    import html as html_module

    # Calculate statistics
    total_tasks = len(records)
    successful_tasks = sum(1 for r in records if r['test_result']['success'] == 1)
    failed_tasks = total_tasks - successful_tasks
    success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Exit code distribution
    exit_codes = Counter(r['test_result']['eval_exit_code'] for r in records)

    # Sort records by instance_id
    data_sorted = sorted(records, key=lambda x: int(x['instance_id']) if x['instance_id'].isdigit() else x['instance_id'])

    html_content = f'''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{model_name} - ML-Bench Results</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background-color: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-card p {{
            margin: 0;
            font-size: 42px;
            font-weight: bold;
        }}
        .progress-bar {{
            width: 100%;
            height: 40px;
            background-color: #ecf0f1;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #2ecc71 0%, #27ae60 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }}
        .chart-container {{
            background-color: #f8f9fa;
            padding: 25px;
            margin: 20px 0;
            border-radius: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-success {{
            background-color: #d4edda;
            color: #155724;
        }}
        .badge-failure {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .ascii-chart {{
            font-family: 'Courier New', monospace;
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 {model_name} - ML-Bench Results</h1>

        <div class="summary-grid">
            <div class="stat-card">
                <h3>Total Tasks</h3>
                <p>{total_tasks}</p>
            </div>
            <div class="stat-card">
                <h3>Successful</h3>
                <p>{successful_tasks}</p>
            </div>
            <div class="stat-card">
                <h3>Failed</h3>
                <p>{failed_tasks}</p>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <p>{success_rate:.1f}%</p>
            </div>
        </div>

        <div class="chart-container">
            <h2>📊 Success Rate Visualization</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%;">
                    {success_rate:.1f}%
                </div>
            </div>
        </div>

        <div class="chart-container">
            <h2>🔢 Exit Code Distribution</h2>
            <div class="ascii-chart">
'''

    max_count = max(exit_codes.values()) if exit_codes else 1
    for code, count in sorted(exit_codes.items()):
        bar = '█' * int((count / max_count) * 40)
        percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
        html_content += f"Exit Code {code:3d}: {bar:<40} {count:3d} ({percentage:5.1f}%)\n"

    html_content += '''
            </div>
        </div>

        <div class="chart-container">
            <h2>📋 Task Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Instance ID</th>
                        <th>Status</th>
                        <th>Exit Code</th>
                    </tr>
                </thead>
                <tbody>
'''

    for record in data_sorted:
        status_class = "success" if record['test_result']['success'] == 1 else "failure"
        badge_class = "badge-success" if record['test_result']['success'] == 1 else "badge-failure"
        status_text = "✅ Success" if record['test_result']['success'] == 1 else "❌ Failed"
        html_content += f'''
                    <tr>
                        <td><strong>{record['instance_id']}</strong></td>
                        <td><span class="badge {badge_class}">{status_text}</span></td>
                        <td>{record['test_result']['eval_exit_code']}</td>
                    </tr>
'''

    html_content += f'''
                </tbody>
            </table>
        </div>

        <div style="text-align: center; margin-top: 40px; color: #6c757d;">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
'''

    with open(output_dir / 'report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"   ✓ Summary report created: {output_dir / 'report.html'}")

def create_trajectory_viz(records, output_dir, model_name):
    """Create trajectory visualization using the enhanced script"""
    # Import the enhanced visualization functions
    import sys
    sys.path.insert(0, '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench')

    # We'll create a simplified version inline
    print(f"   Creating enhanced trajectory HTML...")

    # Just copy the key parts from visualize_trajectory_enhanced.py
    # For simplicity, we'll call it as a subprocess with modified parameters

    # Create a custom script that imports and uses the functions
    script_content = f'''
import sys
sys.path.insert(0, '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench')
from visualize_trajectory_enhanced import create_enhanced_html, load_jsonl

input_file = "{records[0]['metadata']['eval_output_dir']}/../output.jsonl" if 'metadata' in records[0] and 'eval_output_dir' in records[0]['metadata'] else None
if not input_file:
    # Fallback: we already have records loaded
    pass

output_file = "{output_dir / 'trajectory_enhanced.html'}"
records_data = {records}

# Create the HTML directly with records
create_enhanced_html(records_data, output_file)
print(f"   ✓ Trajectory visualization created: {{output_file}}")
'''

    # For now, let's just create a placeholder message
    print(f"   ⏭️  Trajectory visualization will be created separately")
    print(f"   Run: python3 visualize_trajectory_enhanced.py with appropriate input file")

def main():
    print("🚀 Multi-Model ML-Bench Visualization")
    print("=" * 60)

    results = []
    for config in CONFIGS:
        success = create_visualizations_for_model(config)
        results.append((config['name'], success))

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")

    print("\n🎉 All visualizations completed!")
    print("\n📁 Output directories:")
    for config in CONFIGS:
        if Path(config['output_dir']).exists():
            print(f"   {config['name']}: {config['output_dir']}")

if __name__ == "__main__":
    main()
