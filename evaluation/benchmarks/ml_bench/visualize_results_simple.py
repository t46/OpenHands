#!/usr/bin/env python3
"""
ML-Bench Results Visualization Script (Simple version - no external dependencies)
Analyzes and visualizes output.jsonl from ML-Bench evaluation
"""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    return records

def analyze_results(records):
    """Analyze results and create summary statistics"""
    data = []
    for r in records:
        data.append({
            'instance_id': r['instance_id'],
            'success': r['test_result']['success'],
            'exit_code': r['test_result']['eval_exit_code'],
            'max_iterations': r['metadata']['max_iterations'],
            'start_time': r['metadata']['start_time'],
            'agent_class': r['metadata']['agent_class'],
            'model': r['metadata']['llm_config']['model'],
            'eval_output': r['test_result'].get('eval_output', '')[:200],  # First 200 chars
        })
    return data

def create_html_report(data, output_dir):
    """Create an HTML report with analysis"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Calculate statistics
    total_tasks = len(data)
    successful_tasks = sum(1 for d in data if d['success'] == 1)
    failed_tasks = total_tasks - successful_tasks
    success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Sort data by instance_id
    data_sorted = sorted(data, key=lambda x: int(x['instance_id']) if x['instance_id'].isdigit() else x['instance_id'])

    # Exit code statistics
    exit_codes = Counter(d['exit_code'] for d in data)

    # Calculate bar chart dimensions for ASCII art
    def create_ascii_bar(value, max_value, width=50):
        if max_value == 0:
            return ''
        filled = int((value / max_value) * width)
        return '█' * filled + '░' * (width - filled)

    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ML-Bench Evaluation Results</title>
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
        h2 {{
            color: #34495e;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
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
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .stat-card p {{
            margin: 0;
            font-size: 42px;
            font-weight: bold;
        }}
        .chart-container {{
            background-color: #f8f9fa;
            padding: 25px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .progress-bar {{
            width: 100%;
            height: 40px;
            background-color: #ecf0f1;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
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
            transition: width 1s ease;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-radius: 10px;
            overflow: hidden;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .failure {{
            color: #e74c3c;
            font-weight: bold;
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
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .ascii-chart {{
            font-family: 'Courier New', monospace;
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            overflow-x: auto;
            line-height: 1.5;
        }}
        .metric-box {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 ML-Bench Evaluation Results</h1>

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
            <p style="text-align: center; color: #7f8c8d; margin-top: 10px;">
                {successful_tasks} out of {total_tasks} tasks completed successfully
            </p>
        </div>

        <div class="chart-container">
            <h2>🔢 Exit Code Distribution</h2>
            <div class="ascii-chart">
"""

    # Add exit code distribution
    max_count = max(exit_codes.values()) if exit_codes else 1
    for code, count in sorted(exit_codes.items()):
        bar = create_ascii_bar(count, max_count, 40)
        percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
        html_content += f"Exit Code {code:3d}: {bar} {count:3d} ({percentage:5.1f}%)\n"

    html_content += f"""
            </div>
        </div>

        <div class="chart-container">
            <h2>📈 Task Success Distribution</h2>
            <div class="ascii-chart">
"""

    # Create ASCII chart for success by instance
    for i, d in enumerate(data_sorted):
        status = '✓' if d['success'] == 1 else '✗'
        color = '#2ecc71' if d['success'] == 1 else '#e74c3c'
        bar_char = '█' if d['success'] == 1 else '░'
        html_content += f"Task {d['instance_id']:>4s}: {bar_char * 50} {status}\n"
        if (i + 1) % 10 == 0:
            html_content += "\n"

    html_content += """
            </div>
        </div>

        <div class="chart-container">
            <h2>📋 Detailed Task Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Instance ID</th>
                        <th>Status</th>
                        <th>Exit Code</th>
                        <th>Output Preview</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add table rows
    for d in data_sorted:
        status_class = "success" if d['success'] == 1 else "failure"
        badge_class = "badge-success" if d['success'] == 1 else "badge-failure"
        status_text = "✅ Success" if d['success'] == 1 else "❌ Failed"
        output_preview = d['eval_output'].replace('\n', ' ')[:100] + ('...' if len(d['eval_output']) > 100 else '')
        html_content += f"""
                    <tr>
                        <td><strong>{d['instance_id']}</strong></td>
                        <td><span class="badge {badge_class}">{status_text}</span></td>
                        <td>{d['exit_code']}</td>
                        <td style="font-size: 11px; color: #7f8c8d;">{output_preview}</td>
                    </tr>
