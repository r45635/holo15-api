# Holo 1.5 Benchmark Report

**Generated:** 2025-11-02 19:09:10  
**Hostname:** vincents-Mac-Studio.local

## Environment

| Property | Value |
|----------|-------|
| OS | Darwin 24.6.0 |
| Python | 3.13.5 |
| PyTorch | 2.9.0 |
| Transformers | 4.57.1 |

## Configuration

| Parameter | Value |
|-----------|-------|
| Server | `http://vincents-Mac-Studio.local:8000` |
| Model | `Hcompany/Holo1.5-7B` |
| Workload | Image + Text |
| Runs | 10 (+ 1 warmup) |
| Max Tokens | 64 |
| Temperature | 0.0 |

## Input

**Prompt:**
```
What do you see in this image?
```

**Image:** `cat_image.jpg`

## Results

| Metric | Value |
|--------|-------|
| Average Latency | 21980.16 ms |
| P50 (Median) | 21462.43 ms |
| P90 | 29595.83 ms |
| Std Deviation | 4093.41 ms |
| Avg Output Length | 45.0 chars |
| Avg Token Count | 15.0 tokens |
| Throughput | 0.68 tokens/sec |

## Notes

- First request (warmup) was discarded
- All timings are end-to-end from client perspective
- Deterministic output (temperature=0.0) ensures reproducibility

