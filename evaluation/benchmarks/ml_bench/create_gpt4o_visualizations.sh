#!/bin/bash
# Create visualizations for GPT-4o results

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Creating GPT-4o Visualizations"
echo "=================================="
echo ""

# GPT-4o maxiter=50
echo "📊 Processing GPT-4o (maxiter=50)..."
python3 <<'EOF'
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import html as html_module

# Configuration
INPUT_FILE = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-4o_maxiter_50_N_v0.62.0-iter50-gpt5codex/output.jsonl"
OUTPUT_DIR = Path("/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_gpt4o_iter50")
MODEL_NAME = "GPT-4o (maxiter=50)"

# Import visualization functions
sys.path.insert(0, '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench')
from visualize_results_simple import load_jsonl, analyze_results, create_html_report, create_text_summary
from visualize_trajectory_enhanced import create_enhanced_html

print(f"📖 Loading data from: {INPUT_FILE}")
records = load_jsonl(INPUT_FILE)
print(f"   ✓ Loaded {len(records)} tasks")

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Create results summary
print("📊 Creating results summary...")
data = analyze_results(records)
report_path, stats = create_html_report(data, OUTPUT_DIR)
summary_path = create_text_summary(data, OUTPUT_DIR)

print(f"   ✓ Report: {report_path}")
print(f"   ✓ Summary: {summary_path}")
print(f"   Success Rate: {stats['success_rate']:.2f}%")

# Create trajectory visualization
print("🎨 Creating trajectory visualization...")
trajectory_path = OUTPUT_DIR / "trajectory_enhanced.html"
create_enhanced_html(records, trajectory_path)
print(f"   ✓ Trajectory: {trajectory_path}")

print(f"\n✅ GPT-4o (maxiter=50) completed!")
print(f"📁 Output: {OUTPUT_DIR}")
EOF

echo ""
echo "=================================="
echo ""

# GPT-4o maxiter=10
echo "📊 Processing GPT-4o (maxiter=10)..."
python3 <<'EOF'
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# Configuration
INPUT_FILE = "/mnt/home/t46/OpenHands/evaluation/evaluation_outputs/outputs/ml-bench-quarter/CodeActAgent/gpt-4o_maxiter_10_N_v0.62.0/output.jsonl"
OUTPUT_DIR = Path("/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench/visualizations_gpt4o_iter10")
MODEL_NAME = "GPT-4o (maxiter=10)"

# Import visualization functions
sys.path.insert(0, '/mnt/home/t46/OpenHands/evaluation/benchmarks/ml_bench')
from visualize_results_simple import load_jsonl, analyze_results, create_html_report, create_text_summary
from visualize_trajectory_enhanced import create_enhanced_html

print(f"📖 Loading data from: {INPUT_FILE}")
records = load_jsonl(INPUT_FILE)
print(f"   ✓ Loaded {len(records)} tasks")

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Create results summary
print("📊 Creating results summary...")
data = analyze_results(records)
report_path, stats = create_html_report(data, OUTPUT_DIR)
summary_path = create_text_summary(data, OUTPUT_DIR)

print(f"   ✓ Report: {report_path}")
print(f"   ✓ Summary: {summary_path}")
print(f"   Success Rate: {stats['success_rate']:.2f}%")

# Create trajectory visualization
print("🎨 Creating trajectory visualization...")
trajectory_path = OUTPUT_DIR / "trajectory_enhanced.html"
create_enhanced_html(records, trajectory_path)
print(f"   ✓ Trajectory: {trajectory_path}")

print(f"\n✅ GPT-4o (maxiter=10) completed!")
print(f"📁 Output: {OUTPUT_DIR}")
EOF

echo ""
echo "=================================="
echo "🎉 All GPT-4o visualizations completed!"
echo ""
echo "📁 Output directories:"
echo "   GPT-4o (maxiter=50): visualizations_gpt4o_iter50/"
echo "   GPT-4o (maxiter=10):  visualizations_gpt4o_iter10/"
echo ""
