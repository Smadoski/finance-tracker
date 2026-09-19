'use strict';
(() => {
  const form=document.getElementById('json-review-form');
  if(!form || !window.fetch || !window.URL || !window.File) return;
  const generate=document.getElementById('json-generate'), status=document.getElementById('json-status'), actions=document.getElementById('json-actions'), download=document.getElementById('json-download'), share=document.getElementById('json-share');
  let controller=null, file=null, blobURL=null, generation=0;
  function busy(value){generate.disabled=value;form.setAttribute('aria-busy',String(value));}
  function cleanupFile(){if(blobURL)URL.revokeObjectURL(blobURL);blobURL=null;file=null;actions.hidden=true;download.removeAttribute('href');}
  form.addEventListener('submit',async event=>{
    event.preventDefault();const current=++generation;
    if(controller)controller.abort();cleanupFile();controller=new AbortController();const requestController=controller;
    busy(true);status.textContent='Preparing JSON…';
    const timeout=setTimeout(()=>requestController.abort(),30000);
    try{
      const url=new URL(form.action,location.href);url.search=new URLSearchParams(new FormData(form)).toString();
      const response=await fetch(url,{credentials:'same-origin',signal:requestController.signal,headers:{Accept:'application/json'}});
      if(!response.ok || !(response.headers.get('content-type')||'').includes('application/json'))throw new Error('Export unavailable. Check your session and try again.');
      const text=await response.text();JSON.parse(text);
      if(current!==generation)return;
      file=new File([text],'financial-review.json',{type:'application/json'});blobURL=URL.createObjectURL(file);
      download.href=blobURL;actions.hidden=false;
      share.hidden=!(navigator.canShare&&navigator.share&&navigator.canShare({files:[file]}));
      status.textContent='JSON ready. Save a copy or share it. You can continue navigating normally.';
    }catch(error){if(current===generation)status.textContent=error.name==='AbortError'?'Export cancelled or timed out. You can try again.':error.message;}
    finally{clearTimeout(timeout);if(current===generation){controller=null;busy(false);}}
  });
  share.addEventListener('click',async()=>{
    if(!file)return;
    const current=generation;
    // Native share must start directly from this user gesture, after generation has finished.
    try{await navigator.share({files:[file],title:'Financial Review'});if(current===generation)status.textContent='Share completed. You can continue navigating.';}
    catch(error){if(current===generation)status.textContent=error.name==='AbortError'?'Share cancelled. Your JSON is still ready.':'Sharing unavailable. Use Save JSON instead.';}
    finally{if(current===generation){busy(false);share.disabled=false;}}
  });
  download.addEventListener('click',()=>{busy(false);status.textContent='Save opened. This page remains available for navigation.';});
  window.addEventListener('pagehide',()=>{generation++;if(controller)controller.abort();controller=null;busy(false);cleanupFile();});
  window.addEventListener('pageshow',event=>{busy(false);share.disabled=false;if(event.persisted){status.textContent='Generate a new JSON file when ready.';}});
})();
