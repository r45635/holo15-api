# Holo 1.5 API Guide

## Overview

This is a local FastAPI server serving the **Hcompany/Holo1.5-7B** vision-language model on **Apple Silicon** (M1/M2/M3) with **MPS acceleration** and **FP16 precision**.

- **Endpoint**: `http://127.0.0.1:8000`
- **Model**: Holo 1.5 7B (vision + language)
- **Hardware**: macOS Apple Silicon only (MPS backend)
- **Precision**: float16 on MPS, float32 on CPU
- **Default mode**: Deterministic (temperature=0.0)

## Endpoints

### `GET /health`

Health check endpoint returning server status and configuration.

**Response:**
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

**Status values:**
- `ok`: Model loaded and ready
- `not_loaded`: Model not yet initialized
- `error`: Load failed (check `load_error` field)

### `POST /v1/chat/completions`

OpenAI-compatible chat completions endpoint.

**Request body:**
```json
{
  "model": "Hcompany/Holo1.5-7B",
  "messages": [
    {
      "role": "user",
      "content": "Your prompt here"
    }
  ],
  "max_tokens": 128,
  "temperature": 0.0
}
```

**Fields:**
- `model` (string, required): Model identifier (use `"Hcompany/Holo1.5-7B"`)
- `messages` (array, required): Array of message objects with `role` and `content`
- `max_tokens` (int, optional): Maximum tokens to generate (default: 128)
- `temperature` (float, optional): Sampling temperature (default: 0.0 for deterministic output)

**Content formats:**

**Text only:**
```json
{
  "role": "user",
  "content": "What is the capital of France?"
}
```

**Image + text:**
```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What do you see in this image?"},
    {"type": "image", "image": {"b64": "<base64-encoded-image>"}}
  ]
}
```

**Response:**
```json
{
  "id": "chatcmpl-local",
  "object": "chat.completion",
  "model": "Hcompany/Holo1.5-7B",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Generated response text"
    },
    "finish_reason": "stop"
  }]
}
```

## Client Examples

### Python (OpenAI SDK)

```python
from openai import OpenAI
import base64

# Create client pointing to local server
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="not-needed"  # Local server doesn't check keys
)

# Text-only request
response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ],
    max_tokens=64,
    temperature=0.0
)
print(response.choices[0].message.content)

# Image + text request
with open("cat.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What do you see?"},
            {"type": "image", "image": {"b64": image_b64}}
        ]
    }],
    max_tokens=128,
    temperature=0.0
)
print(response.choices[0].message.content)
```

### Node.js (OpenAI SDK)

```javascript
import OpenAI from 'openai';
import fs from 'fs';

const client = new OpenAI({
  baseURL: 'http://127.0.0.1:8000/v1',
  apiKey: 'not-needed'
});

// Text-only request
const response = await client.chat.completions.create({
  model: 'Hcompany/Holo1.5-7B',
  messages: [
    { role: 'user', content: 'What is the capital of France?' }
  ],
  max_tokens: 64,
  temperature: 0.0
});
console.log(response.choices[0].message.content);

// Image + text request
const imageB64 = fs.readFileSync('cat.jpg').toString('base64');

const imageResponse = await client.chat.completions.create({
  model: 'Hcompany/Holo1.5-7B',
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: 'What do you see?' },
      { type: 'image', image: { b64: imageB64 } }
    ]
  }],
  max_tokens: 128,
  temperature: 0.0
});
console.log(imageResponse.choices[0].message.content);
```

### cURL

**Text request:**
```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Hcompany/Holo1.5-7B",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 64,
    "temperature": 0.0
  }'
```

**Image request:**
```bash
b64=$(base64 -i image.jpg)
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"Hcompany/Holo1.5-7B\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"text\", \"text\": \"What is this?\"},
        {\"type\": \"image\", \"image\": {\"b64\": \"$b64\"}}
      ]
    }],
    \"max_tokens\": 128,
    \"temperature\": 0.0
  }"
```

## Performance Guidance

### Image Preprocessing

Images are automatically resized so that the longest side ≤ `HOLO_MAX_SIDE` pixels (default: 1440).

**To adjust:**
```bash
export HOLO_MAX_SIDE=1080  # Lower for faster processing, less detail
./launch.sh
```

