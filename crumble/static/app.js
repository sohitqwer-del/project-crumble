import {$, el, state, api, json, run, show, card, select, message, image, empty, updateSelection} from "./ui.js";
import {openProduct, openComparison, bindReview} from "./detail.js";
import {bindPhoto, showResults} from "./photo.js";
async function status(){
  state.status=await api("/api/status");const s=state.status,stats=$("#stats");stats.replaceChildren();
  for(const [key,label] of [["products","garments"],["assets","images"],["reviews","reviews"]]){
    const n=el("div");n.append(el("b",s[key].toLocaleString()),el("span",label));stats.append(n);
  }
  $("#model-note").textContent=s.encoder.provider==="demo"?"DEMO MODE / Original sample drawings and simple image descriptors. No real-fashion accuracy claim.":"FASHION MODEL / Versioned embeddings. All design and SMV suggestions need review.";
  if(!s.index)$("#model-note").textContent+=" Index is not ready.";
  const readonly=Boolean(s.read_only);$("#workspace-mode").hidden=!readonly;$("#workspace-mode").textContent="PUBLIC DEMO · Explore the sample collection. Run your own workspace to import garments and save reviews.";
  $("#add-open").hidden=readonly;
  $("#review-form").querySelectorAll("input,select,textarea,button").forEach(n=>n.disabled=readonly);
  $("#review-form").setAttribute("aria-label",readonly?"Review form preview. Saving is available in your own workspace.":"Save your garment comparison review");
  $("#text-search").querySelector("button").disabled=s.capabilities?.text_search===false;
  $("#text-query").placeholder=s.capabilities?.text_search===false?"Description search needs the fashion encoder":"Square neck blue dress";
  const lib=$("#library-info");lib.replaceChildren(el("p",s.smv_library.version),el("p",s.smv_library.scope,"muted"));
  if(s.smv_library.illustrative)lib.append(el("p","Illustrative values only.","warning"));
}
let collectionRequest=0;
async function catalogue(){
  const request=++collectionRequest;$("#catalogue-grid").setAttribute("aria-busy","true");$("#collection-caption").textContent="Loading your collection…";
  const data=await api("/api/products?q="+encodeURIComponent($("#filter").value)+"&category="+encodeURIComponent($("#category").value)+"&offset="+(state.page*24)+"&limit=24");
  if(request!==collectionRequest)return;
  const grid=$("#catalogue-grid");grid.setAttribute("aria-busy","false");grid.replaceChildren();
  data.items.forEach(p=>grid.append(card(p)));
  if(!data.items.length)grid.append(empty($("#filter").value||$("#category").value?"No matching garments.":"Your collection starts here.",$("#filter").value||$("#category").value?"Try a different title, brand or category.":"Add garment images with permission to begin building your collection.","+"));
  $("#page-label").textContent="Page "+(state.page+1)+" of "+Math.max(1,Math.ceil(data.total/24));
  $("#collection-caption").textContent=data.total.toLocaleString()+" garment"+(data.total===1?"":"s")+" · "+(data.items.length?"Showing "+(state.page*24+1)+"–"+(state.page*24+data.items.length):"No results")+" · Brands shown are source metadata";
  $("#previous").disabled=state.page===0;$("#next").disabled=(state.page+1)*24>=data.total;
}
async function queue(){
  const data=await api("/api/queue");const list=$("#queue-list");list.replaceChildren();
  if(!data.items.length)list.append(empty("The queue is clear.","Select two garments in your collection to review a pair, or generate candidates with the workspace queue command.","✓"));
  for(const pair of data.items){
    const n=el("div",null,"queue-item");
    const title=el("p",pair.a.title+"  →  "+pair.b.title);title.append(el("small",(pair.a.brand||"Collection")+" / "+(pair.b.brand||"Collection")+" · Awaiting a human review"));n.append(image(pair.a.images[0],pair.a.title),image(pair.b.images[0],pair.b.title),title);
    const b=el("button","Review pair");b.onclick=run(()=>openComparison(pair.a.id,pair.b.id));n.append(b);list.append(n);
  }
}
async function start(){
  await status();$("#login").hidden=true;$("#application").hidden=false;await catalogue();show("catalogue");
}
document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=run(async()=>{show(b.dataset.tab);if(b.dataset.tab==="queue")await queue();if(b.dataset.tab==="workspace")await status();}));
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$("#"+b.dataset.close).close());
document.addEventListener("open-product",run(e=>openProduct(e.detail)));
document.addEventListener("workspace-changed",run(status));
document.addEventListener("select-product",e=>select(e.detail));
document.addEventListener("find-similar",run(async e=>{show("search");showResults(await api("/api/products/"+encodeURIComponent(e.detail.id)+"/similar"));}));
$("#compare-selected").onclick=run(()=>openComparison(state.selected[0].id,state.selected[1].id));
$("#clear-selection").onclick=()=>{state.selected=[];updateSelection();};
$("#compare-close").onclick=()=>{show("catalogue");};
$("#queue-refresh").onclick=run(queue);
$("#filter-form").onsubmit=run(async()=>{state.page=0;await catalogue();});
$("#previous").onclick=run(async()=>{state.page--;await catalogue();});
$("#next").onclick=run(async()=>{state.page++;await catalogue();});
$("#add-open").onclick=()=>$("#add-dialog").showModal();
$("#add-form").onsubmit=run(async e=>{
  const data=new FormData(e.target),metadata={};
  const files=data.getAll("files").filter(x=>x.size>0);if(!files.length||files.length>8)throw new Error("Choose between 1 and 8 garment images.");
  for(const key of ["id","title","brand","category","rights"])metadata[key]=data.get(key);
  const body=new FormData();body.append("metadata",JSON.stringify(metadata));
  for(const file of files)body.append("files",file);
  await api("/api/ingest",{method:"POST",body});$("#add-dialog").close();e.target.reset();
  message("Garment stored. Its images are queued for the embedding worker.");await start();
});
$("#login-form").onsubmit=run(async()=>{await api("/api/session",json("POST",{token:$("#token").value}));$("#token").value="";message("");await start();});
$("#logout").onclick=run(async()=>{await api("/api/session",{method:"DELETE"});location.reload();});
bindReview();bindPhoto();run(start)();

