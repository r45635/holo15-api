from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Any, Optional
from PIL import Image
import io, base64, time
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

# Import security modules
from config import get_settings
from middleware import SecurityMiddleware, setup_logging
from security.auth import init_auth, get_principal, get_principal_optional, Principal
from security.rate_limit import get_rate_limiter, check_rate_limit_ip, check_rate_limit_key
from security.abuse import init_abuse_detector, get_abuse_detector, AbuseContext

# ==== Configuration ====
settings = get_settings()

# ==== FastAPI App ====
# Conditionally disable docs based on settings
app = FastAPI(
    title="Holo 1.5 API",
    version="1.0.0",
    docs_url="/docs" if settings.allow_docs else None,
    redoc_url="/redoc" if settings.allow_docs else None,
    openapi_url="/openapi.json" if settings.allow_docs else None
)

# ==== Middleware Setup ====
# CORS (after security middleware to allow CORS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (logging, request ID, IP extraction, body size limits)
app.add_middleware(SecurityMiddleware, settings=settings)

# ==== Logging Setup ====
app_logger, audit_logger = setup_logging(settings.log_level, settings.audit_log_file)

# ==== Model Config ====
MODEL_ID = settings.model_id
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "mps" else torch.float32
MAX_SIDE = settings.holo_max_side

# ==== Globals ====
model = None
processor = None
load_error: Optional[str] = None

# Stats (in-memory)
stats = {
    "requests": 0,
    "2xx": 0,
    "4xx": 0,
    "5xx": 0,
    "latencies": []  # Keep last 1000
}

# Pillow resample compat
try:
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC  # type: ignore
except Exception:
    RESAMPLE_BICUBIC = Image.BICUBIC


# ==== Image Validation ====
def validate_image_data(b64: str, max_size_mb: float) -> Image.Image:
    """
    Validate and decode base64 image
    Raises HTTPException if invalid
    """
    try:
        # Decode base64
        img_bytes = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")
    
    # Check size
    size_mb = len(img_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large: {size_mb:.2f}MB (max: {max_size_mb}MB)"
        )
    
    # Try to open as image
    try:
        img = Image.open(io.BytesIO(img_bytes))
    except Exception:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format or corrupted image"
        )
    
    # Verify it's an image format we support
    if img.format not in ["JPEG", "PNG", "GIF", "BMP", "TIFF", "WEBP"]:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image format: {img.format}"
        )
    
    # Convert to RGB
    img = img.convert("RGB")
    
    # Check dimensions
    w, h = img.size
    if w > settings.max_image_side or h > settings.max_image_side:
        # Resize if needed
        m = max(w, h)
        r = settings.max_image_side / float(m)
        img = img.resize((int(w * r), int(h * r)), RESAMPLE_BICUBIC)
    
    return img


def move_to_device(inputs: dict):
    """Move inputs to device, casting only floating tensors to DTYPE"""
    out = {}
    for k, v in inputs.items():
        if hasattr(v, "to"):
            if hasattr(v, "dtype") and torch.is_floating_point(v):
                out[k] = v.to(DEVICE, dtype=DTYPE)
            else:
                out[k] = v.to(DEVICE)
        else:
            out[k] = v
    return out


def build_messages_for_chat_template(text_prompt: str, image: Optional[Image.Image]):
    """Build messages array suitable for apply_chat_template"""
    if image is not None:
        content = [
            {"type": "image"},
            {"type": "text", "text": text_prompt}
        ]
    else:
        content = text_prompt
    
    return [{"role": "user", "content": content}]


def extract_text_and_image(messages: List[dict], max_images: int = 1):
    """
    Extract text prompt and image from OpenAI-style messages
    Validates image count
    """
    text_parts = []
    images = []
    
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for part in content:
                part_type = part.get("type")
                if part_type == "text":
                    text_parts.append(part.get("text", ""))
                elif part_type in ("image", "image_url"):
                    if len(images) >= max_images:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Too many images. Maximum: {max_images}"
                        )
                    
                    # Try to get base64 image
                    b64 = (part.get("image") or {}).get("b64")
                    if b64:
                        img = validate_image_data(b64, settings.max_body_mb)
                        images.append(img)
    
    text = "\n".join([t for t in text_parts if t]).strip()
    if not text:
        text = "Describe this image." if images else "Hello."
    
    return text, images[0] if images else None


