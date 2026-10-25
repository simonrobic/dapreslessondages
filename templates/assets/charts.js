/* SPDX-License-Identifier: AGPL-3.0-or-later
   D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md. */
/* D’après les sondages — graphiques (SVG/HTML sans dépendance).
   Les noms viennent des sources de données : toujours insérés via textContent. */
(function () {
  "use strict";

  const node = document.getElementById("payload");
  if (!node) return;
  const P = JSON.parse(node.textContent);
  const C = P.candidats;
  const SVG = "http://www.w3.org/2000/svg";
  const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  const MONTHS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  let scenarioIndex = 0;

  // ---------- utilitaires ----------
  const nf1 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf0 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
  const nf2 = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function prob(p) {
    const v = 100 * p;
    if (v > 0 && v < 1) return "< 1 %";
    if (v > 99 && v < 100) return "> 99 %";
    return nf0.format(v) + " %";
  }
  const share = (v) => nf1.format(v) + " %";
  const color = (name) => `var(--s${(C[name] || {}).slot || 0})`;
  const short = (name) => (C[name] || {}).court || name;
  const party = (name) => (C[name] || {}).parti || "";
  function el(tag, attrs, text) {
    const e = document.createElement(tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (k === "style") e.setAttribute("style", v); else if (k === "class") e.className = v; else e.setAttribute(k, v);
    }
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function svg(tag, attrs, parent) {
    const e = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  }
  function dateFr(iso) {
    const d = new Date(iso + "T12:00:00");
    return `${d.getDate() === 1 ? "1er" : d.getDate()} ${MONTHS_LONG[d.getMonth()]} ${d.getFullYear()}`;
  }
  const scenario = () => P.scenarios[scenarioIndex];

  // ---------- infobulle partagée ----------
  const tip = el("div", { class: "tooltip", role: "status" });
  tip.hidden = true;
  document.body.appendChild(tip);
  function showTip(evt, title, rows) {
    tip.replaceChildren();
    if (title) tip.appendChild(el("div", { class: "tt-title" }, title));
    for (const r of rows) {
      if (r.text) { tip.appendChild(el("div", { class: "tt-text" }, r.text)); continue; }
      const row = el("div", { class: "tt-row" });
      const key = el("span", { class: "key-line", style: `--c:${r.color}` });
      row.append(key, el("strong", null, r.value), el("span", null, r.label));
      tip.appendChild(row);
    }
    tip.hidden = false;
    const pad = 14;
    let x, y;
    if (evt.type === "focus" || evt.clientX === undefined) {
      const b = evt.target.getBoundingClientRect();
      x = b.left + window.scrollX + 20; y = b.bottom + window.scrollY + 6;
    } else {
      x = evt.pageX + pad; y = evt.pageY + pad;
    }
    const w = tip.offsetWidth, h = tip.offsetHeight;
    if (x + w > window.scrollX + document.documentElement.clientWidth - 8) x = Math.max(8, x - w - 2 * pad);
    if (y + h > window.scrollY + window.innerHeight - 8) y = y - h - 2 * pad;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  const hideTip = () => { tip.hidden = true; };
  function hoverable(target, fn) {
    target.addEventListener("pointermove", (e) => fn(e));
    target.addEventListener("pointerleave", hideTip);
    target.addEventListener("focus", (e) => fn(e));
    target.addEventListener("blur", hideTip);
  }

  function dataTable(head, rows) {
    const wrap = el("div", { class: "table-wrap" });
    const t = el("table");
    const tr = el("tr");
    head.forEach((h, i) => tr.appendChild(el("th", i ? { class: "n" } : null, h)));
    t.appendChild(el("thead")).appendChild(tr);
    const tb = el("tbody");
    for (const r of rows) {
      const row = el("tr");
      r.forEach((v, i) => row.appendChild(el("td", i ? { class: "n" } : null, v)));
      tb.appendChild(row);
    }
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }
  function attachTable(container, head, rows) {
    const d = el("details", { class: "data" });
    d.appendChild(el("summary", null, "Voir les données"));
    d.appendChild(dataTable(head, rows));
    container.appendChild(d);
  }

  // ---------- barres : probabilités ----------
  function renderBars(id, key) {
    const box = document.getElementById(id);
    if (!box) return;
    box.replaceChildren();
    const sc = scenario();
    const items = sc.candidats.map((c) => ({ c, v: sc.stats[c][key] })).sort((a, b) => b.v - a.v);
    const shown = items.filter((it, i) => it.v >= 0.005 || i < 3);
    const rest = items.length - shown.length;
    const list = el("div", { class: "bars" });
    for (const it of shown) {
      const s = sc.stats[it.c];
      const row = el("div", { class: "bar-row", tabindex: "0" });
      const label = el("div", { class: "bar-label" }, short(it.c));
      if (party(it.c)) label.appendChild(el("span", { class: "party" }, party(it.c)));
      const track = el("div", { class: "bar-track" });
      track.append(el("div", { class: "bar", style: `width:${Math.max(0.3, 100 * it.v) * 0.86}%;--c:${color(it.c)}` }),
        el("span", { class: "bar-value" }, prob(it.v)));
      row.append(label, track);
      row.setAttribute("aria-label", `${it.c} : ${prob(it.v)}`);
      hoverable(row, (e) => showTip(e, it.c, [
        { color: color(it.c), value: prob(s.p_victoire), label: "de victoire" },
        { color: color(it.c), value: prob(s.p_qualifie), label: "d'être au second tour" },
        { color: color(it.c), value: prob(s.p_premier), label: "d'arriver en tête au 1er tour" },
        { color: color(it.c), value: share(s.moyenne), label: `au 1er tour (${nf0.format(s.q05)}–${nf0.format(s.q95)} %)` },
      ]));
      list.appendChild(row);
    }
    box.appendChild(list);
    if (rest > 0) box.appendChild(el("p", { class: "small muted", style: "margin:10px 0 0" },
      `${rest} autre${rest > 1 ? "s" : ""} candidat${rest > 1 ? "s" : ""} : moins de 0,5 % chacun.`));
    attachTable(box, ["Candidat", key === "p_victoire" ? "Victoire" : "Second tour"],
      items.map((it) => [it.c, prob(it.v)]));
  }

  // ---------- intervalles : premier tour ----------
  function renderRanges(id) {
    const box = document.getElementById(id);
    if (!box) return;
    box.replaceChildren();
    const sc = scenario();
    const res = P.resultats ? P.resultats.premier_tour : null;
    const names = sc.candidats.slice().sort((a, b) => sc.stats[b].moyenne - sc.stats[a].moyenne);
    let max = Math.max(...names.map((c) => sc.stats[c].q95), ...(res ? Object.values(res) : [0]));
    max = Math.ceil(max / 10) * 10;
    const x = (v) => `${(100 * v) / max}%`;

    const legend = el("div", { class: "legend" });
    const l1 = el("span", { class: "legend-item" });
    l1.append(el("span", { class: "key-dot", style: "--c:var(--ink-2)" }), document.createTextNode("score moyen attendu"));
    const l2 = el("span", { class: "legend-item" });
    l2.append(el("span", { class: "key-range" }), document.createTextNode("9 chances sur 10"));
    legend.append(l1, l2);
    if (res) {
      const l3 = el("span", { class: "legend-item" });
      l3.append(el("span", { class: "key-result" }), document.createTextNode("résultat officiel"));
      legend.appendChild(l3);
    }
    box.appendChild(legend);

    const wrap = el("div", { class: "ranges" });
    for (const c of names) {
      const s = sc.stats[c];
      const row = el("div", { class: "range-row", tabindex: "0" });
      const label = el("div", { class: "bar-label" }, short(c));
      if (party(c)) label.appendChild(el("span", { class: "party" }, party(c)));
      const plot = el("div", { class: "range-plot" });
      for (let t = 0; t <= max; t += 10) plot.appendChild(el("div", { class: "range-grid", style: `left:${x(t)}` }));
      plot.appendChild(el("div", { class: "range-line", style: `left:${x(s.q05)};width:calc(${x(s.q95)} - ${x(s.q05)});--c:${color(c)}` }));
      plot.appendChild(el("div", { class: "range-dot", style: `left:${x(s.moyenne)};--c:${color(c)}` }));
      if (res && res[c] !== undefined) plot.appendChild(el("div", { class: "range-result", style: `left:${x(res[c])}` }));
      row.append(label, plot);
      hoverable(row, (e) => {
        const rows = [
          { color: color(c), value: share(s.moyenne), label: "score moyen attendu" },
          { color: color(c), value: `${nf1.format(s.q05)} – ${nf1.format(s.q95)} %`, label: "9 chances sur 10" },
        ];
        if (res && res[c] !== undefined) rows.push({ color: "var(--ink)", value: share(res[c]), label: "résultat officiel" });
        showTip(e, c, rows);
      });
      wrap.appendChild(row);
    }
    const axis = el("div", { class: "range-axis" });
    const ticks = el("div", { class: "range-ticks" });
    for (let t = 0; t <= max; t += 10) {
      ticks.appendChild(el("span", { style: `left:${x(t)}${t === max ? ";transform:translateX(-100%)" : ""}` },
        t === max ? `${t}\u202f%` : String(t)));
    }
    axis.append(el("div"), ticks);
    wrap.appendChild(axis);
    box.appendChild(wrap);
    const head = ["Candidat", "Moyenne", "Bas (5 %)", "Haut (95 %)"];
    if (res) head.push("Résultat");
    attachTable(box, head, names.map((c) => {
      const s = sc.stats[c];
      const r = [c, share(s.moyenne), share(s.q05), share(s.q95)];
      if (res) r.push(res[c] !== undefined ? share(res[c]) : "—");
      return r;
    }));
  }

  // ---------- duels ----------
  function renderDuels(id) {
    const box = document.getElementById(id);
    if (!box) return;
    box.replaceChildren();
    const sc = scenario();
    const real = P.resultats ? P.resultats.second_tour : null;
    const list = el("div", { class: "duels" });
    const duels = sc.duels.filter((d) => d.p_duel >= 0.01).slice(0, 5);
    for (const d of duels) {
      // Le candidat attendu en tête à gauche
      const flip = d.a_moyenne < 50;
      const L = flip ? d.b : d.a, R = flip ? d.a : d.b;
      const lMean = flip ? 100 - d.a_moyenne : d.a_moyenne;
      const lWin = flip ? 1 - d.p_a_gagne : d.p_a_gagne;
      const lLo = flip ? 100 - d.a_q95 : d.a_q05, lHi = flip ? 100 - d.a_q05 : d.a_q95;
      const isReal = real && real[L] !== undefined && real[R] !== undefined;

      const item = el("div", { class: "duel", tabindex: "0" });
      const head = el("div", { class: "duel-head" });
      head.appendChild(el("strong", null, `${short(L)} – ${short(R)}`));
      const pp = el("span", { class: "p" }, `${prob(d.p_duel)} de chances que ce duel ait lieu`);
      head.appendChild(pp);
      item.appendChild(head);
      const bar = el("div", { class: "duel-bar" });
      bar.append(el("div", { class: "left", style: `width:${lMean}%;--ca:${color(L)}` }),
        el("div", { class: "right", style: `width:${100 - lMean}%;--cb:${color(R)}` }),
        el("div", { class: "duel-mid", title: "50 %" }));
      item.appendChild(bar);
      const foot = el("div", { class: "duel-foot" });
      foot.append(el("span", null, `${short(L)} ${nf0.format(lMean)} % · gagne dans ${prob(lWin)} des cas`),
        el("span", null, `${short(R)} ${nf0.format(100 - lMean)} %`));
      item.appendChild(foot);
      if (!d.sonde) item.appendChild(el("p", { class: "small muted", style: "margin:6px 0 0" },
        "Ce duel n'a pas été sondé récemment : le modèle le considère à 50/50."));
      if (isReal) {
        const p = el("p", { class: "small", style: "margin:6px 0 0" });
        p.appendChild(el("span", { class: "tag" }, "Duel réel"));
        p.appendChild(document.createTextNode(` Résultat : ${short(L)} ${share(real[L])}, ${short(R)} ${share(real[R])}`));
        item.appendChild(p);
      }
      hoverable(item, (e) => showTip(e, `${L} – ${R}`, [
        { color: color(L), value: `${nf0.format(lMean)} %`, label: `${short(L)} (${nf0.format(lLo)}–${nf0.format(lHi)} %)` },
        { color: color(R), value: `${nf0.format(100 - lMean)} %`, label: short(R) },
        { color: color(L), value: prob(lWin), label: `de victoire pour ${short(L)}` },
        { color: "var(--ink-2)", value: prob(d.p_duel), label: "de chances que ce duel ait lieu" },
      ]));
      list.appendChild(item);
    }
    box.appendChild(list);
    attachTable(box, ["Duel", "Probabilité du duel", "Score du premier", "Victoire du premier"], duels.map((d) => {
      const flip = d.a_moyenne < 50;
      const L = flip ? d.b : d.a, R = flip ? d.a : d.b;
      return [`${L} – ${R}`, prob(d.p_duel), `${nf0.format(flip ? 100 - d.a_moyenne : d.a_moyenne)} %`, prob(flip ? 1 - d.p_a_gagne : d.p_a_gagne)];
    }));
  }

  // ---------- courbes : évolution ----------
  let evoMode = "victoire";
  function renderEvolution(id) {
    const box = document.getElementById(id);
    if (!box || !P.timeline.length) return;
    box.replaceChildren();
    const TL = P.timeline;
    const t0 = new Date(TL[0].date + "T12:00:00").getTime();
    const endIso = P.resultats ? P.date_premier_tour : TL[TL.length - 1].date;
    const t1 = new Date(endIso + "T12:00:00").getTime();
    const value = (pt, c) => evoMode === "victoire"
      ? (pt.victoire[c] === undefined ? null : 100 * pt.victoire[c])
      : (pt.premier_tour[c] === undefined ? null : pt.premier_tour[c][1]);

    // Séries : candidats colorés présents au moins une fois (et visibles)
    const names = Object.keys(C).filter((c) => C[c].slot > 0 && TL.some((pt) => {
      const v = value(pt, c);
      return v !== null && (evoMode === "victoire" ? v >= 2 : v >= 3);
    }));

    // Légende (toujours présente)
    const legend = el("div", { class: "legend" });
    for (const c of names) {
      const it = el("span", { class: "legend-item" });
      it.append(el("span", { class: "key-line", style: `--c:${color(c)}` }), document.createTextNode(short(c)));
      legend.appendChild(it);
    }
    if (evoMode === "intentions") {
      const it = el("span", { class: "legend-item" });
      it.append(el("span", { class: "key-dot", style: "--c:var(--axis);opacity:.5" }), document.createTextNode("un sondage"));
      legend.appendChild(it);
      if (P.resultats) {
        const r = el("span", { class: "legend-item" });
        r.append(el("span", { class: "key-dot", style: "--c:var(--ink)" }), document.createTextNode("résultat"));
        legend.appendChild(r);
      }
    }
    box.appendChild(legend);

    const chart = el("div", { class: "chart" });
    box.appendChild(chart);
    const W = chart.clientWidth || 600;
    const narrow = W < 560;
    const H = narrow ? 260 : 320;
    const m = { top: 22, right: narrow ? 70 : 96, bottom: 28, left: 34 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    let ymax = evoMode === "victoire" ? 100 : 5 * Math.ceil(Math.max(
      ...TL.flatMap((pt) => names.map((c) => value(pt, c) || 0)),
      ...(P.resultats ? names.map((c) => P.resultats.premier_tour[c] || 0) : [0])) / 5 + 0.2);
    const X = (iso) => m.left + ((new Date(iso + "T12:00:00").getTime() - t0) / (t1 - t0)) * iw;
    const Y = (v) => m.top + ih - (v / ymax) * ih;

    const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
      "aria-label": evoMode === "victoire" ? "Évolution des chances de victoire" : "Évolution des intentions de vote au premier tour" }, chart);

    // Grille et axes
    const step = evoMode === "victoire" ? 25 : (ymax > 30 ? 10 : 5);
    for (let v = 0; v <= ymax + 0.001; v += step) {
      svg("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: m.left + iw, y1: Y(v), y2: Y(v) }, root);
      const t = svg("text", { class: "tick", x: m.left - 6, y: Y(v) + 4, "text-anchor": "end" }, root);
      t.textContent = `${v}${v === ymax || (v + step > ymax) ? " %" : ""}`;
    }
    const start = new Date(t0), end = new Date(t1);
    const months = (end.getFullYear() - start.getFullYear()) * 12 + end.getMonth() - start.getMonth();
    const perMonth = iw / Math.max(1, months);
    const every = [1, 2, 3, 4, 6, 12].find((k) => k * perMonth >= 58) || 12;
    for (let d = new Date(start.getFullYear(), start.getMonth() + 1, 1); d <= end; d.setMonth(d.getMonth() + every)) {
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
      const xx = X(iso);
      svg("line", { class: "gridline", x1: xx, x2: xx, y1: m.top + ih, y2: m.top + ih + 4 }, root);
      const t = svg("text", { class: "tick", x: xx, y: m.top + ih + 18, "text-anchor": "middle" }, root);
      t.textContent = d.getMonth() === 0 || (d.getMonth() < every) ? `${MONTHS[d.getMonth()]} ${String(d.getFullYear()).slice(2)}` : MONTHS[d.getMonth()];
    }

    // Sondages individuels (mode intentions)
    if (evoMode === "intentions") {
      const g = svg("g", {}, root);
      for (const poll of P.sondages) {
        for (const c of names) {
          if (poll.s[c] === undefined) continue;
          const xx = X(poll.d);
          if (xx < m.left) continue;
          svg("circle", { class: "poll-dot", cx: xx, cy: Y(poll.s[c]), r: 2.5, fill: color(c) }, g);
        }
      }
    }

    // Courbes (coupées quand le candidat sort du scénario principal)
    const ends = [];
    for (const c of names) {
      let d = "", prev = false, last = null;
      for (const pt of TL) {
        const v = value(pt, c);
        if (v === null) { prev = false; continue; }
        d += `${prev ? "L" : "M"}${X(pt.date).toFixed(1)},${Y(v).toFixed(1)}`;
        prev = true; last = { x: X(pt.date), y: Y(v), v, date: pt.date };
      }
      svg("path", { class: "series", d, stroke: color(c) }, root);
      if (last) ends.push({ c, ...last });
    }

    // Résultat officiel au jour du vote
    if (P.resultats && evoMode === "intentions") {
      for (const c of names) {
        const v = P.resultats.premier_tour[c];
        if (v === undefined) continue;
        svg("circle", { cx: X(P.date_premier_tour), cy: Y(v), r: 5, fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 2 }, root);
      }
    }

    // Points et étiquettes de fin (sélectives : pas de chevauchement)
    const lastDate = TL[TL.length - 1].date;
    const current = ends.filter((e) => e.date === lastDate).sort((a, b) => a.y - b.y);
    let lastY = -Infinity;
    for (const e of current) {
      svg("circle", { class: "end-dot", cx: e.x, cy: e.y, r: 4, fill: color(e.c) }, root);
      if (e.y - lastY >= 14) {
        const t = svg("text", { class: "end-label", x: e.x + 8, y: e.y + 4 }, root);
        const val = evoMode === "victoire" ? prob(e.v / 100) : share(e.v);
        t.textContent = `${short(e.c)} ${val}`;
        if (e.x + 8 + t.getComputedTextLength() > W) t.textContent = val;  // la légende porte le nom
        if (e.x + 8 + t.getComputedTextLength() > W) t.remove();
        else lastY = e.y;
      }
    }

    // Jalons de campagne
    const evs = (P.evenements || []).filter((ev) => X(ev.date) >= m.left && X(ev.date) <= m.left + iw);
    for (const ev of evs) {
      const xx = X(ev.date);
      svg("line", { class: "event", x1: xx, x2: xx, y1: m.top - 8, y2: m.top + ih }, root).setAttribute("opacity", "0.5");
      const mark = svg("circle", { class: "event-mark", cx: xx, cy: m.top - 12, r: 5, tabindex: "0", role: "img",
        "aria-label": `${dateFr(ev.date)} : ${ev.texte}` }, root);
      hoverable(mark, (e) => { e.stopPropagation(); showTip(e, dateFr(ev.date), [{ text: ev.texte }]); });
    }

    // Réticule + infobulle : toutes les séries à la date pointée
    const cross = svg("line", { class: "crosshair", y1: m.top, y2: m.top + ih, visibility: "hidden" }, root);
    const hit = svg("rect", { x: m.left, y: m.top, width: iw, height: ih, fill: "transparent" }, root);
    hit.addEventListener("pointermove", (e) => {
      const r = root.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      let best = 0, bd = Infinity;
      TL.forEach((pt, i) => { const dd = Math.abs(X(pt.date) - px); if (dd < bd) { bd = dd; best = i; } });
      const pt = TL[best];
      cross.setAttribute("x1", X(pt.date)); cross.setAttribute("x2", X(pt.date));
      cross.setAttribute("visibility", "visible");
      const rows = names.filter((c) => value(pt, c) !== null)
        .sort((a, b) => value(pt, b) - value(pt, a))
        .map((c) => ({ color: color(c), label: short(c),
          value: evoMode === "victoire" ? prob(value(pt, c) / 100) : share(value(pt, c)) }));
      showTip(e, `Prévision du ${dateFr(pt.date)}`, rows);
    });
    hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });

    // Vue tableau
    const head = ["Date"].concat(names.map(short));
    attachTable(box, head, TL.slice().reverse().map((pt) => [dateFr(pt.date)].concat(names.map((c) => {
      const v = value(pt, c);
      return v === null ? "—" : (evoMode === "victoire" ? prob(v / 100) : share(v));
    }))));
  }

  // ---------- au même stade de la campagne ----------
  // Courbe des chances de victoire du candidat en tête à ce stade et du futur élu.
  function drawStageCurve(box, c, j) {
    box.replaceChildren();
    if (c.indirect || !c.courbe || !c.courbe.j.length) return;
    const snap = c.etapes[String(j)] || {};
    const names = [snap.favori, c.elu].filter((x, i, a) => x && a.indexOf(x) === i);
    const meta = (n) => c.candidats[n] || { court: n, slot: 0 };
    const col = (n) => `var(--s${meta(n).slot || 0})`;
    const legend = el("div", { class: "legend" });
    for (const n of names) {
      const it = el("span", { class: "legend-item" });
      it.append(el("span", { class: "key-line", style: `--c:${col(n)}` }), document.createTextNode(`${meta(n).court}, chances de victoire`));
      legend.appendChild(it);
    }
    box.appendChild(legend);

    const chart = el("div", { class: "chart" });
    box.appendChild(chart);
    const W = chart.clientWidth || 400, H = 160;
    const m = { top: 22, right: 16, bottom: 26, left: 34 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    const js = c.courbe.j;
    const jmax = Math.max(...js, j);
    const X = (d) => m.left + (1 - d / jmax) * iw;
    const Y = (v) => m.top + ih - v * ih;
    const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
      "aria-label": `${c.annee} : chances de victoire de ${names.join(" et ")} selon le modèle, jusqu'au premier tour` }, chart);
    for (const v of [0, 0.5, 1]) {
      svg("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: m.left + iw, y1: Y(v), y2: Y(v) }, root);
      svg("text", { class: "tick", x: m.left - 6, y: Y(v) + 4, "text-anchor": "end" }, root).textContent = v === 1 ? "100 %" : String(100 * v);
    }
    const every = jmax > 250 || iw < 320 ? 100 : 50;
    for (let d = every * Math.floor(jmax / every); d >= 0; d -= every) {
      const x = X(d);
      svg("line", { class: "gridline", x1: x, x2: x, y1: m.top + ih, y2: m.top + ih + 4 }, root);
      svg("text", { class: "tick", x, y: H - 6, "text-anchor": d === 0 ? "end" : "middle" }, root)
        .textContent = d === 0 ? "1er tour" : `J-${d}`;
    }
    const xt = X(j);
    svg("line", { class: "today", x1: xt, x2: xt, y1: m.top - 6, y2: m.top + ih }, root);
    const lab = svg("text", { class: "today-label", x: Math.min(Math.max(xt, m.left + 40), m.left + iw - 40), y: m.top - 10, "text-anchor": "middle" }, root);
    lab.textContent = j === P.jours_avant || (P.meme_stade && j === P.meme_stade.jours_avant) ? `aujourd'hui, J-${j}` : `J-${j}`;
    let at = 0;
    js.forEach((d, i) => { if (Math.abs(d - j) < Math.abs(js[at] - j)) at = i; });
    for (const n of names) {
      const vals = c.courbe.series[n] || [];
      let d = "", prev = false;
      js.forEach((dd, i) => {
        const v = vals[i];
        if (v === null || v === undefined) { prev = false; return; }
        d += `${prev ? "L" : "M"}${X(dd).toFixed(1)},${Y(v).toFixed(1)}`;
        prev = true;
      });
      svg("path", { class: "series", d, stroke: col(n) }, root);
      if (vals[at] !== null && vals[at] !== undefined && Math.abs(js[at] - j) <= 7) {
        svg("circle", { class: "end-dot", cx: X(js[at]), cy: Y(vals[at]), r: 4, fill: col(n) }, root);
      }
    }
    const cross = svg("line", { class: "crosshair", y1: m.top, y2: m.top + ih, visibility: "hidden" }, root);
    const hit = svg("rect", { x: m.left, y: m.top, width: iw, height: ih, fill: "transparent" }, root);
    hit.addEventListener("pointermove", (e) => {
      const r = root.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      let k = 0;
      js.forEach((d, i) => { if (Math.abs(X(d) - px) < Math.abs(X(js[k]) - px)) k = i; });
      cross.setAttribute("x1", X(js[k])); cross.setAttribute("x2", X(js[k])); cross.setAttribute("visibility", "visible");
      showTip(e, `J-${js[k]}`, names.map((n) => {
        const v = (c.courbe.series[n] || [])[k];
        return { color: col(n), label: meta(n).court, value: v === null || v === undefined ? "—" : prob(v) };
      }));
    });
    hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
    attachTable(box, ["Jours avant le 1er tour"].concat(names), js.map((d, i) => [`J-${d}`].concat(names.map((n) => {
      const v = (c.courbe.series[n] || [])[i];
      return v === null || v === undefined ? "—" : prob(v);
    }))).reverse());
  }

  function renderCompare() {
    document.querySelectorAll("[data-annee]").forEach((box) => {
      const list = P.comparaisons || (P.meme_stade && P.meme_stade.elections) || [];
      const c = list.find((x) => String(x.annee) === box.dataset.annee);
      if (c) drawStageCurve(box, c, +box.dataset.j);
    });
  }

  // ---------- page « Au même stade de la campagne » ----------
  let stageJ = null;
  function stageLabel(j) { return j === 1 ? "la veille du premier tour" : `à J-${j}`; }
  function renderStagePage() {
    const S = P.meme_stade;
    if (stageJ === null) stageJ = S.jours_avant;
    const sum = document.getElementById("stage-summary");
    const cards = document.getElementById("stage-cards");
    if (!sum || !cards) return;
    const key = String(stageJ);
    const known = S.elections.filter((c) => !c.indirect && c.etapes[key] && c.etapes[key].favori);
    const hits = known.filter((c) => c.etapes[key].issue === "gagne").length;
    sum.replaceChildren();
    const lead = stageLabel(stageJ);
    sum.append(document.createTextNode(`${lead[0].toUpperCase()}${lead.slice(1)}, le candidat en tête des prévisions a été élu `),
      el("strong", null, `${hits} fois sur ${known.length}`),
      document.createTextNode(" parmi les élections pour lesquelles des sondages existaient."));
    if (stageJ === S.jours_avant && S.actuel) {
      sum.append(document.createTextNode(` Aujourd'hui, ${S.actuel.nom} est en tête avec ${prob(S.actuel.p)} de chances.`));
    }

    cards.replaceChildren();
    const pending = [];
    for (const c of S.elections.slice().reverse()) {
      const card = el("article", { class: "card compare-card" });
      const snap = c.indirect ? null : c.etapes[key];
      const date = c.indirect ? c.date_premier_tour : snap.date;
      card.appendChild(el("div", { class: "eyebrow" }, `Présidentielle ${c.annee} · ${dateFr(date)}`));
      const metaOf = (n) => c.candidats[n] || { court: n, slot: 0 };
      const fact = (label, name, extra) => {
        const row = el("div");
        const dd = el("dd");
        dd.append(el("span", { class: "key-dot", style: `--c:var(--s${metaOf(name).slot || 0})` }), el("strong", null, name));
        if (extra) dd.append(document.createTextNode(" "), el("span", { class: "compare-p" }, extra));
        row.append(el("dt", null, label), dd);
        return row;
      };
      const dl = el("dl", { class: "compare-facts" });
      if (c.indirect || snap.absence) {
        card.appendChild(el("p", { class: "compare-absence" }, c.indirect ? c.note : snap.absence));
        dl.appendChild(fact("Élu", c.elu));
        card.appendChild(dl);
      } else {
        dl.appendChild(fact("En tête des prévisions", snap.favori, prob(snap.p_favori)));
        dl.appendChild(fact("Élu", c.elu, snap.issue === "gagne" ? "le même"
          : snap.p_elu === null ? "absent du scénario le plus sondé" : `${prob(snap.p_elu)} de chances alors`));
        card.appendChild(dl);
        const verdict = {
          gagne: "Le candidat en tête à ce stade l'a emporté.",
          absent: `${snap.favori} n'a finalement pas figuré parmi les candidats.`,
          battu: `${snap.favori} a perdu au second tour.`,
          elimine: `${snap.favori} a terminé à la ${snap.rang_favori}e place du premier tour.`,
        }[snap.issue];
        card.appendChild(el("p", { class: `verdict ${snap.issue === "gagne" ? "ok" : "ko"}` }, verdict));
      }
      const chart = el("div", { class: "compare-chart", "data-annee": String(c.annee), "data-j": key });
      card.appendChild(chart);
      if (!c.indirect) {
        const p = el("p", { class: "small", style: "margin:10px 0 0" });
        p.appendChild(el("a", { href: `../${c.annee}/` }, `Toute la campagne ${c.annee}`));
        card.appendChild(p);
      }
      cards.appendChild(card);
      pending.push([chart, c]);
    }
    // Les courbes après la mise en page complète de la grille (largeur finale des colonnes)
    for (const [chart, c] of pending) drawStageCurve(chart, c, stageJ);
  }
  document.querySelectorAll("[data-stage]").forEach((b, _, all) => b.addEventListener("click", () => {
    stageJ = +b.dataset.stage;
    all.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderStagePage();
  }));

  // ---------- page « Préoccupations des Français » ----------
  const SEASON = (iso) => {
    const d = new Date(iso + "T12:00:00");
    return `${d.getMonth() >= 7 ? "automne" : d.getMonth() >= 4 ? "été" : d.getMonth() >= 1 ? "printemps" : "hiver"} ${d.getFullYear()}`;
  };
  function renderConcernTimeline() {
    const Q = P.preoccupations;
    const box = document.getElementById("concerns-timeline");
    if (!box) return;
    box.replaceChildren();
    const keys = Q.series;
    const col = (k) => `var(--s${keys.indexOf(k) + 1})`;
    const legend = el("div", { class: "legend" });
    for (const k of keys) {
      const it = el("span", { class: "legend-item" });
      it.append(el("span", { class: "key-line", style: `--c:${col(k)}` }), document.createTextNode(Q.themes[k]));
      legend.appendChild(it);
    }
    box.appendChild(legend);
    const chart = el("div", { class: "chart" });
    box.appendChild(chart);
    const W = chart.clientWidth || 700, narrow = W < 560, H = narrow ? 260 : 320;
    const m = { top: 24, right: narrow ? 44 : 150, bottom: 28, left: 34 };
    const iw = W - m.left - m.right, ih = H - m.top - m.bottom;
    const T = (iso) => new Date(iso + "T12:00:00").getTime();
    const t0 = T("2005-01-01"), t1 = T(Q.elections[Q.elections.length - 1].date) + 30 * 864e5;
    const X = (iso) => m.left + ((T(iso) - t0) / (t1 - t0)) * iw;
    const ymax = 10 * Math.ceil(Math.max(...Q.vagues.flatMap((w) => keys.map((k) => w.themes[k] || 0))) / 10);
    const Y = (v) => m.top + ih - (v / ymax) * ih;
    const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img",
      "aria-label": "Évolution des préoccupations des Français depuis 2005, Eurobaromètre" }, chart);
    for (let v = 0; v <= ymax; v += 10) {
      svg("line", { class: v === 0 ? "baseline" : "gridline", x1: m.left, x2: m.left + iw, y1: Y(v), y2: Y(v) }, root);
      if (v % 20 === 0) svg("text", { class: "tick", x: m.left - 6, y: Y(v) + 4, "text-anchor": "end" }, root).textContent = v === ymax || v + 20 > ymax ? `${v} %` : String(v);
    }
    for (let y = 2005; y <= 2027; y += narrow ? 4 : 2) {
      const x = X(`${y}-01-01`);
      svg("text", { class: "tick", x, y: m.top + ih + 18, "text-anchor": "middle" }, root).textContent = String(y);
    }
    for (const e of Q.elections) {
      const x = X(e.date);
      svg("line", { class: "event", x1: x, x2: x, y1: m.top - 6, y2: m.top + ih }, root);
      const t = svg("text", { class: "tick", x, y: m.top - 10, "text-anchor": "middle" }, root);
      t.textContent = String(e.annee);
    }
    const ends = [];
    for (const k of keys) {
      let d = "", prev = false, last = null;
      for (const w of Q.vagues) {
        const v = w.themes[k];
        if (v === null || v === undefined) { prev = false; continue; }
        d += `${prev ? "L" : "M"}${X(w.date).toFixed(1)},${Y(v).toFixed(1)}`;
        prev = true; last = { k, x: X(w.date), y: Y(v), v };
      }
      svg("path", { class: "series", d, stroke: col(k) }, root);
      if (last) ends.push(last);
    }
    ends.sort((a, b) => a.y - b.y);
    let lastY = -Infinity;
    for (const e of ends) {
      svg("circle", { class: "end-dot", cx: e.x, cy: e.y, r: 4, fill: col(e.k) }, root);
      if (e.y - lastY >= 14 && !narrow) {
        svg("text", { class: "end-label", x: e.x + 8, y: e.y + 4 }, root).textContent = `${Q.themes[e.k].split(" ")[0]} ${nf0.format(e.v)} %`;
        lastY = e.y;
      }
    }
    const cross = svg("line", { class: "crosshair", y1: m.top, y2: m.top + ih, visibility: "hidden" }, root);
    const hit = svg("rect", { x: m.left, y: m.top, width: iw, height: ih, fill: "transparent" }, root);
    hit.addEventListener("pointermove", (e) => {
      const r = root.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      const w = Q.vagues.reduce((b, x) => Math.abs(X(x.date) - px) < Math.abs(X(b.date) - px) ? x : b);
      cross.setAttribute("x1", X(w.date)); cross.setAttribute("x2", X(w.date)); cross.setAttribute("visibility", "visible");
      showTip(e, `Eurobaromètre ${w.vague}, ${SEASON(w.date)}`, keys.filter((k) => w.themes[k] != null)
        .sort((a, b) => w.themes[b] - w.themes[a])
        .map((k) => ({ color: col(k), label: Q.themes[k], value: `${nf0.format(w.themes[k])} %` })));
    });
    hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
    attachTable(box, ["Vague", "Terrain"].concat(keys.map((k) => Q.themes[k])), Q.vagues.slice().reverse().map((w) =>
      [`EB ${w.vague}`, w.terrain ? `${dateFr(w.terrain[0])} – ${dateFr(w.terrain[1])}` : SEASON(w.date)]
        .concat(keys.map((k) => w.themes[k] == null ? "—" : `${nf0.format(w.themes[k])} %`))));
  }

  let concernJ = null;
  function pairRows(rows, max, who = "des propositions de l'élu") {
    const list = el("div", { class: "pairs" });
    for (const r of rows) {
      const row = el("div", { class: "pair-row", tabindex: "0" });
      row.appendChild(el("div", { class: "pair-label" }, r.label));
      const bars = el("div", { class: "pair-bars" });
      for (const [v, c] of [[r.fr, "var(--ink-2)"], [r.prog, "var(--s7)"]]) {
        if (v === undefined) continue;
        const line = el("div", { class: "pair-line" });
        line.append(el("div", { class: "bar", style: `width:${Math.max(0.4, (100 * (v || 0)) / max) * 0.82}%;--c:${c}` }),
          el("span", { class: "bar-value" }, v === null ? "—" : `${nf0.format(v)} %`));
        bars.appendChild(line);
      }
      row.appendChild(bars);
      hoverable(row, (e) => showTip(e, r.label, [
        ...(r.fr !== undefined ? [{ color: "var(--ink-2)", value: r.fr == null ? "—" : `${nf0.format(r.fr)} %`, label: "des Français citent ce problème" }] : []),
        ...(r.prog !== undefined ? [{ color: "var(--s7)", value: r.prog == null ? "—" : `${nf0.format(r.prog)} %`, label: who }] : []),
      ]));
      list.appendChild(row);
    }
    return list;
  }
  function renderConcernCards() {
    const Q = P.preoccupations;
    const box = document.getElementById("concerns-cards");
    const sum = document.getElementById("concerns-summary");
    if (!box) return;
    if (concernJ === null) concernJ = Q.jours_avant;
    const key = String(concernJ);
    const R = Q.resume[key];
    sum.replaceChildren();
    if (R && R.n) {
      const lead = concernJ === 1 ? "La veille du premier tour" : `À J-${concernJ}`;
      sum.append(document.createTextNode(`${lead}, les trois problèmes que les Français citaient le plus occupaient en moyenne `),
        el("strong", null, `${R.part_top3} % des propositions`),
        document.createTextNode(` du futur président (${R.n} élections, de 2007 à 2022). Score d'alignement moyen : ${R.alignement} sur 100.`));
    }
    box.replaceChildren();
    for (const c of Q.cartes) {
      const card = el("article", { class: "card compare-card" });
      const snap = c.etapes[key];
      const head = c.courante ? `Présidentielle ${c.annee} · campagne en cours` : `Présidentielle ${c.annee} · élu : ${c.elu}`;
      card.appendChild(el("div", { class: "eyebrow" }, head));
      const prog = c.programme ? c.programme.parts : null;
      if (!snap || snap.absence || c.note) {
        card.appendChild(el("p", { class: "compare-absence" }, c.note || snap.absence));
        if (prog) {
          card.appendChild(el("p", { class: "small muted" }, "Thèmes de la profession de foi de l'élu :"));
          const rows = Object.entries(prog).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, v]) => ({ label: Q.themes[k], prog: v }));
          card.appendChild(pairRows(rows, 10 * Math.ceil(Math.max(...rows.map((r) => r.prog)) / 10)));
        }
      } else {
        const t = snap.terrain;
        card.appendChild(el("p", { class: "small muted", style: "margin:0 0 10px" },
          `Eurobaromètre ${snap.vague}, ${SEASON(t ? t[1] : snap.date)}` + (t ? ` (terrain du ${dateFr(t[0])} au ${dateFr(t[1])})` : "")));
        const conc = snap.preoccupations;
        let keys = Object.keys(conc).sort((a, b) => conc[b] - conc[a]).slice(0, 6);
        if (prog) keys = keys.concat(Object.keys(prog).filter((k) => !keys.includes(k) && prog[k] >= 6).sort((a, b) => prog[b] - prog[a])).slice(0, 9);
        const rows = keys.map((k) => ({ label: Q.themes[k], fr: conc[k] ?? null, prog: prog ? (prog[k] ?? 0) : undefined }));
        const max = 10 * Math.ceil(Math.max(...rows.flatMap((r) => [r.fr || 0, r.prog || 0])) / 10);
        card.appendChild(pairRows(rows, max));
        if (prog) {
          const names = snap.top3.map((k) => Q.themes[k].toLowerCase()).join(", ");
          const p = el("p", { class: "verdict-text" });
          p.append(document.createTextNode(`Les trois premières préoccupations (${names}) représentent `),
            el("strong", null, `${snap.part_top3} %`), document.createTextNode(` des propositions de l'élu. Score d'alignement : ${snap.alignement} sur 100.`));
          card.appendChild(p);
        } else if (c.courante) {
          const p = el("p", { class: "small muted" }, "Dernière vague publiée en données ouvertes. La comparaison avec la profession de foi de l'élu sera ajoutée après l'élection ; en attendant, ");
          p.append(el("a", { href: "#candidats-2027" }, "le score provisoire des candidats"), document.createTextNode("."));
          card.appendChild(p);
        }
      }
      if (c.programme) {
        const d = el("details", { class: "data" });
        d.appendChild(el("summary", null, `Classement des ${c.programme.passages.length} passages de la profession de foi`));
        const ul = el("ul", { class: "passages" });
        for (const ps of c.programme.passages) {
          const li = el("li");
          li.append(el("span", { class: "tag" }, Q.themes[ps.theme]), document.createTextNode(` « ${ps.debut} » (${ps.mots} mots)`));
          ul.appendChild(li);
        }
        d.appendChild(ul);
        const src = el("p", { class: "small" });
        if (/^https?:\/\//.test(c.programme.source)) src.appendChild(el("a", { href: c.programme.source, rel: "noopener" }, "Lire la profession de foi"));
        d.appendChild(src);
        card.appendChild(d);
      }
      box.appendChild(card);
    }
  }
  // ---------- score d'alignement des candidats 2027 ----------
  function renderAlignment() {
    const Q = P.preoccupations;
    const A = Q.candidats;
    const box = document.getElementById("align-chart");
    if (!box || !A) return;
    box.replaceChildren();
    const ref = Q.resume[String(Q.jours_avant)];
    const elus = ref ? Object.entries(ref.elus).sort((a, b) => b[0] - a[0]) : [];
    const lo = Math.min(...elus.map((e) => e[1])), hi = Math.max(...elus.map((e) => e[1]));
    const x = (v) => `${v}%`;
    const col = (c) => `var(--s${c.slot || 0})`;

    const legend = el("div", { class: "legend" });
    const items = [["key-dot", "score d'alignement, sur 100"], ["key-range", "marge selon les passages retenus"]];
    if (elus.length) items.push(["key-band", `élus de ${elus[elus.length - 1][0]} à ${elus[0][0]}, au même stade`]);
    items.push(["key-uniform", `programme à parts égales sur tous les thèmes (${A.parts_egales})`]);
    for (const [k, t] of items) {
      const it = el("span", { class: "legend-item" });
      it.append(el("span", { class: k, style: "--c:var(--ink-2)" }), document.createTextNode(t));
      legend.appendChild(it);
    }
    box.appendChild(legend);

    const wrap = el("div", { class: "ranges" });
    for (const c of A.liste) {
      const row = el("div", { class: "range-row", tabindex: "0" });
      const plot = el("div", { class: "range-plot" });
      for (let t = 0; t <= 100; t += 20) plot.appendChild(el("div", { class: "range-grid", style: `left:${x(t)}` }));
      if (elus.length) plot.appendChild(el("div", { class: "range-band", style: `left:${x(lo)};width:${hi - lo}%` }));
      plot.appendChild(el("div", { class: "range-uniform", style: `left:${x(A.parts_egales)}` }));
      plot.appendChild(el("div", { class: "range-line", style: `left:${x(c.fourchette[0])};width:${c.fourchette[1] - c.fourchette[0]}%;--c:${col(c)}` }));
      plot.appendChild(el("div", { class: "range-dot", style: `left:${x(c.alignement)};--c:${col(c)}` }));
      plot.appendChild(el("span", { class: "range-value", style: `left:calc(${x(c.fourchette[1])} + 8px)` }, String(c.alignement)));
      row.append(el("div", { class: "bar-label" }, c.court), plot);
      hoverable(row, (e) => showTip(e, c.candidat, [
        { color: col(c), value: `${c.alignement} / 100`, label: "score d'alignement" },
        { color: col(c), value: `± ${c.marge}`, label: "selon les passages retenus" },
        { color: col(c), value: `${c.part_top3} %`, label: "de ses propositions sur les 3 premières préoccupations" },
      ]));
      wrap.appendChild(row);
    }
    if (elus.length) {
      const row = el("div", { class: "range-row ref-row", tabindex: "0" });
      const plot = el("div", { class: "range-plot" });
      for (let t = 0; t <= 100; t += 20) plot.appendChild(el("div", { class: "range-grid", style: `left:${x(t)}` }));
      plot.appendChild(el("div", { class: "range-band", style: `left:${x(lo)};width:${hi - lo}%` }));
      plot.appendChild(el("div", { class: "range-uniform", style: `left:${x(A.parts_egales)}` }));
      for (const [y, v] of elus) plot.appendChild(el("div", { class: "range-result", style: `left:${x(v)}` }));
      row.append(el("div", { class: "bar-label muted" }, "Élus, au même stade"), plot);
      hoverable(row, (e) => showTip(e, `Élus, à J-${Q.jours_avant}`, elus.map(([y, v]) => {
        const card = Q.cartes.find((c) => String(c.annee) === y);
        return { color: "var(--ink)", value: `${v} / 100`, label: `${card ? card.elu : ""} (${y})` };
      })));
      wrap.appendChild(row);
    }
    const axis = el("div", { class: "range-axis" });
    const ticks = el("div", { class: "range-ticks" });
    for (let t = 0; t <= 100; t += 20) ticks.appendChild(el("span", { style: `left:${x(t)}${t === 100 ? ";transform:translateX(-100%)" : ""}` }, String(t)));
    axis.append(el("div"), ticks);
    wrap.appendChild(axis);
    box.appendChild(wrap);
    attachTable(box, ["Candidat", "Score", "Marge", "Part des 3 premières préoccupations"],
      A.liste.map((c) => [c.candidat, `${c.alignement} / 100`, `± ${c.marge}`, `${c.part_top3} %`])
        .concat(elus.map(([y, v]) => [`${(Q.cartes.find((c) => String(c.annee) === y) || {}).elu} (élu en ${y}, à J-${Q.jours_avant})`, `${v} / 100`, "—", "—"])));

    const cards = document.getElementById("align-cards");
    cards.replaceChildren();
    const conc = A.preoccupations;
    const top = Object.keys(conc).sort((a, b) => conc[b] - conc[a]);
    for (const c of A.liste) {
      const card = el("article", { class: "card compare-card" });
      const eb = el("div", { class: "eyebrow align-head" });
      eb.append(el("span", { class: "key-dot", style: `--c:${col(c)}` }), document.createTextNode(c.candidat));
      card.appendChild(eb);
      const score = el("p", { class: "align-score" });
      score.append(el("strong", null, String(c.alignement)), el("span", null, ` / 100 · ± ${c.marge}`));
      card.appendChild(score);
      const names = c.top3.map((k) => Q.themes[k].toLowerCase()).join(", ");
      const v = el("p", { class: "verdict-text", style: "margin:0 0 12px" });
      v.append(document.createTextNode(`Les trois premières préoccupations (${names}) occupent `),
        el("strong", null, `${c.part_top3} %`), document.createTextNode(" de ses propositions."));
      card.appendChild(v);
      let keys = top.slice(0, 6);
      keys = keys.concat(Object.keys(c.parts).filter((k) => !keys.includes(k) && c.parts[k] >= 6).sort((a, b) => c.parts[b] - c.parts[a])).slice(0, 9);
      const rows = keys.map((k) => ({ label: Q.themes[k], fr: conc[k] ?? null, prog: c.parts[k] ?? 0 }));
      const max = 10 * Math.ceil(Math.max(...rows.flatMap((r) => [r.fr || 0, r.prog || 0])) / 10);
      card.appendChild(pairRows(rows, max, "des propositions du candidat"));
      card.appendChild(el("p", { class: "small muted", style: "margin:12px 0 0" }, c.remarque));
      const d = el("details", { class: "data" });
      d.appendChild(el("summary", null, `Textes retenus et classement des ${c.passages.length} passages`));
      const docs = el("ul", { class: "small" });
      for (const doc of c.documents) docs.appendChild(el("li")).appendChild(el("a", { href: doc.url, rel: "noopener" }, doc.titre));
      d.append(docs, el("p", { class: "small muted" }, `Consultés le ${dateFr(c.collecte)} · ${c.mots} mots analysés.`));
      const ul = el("ul", { class: "passages" });
      for (const ps of c.passages) {
        const li = el("li");
        li.append(el("span", { class: "tag" }, Q.themes[ps.theme]), document.createTextNode(` « ${ps.debut} » (${ps.mots} mots)`));
        ul.appendChild(li);
      }
      d.appendChild(ul);
      card.appendChild(d);
      cards.appendChild(card);
    }
  }
  document.querySelectorAll("[data-cstage]").forEach((b, _, all) => b.addEventListener("click", () => {
    concernJ = +b.dataset.cstage;
    all.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderConcernCards();
  }));

  // ---------- sondages retenus ----------
  function renderRetained(id) {
    const box = document.getElementById(id);
    if (!box) return;
    box.replaceChildren();
    const wrap = el("div", { class: "table-wrap" });
    const t = el("table");
    const tr = el("tr");
    [["Institut"], ["Fin de l'enquête"], ["Hypothèses", "n"], ["Poids", "n"]].forEach(([h, c]) => tr.appendChild(el("th", c ? { class: c } : null, h)));
    t.appendChild(el("thead")).appendChild(tr);
    const tb = el("tbody");
    for (const s of scenario().sondages_retenus) {
      const row = el("tr");
      const name = el("td");
      if (s.source && /^https?:\/\//.test(s.source)) {
        const a = el("a", { href: s.source, rel: "noopener" }, s.sondeur);
        name.appendChild(a);
      } else name.textContent = s.sondeur;
      row.append(name, el("td", null, dateFr(s.fin)), el("td", { class: "n" }, String(s.lignes)),
        el("td", { class: "n" }, nf2.format(s.poids)));
      tb.appendChild(row);
    }
    t.appendChild(tb);
    wrap.appendChild(t);
    box.appendChild(wrap);
  }

  // ---------- composez votre scénario ----------
  let composerNote = "";
  function renderComposer() {
    const box = document.getElementById("composer");
    if (!box || !P.scenarios || P.scenarios.length < 2) return;
    box.replaceChildren();
    const keys = P.scenarios.map((s) => new Set(s.cle));
    const all = [...new Set(P.scenarios.flatMap((s) => s.cle))];
    const variable = all.filter((c) => !keys.every((k) => k.has(c)))
      .sort((a, b) => ((C[a] || {}).ordre ?? 99) - ((C[b] || {}).ordre ?? 99) || short(a).localeCompare(short(b)));
    const current = keys[scenarioIndex];
    for (const c of variable) {
      const b = el("button", { class: "chip cand", type: "button", "aria-pressed": String(current.has(c)) }, short(c));
      b.addEventListener("click", () => {
        const want = new Set(current);
        if (want.has(c)) want.delete(c); else want.add(c);
        let best = 0, bestD = Infinity;
        keys.forEach((k, i) => {
          const d = [...want].filter((x) => !k.has(x)).length + [...k].filter((x) => !want.has(x)).length;
          if (d < bestD) { bestD = d; best = i; }
        });
        composerNote = bestD === 0 ? "" : "Aucun sondage récent n'a testé exactement cette liste : voici le scénario sondé le plus proche.";
        scenarioIndex = best;
        renderAll();
      });
      box.appendChild(b);
    }
    if (scenarioIndex !== 0) {
      const r = el("button", { class: "chip reset", type: "button" }, "Revenir au scénario le plus sondé");
      r.addEventListener("click", () => { scenarioIndex = 0; composerNote = ""; renderAll(); });
      box.appendChild(r);
    }
  }

  // ---------- questions de campagne ----------
  function renderQuestions() {
    const box = document.getElementById("questions");
    if (!box) return;
    box.replaceChildren();
    for (const q of scenario().questions || []) {
      const t = el("div", { class: "tile" });
      t.append(el("p", { class: "tile-q" }, q.question), el("p", { class: "tile-v" }, prob(q.p)), el("p", { class: "tile-d" }, q.detail));
      box.appendChild(t);
    }
  }

  // ---------- commandes ----------
  function renderScenarioNote() {
    const n = document.getElementById("scenario-note");
    if (!n) return;
    const sc = scenario();
    n.textContent = (composerNote ? composerNote + " " : "") + `${sc.libelle}. ${sc.n_hypotheses} hypothèse${sc.n_hypotheses > 1 ? "s" : ""} de sondage correspondent à ce scénario, `
      + `publiées par ${sc.instituts.length} institut${sc.instituts.length > 1 ? "s" : ""} `
      + `(${sc.instituts.join(", ")}) au cours des deux derniers mois.`;
  }
  function renderAll() {
    renderBars("victoire", "p_victoire");
    renderBars("qualif", "p_qualifie");
    renderRanges("premier-tour");
    renderDuels("duels");
    renderScenarioNote();
    renderRetained("retenus");
    renderComposer();
    renderQuestions();
  }

  const chips = document.querySelectorAll("[data-scenario]");
  chips.forEach((b) => b.addEventListener("click", () => {
    scenarioIndex = +b.dataset.scenario;
    chips.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderAll();
  }));
  const modes = document.querySelectorAll("[data-evo]");
  modes.forEach((b) => b.addEventListener("click", () => {
    evoMode = b.dataset.evo;
    modes.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderEvolution("evolution");
  }));

  if (P.scenarios) {
    renderAll();
    renderEvolution("evolution");
  }
  if (P.comparaisons) renderCompare();
  if (P.meme_stade) renderStagePage();
  if (P.preoccupations) {
    renderConcernTimeline(); renderConcernCards(); renderAlignment();
    // Les cartes sont dessinées après le chargement : on rejoint l'ancre une fois la page en place
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target) target.scrollIntoView();
  }
  let lastW = 0, timer;
  new ResizeObserver(() => {
    const w = document.querySelector("main")?.clientWidth || 0;
    if (Math.abs(w - lastW) < 8) return;
    lastW = w;
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (P.scenarios) { renderEvolution("evolution"); renderRanges("premier-tour"); }
      if (P.comparaisons) renderCompare();
      if (P.meme_stade) renderStagePage();
      if (P.preoccupations) renderConcernTimeline();
    }, 120);
  }).observe(document.body);
})();
