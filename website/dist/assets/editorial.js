"use strict";
(() => {
 const looks={
  reference:{name:"The original.",details:"Short sleeves · No pockets",low:0,high:0},
  long:{name:"A longer line.",details:"Short sleeve hems → long sleeves with cuffs",low:.9,high:1.7},
  pockets:{name:"An added detail.",details:"No pockets → two patch pockets",low:1.2,high:1.8},
  combined:{name:"A new direction.",details:"Long sleeves with cuffs · Two patch pockets",low:2.1,high:3.5}
 };
 const cards=[...document.querySelectorAll("[data-look]")];
 cards.forEach(card=>card.addEventListener("click",()=>{
  const key=card.dataset.look,look=looks[key];
  cards.forEach(c=>{const on=c===card;c.classList.toggle("selected",on);c.setAttribute("aria-pressed",String(on));});
  document.querySelector("#selected-name").textContent=look.name;
  document.querySelector("#selected-details").textContent=look.details;
  const time=document.querySelector("#selected-time");
  time.replaceChildren(document.createTextNode((look.low>0?"+":"")+look.low.toFixed(2)+"–"+look.high.toFixed(2)+" "));
  const small=document.createElement("small");small.textContent="min";time.append(small);
  document.querySelector("#selected-link").href="demo.html?variant="+key;
 }));
})();