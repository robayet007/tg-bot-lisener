// API Configuration - Use relative URLs to work on any domain (localhost, Fly.io, Vercel)
const API_BASE_URL = 'https://tg-bot-lisener.vercel.app'; // Empty string = same origin

// Debug mode (can be enabled via console: window.DEBUG = true)
window.DEBUG = window.DEBUG || false;

// DOM Elements
let statusIndicator, statusText, appStatus, botStatus, listenerStatus;
let commandForm, rawMessageForm, sendCommandBtn, sendRawBtn;
let responseContent, copyBtn, errorDisplay;

// Health check interval
let healthCheckInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing API Tester...');
    
    // Get DOM elements
    statusIndicator = document.getElementById('statusIndicator');
    statusText = document.getElementById('statusText');
    appStatus = document.getElementById('appStatus');
    botStatus = document.getElementById('botStatus');
    listenerStatus = document.getElementById('listenerStatus');
    commandForm = document.getElementById('commandForm');
    rawMessageForm = document.getElementById('rawMessageForm');
    sendCommandBtn = document.getElementById('sendCommandBtn');
    sendRawBtn = document.getElementById('sendRawBtn');
    responseContent = document.getElementById('responseContent');
    copyBtn = document.getElementById('copyBtn');
    errorDisplay = document.getElementById('errorDisplay');
    
    // Verify all elements exist
    if (!commandForm || !rawMessageForm) {
        logError('Critical: Form elements not found!', { commandForm, rawMessageForm });
        showError('Error: Page elements not loaded correctly. Please refresh the page.');
        return;
    }
    
    console.log('✓ DOM elements loaded');
    console.log(`📡 API Base URL: ${API_BASE_URL}`);
    
    // Check health on load
    checkHealth();
    
    // Set up auto-refresh health check every 15 seconds (reduced frequency to avoid timeouts)
    healthCheckInterval = setInterval(checkHealth, 15000);
    
    // Set up form handlers
    commandForm.addEventListener('submit', handleCommandSubmit);
    rawMessageForm.addEventListener('submit', handleRawMessageSubmit);
    
    // Set up copy button
    if (copyBtn) {
        copyBtn.addEventListener('click', copyResponse);
    }
    
    // Set up connection test button if it exists
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', testConnection);
    }
    
    console.log('✓ Event listeners attached');
});

// Logging Functions
function logError(message, details = null) {
    console.error(`❌ ${message}`, details || '');
    if (window.DEBUG && details) {
        console.trace('Error stack trace');
    }
}

function logRequest(method, url, data = null) {
    if (window.DEBUG) {
        console.log(`📤 ${method} ${url}`, data || '');
    }
}

function logResponse(method, url, status, data = null) {
    if (window.DEBUG) {
        console.log(`📥 ${method} ${url} [${status}]`, data || '');
    }
}

function logInfo(message, data = null) {
    if (window.DEBUG) {
        console.log(`ℹ️ ${message}`, data || '');
    }
}

// Fetch with timeout
async function fetchWithTimeout(url, options = {}, timeout = 30000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError' || error.name === 'TimeoutError') {
            throw new Error(`Request timeout: The server took too long to respond (${timeout/1000}s). The API might be slow or unreachable.`);
        }
        // Check for network errors
        if (error.message && error.message.includes('Failed to fetch')) {
            throw new Error('Network error: Cannot reach the server. Check your internet connection and that the API is running.');
        }
        throw error;
    }
}

