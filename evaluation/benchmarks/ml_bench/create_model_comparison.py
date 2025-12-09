#!/usr/bin/env python3
"""
Create a comparison page for all models
"""

import json
from pathlib import Path
from datetime import datetime

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    return records

def calculate_stats(records):
    """Calculate statistics from records"""
    total = len(records)
    successes = sum(1 for r in records if r['test_result']['success'] == 1)
    failures = total - successes
    success_rate = (successes / total * 100) if total > 0 else 0

    return {
        'total': total,
        'successes': successes,
        'failures': failures,
        'success_rate': success_rate
    }

def main():
    models = [
        {
            'name': 'Claude Sonnet 4.5',
            'iterations': 100,
            'file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_v0.62.0/output.jsonl',
            'viz_dir': 'visualizations_claude_sonnet_iter100'
        },
        {
            'name': 'GPT-4o',
            'iterations': 50,
            'file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-4o_maxiter_50_N_v0.62.0-iter50-gpt5codex/output.jsonl',
            'viz_dir': 'visualizations_gpt4o_iter50'
        },
        {
            'name': 'GPT-5',
            'iterations': 50,
            'file': '/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-5_maxiter_50_N_v0.62.0-iter50-gpt5/output.jsonl',
            'viz_dir': 'visualizations_gpt5_iter50'
        }
    ]

    # Load and calculate stats for each model
    model_stats = []
    for model in models:
        if Path(model['file']).exists():
            records = load_jsonl(model['file'])
            stats = calculate_stats(records)
            model_stats.append({
                'name': model['name'],
                'iterations': model['iterations'],
                'viz_dir': model['viz_dir'],
                **stats
            })

    # Sort by success rate descending
    model_stats.sort(key=lambda x: x['success_rate'], reverse=True)

    # Create HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ML-Bench Model Comparison</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .model-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 5px solid;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .model-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .model-card.rank-1 {{
            border-left-color: #ffd700;
            background: linear-gradient(135deg, #fff9e6 0%, #ffffff 100%);
        }}

        .model-card.rank-2 {{
            border-left-color: #c0c0c0;
        }}

        .model-card.rank-3 {{
            border-left-color: #cd7f32;
        }}

        .model-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .model-name {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .rank-badge {{
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }}

        .rank-badge.gold {{
            background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
            color: #333;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}

        .stat-box {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 5px;
        }}

        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .stat-value.success {{
            color: #28a745;
        }}

        .success-bar {{
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }}

        .success-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }}

        .links {{
            margin-top: 15px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .link-btn {{
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9em;
            transition: background 0.2s;
        }}

        .link-btn:hover {{
            background: #5568d3;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            border-top: 1px solid #e9ecef;
        }}

        .comparison-table {{
            margin-top: 40px;
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}

        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏆 ML-Bench Model Comparison</h1>
            <p>Performance comparison across different language models</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <h2 style="margin-bottom: 20px;">Model Rankings</h2>
'''

    for i, stats in enumerate(model_stats, 1):
        rank_class = f"rank-{i}" if i <= 3 else ""
        rank_badge_class = "gold" if i == 1 else ""

        html += f'''
            <div class="model-card {rank_class}">
                <div class="model-header">
                    <div class="model-name">#{i} {stats['name']}</div>
                    <div class="rank-badge {rank_badge_class}">
                        {'🥇 ' if i == 1 else '🥈 ' if i == 2 else '🥉 ' if i == 3 else ''}
                        Rank {i}
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-label">Success Rate</div>
                        <div class="stat-value success">{stats['success_rate']:.1f}%</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Successes</div>
                        <div class="stat-value">{stats['successes']}/{stats['total']}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Failures</div>
                        <div class="stat-value">{stats['failures']}</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-label">Max Iterations</div>
                        <div class="stat-value">{stats['iterations']}</div>
                    </div>
                </div>

                <div class="success-bar">
                    <div class="success-fill" style="width: {stats['success_rate']:.1f}%">
                        {stats['success_rate']:.1f}%
                    </div>
                </div>

                <div class="links">
                    <a href="{stats['viz_dir']}/report.html" class="link-btn">📊 View Report</a>
                </div>
            </div>
'''

    # Comparison table
    html += '''
            <div class="comparison-table">
                <h2 style="margin-bottom: 20px;">Detailed Comparison</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Model</th>
                            <th>Success Rate</th>
                            <th>Successes</th>
                            <th>Failures</th>
                            <th>Total</th>
                            <th>Max Iterations</th>
                        </tr>
                    </thead>
                    <tbody>
'''

    for i, stats in enumerate(model_stats, 1):
        html += f'''
                        <tr>
                            <td><strong>#{i}</strong></td>
                            <td><strong>{stats['name']}</strong></td>
                            <td><strong style="color: #28a745;">{stats['success_rate']:.1f}%</strong></td>
                            <td>{stats['successes']}</td>
                            <td>{stats['failures']}</td>
                            <td>{stats['total']}</td>
                            <td>{stats['iterations']}</td>
                        </tr>
'''

    html += '''
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <p>ML-Bench Evaluation Results</p>
            <p>Dataset: ml-bench-quarter (68 instances)</p>
        </div>
    </div>
</body>
</html>
'''

    output_file = Path('/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/model_comparison.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Model comparison page created: {output_file}")
    print(f"\n📊 Rankings:")
    for i, stats in enumerate(model_stats, 1):
        print(f"   #{i} {stats['name']}: {stats['success_rate']:.1f}% ({stats['successes']}/{stats['total']})")

if __name__ == "__main__":
    main()
