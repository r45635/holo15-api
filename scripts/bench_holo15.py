#!/usr/bin/env python3
"""
Benchmark script for Holo 1.5 local API server.
Measures end-to-end latency for text and image+text workloads.

Compatible with Python 3.13, requires only 'requests' package.
Optional: uses transformers for token counting if available.
"""
import argparse
import base64
import csv
import json
import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev

# Optional imports
try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    AutoTokenizer = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark Holo 1.5 API latency",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--server", default="http://127.0.0.1:8000", 
                        help="Server base URL")
    parser.add_argument("--model", default="Hcompany/Holo1.5-7B", 
                        help="Model name")
    parser.add_argument("--prompt", required=True, 
                        help="Text prompt")
    parser.add_argument("--image", default=None, 
                        help="Path to image file (optional)")
    parser.add_argument("--runs", type=int, default=10, 
                        help="Number of benchmark runs (after warmup)")
    parser.add_argument("--max-tokens", type=int, default=64, 
                        help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.0, 
                        help="Sampling temperature (0.0 = deterministic)")
    parser.add_argument("--csv", default="bench_results.csv", 
                        help="CSV output file")
    parser.add_argument("--markdown", default="bench_report.md", 
                        help="Markdown report output file")
    parser.add_argument("--no-report", action="store_true",
                        help="Skip generating Markdown report")
    return parser.parse_args()


def load_image_b64(image_path):
    """Load image and encode as base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_request(args, image_b64=None):
    """Build chat completion request payload"""
    if image_b64:
        content = [
            {"type": "text", "text": args.prompt},
            {"type": "image", "image": {"b64": image_b64}}
        ]
    else:
        content = args.prompt
    
    return {
        "model": args.model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature
    }


def call_api(server_url, payload):
    """Make API call and return (latency_ms, response_text, success)"""
    import requests
    
    url = f"{server_url}/v1/chat/completions"
    start = time.perf_counter()
    
    try:
        resp = requests.post(url, json=payload, timeout=300)
        elapsed = time.perf_counter() - start
        resp.raise_for_status()
        
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        
        if not content:
            print("Warning: Empty response received", file=sys.stderr)
            return elapsed * 1000, "", False
        
        return elapsed * 1000, content, True
        
    except requests.exceptions.RequestException as e:
        elapsed = time.perf_counter() - start
        print(f"Error: API call failed: {e}", file=sys.stderr)
        return elapsed * 1000, "", False


def run_benchmark(args):
    """Execute benchmark runs"""
    print(f"🎯 Benchmark Configuration")
    print(f"   Server: {args.server}")
    print(f"   Model: {args.model}")
    print(f"   Workload: {'image+text' if args.image else 'text-only'}")
    print(f"   Runs: {args.runs} (+ 1 warmup)")
    print(f"   Max tokens: {args.max_tokens}")
    print(f"   Temperature: {args.temperature}")
    if args.image:
        print(f"   Image: {args.image}")
    print(f"   Prompt: {args.prompt[:60]}{'...' if len(args.prompt) > 60 else ''}")
    print()
    
    # Try to load tokenizer for token counting
    tokenizer = None
    if HAS_TRANSFORMERS:
        try:
            print("🔤 Loading tokenizer for token counting...")
            tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
            print("   ✓ Tokenizer loaded")
        except Exception as e:
            print(f"   ⚠️  Could not load tokenizer: {e}")
            print("   Continuing without token counts...")
    else:
        print("⚠️  transformers not installed - token counts unavailable")
    print()
    
    # Load image if provided
    image_b64 = None
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image file not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        image_b64 = load_image_b64(args.image)
        print(f"✓ Loaded image: {args.image} ({len(image_b64)} bytes base64)")
    
    # Build request payload
    payload = build_request(args, image_b64)
    
    # Warmup run (discard)
    print("🔥 Warmup run (discarded)...")
    warmup_ms, warmup_text, warmup_ok = call_api(args.server, payload)
    if not warmup_ok:
        print("Error: Warmup run failed. Aborting.", file=sys.stderr)
        sys.exit(1)
    warmup_tokens = count_tokens(warmup_text, tokenizer) if tokenizer else None
    if warmup_tokens:
        print(f"   {warmup_ms:.1f} ms → {len(warmup_text)} chars, ~{warmup_tokens} tokens")
    else:
        print(f"   {warmup_ms:.1f} ms → {len(warmup_text)} chars")
    print()
    
    # Benchmark runs
    print(f"📊 Running {args.runs} iterations...")
    latencies = []
    output_lengths = []
    token_counts = []
    
    for i in range(args.runs):
        lat_ms, text, ok = call_api(args.server, payload)
        if not ok:
            print(f"Run {i+1}/{args.runs}: FAILED", file=sys.stderr)
            continue
        
        latencies.append(lat_ms)
        output_lengths.append(len(text))
        
        tokens = count_tokens(text, tokenizer) if tokenizer else None
        if tokens:
            token_counts.append(tokens)
            print(f"   Run {i+1:2d}/{args.runs}: {lat_ms:7.1f} ms → {len(text):4d} chars, ~{tokens:3d} tokens")
        else:
            print(f"   Run {i+1:2d}/{args.runs}: {lat_ms:7.1f} ms → {len(text):4d} chars")
    
    if not latencies:
        print("Error: All runs failed. No results to report.", file=sys.stderr)
        sys.exit(1)
    
    # Compute statistics
    avg_ms = mean(latencies)
    p50_ms = median(latencies)
    p90_ms = sorted(latencies)[int(len(latencies) * 0.9)] if len(latencies) >= 10 else None
    std_ms = stdev(latencies) if len(latencies) > 1 else 0.0
    avg_outlen = mean(output_lengths)
    avg_tokens = mean(token_counts) if token_counts else None
    
    # Print summary
    print()
    print("=" * 60)
    print("📈 Summary Statistics")
    print("=" * 60)
    print(f"   Average latency:    {avg_ms:7.1f} ms")
    print(f"   P50 (median):       {p50_ms:7.1f} ms")
    if p90_ms is not None:
        print(f"   P90:                {p90_ms:7.1f} ms")
    print(f"   Std deviation:      {std_ms:7.1f} ms")
    print(f"   Avg output length:  {avg_outlen:7.1f} chars")
    if avg_tokens:
        print(f"   Avg token count:    {avg_tokens:7.1f} tokens")
        tokens_per_sec = (avg_tokens / avg_ms) * 1000
        print(f"   Throughput:         {tokens_per_sec:7.1f} tokens/sec")
    print("=" * 60)
    
    # Save to CSV
    save_to_csv(args, avg_ms, p50_ms, p90_ms, std_ms, avg_outlen, avg_tokens)
    
    # Generate Markdown report
    if not args.no_report:
        generate_markdown_report(args, avg_ms, p50_ms, p90_ms, std_ms, avg_outlen, avg_tokens)
    
    return {
        "avg_ms": avg_ms,
        "p50_ms": p50_ms,
        "p90_ms": p90_ms,
        "std_ms": std_ms,
        "avg_outlen": avg_outlen,
        "avg_tokens": avg_tokens
    }


def count_tokens(text, tokenizer):
    """Count tokens in text using tokenizer"""
    if not tokenizer or not text:
        return None
    try:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        return len(tokens)
    except Exception:
        return None


def save_to_csv(args, avg_ms, p50_ms, p90_ms, std_ms, avg_outlen, avg_tokens=None):
    """Append results to CSV file"""
    csv_path = Path(args.csv)
    file_exists = csv_path.exists()
    
    # Gather system info
    timestamp = datetime.now().isoformat()
    workload = "image" if args.image else "text"
    os_info = f"{platform.system()} {platform.release()}"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    # CSV row
    row = {
        "timestamp": timestamp,
        "workload": workload,
        "runs": args.runs,
        "avg_ms": f"{avg_ms:.2f}",
        "p50_ms": f"{p50_ms:.2f}",
        "p90_ms": f"{p90_ms:.2f}" if p90_ms else "",
        "stdev_ms": f"{std_ms:.2f}",
        "outlen_avg": f"{avg_outlen:.1f}",
        "tokens_avg": f"{avg_tokens:.1f}" if avg_tokens else "",
        "server": args.server,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "os": os_info,
        "python": python_version
    }
    
    # Write CSV
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    
    print(f"\n✓ Results appended to: {csv_path.absolute()}")


def generate_markdown_report(args, avg_ms, p50_ms, p90_ms, std_ms, avg_outlen, avg_tokens=None):
    """Generate Markdown summary report"""
    report_path = Path(args.markdown)
    
    # Get system info
    import socket
    try:
        import torch
        torch_version = torch.__version__
    except ImportError:
        torch_version = "N/A"
    
    try:
        import transformers
        transformers_version = transformers.__version__
    except ImportError:
        transformers_version = "N/A"
    
    os_info = f"{platform.system()} {platform.release()}"
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    hostname = socket.gethostname()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build report
    report = f"""# Holo 1.5 Benchmark Report

