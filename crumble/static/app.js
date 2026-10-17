import {$, el, state, api, json, run, show, card, select, message, image} from "./ui.js";
import {openProduct, openComparison, bindReview} from "./detail.js";
import {bindPhoto, showResults} from "./photo.js";
async function status(){
  state.status=await api("/api/status");const s=state.status,stats=$("#stats");stats.replaceChildren();
  for(const [key,label] of [["products","garments"],["assets","images"],["reviews","reviews"]]){
    const n=el("div");n.append(el("b",s[key].toLocaleString()),el("span",label));stats.append(n);
  }
  $("#model-note").textContent=s.encoder.provider==="demo"?"DEMO MODE / Original sample drawings and simple image descriptors. No real-fashion accuracy claim.":"FASHION MODEL / Versioned embeddings. All design and SMV suggestions need review.";
  if(!s.index)$("#model-note").textContent+=" Index is not ready.";
  const lib=$("#library-info");lib.replaceChildren(el("p",s.smv_library.version),el("p",s.smv_library.scope,"muted"));
  if(s.smv_library.illustrative)lib.append(el("p","Illustrative values only.","warning"));
}
async function catalogue(){
  const data=await api("/api/products?q="+encodeURIComponent($("#filter").value)+"&category="+encodeURIComponent($("#category").value)+"&offset="+(state.page*24)+"&limit=24");
  const grid=$("#catalogue-grid");grid.replaceChildren();
  data.items.forEach(p=>grid.append(card(p)));
  if(!data.items.length)grid.append(el("p","No garments yet. Add your own or run the demo command."));
  $("#page-label").textContent=data.total+" garments / page "+(state.page+1);
  $("#previous").disabled=state.page===0;$("#next").disabled=(state.page+1)*24>=data.total;
}
async function queue(){
  const data=await api("/api/queue");const list=$("#queue-list");list.replaceChildren();
  if(!data.items.length)list.append(el("p","No pending pairs. Run crumble queue to propose candidates, or select two garments from the collection."));
  for(const pair of data.items){
    const n=el("div",null,"queue-item");
    n.append(image(pair.a.images[0],pair.a.title),image(pair.b.images[0],pair.b.title),el("p",pair.a.title+" ? "+pair.b.title));
    const b=el("button","Review pair");b.onclick=run(()=>openComparison(pair.a.id,pair.b.id));n.append(b);list.append(n);
  }
}
async function start(){
  await status();$("#login").hidden=true;$("#application").hidden=false;await catalogue();show("catalogue");
}
document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=run(async()=>{show(b.dataset.tab);if(b.dataset.tab==="queue")await queue();if(b.dataset.tab==="workspace")await status();}));
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$("#"+b.dataset.close).close());
document.addEventListener("open-product",run(e=>openProduct(e.detail)));
document.addEventListener("select-product",e=>select(e.detail));
document.addEventListener("find-similar",run(async e=>{show("search");showResults(await api("/api/products/"+encodeURIComponent(e.detail.id)+"/similar"));}));
$("#compare-selected").onclick=run(()=>openComparison(state.selected[0].id,state.selected[1].id));
$("#clear-selection").onclick=()=>{state.selected=[];$("#selection").hidden=true;};
$("#compare-close").onclick=()=>{show("catalogue");};
$("#queue-refresh").onclick=run(queue);
$("#filter-form").onsubmit=run(async()=>{state.page=0;await catalogue();});
$("#previous").onclick=run(async()=>{state.page--;await catalogue();});
$("#next").onclick=run(async()=>{state.page++;await catalogue();});
$("#add-open").onclick=()=>$("#add-dialog").showModal();
$("#add-form").onsubmit=run(async e=>{
  const data=new FormData(e.target),metadata={};
  for(const key of ["id","title","brand","category","rights"])metadata[key]=data.get(key);
  const body=new FormData();body.append("metadata",JSON.stringify(metadata));
  for(const file of data.getAll("files"))body.append("files",file);
  await api("/api/ingest",{method:"POST",body});$("#add-dialog").close();e.target.reset();
  message("Garment stored. Its images are queued for the embedding worker.");await start();
});
$("#login-form").onsubmit=run(async()=>{await api("/api/session",json("POST",{token:$("#token").value}));$("#token").value="";message("");await start();});
$("#logout").onclick=run(async()=>{await api("/api/session",{method:"DELETE"});location.reload();});
bindReview();bindPhoto();run(start)();