def _warmup():
    """Warmup to validate token/feature alignment and reduce first-token latency"""
    app_logger.info("Running warmup inference...")
    dummy_img = Image.new("RGB", (512, 512), color="gray")
    dummy_text = "What do you see?"
    
    messages = build_messages_for_chat_template(dummy_text, dummy_img)
    formatted_text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = processor(text=[formatted_text], images=[dummy_img], return_tensors="pt")
    inputs = move_to_device(inputs)
    
    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=4)
    
    app_logger.info("Warmup complete!")


def init_model():
    """Load model and processor, run warmup"""
    global model, processor, load_error
    if model is not None and processor is not None:
        return
    
    try:
        app_logger.info(f"Loading model: {MODEL_ID} on {DEVICE} dtype {DTYPE}")
        processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID, torch_dtype=DTYPE, low_cpu_mem_usage=True
        ).to(DEVICE).eval()
        
        _warmup()
        app_logger.info("Model ready!")
    except Exception as e:
        load_error = f"{type(e).__name__}: {e}"
        app_logger.error(f"Model load error: {load_error}")


@app.on_event("startup")
def on_startup():
    """Initialize all services on startup"""
    app_logger.info("="*70)
    app_logger.info("Holo 1.5 API - Secure Production Mode")
    app_logger.info("="*70)
    
    # Initialize security
    init_auth(settings.api_keys_file)
    init_abuse_detector(
        settings.denylist_file,
        settings.abuse_threshold_errors,
        settings.abuse_window_seconds
    )
    
    # Configure rate limiting
    limiter = get_rate_limiter()
    limiter.configure(
        settings.rate_limit_ip,
        settings.rate_limit_key,
        settings.burst_ip,
        settings.burst_key
    )
    
    # Load model
    init_model()
    
    app_logger.info("="*70)
    app_logger.info("✅ Startup complete")
    app_logger.info("="*70)


# ==== Request Models ====
class Message(BaseModel):
    role: str
    content: Any

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: int = 128
    temperature: float = 0.0


# ==== Endpoints ====
@app.get("/health")
def health(
    request: Request,
    principal: Optional[Principal] = Depends(get_principal_optional)
):
    """
    Health check endpoint (public but rate-limited by IP)
    """
    # Rate limit by IP only
    check_rate_limit_ip(request)
    
    # Track for abuse (public endpoint can be abused)
    abuse_detector = get_abuse_detector()
    ctx = AbuseContext(
        ip=request.state.client_ip,
        key_id=principal.key_id if principal else None,
        status_code=200
    )
    
    if abuse_detector.check_and_maybe_block(ctx):
        raise HTTPException(status_code=403, detail="Access denied: blocked for abuse")
    
    status = "ok" if (model is not None and load_error is None) else ("error" if load_error else "not_loaded")
    return {
        "status": status,
        "device": DEVICE,
        "dtype": str(DTYPE),
        "model": MODEL_ID,
        "max_side": MAX_SIDE,
        "load_error": load_error,
        "version": "1.0.0"
    }


