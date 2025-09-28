(function(){
  'use strict';
  // Minimal viewer app – ES5 compatible
  var byId = function(id){ return document.getElementById(id); };
  var $stream = byId('streamlog');
  var $events = byId('eventlog');
  var $img = byId('browserimg');
  var $badge = byId('connstatus');
  
  // Notify parent window once when first activity is detected (for auto-switching tabs)
  var _postedPlaywrightActivity = false;
  function _notifyParentActivity(){
    if (_postedPlaywrightActivity) return;
    try {
      if (window && window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'mcp_playwright_activity' }, '*');
        _postedPlaywrightActivity = true;
      }
    } catch(_e){}
  }

  function setBadge(state, text){
    if(!$badge) return;
    $badge.className = 'badge ' + (state==='ok'?'badge-ok':state==='err'?'badge-err':state==='warn'?'badge-warn':'badge-info');
    $badge.textContent = text || (state==='ok'?'Connected':'Connecting…');
  }
  function append(pre, text, cls){
    if(!pre) return;
    var span = document.createElement('span');
    if(cls) span.className = cls;
    try{
      if (text == null) { span.textContent = ''; }
      else if (typeof text === 'string') { span.textContent = text; }
      else if (typeof text === 'number' || typeof text === 'boolean') { span.textContent = String(text); }
      else if (typeof text === 'object') {
        // Prefer text/message/content fields
        if (text.text != null) { span.textContent = String(text.text); }
        else if (text.message != null) { span.textContent = String(text.message); }
        else if (text.content != null) {
          if (typeof text.content === 'string') { span.textContent = text.content; }
          else if (Array.isArray(text.content)) {
            try {
              span.textContent = text.content.map(function(c){
                if (typeof c === 'string') return c;
                if (c && typeof c.text === 'string') return c.text;
                return JSON.stringify(c);
              }).join(' ');
            } catch(_e) { span.textContent = JSON.stringify(text.content); }
          } else { span.textContent = JSON.stringify(text.content); }
        } else {
          // Compact key=value format for small objects; fallback to JSON
          try{
            var keys = Object.keys(text);
            if (keys.length && keys.length <= 4) {
              span.textContent = keys.map(function(k){
                var val = text[k];
                if (val && typeof val === 'object') return k + '=' + JSON.stringify(val);
                return k + '=' + String(val);
              }).join(' ');
            } else {
              span.textContent = JSON.stringify(text);
            }
          }catch(_e){ span.textContent = JSON.stringify(text); }
        }
      } else { span.textContent = String(text); }
    }catch(_e){ span.textContent = String(text||''); }
    pre.appendChild(span);
    pre.appendChild(document.createTextNode('\n'));
    pre.scrollTop = pre.scrollHeight;
  }
  function render(kind, payload){
    try{
      if(kind === 'chunk') return append($stream, payload, '');
      if(kind === 'status') return append($events, payload, 'ok');
      if(kind === 'error') return append($events, payload, 'err');
      if(kind === 'tool') { var r = append($events, payload, 'tool'); _notifyParentActivity(); return r; }
      if(kind === 'browser' && payload){
        // Support data_uri, url, or raw base64 data
        if(payload.data_uri){ if($img) $img.src = payload.data_uri; }
        else if(payload.url){ if($img) $img.src = payload.url; }
        else if(payload.data){ if($img) $img.src = 'data:image/png;base64,' + String(payload.data); }
        if(payload.text) append($events, payload.text, 'tool');
        _notifyParentActivity();
        return;
      }
      if(kind === 'content') return append($stream, payload, '');
      if(kind === 'source') return append($events, 'Source: ' + payload, '');
    }catch(_e){}
  }

  function coerceAndRender(item){
    try{
      var msg = item;
      if(typeof msg === 'string'){
        try { msg = JSON.parse(msg); } catch(_e) {}
      }
      if(!msg || typeof msg !== 'object') return;
      var kind = msg.kind || msg.type || '';
      var payload = msg.text != null ? msg.text : (msg.payload != null ? msg.payload : msg);
      // Track sequence/id for polling
      try{
        if(typeof msg.seq === 'number'){ lastId = msg.seq; }
        else if(typeof msg.id === 'number'){ lastId = msg.id; }
        else if(typeof msg.since === 'number'){ lastId = msg.since; }
      }catch(_e){}
      render(kind, payload);
    }catch(_e){}
  }

  var useSSE = !!(window.EventSource);
  var lastId = 0;
  function connectSSE(){
    try{
      var es = new EventSource('/events');
      es.onopen = function(){ setBadge('ok', 'Connected (SSE)'); };
      es.onmessage = function(ev){
        try{
          var msg = JSON.parse(ev.data);
          coerceAndRender(msg);
        }catch(_e){ /* ignore parse error */ }
      };
      es.onerror = function(){
        try{ es.close(); }catch(_e){}
        setBadge('warn', 'SSE failed. Switching to poll…');
        connectPoll();
      };
    }catch(_e){ setBadge('err', 'SSE init failed'); connectPoll(); }
  }
  function connectPoll(){
    function loop(){
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/events.json?since=' + String(lastId), true);
      xhr.onreadystatechange = function(){
        if(xhr.readyState === 4){
          try{
            if(xhr.status === 200){
              var body = xhr.responseText || '';
              var data = {};
              try { data = JSON.parse(body); } catch(_e) { data = {}; }
              // Server returns object: { since, items }
              if(data && typeof data === 'object'){
                if(typeof data.since === 'number') lastId = data.since;
                var items = data.items || [];
                for(var i=0;i<items.length;i++){
                  coerceAndRender(items[i]);
                }
              }
              setTimeout(loop, 800);
            }else{
              setTimeout(loop, 1500);
            }
          }catch(_e){ setTimeout(loop, 1500); }
        }
      };
      xhr.onerror = function(){ setBadge('err', 'Poll error. Retrying…'); };
      xhr.send();
    }
    setBadge('ok', 'Connected (poll)');
    loop();
  }

  if(useSSE) connectSSE(); else connectPoll();
})();