"use strict";
(() => {
 const $=selector=>document.querySelector(selector),photos=window.CrumbleStudy;
 const keys=Object.keys(photos),query=new URLSearchParams(location.search).get('photo');
 let selected=Object.hasOwn(photos,query)?query:'stripe';
 const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!=null)el.textContent=text;if(cls)el.className=cls;return el;};
 const record=$('#style-record');
 function selectRecord(key,scroll=false){
  selected=key;const photo=photos[key];record.hidden=false;
  const im=$('#record-image');im.src='assets/collection/'+photo.image;im.alt=photo.alt;im.width=photo.width;im.height=photo.height;
  $('#record-title').textContent=photo.name;$('#record-description').textContent=photo.details;
  const fields=$('#record-fields');fields.replaceChildren();
  const values=[['Source brand',photo.creator],['Category',photo.observed.category],['Photo view',photo.view],['Source photo ID',photo.photo_id],['Photo published',photo.published],['Image rights','Unsplash License']];
  for(const [label,value] of values){const row=node('div');row.append(node('dt',label),node('dd',value));fields.append(row);}
  $('#record-source').href=photo.source;
  document.querySelectorAll('[data-record]').forEach(button=>{const active=button.dataset.record===key;button.classList.toggle('selected',active);button.setAttribute('aria-pressed',String(active));});
  const url=new URL(location.href);url.searchParams.set('photo',key);history.replaceState(null,'',url);
  if(scroll)record.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});
 }
 function render(){
  const term=$('#sample-search').value.trim().toLowerCase(),category=$('#sample-category').value;
  const visible=keys.filter(key=>{const p=photos[key];return(!category||p.observed.category===category)&&(!term||[p.name,p.creator,p.details].join(' ').toLowerCase().includes(term));});
  const grid=$('#archive-grid');grid.replaceChildren();
  visible.forEach(key=>{const p=photos[key],button=node('button',null,'look-card'),frame=node('span',null,'look-image'),im=document.createElement('img');button.type='button';button.dataset.record=key;button.setAttribute('aria-label','Open '+p.name);im.src='assets/collection/'+p.image;im.width=p.width;im.height=p.height;im.alt=p.alt;im.loading='lazy';const hint=node('span','View','look-inspect');hint.setAttribute('aria-hidden','true');frame.append(im,hint);button.append(frame,node('span',p.name,'look-title'),node('span',p.creator+' / '+p.view,'look-description'));button.addEventListener('click',()=>selectRecord(key,true));grid.append(button);});
  $('#archive-count').textContent=visible.length+' sample record'+(visible.length===1?'':'s')+'. Filtered by metadata; no similarity model runs on this page.';
  $('#archive-empty').hidden=visible.length>0;record.hidden=!visible.length;
  if(visible.length)selectRecord(visible.includes(selected)?selected:visible[0]);
 }
 $('#sample-search').addEventListener('input',render);$('#sample-category').addEventListener('change',render);
 const dialog=document.createElement('dialog');dialog.className='photo-viewer';dialog.setAttribute('aria-label','Full garment photograph');const close=node('button','Close');close.type='button';close.setAttribute('aria-label','Close garment photo');const full=document.createElement('img');full.src='assets/collection/'+photos[selected].image;full.alt=photos[selected].alt;dialog.append(close,full);document.body.append(dialog);close.addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
 $('#record-zoom').addEventListener('click',()=>{full.src=$('#record-image').src;full.alt=$('#record-image').alt;dialog.showModal();});
 render();
})();
