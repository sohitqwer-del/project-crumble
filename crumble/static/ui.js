export const $ = q => document.querySelector(q);
export const state = {selected: [], comparison: null, page: 0, status: null, tab:"catalogue"};
export function el(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;}
export function message(text,kind="status"){$("#notice").textContent=text;$("#notice").dataset.kind=kind;}
export async function api(path,options={}){
  let res;try{res=await fetch(path,options);}catch{throw new Error("Connection lost. Check your network, then try again.");}
  if(res.status===401){$("#login").hidden=false;$("#application").hidden=true;throw new Error("Sign in to open this workspace.");}
  let data;try{data=await res.json();}catch{throw new Error("The workspace returned an unexpected response. Please try again.");}
  if(!res.ok)throw new Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail||"Request failed."));
  return data;
}
export function json(method,body){return{method,headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};}
export function run(fn){
  return async event=>{
    if(event?.preventDefault)event.preventDefault();
    const source=event?.currentTarget;
    const button=source?.tagName==="BUTTON"?source:source?.tagName==="FORM"?(event.submitter||source.querySelector('button[type=submit],button:not([type])')):null;
    if(button?.dataset.pending==="true")return;
    if(button){button.dataset.pending="true";button.setAttribute("aria-busy","true");}
    try{await fn(event);}catch(error){document.querySelectorAll('[aria-busy="true"]:not(button)').forEach(n=>n.setAttribute("aria-busy","false"));message(error.message||"Something went wrong. Please try again.","error");}
    finally{if(button){delete button.dataset.pending;button.removeAttribute("aria-busy");}}
  };
}
export function show(tab){
  state.tab=tab;$("#comparison").hidden=true;
  document.querySelectorAll(".tab").forEach(n=>n.hidden=n.id!==tab);
  document.querySelectorAll("nav button").forEach(n=>{n.classList.toggle("active",n.dataset.tab===tab);if(n.dataset.tab===tab)n.setAttribute("aria-current","page");else n.removeAttribute("aria-current");});
  if(tab==="catalogue")updateSelection();
}
export function image(aid,alt){
  const n=el("img");if(aid)n.src="/assets/"+encodeURIComponent(aid);
  n.alt=alt||"Garment image";n.loading="lazy";n.decoding="async";
  n.onerror=()=>{n.onerror=null;n.removeAttribute("src");n.alt="Image unavailable: "+(alt||"garment");};return n;
}
export function dispatch(name,detail){document.dispatchEvent(new CustomEvent(name,{detail}));}
export function empty(title,text,symbol="↗"){
  const n=el("div",null,"empty-state");n.append(el("span",symbol,"empty-symbol"),el("h3",title),el("p",text));return n;
}
export function card(p,score,controls=true){
  const n=el("article",null,"card");n.dataset.productId=p.id;
  n.append(image(p.images[0],p.title));
  const body=el("div",null,"card-body");
  body.append(el("p",p.brand||"Your collection","eyebrow"),el("h3",p.title));
  body.append(el("p",p.category||"Category not supplied","card-category"));
  if(score!=null)body.append(el("span","Similarity "+score.toFixed(3)+" · uncalibrated","score"));
  if(controls){
    const actions=el("div",null,"card-actions");
    for(const [label,name] of [["Details","open-product"],["Select to compare","select-product"],["Similar ↗","find-similar"]]){
      const b=el("button",label);b.type="button";
      if(name==="select-product"){b.dataset.selectId=p.id;b.setAttribute("aria-pressed",String(state.selected.some(x=>x.id===p.id)));}
      b.setAttribute("aria-label",label+": "+p.title);b.onclick=()=>dispatch(name,p);actions.append(b);
    }
    body.append(actions);
  }
  n.classList.toggle("selected",state.selected.some(x=>x.id===p.id));n.append(body);return n;
}
export function updateSelection(){
  $("#selection").hidden=!state.selected.length||!$("#comparison").hidden;
  $("#selection-label").textContent=state.selected.length===1?"1 of 2 selected · "+state.selected[0].title:state.selected.map(x=>x.title).join("  →  ");
  $("#compare-selected").disabled=state.selected.length!==2;
  document.querySelectorAll("[data-product-id]").forEach(n=>n.classList.toggle("selected",state.selected.some(p=>p.id===n.dataset.productId)));
  document.querySelectorAll("[data-select-id]").forEach(n=>{const selected=state.selected.some(p=>p.id===n.dataset.selectId);n.setAttribute("aria-pressed",String(selected));n.textContent=selected?"Selected ✓":"Select to compare";});
}
export function select(p){
  const old=state.selected.findIndex(x=>x.id===p.id);
  if(old>=0)state.selected.splice(old,1);
  else if(state.selected.length<2)state.selected.push(p);
  else{message("Two garments are selected. Deselect one to choose a different pair.");return;}
  updateSelection();
}

