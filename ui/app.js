// State management
let currentImage = null;
let currentImageBase64 = null;

// DOM elements
const chatContainer = document.getElementById('chatContainer');
const promptInput = document.getElementById('promptInput');
const sendButton = document.getElementById('sendButton');
const imageButton = document.getElementById('imageButton');
const fileInput = document.getElementById('fileInput');
const imagePreview = document.getElementById('imagePreview');
const dropZone = document.getElementById('dropZone');

// Config inputs
const baseUrlInput = document.getElementById('baseUrl');
const apiKeyInput = document.getElementById('apiKey');
const modelInput = document.getElementById('model');
const maxTokensInput = document.getElementById('maxTokens');
const temperatureInput = document.getElementById('temperature');

// Initialize
init();

function init() {
    // Check if all required elements exist
    if (!chatContainer || !promptInput || !sendButton || !imageButton || 
        !fileInput || !imagePreview || !dropZone || !baseUrlInput || 
        !apiKeyInput || !modelInput || !maxTokensInput || !temperatureInput) {
        console.error('Missing required DOM elements!');
        console.error({
            chatContainer: !!chatContainer,
            promptInput: !!promptInput,
            sendButton: !!sendButton,
            imageButton: !!imageButton,
            fileInput: !!fileInput,
            imagePreview: !!imagePreview,
            dropZone: !!dropZone,
            baseUrlInput: !!baseUrlInput,
            apiKeyInput: !!apiKeyInput,
            modelInput: !!modelInput,
            maxTokensInput: !!maxTokensInput,
            temperatureInput: !!temperatureInput
        });
        return;
    }
    
    console.log('✅ UI initialized successfully');
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    imageButton.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    promptInput.addEventListener('keydown', handleKeyPress);
    
    // Drag and drop
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    
    // Prevent default drag behavior on document
    document.addEventListener('dragover', (e) => e.preventDefault());
    document.addEventListener('drop', (e) => e.preventDefault());
}

function handleKeyPress(e) {
    // Cmd/Ctrl + Enter to send
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        sendMessage();
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        loadImage(file);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        loadImage(files[0]);
    }
}

function loadImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1]; // Remove data:image/...;base64, prefix
        currentImage = file;
        currentImageBase64 = base64;
        showImagePreview(e.target.result);
    };
    reader.readAsDataURL(file);
}

function showImagePreview(dataUrl) {
    imagePreview.innerHTML = `
        <img src="${dataUrl}" alt="Preview">
        <button class="remove-image" onclick="clearImage()">✕ Remove</button>
    `;
}

function clearImage() {
    currentImage = null;
    currentImageBase64 = null;
    imagePreview.innerHTML = '';
    fileInput.value = '';
}

function addMessage(role, content, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message${isError ? ' error-message' : ''}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // If user message with image, show thumbnail
    if (role === 'user' && currentImage) {
        const img = document.createElement('img');
        img.className = 'message-image';
        img.src = URL.createObjectURL(currentImage);
        contentDiv.appendChild(img);
    }
    
    const textNode = document.createTextNode(content);
    contentDiv.appendChild(textNode);
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.id = 'loading-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<span class="loading"></span> <span class="loading"></span> <span class="loading"></span>';
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeLoadingMessage() {
    const loadingMsg = document.getElementById('loading-message');
    if (loadingMsg) {
        loadingMsg.remove();
    }
}

async function sendMessage() {
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        return;
    }
    
    // Disable send button
    sendButton.disabled = true;
    
    // Get config values
    const baseUrl = baseUrlInput.value.trim();
    const apiKey = apiKeyInput.value.trim();
    const model = modelInput.value.trim();
    const maxTokens = parseInt(maxTokensInput.value);
    const temperature = parseFloat(temperatureInput.value);
    
    // Validate API key
    if (!apiKey) {
        addMessage('error', '⚠️ Please enter your API key in the configuration above.');
        sendButton.disabled = false;
        return;
    }
    
    // Build message content
    let content;
    if (currentImageBase64) {
        // Image + text: content is an array
        content = [
            { type: "text", text: prompt },
            { type: "image", image: { b64: currentImageBase64 } }
        ];
    } else {
        // Text only: content is a string
        content = prompt;
    }
    
    // Add user message to chat
    addMessage('user', prompt);
    
    // Clear input
    promptInput.value = '';
    const imageToDisplay = currentImage;
    clearImage();
    
    // Show loading
    addLoadingMessage();
    
    try {
        // Make API request
        console.log('Sending request to:', `${baseUrl}/chat/completions`);
        console.log('Request body:', {
            model: model,
            messages: [
                {
                    role: 'user',
                    content: content
                }
            ],
            max_tokens: maxTokens,
            temperature: temperature
        });
        
        const response = await fetch(`${baseUrl}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: model,
                messages: [
                    {
                        role: 'user',
                        content: content
                    }
                ],
                max_tokens: maxTokens,
                temperature: temperature
            })
        });
        
        removeLoadingMessage();
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Error response:', errorData);
            const errorMsg = errorData.detail || errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMsg);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        // Extract assistant's reply
        const reply = data.choices?.[0]?.message?.content || '(empty response)';
        
        // Add assistant message
        addMessage('assistant', reply);
        
    } catch (error) {
        removeLoadingMessage();
        console.error('Error:', error);
        addMessage('error', `❌ Error: ${error.message}`, true);
    } finally {
        sendButton.disabled = false;
        promptInput.focus();
    }
}

// Expose clearImage to global scope for onclick handler
window.clearImage = clearImage;