**Tradeoffs:**
- **1440px**: Best quality, ~15-20s first-token latency
- **1080px**: Balanced, ~10-15s latency
- **720px**: Fastest, ~8-12s latency, reduced detail

### Precision & Device

- **MPS (Apple Silicon)**: Uses FP16 for lower memory and faster inference
- **CPU fallback**: Automatic for unsupported ops (set `PYTORCH_ENABLE_MPS_FALLBACK=1`)

### Determinism

- **temperature=0.0** (default): Deterministic, reproducible outputs
- **temperature>0**: Enables sampling, non-deterministic

For benchmarking, always use `temperature=0.0`.

## Benchmarking Methodology

### What to Report

When sharing benchmark results, include:

**System Information:**
- Machine model (e.g., "MacBook Pro M2 Max, 32GB")
- macOS version
- Python version
- PyTorch version
- Transformers version

**Server Configuration:**
- `HOLO_MAX_SIDE` setting
- Device (mps/cpu)
- Dtype (float16/float32)

**Test Parameters:**
- Workload type (text-only / image+text)
- Number of runs
- `max_tokens` setting
- `temperature` setting
- Prompt and image (if any)

### Warmup Rule

**Always discard the first request** - it includes model initialization and CUDA/MPS kernel compilation.

Run at least **10 iterations** after warmup for reliable statistics.

### Metrics to Collect

- **Latency (ms)**: End-to-end request time
  - Average (mean)
  - P50 (median)
  - P90 (90th percentile)
  - Standard deviation
- **Output length**: Number of characters or tokens generated
- **Throughput**: Tokens per second (if token counting is available)

### Reproducibility Checklist

- [ ] Warmup request completed and discarded
- [ ] Deterministic mode (`temperature=0.0`)
- [ ] Same prompt/image across runs
- [ ] System idle (no heavy background processes)
- [ ] Consistent `HOLO_MAX_SIDE` setting
- [ ] Document exact model version/commit
- [ ] Report system specs (machine, OS, Python, PyTorch versions)

### Using the Benchmark Script

See `scripts/bench_holo15.py`:

```bash
# Text-only benchmark
python scripts/bench_holo15.py \
  --runs 10 \
  --prompt "Say hello in one sentence." \
  --csv bench_results.csv

# Image + text benchmark
python scripts/bench_holo15.py \
  --runs 10 \
  --image cat.jpg \
  --prompt "What do you see?" \
  --csv bench_results.csv
```

Results are printed to console and appended to CSV for tracking over time.

## Known Limitations

### No Streaming

The server does not support streaming responses (`stream=true`). All responses are returned complete after generation finishes.

### Single Model

Only one model can be loaded at a time. The server serves `Hcompany/Holo1.5-7B` exclusively.

### Python 3.13 Compatibility

Uvicorn runs without `--loop uvloop` and `--http httptools` flags as these are not yet available for Python 3.13. Performance impact is minimal for local use.

### Token Limits

- Input: Limited by model context window (~32K tokens for Holo 1.5)
- Output: Configurable via `max_tokens` (default: 128)

Exceeding limits will result in truncation or errors.

### Image Formats

Supported: JPEG, PNG, WebP, GIF (first frame)  
All images converted to RGB internally.

## Troubleshooting

### Server won't start

Check `/health` for error details:
```bash
curl http://127.0.0.1:8000/health | python3 -m json.tool
```

### Slow inference

- Reduce `HOLO_MAX_SIDE` (e.g., 1080 or 720)
- Ensure MPS is being used (`"device": "mps"` in `/health`)
- Close other applications to free memory

### Memory errors

- Lower `HOLO_MAX_SIDE` to reduce VRAM usage
- Use smaller `max_tokens` values
- Restart the server to clear cached data

### Incorrect responses

- Verify `temperature=0.0` for deterministic output
- Check that image base64 encoding is correct
- Try with simpler prompts to isolate issues

## Support

For issues with:
- **API server**: Check server logs and `/health` endpoint
- **Model behavior**: Refer to Holo 1.5 model card on Hugging Face
- **Performance**: See benchmarking methodology above

This is a local development server - not intended for production use.
