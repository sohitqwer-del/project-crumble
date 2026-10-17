import {$, el, api, json, run, image, message, state} from "./ui.js";

export async function openProduct(product) {
  const p = await api("/api/products/" + encodeURIComponent(product.id));
  const box = $("#product-detail"); box.replaceChildren(el("p", p.brand, "eyebrow"), el("h2", p.title));
  const photo = image(p.images[0], p.title); photo.className = "detail-photo"; box.append(photo);
  const views = el("div", null, "card-actions");
  p.images.forEach((aid, i) => {const b = el("button", "View " + (i + 1)); b.onclick = () => photo.src = "/assets/" + aid; views.append(b);});
  box.append(views, el("p", "Image rights: " + p.rights, "muted"));
  const reviewer = el("input"); reviewer.placeholder = "Your name"; reviewer.value = $("#reviewer").value;
  const label = el("label", "Reviewer name (required for corrections)"); label.append(reviewer); box.append(label);
  const infer = el("button", "Suggest visible parts");
  infer.onclick = run(async () => {
    const data = await api("/api/products/" + p.id + "/infer", {method:"POST"});
    for (const [field, proposal] of Object.entries(data.proposals)) {
      const row = box.querySelector('[data-field="' + field + '"]');
      if (row && row.querySelector("select").value !== "verified") {
        row.querySelector("select").value = proposal.state;
        row.querySelector("input").value = proposal.values.join(", ");
        row.dataset.source = "visual:" + proposal.source + ";image:" + data.image;
      }
    }
    message("Visual proposals loaded. Check each field and save corrections separately.");
  });
  box.append(infer, el("p", "Unknown is different from a confirmed absence. Enter 'none' only when verified.", "muted"));
  for (const [key, f] of Object.entries(p.structure.fields)) {
    const row = el("div", null, "part-row"); row.dataset.field = key;
    row.append(el("p", f.label));
    const values = el("input"); values.value = f.values.join(", "); values.setAttribute("aria-label", f.label + " value");
    const select = el("select"); select.setAttribute("aria-label", f.label + " evidence");
    ["unknown", "not_visible", "stated", "inferred", "verified", "conflicting"].forEach(v => {
      const option = el("option", v.replaceAll("_", " ")); option.value = v; select.append(option);
    }); select.value = f.state;
    values.oninput = () => { delete row.dataset.source; };
    const save = el("button", "Save part");
    save.onclick = run(async () => {
      if (!reviewer.value.trim()) throw new Error("Enter the reviewer name first.");
      const payload = {snapshot:p.snapshot, field:key, reviewer:reviewer.value,
        claim:{state:select.value, values:values.value.split(",").map(x=>x.trim()).filter(Boolean),
          source:row.dataset.source || "reviewer correction"}, note:""};
      const result = await api("/api/products/" + p.id + "/parts", json("PATCH", payload));
      p.snapshot = result.snapshot; $("#reviewer").value = reviewer.value;
      message(f.label + " saved with its evidence snapshot.");
    });
    row.append(values, select, save); box.append(row);
  }
  const history = el("button", "Show observation history");
  history.onclick = run(async () => {
    const h = await api("/api/products/" + p.id + "/history");
    const list = el("div");
    list.append(el("p", h.date_meaning, "muted"));
    h.snapshots.forEach(s => list.append(el("p", (s.observed_at || "No source date supplied") + " / " + s.title)));
    list.append(el("p", h.events.length + " recorded corrections / " + h.reviewed_relationships.length + " relationship reviews"));
    history.replaceWith(list);
  });
  box.append(history);
  if (!$("#product-dialog").open) $("#product-dialog").showModal();
}
export async function openComparison(a, b) {
  const data = await api("/api/compare?a=" + encodeURIComponent(a) + "&b=" + encodeURIComponent(b));
  state.comparison = data;
  document.querySelectorAll(".tab").forEach(n => n.hidden = true);
  $("#comparison").hidden = false; $("#selection").hidden = true;
  const products = $("#compare-products"); products.replaceChildren();
  [data.a, data.b].forEach((p, i) => {
    const n = el("div", null, "panel"); const im = image(p.images[0], p.title); im.className="detail-photo";
    n.append(el("p", i ? "AFTER / COMPARISON" : "BEFORE / REFERENCE", "eyebrow"), im, el("h3", p.title));
    products.append(n);
  });
  const rows=$("#compare-rows"), changed=$("#changed-fields"); rows.replaceChildren(); changed.replaceChildren();
  for (const row of data.comparison.rows) {
    const tr=el("tr");
    tr.append(el("td",row.label),el("td",row.a.values.join(", ") || "Unknown"),el("td",row.b.values.join(", ") || "Unknown"));
    const td=el("td"); td.append(el("span",row.status.replaceAll("_"," "), "badge "+row.status)); tr.append(td); rows.append(tr);
    const l=el("label"), c=el("input"); c.type="checkbox"; c.value=row.key; l.append(c,document.createTextNode(row.label)); changed.append(l);
  }
  const smv=$("#smv"), s=data.smv; smv.replaceChildren(el("p","SUGGESTED OPERATION CHANGE","eyebrow"),el("h3","SMV impact"));
  if(s.illustrative) smv.append(el("p","Illustrative demo times. These are invented examples, not factory standards.","warning"));
  const d=s.mapped_delta;
  smv.append(el("div",d.low == null ? "Time data needed" : (d.low>0?"+":"")+d.low.toFixed(2)+" to "+(d.high>0?"+":"")+d.high.toFixed(2)+" min","delta"));
  smv.append(el("p",s.explanation),el("p",s.scope,"muted"));
  for(const row of s.mapped){
    const n=el("div",null,"smv-line"); n.append(el("b",row.field.replaceAll("_"," ")+": "+row.before.join(", ")+" / "+row.after.join(", ")));
    for(const op of row.operations) n.append(el("p",(op.quantity_delta>0?"+":"")+op.quantity_delta+" / "+op.label+" / "+op.low+" to "+op.high+" min each / "+op.source));
    smv.append(n);
  }
  if(s.unmapped_changes.length) smv.append(el("p","Unmapped changes: "+s.unmapped_changes.map(x=>x.field).join(", "),"warning"));
  smv.append(el("p",s.unknown_fields.length+" fields need more evidence. No new total garment SMV is calculated.","muted"));
  $("#relation").value=""; $("#review-note").value=""; $("#smv-decision").value="not_reviewed";
  $("#review-saved").textContent=data.reviews.length+" prior reviews for this pair.";
  $("#comparison").scrollIntoView({behavior:"instant"});
}
export function bindReview(){
  $("#relation").onchange=()=>{if($("#relation").value==="same_visible_design") document.querySelectorAll("#changed-fields input").forEach(x=>x.checked=false);};
  $("#review-form").onsubmit=run(async()=>{
    const d=state.comparison;
    const body={a:d.a.id,b:d.b.id,snapshot_a:d.a.snapshot,snapshot_b:d.b.snapshot,
      relation:$("#relation").value,reviewer:$("#reviewer").value,note:$("#review-note").value,
      changed:[...document.querySelectorAll("#changed-fields input:checked")].map(x=>x.value),
      smv_decision:$("#smv-decision").value,smv_library_hash:d.smv.library_hash};
    await api("/api/reviews",json("POST",body)); $("#review-saved").textContent="Review saved. Evidence and operation library recorded."; message("Review saved.");
  });
}

