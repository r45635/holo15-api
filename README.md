# Holo 1.5 Local API

Minimal local API to serve the **Hcompany/Holo1.5-7B** vision-language model on macOS (Apple Silicon) with FastAPI, using PyTorch MPS and Hugging Face Transformers.

## Features

- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ Supports both text-only and image+text requests
- ✅ Uses `apply_chat_template` for proper image token alignment
- ✅ Runs on Apple Silicon MPS (GPU acceleration)
- ✅ No "Image features and image tokens do not match" errors
- ✅ Automatic port conflict detection and resolution
- 🔐 **Production-ready security** (API keys, rate limiting, abuse detection)

## 📚 Documentation

- **[README_SECURITY.md](README_SECURITY.md)** - Production deployment with security (API keys, rate limiting, monitoring)
- **[docs/SECURITY.md](docs/SECURITY.md)** - Complete security guide and best practices
- **API Client Examples** - See README_SECURITY.md for Python, JavaScript, cURL examples

## Quick Setup

### 1. Create virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch the server

```bash
./launch.sh
```

The server will start on `http://127.0.0.1:8000` by default.

## API Endpoints

### Health Check

```bash
curl http://127.0.0.1:8000/health
```

Response:
```json
{
  "status": "ok",
  "device": "mps",
  "dtype": "torch.float16",
  "model": "Hcompany/Holo1.5-7B",
  "max_side": 1440,
  "load_error": null
}
```

### Text-Only Chat

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Hcompany/Holo1.5-7B",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "max_tokens": 64,
    "temperature": 0.0
  }'
```

### Image + Text Chat

```bash
# Encode your image to base64
b64=$(base64 -i cat.jpg)

# Send request with image
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"Hcompany/Holo1.5-7B\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"text\", \"text\": \"What do you see in this image?\"},
        {\"type\": \"image\", \"image\": {\"b64\": \"$b64\"}}
      ]
    }],
    \"max_tokens\": 128,
    \"temperature\": 0.0
  }"
```

## Testing

A test script is provided:

```bash
# Basic tests (health check + text-only)
source .venv/bin/activate
python test_api.py

# Test with an image
python test_api.py cat_image.jpg
```

## Docs & Benchmarks

### 📚 Full API Documentation

See **[docs/API_GUIDE.md](docs/API_GUIDE.md)** for comprehensive documentation including:

- OpenAI SDK examples (Python & Node.js)
- Performance tuning guidance
- Benchmarking methodology
- Known limitations and troubleshooting

### 🔬 Benchmarking

Measure latency and performance with the included benchmark script:

```bash
# Text-only benchmark
python ./scripts/bench_holo15.py --runs 10 --prompt "Say hello in one sentence."

# Image + text benchmark
python ./scripts/bench_holo15.py --runs 10 --image cat.jpg --prompt "What do you see?"
```

**Results** are printed to console and appended to `bench_results.csv` for tracking over time.

**Key features:**
- Automatic warmup (first request discarded)
- Statistics: avg, P50, P90, stdev
- CSV export with system info
- Compatible with Python 3.13

See [docs/API_GUIDE.md#benchmarking-methodology](docs/API_GUIDE.md#benchmarking-methodology) for detailed guidance.

## Configuration

Environment variables (can be set in `launch.sh`):

- `HOLO_MODEL`: Model ID (default: `Hcompany/Holo1.5-7B`)
- `HOLO_MAX_SIDE`: Max image dimension in pixels (default: `1440`)
- `HOLO_HOST`: Server host (default: `127.0.0.1`)
- `HOLO_PORT`: Server port (default: `8000`)
- `PYTORCH_ENABLE_MPS_FALLBACK`: Enable MPS fallback (default: `1`)
- `PYTORCH_MPS_HIGH_WATERMARK_RATIO`: MPS memory management (default: `0.0`)

**Note**: Use `HOLO_HOST` and `HOLO_PORT` instead of `HOST` and `PORT` to avoid conflicts with system environment variables.

## Architecture

### Key Implementation Details

1. **Chat Template**: Uses `processor.apply_chat_template()` to properly format messages with image tokens
2. **Image Processing**: 
   - Images are resized to max 1440px on longest side
   - Base64 encoded images are decoded and converted to RGB
3. **Token Handling**:
   - Only generated tokens are decoded (input is skipped)
   - Proper dtype casting: floating tensors to float16, integers stay as Long
4. **MPS Optimization**:
   - Runs on Apple Silicon GPU with float16 precision
   - Automatic fallback to CPU operations when needed

### Files

- `server.py`: FastAPI application with model loading and inference
- `launch.sh`: Startup script with environment configuration
- `test_api.py`: Test script for API validation
- `requirements.txt`: Python dependencies
- `docs/API_GUIDE.md`: Complete API documentation
- `scripts/bench_holo15.py`: Benchmarking tool

## Requirements

- Python 3.13
- macOS with Apple Silicon (M1/M2/M3)
- ~16GB RAM recommended for Holo 1.5 7B model

## Performance Benchmarks

### Test Environment

**Hardware:**
- **Model:** Mac Studio (Mac14,13)
- **Chip:** Apple M2 Max
- **CPU Cores:** 12 (8 performance + 4 efficiency)
- **Memory:** 32 GB
- **GPU:** Apple M2 Max (38-core)

**Software:**
- **OS:** macOS 15.7.1 (Sequoia)
- **Python:** 3.13.5
- **PyTorch:** 2.9.0
- **Transformers:** 4.57.1
- **CUDA/ROCm:** Not applicable (MPS backend)

### Measured Performance

Results from 10-run benchmarks (+ 1 warmup, discarded):

#### Text-Only Inference
```
Prompt: "Say hello in one sentence."
Average Latency: 511 ms
Throughput: 17.6 tokens/sec
Std Deviation: 6.9 ms (very stable)
```

#### Image + Text Inference
```
Prompt: "What do you see in this image?" + cat_image.jpg
Average Latency: 21,980 ms (~22 seconds)
P50 (Median): 21,462 ms
P90: 29,596 ms
Throughput: 0.68 tokens/sec
Avg Output: 15 tokens
```

**Notes:**
- Image inference includes vision encoding (1849 image tokens processed)
- Text-only is highly consistent (low stdev)
- Performance scales with `HOLO_MAX_SIDE` setting (default: 1440px)
- First request (warmup) typically ~1500ms, subsequent requests ~500ms

See `bench_report.md` and `bench_results.csv` for detailed measurements.

## Troubleshooting

### Port already in use

The launch script will automatically detect if port 8000 is in use and offer to kill the conflicting process.

### Model loading errors

Check the `/health` endpoint to see detailed error messages:

```bash
curl http://127.0.0.1:8000/health | python3 -m json.tool
```

### Memory issues

Reduce `HOLO_MAX_SIDE` or adjust MPS environment variables in `launch.sh`.

## License

This is a minimal wrapper around the Holo 1.5 model. Please refer to the model's license on Hugging Face.
