(function() {
  const config = window.brochat || {};
  
  // Find script element to support data-bot-id
  let currentScript = document.currentScript;
  if (!currentScript) {
    const scripts = document.getElementsByTagName('script');
    for (let i = 0; i < scripts.length; i++) {
      if (scripts[i].src && scripts[i].src.includes('widget.js')) {
        currentScript = scripts[i];
        break;
      }
    }
  }

  const dataBotId = currentScript ? currentScript.getAttribute('data-bot-id') : null;
  const botId = config.botId || dataBotId;

  if (!botId) {
    console.error('BroChat: botId or data-bot-id attribute is required');
    return;
  }

  // Configuration
  const position = config.position === 'left' ? 'left' : 'right';
  let primaryColor = config.primaryColor;
  
  // Try to detect API base URL from current script src
  let apiBaseUrl = 'https://brochat-gxkm.onrender.com';
  const scripts = document.getElementsByTagName('script');
  for (let i = 0; i < scripts.length; i++) {
    const src = scripts[i].src;
    if (src && src.includes('widget.js')) {
      try {
        const url = new URL(src);
        apiBaseUrl = url.origin;
      } catch(e) {}
      break;
    }
  }

  // Generate visitor ID
  let visitorId = localStorage.getItem('brochat_visitor_id');
  if (!visitorId) {
    visitorId = 'visitor_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('brochat_visitor_id', visitorId);
  }

  // Create UI container
  const container = document.createElement('div');
  container.className = 'brochat-widget-container brochat-pos-' + position;
  document.body.appendChild(container);

  // CSS injection
  function injectCSS(color) {
    const defaultColor = '#c6ff6d';
    const themeColor = color || defaultColor;
    
    const style = document.createElement('style');
    style.innerHTML = `
      .brochat-widget-container {
        position: fixed;
        bottom: 24px;
        z-index: 999999;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        box-sizing: border-box;
      }
      .brochat-pos-right { right: 24px; }
      .brochat-pos-left { left: 24px; }
      .brochat-widget-container * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }
      
      .brochat-bubble {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background-color: ${themeColor};
        box-shadow: 0 4px 12px rgba(20, 58, 53, 0.15);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.3s ease;
        position: absolute;
        bottom: 0;
      }
      .brochat-pos-right .brochat-bubble { right: 0; }
      .brochat-pos-left .brochat-bubble { left: 0; }
      
      .brochat-bubble:hover {
        transform: scale(1.05);
      }
      .brochat-pulse {
        animation: brochat-pulse-anim 2s infinite;
      }
      @keyframes brochat-pulse-anim {
        0% { box-shadow: 0 0 0 0 rgba(198, 255, 109, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(198, 255, 109, 0); }
        100% { box-shadow: 0 0 0 0 rgba(198, 255, 109, 0); }
      }
      
      .brochat-bubble svg {
        width: 28px;
        height: 28px;
        fill: #143a35;
      }

      .brochat-window {
        position: absolute;
        bottom: 76px;
        width: 380px;
        height: 520px;
        background: #ffffff;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(20, 58, 53, 0.15);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        opacity: 0;
        pointer-events: none;
        transform: translateY(20px);
        transition: opacity 0.3s ease, transform 0.3s ease;
      }
      .brochat-pos-right .brochat-window { right: 0; transform-origin: bottom right; }
      .brochat-pos-left .brochat-window { left: 0; transform-origin: bottom left; }
      
      .brochat-window.brochat-open {
        opacity: 1;
        pointer-events: all;
        transform: translateY(0);
      }

      .brochat-header {
        background: #143a35;
        padding: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #ffffff;
      }
      
      .brochat-header-info {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      
      .brochat-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: ${themeColor};
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .brochat-avatar svg {
        width: 20px;
        height: 20px;
        fill: #143a35;
      }
      
      .brochat-bot-details {
        display: flex;
        flex-direction: column;
      }
      .brochat-bot-name {
        font-weight: 600;
        font-size: 16px;
      }
      .brochat-status {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #dce7e0;
      }
      .brochat-status-dot {
        width: 8px;
        height: 8px;
        background: #4caf50;
        border-radius: 50%;
      }

      .brochat-close-btn {
        background: none;
        border: none;
        color: #ffffff;
        cursor: pointer;
        padding: 4px;
        display: flex;
        transition: transform 0.2s;
      }
      .brochat-close-btn:hover {
        transform: scale(1.1);
      }
      .brochat-close-btn svg {
        width: 24px;
        height: 24px;
        fill: currentColor;
      }

      .brochat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: #ffffff;
      }
      
      .brochat-message {
        max-width: 85%;
        padding: 12px 16px;
        border-radius: 20px;
        font-size: 14px;
        line-height: 1.4;
        word-wrap: break-word;
        animation: brochat-fade-in 0.3s ease;
      }
      
      @keyframes brochat-fade-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }

      .brochat-message.bot {
        align-self: flex-start;
        background: #e6eeea;
        color: #102d2a;
        border-bottom-left-radius: 4px;
      }
      .brochat-message.user {
        align-self: flex-end;
        background: #1c5047;
        color: #ffffff;
        border-bottom-right-radius: 4px;
      }
      
      .brochat-message-time {
        font-size: 10px;
        opacity: 0.6;
        margin-top: 4px;
        text-align: right;
      }

      .brochat-typing {
        display: none;
        align-items: center;
        gap: 4px;
        padding: 12px 16px;
        background: #e6eeea;
        border-radius: 20px;
        border-bottom-left-radius: 4px;
        align-self: flex-start;
        width: fit-content;
      }
      .brochat-typing.active {
        display: flex;
      }
      .brochat-dot {
        width: 6px;
        height: 6px;
        background: #58716a;
        border-radius: 50%;
        animation: brochat-bounce 1.4s infinite ease-in-out both;
      }
      .brochat-dot:nth-child(1) { animation-delay: -0.32s; }
      .brochat-dot:nth-child(2) { animation-delay: -0.16s; }
      
      @keyframes brochat-bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
      }

      .brochat-input-area {
        padding: 16px;
        border-top: 1px solid #dce7e0;
        display: flex;
        gap: 12px;
        background: #ffffff;
        align-items: center;
      }
      
      .brochat-input {
        flex: 1;
        border: 1px solid #dce7e0;
        border-radius: 24px;
        padding: 12px 16px;
        font-size: 14px;
        outline: none;
        transition: border-color 0.2s;
        color: #102d2a;
      }
      .brochat-input:focus {
        border-color: ${themeColor};
      }
      .brochat-input:disabled {
        background: #f5f8f6;
        cursor: not-allowed;
      }
      
      .brochat-send-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: ${themeColor};
        border: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s, opacity 0.2s;
      }
      .brochat-send-btn:hover {
        transform: scale(1.05);
      }
      .brochat-send-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .brochat-send-btn svg {
        width: 18px;
        height: 18px;
        fill: #143a35;
        margin-left: 2px;
      }

      @media (max-width: 500px) {
        .brochat-widget-container {
          bottom: 16px;
        }
        .brochat-pos-right { right: 16px; }
        .brochat-pos-left { left: 16px; }
        
        .brochat-window {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          width: 100vw;
          height: 100vh;
          border-radius: 0;
          transform: translateY(100%);
        }
        
        .brochat-close-btn svg {
          transform: rotate(-90deg);
        }
      }
    `;
    document.head.appendChild(style);
  }

  // Build DOM
  function buildUI(botInfo) {
    const botName = botInfo.name || 'Assistant';
    
    container.innerHTML = `
      <div class="brochat-window" id="brochat-window">
        <div class="brochat-header">
          <div class="brochat-header-info">
            <div class="brochat-avatar">
              <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>
            </div>
            <div class="brochat-bot-details">
              <span class="brochat-bot-name">${botName}</span>
              <div class="brochat-status">
                <span class="brochat-status-dot"></span> Online
              </div>
            </div>
          </div>
          <button class="brochat-close-btn" id="brochat-close">
            <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
          </button>
        </div>
        <div class="brochat-messages" id="brochat-messages">
          <div class="brochat-typing" id="brochat-typing">
            <div class="brochat-dot"></div>
            <div class="brochat-dot"></div>
            <div class="brochat-dot"></div>
          </div>
        </div>
        <div class="brochat-input-area">
          <input type="text" class="brochat-input" id="brochat-input" placeholder="Type a message..." />
          <button class="brochat-send-btn" id="brochat-send">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
      </div>
      <div class="brochat-bubble brochat-pulse" id="brochat-bubble">
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
      </div>
    `;

    const windowEl = document.getElementById('brochat-window');
    const bubbleEl = document.getElementById('brochat-bubble');
    const closeBtn = document.getElementById('brochat-close');
    const messagesEl = document.getElementById('brochat-messages');
    const inputEl = document.getElementById('brochat-input');
    const sendBtn = document.getElementById('brochat-send');
    const typingEl = document.getElementById('brochat-typing');

    let isOpen = false;

    // Toggle chat
    function toggleChat() {
      isOpen = !isOpen;
      if (isOpen) {
        windowEl.classList.add('brochat-open');
        bubbleEl.classList.remove('brochat-pulse');
        setTimeout(() => inputEl.focus(), 300);
      } else {
        windowEl.classList.remove('brochat-open');
      }
    }

    bubbleEl.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Initial Welcome Message
    if (botInfo.welcomeMessage) {
      appendMessage(botInfo.welcomeMessage, 'bot');
    } else {
      appendMessage('Hi there! How can I help you today?', 'bot');
    }

    function formatTime() {
      const d = new Date();
      let h = d.getHours();
      let m = d.getMinutes();
      const ampm = h >= 12 ? 'PM' : 'AM';
      h = h % 12;
      h = h ? h : 12;
      m = m < 10 ? '0' + m : m;
      return h + ':' + m + ' ' + ampm;
    }

    function appendMessage(text, sender) {
      const msgDiv = document.createElement('div');
      msgDiv.className = 'brochat-message ' + sender;
      
      const content = document.createElement('div');
      content.textContent = text;
      msgDiv.appendChild(content);

      const timeDiv = document.createElement('div');
      timeDiv.className = 'brochat-message-time';
      timeDiv.textContent = formatTime();
      msgDiv.appendChild(timeDiv);

      messagesEl.insertBefore(msgDiv, typingEl);
      scrollToBottom();
    }

    function scrollToBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    async function sendMessage() {
      const text = inputEl.value.trim();
      if (!text) return;

      inputEl.value = '';
      inputEl.disabled = true;
      sendBtn.disabled = true;

      appendMessage(text, 'user');
      typingEl.classList.add('active');
      scrollToBottom();

      try {
        const response = await fetch(`${apiBaseUrl}/api/chat/${botId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, visitor_id: visitorId })
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const data = await response.json();
        
        let reply = data.answer || data.response || data.message || data.text || data.reply;
        if (!reply && typeof data === 'string') reply = data;
        if (!reply) reply = "I'm not sure how to respond to that.";

        appendMessage(reply, 'bot');
      } catch (error) {
        console.error('BroChat Error:', error);
        appendMessage('Sorry, something went wrong. Please try again later.', 'bot');
      } finally {
        typingEl.classList.remove('active');
        inputEl.disabled = false;
        sendBtn.disabled = false;
        inputEl.focus();
        scrollToBottom();
      }
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }

  // Init
  async function init() {
    try {
      const response = await fetch(`${apiBaseUrl}/api/bots/${botId}/widget-config`);
      if (response.ok) {
        const data = await response.json();
        if (!primaryColor && data.theme_color) {
          primaryColor = data.theme_color;
        }
        injectCSS(primaryColor);
        buildUI({
          name: data.name,
          welcomeMessage: data.welcome_message
        });
      } else {
        throw new Error('Failed to fetch config');
      }
    } catch (e) {
      console.warn('BroChat: using default config', e);
      injectCSS(primaryColor);
      buildUI({
        name: 'Chat Bot',
        welcomeMessage: 'Hello! How can I help?'
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