@app.post("/v1/chat/completions")
def chat(
    request: Request,
    req: ChatRequest,
    principal: Principal = Depends(get_principal)
):
    """
    OpenAI-compatible chat completions endpoint
    Requires authentication, rate-limited by both IP and API key
    """
    start_time = time.time()
    
    # Check if denied
    abuse_detector = get_abuse_detector()
    if abuse_detector.is_denied(request.state.client_ip):
        raise HTTPException(status_code=403, detail="IP blocked for abuse")
    if abuse_detector.is_denied(f"key:{principal.key_id}"):
        raise HTTPException(status_code=403, detail="API key blocked for abuse")
    
    # Rate limiting (IP + key)
    check_rate_limit_ip(request)
    check_rate_limit_key(request)
    
    # Check scope
    if not principal.has_scope("chat:read"):
        raise HTTPException(status_code=403, detail="Insufficient scopes for this operation")
    
    # Validate max_tokens
    if req.max_tokens > settings.max_tokens_limit:
        raise HTTPException(
            status_code=400,
            detail=f"max_tokens too large. Maximum: {settings.max_tokens_limit}"
        )
    
    # Initialize model
    init_model()
    if model is None or processor is None:
        # Track error
        ctx = AbuseContext(
            ip=request.state.client_ip,
            key_id=principal.key_id,
            status_code=503,
            error_type="model_not_loaded"
        )
        abuse_detector.track_request(ctx)
        
        raise HTTPException(status_code=503, detail=f"Model failed to load: {load_error}")
    
    # Extract and validate messages
    try:
        text_prompt, image = extract_text_and_image([m.model_dump() for m in req.messages])
    except HTTPException:
        # Track validation errors
        ctx = AbuseContext(
            ip=request.state.client_ip,
            key_id=principal.key_id,
            status_code=400,
            error_type="invalid_request"
        )
        abuse_detector.track_request(ctx)
        raise
    
    # Build and process
    try:
        messages = build_messages_for_chat_template(text_prompt, image)
        formatted_text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        images = [image] if image else None
        
        with torch.inference_mode():
            inputs = processor(text=[formatted_text], images=images, return_tensors="pt")
            inputs = move_to_device(inputs)
            
            input_length = inputs["input_ids"].shape[1]
            
            gen_kwargs = {
                "max_new_tokens": req.max_tokens,
                "do_sample": req.temperature > 0,
                "pad_token_id": processor.tokenizer.pad_token_id,
                "eos_token_id": processor.tokenizer.eos_token_id,
            }
            if req.temperature > 0:
                gen_kwargs["temperature"] = req.temperature
            
            output_ids = model.generate(**inputs, **gen_kwargs)
            generated_ids = output_ids[:, input_length:]
            response_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Track success
        latency_ms = (time.time() - start_time) * 1000
        stats["requests"] += 1
        stats["2xx"] += 1
        stats["latencies"].append(latency_ms)
        if len(stats["latencies"]) > 1000:
            stats["latencies"] = stats["latencies"][-1000:]
        
        ctx = AbuseContext(
            ip=request.state.client_ip,
            key_id=principal.key_id,
            status_code=200
        )
        abuse_detector.track_request(ctx)
        
        # Return response with Cache-Control header
        return JSONResponse(
            content={
                "id": f"chatcmpl-{request.state.request_id[:8]}",
                "object": "chat.completion",
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop"
                }],
            },
            headers={"Cache-Control": "no-store"}
        )
    
    except Exception as e:
        # Track error
        ctx = AbuseContext(
            ip=request.state.client_ip,
            key_id=principal.key_id,
            status_code=500,
            error_type="generation_error"
        )
        abuse_detector.track_request(ctx)
        
        app_logger.error(f"Generation error: {e}", extra={"request_id": request.state.request_id})
        raise HTTPException(status_code=500, detail="Generation failed")


@app.get("/metrics")
def metrics(
    request: Request,
    principal: Principal = Depends(get_principal)
):
    """
    Simple metrics endpoint (requires authentication)
    Returns basic stats about requests
    """
    check_rate_limit_key(request)
    
    if not principal.has_scope("*"):
        raise HTTPException(status_code=403, detail="Admin scope required")
    
    # Calculate latency percentiles
    latencies = sorted(stats["latencies"])
    p50 = latencies[len(latencies)//2] if latencies else 0
    p95 = latencies[int(len(latencies)*0.95)] if latencies else 0
    
    return {
        "requests_total": stats["requests"],
        "requests_2xx": stats["2xx"],
        "requests_4xx": stats["4xx"],
        "requests_5xx": stats["5xx"],
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "abuse_stats": get_abuse_detector().get_stats()
    }
