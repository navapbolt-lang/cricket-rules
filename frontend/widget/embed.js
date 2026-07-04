(function () {
  'use strict';

  const script = document.currentScript;
  if (!script) return;

  const config = {
    partner: script.dataset.partner || 'unknown',
    brandColor: script.dataset.brandColor || '#1a1a2e',
    logo: script.dataset.logo || '',
    position: script.dataset.position || 'right',
    apiBase: script.dataset.apiBase || 'https://api.cricketrules.ai/api/v1',
    greeting: script.dataset.greeting || 'Ask me any cricket rules question. I\'ll answer with exact law citations.',
    placeholder: script.dataset.placeholder || 'Ask a cricket rules question...',
  };

  const SESSION_ID = 'cr_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
  let selectedFormat = 'odi';
  let streamingAbort = null;

  const shadowHost = document.createElement('div');
  shadowHost.id = 'cr-widget-host';
  document.body.appendChild(shadowHost);

  const shadow = shadowHost.attachShadow({ mode: 'closed' });

  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = [
      '.cr-widget-button{position:fixed;bottom:24px;right:var(--widget-pos,24px);width:56px;height:56px;border-radius:50%;background:var(--brand-color,#1a1a2e);color:#fff;border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,0.25);z-index:999999;display:flex;align-items:center;justify-content:center;transition:transform .2s,box-shadow .2s}',
      '.cr-widget-button:hover{transform:scale(1.08);box-shadow:0 6px 24px rgba(0,0,0,0.35)}',
      '.cr-widget-sidebar{position:fixed;bottom:24px;right:var(--widget-pos,24px);width:380px;height:600px;max-height:calc(100vh - 48px);background:#fff;border-radius:16px;box-shadow:0 8px 40px rgba(0,0,0,0.18);z-index:999999;display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px;line-height:1.5;color:#1a1a2e}',
      '.cr-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:var(--brand-color,#1a1a2e);color:#fff;flex-shrink:0}',
      '.cr-header-logo{display:flex;align-items:center;gap:10px;font-weight:600;font-size:15px}',
      '.cr-header-logo img{width:28px;height:28px;border-radius:50%;object-fit:cover}',
      '.cr-default-icon{font-size:24px}',
      '.cr-btn-icon{background:0 0;border:none;color:#fff;font-size:18px;cursor:pointer;padding:4px 8px;border-radius:6px;opacity:.8}',
      '.cr-btn-icon:hover{opacity:1}',
      '.cr-messages{flex:1;overflow-y:auto;padding:12px 16px;display:flex;flex-direction:column;gap:10px;background:#f8f9fc}',
      '.cr-messages::-webkit-scrollbar{width:5px}',
      '.cr-messages::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}',
      '.cr-message{display:flex;gap:8px;max-width:90%;flex-wrap:wrap}',
      '.cr-user{align-self:flex-end;flex-direction:row-reverse}',
      '.cr-bot{align-self:flex-start}',
      '.cr-avatar{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;background:#e8ecf4}',
      '.cr-bubble{background:#fff;padding:10px 14px;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,0.06);word-wrap:break-word}',
      '.cr-user .cr-bubble{background:var(--brand-color,#1a1a2e);color:#fff;border-bottom-right-radius:4px}',
      '.cr-bot .cr-bubble{background:#fff;border-bottom-left-radius:4px}',
      '.cr-bubble p{margin:0}',
      '.cr-bubble p+p{margin-top:8px}',
      '.cr-typing .cr-bubble{display:flex;gap:4px;align-items:center;padding:14px 18px}',
      '.cr-dot{width:8px;height:8px;background:#999;border-radius:50%;animation:cr-bounce 1.4s ease-in-out both}',
      '.cr-dot:nth-child(1){animation-delay:-.32s}',
      '.cr-dot:nth-child(2){animation-delay:-.16s}',
      '@keyframes cr-bounce{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}',

      '.cr-feedback{display:flex;gap:8px;margin-top:8px}',
      '.cr-fb-btn{background:#fff;border:1px solid #ddd;border-radius:8px;padding:4px 10px;font-size:13px;cursor:pointer;opacity:.7;transition:all .15s}',
      '.cr-fb-btn:hover{opacity:1;border-color:#999;background:#f5f5f5}',
      '.cr-bot .cr-feedback{width:100%;margin-left:38px}',
      '.cr-suggestions{display:flex;flex-wrap:wrap;gap:6px;padding:4px 0}',
      '.cr-suggestions-label{width:100%;font-size:11px;color:#888;margin-bottom:2px}',
      '.cr-suggestion-btn{background:#eef2ff;border:none;border-radius:12px;padding:6px 12px;font-size:12px;color:var(--brand-color,#1a1a2e);cursor:pointer;text-align:left;max-width:100%;word-wrap:break-word}',
      '.cr-suggestion-btn:hover{background:#dde4ff}',
      '.cr-input-area{border-top:1px solid #e8e8e8;padding:10px 12px;background:#fff;flex-shrink:0}',
      '.cr-format-bar{display:flex;gap:4px;margin-bottom:8px}',
      '.cr-format-btn{flex:1;padding:5px 0;border:1px solid #e0e0e0;border-radius:6px;background:#f8f8f8;font-size:12px;font-weight:500;cursor:pointer;color:#555}',
      '.cr-format-btn.active{background:var(--brand-color,#1a1a2e);color:#fff;border-color:var(--brand-color,#1a1a2e)}',
      '.cr-input-row{display:flex;gap:8px}',
      '.cr-input-row input{flex:1;padding:10px 12px;border:1px solid #e0e0e0;border-radius:10px;font-size:14px;outline:none}',
      '.cr-input-row input:focus{border-color:var(--brand-color,#1a1a2e)}',
      '.cr-send-btn{width:40px;height:40px;border-radius:50%;background:var(--brand-color,#1a1a2e);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}',
      '.cr-send-btn:hover{opacity:.85}',
      '@media(max-width:480px){.cr-widget-sidebar{bottom:0;right:0;left:0;width:100%;height:100%;max-height:100%;border-radius:0}}',
    ].join(' ');
    shadow.appendChild(style);
  }

  function buildHTML() {
    const dir = config.position === 'left' ? 'left:24px' : 'right:24px';
    const side = config.position === 'left' ? 'left' : 'right';
    const hostStyle = `--brand-color:${config.brandColor};--widget-pos:${dir}`;
    shadow.host.style.cssText = `all:initial;${hostStyle}`;

    const tmpl = document.createElement('div');
    tmpl.innerHTML = `
      <div class="cr-widget-button" id="cr-toggle" style="${dir}">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2C6.48 2 2 6.48 2 12c0 1.88.54 3.63 1.48 5.12L2 22l4.88-1.48A9.96 9.96 0 0012 22c5.52 0 10-4.48 10-10S17.52 2 12 2z"/>
          <path d="M9 9h.01M15 9h.01M9 13c.86.86 2.04 1.5 3 1.5s2.14-.64 3-1.5"/>
        </svg>
      </div>
      <div class="cr-widget-sidebar" id="cr-sidebar" style="${dir};display:none">
        <div class="cr-header">
          <div class="cr-header-logo">
            ${config.logo ? `<img id="cr-logo" src="${config.logo}" alt="logo"/>` : `<div class="cr-default-icon">🏏</div>`}
            <span>CricketGPT</span>
          </div>
          <button id="cr-close" class="cr-btn-icon" aria-label="Close">✕</button>
        </div>
        <div class="cr-messages" id="cr-messages">
          <div class="cr-message cr-bot">
            <div class="cr-avatar">🤖</div>
            <div class="cr-bubble"><p>${config.greeting}</p></div>
          </div>
          <div class="cr-suggestions" id="cr-suggestions"></div>
        </div>
        <div class="cr-input-area">
          <div class="cr-format-bar" id="cr-format-bar">
            <button data-format="test" class="cr-format-btn">Test</button>
            <button data-format="odi" class="cr-format-btn active">ODI</button>
            <button data-format="t20i" class="cr-format-btn">T20I</button>
            <button data-format="auto" class="cr-format-btn">Auto</button>
          </div>
          <div class="cr-input-row">
            <input type="text" id="cr-input" placeholder="${config.placeholder}" autocomplete="off" />
            <button id="cr-send" class="cr-send-btn" aria-label="Send">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
    shadow.appendChild(tmpl);
  }

  function $(id) { return shadow.getElementById(id); }

  function setup() {
    const toggle = $('cr-toggle');
    const sidebar = $('cr-sidebar');
    const close = $('cr-close');
    const input = $('cr-input');
    const send = $('cr-send');
    const messages = $('cr-messages');
    const suggestions = $('cr-suggestions');
    const formatBar = $('cr-format-bar');

    toggle.addEventListener('click', function () {
      sidebar.style.display = 'flex';
      toggle.style.display = 'none';
      input.focus();
      loadSuggestions();
    });

    close.addEventListener('click', function () {
      sidebar.style.display = 'none';
      toggle.style.display = 'flex';
    });

    formatBar.addEventListener('click', function (e) {
      const btn = e.target.closest('.cr-format-btn');
      if (!btn) return;
      formatBar.querySelectorAll('.cr-format-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      selectedFormat = btn.dataset.format;
    });

    function sendMessage() {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      appendMessage(text, 'user');
      removeSuggestions();
      showTyping();
      callAPI(text);
    }

    send.addEventListener('click', sendMessage);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') sendMessage();
    });
  }

  function appendMessage(text, role) {
    const messages = $('cr-messages');
    const div = document.createElement('div');
    div.className = 'cr-message cr-' + role;

    const avatar = document.createElement('div');
    avatar.className = 'cr-avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    div.appendChild(avatar);

    const bubble = document.createElement('div');
    bubble.className = 'cr-bubble';

    const p = document.createElement('p');
    p.textContent = text;
    bubble.appendChild(p);

    div.appendChild(bubble);

    if (role === 'bot') {
      var feedback = document.createElement('div');
      feedback.className = 'cr-feedback';
      feedback.innerHTML =
        '<button class="cr-fb-btn cr-fb-up" data-vote="up" title="Helpful">👍</button>' +
        '<button class="cr-fb-btn cr-fb-down" data-vote="down" title="Not helpful">👎</button>';
      div.appendChild(feedback);
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function showTyping() {
    const messages = $('cr-messages');
    const div = document.createElement('div');
    div.className = 'cr-message cr-bot cr-typing';
    div.id = 'cr-typing-indicator';
    const avatar = document.createElement('div');
    avatar.className = 'cr-avatar';
    avatar.textContent = '🤖';
    div.appendChild(avatar);
    const bubble = document.createElement('div');
    bubble.className = 'cr-bubble';
    bubble.innerHTML = '<span class="cr-dot"></span><span class="cr-dot"></span><span class="cr-dot"></span>';
    div.appendChild(bubble);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    var el = $('cr-typing-indicator');
    if (el) el.remove();
  }

  function removeSuggestions() {
    var el = $('cr-suggestions');
    if (el) el.innerHTML = '';
  }

  function appendStreamToken(text) {
    var indicator = $('cr-typing-indicator');
    if (!indicator) return;
    var bubble = indicator.querySelector('.cr-bubble');
    if (!bubble) return;
    var p = bubble.querySelector('p');
    if (!p) {
      p = document.createElement('p');
      bubble.innerHTML = '';
      bubble.appendChild(p);
    }
    p.textContent += text;
    var msgs = $('cr-messages');
    msgs.scrollTop = msgs.scrollHeight;
  }

  function finalizeStream(_, guardrailStatus) {
    var indicator = $('cr-typing-indicator');
    if (indicator) {
      indicator.classList.remove('cr-typing');
      indicator.id = 'cr-msg-' + Date.now();
      var feedback = document.createElement('div');
      feedback.className = 'cr-feedback';
      feedback.innerHTML =
        '<button class="cr-fb-btn cr-fb-up" data-vote="up" title="Helpful">👍</button>' +
        '<button class="cr-fb-btn cr-fb-down" data-vote="down" title="Not helpful">👎</button>';
      indicator.appendChild(feedback);
    }
  }

  function handleFeedback(e) {
    var btn = e.target.closest('.cr-fb-btn');
    if (!btn) return;
    var vote = btn.dataset.vote;
    var msgDiv = btn.closest('.cr-message');
    var queryEl = msgDiv && msgDiv.previousElementSibling;
    var query = queryEl ? queryEl.querySelector('.cr-bubble p').textContent : '';
    var response = msgDiv ? msgDiv.querySelector('.cr-bubble p').textContent : '';

    var payload = {
      session_id: SESSION_ID,
      query: query,
      response: response,
      vote: vote
    };
    fetch(config.apiBase + '/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': config.partner },
      body: JSON.stringify(payload)
    }).catch(function () {});
    btn.parentElement.querySelectorAll('.cr-fb-btn').forEach(function (b) { b.style.opacity = '0.4'; });
    btn.style.opacity = '1';
  }

  function callAPI(text) {
    if (streamingAbort) {
      streamingAbort.abort();
      streamingAbort = null;
    }

    var formatParam = selectedFormat === 'auto' ? null : selectedFormat;

    if (typeof EventSource !== 'undefined' && !('noSSE' in config)) {
      streamingAbort = new AbortController();
      var url = config.apiBase + '/chat/stream';
      var payload = JSON.stringify({
        query: text,
        format: formatParam,
        context: 'general',
        session_id: SESSION_ID
      });

      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': config.partner },
        body: payload,
        signal: streamingAbort.signal
      }).then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var reader = resp.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';

        function read() {
          reader.read().then(function (result) {
            if (result.done) {
              finalizeStream(null, null);
              streamingAbort = null;
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';
            lines.forEach(function (line) {
              if (line.startsWith('data: ')) {
                try {
                  var data = JSON.parse(line.slice(6));
                  if (data.type === 'token' && data.text) {
                    appendStreamToken(data.text);
                  } else if (data.type === 'done' && data.response) {
                    finalizeStream(null, data.response.guardrail_status);
                    streamingAbort = null;
                  }
                } catch (err) {}
              }
            });
            read();
          }).catch(function (err) {
            if (err.name !== 'AbortError') {
              hideTyping();
              appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
              streamingAbort = null;
            }
          });
        }
        read();
      }).catch(function (err) {
        if (err.name !== 'AbortError') {
          hideTyping();
          appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
      });
    } else {
      fetch(config.apiBase + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': config.partner },
        body: JSON.stringify({
          query: text,
          format: formatParam,
          context: 'general',
          session_id: SESSION_ID
        })
      }).then(function (resp) {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      }).then(function (data) {
        hideTyping();
        appendMessage(data.answer, 'bot');
        loadSuggestions();
      }).catch(function (err) {
        hideTyping();
        appendMessage('Sorry, I encountered an error. Please try again.', 'bot');
      });
    }
  }

  function loadSuggestions() {
    var container = $('cr-suggestions');
    if (!container) return;
    var formatParam = selectedFormat === 'auto' ? null : selectedFormat;
    fetch(config.apiBase + '/suggestions?format=' + (formatParam || '') + '&context=general', {
      headers: { 'X-API-Key': config.partner }
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.suggestions || data.suggestions.length === 0) return;
      container.innerHTML = '<div class="cr-suggestions-label">Try asking:</div>';
      data.suggestions.forEach(function (s) {
        var btn = document.createElement('button');
        btn.className = 'cr-suggestion-btn';
        btn.textContent = s.question;
        btn.addEventListener('click', function () {
          $('cr-input').value = s.question;
          $('cr-send').click();
        });
        container.appendChild(btn);
      });
    }).catch(function () {});
  }

  shadow.addEventListener('click', function (e) { handleFeedback(e); });

  injectStyles();
  buildHTML();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup);
  } else {
    setup();
  }
})();
