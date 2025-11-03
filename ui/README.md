# Holo 1.5 Web UI

Minimal GPT-style chat interface for the Holo 1.5 API.

## Features

- 💬 Text-only and image+text conversations
- 🖼️ Drag-and-drop or file picker for images
- ⚙️ Configurable: API URL, model, max tokens, temperature
- 🎨 Clean dark theme with distinct message bubbles
- ⌨️ Keyboard shortcut: Cmd/Ctrl+Enter to send

## Quick Start

### 1. Start the API server

In the project root:

```bash
./launch.sh
```

The server will start at `http://127.0.0.1:8000`

### 2. Start the web UI

```bash
cd ui
python3 -m http.server 5500
```

### 3. Open in browser

Navigate to: **http://127.0.0.1:5500**

## Usage

### Text-Only Chat

1. Type your message in the textarea
2. Press **Cmd/Ctrl+Enter** or click **Send**
3. Wait for the assistant's response

### Image + Text Chat

1. Click **Image** button or drag an image onto the drop zone
2. A thumbnail preview will appear
3. Type your prompt (e.g., "What do you see in this image?")
4. Send the message

The image will be base64-encoded and sent to the API.

## Configuration

Default values in the header:

- **API Base URL**: `http://127.0.0.1:8000/v1`
- **Model**: `Hcompany/Holo1.5-7B`
- **Max Tokens**: `128`
- **Temperature**: `0.0`

You can modify these values at any time.

## Files

- `index.html` - Main HTML structure
- `styles.css` - Dark theme styling
- `app.js` - Client-side logic (fetch, drag-and-drop, message handling)

## Troubleshooting

### CORS Errors

If you see CORS errors in the browser console, make sure the API server (`server.py`) includes the CORS middleware (already added):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Server Not Found

- Check that the API server is running on port 8000
- Verify the **API Base URL** in the UI header matches your server (should be `http://127.0.0.1:8000/v1`)
- Both 127.0.0.1 and localhost should work due to CORS configuration

### Image Not Uploading

- Only image files (JPEG, PNG, etc.) are supported
- Large images may take time to encode to base64
- Check browser console for errors

## Optional Follow-ups

See the main project README for optional enhancements:

- **Message History**: Include full conversation context in each request
- **Streaming (SSE)**: Real-time token-by-token responses
- **Multi-image Support**: Attach up to 4 images per prompt
- **System Prompts & Presets**: Add system messages and preset configurations
