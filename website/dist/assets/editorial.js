"use strict";
(() => {
 const cards=[...document.querySelectorAll("[data-look]")];
 cards.forEach(card=>card.addEventListener("click",()=>{
  const key=card.dataset.look,look=window.CrumbleStudy[key];
  cards.forEach(c=>{const on=c===card;c.classList.toggle("selected",on);c.setAttribute("aria-pressed",String(on));});
  document.querySelector("#selected-name").textContent=look.title;
  document.querySelector("#selected-details").textContent=look.details;
  document.querySelector("#selected-view").textContent=look.view;
  document.querySelector("#selected-link").href="demo.html?photo="+key;
 }));
})();
