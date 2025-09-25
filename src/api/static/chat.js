/**
 * DAB Generator - Modern Chat Client
 * Enhanced with animations, better UX, and professional interactions
 */
class DABChatClient {
    constructor() {
        this.apiBase = window.location.origin;
        this.conversationId = null;
        this.isConnected = false;
        this.isProcessing = false;
        
        // DOM elements
        this.initializeElements();
        
        // Initialize the application
        this.init();
    }
    
    initializeElements() {
        // Main elements
        this.messagesContainer = document.getElementById('messages-container');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatForm = document.getElementById('chat-form');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.statusIndicator = document.getElementById('status-indicator');
        this.charCounter = document.getElementById('char-counter');
        this.loadingOverlay = document.getElementById('loading-overlay');
        
        // Status elements
        this.statusDot = this.statusIndicator.querySelector('.status-dot');
        this.statusText = this.statusIndicator.querySelector('.status-text');
    }
    
    init() {
        this.showLoadingOverlay('Initializing DAB Generator...');
        this.setupEventListeners();
        this.initializeApplication();
    }
    
    async initializeApplication() {
        try {
            await this.checkAPIHealth();
            this.setupInputBehavior();
            this.focusInput();
            
            // Hide welcome card after user starts typing
            this.setupWelcomeCardBehavior();
            
        } catch (error) {
            console.error('Initialization failed:', error);
            this.showErrorMessage('Failed to initialize. Please refresh the page.');
        } finally {
            this.hideLoadingOverlay();
        }
    }
    
    setupEventListeners() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Input changes and interactions
        this.messageInput.addEventListener('input', (e) => this.handleInputChange(e));
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.messageInput.addEventListener('paste', (e) => this.handlePaste(e));
        
