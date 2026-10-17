export const $ = (q) => document.querySelector(q);
export const state = {selected: [], comparison: null, page: 0, status: null};
export function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
export function message(text) { $("#notice").textContent = text; }
export async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (res.status === 401) {
    $("#login").hidden = false; $("#application").hidden = true;
    throw new Error("Sign in to open this workspace.");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}
export function json(method, body) { return {method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(body)}; }
export function run(fn) {
  return async (event) => {
    if (event?.preventDefault) event.preventDefault();
    const button = event?.currentTarget?.tagName === "BUTTON" ? event.currentTarget : null;
    if (button) button.disabled = true;
    try { await fn(event); }
    catch (error) { message(error.message); }
    finally { if (button) button.disabled = false; }
  };
}
export function show(tab) {
  $("#comparison").hidden = true;
  document.querySelectorAll(".tab").forEach(n => n.hidden = n.id !== tab);
  document.querySelectorAll("nav button").forEach(n => n.classList.toggle("active", n.dataset.tab === tab));
}
export function image(aid, alt) {
  const n = el("img"); n.src = "/assets/" + encodeURIComponent(aid); n.alt = alt; n.loading = "lazy"; return n;
}
export function dispatch(name, detail) { document.dispatchEvent(new CustomEvent(name, {detail})); }
export function card(p, score, controls = true) {
  const n = el("article", null, "card");
  n.append(image(p.images[0], p.title));
  const body = el("div", null, "card-body");
  body.append(el("p", p.brand || "Independent collection", "eyebrow"), el("h3", p.title));
  if (score != null) body.append(el("span", "Similarity " + score.toFixed(3), "score"));
  if (controls) {
    const actions = el("div", null, "card-actions");
    for (const [label, name] of [["Details", "open-product"], ["Select to compare", "select-product"], ["Similar", "find-similar"]]) {
      const b = el("button", label); b.onclick = () => dispatch(name, p); actions.append(b);
    }
    body.append(actions);
  }
  n.append(body); return n;
}
export function select(p) {
  const old = state.selected.findIndex(x => x.id === p.id);
  if (old >= 0) state.selected.splice(old, 1);
  else if (state.selected.length < 2) state.selected.push(p);
  else { message("Two garments are selected. Clear the selection to choose another pair."); return; }
  $("#selection").hidden = !state.selected.length;
  $("#selection-label").textContent = state.selected.map(x => x.title).join("  to  ");
  $("#compare-selected").disabled = state.selected.length !== 2;
}

