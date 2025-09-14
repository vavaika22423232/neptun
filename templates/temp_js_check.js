    // --- Comments UI styles inject ---
    (function(){
      if(document.getElementById('commentsStyles')) return;
      const css = `
  /* Modern Chat UI Redesign */
  .comments-card{
    position:fixed;
    bottom:6.2rem;
    right:14px;
    width:340px;
    max-height:65vh;
    display:flex;
    flex-direction:column;
    background:linear-gradient(145deg, rgba(15,23,42,.92) 0%, rgba(30,41,59,.95) 100%);
    backdrop-filter:blur(16px) saturate(180%);
    border:1px solid rgba(148,163,184,.15);
    border-radius:20px;
    box-shadow:0 20px 50px -12px rgba(0,0,0,.65), 0 0 0 1px rgba(148,163,184,.08);
    font-family:'Inter',system-ui,sans-serif;
    color:#f8fafc;
    z-index:520;
    overflow:hidden;
    transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .comments-card::before{
    content:'';
    position:absolute;
    top:0;
    left:0;
    right:0;
    height:1px;
    background:linear-gradient(90deg, transparent, rgba(59,130,246,.6), transparent);
  }
  .comments-card.collapsed{display:none;}
  
  .comments-header{
    padding:16px 18px 12px;
    font-weight:700;
    font-size:.95rem;
    letter-spacing:.3px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    background:linear-gradient(135deg, rgba(59,130,246,.1), rgba(16,185,129,.08));
    border-bottom:1px solid rgba(148,163,184,.1);
  }
  .ch-left{
    display:flex;
    align-items:center;
    gap:8px;
    color:#e2e8f0;
  }
  .sound-toggle-btn{
    background:rgba(148,163,184,.1);
    border:1px solid rgba(148,163,184,.15);
    color:#94a3b8;
    font-size:14px;
    width:28px;
    height:28px;
    border-radius:50%;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    transition:all .2s ease;
    margin-left:auto;
  }
  .sound-toggle-btn:hover{
    background:rgba(59,130,246,.15);
    border-color:rgba(59,130,246,.3);
    color:#93c5fd;
  }
  .comments-count{
    font-weight:600;
    font-size:.7rem;
    background:linear-gradient(135deg, #3b82f6, #1d4ed8);
    color:#fff;
    padding:3px 8px 4px;
    border-radius:16px;
    box-shadow:0 2px 8px rgba(59,130,246,.3);
    min-width:20px;
    text-align:center;
  }
  .comments-close{
    background:rgba(148,163,184,.1);
    border:none;
    color:#cbd5e1;
    font-size:18px;
    line-height:1;
    cursor:pointer;
    padding:8px;
    border-radius:12px;
    transition:all .25s ease;
    backdrop-filter:blur(8px);
  }
  .comments-close:hover{
    background:rgba(239,68,68,.15);
    color:#f87171;
    transform:scale(1.1);
  }
  
  /* Chat filters */
  .chat-filters {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(148,163,184,.1);
    background: rgba(15,23,42,.4);
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }
  
  .filter-group {
    display: flex;
    gap: 4px;
  }
  
  .filter-btn {
    background: rgba(148,163,184,.08);
    border: 1px solid rgba(148,163,184,.15);
    color: #94a3b8;
    font-size: .65rem;
    padding: 4px 10px;
    border-radius: 12px;
    cursor: pointer;
    transition: all .2s ease;
    font-weight: 500;
  }
  .filter-btn:hover {
    background: rgba(59,130,246,.15);
    border-color: rgba(59,130,246,.3);
    color: #93c5fd;
  }
  .filter-btn.active {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    border-color: transparent;
    color: white;
    box-shadow: 0 2px 8px rgba(59,130,246,.3);
  }
  
  .search-group {
    position: relative;
    margin-left: auto;
  }
  
  #chatSearch {
    background: rgba(15,23,42,.8);
    border: 1px solid rgba(148,163,184,.15);
    color: #f1f5f9;
    font-size: .65rem;
    padding: 4px 24px 4px 8px;
    border-radius: 10px;
    width: 120px;
    outline: none;
    transition: all .2s ease;
  }
  #chatSearch:focus {
    border-color: #3b82f6;
    background: rgba(15,23,42,.95);
    width: 160px;
  }
  #chatSearch::placeholder { color: #64748b; }
  
  .clear-btn {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #64748b;
    font-size: .7rem;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    line-height: 1;
    opacity: 0;
    transition: all .2s ease;
  }
  #chatSearch:not(:placeholder-shown) + .clear-btn {
    opacity: 1;
  }
  .clear-btn:hover {
    background: rgba(239,68,68,.15);
    color: #f87171;
  }
  
  .comments-list{
    overflow-y:auto;
    padding:8px 12px 12px;
    scrollbar-width:thin;
    display:flex;
    flex-direction:column;
    gap:12px;
    scrollbar-color:rgba(148,163,184,.3) transparent;
  }
  .comments-list::-webkit-scrollbar{width:6px;}
  .comments-list::-webkit-scrollbar-track{background:transparent;}
  .comments-list::-webkit-scrollbar-thumb{
    background:linear-gradient(180deg, rgba(148,163,184,.3), rgba(148,163,184,.5));
    border-radius:3px;
  }
  .comments-list::-webkit-scrollbar-thumb:hover{background:rgba(148,163,184,.6);}
  
  .comment-item{
    background:linear-gradient(135deg, rgba(30,41,59,.8), rgba(15,23,42,.9));
    border:1px solid rgba(148,163,184,.12);
    border-radius:16px;
    padding:12px 14px;
    font-size:.78rem;
    line-height:1.4;
    position:relative;
    animation:slideInMessage .5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    white-space:pre-wrap;
    word-wrap:break-word;
    backdrop-filter:blur(8px);
    transition:all .3s ease;
  }
  .comment-item::before{
    content:'';
    position:absolute;
    top:0;
    left:0;
    right:0;
    height:1px;
    background:linear-gradient(90deg, transparent, rgba(148,163,184,.2), transparent);
    border-radius:16px 16px 0 0;
  }
  .comment-item:hover{
    border-color:rgba(59,130,246,.4);
    background:linear-gradient(135deg, rgba(59,130,246,.08), rgba(30,41,59,.9));
    transform:translateY(-1px);
    box-shadow:0 8px 25px -8px rgba(0,0,0,.4);
  }
  .comment-time{
    opacity:.65;
    font-size:.65rem;
    margin-top:6px;
    letter-spacing:.2px;
    color:#94a3b8;
  }
  
  .comment-foot{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-top:8px;
    gap:8px;
  }
  .comment-reply-btn{
    background:rgba(59,130,246,.1);
    border:1px solid rgba(59,130,246,.2);
    color:#93c5fd;
    font-size:.65rem;
    cursor:pointer;
    padding:4px 8px;
    border-radius:8px;
    line-height:1;
    transition:all .2s ease;
    font-weight:500;
  }
  .comment-reply-btn:hover{
    background:rgba(59,130,246,.2);
    color:#dbeafe;
    border-color:rgba(59,130,246,.4);
    transform:scale(1.05);
  }
  
  .comment-reply-ref{
    font-size:.65rem;
    opacity:.8;
    margin:-2px 0 6px;
    padding:4px 8px 5px;
    background:rgba(15,23,42,.7);
    border:1px solid rgba(148,163,184,.15);
    border-radius:12px;
    display:inline-block;
    max-width:100%;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
    color:#cbd5e1;
  }
  .comment-reply-ref.missing{opacity:.45;color:#64748b;}
  .cancel-reply-btn{
    background:transparent;
    border:none;
    color:#f87171;
    font-size:14px;
    line-height:1;
    cursor:pointer;
    padding:0 4px;
    margin-left:6px;
    transition:all .2s ease;
  }
  .cancel-reply-btn:hover{color:#ef4444;transform:scale(1.1);}
  .reply-target{color:#93c5fd;font-weight:500;}
  
  @keyframes slideInMessage{
    from{
      opacity:0;
      transform:translateY(10px) scale(0.95);
    }
    to{
      opacity:1;
      transform:translateY(0) scale(1);
    }
  }
  
  .comment-form{
    border-top:1px solid rgba(148,163,184,.12);
    padding:12px 14px 14px;
    display:flex;
    flex-direction:column;
    gap:10px;
    background:linear-gradient(135deg, rgba(15,23,42,.6), rgba(30,41,59,.4));
  }
  .comment-form textarea{
    resize:vertical;
    min-height:70px;
    max-height:200px;
    background:rgba(15,23,42,.8);
    border:2px solid rgba(148,163,184,.15);
    border-radius:14px;
    padding:12px 14px;
    font-size:.75rem;
    line-height:1.4;
    color:#f1f5f9;
    font-family:inherit;
    outline:none;
    box-shadow:inset 0 1px 3px rgba(0,0,0,.1);
    transition:all .25s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .comment-form textarea::placeholder{color:#64748b;}
  .comment-form textarea:focus{
    border-color:#3b82f6;
    box-shadow:0 0 0 3px rgba(59,130,246,.2), inset 0 1px 3px rgba(0,0,0,.1);
    background:rgba(15,23,42,.95);
  }
  
  .comment-actions{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
  }
  #commentSubmit{
    background:linear-gradient(135deg, #3b82f6, #1d4ed8);
    border:none;
    color:#fff;
    font-weight:600;
    font-size:.72rem;
    padding:10px 20px;
    border-radius:14px;
    cursor:pointer;
    display:inline-flex;
    align-items:center;
    gap:6px;
    letter-spacing:.3px;
    box-shadow:0 8px 25px -8px rgba(59,130,246,.6);
    transition:all .25s cubic-bezier(0.4, 0, 0.2, 1);
    position:relative;
    overflow:hidden;
  }
  #commentSubmit::before{
    content:'';
    position:absolute;
    top:0;
    left:-100%;
    width:100%;
    height:100%;
    background:linear-gradient(90deg, transparent, rgba(255,255,255,.2), transparent);
    transition:left .5s ease;
  }
  #commentSubmit:hover::before{left:100%;}
  #commentSubmit:hover{
    background:linear-gradient(135deg, #1d4ed8, #1e40af);
    transform:translateY(-1px);
    box-shadow:0 12px 35px -10px rgba(59,130,246,.7);
  }
  #commentSubmit:active{transform:translateY(0);}
  #commentSubmit:disabled{
    background:linear-gradient(135deg, #374151, #4b5563);
    cursor:default;
    box-shadow:none;
    transform:none;
  }
  
  .comment-hint{
    font-size:.6rem;
    opacity:.7;
    color:#94a3b8;
    white-space:nowrap;
  }
  .comment-empty{
    padding:20px 8px;
    font-size:.7rem;
    opacity:.6;
    text-align:center;
    color:#64748b;
  }
  
  /* Enhanced FAB */
  .comments-fab{
    position:fixed;
    bottom:90px;
    right:18px;
    width:60px;
    height:60px;
    border:none;
    border-radius:50%;
    background:linear-gradient(135deg, #3b82f6, #1d4ed8);
    color:#fff;
    font-size:24px;
    font-weight:600;
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    box-shadow:0 12px 30px -8px rgba(59,130,246,.7);
    z-index:1299;
    transition:all .3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter:blur(8px);
  }
  .comments-fab::before{
    content:'';
    position:absolute;
    inset:-2px;
    border-radius:50%;
    background:linear-gradient(135deg, #3b82f6, #1d4ed8);
    z-index:-1;
    opacity:0;
    transition:opacity .3s ease;
  }
  .comments-fab:hover::before{opacity:1;}
  .comments-fab:hover{
    background:linear-gradient(135deg, #1d4ed8, #1e40af);
    transform:translateY(-2px) scale(1.05);
    box-shadow:0 16px 40px -10px rgba(59,130,246,.8);
  }
  .comments-fab:active{transform:translateY(0) scale(0.95);}
  .comments-fab.hidden{display:none !important;}
  
  
  /* Enhanced reaction system styles */
  .comment-reactions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 4px;
  }
  
  .reaction-btn {
    background: rgba(59,130,246,.12);
    border: 1px solid rgba(59,130,246,.25);
    color: #93c5fd;
    font-size: .65rem;
    padding: 3px 8px 4px;
    border-radius: 12px;
    cursor: pointer;
    transition: all .2s ease;
    font-family: inherit;
  }
  .reaction-btn:hover {
    background: rgba(59,130,246,.2);
    border-color: rgba(59,130,246,.4);
    transform: scale(1.05);
  }
  
  .quick-reactions {
    display: flex;
    gap: 4px;
    margin-top: 6px;
    opacity: 0;
    transition: opacity .2s ease;
  }
  .comment-item:hover .quick-reactions {
    opacity: 1;
  }
  
  .quick-react-btn {
    background: rgba(148,163,184,.08);
    border: 1px solid rgba(148,163,184,.15);
    color: #94a3b8;
    font-size: .7rem;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all .2s ease;
    line-height: 1;
  }
  .quick-react-btn:hover {
    background: rgba(59,130,246,.15);
    border-color: rgba(59,130,246,.3);
    transform: scale(1.1);
  }
  .quick-react-btn.active {
    background: rgba(59,130,246,.2);
    border-color: rgba(59,130,246,.4);
    color: #dbeafe;
  }
  .quick-react-btn.reaction-clicked {
    animation: reactionPop .3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }
  
  @keyframes reactionPop {
    0% { transform: scale(1); }
    50% { transform: scale(1.3); }
    100% { transform: scale(1); }
  }
  
  /* Responsive adjustments */
  @media (max-width:900px){
    .comments-fab{bottom:4.6rem;right:1rem;}
    .comments-card{right:8px;left:auto;width:88%;max-width:440px;bottom:82px;max-height:58vh;}
    .comments-card.collapsed{display:none;}
  }
  @media (max-width:520px){
    .comments-fab{bottom:4.9rem;}
    .comments-card{width:92%;}
    .quick-reactions { opacity: 1; } /* Always show on mobile */
  }
      `;
      `;
      const st=document.createElement('style'); st.id='commentsStyles'; st.textContent=css; document.head.appendChild(st);
    })();
    // --- Comments logic ---
    let commentsPolling=null; let commentsBusy=false;
    async function fetchComments(){
      try { const r= await fetch('/comments'); const j= await r.json(); if(!j.ok) return; renderComments(j.items||[]);} catch(e){}
    }
    function renderComments(arr){
      const list = document.getElementById('commentsList'); const cnt=document.getElementById('commentsCount'); if(!list) return;
      if(!arr.length){ list.innerHTML='<div class="comment-empty">Немає коментарів</div>'; if(cnt) cnt.textContent='0'; return; }
      
      // Check for new comments and play sound
      if(lastCommentCount > 0 && arr.length > lastCommentCount) {
        playNotificationSound('message');
      }
      lastCommentCount = arr.length;
      
      if(cnt) cnt.textContent=arr.length;
      // Build a lookup for parent texts to show context on replies
      const byId = {}; arr.forEach(c=>{ byId[c.id]=c; });
      list.innerHTML = arr.map(c=>{
        let ctx='';
        if(c.reply_to && byId[c.reply_to]){
          const p = byId[c.reply_to];
            ctx = '<div class="comment-reply-ref" data-ref="' + c.reply_to + '">&crarr; <span class="cr-text">' + escapeHtml(p.text.substring(0,85)) + (p.text.length>85?'&hellip;':'') + '</span></div>';
        } else if(c.reply_to){
            ctx = '<div class="comment-reply-ref missing">&crarr; <span class="cr-text">(\u043d\u0435\u043c\u0430\u0454 \u043e\u0440\u0438\u0433\u0456\u043d\u0430\u043b\u0443)</span></div>';
        }
        
        // Render reactions
        let reactionsHtml = '';
        if(c.reactions && Object.keys(c.reactions).length > 0) {
          reactionsHtml = '<div class="comment-reactions">';
          for(const [emoji, count] of Object.entries(c.reactions)) {
            reactionsHtml += '<button class="reaction-btn" data-comment="' + c.id + '" data-emoji="' + emoji + '">' + emoji + ' ' + count + '</button>';
          }
          reactionsHtml += '</div>';
        }
        
        // Quick react buttons
        const quickReacts = ['👍', '❤️', '🔥', '😢', '😡', '😂', '👎'];
        let quickReactHtml = '<div class="quick-reactions">';
        quickReacts.forEach(emoji => {
          const isActive = c.reactions && c.reactions[emoji] ? 'active' : '';
          quickReactHtml += '<button class="quick-react-btn ' + isActive + '" data-comment="' + c.id + '" data-emoji="' + emoji + '" title="React ' + emoji + '">' + emoji + '</button>';
        });
        quickReactHtml += '</div>';
        
        return '<div class="comment-item" data-id="' + c.id + '" role="listitem">' + ctx + '<div class="comment-body">' + escapeHtml(c.text) + '</div>' + reactionsHtml + '<div class="comment-foot"><div class="comment-time">' + c.ts + '</div><button class="comment-reply-btn" data-reply="' + c.id + '" title="Reply">&crarr;</button></div>' + quickReactHtml + '</div>';
      }).join('');
      list.scrollTop = list.scrollHeight;
      
      // Attach reply handlers
      list.querySelectorAll('.comment-reply-btn').forEach(btn=>{
         btn.addEventListener('click', e=>{
            const id = btn.getAttribute('data-reply');
            beginReply(id, byId[id]);
         });
      });
      
      // Attach reaction handlers
      list.querySelectorAll('.quick-react-btn, .reaction-btn').forEach(btn=>{
         btn.addEventListener('click', e=>{
            e.preventDefault();
            const commentId = btn.getAttribute('data-comment');
            const emoji = btn.getAttribute('data-emoji');
            toggleReaction(commentId, emoji, btn);
         });
      });
    }
         btn.addEventListener('click', e=>{
            const id = btn.getAttribute('data-reply');
            beginReply(id, byId[id]);
         });
      });
    }
    function escapeHtml(s){ return s? s.replace(/[&<>"']/g, ch=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch])):''; }
    
    // Reaction system
    async function toggleReaction(commentId, emoji, btnElement) {
      if(!commentId || !emoji) return;
      
      try {
        const response = await fetch('/comments/react', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment_id: commentId, emoji: emoji })
        });
        
        const result = await response.json();
        
        if(result.ok) {
          // Update button visual feedback
          if(btnElement) {
            btnElement.classList.add('reaction-clicked');
            setTimeout(() => {
              btnElement.classList.remove('reaction-clicked');
            }, 200);
          }
          
          // Refresh comments to show updated reactions
          fetchComments();
        } else {
          console.warn('Reaction failed:', result.error);
          if(result.error === 'rate_limited') {
            showToast('\u0417\u0430\u0431\u0430\u0433\u0430\u0442\u043e \u0440\u0435\u0430\u043a\u0446\u0456\u0439! \u0421\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u0456\u0437\u043d\u0456\u0448\u0435', 'warning');
          }
        }
      } catch(error) {
        console.error('Reaction error:', error);
      }
    }
    
    function showToast(message, type = 'info') {
      const toast = document.createElement('div');
      toast.className = 'toast toast-' + type;
      toast.textContent = message;
      
      // Set styles individually
      toast.style.position = 'fixed';
      toast.style.top = '20px';
      toast.style.right = '20px';
      toast.style.padding = '12px 16px';
      toast.style.borderRadius = '8px';
      toast.style.color = 'white';
      toast.style.fontWeight = '500';
      toast.style.zIndex = '9999';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-20px)';
      toast.style.transition = 'all 0.3s ease';
      toast.style.background = (type === 'warning' ? '#f59e0b' : type === 'error' ? '#ef4444' : '#3b82f6');
      
      document.body.appendChild(toast);
      
      // Animate in
      setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
      }, 10);
      
      // Remove after 3 seconds
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => document.body.removeChild(toast), 300);
      }, 3000);
    }
    
    // Sound notification system
    let audioEnabled = localStorage.getItem('chatSounds') !== 'false';
    let lastCommentCount = 0;
    
    function playNotificationSound(type = 'message') {
      if (!audioEnabled) return;
      
      try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Different sounds for different events
        if (type === 'message') {
          // Pleasant notification sound
          oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
          oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
          gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
          oscillator.start();
          oscillator.stop(audioContext.currentTime + 0.3);
        } else if (type === 'reaction') {
          // Quick pop sound for reactions
          oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
          gainNode.gain.setValueAtTime(0.05, audioContext.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
          oscillator.start();
          oscillator.stop(audioContext.currentTime + 0.1);
        }
      } catch (e) {
        console.debug('Audio notification failed:', e);
      }
    }
    
    function toggleSounds() {
      audioEnabled = !audioEnabled;
      localStorage.setItem('chatSounds', audioEnabled);
      showToast(audioEnabled ? '\u0417\u0432\u0443\u043a\u0438 \u0443\u0432\u0456\u043c\u043a\u043d\u0435\u043d\u043e 🔊' : '\u0417\u0432\u0443\u043a\u0438 \u0432\u0438\u043c\u043a\u043d\u0435\u043d\u043e 🔇', 'info');
      updateSoundButton();
    }
    
    function updateSoundButton() {
      const btn = document.getElementById('soundToggle');
      if (btn) {
        btn.innerHTML = audioEnabled ? '🔊' : '🔇';
        btn.title = audioEnabled ? 'Вимкнути звуки' : 'Увімкнути звуки';
      }
    }
    let currentReplyTo = null;
    function beginReply(id, parent){
       currentReplyTo = id;
       const hint = document.getElementById('commentHint');
       if(hint){
         const prevTxt = parent && parent.text ? parent.text : '';
         hint.innerHTML = '\u0412\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u044c &crarr; <span class="reply-target">' + escapeHtml(prevTxt.substring(0,60)) + (prevTxt.length>60?'&hellip;':'') + '</span> <button type="button" id="cancelReply" class="cancel-reply-btn" title="\u0421\u043a\u0430\u0441\u0443\u0432\u0430\u0442\u0438">&times;</button>';
       }
       const ta=document.getElementById('commentText'); if(ta){ ta.focus(); }
       setTimeout(()=>{ const c=document.getElementById('cancelReply'); if(c){ c.addEventListener('click', cancelReply); }},0);
    }
    function cancelReply(){
       currentReplyTo = null;
       const hint = document.getElementById('commentHint'); if(hint){ hint.textContent='\u0410\u043d\u043e\u043d\u0456\u043c\u043d\u043e • \u0431\u0435\u0437 \u0440\u0435\u0454\u0441\u0442\u0440\u0430\u0446\u0456\u0457'; }
    }
    function setupCommentForm(){
      const form=document.getElementById('commentForm'); const ta=document.getElementById('commentText'); const btn=document.getElementById('commentSubmit'); if(!form) return;
      form.addEventListener('submit', async e=>{
        e.preventDefault(); if(commentsBusy) return; const text=(ta.value||'').trim(); if(!text) return; commentsBusy=true; btn.disabled=true; const orig=btn.textContent; btn.textContent='Надсилання…';
        const payload = { text };
        if(currentReplyTo) payload.reply_to = currentReplyTo;
        try { const r= await fetch('/comments',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}); const j= await r.json(); if(j.ok){ ta.value=''; cancelReply(); fetchComments(); btn.textContent='Готово'; setTimeout(()=>{btn.textContent=orig;},1200);} else { btn.textContent='Помилка'; setTimeout(()=>{btn.textContent=orig;},1400);} }
        catch(err){ btn.textContent='Збій'; setTimeout(()=>{btn.textContent=orig;},1400);} finally { commentsBusy=false; btn.disabled=false; }
      });
    }
    function startComments(){ if(commentsPolling) return; fetchComments(); commentsPolling=setInterval(fetchComments, 10000); }
   function toggleComments(force){
    const card=document.getElementById('commentsCard'); const fab=document.getElementById('commentsFab'); if(!card||!fab) return;
    const isCollapsed = card.classList.contains('collapsed');
    const expand = force!==undefined ? force : isCollapsed;
    if(expand){
      card.classList.remove('collapsed');
      fab.setAttribute('aria-label','Згорнути коментарі'); fab.textContent='×';
      // On large screens hide fab (we have close button); on small keep for consistency
      if(window.innerWidth >= 900){ fab.classList.add('hidden'); } else { fab.classList.remove('hidden'); }
    } else {
      card.classList.add('collapsed');
      fab.setAttribute('aria-label','Відкрити коментарі'); fab.textContent='💬';
      fab.classList.remove('hidden');
    }
   }
    document.addEventListener('DOMContentLoaded', ()=>{
      setupCommentForm(); startComments();
  try { hookZoomRedraw(); } catch(e){}
      const fab=document.getElementById('commentsFab'); const closeBtn=document.getElementById('commentsCloseBtn'); const card=document.getElementById('commentsCard');
      // Initial state: show card on desktop, show fab only when collapsed
      if(window.innerWidth < 900 && card){ card.classList.add('collapsed'); } else {
        // Ensure fab hidden while open on desktop
        const fabEl=document.getElementById('commentsFab'); if(card && !card.classList.contains('collapsed') && fabEl){ fabEl.classList.add('hidden'); }
      }
      if(fab){ fab.addEventListener('click', ()=>toggleComments()); }
      if(closeBtn){ closeBtn.addEventListener('click', ()=>toggleComments(false)); }
      window.addEventListener('resize', ()=>{
        const c=document.getElementById('commentsCard'); const f=document.getElementById('commentsFab');
        if(window.innerWidth >= 900){
          if(c && !c.classList.contains('collapsed')){ if(f) f.classList.add('hidden'); }
          else { if(f) f.classList.remove('hidden'); }
        } else {
          // mobile - fab always visible; if panel open show ×, else 💬 handled by toggle
          if(f) f.classList.remove('hidden');
        }
      });
    });
    // Disclaimer persistence
    function hideDisclaimer(){
      const el = document.getElementById('disclaimerBar');
      if(el){ el.classList.add('hidden'); }
      try { localStorage.setItem('disclaimer_ack','1'); } catch(e){}
    }
    function showDisclaimer(){
      const el = document.getElementById('disclaimerBar');
      if(!el) return;
      if(localStorage.getItem('disclaimer_ack')==='1') return; // already acknowledged
      el.style.display='flex';
    }
    document.addEventListener('DOMContentLoaded', showDisclaimer);
    // Donation modal logic
    function toggleDonate(force){
      const ov = document.getElementById('donateModal');
      if(!ov) return;
      let show;
      if(typeof force === 'boolean') show = force; else show = !ov.classList.contains('active');
      ov.classList.toggle('active', show);
      if(show){
        try { document.body.style.overflow='hidden'; } catch(e){}
      } else {
        try { document.body.style.overflow=''; } catch(e){}
      }
    }
    
    // Server Support Functions (updated for card layout)
    function loadDonationAmount() {
      try {
        const amountElement = document.getElementById('donationAmount')?.querySelector('.amount');
        const supportAmountElement = document.getElementById('supportAmount');
        const progressAmountElement = document.getElementById('progressAmount');
        const progressFillElement = document.getElementById('progressFill');
        
        if (!amountElement && !supportAmountElement) return;
        
        const targetAmount = 13200; // Target amount in UAH
        
        // Check for cached amount
        const cachedAmount = localStorage.getItem('donationAmount');
        const cacheTime = localStorage.getItem('donationAmountTime');
        const now = Date.now();
        
        // Default fallback amount (known current amount)
        const fallbackAmount = 462;
        
        // Use cache if it's less than 15 minutes old (reduced from 30)
        if (cachedAmount && cacheTime && (now - parseInt(cacheTime)) < 900000) {
          const amount = parseFloat(cachedAmount) || fallbackAmount;
          updateAmountDisplay(amount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
          console.log('Using cached donation amount:', amount, 'грн');
          return;
        }
        
        // IMMEDIATELY show fallback amount to avoid showing 0
        updateAmountDisplay(fallbackAmount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
        console.log('Showing fallback amount immediately:', fallbackAmount, 'грн');
        
        // Then try to fetch real data in background with retry
        fetchMonobankAmountWithRetry(targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement, now);
        
      } catch(e) {
        console.error('Failed to load donation amount:', e);
        // Show fallback amount on any error
        const fallbackAmount = 462;
        updateAmountDisplay(fallbackAmount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
      }
    }
    
    // Enhanced function with retry mechanism
    async function fetchMonobankAmountWithRetry(targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement, cacheTime, retryCount = 0) {
      const maxRetries = 3;
      const retryDelay = [1000, 3000, 5000]; // Delays for each retry
      
      try {
        await fetchMonobankAmount(targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement, cacheTime);
      } catch (error) {
        console.warn('Attempt ' + (retryCount + 1) + ' failed:', error);
        
        if (retryCount < maxRetries) {
          console.log('Retrying in ' + retryDelay[retryCount] + 'ms...');
          setTimeout(() => {
            fetchMonobankAmountWithRetry(targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement, cacheTime, retryCount + 1);
          }, retryDelay[retryCount]);
        } else {
          console.warn('All retry attempts failed, keeping fallback amount');
        }
      }
    }

    async function fetchMonobankAmount(targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement, cacheTime) {
      try {
        // Use a CORS proxy to fetch Monobank jar data
        const jarId = '6Vi9TVzJZQ';
        
        // Try multiple proxy services for better reliability
        const proxyUrls = [
          'https://api.allorigins.win/get?url=' + encodeURIComponent('https://send.monobank.ua/jar/' + jarId),
          'https://cors-anywhere.herokuapp.com/https://send.monobank.ua/jar/' + jarId,
          'https://thingproxy.freeboard.io/fetch/https://send.monobank.ua/jar/' + jarId
        ];
        
        let htmlContent = null;
        let lastError = null;
        
        // Try each proxy until one works
        for (let i = 0; i < proxyUrls.length; i++) {
          const proxyUrl = proxyUrls[i];
          try {
            console.log('Trying proxy ' + (i + 1) + '/' + proxyUrls.length + ': ' + proxyUrl.split('?')[0] + '...');
            
            // Add timeout to fetch
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
            
            const response = await fetch(proxyUrl, {
              method: 'GET',
              headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
              },
              signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
              throw new Error('HTTP ' + response.status + ': ' + response.statusText);
            }
            
            const data = await response.json();
            htmlContent = data.contents || data;
            if (htmlContent && htmlContent.length > 100) { // Make sure we got actual content
              console.log('Proxy ' + (i + 1) + ' successful, content length: ' + htmlContent.length);
              break;
            } else {
              throw new Error('Empty or invalid content received');
            }
            
          } catch (err) {
            lastError = err;
            console.warn('Proxy ' + (i + 1) + ' failed: ' + err.message);
            
            // Add small delay between proxy attempts
            if (i < proxyUrls.length - 1) {
              await new Promise(resolve => setTimeout(resolve, 500));
            }
            continue;
          }
        }
        
        if (!htmlContent) {
          throw new Error('All proxies failed. Last error: ' + lastError);
        }
        
        // Parse the HTML to extract the current amount
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlContent, 'text/html');
        
        // Look for amount in the page content with multiple patterns
        let amount = 0;
        
        // Try different patterns to find the amount
        const patterns = [
          // Pattern 1: Look for "Зібрано: 462 грн" or similar (most specific)
          /зібрано[:\s]*(\d+(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*грн/i,
          // Pattern 2: Look for "сума: 462 грн" or similar
          /сума[:\s]*(\d+(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*грн/i,
          // Pattern 3: JSON-like structure with amount
          /"amount"[:\s]*(\d+(?:[.,]\d+)?)/i,
          // Pattern 4: Look for large numbers in quotes (JSON-like)
          /"(\d{3,}(?:[.,]\d+)?)"/,
          // Pattern 5: Look for amount in span or div with class containing "amount"
          /<[^>]*class="[^"]*amount[^"]*"[^>]*>[\s\S]*?(\d+(?:[,\s]\d{3})*(?:[.,]\d+)?)/i,
          // Pattern 6: Look for large numbers followed by грн (broader)
          /(\d{2,}(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*грн/i,
          // Pattern 7: Look for amount in data attributes
          /data-amount="(\d+(?:[.,]\d+)?)"/i,
          // Pattern 8: Find numbers that look like currency amounts (3+ digits)
          /\b(\d{3,}(?:[.,]\d{2})?)\b/g
        ];
        
        for (let i = 0; i < patterns.length; i++) {
          const pattern = patterns[i];
          const isGlobal = pattern.global;
          
          if (isGlobal) {
            // For global patterns, find all matches
            let match;
            while ((match = pattern.exec(htmlContent)) !== null) {
              const rawAmount = match[1].replace(/[,\s]/g, '').replace(',', '.');
              const parsedAmount = parseFloat(rawAmount);
              if (parsedAmount && parsedAmount >= 400 && parsedAmount <= 15000) { // Reasonable range
                if (parsedAmount > amount) {
                  amount = parsedAmount;
                  console.log('Found amount using pattern ' + (i + 1) + ': ' + parsedAmount);
                }
              }
            }
          } else {
            // For non-global patterns
            const match = htmlContent.match(pattern);
            if (match) {
              const rawAmount = match[1].replace(/[,\s]/g, '').replace(',', '.');
              const parsedAmount = parseFloat(rawAmount);
              if (parsedAmount && parsedAmount >= 400 && parsedAmount <= 15000) { // Reasonable range
                if (parsedAmount > amount) {
                  amount = parsedAmount;
                  console.log('Found amount using pattern ' + (i + 1) + ': ' + parsedAmount);
                }
              }
            }
          }
        }
        
        // If still no amount found, try parsing the DOM structure
        if (amount === 0 || amount < 400) {
          console.log('Trying DOM parsing for amount...');
          const amountElements = doc.querySelectorAll('[class*="amount"], [class*="sum"], [class*="total"], [class*="collected"], [class*="raised"]');
          for (const element of amountElements) {
            const text = element.textContent || element.innerText || '';
            const numberMatch = text.match(/(\d+(?:[,\s]\d{3})*(?:[.,]\d+)?)/);
            if (numberMatch) {
              const parsedAmount = parseFloat(numberMatch[1].replace(/[,\s]/g, '').replace(',', '.'));
              if (parsedAmount && parsedAmount >= 400 && parsedAmount <= 15000) {
                if (parsedAmount > amount) {
                  amount = parsedAmount;
                  console.log('Found amount in DOM element: ' + parsedAmount);
                }
              }
            }
          }
        }
        
        // If amount is reasonable, cache and use it
        if (amount >= 400) {
          localStorage.setItem('donationAmount', amount.toString());
          localStorage.setItem('donationAmountTime', cacheTime.toString());
          
          updateAmountDisplay(amount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
          
          console.log('Donation amount loaded:', amount, 'грн');
        } else {
          // Amount is too low or invalid, use fallback
          console.warn('Invalid amount detected:', amount, 'using fallback');
          throw new Error('Invalid amount: ' + amount);
        }
        
        // Debug: log the HTML content to help with troubleshooting
        if (amount === 0 || amount < 400) {
          console.warn('Low amount detected, HTML content preview:', htmlContent.substring(0, 500));
        }
        
      } catch(error) {
        console.warn('Failed to fetch from Monobank, using fallback:', error);
        
        // Fallback to a reasonable estimate based on current knowledge
        const fallbackAmount = 462; // Current known amount from manual check
        updateAmountDisplay(fallbackAmount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
        
        // Cache fallback for 5 minutes (shorter cache for fallback)
        localStorage.setItem('donationAmount', fallbackAmount.toString());
        localStorage.setItem('donationAmountTime', Date.now().toString());
      }
    }
    
    // Alternative method: try to get data from Monobank public API
    async function tryMonobankPublicAPI() {
      try {
        // This is a fallback method to try getting jar info
        const jarId = '6Vi9TVzJZQ';
        
        // Try direct approach with different headers
  const response = await fetch('https://send.monobank.ua/jar/' + jarId, {
          method: 'GET',
          mode: 'no-cors',
          headers: {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
          }
        });
        
        console.log('Direct Monobank response:', response);
        
      } catch (error) {
        console.log('Direct Monobank API not accessible:', error);
      }
    }
    
    function updateAmountDisplay(amount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement) {
      const formattedAmount = formatAmount(amount);
      const progressPercent = Math.min((amount / targetAmount) * 100, 100);
      
      if (amountElement) amountElement.textContent = formattedAmount;
      if (supportAmountElement) supportAmountElement.textContent = formattedAmount;
      if (progressAmountElement) progressAmountElement.textContent = formattedAmount;
      if (progressFillElement) {
        progressFillElement.style.width = progressPercent + '%';
        progressFillElement.style.background = progressPercent >= 100 
          ? 'linear-gradient(90deg, #10b981, #059669)' 
          : 'linear-gradient(90deg, #3b82f6, #8b5cf6)';
      }
      
      // Store as last known good amount
      localStorage.setItem('lastKnownAmount', amount.toString());
    }
    
    function handleAmountError(amountElement, supportAmountElement, progressAmountElement) {
      if (amountElement) amountElement.textContent = '0';
      if (supportAmountElement) supportAmountElement.textContent = '0';
      if (progressAmountElement) progressAmountElement.textContent = '0';
    }
    
    function formatAmount(amount) {
      // Format number with thousand separators and proper decimal handling
      if (typeof amount === 'string') {
        const num = parseFloat(amount);
        if (isNaN(num)) return amount;
        amount = num;
      }
      
      // Round to 2 decimal places if needed, then format with commas
      const rounded = Math.round(amount * 100) / 100;
      return rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    
    function copyDonate(val, btn){
      try { navigator.clipboard.writeText(val); } catch(e){
        const ta=document.createElement('textarea'); ta.value=val; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); }catch(e2){} document.body.removeChild(ta);
      }
      const toast = document.getElementById('copyToast');
      if(toast){ toast.classList.remove('show'); void toast.offsetWidth; toast.classList.add('show'); }
      if(btn){
        const orig = btn.innerHTML;
        btn.innerHTML = '<i class="material-icons" style="font-size:14px;">check_circle</i>Готово';
        setTimeout(()=>{ btn.innerHTML = orig; }, 2200);
      }
    }
    function openJar(){ window.open('https://send.monobank.ua/jar/6Vi9TVzJZQ','_blank','noopener'); }
    
    function refreshDonationAmount() {
      // Clear cache and force reload
      localStorage.removeItem('donationAmount');
      localStorage.removeItem('donationAmountTime');
      
      // Show loading state
      const supportAmountElement = document.getElementById('supportAmount');
      const progressAmountElement = document.getElementById('progressAmount');
      
      if (supportAmountElement) supportAmountElement.textContent = '...';
      if (progressAmountElement) progressAmountElement.textContent = '...';
      
      // Reload amount
      loadDonationAmount();
      
      console.log('Manual refresh of donation amount triggered');
    }
    
    // Debug functions for console testing
    window.testMonobankAPI = async function() {
      console.log('Testing Monobank API access...');
      
      const jarId = '6Vi9TVzJZQ';
      const proxyUrl = 'https://api.allorigins.win/get?url=' + encodeURIComponent('https://send.monobank.ua/jar/' + jarId);
      
      try {
        const response = await fetch(proxyUrl);
        const data = await response.json();
        console.log('API Response:', data);
        
        if (data.contents) {
          console.log('HTML Content preview:', data.contents.substring(0, 1000));
          
          // Test parsing
          const patterns = [
            /зібрано[:\s]*(\d+(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*грн/i,
            /(\d{2,}(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*грн/i
          ];
          
          for (const pattern of patterns) {
            const match = data.contents.match(pattern);
            if (match) {
              console.log('Found amount with pattern:', pattern, 'Amount:', match[1]);
            }
          }
        }
        
      } catch (error) {
        console.error('API Test failed:', error);
      }
    };
    
    window.setManualAmount = function(amount) {
      const targetAmount = 13200;
      const amountElement = document.getElementById('donationAmount')?.querySelector('.amount');
      const supportAmountElement = document.getElementById('supportAmount');
      const progressAmountElement = document.getElementById('progressAmount');
      const progressFillElement = document.getElementById('progressFill');
      
      updateAmountDisplay(amount, targetAmount, amountElement, supportAmountElement, progressAmountElement, progressFillElement);
      
      // Cache the manually set amount
      localStorage.setItem('donationAmount', amount.toString());
      localStorage.setItem('donationAmountTime', Date.now().toString());
      
      console.log('Manual amount set to:', amount);
    };
    
    // Keyboard event handlers
    document.addEventListener('keydown', e => { 
      if(e.key === 'Escape') { 
        toggleDonate(false); 
      } 
    });
    // Константы и настройки
    const UKRAINE_CENTER = { lat: 48.3794, lng: 31.1656 };
    
    // Cache busting timestamp for image updates
    const IMAGE_VERSION = '20250911184500'; // Updated when images are optimized
    
    // Optimized icon loading system with placeholders
    const ICONS = {
      shahed: `/static/shahed.png?v=${IMAGE_VERSION}`,
      raketa: `/static/raketa.png?v=${IMAGE_VERSION}`,
      avia: `/static/avia.png?v=${IMAGE_VERSION}`,
      pvo: `/static/rozved.png?v=${IMAGE_VERSION}`,
      rozved: `/static/rozved.png?v=${IMAGE_VERSION}`, // Reconnaissance UAVs
      rszv: `/static/rszv.png?v=${IMAGE_VERSION}`,
      vibuh: `/static/vibuh.png?v=${IMAGE_VERSION}`,
      alarm: `/static/trivoga.png?v=${IMAGE_VERSION}`,
      alarm_cancel: `/static/vidboi.png?v=${IMAGE_VERSION}`,
      mlrs: `/static/mlrs.png?v=${IMAGE_VERSION}`,
      artillery: `/static/artillery.png?v=${IMAGE_VERSION}`,
      obstril: `/static/obstril.png?v=${IMAGE_VERSION}`,
      fpv: `/static/fpv.png?v=${IMAGE_VERSION}`,
      default: `/static/default.png?v=${IMAGE_VERSION}`
    };
    
    // Placeholder versions for instant loading
    const PLACEHOLDERS = {
      shahed: `/static/placeholders/shahed.png?v=${IMAGE_VERSION}`,
      raketa: `/static/placeholders/raketa.png?v=${IMAGE_VERSION}`,
      avia: `/static/placeholders/avia.png?v=${IMAGE_VERSION}`,
      pvo: `/static/placeholders/rozved.png?v=${IMAGE_VERSION}`,
      rozved: `/static/placeholders/rozved.png?v=${IMAGE_VERSION}`, // Reconnaissance UAVs
      rszv: `/static/placeholders/rszv.png?v=${IMAGE_VERSION}`,
      vibuh: `/static/placeholders/vibuh.png?v=${IMAGE_VERSION}`,
      alarm: `/static/placeholders/trivoga.png?v=${IMAGE_VERSION}`,
      alarm_cancel: `/static/placeholders/vidboi.png?v=${IMAGE_VERSION}`,
      mlrs: `/static/placeholders/mlrs.png?v=${IMAGE_VERSION}`,
      artillery: `/static/placeholders/artillery.png?v=${IMAGE_VERSION}`,
      obstril: `/static/placeholders/obstril.png?v=${IMAGE_VERSION}`,
      fpv: `/static/placeholders/fpv.png?v=${IMAGE_VERSION}`,
      default: `/static/placeholders/default.png?v=${IMAGE_VERSION}`
    };
    
    // Lazy loading system for images with progressive enhancement
    const imageCache = new Map();
    const loadingImages = new Map();
    const placeholderCache = new Map();
    
    // Tiny placeholder for immediate display
    const INSTANT_PLACEHOLDER = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    
    // Fallback icon for errors
    const FALLBACK_ICON = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAALElEQVQokWP8////fwY0wAgjGJgGLABWMMRAFEg0gGE0GoBmGuwmCkYBAGmxD/dzJvLRwAAAABJRU5ErkJggg==';
    
    // Progressive image loader: placeholder → optimized image
    function loadImageProgressive(iconType) {
      const fullUrl = ICONS[iconType] || ICONS.default;
      const placeholderUrl = PLACEHOLDERS[iconType] || PLACEHOLDERS.default;
      
      return new Promise((resolve) => {
        // Step 1: Try to load placeholder first (very fast)
        if (placeholderUrl && !placeholderCache.has(placeholderUrl)) {
          const placeholderImg = new Image();
          placeholderImg.onload = () => {
            placeholderCache.set(placeholderUrl, true);
          };
          placeholderImg.src = placeholderUrl;
        }
        
        // Return placeholder immediately for instant display
        resolve(placeholderUrl || INSTANT_PLACEHOLDER);
        
        // Step 2: Load full quality image in background
        setTimeout(() => {
          if (!imageCache.has(fullUrl)) {
            const fullImg = new Image();
            fullImg.onload = () => {
              imageCache.set(fullUrl, true);
              // Update any markers using this icon
              updateMarkersWithFullImage(iconType, fullUrl);
            };
            fullImg.onerror = () => {
              console.warn(`Failed to load full image: ${fullUrl}`);
              imageCache.set(fullUrl, 'error');
            };
            fullImg.src = fullUrl;
          }
        }, 100); // Small delay to prioritize placeholder loading
      });
    }
    
    // Update markers with full quality images when available
    function updateMarkersWithFullImage(iconType, fullUrl) {
      // Find all img elements using this icon type and update them
      document.querySelectorAll(`img[data-icon-type="${iconType}"]`).forEach(img => {
        if (imageCache.get(fullUrl) === true) {
          img.style.transition = 'opacity 0.3s ease-in-out';
          img.style.opacity = '0.7';
          setTimeout(() => {
            img.src = fullUrl;
            img.style.opacity = '1';
          }, 50);
        }
      });
    }
    
    // Priority-based preloading for most common icons
    function preloadCriticalIcons() {
      const criticalIcons = ['shahed', 'raketa', 'avia', 'rozved', 'alarm']; // Most common types
      
      criticalIcons.forEach((iconType, index) => {
        setTimeout(() => {
          loadImageProgressive(iconType);
        }, index * 100); // Stagger loading
      });
    }
    
    // Background preloading for remaining icons (lower priority)
    function preloadRemainingIcons() {
      const remainingIcons = Object.keys(ICONS).filter(key => 
        !['shahed', 'raketa', 'avia', 'alarm'].includes(key)
      );
      
      // Delay and spread out loading to avoid bandwidth congestion
      remainingIcons.forEach((iconType, index) => {
        setTimeout(() => {
          loadImageProgressive(iconType);
        }, (index + 1) * 300); // 300ms between each load
      });
    }
    
    // Smart icon getter with progressive loading
    async function getIconUrl(iconType) {
      try {
        return await loadImageProgressive(iconType);
      } catch (error) {
        console.warn(`Failed to get icon ${iconType}:`, error);
        return FALLBACK_ICON;
      }
    }
    // Состояние приложения
  let map;
    let markerLayer = null;
    let markers = [];
    // Проста мапа транслітерації/перекладу російських / застарілих назв на українські
    const PLACE_UA_MAP = (()=>{
      const m = new Map([
        ['киев','Київ'],['київ','Київ'],['kiev','Київ'],
        ['одесса','Одеса'],['odesa','Одеса'],
        ['харьков','Харків'],['kharkov','Харків'],['харків','Харків'],
        ['днепропетровск','Дніпро'],['дніпропетровськ','Дніпро'],['днепр','Дніпро'],['дніпр','Дніпро'],['dnipro','Дніпро'],
        ['чернигов','Чернігів'],['чернигів','Чернігів'],
        ['запорожье','Запоріжжя'],['запорожье','Запоріжжя'],['запоріжье','Запоріжжя'],['запоріжжя','Запоріжжя'],
        ['николаев','Миколаїв'],['миколаев','Миколаїв'],['миколаїв','Миколаїв'],
        ['житомир','Житомир'],
        ['полтава','Полтава'],
        ['херсон','Херсон'],
        ['луганск','Луганськ'],['луганськ','Луганськ'],
        ['донецк','Донецьк'],['донецьк','Донецьк'],
        ['суми','Суми'],['сумы','Суми'],
        ['черкассы','Черкаси'],['черкасі','Черкаси'],
        ['черновцы','Чернівці'],['чернівці','Чернівці'],
        ['ивано-франковск','Івано-Франківськ'],['івано-франківськ','Івано-Франківськ'],
        ['львов','Львів'],['львів','Львів'],
        ['ужгород','Ужгород'],
        ['тернополь','Тернопіль'],['тернопіль','Тернопіль'],
        ['винница','Вінниця'],['вінниця','Вінниця'],
        ['ровно','Рівне'],['ровне','Рівне'],['рівне','Рівне'],
        ['кропивницкий','Кропивницький'],['кропивницький','Кропивницький'],
        ['севастополь','Севастополь'],
        ['симферополь','Сімферополь'],
        ['мариуполь','Маріуполь'],['маріуполь','Маріуполь'],
        ['горловка','Горлівка'],['горлівка','Горлівка'],
        ['алчевск','Алчевськ'],['алчевськ','Алчевськ']
      ]);
      return m;
    })();
    function normalizeKey(s){ return s.toLowerCase().replace(/\s+/g,' ').trim(); }
    function translatePlace(name){
      if(!name || typeof name !== 'string') return name;
      const key = normalizeKey(name);
      if(PLACE_UA_MAP.has(key)) return PLACE_UA_MAP.get(key);
      // Якщо вже містить українські специфічні літери – залишаємо
      if(/[іїєґ]/i.test(name)) return name;
      // Легка заміна рос. літер на укр. приблизно
      let t = name
        .replace(/ё/g,'йо').replace(/ы/g,'и').replace(/э/g,'е')
        .replace(/ъ/g,'ʼ');
      return t;
    }
    // Удаляем лишние звездочки / markdown-звезды из текста
    function cleanMessage(t){
      if(!t) return t;
      // убрать тройные/двойные звездочки и одиночные вокруг эмодзи/слов
      let s = t.replace(/\*{2,}/g,'');
      // убрать звездочки, прилегающие к началу/концу строки
      s = s.replace(/^\*+/,'').replace(/\*+$/,'');
      return s.trim();
    }
    // Цільові міста для відображення спеціальної іконки FPV при загрозі БПЛА
    const FPV_CITIES = ['херсон','білозерка','марганець','нікополь'];
    function isFPVThreat(place, text, threatType){
      const combined = (place ? place + ' ' : '') + (text || '');
      const lower = combined.toLowerCase();
      if(!FPV_CITIES.some(c => lower.includes(c))) return false;
      const tt = (threatType||'').toLowerCase();
      const txt = (text||'').toLowerCase();
      // Exclude reconnaissance / observation drone reports
      if(/розвід|развед|спостереж/i.test(txt)) return false;
      // Always treat shahed stream as threat
      if (tt === 'shahed') return true;
      const hasFPV = /\bfpv\b/.test(txt);
      const hasGenericUAV = /бпла/.test(txt);
      // Attack / strike intent keywords
      const attackCtx = /(удар|ата(к|ц)|прил(і|ы)т|мас(ов|ова)|загроз|пуск|запуск|зліт|виліт|вылет|злет)/.test(txt);
      if (hasFPV) return true;
      if (hasGenericUAV && attackCtx) return true;
      return false;
    }
    // Helper: build semi-circle polygon (returns array of [lat,lng])
    function buildSemiCircle(lat, lng, startBearing, endBearing, radiusKm, segments){
      const pts=[]; const R=6371; const toRad=d=>d*Math.PI/180; const toDeg=r=>r*180/Math.PI;
      const lat1=toRad(lat); const lon1=toRad(lng); const angDist=radiusKm/R;
      let span = (endBearing - startBearing); if (span < 0) span += 360;
      for(let i=0;i<=segments;i++){
        const brg = (startBearing + span*(i/segments)) % 360;
        const br = toRad(brg);
        const lat2 = Math.asin(Math.sin(lat1)*Math.cos(angDist)+Math.cos(lat1)*Math.sin(angDist)*Math.cos(br));
        const lon2 = lon1 + Math.atan2(Math.sin(br)*Math.sin(angDist)*Math.cos(lat1), Math.cos(angDist)-Math.sin(lat1)*Math.sin(lat2));
        pts.push([toDeg(lat2), ((toDeg(lon2)+540)%360)-180]);
      }
      pts.unshift([lat,lng]);
      return pts;
    }
    async function updateMarkers() {
      const timeRange = 50; // fixed
      const threatType = document.getElementById('threatTypeSelect').value;
      const params = new URLSearchParams({ timeRange, confRange: 0 });
  const overlay = document.getElementById('markerLoadingOverlay');
  if (overlay && (!markers || markers.length===0)) overlay.classList.remove('hidden');
      const res = await fetch(`/data?${params.toString()}`);
      const data = await res.json();
      let points = (data.tracks || []).filter(p => {
        if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return false;
        if (isNaN(p.lat) || isNaN(p.lng)) return false;
        if (Math.abs(p.lat) < 1 && Math.abs(p.lng) < 1) return false;
        if (p.lat < 43 || p.lat > 53.5 || p.lng < 21 || p.lng > 41) return false;
        const vague = ['схід','захід','північ','південь','восток','запад','север','юг'];
        if (!p.place || vague.includes(p.place.toLowerCase())) return false;
        return true;
      });
  // Expose current points for search suggestions
  window.__lastPoints = points;
      if (threatType) points = points.filter(p => (p.threat_type || '').toLowerCase() === threatType);
  if (overlay) { if (points.length>0) overlay.classList.add('hidden'); else overlay.classList.remove('hidden'); }
      if (markerLayer) { markerLayer.clearLayers(); }
      else { markerLayer = L.layerGroup().addTo(map); }
      markers = [];
      // --------- Performance adaptive mode ---------
      const MAX_DIRECT_MARKERS = 650; // threshold where we switch to clustered fast mode
      const useFastMode = points.length > MAX_DIRECT_MARKERS;
      if (useFastMode) {
        const z = map.getZoom();
        // cell size (degrees) shrinks with zoom to gradually reveal more detail
        let cell = 0.55;
        if (z >= 7) cell = 0.32; if (z >= 8) cell = 0.18; if (z >= 9) cell = 0.11; if (z >= 10) cell = 0.06;
        const keyFn = p => `${Math.floor(p.lat / cell)}_${Math.floor(p.lng / cell)}`;
        const buckets = new Map();
        for (const p of points){
          const k = keyFn(p);
            let b = buckets.get(k);
            if(!b){ b = { items:[], latSum:0, lngSum:0, types: new Map(), latest:0 }; buckets.set(k,b); }
            b.items.push(p); b.latSum += p.lat; b.lngSum += p.lng; 
            const tt=(p.threat_type||'').toLowerCase(); b.types.set(tt, (b.types.get(tt)||0)+1);
            const ts = Date.parse((p.date||'').replace(/-/g,'/')) || 0; if(ts> b.latest) b.latest = ts;
        }
        buckets.forEach(async b => {
          const lat = b.latSum / b.items.length;
          const lng = b.lngSum / b.items.length;
          // choose dominant threat type for icon (fallback default)
          let dominant = 'default'; let maxc=0;
          b.types.forEach((c,t)=>{ if(c>maxc){ maxc=c; dominant=t; } });
          
          // Use optimized async image loading for clusters
          let iconUrl = PLACEHOLDER_ICON; // Start with placeholder
          try {
            iconUrl = await getIconUrl(dominant);
          } catch (error) {
            console.warn('Failed to load cluster icon:', error);
            iconUrl = FALLBACK_ICON;
          }
          
          const count = b.items.length;
          const ageMin = (Date.now()-b.latest)/60000;
          const freshness = ageMin < 8 ? 'fresh' : ageMin < 20 ? 'stale' : 'old';
          const html = `<div class='cluster cluster-${freshness}'><img src='${iconUrl}' alt='' loading="lazy"><b>${count}</b></div>`;
          const icon = L.divIcon({ html, className:'', iconSize:[44,52], iconAnchor:[22,48] });
          const m = L.marker([lat,lng], {icon});
          // Popup summary
          const typeLines = [...b.types.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([t,c])=>`<div>${t||'—'}: ${c}</div>`).join('');
          m.bindPopup(`<div style='font-size:.7rem;line-height:1.25;'><b>${count}</b> подій<br>${typeLines}<div style='margin-top:4px;opacity:.55;'>кластер (деталі при збільшенні)</div></div>`);
          m.addTo(markerLayer); markers.push(m);
        });
        // Style inject (once)
        if(!document.getElementById('clusterStyles')){
          const st=document.createElement('style'); st.id='clusterStyles'; st.textContent=`
            .cluster{position:relative;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#1e293b,#0f172a);border:2px solid #334155;border-radius:18px;padding:4px 6px 6px;box-shadow:0 4px 12px -3px rgba(0,0,0,.4);} 
            .cluster img{width:26px;height:26px;object-fit:contain;filter:drop-shadow(0 0 4px rgba(0,0,0,.5));margin-right:2px;} 
            .cluster b{font-size:.8rem;font-family:Inter,system-ui,sans-serif;color:#fff;text-shadow:0 1px 2px #000;} 
            .cluster-fresh{background:linear-gradient(160deg,#164e63,#0f2d40);border-color:#155e75;} 
            .cluster-stale{background:linear-gradient(160deg,#3f3f46,#27272a);border-color:#52525b;} 
            .cluster-old{background:linear-gradient(160deg,#1e1b4b,#0f172a);border-color:#312e81;opacity:.72;} 
          `; document.head.appendChild(st); }
        // Update event list but skip detailed marker render heavy stuff
        updateEventList(data.events || []);
        try { document.dispatchEvent(new CustomEvent('markersUpdated', {detail: data})); } catch(e){}
  if (overlay && points.length>0) overlay.classList.add('hidden');
        return; // exit early in fast mode
      }
  // Container for border-shelling overlays (semi-circles)
  let borderShellingDrawn = false;
      points.forEach(async p => {
        let iconUrl = ICONS[p.threat_type] || ICONS.default;
        if (p.marker_icon) {
          iconUrl = (p.marker_icon.startsWith('http') || p.marker_icon.startsWith('/')) ? p.marker_icon : '/static/' + p.marker_icon;
        }
        // Override for FPV targeted settlements
        if (isFPVThreat(p.place, p.text, p.threat_type)) {
          iconUrl = ICONS.fpv || iconUrl;
        }
        
        // Use optimized async image loading
        try {
          iconUrl = await getIconUrl(p.threat_type || 'default');
        } catch (error) {
          console.warn('Failed to load icon, using fallback:', error);
          iconUrl = FALLBACK_ICON;
        }
        // Extract inline count / direction from place label pattern 'Name (N) ←півдня'
        if (!p.count && p.place) {
          const m = p.place.match(/\((\d{1,3})\)/);
          if (m) { p.count = parseInt(m[1]); }
        }
        let arrowDir = null;
        if (p.place && p.place.includes('←')) {
          arrowDir = p.place.split('←').pop().trim();
        }
  const threatClass = (p.threat_type||'default').toLowerCase();
  const countBadge = (p.threat_type==='shahed' || /shahed|шахед|бпла/i.test(p.threat_type||'')) && p.count && p.count>1 ? `<div class="tm-badge">${p.count}×</div>` : '';
  // Dynamic scale: keep screen footprint smaller on distant zooms so visual offset feels minimal
  let z = map.getZoom ? map.getZoom() : 6;
  let base = 34; // base size at mid zoom
  // scale factor: grow slightly after zoom 7, shrink under 5
  let factor = z >= 9 ? 1.25 : z >= 7 ? 1.0 : z >= 6 ? 0.85 : z >=5 ? 0.7 : 0.55;
  const w = Math.round(base * factor);
  const h = Math.round(w * 1.15);
  const html = `<div class='tm-wrap'><img class='plain-marker-img' style='width:${w}px;height:${h}px;' src='${iconUrl}' alt='' loading="lazy" data-icon-type="${p.threat_type || 'default'}">${countBadge}</div>`;
  // Anchor to visual center (half width/height) instead of bottom so geographic point stays stable when scaling
  const icon = L.divIcon({ html, className:'', iconSize:[w,h], iconAnchor:[w/2, h/2], popupAnchor:[0,-h/2] });
  const m = L.marker([p.lat, p.lng], { icon, riseOnHover:true });
        // Optional short polyline showing nominal approach direction (simple cardinal/ordinal mapping)
        if (arrowDir) {
          const dir = arrowDir.toLowerCase();
          let dx=0, dy=0;
          if (dir.includes('півд')) dy = -0.25; // tail origin south of marker => movement northwards
          if (dir.includes('північ')) dy = 0.25;
          if (dir.includes('сход')) dx = -0.25; // east origin => movement westwards
          if (dir.includes('зах')) dx = 0.25;
          if (dx !==0 || dy !==0) {
            const tailStart=[p.lat+dy, p.lng+dx];
            // Simple static direction hint line
            L.polyline([tailStart,[p.lat,p.lng]], {color:'#f59e0b', weight:2, opacity:0.55, dashArray:'4 3'}).addTo(markerLayer);
            // Animated trajectory arc for missiles / drones
            if (/(raketa|shahed|fpv|pusk)/i.test(p.threat_type||'')) {
              try { addTrajectoryArc(p, dx, dy); } catch(e){}
            }
          }
        }
        
        // Enhanced Shahed course visualization
        if (p.threat_type === 'shahed' && (p.course_source || p.course_target || p.course_direction)) {
          try {
            addShahedCourseVisualization(p);
          } catch(e) {
            console.warn('Shahed course visualization failed:', e);
          }
        }
        const placeUA = translatePlace(p.place);
        const popupHtml = `<div style=\"background:#ffffff;color:#1e293b;border:1px solid #d7dde3;border-radius:12px;padding:10px 10px;min-width:190px;font-size:.8rem;line-height:1.35;box-shadow:0 4px 14px -4px rgba(0,0,0,.18);\">`
          + (placeUA ? `<div style='font-size:.9rem;font-weight:600;margin-bottom:4px;'>${placeUA}</div>` : '')
          + (p.count ? `<div style='margin-bottom:4px;font-weight:600;color:#b91c1c;'>Кількість: ${p.count}×</div>` : '')
          + `<div style='white-space:pre-wrap;'>${cleanMessage(p.text||'')}</div>`
          + `<div style='margin-top:6px;font-size:.6rem;opacity:.55;'>${p.date || ''}</div>`
          + `</div>`;
        m.bindPopup(popupHtml, { closeButton:false, autoPan:true });
  if (p.count && p.count > 1) { m.openPopup(); }
        markerLayer.addLayer(m);
        markers.push(m);

        // Red semi-circle (sector) for border shelling alerts (visualizing incoming danger from external border)
        if (p.border_shelling && !borderShellingDrawn) {
          borderShellingDrawn = true; // only one large overlay per update to avoid clutter
          try {
            // Draw a semi-circle (180°) oriented toward likely hostile border (east / north-east for Харківська / Сумська, adjust by longitude)
            const centerLat = p.lat; const centerLng = p.lng;
            const spanKm = 120; // radius
            const segments = 80; // smoothness
            // Bearing range depending on oblast heuristic
            let startBearing = 315; // NW
            let endBearing = 135;  // SE
            if (centerLng > 35) { startBearing = 290; endBearing = 110; }
            const pts = [];
            const R = 6371; // km
            const toRad = d=>d*Math.PI/180; const toDeg = r=>r*180/Math.PI;
            for(let i=0;i<=segments;i++){
              const brg = startBearing + (endBearing-startBearing)* (i/segments);
              const d = spanKm / R; // angular distance
              const br = toRad(brg);
              const lat1 = toRad(centerLat);
              const lon1 = toRad(centerLng);
              const lat2 = Math.asin(Math.sin(lat1)*Math.cos(d)+Math.cos(lat1)*Math.sin(d)*Math.cos(br));
              const lon2 = lon1 + Math.atan2(Math.sin(br)*Math.sin(d)*Math.cos(lat1), Math.cos(d)-Math.sin(lat1)*Math.sin(lat2));
              pts.push([toDeg(lat2), ((toDeg(lon2)+540)%360)-180]);
            }
            pts.unshift([centerLat, centerLng]);
            const poly = L.polygon(pts, {color:'#b91c1c', weight:1, fillColor:'#dc2626', fillOpacity:0.18, stroke:true});
            poly.addTo(markerLayer);
          } catch(e){}
        }
        // KAB guided bomb threat zone (semi-circle) for raketa markers whose text mentions 'каб'
        if (!p.border_shelling && p.threat_type && p.threat_type.toLowerCase()==='raketa' && /каб/i.test(p.text||'')) {
          try {
            const centerLat = p.lat; const centerLng = p.lng;
            // West-facing semi-circle (threat from east -> projecting toward Ukraine)
            const startBearing = 180, endBearing = 360;
            const OUTER = 10; // km outer radius (reduced from 50)
            const segments = 96;
            // Ensure SVG gradients exist once
            (function ensureKabGrad(){
              const mapPane = document.querySelector('.leaflet-overlay-pane svg');
              if(!mapPane) return;
              if(mapPane.querySelector('#kabGradOuter')) return;
              const defs = mapPane.querySelector('defs') || (function(){ const d=document.createElementNS('http://www.w3.org/2000/svg','defs'); mapPane.insertBefore(d,mapPane.firstChild); return d; })();
              const gOuter = document.createElementNS('http://www.w3.org/2000/svg','radialGradient');
              gOuter.id='kabGradOuter'; gOuter.setAttribute('fx','35%'); gOuter.setAttribute('fy','30%');
              [['0%','#ff7b6f'],['65%','rgba(255,59,48,0.55)'],['100%','rgba(255,59,48,0)']].forEach(([o,c])=>{ const stop=document.createElementNS('http://www.w3.org/2000/svg','stop'); stop.setAttribute('offset',o); stop.setAttribute('stop-color',c); defs.appendChild(gOuter); gOuter.appendChild(stop); });
              const gMid = document.createElementNS('http://www.w3.org/2000/svg','radialGradient');
              gMid.id='kabGradMid'; gMid.setAttribute('fx','40%'); gMid.setAttribute('fy','35%');
              [['0%','#ffb4ab'],['60%','rgba(255,107,94,.65)'],['100%','rgba(255,107,94,0)']].forEach(([o,c])=>{ const stop=document.createElementNS('http://www.w3.org/2000/svg','stop'); stop.setAttribute('offset',o); stop.setAttribute('stop-color',c); defs.appendChild(gMid); gMid.appendChild(stop); });
            })();
            const layerDefs = [
              {r:OUTER, cls:'kab-zone-outer'},
              {r:OUTER*0.66, cls:'kab-zone-mid'},
              {r:OUTER*0.38, cls:'kab-zone-inner'}
            ];
            layerDefs.forEach(ld=>{
              const pts = buildSemiCircle(centerLat, centerLng, startBearing, endBearing, ld.r, segments);
              const poly = L.polygon(pts, {className:ld.cls, color:'#ff3b30', weight:0.6, fillOpacity:0.22, stroke:true}).addTo(markerLayer);
            });
            // Scanning arc (outline only)
            const scanPts = buildSemiCircle(centerLat, centerLng, startBearing, endBearing, OUTER*0.92, segments);
            const scan = L.polygon(scanPts, {className:'kab-zone-scan', color:'#ffe0dc', weight:1, fill:false});
            scan.addTo(markerLayer);
            try { addKabRotor(centerLat, centerLng, OUTER*0.92); } catch(e){}
            // Center glow & label using a divIcon
            const centerDiv = L.divIcon({ html:`<div class='kab-center-glow'></div>`, className:'', iconSize:[36,36] });
            L.marker([centerLat, centerLng], {icon:centerDiv, interactive:false}).addTo(markerLayer);
            // Label placed at midpoint of arc (bearing 270°)
            const midBearing = 270 * Math.PI/180; const R=6371; const d= (OUTER*0.62)/R; const toRad=x=>x*Math.PI/180; const toDeg=r=>r*180/Math.PI;
            const lat1=toRad(centerLat); const lon1=toRad(centerLng);
            const lat2 = Math.asin(Math.sin(lat1)*Math.cos(d)+Math.cos(lat1)*Math.sin(d)*Math.cos(midBearing));
            const lon2 = lon1 + Math.atan2(Math.sin(midBearing)*Math.sin(d)*Math.cos(lat1), Math.cos(d)-Math.sin(lat1)*Math.sin(lat2));
            const labelDiv = L.divIcon({ html:`<div class='kab-label'>КАБ<br><span style='font-weight:400;opacity:.8'>~${OUTER}км</span></div>`, className:'', iconSize:[1,1] });
            L.marker([toDeg(lat2), ((toDeg(lon2)+540)%360)-180], {icon:labelDiv, interactive:false}).addTo(markerLayer);
          } catch(e){}
        }
      });
      updateEventList(data.events || []);
  // Notify listeners (banner heuristics etc.)
  try { document.dispatchEvent(new CustomEvent('markersUpdated', {detail: data})); } catch(e){}
  if (overlay && markers.length>0) overlay.classList.add('hidden');
    }
    // Re-scale markers on zoom (debounced)
    let _zoomRedrawTimer=null;
    function hookZoomRedraw(){
      if(!map) return;
      map.on('zoomend', ()=>{
        if(_zoomRedrawTimer) clearTimeout(_zoomRedrawTimer);
        _zoomRedrawTimer = setTimeout(()=>updateMarkers(), 40);
      });
    }
    // Create a curved arc (quadratic bezier approximation) and fading tail
    function addTrajectoryArc(p, dx, dy){
      const isDrone = /(shahed|fpv)/i.test(p.threat_type||'');
      const scale = isDrone ? 1.4 : 2.0; // longer for missiles
      const latEnd = p.lat, lngEnd = p.lng;
      const latStart = latEnd + dy*scale;
      const lngStart = lngEnd + dx*scale;
      // Perp vector for curvature
      let perpX = -dy, perpY = dx;
      const norm = Math.hypot(perpX, perpY)||1;
      perpX/=norm; perpY/=norm;
      const curveFactor = 0.35 * (isDrone?0.8:1); // subtler for drones
      const controlLat = (latStart+latEnd)/2 + perpY*curveFactor;
      const controlLng = (lngStart+lngEnd)/2 + perpX*curveFactor;
      const steps = 24;
      const pts = [];
      for(let i=0;i<=steps;i++){
        const t = i/steps; // quadratic bezier
        const oneMinus = 1-t;
        const lat = oneMinus*oneMinus*latStart + 2*oneMinus*t*controlLat + t*t*latEnd;
        const lng = oneMinus*oneMinus*lngStart + 2*oneMinus*t*controlLng + t*t*lngEnd;
        pts.push([lat,lng]);
      }
      // Animated dashed arc (continuous)
      L.polyline(pts, {color: isDrone? '#00b3ff':'#ff784e', weight:2.2, opacity:0.8, className:'traj-arc'+(isDrone?' drone':'')}).addTo(markerLayer);
      // Fading thicker tail (static path that fades out)
      L.polyline(pts, {color: isDrone? '#41c9ff':'#ff9d7b', weight:3.4, opacity:0.5, className:'traj-tail'+(isDrone?' drone':'')}).addTo(markerLayer);
    }
    
    // --- Shahed course visualization ---
    function addShahedCourseVisualization(p) {
      const { course_source, course_target, course_direction, course_type } = p;
      
      // If we have specific source and target cities, try to draw a path between them
      if (course_source && course_target) {
        // This would require city coordinates lookup on frontend
        // For now, we'll use the direction information
        addCourseDirectionIndicator(p, course_direction || 'на ' + course_target);
        return;
      }
      
      // If we have course direction, show it
      if (course_direction) {
        addCourseDirectionIndicator(p, course_direction);
        return;
      }
      
      // If we have target city, show direction arrow pointing roughly toward it
      if (course_target) {
        addCourseDirectionIndicator(p, 'на ' + course_target);
        return;
      }
    }
    
    // --- Course direction indicator for Shahed threats ---
    function addCourseDirectionIndicator(p, directionText) {
      const lat = p.lat, lng = p.lng;
      let dx = 0, dy = 0;
      
      // Parse direction from text
      const dir = directionText.toLowerCase();
      
      // Extract city name if format is "на [city]"
      const cityMatch = dir.match(/на\s+([а-яіїєґa-z\s\-']+)/);
      if (cityMatch) {
        const cityName = cityMatch[1].trim();
        
        // Simple heuristic direction mapping based on well-known cities
        const cityDirections = {
          'київ': {dx: 0.4, dy: 0.6},
          'харків': {dx: 0.7, dy: 0.2},
          'дніпро': {dx: 0.5, dy: -0.1},
          'одеса': {dx: -0.3, dy: -0.5},
          'львів': {dx: -0.8, dy: 0.3},
          'чернігів': {dx: 0.2, dy: 0.8},
          'суми': {dx: 0.6, dy: 0.5},
          'полтава': {dx: 0.5, dy: 0.3},
          'кременчук': {dx: 0.3, dy: 0.1},
          'черкаси': {dx: 0.2, dy: 0.2}
        };
        
        // Find matching city
        for (const [city, coords] of Object.entries(cityDirections)) {
          if (cityName.includes(city)) {
            dx = coords.dx;
            dy = coords.dy;
            break;
          }
        }
      }
      
      // Fallback to cardinal directions if no city match
      if (dx === 0 && dy === 0) {
        if (dir.includes('північ')) dy = 0.5;
        if (dir.includes('південь') || dir.includes('півден')) dy = -0.5;
        if (dir.includes('схід')) dx = 0.5;
        if (dir.includes('захід')) dx = -0.5;
        
        // Compound directions
        if (dir.includes('північно-схід') || dir.includes('північний схід')) {
          dx = 0.35; dy = 0.35;
        } else if (dir.includes('північно-захід') || dir.includes('північний захід')) {
          dx = -0.35; dy = 0.35;
        } else if (dir.includes('південно-схід') || dir.includes('південний схід')) {
          dx = 0.35; dy = -0.35;
        } else if (dir.includes('południowo-zachód') || dir.includes('південний захід')) {
          dx = -0.35; dy = -0.35;
        }
      }
      
      // Create course line if we have direction
      if (dx !== 0 || dy !== 0) {
        const startLat = lat - dy * 0.3;
        const startLng = lng - dx * 0.3;
        const endLat = lat + dy * 0.8;
        const endLng = lng + dx * 0.8;
        
        // Course line
        const courseLine = L.polyline([
          [startLat, startLng],
          [lat, lng],
          [endLat, endLng]
        ], {
          color: '#00d4ff',
          weight: 3,
          opacity: 0.8,
          dashArray: '8 4',
          className: 'shahed-course-line'
        }).addTo(markerLayer);
        
        // Direction arrow at the end
        const arrowSize = 0.1;
        const arrowPoints = [
          [endLat, endLng],
          [endLat - dy * arrowSize + dx * arrowSize * 0.5, endLng - dx * arrowSize - dy * arrowSize * 0.5],
          [endLat - dy * arrowSize - dx * arrowSize * 0.5, endLng - dx * arrowSize + dy * arrowSize * 0.5]
        ];
        
        L.polyline(arrowPoints, {
          color: '#00d4ff',
          weight: 3,
          opacity: 0.9,
          className: 'shahed-course-arrow'
        }).addTo(markerLayer);
        
        // Add course info to popup if it exists
        setTimeout(() => {
          const courseInfo = `<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #333;">
            <strong>🎯 Курс:</strong> ${directionText}
          </div>`;
          
          // Try to add to existing popup content
          if (p._popup && p._popup.getContent) {
            const existingContent = p._popup.getContent();
            p._popup.setContent(existingContent + courseInfo);
          }
        }, 100);
      }
    }
    // --- KAB rotating scan line (single per map instance concurrently) ---
    function addKabRotor(lat, lng, radiusKm){
      // Access overlay pane SVG
      const pane = document.querySelector('.leaflet-overlay-pane svg');
      if(!pane) return;
      // Gradient for tail if not present
      let defs = pane.querySelector('defs');
      if(!defs){ defs=document.createElementNS('http://www.w3.org/2000/svg','defs'); pane.insertBefore(defs,pane.firstChild); }
      if(!pane.querySelector('#kabRotorGrad')){
        const lg=document.createElementNS('http://www.w3.org/2000/svg','linearGradient');
        lg.id='kabRotorGrad'; lg.setAttribute('x1','0%'); lg.setAttribute('y1','50%'); lg.setAttribute('x2','100%'); lg.setAttribute('y2','50%');
        [['0%','rgba(255,224,220,0)'],['35%','rgba(255,224,220,0.05)'],['65%','rgba(255,150,130,0.55)'],['100%','rgba(255,120,100,0.95)']].forEach(([o,c])=>{ const st=document.createElementNS('http://www.w3.org/2000/svg','stop'); st.setAttribute('offset',o); st.setAttribute('stop-color',c); lg.appendChild(st); });
        defs.appendChild(lg);
      }
      // Build a group with a short line from center to arc
      const g=document.createElementNS('http://www.w3.org/2000/svg','g');
      g.setAttribute('class','kab-rotor-group');
      // Convert lat/lng to projected points using Leaflet internal projection
      const mapPointCenter = map.latLngToLayerPoint([lat,lng]);
      // pick an initial angle (random for slight variation)
      const angle = Math.random()*Math.PI*2;
      const edgeLatLng = destinationPoint(lat,lng,angle,radiusKm);
      const edgePoint = map.latLngToLayerPoint(edgeLatLng);
      const line=document.createElementNS('http://www.w3.org/2000/svg','line');
      line.setAttribute('x1',mapPointCenter.x); line.setAttribute('y1',mapPointCenter.y);
      line.setAttribute('x2',edgePoint.x); line.setAttribute('y2',edgePoint.y);
      line.setAttribute('class','kab-rotor-line');
      // Tail (shorter) offset slightly behind main line
      const tail=document.createElementNS('http://www.w3.org/2000/svg','line');
      tail.setAttribute('x1',mapPointCenter.x); tail.setAttribute('y1',mapPointCenter.y);
      tail.setAttribute('x2', (mapPointCenter.x+edgePoint.x)/2); tail.setAttribute('y2',(mapPointCenter.y+edgePoint.y)/2);
      tail.setAttribute('class','kab-rotor-tail');
      g.appendChild(tail); g.appendChild(line); pane.appendChild(g);
      // Recenter transform origin to center (SVG group rotates around 0,0 with applied translate)
      g.style.transformOrigin = `${mapPointCenter.x}px ${mapPointCenter.y}px`;
      // Helper to update geometry on zoom/pan
      function refresh(){
        const centerP = map.latLngToLayerPoint([lat,lng]);
        const edgeLatLng2 = destinationPoint(lat,lng,angle, radiusKm);
        const edgeP = map.latLngToLayerPoint(edgeLatLng2);
        line.setAttribute('x1',centerP.x); line.setAttribute('y1',centerP.y);
        line.setAttribute('x2',edgeP.x); line.setAttribute('y2',edgeP.y);
        tail.setAttribute('x1',centerP.x); tail.setAttribute('y1',centerP.y);
        tail.setAttribute('x2',(centerP.x+edgeP.x)/2); tail.setAttribute('y2',(centerP.y+edgeP.y)/2);
        g.style.transformOrigin = `${centerP.x}px ${centerP.y}px`;
      }
      map.on('zoom move', refresh);
      // Cleanup when layer group cleared
      if(markerLayer){ markerLayer.on('remove', ()=>{ try{ g.remove(); }catch(e){} map.off('zoom',refresh); map.off('move',refresh); }); }
    }
    function destinationPoint(lat,lng,bearingRad,distKm){
      const R=6371; const δ=distKm/R; const φ1=lat*Math.PI/180; const λ1=lng*Math.PI/180; const θ=bearingRad; const sinφ1=Math.sin(φ1), cosφ1=Math.cos(φ1), sinδ=Math.sin(δ), cosδ=Math.cos(δ); const sinφ2 = sinφ1*cosδ + cosφ1*sinδ*Math.cos(θ); const φ2 = Math.asin(sinφ2); const y = Math.sin(θ)*sinδ*cosφ1; const x = cosδ - sinφ1*sinφ2; const λ2 = λ1 + Math.atan2(y,x); return [ (φ2*180/Math.PI), ((λ2*180/Math.PI)+540)%360-180 ]; }
    function updateEventList(points) {
      const el = document.getElementById('eventList');
      if (!el) return;
      if (!points || !points.length) {
        el.innerHTML = '<div style="color:#888;padding:12px;">Подій не знайдено</div>';
        return;
      }
      el.innerHTML = points.slice(0, 20).map(ev => {
        let iconUrl = ICONS[ev.threat_type] || ICONS.default;
        if (ev.marker_icon) {
          if (ev.marker_icon.startsWith('http') || ev.marker_icon.startsWith('/')) {
            iconUrl = ev.marker_icon;
          } else {
            iconUrl = '/static/' + ev.marker_icon;
          }
        }
        if (isFPVThreat(ev.place, ev.text, ev.threat_type)) {
          iconUrl = ICONS.fpv || iconUrl;
        }
  const isCancel = ev.threat_type === 'alarm_cancel';
  const placeLine = (ev.place && !isCancel) ? `<b>${translatePlace(ev.place)}</b><br>` : '';
  return `<div class='event'><img class='event-icon' src='${iconUrl}' alt='${ev.threat_type || ''}'><div class='event-info'>${placeLine}${cleanMessage(ev.text||'')}<div class='event-time'>${ev.date || ''}</div></div></div>`;
      }).join('');
    }
    async function initMap() {
      map = L.map('map', { zoomControl:false, attributionControl:false }).setView([48.3794,31.1656], 6);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        tileSize: 256,
        crossOrigin:true,
        attribution:''
      }).addTo(map);
      // --- Place search wiring ---
      const psWrap = document.getElementById('placeSearch');
      const psInput = document.getElementById('placeSearchInput');
      const psBtn = document.getElementById('placeSearchBtn');
      const psSuggest = document.getElementById('placeSearchSuggest');
      let psHistory = JSON.parse(localStorage.getItem('ps_history')||'[]');
      let psActiveIndex = -1; // keyboard navigation index
      const psCache = {}; // prefix -> matches cache
      function debounce(fn, ms){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; }
      function persistHistory(){ localStorage.setItem('ps_history', JSON.stringify(psHistory.slice(0,25))); }
      function showSuggest(list){
        if(!psSuggest) return;
        if(!list || !list.length){ psSuggest.innerHTML = '<div class="ps-empty">Немає варіантів</div>'; psSuggest.style.display='block'; return; }
        psSuggest.innerHTML = list.map((n,i)=>`<div class='ps-item${i===psActiveIndex?' active':''}' data-name='${n}'>${n}<span style='opacity:.45;'>⌖</span></div>`).join('');
        psSuggest.style.display='block';
      }
      function hideSuggest(){ if(psSuggest) psSuggest.style.display='none'; }
      function addHistory(name){ name = name.trim(); if(!name) return; psHistory = [name, ...psHistory.filter(n=>n!==name)]; persistHistory(); }
      function highlightNext(delta){
        if(!psSuggest || psSuggest.style.display!=='block') return;
        const items = [...psSuggest.querySelectorAll('.ps-item')];
        if(!items.length) return;
        psActiveIndex = (psActiveIndex + delta + items.length) % items.length;
        items.forEach((el,i)=> el.classList.toggle('active', i===psActiveIndex));
      }
      async function locate(query){
        if(!query) return;
        psWrap?.classList.add('loading');
        try {
          const r = await fetch(`/locate?q=${encodeURIComponent(query)}`);
          const j = await r.json();
          if(j.status==='ok'){
            addHistory(j.name);
            map.setView([j.lat,j.lng], Math.max(map.getZoom(), 9), { animate:true });
            // flash circle
            const circle = L.circle([j.lat,j.lng], { radius: 9000, color:'#3b82f6', weight:2, fillColor:'#2563eb', fillOpacity:0.15 });
            circle.addTo(map);
            setTimeout(()=>{ circle.setStyle({opacity:0, fillOpacity:0}); setTimeout(()=>{ try{map.removeLayer(circle);}catch(e){} }, 650); }, 1600);
          } else if(j.status==='suggest' && Array.isArray(j.matches)) {
            showSuggest(j.matches.map(n=> n));
          } else {
            // show not found suggestion with history fallback
            showSuggest(psHistory.slice(0,6));
          }
        } catch(e){ showSuggest(psHistory.slice(0,6)); }
        finally { psWrap?.classList.remove('loading'); }
      }
      async function fetchBackendSuggest(prefix){
        const p = prefix.toLowerCase();
        if(psCache[p]) return psCache[p];
        try {
          const r = await fetch(`/locate?q=${encodeURIComponent(p)}`);
          const j = await r.json();
          if(j.status==='suggest'){
            psCache[p] = j.matches || [];
            return psCache[p];
          }
        } catch(e){}
        psCache[p] = [];
        return [];
      }
      if(psBtn){ psBtn.addEventListener('click', ()=> locate(psInput.value.trim())); }
      if(psInput){
        psInput.addEventListener('keydown', e=>{
          if(e.key==='ArrowDown'){ highlightNext(1); e.preventDefault(); }
          else if(e.key==='ArrowUp'){ highlightNext(-1); e.preventDefault(); }
          else if(e.key==='Enter'){
            e.preventDefault();
            const active = psSuggest && psSuggest.querySelector('.ps-item.active');
            if(active){ const name = active.getAttribute('data-name'); psInput.value = name; hideSuggest(); locate(name); }
            else { locate(psInput.value.trim()); hideSuggest(); }
          } else if(e.key==='Escape'){ hideSuggest(); }
        });
        psInput.addEventListener('input', debounce(async ()=>{
          const vRaw = psInput.value.trim();
          const v = vRaw.toLowerCase();
          psActiveIndex = -1;
          if(!v){ hideSuggest(); return; }
          // Local fuzzy from markers + history
          const set = new Set();
          for(const m of (window.__lastPoints||[])){
            const place = (m.place||'').trim(); if(!place) continue; const norm = place.toLowerCase();
            if(norm.includes(v)) set.add(place);
            if(set.size>=12) break;
          }
          psHistory.filter(h=>h.toLowerCase().includes(v)).forEach(h=> set.add(h));
          let list = [...set];
          // Backend suggestions (prefix) merge
          if(v.length>=2){
            const backend = await fetchBackendSuggest(v);
            for(const name of backend){ if(!list.includes(name)) list.push(name); if(list.length>=20) break; }
          }
          if(list.length){ showSuggest(list.slice(0,20)); } else hideSuggest();
        }, 180));
      }
      if(psSuggest){
        psSuggest.addEventListener('click', e=>{
          const div = e.target.closest('.ps-item'); if(!div) return; const name = div.getAttribute('data-name');
          psInput.value = name; hideSuggest(); locate(name);
        });
      }
      document.addEventListener('click', e=>{ if(!psWrap.contains(e.target)) hideSuggest(); });
      // --- Darken all non-Ukraine territory (dynamic mask loading precise border if available) ---
      let worldMaskLayer = null;
      async function initWorldMask(){
        const worldRing = [ [85,-180],[85,180],[-85,180],[-85,-180] ];
        // Fallback simplified Ukraine ring (used until precise GeoJSON loads)
        const fallbackRing = [
          [52.37,23.60],[51.90,23.60],[51.90,24.00],[51.50,24.50],[51.90,25.30],
          [51.90,26.00],[51.60,26.60],[51.50,27.50],[51.60,28.20],[51.30,29.20],
          [51.60,30.60],[52.30,31.80],[52.10,32.70],[52.40,34.40],[52.30,35.90],
          [52.00,37.40],[51.20,38.20],[50.30,39.70],[49.10,40.10],[48.30,39.70],
          [47.10,38.50],[46.00,38.20],[45.35,37.40],[45.40,36.60],[45.20,34.90],
          [45.35,33.30],[46.07,30.95],[46.58,30.06],[47.80,29.48],[48.37,28.05],
          [48.47,27.53],[48.27,26.86],[47.74,26.63],[47.85,24.96],[48.15,23.53],
          [48.62,22.57],[49.90,22.09],[51.94,22.93],[52.37,23.60]
        ];
        function drawMask(rings){
          if(worldMaskLayer){ worldMaskLayer.remove(); worldMaskLayer=null; }
            worldMaskLayer = L.polygon([worldRing, ...rings], {
              stroke:false,
              fill:true,
              fillColor:'#0f172a',
              fillOpacity:0.70,
              interactive:false,
              className:'world-mask'
            }).addTo(map);
            const el = worldMaskLayer.getElement();
            if(el){ el.style.pointerEvents='none'; el.style.mixBlendMode='multiply'; }
        }
        // Initial quick mask
        drawMask([fallbackRing]);
        // Try precise GeoJSON (place file at /static/ukraine_border.geojson)
        try {
          const resp = await fetch('/static/geoBoundaries-UKR-ADM0_simplified.geojson');
          if(resp.ok){
            const gj = await resp.json();
            // Expect first feature Polygon or MultiPolygon in lon/lat
            const feats = (gj.features||[]);
            if(feats.length){
              const geom = feats[0].geometry;
              let rings=[];
              if(geom.type==='Polygon'){
                rings = geom.coordinates.map(r=> r.map(([lng,lat])=>[lat,lng]));
              } else if(geom.type==='MultiPolygon'){
                // Merge outer boundaries; treat each outer ring as separate hole (rare) or pick largest
                const polys = geom.coordinates.map(poly=> poly[0]); // first ring of each polygon
                // Choose largest by number of points (likely mainland) and treat others as islands (append too)
                polys.sort((a,b)=>b.length-a.length);
                rings = polys.map(r=> r.map(([lng,lat])=>[lat,lng]));
              }
              if(rings.length){
                // Use only first ring as hole if performance needed; or all rings
                drawMask(rings.slice(0,3));
              }
            }
          }
        } catch(e){ console.warn('Precise border load failed, using fallback ring', e); }
      }
      initWorldMask();
      // ---- Presence (active users) ----
      const uid = localStorage.getItem('presence_id') || (self.crypto?.randomUUID ? crypto.randomUUID() : (Date.now()+""+Math.random()).replace(/\D/g,''));
      localStorage.setItem('presence_id', uid);
      async function pingPresence(){
        try {
          const r = await fetch('/presence', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id:uid})});
          const j = await r.json();
          if(j.status === 'blocked'){
            // Show overlay and stop further updates
            const ov = document.createElement('div');
            ov.style.cssText='position:fixed;inset:0;background:#0a0f1f;display:flex;align-items:center;justify-content:center;z-index:9999;font-family:Inter,sans-serif;color:#fff;padding:2rem;text-align:center;';
            ov.innerHTML='<div style="max-width:480px;">Ваш доступ тимчасово обмежено.</div>';
            document.body.appendChild(ov);
            return;
          }
          if(j.visitors !== undefined){
            const el = document.getElementById('liveUsers');
            if(el){ el.querySelector('strong').textContent = j.visitors; }
          }
        } catch(e){}
      }
      pingPresence();
  setInterval(pingPresence, 5000);

      // --- Интеграция с alerts.in.ua ---
      let airAlarmLayer = null;
      let ukrBorderLayer = null;
  let raionAlarmLayer = null;
      async function fetchAirAlarms(){
        try { const r = await fetch('https://alerts.com.ua/api/states'); const j = await r.json(); return j.regions || {}; } catch(e){ return {}; }
      }
      async function showAirAlarmsOnMap(){
        const regions = await fetchAirAlarms();
        const geoRes = await fetch('https://alerts.com.ua/static/geo/ukraine_regions.json');
        const geo = await geoRes.json();
        if (airAlarmLayer) { airAlarmLayer.remove(); }
        airAlarmLayer = L.geoJSON(geo, {
         
          style: feature => {
            let code = feature.properties.id || feature.properties.ISO_3166_2;
            if (code) code = code.toUpperCase();
            let alarm = false;
            if (code && regions[code]) alarm = regions[code].alert;
            if (!alarm && code && regions[code.toLowerCase()]) alarm = regions[code.toLowerCase()].alert;
            return {
              color: alarm ? '#d93025' : '#c9d0d6',
              weight: alarm ? 2 : 1,
              fillColor: alarm ? '#ffd54f' : '#f1f3f6',
              fillOpacity: alarm ? 0.5 : 0.15
            };
          }
        }).addTo(map);
        // Draw a clear national border outline (union of all regions)
        try {
          if (turf && geo && geo.features && geo.features.length){
            let unionGeom = null;
            for(const f of geo.features){
              unionGeom = unionGeom ? turf.union(unionGeom, f) : f;
            }
            if (ukrBorderLayer) { ukrBorderLayer.remove(); }
            if (unionGeom){
              // Outer glow effect: two strokes
              const outer = L.geoJSON(unionGeom, { style:{ color:'rgba(17,24,39,0.55)', weight:8, opacity:0.7, fill:false } });
              const inner = L.geoJSON(unionGeom, { style:{ color:'#111827', weight:3, opacity:0.95, fill:false } });
              ukrBorderLayer = L.layerGroup([outer, inner]).addTo(map);
              ukrBorderLayer.bringToFront();
            }
          }
        } catch(e){}
      }
      showAirAlarmsOnMap();
      setInterval(showAirAlarmsOnMap, 20000);

      // ---- Dynamic raion alarm overlay (district-level) ----
      async function fetchRaionAlarms(){
        try { const r = await fetch('/raion_alarms'); return (await r.json()).alarms || []; } catch(e){ return []; }
      }
      async function updateRaionAlarms(){
        const alarms = await fetchRaionAlarms();
        if (raionAlarmLayer){ raionAlarmLayer.remove(); raionAlarmLayer = null; }
        if(!alarms.length) return;
        // Build circle-ish polygons (approx) or simple circles since we lack exact raion geometry right now
        const feats = alarms.map(a=>({
          type:'Feature', properties:{ raion:a.raion, place:a.place, since:a.since },
          geometry:{ type:'Point', coordinates:[a.lng, a.lat] }
        }));
        raionAlarmLayer = L.layerGroup();
        feats.forEach(f=>{
          const lat = f.geometry.coordinates[1];
          const lng = f.geometry.coordinates[0];
          // Represent district area with a translucent red circle (radius ~20km) placeholder
            const circle = L.circle([lat,lng], { radius: 20000, color:'#b91c1c', weight:1, fillColor:'#dc2626', fillOpacity:0.2 });
            circle.addTo(raionAlarmLayer);
            circle.bindPopup(`<b>${f.properties.place}</b><br>Повітряна тривога (район)`);
            // Add animated hatch overlay using a custom divIcon centered
            const Hatch = L.Marker.extend({ options:{ } });
            const hatchSize = 20000; // we adapt via CSS scale after projection
            const hatch = L.marker([lat,lng], { interactive:false, icon: L.divIcon({className:'', html:`<div class='raion-alarm-anim' style='width:300px;height:300px;transform:translate(-50%,-50%);'></div>`}) });
            hatch.addTo(raionAlarmLayer);
            // Adjust size on zoom (approximate meters to pixels)
            function rescale(){
              const pCenter = map.latLngToLayerPoint([lat,lng]);
              const pEdge = map.latLngToLayerPoint([lat + (20000/111320), lng]); // rough lat meter conversion
              const pxRadius = Math.abs(pEdge.y - pCenter.y);
              const el = hatch.getElement()?.querySelector('.raion-alarm-anim');
              if(el){ const d = pxRadius*2; el.style.width=d+'px'; el.style.height=d+'px'; }
            }
            map.on('zoom', rescale); map.on('move', rescale);
            setTimeout(rescale,50);
        });
        raionAlarmLayer.addTo(map);
      }
      updateRaionAlarms();
      setInterval(updateRaionAlarms, 15000);

      await updateMarkers();
      try {
    const es = new EventSource('/stream');
    const uid2 = localStorage.getItem('presence_id');
    es.onmessage = ev => {
          try {
            const p = JSON.parse(ev.data);
      if (p.tracks && p.tracks.length) { updateMarkers(); }
      if (p.control && p.control.type === 'block' && p.control.id && uid2 && p.control.id === uid2) {
               // show block overlay instantly
               const ov = document.createElement('div');
               ov.style.cssText='position:fixed;inset:0;background:#0a0f1f;display:flex;align-items:center;justify-content:center;z-index:9999;font-family:Inter,sans-serif;color:#fff;padding:2rem;text-align:center;';
               ov.innerHTML='<div style="max-width:480px;">Ваш доступ тимчасово обмежено.</div>';
               document.body.appendChild(ov);
               try { es.close(); } catch(e){}
            }
          } catch(e){}
        };
      } catch(e) {}
      setInterval(updateMarkers, 10000);
      // --- Re-cluster / re-render markers on zoom (debounced) so fast-mode buckets follow zoom level ---
      (function(){
        let zoomRedrawTimer=null; let lastZoom=map.getZoom();
        function onZoomEnd(){
          const z = map.getZoom();
            if(z===lastZoom) return; // no change
            lastZoom = z;
            if(zoomRedrawTimer){ clearTimeout(zoomRedrawTimer); }
            zoomRedrawTimer = setTimeout(()=>{ try { updateMarkers(); } catch(e){} }, 180);
        }
        map.on('zoomend', onZoomEnd);
      })();
    }
  function openWarn(){const o=document.getElementById('warnModal'); if(o) o.style.display='flex';}
  function closeWarn(){const o=document.getElementById('warnModal'); if(o) o.style.display='none';}
  function ackWarn(){ closeWarn(); }
  function toggleMapExpand(){
    const body = document.body;
    const btn = document.getElementById('expandBtn');
    const icon = document.getElementById('expandIcon');
    const mapCard = document.querySelector('.map-card');
    const wasExpanded = body.classList.contains('map-expanded');
    if(wasExpanded){
      body.classList.remove('map-expanded');
      if(btn){ btn.title='Розгорнути карту'; btn.setAttribute('aria-label','Розгорнути карту'); }
      if(icon){ icon.textContent='fullscreen'; }
  if(mapCard){ mapCard.style.height=''; }
      // restore map size
  setTimeout(()=>{ if(map){ map.invalidateSize(); } },150);
    } else {
      body.classList.add('map-expanded');
      if(btn){ btn.title='Згорнути карту'; btn.setAttribute('aria-label','Згорнути карту'); }
      if(icon){ icon.textContent='fullscreen_exit'; }
      // Set explicit height for iOS Safari dynamic bars
      if(mapCard){ mapCard.style.height= window.innerHeight + 'px'; }
  setTimeout(()=>{ if(map){ map.invalidateSize(); map.setView([UKRAINE_CENTER.lat, UKRAINE_CENTER.lng]); } },200);
    }
  }
  // Adjust fullscreen height on orientation / resize for mobile
  window.addEventListener('orientationchange', ()=>{ if(document.body.classList.contains('map-expanded')){ const mapCard=document.querySelector('.map-card'); if(mapCard){ mapCard.style.height=window.innerHeight+'px'; if(map){ map.invalidateSize(); } } } });
  window.addEventListener('resize', ()=>{ if(document.body.classList.contains('map-expanded')){ const mapCard=document.querySelector('.map-card'); if(mapCard){ mapCard.style.height=window.innerHeight+'px'; if(map){ map.invalidateSize(); } } } });
  window.onload = () => { 
    // Start optimized icon preloading
    preloadCriticalIcons(); 
    
    // Initialize map
    initMap(); 
    
    // Show disclaimer
    openWarn(); 
    
    // Start background preloading after initial load
    setTimeout(() => {
      preloadRemainingIcons();
    }, 2000); // Wait 2 seconds to avoid interfering with initial page load
  };
    // Smart Mass Attack Banner Logic (wrapped inside same script tag)
    (function(){
      const banner = document.getElementById('massAttackBanner');
      const closeBtn = document.getElementById('maClose');
      const textEl = document.getElementById('maDynamicText');
      const heurEl = document.getElementById('maHeuristics');
      if(!banner) return;

      const LS_KEY = 'maBannerDismissedAt';
      const DISMISS_COOLDOWN_MIN = 90; // minutes user dismissal persists
      const MAX_AGE_MIN = 180; // hide banner if last triggering event older

      function minutesAgo(ts){
        return (Date.now() - ts) / 60000;
      }

      function isDismissedRecent(){
        try{ const raw = localStorage.getItem(LS_KEY); if(!raw) return false; const t = parseInt(raw,10); return minutesAgo(t) < DISMISS_COOLDOWN_MIN; }catch(e){ return false; }
      }

      function markDismissed(){
        try{ localStorage.setItem(LS_KEY, Date.now().toString()); }catch(e){}
      }

      const heuristics = [];
      let freshestTrigger = 0;

      function qualifies(evt){
        if(!evt || !evt.type || !evt.text) return false;
        // Only consider missile / drone / pusk related events
        const t = (evt.type||'').toLowerCase();
        if(!(t.includes('shahed') || t.includes('raketa') || t.includes('pusk'))) return false;
        const tx = (evt.text||'').toLowerCase();
        // Heuristic keywords
        const kw = [ 'мас', 'комбінован', 'комбінован', 'хвиля', 'залп', 'велика кількість', 'велика к-сть', 'загальний старт', 'масштаб' ];
        if(kw.some(k=> tx.includes(k))){ heuristics.push('ключові слова'); return true; }
        // Multi-launch density: count punctuation separators and numbers
        const numLaunch = (tx.match(/(\b\d{1,3}\b\s*(пуск|злет|запуск))/g)||[]).length;
        if(numLaunch >= 3){ heuristics.push('число пусків ≥3'); return true; }
        return false;
      }

      function updateHeuristics(){
        heurEl.innerHTML='';
        [...new Set(heuristics)].forEach(h=>{
          const span = document.createElement('span'); span.textContent = h; heurEl.appendChild(span);
        });
        if(freshestTrigger){
          const age = Math.round(minutesAgo(freshestTrigger));
          const span = document.createElement('span'); span.textContent = 'оновлено ' + age + ' хв тому'; heurEl.appendChild(span);
        }
      }

      function showBanner(dynamicLine){
        if(isDismissedRecent()) return;
        if(dynamicLine){ textEl.textContent = dynamicLine; }
        updateHeuristics();
        banner.classList.remove('hidden');
      }

      closeBtn.addEventListener('click', ()=>{ banner.classList.add('hidden'); markDismissed(); });

      // Integrate with existing SSE stream of events if available
      function initSSE(){
        try {
          const es = new EventSource('/stream');
          es.onmessage = (e)=>{
            try{
              const data = JSON.parse(e.data);
              if(!data || !data.event) return;
              const evt = data.event;
              if(evt.timestamp){ freshestTrigger = Math.max(freshestTrigger, evt.timestamp*1000); }
              if(evt.timestamp && minutesAgo(evt.timestamp*1000) > MAX_AGE_MIN) return; // too old
              if(qualifies(evt)){
                const line = (evt.text||'').split('\n').find(l=>/(мас|комбінован|масов|велика кількість|хвиля|залп)/i.test(l)) || textEl.textContent;
                freshestTrigger = Date.now();
                showBanner(line);
              }
            }catch(err){ /* ignore */ }
          };
        }catch(e){ /* SSE not essential */ }
      }

      // On load also scan existing DOM list items (historical) for triggers
      function scanInitial(){
        const items = document.querySelectorAll('#eventList .event-info');
        let foundLine = null;
        items.forEach(li=>{
          const txt = li.textContent||'';
          if(/(мас|комбінован|масов|велика кількість|хвиля|залп)/i.test(txt)){
            heuristics.push('ключові слова');
            if(!foundLine) foundLine = txt.trim().slice(0,220);
          }
        });
        if(foundLine){ freshestTrigger = Date.now(); showBanner(foundLine); }
      }

      function evaluateDataset(ds){
        if(!ds) return;
        const events = ds.events||[];
        for(const ev of events){
          const t = (ev.text||'');
            if(/(мас|комбінован|масов|велика кількість|хвиля|залп)/i.test(t)){
              heuristics.push('ключові слова');
              freshestTrigger = Date.now();
              return showBanner(t.split('\n')[0].slice(0,220));
            }
        }
        const tracks = ds.tracks||[];
        const missiles = tracks.filter(x=>/(raketa|pusk)/i.test(x.threat_type||'')) .length;
        const drones = tracks.filter(x=>/(shahed|fpv)/i.test(x.threat_type||'')) .length;
        // If both missile and drone counts exceed thresholds, treat as combo risk
        if(missiles >= 3 && drones >= 5){
          heuristics.push('комбіновано (рахунок)');
          freshestTrigger = Date.now();
          showBanner(`Ознаки комбінованої активності: ракети ~${missiles}, БПЛА ~${drones}`);
        }
      }

      document.addEventListener('markersUpdated', e=>{
        if(isDismissedRecent()) return;
        evaluateDataset(e.detail);
      });

      if(!isDismissedRecent()){
        scanInitial();
        initSSE();
      }
    })();