"""

    html_content += f"""
                </tbody>
            </table>
        </div>

        <div class="chart-container">
            <h2>ℹ️ Evaluation Metadata</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                <div class="metric-box">
                    <strong>Model:</strong> {data[0]['model'] if data else 'N/A'}
                </div>
                <div class="metric-box">
                    <strong>Max Iterations:</strong> {data[0]['max_iterations'] if data else 'N/A'}
                </div>
                <div class="metric-box">
                    <strong>Agent Class:</strong> {data[0]['agent_class'] if data else 'N/A'}
                </div>
                <div class="metric-box">
                    <strong>Start Time:</strong> {data[0]['start_time'] if data else 'N/A'}
                </div>
            </div>
        </div>

        <div class="footer">
            <p><strong>Generated on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>ML-Bench Evaluation Report - GPT-5 Model</p>
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    report_path = output_dir / 'report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return report_path, {
        'total_tasks': total_tasks,
        'successful_tasks': successful_tasks,
        'failed_tasks': failed_tasks,
        'success_rate': success_rate,
        'exit_codes': dict(exit_codes)
    }

def create_text_summary(data, output_dir):
    """Create a text summary file"""
    output_dir = Path(output_dir)

    total_tasks = len(data)
    successful_tasks = sum(1 for d in data if d['success'] == 1)
    failed_tasks = total_tasks - successful_tasks
    success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

    exit_codes = Counter(d['exit_code'] for d in data)

    summary = f"""
╔════════════════════════════════════════════════════════════════╗
║         ML-Bench Evaluation Results Summary                    ║
╚════════════════════════════════════════════════════════════════╝

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 OVERALL STATISTICS
{'─' * 60}
  Total Tasks:        {total_tasks}
  Successful Tasks:   {successful_tasks} ✓
  Failed Tasks:       {failed_tasks} ✗
  Success Rate:       {success_rate:.2f}%

🔢 EXIT CODE DISTRIBUTION
{'─' * 60}
"""

    for code, count in sorted(exit_codes.items()):
        percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
        bar = '█' * int(percentage / 2)
        summary += f"  Exit Code {code:3d}: {bar:<50} {count:3d} ({percentage:5.1f}%)\n"

    summary += f"""
📋 TASK RESULTS
{'─' * 60}
"""

    data_sorted = sorted(data, key=lambda x: int(x['instance_id']) if x['instance_id'].isdigit() else x['instance_id'])

    for d in data_sorted:
        status = '✓ PASS' if d['success'] == 1 else '✗ FAIL'
        summary += f"  Task {d['instance_id']:>4s}: {status} (Exit: {d['exit_code']})\n"

    summary += f"""
{'─' * 60}
ℹ️  METADATA
{'─' * 60}
  Model:            {data[0]['model'] if data else 'N/A'}
  Max Iterations:   {data[0]['max_iterations'] if data else 'N/A'}
  Agent Class:      {data[0]['agent_class'] if data else 'N/A'}
  Start Time:       {data[0]['start_time'] if data else 'N/A'}
"""

    summary_path = output_dir / 'summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)

    return summary_path

def main():
    # File paths
    input_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-5_maxiter_50_N_v0.62.0-iter50-gpt5/output.jsonl"
    output_dir = "/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations"

    print("📖 Loading data...")
    records = load_jsonl(input_file)
    print(f"   Loaded {len(records)} records")

    print("\n📊 Analyzing results...")
    data = analyze_results(records)

    print("\n🌐 Generating HTML report...")
    report_path, stats = create_html_report(data, output_dir)
    print(f"   ✓ HTML report created: {report_path}")

    print("\n📝 Creating text summary...")
    summary_path = create_text_summary(data, output_dir)
    print(f"   ✓ Text summary created: {summary_path}")

    print("\n" + "=" * 60)
    print("✅ VISUALIZATION COMPLETE!")
    print("=" * 60)
    print(f"\n📁 Output Directory: {output_dir}")
    print(f"🌐 HTML Report:      {report_path}")
    print(f"📄 Text Summary:     {summary_path}")
    print("\n📈 Quick Summary:")
    print(f"   Total Tasks:      {stats['total_tasks']}")
    print(f"   Successful:       {stats['successful_tasks']} ✓")
    print(f"   Failed:           {stats['failed_tasks']} ✗")
    print(f"   Success Rate:     {stats['success_rate']:.2f}%")
    print("\n💡 Open report.html in your browser to view the full report!")

if __name__ == "__main__":
    main()
