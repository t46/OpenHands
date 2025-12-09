#!/usr/bin/env python3
"""
ML-Bench Trajectory Visualization for claude_sonnet_20251204
Creates a structured, easy-to-read HTML report from output.jsonl
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import html

def load_jsonl(file_path):
    """Load JSONL file and return list of records"""
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    return records

def format_tool(tool):
    """Format a tool definition as structured HTML"""
    if not isinstance(tool, dict):
        return html.escape(str(tool))

    tool_type = tool.get('type', 'unknown')
    function_data = tool.get('function', {})

    tool_html = f'''
    <div class="tool-card">
        <div class="tool-header">
            <span class="tool-badge">{html.escape(tool_type)}</span>
            <strong>{html.escape(function_data.get('name', 'Unnamed Tool'))}</strong>
        </div>
        <div class="tool-body">
            <div class="tool-description">
                {html.escape(function_data.get('description', 'No description')[:200])}...
            </div>
        </div>
    </div>
    '''
    return tool_html

def format_json_value(value, max_length=500):
    """Format a JSON value for display"""
    if value is None:
        return '<span class="json-null">null</span>'
    elif isinstance(value, bool):
        return f'<span class="json-bool">{str(value).lower()}</span>'
    elif isinstance(value, (int, float)):
        return f'<span class="json-number">{value}</span>'
    elif isinstance(value, str):
        escaped = html.escape(value)
        if len(escaped) > max_length:
            short = escaped[:max_length]
            full = escaped
            return f'''
            <span class="json-string expandable-text">
                <span class="text-short">"{short}..."</span>
                <span class="text-full" style="display:none;">"{full}"</span>
                <button class="expand-btn" onclick="toggleText(this)">Show more</button>
            </span>
            '''
        return f'<span class="json-string">"{escaped}"</span>'
    elif isinstance(value, list):
        if len(value) == 0:
            return '<span class="json-array">[]</span>'
        if all(isinstance(item, dict) and 'type' in item and 'function' in item for item in value):
            # This is a tools array
            tools_html = '<div class="tools-list">'
            for i, tool in enumerate(value):
                tools_html += format_tool(tool)
            tools_html += '</div>'
            return f'<details class="json-array-details"><summary>{len(value)} tools available (click to expand)</summary>{tools_html}</details>'
        else:
            items = ', '.join(format_json_value(item, 100) for item in value[:5])
            if len(value) > 5:
                items += f', ... ({len(value) - 5} more)'
            return f'<span class="json-array">[{items}]</span>'
    elif isinstance(value, dict):
        if len(value) == 0:
            return '<span class="json-object">{{}}</span>'
        items_html = '<div class="json-object-items">'
        for k, v in list(value.items())[:10]:
            items_html += f'<div class="json-item"><span class="json-key">{html.escape(str(k))}:</span> {format_json_value(v, 200)}</div>'
        if len(value) > 10:
            items_html += f'<div class="json-item">... {len(value) - 10} more fields</div>'
        items_html += '</div>'
        return f'<details class="json-object-details"><summary>Object with {len(value)} fields</summary>{items_html}</details>'
    else:
        return html.escape(str(value))

def get_message_icon(msg_type):
    """Get icon for message type"""
    icons = {
        'system': '⚙️',
        'user': '👤',
        'agent': '🤖',
        'read': '📖',
        'write': '✍️',
        'run': '▶️',
        'finish': '✅',
        'think': '💭',
        'browser': '🌐',
        'unknown': '❓'
    }
    return icons.get(msg_type, '📝')

def get_message_color(msg_type):
    """Get color for message type"""
    colors = {
        'system': '#6c757d',
        'user': '#007bff',
        'agent': '#28a745',
        'read': '#17a2b8',
        'write': '#ffc107',
        'run': '#fd7e14',
        'finish': '#28a745',
        'think': '#6f42c1',
        'browser': '#20c997',
        'unknown': '#6c757d'
    }
    return colors.get(msg_type, '#6c757d')

def create_enhanced_html(records, output_path, title="Claude Sonnet 20251204"):
    """Create enhanced HTML visualization"""

    html_content = f'''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ML-Bench: {title} - Trajectory Results</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f8f9fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card h3 {{
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}

        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}

        .controls {{
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .controls button {{
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}

        .controls button:hover {{
            background: #5568d3;
            transform: translateY(-2px);
        }}

        .task {{
            background: white;
            margin-bottom: 20px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }}

        .task:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .task-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s;
        }}

        .task-header:hover {{
            background: linear-gradient(135deg, #5568d3 0%, #6a3f8f 100%);
        }}

        .task-header h2 {{
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .task-status {{
            display: flex;
            gap: 15px;
            align-items: center;
        }}

        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            background: rgba(255,255,255,0.2);
        }}

        .status-badge.success {{
            background: #28a745;
        }}

        .status-badge.failure {{
            background: #dc3545;
        }}

        .expand-icon {{
            font-size: 24px;
            transition: transform 0.3s;
        }}

        .expand-icon.expanded {{
            transform: rotate(180deg);
        }}

        .task-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease-out;
        }}

        .task-content.expanded {{
            max-height: 50000px;
            transition: max-height 1s ease-in;
        }}

        .task-body {{
            padding: 20px;
        }}

        .section {{
            margin-bottom: 30px;
        }}

        .section h3 {{
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e9ecef;
            font-size: 16px;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .metadata-item {{
            background: #f8f9fa;
            padding: 12px 15px;
            border-radius: 6px;
            border-left: 3px solid #667eea;
        }}

        .metadata-item strong {{
            color: #495057;
            display: block;
            margin-bottom: 4px;
            font-size: 12px;
            text-transform: uppercase;
        }}

        .history-container {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .message {{
            background: #f8f9fa;
            border-radius: 8px;
            overflow: hidden;
            border-left: 4px solid #6c757d;
            transition: all 0.3s;
        }}

        .message:hover {{
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }}

        .message-header {{
            padding: 12px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
        }}

        .message-type {{
            font-weight: bold;
            font-size: 14px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}

        .message-time {{
            font-size: 11px;
            color: #6c757d;
            font-family: 'Courier New', monospace;
        }}

        .message-body {{
            padding: 15px;
        }}

        .message-field {{
            margin-bottom: 12px;
        }}

        .message-field strong {{
            color: #495057;
            font-size: 12px;
            text-transform: uppercase;
            display: block;
            margin-bottom: 6px;
        }}

        .message-field-content {{
            background: white;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.5;
            overflow-x: auto;
        }}

        .tools-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}

        .tool-card {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
            transition: all 0.3s;
        }}

        .tool-card:hover {{
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
        }}

        .tool-header {{
            background: #f8f9fa;
            padding: 10px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .tool-badge {{
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            text-transform: uppercase;
        }}

        .tool-body {{
            padding: 10px;
        }}

        .tool-description {{
            font-size: 12px;
            color: #6c757d;
            line-height: 1.4;
        }}

        .json-key {{
            color: #0066cc;
            font-weight: bold;
        }}

        .json-string {{
            color: #008000;
        }}

        .json-number {{
            color: #ff6600;
        }}

        .json-bool {{
            color: #0000ff;
        }}

        .json-null {{
            color: #999;
            font-style: italic;
        }}

        .json-object-details, .json-array-details {{
            margin: 5px 0;
        }}

        .json-object-details summary, .json-array-details summary {{
            cursor: pointer;
            padding: 5px;
            background: #f8f9fa;
            border-radius: 3px;
            font-weight: bold;
            color: #495057;
        }}

        .json-object-details summary:hover, .json-array-details summary:hover {{
            background: #e9ecef;
        }}

        .json-object-items {{
            margin-left: 20px;
            margin-top: 10px;
        }}

        .json-item {{
            padding: 5px 0;
            border-bottom: 1px solid #f8f9fa;
        }}

        .expandable-text {{
            position: relative;
        }}

        .expand-btn {{
            margin-left: 10px;
            padding: 2px 8px;
            font-size: 10px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }}

        .expand-btn:hover {{
            background: #5568d3;
        }}

        pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .timeline-view {{
            position: relative;
            padding-left: 40px;
        }}

        .timeline-view::before {{
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #dee2e6;
        }}

        .timeline-message {{
            position: relative;
            margin-bottom: 15px;
        }}

        .timeline-message::before {{
            content: '';
            position: absolute;
            left: -29px;
            top: 10px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: white;
            border: 3px solid;
            z-index: 1;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 14px;
            margin-top: 40px;
        }}
    </style>
    <script>
        function toggleTask(taskId) {{
            const content = document.getElementById('task-' + taskId);
            const icon = document.getElementById('icon-' + taskId);
            content.classList.toggle('expanded');
            icon.classList.toggle('expanded');
        }}

        function expandAll() {{
            document.querySelectorAll('.task-content').forEach(el => el.classList.add('expanded'));
            document.querySelectorAll('.expand-icon').forEach(el => el.classList.add('expanded'));
        }}

        function collapseAll() {{
            document.querySelectorAll('.task-content').forEach(el => el.classList.remove('expanded'));
            document.querySelectorAll('.expand-icon').forEach(el => el.classList.remove('expanded'));
        }}

        function toggleText(btn) {{
            const parent = btn.parentElement;
            const shortText = parent.querySelector('.text-short');
            const fullText = parent.querySelector('.text-full');

            if (fullText.style.display === 'none') {{
                shortText.style.display = 'none';
                fullText.style.display = 'inline';
                btn.textContent = 'Show less';
            }} else {{
                shortText.style.display = 'inline';
                fullText.style.display = 'none';
                btn.textContent = 'Show more';
            }}
        }}

        function filterByStatus(status) {{
            const tasks = document.querySelectorAll('.task');
            tasks.forEach(task => {{
                if (status === 'all') {{
                    task.style.display = 'block';
                }} else if (status === 'success') {{
                    task.style.display = task.querySelector('.status-badge.success') ? 'block' : 'none';
                }} else if (status === 'failure') {{
                    task.style.display = task.querySelector('.status-badge.failure') ? 'block' : 'none';
                }}
            }});
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>🤖 ML-Bench: {title} - Trajectory Results</h1>
'''

    # Calculate summary statistics
    total_tasks = len(records)
    success_count = sum(1 for r in records if r['test_result']['success'] == 1)
    failure_count = total_tasks - success_count
    success_rate = (success_count / total_tasks * 100) if total_tasks > 0 else 0

    # Exit code distribution
    exit_codes = defaultdict(int)
    for r in records:
        exit_codes[r['test_result']['eval_exit_code']] += 1

    html_content += f'''
        <div class="summary-stats">
            <div class="stat-card">
                <h3>Total Tasks</h3>
                <div class="value">{total_tasks}</div>
            </div>
            <div class="stat-card">
                <h3>Success</h3>
                <div class="value" style="color: #28a745;">{success_count}</div>
            </div>
            <div class="stat-card">
                <h3>Failure</h3>
                <div class="value" style="color: #dc3545;">{failure_count}</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div class="value">{success_rate:.1f}%</div>
            </div>
        </div>

        <div class="controls">
            <button onclick="expandAll()">📖 Expand All</button>
            <button onclick="collapseAll()">📕 Collapse All</button>
            <button onclick="filterByStatus('all')">🔘 Show All</button>
            <button onclick="filterByStatus('success')">✅ Success Only</button>
            <button onclick="filterByStatus('failure')">❌ Failures Only</button>
        </div>
'''

    # Process each task
    for idx, record in enumerate(records, 1):
        instance_id = record['instance_id']
        test_result = record['test_result']
        success = test_result['success']
        exit_code = test_result['eval_exit_code']
        history = record.get('history', [])
        metadata = record.get('metadata', {})

        status_class = 'success' if success == 1 else 'failure'
        status_text = '✅ Success' if success == 1 else '❌ Failed'
        status_icon = '✅' if success == 1 else '❌'

        html_content += f'''
        <div class="task">
            <div class="task-header" onclick="toggleTask({idx})">
                <h2>
                    {status_icon} Task #{idx} - Instance ID: {instance_id}
                </h2>
                <div class="task-status">
                    <span class="status-badge {status_class}">{status_text}</span>
                    <span class="status-badge">Exit: {exit_code}</span>
                    <span class="status-badge">{len(history)} Messages</span>
                    <span class="expand-icon" id="icon-{idx}">▼</span>
                </div>
            </div>
            <div class="task-content" id="task-{idx}">
                <div class="task-body">
'''

        # Instruction
        if 'instruction' in record:
            instruction = record['instruction'][:500]
            html_content += f'''
                    <div class="section">
                        <h3>📝 Task Instruction</h3>
                        <div class="metadata-item">
                            {html.escape(instruction)}...
                        </div>
                    </div>
'''

        # Test Result
        html_content += f'''
                    <div class="section">
                        <h3>📊 Test Result</h3>
                        <div class="metadata-grid">
                            <div class="metadata-item">
                                <strong>Exit Code</strong>
                                {exit_code}
                            </div>
                            <div class="metadata-item">
                                <strong>Success</strong>
                                {success}
                            </div>
                        </div>
                    </div>
'''

        # Metadata
        html_content += '''
                    <div class="section">
                        <h3>⚙️ Metadata</h3>
                        <div class="metadata-grid">
'''

        llm_config = metadata.get('llm_config', {})
        html_content += f'''
                            <div class="metadata-item">
                                <strong>Model</strong>
                                {html.escape(str(llm_config.get('model', 'N/A')))}
                            </div>
                            <div class="metadata-item">
                                <strong>Max Iterations</strong>
                                {metadata.get('max_iterations', 'N/A')}
                            </div>
                            <div class="metadata-item">
                                <strong>Start Time</strong>
                                {metadata.get('start_time', 'N/A')}
                            </div>
                            <div class="metadata-item">
                                <strong>Agent Class</strong>
                                {metadata.get('agent_class', 'N/A')}
                            </div>
'''

        html_content += '''
                        </div>
                    </div>
'''

        # Conversation History with Timeline
        html_content += '''
                    <div class="section">
                        <h3>💬 Conversation History</h3>
                        <div class="history-container timeline-view">
'''

        for msg_idx, msg in enumerate(history):
            if not isinstance(msg, list) or len(msg) < 2:
                continue

            msg_data = msg[1]
            msg_type = msg_data.get('source', 'unknown')
            timestamp = msg_data.get('timestamp', '')

            icon = get_message_icon(msg_type)
            color = get_message_color(msg_type)

            html_content += f'''
                            <div class="timeline-message">
                                <div class="message" style="border-left-color: {color};">
                                    <div class="message-header">
                                        <span class="message-type" style="color: {color};">
                                            {icon} {html.escape(msg_type.upper())}
                                        </span>
                                        <span class="message-time">{html.escape(str(timestamp))}</span>
                                    </div>
                                    <div class="message-body">
'''

            # Format each field in the message
            for key, value in msg_data.items():
                if key in ['id', 'timestamp', 'source']:
                    continue

                html_content += f'''
                                        <div class="message-field">
                                            <strong>{html.escape(str(key))}</strong>
                                            <div class="message-field-content">
                                                {format_json_value(value)}
                                            </div>
                                        </div>
'''

            html_content += '''
                                    </div>
                                </div>
                            </div>
'''

        html_content += '''
                        </div>
                    </div>
'''

        html_content += '''
                </div>
            </div>
        </div>
'''

    html_content += f'''
        <div class="footer">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>ML-Bench Trajectory Visualization - {title}</p>
            <p>Success Rate: {success_rate:.1f}% ({success_count}/{total_tasks} tasks)</p>
        </div>
    </div>
</body>
</html>
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_path

def main():
    input_file = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/claude-sonnet-4-5-20250929_maxiter_100_N_claude_sonnet_20251204/output.jsonl"
    output_file = "/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/trajectory_claude_sonnet_20251204.html"

    print("📖 Loading trajectory data...")
    records = load_jsonl(input_file)
    print(f"   Loaded {len(records)} tasks")

    print("\n🎨 Creating enhanced visualization...")
    output_path = create_enhanced_html(records, output_file, title="Claude Sonnet 20251204 (インストラクション修正後)")
    print(f"   ✓ HTML created: {output_path}")

    # Calculate summary
    success_count = sum(1 for r in records if r['test_result']['success'] == 1)
    success_rate = (success_count / len(records) * 100) if len(records) > 0 else 0

    print("\n✅ Done!")
    print(f"\n📊 Summary:")
    print(f"   Total: {len(records)} tasks")
    print(f"   Success: {success_count} ({success_rate:.1f}%)")
    print(f"   Failure: {len(records) - success_count}")
    print(f"\n🌐 Open in browser: file://{output_path}")

if __name__ == "__main__":
    main()