// Health Check Function
async function checkHealth() {
    try {
        logRequest('GET', `${API_BASE_URL}/health`);
        const response = await fetchWithTimeout(`${API_BASE_URL}/health`, {
            method: 'GET'
        }, 15000); // Increased timeout to 15 seconds
        
        if (!response.ok) {
            throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        logResponse('GET', '/health', response.status, data);
        
        // Update status indicator
        if (data.status === 'ok') {
            statusIndicator.classList.remove('offline');
            statusIndicator.classList.add('online');
            statusText.textContent = 'Online';
        } else {
            statusIndicator.classList.remove('online');
            statusIndicator.classList.add('offline');
            statusText.textContent = 'Offline';
        }
        
        // Update health info
        appStatus.textContent = data.status === 'ok' ? '✓ OK' : '✗ Error';
        botStatus.textContent = data.bot_initialized ? '✓ Yes' : '✗ No';
        listenerStatus.textContent = data.listener_running ? '✓ Running' : '✗ Stopped';
        
    } catch (error) {
        logError('Health check failed', error);
        
        // Connection error
        statusIndicator.classList.remove('online');
        statusIndicator.classList.add('offline');
        
        const errorMsg = getErrorMessage(error);
        if (errorMsg.includes('timeout')) {
            statusText.textContent = 'Timeout';
            appStatus.textContent = '⏱ Timeout';
        } else {
            statusText.textContent = 'Offline';
            appStatus.textContent = '✗ Error';
        }
        
        botStatus.textContent = '-';
        listenerStatus.textContent = '-';
        
        // Show error in error display if available (only for manual checks, not auto-refresh)
        // Don't show error display for auto health checks to avoid spam
    }
}

// Test Connection Function
async function testConnection() {
    const testBtn = document.getElementById('testConnectionBtn');
    if (testBtn) {
        testBtn.disabled = true;
        testBtn.textContent = 'Testing...';
    }
    
    try {
        logInfo('Testing connection to API...');
        showErrorDisplay('Testing connection...', 'info');
        
        const response = await fetchWithTimeout(`${API_BASE_URL}/health`, {
            method: 'GET'
        }, 20000); // Increased timeout to 20 seconds for manual test
        
        if (response.ok) {
            const data = await response.json();
            showErrorDisplay(`✓ Connection successful! Status: ${data.status}`, 'success');
            logInfo('Connection test successful', data);
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        const errorMsg = getErrorMessage(error);
        showErrorDisplay(`✗ Connection failed: ${errorMsg}`, 'error');
        logError('Connection test failed', error);
    } finally {
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.textContent = 'Test Connection';
        }
    }
}

// Get user-friendly error message
function getErrorMessage(error) {
    if (error.message) {
        return error.message;
    }
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        return 'Network error: Cannot connect to server. Check your internet connection and CORS settings.';
    }
    
    if (error.name === 'AbortError') {
        return 'Request timeout: The server took too long to respond';
    }
    
    return error.toString();
}

// Handle Command Form Submit
async function handleCommandSubmit(e) {
    e.preventDefault();
    logInfo('Command form submitted');
    
    const command = document.getElementById('command').value.trim();
    if (!command) {
        showError('Please enter a command');
        return;
    }
    
    logInfo(`Sending command: "${command}"`);
    
    // Disable button and show loading
    sendCommandBtn.disabled = true;
    sendCommandBtn.innerHTML = '<span class="spinner"></span> Sending...';
    
    // Clear any previous errors
    if (errorDisplay) {
        clearErrorDisplay();
    }
    
    try {
        const response = await sendCommand(command);
        logInfo('Command sent successfully', response);
        showResponse(response, 'success');
        showErrorDisplay('✓ Command sent successfully!', 'success');
    } catch (error) {
        const errorMsg = getErrorMessage(error);
        logError('Failed to send command', { command, error });
        showError(errorMsg);
        showErrorDisplay(`✗ Error: ${errorMsg}`, 'error');
    } finally {
        // Re-enable button
        sendCommandBtn.disabled = false;
        sendCommandBtn.textContent = 'Send Command';
    }
}

// Handle Raw Message Form Submit
async function handleRawMessageSubmit(e) {
    e.preventDefault();
    logInfo('Raw message form submitted');
    
    const prefix = document.getElementById('prefix').value.trim();
    const uid = document.getElementById('uid').value.trim();
    const diamonds = document.getElementById('diamonds').value.trim();
    
    if (!prefix || !uid || !diamonds) {
        showError('Please fill in all fields');
        return;
    }
    
    logInfo(`Sending raw message: prefix="${prefix}", uid="${uid}", diamonds="${diamonds}"`);
    
    // Disable button and show loading
    sendRawBtn.disabled = true;
    sendRawBtn.innerHTML = '<span class="spinner"></span> Sending...';
    
    // Clear any previous errors
    if (errorDisplay) {
        clearErrorDisplay();
    }
    
    try {
        const response = await sendRawMessage(prefix, uid, diamonds);
        logInfo('Raw message sent successfully', response);
        // Determine response class based on status
        const responseClass = response.success ? 'success' : 
                             (response.status === 'failed' ? 'error' : 'pending');
        showResponse(response, responseClass);
        
        if (response.success) {
            showErrorDisplay('✓ Message sent successfully!', 'success');
        } else {
            showErrorDisplay(`⚠ Status: ${response.status || 'pending'}`, 'warning');
        }
    } catch (error) {
        const errorMsg = getErrorMessage(error);
        logError('Failed to send raw message', { prefix, uid, diamonds, error });
        showError(errorMsg);
        showErrorDisplay(`✗ Error: ${errorMsg}`, 'error');
    } finally {
        // Re-enable button
        sendRawBtn.disabled = false;
        sendRawBtn.textContent = 'Send Raw Message';
    }
}