**Generated:** {timestamp}  
**Hostname:** {hostname}

## Environment

| Property | Value |
|----------|-------|
| OS | {os_info} |
| Python | {python_version} |
| PyTorch | {torch_version} |
| Transformers | {transformers_version} |

## Configuration

| Parameter | Value |
|-----------|-------|
| Server | `{args.server}` |
| Model | `{args.model}` |
| Workload | {('Image + Text' if args.image else 'Text only')} |
| Runs | {args.runs} (+ 1 warmup) |
| Max Tokens | {args.max_tokens} |
| Temperature | {args.temperature} |

## Input

**Prompt:**
```
{args.prompt}
```

"""
    
    if args.image:
        report += f"""**Image:** `{args.image}`

"""
    
    # Statistics table
    report += f"""## Results

| Metric | Value |
|--------|-------|
| Average Latency | {avg_ms:.2f} ms |
| P50 (Median) | {p50_ms:.2f} ms |
"""
    
    if p90_ms is not None:
        report += f"""| P90 | {p90_ms:.2f} ms |
"""
    
    report += f"""| Std Deviation | {std_ms:.2f} ms |
| Avg Output Length | {avg_outlen:.1f} chars |
"""
    
    if avg_tokens:
        tokens_per_sec = (avg_tokens / avg_ms) * 1000
        report += f"""| Avg Token Count | {avg_tokens:.1f} tokens |
| Throughput | {tokens_per_sec:.2f} tokens/sec |
"""
    
    report += """
## Notes

- First request (warmup) was discarded
- All timings are end-to-end from client perspective
- Deterministic output (temperature=0.0) ensures reproducibility

"""
    
    # Write report
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"✓ Markdown report saved to: {report_path.absolute()}")


def main():
    args = parse_args()
    
    # Check requests is available
    try:
        import requests
    except ImportError:
        print("Error: 'requests' package required. Install with:", file=sys.stderr)
        print("  pip install requests", file=sys.stderr)
        sys.exit(1)
    
    # Run benchmark
    try:
        run_benchmark(args)
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
