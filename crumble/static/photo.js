import {$, api, run, card, message} from "./ui.js";
export function bindPhoto(){
  let bitmap=null, start=null;
  const canvas=$("#crop"), ctx=canvas.getContext("2d");
  const fields=["x1","y1","x2","y2"].map(x=>$("#crop-"+x));
  function bounds(){return fields.map(x=>Number(x.value)/100);}
  function draw(){
    if(!bitmap)return;
    ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
    const [x1,y1,x2,y2]=bounds();ctx.strokeStyle="#14694c";ctx.lineWidth=3;
    ctx.strokeRect(x1*canvas.width,y1*canvas.height,(x2-x1)*canvas.width,(y2-y1)*canvas.height);
  }
  async function load(file){
    if(!file)return;
    if(file.size>20*1024*1024)throw new Error("Choose an image below 20 MB.");
    const next=await createImageBitmap(file);
    if(next.width*next.height>20_000_000){next.close();throw new Error("Choose an image below 20 megapixels.");}
    bitmap?.close();bitmap=next;
    canvas.width=Math.round(700*Math.min(1,bitmap.width/bitmap.height));
    canvas.height=Math.round(700*Math.min(1,bitmap.height/bitmap.width));
    canvas.hidden=false;$("#crop-controls").hidden=false;$("#search-photo").disabled=false;
    [0,0,100,100].forEach((v,i)=>fields[i].value=v);draw();
  }
  $("#photo").onchange=run(e=>load(e.target.files[0]));
  $("#drop").ondragover=e=>e.preventDefault();
  $("#drop").ondrop=run(e=>load(e.dataTransfer.files[0]));
  $("#drop").onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();$("#photo").click();}};
  document.addEventListener("paste",run(async e=>{
    if($("#search").hidden || ["INPUT","TEXTAREA"].includes(document.activeElement.tagName))return;
    const item=[...e.clipboardData.items].find(x=>x.type.startsWith("image/"));if(item)await load(item.getAsFile());
  }));
  function point(e){const r=canvas.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];}
  canvas.onpointerdown=e=>{start=point(e);canvas.setPointerCapture(e.pointerId);};
  canvas.onpointerup=e=>{
    if(!start)return;const end=point(e);
    if(Math.abs(end[0]-start[0])>.01&&Math.abs(end[1]-start[1])>.01){
      [Math.min(start[0],end[0]),Math.min(start[1],end[1]),Math.max(start[0],end[0]),Math.max(start[1],end[1])].forEach((v,i)=>fields[i].value=Math.round(v*100));
    }
    start=null;draw();
  };
  fields.forEach(x=>x.oninput=draw);
  $("#search-photo").onclick=run(async()=>{
    const [x1,y1,x2,y2]=bounds();
    if(!bitmap || ![x1,y1,x2,y2].every(Number.isFinite)||x1<0||y1<0||x2>1||y2>1||x2<=x1||y2<=y1)throw new Error("Choose a valid crop rectangle.");
    const temp=document.createElement("canvas"),w=(x2-x1)*bitmap.width,h=(y2-y1)*bitmap.height;
    temp.width=Math.max(1,Math.round(w));temp.height=Math.max(1,Math.round(h));
    temp.getContext("2d").drawImage(bitmap,x1*bitmap.width,y1*bitmap.height,w,h,0,0,temp.width,temp.height);
    const blob=await new Promise(resolve=>temp.toBlob(resolve,"image/jpeg",.95)),data=new FormData();
    data.append("file",blob,"query.jpg");data.append("category",$("#search-category").value);
    message("Searching the garment index?");
    showResults(await api("/api/search/photo",{method:"POST",body:data}));message("");
  });
  $("#text-search").onsubmit=run(async()=>{
    showResults(await api("/api/search/text?q="+encodeURIComponent($("#text-query").value)));
  });
}
export function showResults(data){
  const grid=$("#search-grid");grid.replaceChildren();
  data.items.forEach(r=>grid.append(card(r.product,r.score)));
  $("#search-caption").textContent=data.items.length+" matches / "+data.model.provider+" / similarity, not probability"+
    (data.filter_may_limit_results?" / Filters reduced the candidate pool.":"");
}

