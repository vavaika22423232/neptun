// Detect ?embed=1 and ?theme=light|dark before body paint
(function(){try{var q=new URLSearchParams(window.location.search);if(q.get('embed')==='1'){document.documentElement.classList.add('embed-mode');if(q.get('theme')==='light'){document.documentElement.classList.add('theme-light')}}}catch(e){}})();
