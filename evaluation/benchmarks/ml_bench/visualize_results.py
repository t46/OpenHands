#!/usr/bin/env python3
"""
ML-Bench Results Visualization Script
Analyzes and visualizes output.jsonl from ML-Bench evaluation
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import numpy as np

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            records.append(json.loads(line.strip()))
    return records

def analyze_results(records):
    """Analyze results and create summary statistics"""
    df = pd.DataFrame([{
        'instance_id': r['instance_id'],
        'success': r['test_result']['success'],
        'exit_code': r['test_result']['eval_exit_code'],
        'max_iterations': r['metadata']['max_iterations'],
        'start_time': r['metadata']['start_time'],
        'agent_class': r['metadata']['agent_class'],
        'model': r['metadata']['llm_config']['model'],
    } for r in records])

    return df

def create_visualizations(df, output_dir):
    """Create multiple visualizations"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # 1. Success Rate Overview
    fig, ax = plt.subplots(figsize=(10, 6))
    success_counts = df['success'].value_counts()
    colors = ['#2ecc71' if x == 1 else '#e74c3c' for x in success_counts.index]
    ax.pie(success_counts.values, labels=['Success', 'Failure'], autopct='%1.1f%%',
           colors=colors, startangle=90, textprops={'fontsize': 14})
    ax.set_title('Overall Success Rate', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'success_rate.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Success by Instance ID
    fig, ax = plt.subplots(figsize=(16, 6))
    df_sorted = df.sort_values('instance_id')
    colors = ['#2ecc71' if x == 1 else '#e74c3c' for x in df_sorted['success']]
    ax.bar(range(len(df_sorted)), df_sorted['success'], color=colors, alpha=0.7)
    ax.set_xlabel('Instance Index', fontsize=12)
    ax.set_ylabel('Success (1=Pass, 0=Fail)', fontsize=12)
    ax.set_title('Success Rate by Task Instance', fontsize=14, fontweight='bold')
    ax.set_ylim(-0.1, 1.1)
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_dir / 'success_by_instance.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 3. Exit Code Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    exit_code_counts = df['exit_code'].value_counts().sort_index()
    colors_exit = ['#2ecc71' if x == 0 else '#e74c3c' for x in exit_code_counts.index]
    ax.bar(exit_code_counts.index.astype(str), exit_code_counts.values,
           color=colors_exit, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Exit Code', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Exit Code Distribution', fontsize=14, fontweight='bold')
    for i, (idx, val) in enumerate(zip(exit_code_counts.index, exit_code_counts.values)):
        ax.text(i, val + 0.5, str(val), ha='center', va='bottom', fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'exit_code_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()

    # 4. Timeline of Evaluations (if timestamps available)
    if 'start_time' in df.columns and df['start_time'].notna().any():
        fig, ax = plt.subplots(figsize=(14, 6))
        df['datetime'] = pd.to_datetime(df['start_time'])
        df_sorted_time = df.sort_values('datetime')
        colors = ['#2ecc71' if x == 1 else '#e74c3c' for x in df_sorted_time['success']]
        ax.scatter(df_sorted_time['datetime'], df_sorted_time.index,
                  c=colors, s=100, alpha=0.6, edgecolors='black')
        ax.set_xlabel('Evaluation Start Time', fontsize=12)
        ax.set_ylabel('Task Index', fontsize=12)
        ax.set_title('Evaluation Timeline', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'timeline.png', dpi=300, bbox_inches='tight')
        plt.close()

    # 5. Summary Statistics Table
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis('tight')
    ax.axis('off')

    total_tasks = len(df)
    successful_tasks = df['success'].sum()
    failed_tasks = total_tasks - successful_tasks
    success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0

    summary_data = [
        ['Metric', 'Value'],
        ['Total Tasks', f'{total_tasks}'],
        ['Successful Tasks', f'{successful_tasks}'],
        ['Failed Tasks', f'{failed_tasks}'],
        ['Success Rate', f'{success_rate:.2f}%'],
        ['Model', df['model'].iloc[0] if 'model' in df.columns else 'N/A'],
        ['Max Iterations', df['max_iterations'].iloc[0] if 'max_iterations' in df.columns else 'N/A'],
    ]

    table = ax.table(cellText=summary_data, cellLoc='left', loc='center',
                     colWidths=[0.4, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2)

    # Style header row
    for i in range(2):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Style data rows
    for i in range(1, len(summary_data)):
        for j in range(2):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#ecf0f1')

    ax.set_title('Summary Statistics', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / 'summary_stats.png', dpi=300, bbox_inches='tight')
    plt.close()

    return {
        'total_tasks': total_tasks,
        'successful_tasks': successful_tasks,
        'failed_tasks': failed_tasks,
        'success_rate': success_rate
    }

def create_html_report(df, stats, output_dir):
    """Create an HTML report with embedded images"""
    output_dir = Path(output_dir)

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
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
        }}
        .summary-box {{
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-card p {{
            margin: 0;
            font-size: 32px;
            font-weight: bold;
        }}
        .visualization {{
            background-color: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .visualization img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 14px;
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
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .failure {{
            color: #e74c3c;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>🤖 ML-Bench Evaluation Results</h1>

    <div class="summary-box">
        <h2>📊 Summary Statistics</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <h3>Total Tasks</h3>
                <p>{stats['total_tasks']}</p>
            </div>
            <div class="stat-card">
                <h3>Successful</h3>
                <p>{stats['successful_tasks']}</p>
            </div>
            <div class="stat-card">
                <h3>Failed</h3>
                <p>{stats['failed_tasks']}</p>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <p>{stats['success_rate']:.1f}%</p>
            </div>
        </div>
    </div>

    <div class="visualization">
        <h2>🎯 Overall Success Rate</h2>
        <img src="success_rate.png" alt="Success Rate">
    </div>

    <div class="visualization">
        <h2>📈 Success by Task Instance</h2>
        <img src="success_by_instance.png" alt="Success by Instance">
    </div>

    <div class="visualization">
        <h2>🔢 Exit Code Distribution</h2>
        <img src="exit_code_distribution.png" alt="Exit Code Distribution">
    </div>

    <div class="visualization">
        <h2>📋 Detailed Summary</h2>
        <img src="summary_stats.png" alt="Summary Statistics">
    </div>

    <div class="summary-box">
        <h2>📝 Task Results Table</h2>
        <table>
            <thead>
                <tr>
                    <th>Instance ID</th>
                    <th>Status</th>
                    <th>Exit Code</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add table rows
    for _, row in df.sort_values('instance_id').iterrows():
        status_class = "success" if row['success'] == 1 else "failure"
        status_text = "✅ Success" if row['success'] == 1 else "❌ Failed"
        html_content += f"""
                <tr>
                    <td>{row['instance_id']}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{row['exit_code']}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
    </div>

    <div class="footer">
        <p>Generated on """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
        <p>ML-Bench Evaluation - GPT-5 Model (Max Iterations: 50)</p>
    </div>
</body>
</html>
"""

    with open(output_dir / 'report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # File paths
    input_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-5_maxiter_50_N_v0.62.0-iter50-gpt5/output.jsonl"
    output_dir = "/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations"

    print("Loading data...")
    records = load_jsonl(input_file)
    print(f"Loaded {len(records)} records")

    print("Analyzing results...")
    df = analyze_results(records)

    print("Creating visualizations...")
    stats = create_visualizations(df, output_dir)

    print("Generating HTML report...")
    create_html_report(df, stats, output_dir)

    print(f"\n✅ Visualization complete!")
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Report: {output_dir}/report.html")
    print(f"\n📈 Summary:")
    print(f"  Total Tasks: {stats['total_tasks']}")
    print(f"  Successful: {stats['successful_tasks']}")
    print(f"  Failed: {stats['failed_tasks']}")
    print(f"  Success Rate: {stats['success_rate']:.2f}%")

if __name__ == "__main__":
    main()
