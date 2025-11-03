from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional
from PIL import Image
import io, base64, os

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

app = FastAPI(title="Holo 1.5 Local API")

# ==== Config ====
MODEL_ID = os.environ.get("HOLO_MODEL", "Hcompany/Holo1.5-7B")
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
DTYPE = torch.float16 if DEVICE == "mps" else torch.float32
MAX_SIDE = int(os.environ.get("HOLO_MAX_SIDE", "1440"))

# ==== Globals ====
model = None
processor = None
load_error: Optional[str] = None

# Pillow resample compat
try:
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC  # type: ignore
except Exception:
    RESAMPLE_BICUBIC = Image.BICUBIC

def decode_image_b64(b64: str) -> Image.Image:
    """Decode base64 image and resize if needed"""
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    w, h = img.size
    m = max(w, h)
    if m > MAX_SIDE:
        r = MAX_SIDE / float(m)
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
        # Image + text: use structured content
        content = [
            {"type": "image"},
            {"type": "text", "text": text_prompt}
        ]
    else:
        # Text only: simple string content
        content = text_prompt
    
    return [{"role": "user", "content": content}]

def extract_text_and_image(messages: List[dict]):
    """Extract text prompt and image from OpenAI-style messages"""
    text_parts = []
    image = None
    
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
                    # Try to get base64 image
                    b64 = (part.get("image") or {}).get("b64")
                    if b64:
                        image = decode_image_b64(b64)
    
    text = "\n".join([t for t in text_parts if t]).strip()
    if not text:
        text = "Describe this image." if image else "Hello."
    
    return text, image

def _warmup():
    """Warmup to validate token/feature alignment and reduce first-token latency"""
    print("[warmup] Running warmup inference...")
    dummy_img = Image.new("RGB", (512, 512), color="gray")
    dummy_text = "What do you see?"
    
    # Use the same flow as real inference
    messages = build_messages_for_chat_template(dummy_text, dummy_img)
    formatted_text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = processor(text=[formatted_text], images=[dummy_img], return_tensors="pt")
    inputs = move_to_device(inputs)
    
    with torch.inference_mode():
        _ = model.generate(**inputs, max_new_tokens=4)
    
    print("[warmup] Complete!")

def init_model():
    """Load model and processor, run warmup"""
    global model, processor, load_error
    if model is not None and processor is not None:
        return
    
    try:
        print(f"[startup] Loading: {MODEL_ID} on {DEVICE} dtype {DTYPE}")
        processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
        model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID, torch_dtype=DTYPE, low_cpu_mem_usage=True
        ).to(DEVICE).eval()
        
        _warmup()
        print("[startup] Model ready!")
    except Exception as e:
        load_error = f"{type(e).__name__}: {e}"
        print(f"[startup] Load error: {load_error}")

@app.on_event("startup")
def on_startup():
    init_model()

class Message(BaseModel):
    role: str
    content: Any

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: int = 128
    temperature: float = 0.0

@app.get("/health")
def health():
    """Health check endpoint"""
    status = "ok" if (model is not None and load_error is None) else ("error" if load_error else "not_loaded")
    return {
        "status": status,
        "device": DEVICE,
        "dtype": str(DTYPE),
        "model": MODEL_ID,
        "max_side": MAX_SIDE,
        "load_error": load_error
    }

@app.post("/v1/chat/completions")
def chat(req: ChatRequest):
    """OpenAI-compatible chat completions endpoint"""
    init_model()
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail=f"Model failed to load: {load_error}")
    
    # Extract text and image from OpenAI-style messages
    text_prompt, image = extract_text_and_image([m.model_dump() for m in req.messages])
    
    # Build messages for chat template
    messages = build_messages_for_chat_template(text_prompt, image)
    
    # Apply chat template to get properly formatted text with image tokens
    formatted_text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    
    # Process with image if present
    images = [image] if image else None
    
    with torch.inference_mode():
        inputs = processor(text=[formatted_text], images=images, return_tensors="pt")
        inputs = move_to_device(inputs)
        
        input_length = inputs["input_ids"].shape[1]
        
        # Generation parameters
        gen_kwargs = {
            "max_new_tokens": req.max_tokens,
            "do_sample": req.temperature > 0,
            "pad_token_id": processor.tokenizer.pad_token_id,
            "eos_token_id": processor.tokenizer.eos_token_id,
        }
        if req.temperature > 0:
            gen_kwargs["temperature"] = req.temperature
        
        # Generate
        output_ids = model.generate(**inputs, **gen_kwargs)
        
        # Decode only the generated tokens (skip input)
        generated_ids = output_ids[:, input_length:]
        response_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_text},
            "finish_reason": "stop"
        }],
    }
