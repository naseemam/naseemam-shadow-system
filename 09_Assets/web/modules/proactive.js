(()=>{
  'use strict';

  const style=document.createElement('style');
  style.textContent=`
    .ameer-proactive-fab{position:fixed;left:18px;bottom:24px;z-index:80;border:0;border-radius:999px;background:#101828;color:#fff;padding:11px 15px;font:800 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,Arial,sans-serif;box-shadow:0 12px 32px rgba(15,23,42,.25);display:flex;align-items:center;gap:8px}
    .ameer-proactive-count{min-width:22px;height:22px;padding:0 6px;border-radius:999px;background:#2864dc;display:inline-flex;align-items:center;justify-content:center;font-size:11px}
    .ameer-proactive-panel{position:fixed;left:14px;right:14px;bottom:80px;z-index:79;max-width:720px;margin:auto;background:#fff;border:1px solid #e4e7ec;border-radius:22px;box-shadow:0 24px 70px rgba(15,23,42,.24);padding:14px;max-height:62vh;overflow:auto;display:none;direction:rtl;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,Arial,sans-serif}
    .ameer-proactive-panel.open{display:block}.ameer-proactive-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.ameer-proactive-head strong{font-size:17px}.ameer-proactive-close{border:1px solid #e4e7ec;background:#fff;border-radius:10px;padding:6px 10px}.ameer-event{border:1px solid #e4e7ec;border-radius:15px;padding:12px;margin:8px 0;background:#fff}.ameer-event.success{border-right:4px solid #178a55}.ameer-event.warning,.ameer-event.attention{border-right:4px solid #b76e00}.ameer-event.error{border-right:4px solid #c73838}.ameer-event-title{font-weight:900}.ameer-event-summary{font-size:13px;color:#667085;line-height:1.7;margin-top:4px}.ameer-event-time{font-size:10px;color:#98a2b3;margin-top:6px;direction:ltr}.ameer-proactive-toast{position:fixed;top:18px;left:18px;right:18px;z-index:100;max-width:640px;margin:auto;background:#101828;color:#fff;border-radius:16px;padding:13px 15px;box-shadow:0 18px 48px rgba(15,23,42,.28);direction:rtl;font:700 13px -apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,Arial,sans-serif;opacity:0;transform:translateY(-12px);pointer-events:none;transition:.22s}.ameer-proactive-toast.show{opacity:1;transform:translateY(0)}
  `;
  document.head.appendChild(style);

  const fab=document.createElement('button');
  fab.className='ameer-proactive-fab';
  fab.innerHTML='<span>🔔 مبادرات أمير</span><span class="ameer-proactive-count">0</span>';
  const count=fab.querySelector('.ameer-proactive-count');

  const panel=document.createElement('section');
  panel.className='ameer-proactive-panel';
  panel.innerHTML='<div class="ameer-proactive-head"><strong>مستجدات أمير</strong><button class="ameer-proactive-close">إغلاق</button></div><div class="ameer-proactive-list">جارٍ تحميل الأحداث…</div>';
  const list=panel.querySelector('.ameer-proactive-list');

  const toast=document.createElement('div');
  toast.className='ameer-proactive-toast';
  document.body.append(panel,fab,toast);

  let lastNewest='';
  let currentEvents=[];

  const esc=(value)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const when=(value)=>{try{return new Date(value).toLocaleString('ar-SA',{dateStyle:'short',timeStyle:'short'})}catch(_){return value||''}};

  function render(events){
    currentEvents=events||[];
    if(!currentEvents.length){list.innerHTML='<div style="padding:24px;text-align:center;color:#667085">لا توجد مستجدات بعد.</div>';return;}
    list.innerHTML=currentEvents.map(ev=>`<article class="ameer-event ${esc(ev.severity||'info')}"><div class="ameer-event-title">${esc(ev.title||'مستجد')}</div><div class="ameer-event-summary">${esc(ev.summary||'')}</div><div class="ameer-event-time">${esc(when(ev.at))}</div></article>`).join('');
  }

  function showToast(ev){
    if(!ev)return;
    toast.textContent=`أمير: ${ev.title||'مستجد'} — ${ev.summary||''}`;
    toast.classList.add('show');
    setTimeout(()=>toast.classList.remove('show'),6500);
  }

  async function refresh(){
    try{
      const r=await fetch('/ui/proactive',{cache:'no-store'});
      if(!r.ok)return;
      const data=await r.json();
      const events=data.events||[];
      count.textContent=String(data.unread_count||0);
      count.style.display=(data.unread_count||0)>0?'inline-flex':'none';
      render(events);
      const newest=events[0];
      if(newest&&lastNewest&&newest.at!==lastNewest)showToast(newest);
      if(newest)lastNewest=newest.at;
    }catch(_){/* visible console remains usable if polling is temporarily unavailable */}
  }

  async function markSeen(){
    const newest=currentEvents[0];
    try{
      await fetch('/ui/proactive/seen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({at:newest?.at||new Date().toISOString()})});
      count.textContent='0';count.style.display='none';
    }catch(_){}
  }

  fab.addEventListener('click',async()=>{panel.classList.toggle('open');if(panel.classList.contains('open'))await markSeen();});
  panel.querySelector('.ameer-proactive-close').addEventListener('click',()=>panel.classList.remove('open'));

  refresh();
  setInterval(refresh,10000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
})();