        // Example prompt clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.example-card')) {
                const card = e.target.closest('.example-card');
                const prompt = card.getAttribute('data-prompt');
                this.selectExamplePrompt(prompt);
            }
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
        
        // Handle window focus for better UX
        window.addEventListener('focus', () => this.focusInput());
        
        // Handle connection changes
        window.addEventListener('online', () => this.handleConnectionChange(true));
        window.addEventListener('offline', () => this.handleConnectionChange(false));
    }
    
    setupWelcomeCardBehavior() {
        const welcomeCard = document.querySelector('.welcome-card');
        if (welcomeCard) {
            const observer = new MutationObserver(() => {
                const hasMessages = this.messagesContainer.children.length > 1;
                if (hasMessages) {
                    welcomeCard.style.transform = 'scale(0.95)';
                    welcomeCard.style.opacity = '0.7';
                    welcomeCard.style.transition = 'all 0.3s ease';
                }
            });
            observer.observe(this.messagesContainer, { childList: true });
        }
    }
    
    async checkAPIHealth() {
        try {
            this.updateStatus('checking', 'Connecting...');
            
            const response = await fetch(`${this.apiBase}/api/health`);
            const health = await response.json();
            
            if (health.status === 'healthy') {
                const statusText = `Connected • Claude: ${health.claude_configured ? 'Ready' : 'Setup needed'}`;
                this.updateStatus('connected', statusText);
                this.isConnected = true;
            } else {
                this.updateStatus('error', 'Service unavailable');
                this.isConnected = false;
            }
            
            return health;
        } catch (error) {
            this.updateStatus('error', 'Connection failed');
            this.isConnected = false;
            throw error;
        }
    }
    
    updateStatus(type, message) {
        this.statusDot.className = `status-dot ${type}`;
        this.statusText.textContent = message;
        
        // Add animation
        this.statusIndicator.style.transform = 'scale(1.05)';
        setTimeout(() => {
            this.statusIndicator.style.transform = 'scale(1)';
        }, 150);
    }
    
    setupInputBehavior() {
        // Set up smart placeholder rotation
        const placeholders = [
            "Ask me to generate bundles, analyze code, or optimize configurations...",
            "Try: Generate a bundle from job 662067900958232",
            "Try: Create bundles for my workspace code",
            "Try: Optimize my streaming job for development"
        ];
        
        let placeholderIndex = 0;
        setInterval(() => {
            if (!this.messageInput.value && !document.activeElement === this.messageInput) {
                placeholderIndex = (placeholderIndex + 1) % placeholders.length;
                this.messageInput.placeholder = placeholders[placeholderIndex];
            }
        }, 4000);
    }
    
    selectExamplePrompt(prompt) {
        this.messageInput.value = prompt;
        this.updateCharCounter();
        this.updateSendButton();
        this.autoResizeTextarea();
        
        // Add visual feedback
        this.messageInput.style.background = 'rgba(255, 107, 53, 0.05)';
        setTimeout(() => {
            this.messageInput.style.background = '';
        }, 300);
        
        this.focusInput();
        
        // Scroll to input
        this.messageInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    handleInputChange(e) {
        this.updateCharCounter();
        this.updateSendButton();
        this.autoResizeTextarea();
    }
    
    handleKeyDown(e) {
        // Send on Enter (but not Shift+Enter)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSubmit(e);
        }
        
        // Handle Escape to clear
        if (e.key === 'Escape') {
            this.clearInput();
        }
    }
    
    handlePaste(e) {
        // Handle large pastes gracefully
        setTimeout(() => {
            this.updateCharCounter();
            this.updateSendButton();
            this.autoResizeTextarea();
        }, 0);
    }
    
    updateCharCounter() {
        const length = this.messageInput.value.length;
        this.charCounter.textContent = length;
        
        // Change color based on limit
        const maxLength = parseInt(this.messageInput.getAttribute('maxlength'));
        const ratio = length / maxLength;
        
        if (ratio > 0.9) {
            this.charCounter.style.color = 'var(--color-error)';
        } else if (ratio > 0.7) {
            this.charCounter.style.color = 'var(--color-warning)';
        } else {
            this.charCounter.style.color = 'var(--color-gray-400)';
        }
    }
    
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        const canSend = hasText && this.isConnected && !this.isProcessing;
        
        this.sendButton.disabled = !canSend;
        
        // Visual feedback
        if (canSend && hasText) {
            this.sendButton.style.transform = 'scale(1.05)';
            this.sendButton.style.boxShadow = 'var(--shadow-lg)';
        } else {
            this.sendButton.style.transform = '';
            this.sendButton.style.boxShadow = '';
        }
    }
    
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        const scrollHeight = this.messageInput.scrollHeight;
        const maxHeight = 120;
        this.messageInput.style.height = Math.min(scrollHeight, maxHeight) + 'px';
    }
    
    focusInput() {
        if (!this.isProcessing && window.innerWidth > 768) {
            this.messageInput.focus();
        }
    }
    
    clearInput() {
        this.messageInput.value = '';
        this.updateCharCounter();
        this.updateSendButton();
        this.autoResizeTextarea();
        this.messageInput.style.height = '';
    }
    
    handleConnectionChange(isOnline) {
        this.isConnected = isOnline;
        if (isOnline) {
            this.checkAPIHealth();
        } else {
            this.updateStatus('error', 'Offline');
        }
        this.updateSendButton();
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message || !this.isConnected || this.isProcessing) return;
        
        this.sendMessage(message);
    }
    
    async sendMessage(message) {
        // Add user message immediately
        this.addUserMessage(message);
        
        // Clear input and update UI
        this.clearInput();
        this.setProcessingState(true);
        
        try {
            await this.streamChatResponse(message);
        } catch (error) {
            console.error('Chat error:', error);
            this.addErrorMessage(`Failed to send message: ${error.message}`);
        } finally {
            this.setProcessingState(false);
        }
    }
    
    setProcessingState(processing) {
        this.isProcessing = processing;
        this.updateSendButton();
        
        if (processing) {
            this.showTypingIndicator();
            this.updateStatus('checking', 'Processing...');
        } else {
            this.hideTypingIndicator();
            this.checkAPIHealth(); // Refresh status
        }
    }
    
    async streamChatResponse(message) {
        const payload = {
            message: message,
            conversation_id: this.conversationId
        };
        
        try {
            const response = await fetch(`${this.apiBase}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Read the response as a stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let currentMessageElement = null;
            let isFirstMessage = true;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (isFirstMessage && data.type === 'message') {
                                this.hideTypingIndicator();
                                isFirstMessage = false;
                            }
                            
                            currentMessageElement = this.handleStreamMessage(data, currentMessageElement);
                        } catch (e) {
                            console.warn('Failed to parse SSE data:', line, e);
                        }
                    }
                }
            }
        } catch (error) {
            this.hideTypingIndicator();
            throw error;
        }
    }
    
    handleStreamMessage(data, currentMessageElement) {
        switch (data.type) {
            case 'message':
                if (currentMessageElement) {
                    // Append to existing message with typing effect
                    this.appendToMessage(currentMessageElement, data.content);
                } else {
                    // Create new message
                    currentMessageElement = this.addAssistantMessage(data.content);
                }
                break;
                
            case 'tool_use':
                this.addToolUseIndicator(data.tool, data.status);
                break;
                
            case 'file_generated':
                this.addFileDownload(data.filename, data.download_url);
                break;
                
            case 'complete':
                this.conversationId = data.conversation_id;
                if (data.files_generated > 0) {
                    this.addCompletionMessage(data);
                }
                break;
                
            case 'error':
                this.addErrorMessage(data.content);
                break;
        }
        
        this.scrollToBottom();
        return currentMessageElement;
    }
    
    addUserMessage(content) {
        const messageDiv = this.createMessageBubble('user', content);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        return messageDiv;
    }
    
    addAssistantMessage(content) {
        const messageDiv = this.createMessageBubble('assistant', content);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        return messageDiv;
    }
    
    createMessageBubble(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${role}`;
        
        const avatar = role === 'user' ? '👤' : '🤖';
        const avatarClass = role === 'user' ? 'user' : 'assistant';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-gradient"></div>
                <span class="avatar-icon">${avatar}</span>
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessageContent(content)}</div>
            </div>
        `;
        
        // Add entrance animation
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            messageDiv.style.transition = 'all 0.3s ease';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 50);
        
        return messageDiv;
    }
    
    appendToMessage(messageElement, content) {
        const textElement = messageElement.querySelector('.message-text');
        if (textElement) {
            // Add typing effect for streaming
            const newContent = this.formatMessageContent(content);
            textElement.innerHTML += newContent;
            
            // Highlight new content briefly
            const tempSpan = document.createElement('span');
            tempSpan.innerHTML = newContent;
            tempSpan.style.background = 'rgba(255, 107, 53, 0.1)';
            tempSpan.style.borderRadius = '2px';
            
            setTimeout(() => {
                tempSpan.style.background = '';
            }, 500);
            
            this.scrollToBottom();
        }
    }
    
    addToolUseIndicator(tool, status) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble assistant';
        
        const statusEmoji = status === 'starting' ? '⚡' : '✅';
        const toolName = tool.replace('mcp__databricks-mcp__', '').replace(/_/g, ' ');
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-gradient"></div>
                <span class="avatar-icon">🔧</span>
            </div>
            <div class="message-content" style="background: linear-gradient(135deg, var(--color-info), var(--color-accent)); color: white; border-color: var(--color-info);">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 500;">
                    <span>${statusEmoji}</span>
                    <span>Using: ${toolName}</span>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Add pulse animation
        const avatar = messageDiv.querySelector('.message-avatar');
        avatar.style.animation = 'pulse 1s ease-in-out infinite';
        setTimeout(() => avatar.style.animation = '', 2000);
    }
    
    addFileDownload(filename, downloadUrl) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble assistant';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-gradient"></div>
                <span class="avatar-icon">📦</span>
            </div>
            <div class="message-content" style="background: linear-gradient(135deg, var(--color-success), #38A169); color: white; border-color: var(--color-success);">
                <div style="text-align: center;">
                    <div style="margin-bottom: 12px; font-weight: 600;">✅ Bundle Generated!</div>
                    <a href="${downloadUrl}" class="download-button" download="${filename}" 
                       style="display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.2); color: white; text-decoration: none; padding: 12px 20px; border-radius: 12px; font-weight: 500; transition: all 0.3s ease; backdrop-filter: blur(10px);"
                       onmouseover="this.style.background='rgba(255,255,255,0.3)'; this.style.transform='translateY(-2px)'"
                       onmouseout="this.style.background='rgba(255,255,255,0.2)'; this.style.transform='translateY(0)'">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                            <polyline points="7,10 12,15 17,10"/>
                            <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        Download ${filename}
                    </a>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addCompletionMessage(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble assistant';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <div class="avatar-gradient"></div>
                <span class="avatar-icon">🎉</span>
            </div>
            <div class="message-content">
                <div style="text-align: center; padding: 8px;">
                    <div style="font-size: 18px; margin-bottom: 8px;">🎉 Task Complete!</div>
                    <div style="color: var(--color-gray-600); font-size: 14px;">
                        Generated ${data.files_generated} file${data.files_generated !== 1 ? 's' : ''} • 
                        Ready for deployment
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addErrorMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble assistant';
        
        messageDiv.innerHTML = `
            <div class="message-avatar" style="background: var(--color-error);">
                <span class="avatar-icon">⚠️</span>
            </div>
            <div class="message-content" style="background: #FED7D7; border-color: var(--color-error); color: #C53030;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 16px;">❌</span>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 4px;">Error</div>
                        <div style="font-size: 14px; opacity: 0.9;">${content}</div>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessageContent(content) {
        return content
            .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
            .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: var(--color-gray-100); padding: 2px 6px; border-radius: 4px; font-family: monospace;">$1</code>')
            .replace(/\\n\\n/g, '</p><p>')
            .replace(/\\n/g, '<br>');
    }
    
    showTypingIndicator() {
        this.typingIndicator.classList.remove('hidden');
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.classList.add('hidden');
    }
    
    showLoadingOverlay(message) {
        this.loadingOverlay.classList.remove('hidden');
        const loadingText = this.loadingOverlay.querySelector('.loading-text');
        if (loadingText) loadingText.textContent = message;
    }
    
    hideLoadingOverlay() {
        this.loadingOverlay.classList.add('hidden');
    }
    
    showErrorMessage(message) {
        // Create a temporary error notification
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--color-error);
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            z-index: var(--z-tooltip);
            animation: slideInRight 0.3s ease;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => document.body.removeChild(errorDiv), 300);
        }, 5000);
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTo({
            top: this.messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Add a subtle loading animation to the page
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.5s ease';
    
    setTimeout(() => {
        document.body.style.opacity = '1';
        new DABChatClient();
    }, 100);
});

// Add some utility functions for enhanced UX
window.addEventListener('beforeunload', (e) => {
    // Warn user if they're in the middle of a conversation
    const client = window.dabChatClient;
    if (client && client.isProcessing) {
        e.preventDefault();
        return e.returnValue = 'You have an active conversation. Are you sure you want to leave?';
    }
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + / to focus input
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        const messageInput = document.getElementById('message-input');
        if (messageInput) messageInput.focus();
    }
});