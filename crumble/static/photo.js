import {$, api, run, card, message, empty} from "./ui.js";
let resultsSequence=0;
export function beginResults(){
  const request=++resultsSequence;
  $("#search-grid").replaceChildren();$("#search-grid").setAttribute("aria-busy","true");
  $("#search-caption").textContent="Finding the closest previous styles in your archive…";
  message("");
  return request;
}
export function failResults(error,request){
  if(request!==resultsSequence)return;
  $("#search-grid").setAttribute("aria-busy","false");
  $("#search-grid").replaceChildren(empty("Search could not finish.","Your archive has not changed. Try the search again."));
  $("#search-caption").textContent="Search failed. Please try again.";
  message(error?.message||"The search could not finish. Please try again.","error");
}
export function bindPhoto(){
  let bitmap=null, start=null, loadSequence=0;
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
    if(!["image/jpeg","image/png","image/webp"].includes(file.type))throw new Error("Choose a JPG, PNG or WebP image.");
    const sequence=++loadSequence;
    if(file.size>20*1024*1024)throw new Error("Choose an image below 20 MB.");
    let next;try{next=await createImageBitmap(file);}catch{throw new Error("This image could not be opened. Choose another JPG, PNG or WebP.");}
    if(sequence!==loadSequence){next.close();return;}
    if(next.width*next.height>20_000_000){next.close();throw new Error("Choose an image below 20 megapixels.");}
    bitmap?.close();bitmap=next;
    resultsSequence++;$("#search-grid").replaceChildren(empty("Reference ready.","Crop to the garment, then find the closest previous styles in your archive."));$("#search-grid").setAttribute("aria-busy","false");$("#search-caption").textContent="New reference selected. Run a search to see its closest previous styles.";message("");
    canvas.width=Math.round(700*Math.min(1,bitmap.width/bitmap.height));
    canvas.height=Math.round(700*Math.min(1,bitmap.height/bitmap.width));
    canvas.hidden=false;$("#crop-controls").hidden=false;$("#crop-reset").hidden=false;$("#search-photo").disabled=false;
    $("#photo-caption").textContent=(file.name||"Pasted reference")+" · "+bitmap.width+" × "+bitmap.height+" px. Drag to isolate one garment.";
    [0,0,100,100].forEach((v,i)=>fields[i].value=v);draw();
  }
  $("#photo").onchange=run(e=>load(e.target.files[0]));
  $("#drop").ondragover=e=>{e.preventDefault();$("#drop").classList.add("dragging");};
  $("#drop").ondragleave=()=>$("#drop").classList.remove("dragging");
  $("#drop").ondrop=run(e=>{$("#drop").classList.remove("dragging");return load(e.dataTransfer.files[0]);});
  $("#drop").onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();$("#photo").click();}};
  document.addEventListener("paste",e=>{
    if($("#search").hidden || ["INPUT","TEXTAREA"].includes(document.activeElement.tagName))return;
    const item=[...e.clipboardData.items].find(x=>x.type.startsWith("image/"));
    if(item){e.preventDefault();run(()=>load(item.getAsFile()))();}
  });
  $("#crop-reset").onclick=()=>{[0,0,100,100].forEach((v,i)=>fields[i].value=v);draw();};
  function point(e){const r=canvas.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];}
  canvas.onpointerdown=e=>{start=point(e);canvas.setPointerCapture(e.pointerId);};
  canvas.onpointermove=e=>{if(!start)return;const end=point(e);draw();ctx.strokeStyle="#b96c4a";ctx.setLineDash([6,4]);ctx.strokeRect(start[0]*canvas.width,start[1]*canvas.height,(end[0]-start[0])*canvas.width,(end[1]-start[1])*canvas.height);ctx.setLineDash([]);};
  canvas.onpointercancel=()=>{start=null;draw();};
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
    const request=beginResults();
    try{
      const blob=await new Promise(resolve=>temp.toBlob(resolve,"image/jpeg",.95)),data=new FormData();
      if(request!==resultsSequence)return;
      if(!blob)throw new Error("The crop could not be prepared. Choose the image again and retry.");
      data.append("file",blob,"query.jpg");data.append("category",$("#search-category").value);data.append("limit","4");
      message("Searching your style archive…");
      showResults(await api("/api/search/photo",{method:"POST",body:data}),request);
    }catch(error){failResults(error,request);}
  });
  $("#text-search").onsubmit=run(async()=>{
    if(!$("#text-query").value.trim())throw new Error("Describe the garment you want to find.");
    const request=beginResults();message("Searching by description…");
    try{showResults(await api("/api/search/text?q="+encodeURIComponent($("#text-query").value)+"&limit=4"),request);}
    catch(error){failResults(error,request);}
  });
}
export function showResults(data,request=resultsSequence){
  if(request!==resultsSequence)return;
  const grid=$("#search-grid");grid.setAttribute("aria-busy","false");grid.replaceChildren();
  const items=data.items.slice(0,4);
  items.forEach((r,i)=>grid.append(card(r.product,r.score,true,i+1,r.matched_image)));
  if(!items.length)grid.append(empty("No previous styles found.","Try a wider crop, another reference image or a different category. Add and index your previous styles to build the archive."));
  $("#search-caption").textContent=items.length+" closest previous style"+(items.length===1?"":"s")+" · up to 4 from your indexed archive"+
    (items.length>0&&items.length<4?" · Fewer than four candidates are available for this search.":"")+
    (data.filter_may_limit_results?" Filters reduced the candidate pool.":"");
  message("");
}