// Send Command API Call
async function sendCommand(command) {
    const url = `${API_BASE_URL}/api/send`;
    const payload = { command };
    
    logRequest('POST', url, payload);
    
    try {
        const response = await fetchWithTimeout(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        }, 30000);
        
        logResponse('POST', '/api/send', response.status);
        
        if (!response.ok) {
            let errorData = {};
            try {
                errorData = await response.json();
            } catch (e) {
                logError('Failed to parse error response', e);
            }
            
            const errorMsg = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
            logError('API error response', { status: response.status, error: errorData });
            throw new Error(errorMsg);
        }
        
        const data = await response.json();
        logResponse('POST', '/api/send', response.status, data);
        return data;
        
    } catch (error) {
        // Check for CORS error
        if (error.message.includes('CORS') || error.message.includes('Failed to fetch')) {
            logError('CORS error detected', error);
            throw new Error('CORS Error: The server may not allow requests from this origin. Check CORS configuration.');
        }
        
        // Check for network error
        if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
            logError('Network error detected', error);
            throw new Error('Network Error: Cannot connect to the server. Please check your internet connection and that the API is running.');
        }
        
        throw error;
    }
}

// Send Raw Message API Call
async function sendRawMessage(prefix, uid, diamonds) {
    const url = `${API_BASE_URL}/api/send-message-raw`;
    const payload = { prefix, uid, diamonds };
    
    logRequest('POST', url, payload);
    
    try {
        const response = await fetchWithTimeout(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        }, 30000);
        
        logResponse('POST', '/api/send-message-raw', response.status);
        
        if (!response.ok) {
            let errorData = {};
            try {
                errorData = await response.json();
            } catch (e) {
                logError('Failed to parse error response', e);
            }
            
            const errorMsg = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
            logError('API error response', { status: response.status, error: errorData });
            throw new Error(errorMsg);
        }
        
        const data = await response.json();
        logResponse('POST', '/api/send-message-raw', response.status, data);
        return data;
        
    } catch (error) {
        // Check for CORS error
        if (error.message.includes('CORS') || error.message.includes('Failed to fetch')) {
            logError('CORS error detected', error);
            throw new Error('CORS Error: The server may not allow requests from this origin. Check CORS configuration.');
        }
        
        // Check for network error
        if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
            logError('Network error detected', error);
            throw new Error('Network Error: Cannot connect to the server. Please check your internet connection and that the API is running.');
        }
        
        throw error;
    }
}

// Show Response
function showResponse(data, className = 'success') {
    // Remove empty message
    responseContent.innerHTML = '';
    responseContent.className = `response-content ${className}`;
    
    // Format JSON with indentation
    const formattedJson = JSON.stringify(data, null, 2);
    
    // Create pre element for better formatting
    const pre = document.createElement('pre');
    pre.textContent = formattedJson;
    responseContent.appendChild(pre);
    
    // Show copy button
    if (copyBtn) {
        copyBtn.style.display = 'inline-flex';
    }
    
    // Store current response for copying
    responseContent.dataset.response = formattedJson;
    
    // Scroll to response
    responseContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show Error
function showError(message) {
    logError('Showing error to user', message);
    const errorData = {
        success: false,
        error: message,
        timestamp: new Date().toISOString()
    };
    showResponse(errorData, 'error');
}

// Show Error Display (top banner)
function showErrorDisplay(message, type = 'error') {
    if (!errorDisplay) return;
    
    errorDisplay.textContent = message;
    errorDisplay.className = `error-display ${type}`;
    errorDisplay.style.display = 'block';
    
    // Auto-hide after 5 seconds for success/info messages
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            clearErrorDisplay();
        }, 5000);
    }
}

// Clear Error Display
function clearErrorDisplay() {
    if (errorDisplay) {
        errorDisplay.style.display = 'none';
        errorDisplay.textContent = '';
        errorDisplay.className = 'error-display';
    }
}

// Copy Response to Clipboard
async function copyResponse() {
    const textToCopy = responseContent.dataset.response || responseContent.textContent;
    
    try {
        await navigator.clipboard.writeText(textToCopy);
        
        // Show feedback
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✓ Copied!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    } catch (error) {
        logError('Failed to copy to clipboard', error);
        alert('Failed to copy to clipboard');
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (healthCheckInterval) {
        clearInterval(healthCheckInterval);
    }
});

// Export for debugging
window.testConnection = testConnection;
window.DEBUG = window.DEBUG || false;

console.log('✓ API Tester JavaScript loaded');
console.log('💡 Tip: Set window.DEBUG = true in console to enable debug logging');
