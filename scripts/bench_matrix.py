#!/usr/bin/env python3
"""
Matrix benchmark script for Holo 1.5 API across different HOLO_MAX_SIDE values.
Tests performance impact of different image resolution settings.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark Holo 1.5 API across HOLO_MAX_SIDE values",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--server", default="http://127.0.0.1:8000",
                        help="Server base URL")
    parser.add_argument("--image", required=True,
                        help="Path to image file for testing")
    parser.add_argument("--prompt", default="What do you see in this image?",
                        help="Text prompt")
    parser.add_argument("--runs", type=int, default=10,
                        help="Number of runs per configuration")
    parser.add_argument("--max-sides", default="720,1080,1440",
                        help="Comma-separated list of HOLO_MAX_SIDE values")
    parser.add_argument("--csv", default="bench_matrix.csv",
                        help="CSV output file")
    return parser.parse_args()


def run_single_benchmark(args, max_side):
    """Run benchmark for a specific HOLO_MAX_SIDE value"""
    print(f"\n{'='*60}")
    print(f"Testing HOLO_MAX_SIDE={max_side}")
    print(f"{'='*60}\n")
    
    # Note: This assumes the server is already running
    # In practice, you'd need to restart the server with the new env var
    # or implement a way to change it dynamically
    
    bench_script = Path(__file__).parent / "bench_holo15.py"
    
    cmd = [
        sys.executable,
        str(bench_script),
        "--server", args.server,
        "--image", args.image,
        "--prompt", args.prompt,
        "--runs", str(args.runs),
        "--csv", args.csv,
        "--no-report"  # Skip individual reports
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running benchmark: {e}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False


def print_comparison_table(csv_file, max_sides):
    """Print a comparison table of results"""
    import csv
    
    print(f"\n{'='*80}")
    print("COMPARISON TABLE")
    print(f"{'='*80}\n")
    
    if not Path(csv_file).exists():
        print("No results file found")
        return
    
    # Read last N results (where N = number of max_sides)
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if len(rows) < len(max_sides):
        print("Not enough results to compare")
        return
    
    # Take last N rows
    results = rows[-len(max_sides):]
    
    print(f"{'MAX_SIDE':<12} {'Avg (ms)':<12} {'P50 (ms)':<12} {'P90 (ms)':<12} {'Tokens':<10} {'Tokens/s':<10}")
    print("-" * 80)
    
    for row, max_side in zip(results, max_sides):
        avg_ms = float(row['avg_ms'])
        p50_ms = float(row['p50_ms'])
        p90_ms = row['p90_ms'] if row['p90_ms'] else 'N/A'
        tokens = row.get('tokens_avg', 'N/A')
        
        if tokens != 'N/A' and tokens:
            tokens_f = float(tokens)
            tokens_per_s = (tokens_f / avg_ms) * 1000
            tokens_str = f"{tokens_f:.1f}"
            tps_str = f"{tokens_per_s:.2f}"
        else:
            tokens_str = 'N/A'
            tps_str = 'N/A'
        
        if p90_ms != 'N/A':
            p90_str = f"{float(p90_ms):.1f}"
        else:
            p90_str = 'N/A'
        
        print(f"{max_side:<12} {avg_ms:<12.1f} {p50_ms:<12.1f} {p90_str:<12} {tokens_str:<10} {tps_str:<10}")
    
    print()


def main():
    args = parse_args()
    
    # Parse max_sides
    max_sides = [int(x.strip()) for x in args.max_sides.split(',')]
    
    print(f"🎯 Matrix Benchmark Configuration")
    print(f"   Image: {args.image}")
    print(f"   Prompt: {args.prompt}")
    print(f"   Runs per config: {args.runs}")
    print(f"   MAX_SIDE values: {max_sides}")
    print(f"   CSV output: {args.csv}")
    print()
    print("⚠️  Note: This script assumes the server is already running.")
    print("   For accurate results, restart the server with each HOLO_MAX_SIDE value.")
    print("   Example: HOLO_MAX_SIDE=720 ./launch.sh")
    
    input("\nPress Enter to continue or Ctrl+C to abort...")
    
    # Run benchmarks for each max_side
    success_count = 0
    for max_side in max_sides:
        print(f"\n⚠️  Please restart server with: HOLO_MAX_SIDE={max_side} ./launch.sh")
        input("Press Enter when server is ready...")
        
        if run_single_benchmark(args, max_side):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Completed {success_count}/{len(max_sides)} benchmarks")
    print(f"{'='*60}")
    
    if success_count > 0:
        print_comparison_table(args.csv, max_sides)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMatrix benchmark interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
