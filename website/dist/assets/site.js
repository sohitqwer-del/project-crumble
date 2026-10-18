"use strict";
const menuButton=document.querySelector(".menu-toggle");
const menu=document.querySelector("#main-nav");
if(menuButton&&menu){
  function closeMenu(){menu.classList.remove("open");menuButton.setAttribute("aria-expanded","false");}
  menuButton.addEventListener("click",()=>{const open=menuButton.getAttribute("aria-expanded")!=="true";menu.classList.toggle("open",open);menuButton.setAttribute("aria-expanded",String(open));});
  menu.addEventListener("click",e=>{if(e.target.closest("a"))closeMenu();});
  document.addEventListener("keydown",e=>{if(e.key==="Escape"&&menu.classList.contains("open")){closeMenu();menuButton.focus();}});
  document.addEventListener("click",e=>{if(!e.target.closest(".site-header,.editorial-header"))closeMenu();});
  matchMedia("(min-width:781px)").addEventListener("change",closeMenu);
}
document.querySelectorAll(".copy-button").forEach(button=>button.addEventListener("click",async()=>{
  const code=button.closest(".code-block").querySelector("code");
  try{await navigator.clipboard.writeText(code.textContent);button.textContent="Copied ✓";setTimeout(()=>button.textContent="Copy",1800);}catch{button.textContent="Select text";const selection=getSelection();const range=document.createRange();range.selectNodeContents(code);selection.removeAllRanges();selection.addRange(range);}
}));
const osButtons=[...document.querySelectorAll("[data-os]")];
function selectOS(button){osButtons.forEach(b=>{const selected=b===button;b.setAttribute("aria-selected",String(selected));b.tabIndex=selected?0:-1;});document.querySelectorAll("[data-os-panel]").forEach(panel=>panel.hidden=panel.dataset.osPanel!==button.dataset.os);}
osButtons.forEach((button,index)=>{button.addEventListener("click",()=>selectOS(button));button.addEventListener("keydown",e=>{let i=index;if(e.key==="ArrowRight")i=(index+1)%osButtons.length;else if(e.key==="ArrowLeft")i=(index+osButtons.length-1)%osButtons.length;else if(e.key==="Home")i=0;else if(e.key==="End")i=osButtons.length-1;else return;e.preventDefault();selectOS(osButtons[i]);osButtons[i].focus();});});
