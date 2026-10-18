"use strict";
(() => {
  const $=selector=>document.querySelector(selector);
  const key="project-crumble.browser-demo.v2";
  const library={version:"crumble-browser-demo-v1",illustrative:true,source:"Invented examples for the browser demonstration. Not production standards.",operations:[
    {id:"short-sleeve-hem",label:"Finish short-sleeve hem",low:.25,high:.35,machine:"Illustrative hem method",field:"sleeve_length"},
    {id:"long-sleeve-cuff",label:"Attach long-sleeve cuff",low:.8,high:1.1,machine:"Illustrative cuff method",field:"sleeve_length"},
    {id:"patch-pocket",label:"Attach patch pocket",low:.6,high:.9,machine:"Illustrative pocket method",field:"pockets"}
  ]};
  let reversed=false;
  const baseline={sleeve:"short",pockets:false};
  const signed=n=>(n>0?"+":"")+(Math.abs(n)<.00001?0:n).toFixed(2);
  const formatRange=(low,high)=>signed(low)+" to "+signed(high);
  const options=()=>({sleeve:document.querySelector('input[name="sleeve"]:checked').value,pockets:$("#pockets").checked});
  const sides=()=>reversed?[options(),baseline]:[baseline,options()];
  function element(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;}
  function garment(g,id){
    const name=g.sleeve==='long'?(g.pockets?'combined':'long'):(g.pockets?'pockets':'reference');
    const description='Ivory linen square-neck dress, '+(g.sleeve==='long'?'long sleeves with cuffs':'short sleeves')+(g.pockets?', two patch pockets':', no pockets');
    return '<div class="studio-product-photo"><button class="studio-photo-zoom" type="button" aria-label="View garment photo in detail"><img src="assets/collection/'+name+'.webp" width="560" height="700" alt="'+description+'"><span>View detail &#8599;</span></button></div>';
  }
  function compute(){
    const [a,b]=sides();
    const quantities=g=>[g.sleeve==="short"?2:0,g.sleeve==="long"?2:0,g.pockets?2:0];
    const before=quantities(a),after=quantities(b);
    const operations=library.operations.map((op,i)=>{const quantity_delta=after[i]-before[i];return{...op,quantity_before:before[i],quantity_after:after[i],quantity_delta,delta_low:quantity_delta>=0?quantity_delta*op.low:quantity_delta*op.high,delta_high:quantity_delta>=0?quantity_delta*op.high:quantity_delta*op.low};}).filter(op=>op.quantity_delta!==0);
    return{a,b,operations,low:operations.reduce((sum,op)=>sum+op.delta_low,0),high:operations.reduce((sum,op)=>sum+op.delta_high,0)};
  }
  function render(){
    const d=compute();
    $("#garment-a").innerHTML=garment(d.a,"a");$("#garment-b").innerHTML=garment(d.b,"b");
    $("#a-label").textContent=reversed?"CHANGED DESIGN":"REFERENCE";$("#b-label").textContent=reversed?"REFERENCE":"CHANGED DESIGN";
    const delta=$("#delta-value");delta.replaceChildren(document.createTextNode(signed(d.low)+"–"+signed(d.high)+" "),element("small","min"));
    $("#delta-summary").textContent=d.operations.length?d.operations.length+" mapped operation changes. Input-bound range; not a confidence interval.":"No mapped operation change. Other construction details remain unknown.";
    $("#table-total").textContent=formatRange(d.low,d.high);
    const rows=[["Neckline","Square","Square","Unchanged"],["Sleeves",d.a.sleeve==="long"?"Long + cuffs":"Short + hems",d.b.sleeve==="long"?"Long + cuffs":"Short + hems",d.a.sleeve===d.b.sleeve?"Unchanged":"Changed"],["Pockets",d.a.pockets?"Two patch pockets":"None",d.b.pockets?"Two patch pockets":"None",d.a.pockets===d.b.pockets?"Unchanged":"Changed"],["Lining","Unknown","Unknown","Needs evidence"]];
    const parts=$("#parts-table");parts.replaceChildren();
    rows.forEach(([label,a,b,status])=>{const row=element("tr");row.append(element("td",label),element("td",a),element("td",b));const td=element("td");td.append(element("span",status,"state "+(status==="Changed"?"changed":status==="Needs evidence"?"unknown":"")));row.append(td);parts.append(row);});
    const operations=$("#operations-table");operations.replaceChildren();
    d.operations.forEach(op=>{const row=element("tr"),label=element("td",op.label);label.append(element("small",op.low.toFixed(2)+"–"+op.high.toFixed(2)+" min each · invented example"));row.append(label,element("td",(op.quantity_delta>0?"+":"")+op.quantity_delta,"mono"),element("td",formatRange(op.delta_low,op.delta_high),"mono"));operations.append(row);});
    if(!d.operations.length){const row=element("tr"),td=element("td","No changed operations in this example library.");td.colSpan=3;row.append(td);operations.append(row);}
  }
  function draft(){const d=compute();return{schema:"crumble-browser-review/2",created_at:new Date().toISOString(),collection:"Crumble demo collection",illustrative:true,garments:{a:{...d.a,neckline:"square"},b:{...d.b,neckline:"square"}},controls:{...options(),reversed},review:{reviewer:$("#draft-reviewer").value.trim(),relationship:$("#draft-relation").value,smv_decision:$("#draft-decision").value,note:$("#draft-note").value.trim()},smv:{library,mapped_operations:d.operations,mapped_delta:{low:Number(d.low.toFixed(4)),high:Number(d.high.toFixed(4)),unit:"standard minutes"},unknown_fields:["lining","interfacing","seam_finish","fabric_weight"],unmapped_construction:["sleeve shaping and other construction work outside this illustrative library"],scope:"Mapped operation change only. No total garment SMV is calculated."},provenance:{garments:"Original AI-generated Project Crumble sample imagery",parts:"Explicit browser controls; no model inference",times:"Invented examples; not factory standards",storage:"Browser-local draft. No network submission."}};}
  const status=text=>$("#draft-status").textContent=text;
  $("#swap-comparison").addEventListener("click",()=>{reversed=!reversed;render();});
  document.querySelectorAll('input[name="sleeve"],#pockets').forEach(n=>n.addEventListener("change",()=>{render();status("Design updated. Save or export to keep this version of your review.");}));
  $("#draft-form").addEventListener("submit",e=>{e.preventDefault();try{localStorage.setItem(key,JSON.stringify(draft()));status("Draft saved on this browser. Nothing was sent to a server.");}catch{status("This browser cannot save a local draft. You can still download the JSON.");}});
  $("#export-draft").addEventListener("click",()=>{const data=draft();const blob=new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="crumble-demo-review.json";document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);status("Review JSON prepared for download. Demo assumptions and unknown fields are included.");});
  $("#load-draft").addEventListener("click",()=>{try{const saved=JSON.parse(localStorage.getItem(key)||"null");if(!saved){status("No saved draft in this browser yet.");return;}if(saved.schema!=="crumble-browser-review/2"||!saved.controls||!saved.review)throw new Error("Unknown draft format");const controls=saved.controls;const sleeve=controls.sleeve==="short"?"short":"long";document.querySelector('input[name="sleeve"][value="'+sleeve+'"]').checked=true;$("#pockets").checked=Boolean(controls.pockets);reversed=Boolean(controls.reversed);$("#draft-reviewer").value=String(saved.review.reviewer||"").slice(0,100);$("#draft-relation").value=saved.review.relationship;$("#draft-decision").value=saved.review.smv_decision;$("#draft-note").value=String(saved.review.note||"").slice(0,2000);render();status("Saved draft restored. Check the design and review before using it.");}catch{status("The saved draft could not be restored. Export a new review or clear the stored draft.");}});
  $("#clear-draft").addEventListener("click",()=>{try{localStorage.removeItem(key);status("Saved browser draft cleared. The current example is still on screen.");}catch{status("Browser storage is unavailable. No draft could be cleared.");}});
  $("#reset-demo").addEventListener("click",()=>{$("#draft-form").reset();document.querySelector('input[name="sleeve"][value="long"]').checked=true;$("#pockets").checked=true;reversed=false;render();status("Example reset. A saved browser draft, if any, is unchanged.");});
  const photoDialog=document.createElement("dialog");photoDialog.className="photo-viewer";
  const photoClose=document.createElement("button");photoClose.type="button";photoClose.textContent="Close ×";photoClose.setAttribute("aria-label","Close garment photo");
  const enlarged=document.createElement("img");enlarged.src="assets/collection/reference.webp";enlarged.alt="Garment detail";photoDialog.append(photoClose,enlarged);document.body.append(photoDialog);
  photoClose.addEventListener("click",()=>photoDialog.close());
  photoDialog.addEventListener("click",e=>{if(e.target===photoDialog)photoDialog.close()});
  document.querySelector(".garment-stage").addEventListener("click",e=>{
    const button=e.target.closest(".studio-photo-zoom");if(!button)return;
    const image=button.querySelector("img");enlarged.src=image.src;enlarged.alt=image.alt;photoDialog.showModal();
  });
  const variant=new URLSearchParams(location.search).get('variant');
  if(['reference','long','pockets','combined'].includes(variant)){
    document.querySelector('input[name="sleeve"][value="'+(['long','combined'].includes(variant)?'long':'short')+'"]').checked=true;
    document.querySelector('#pockets').checked=['pockets','combined'].includes(variant);
  }
  render();
})();
