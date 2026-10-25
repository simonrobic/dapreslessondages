/* SPDX-License-Identifier: AGPL-3.0-or-later
   D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md. */
/* Consentement : Screeb (questionnaires, analyse d'usage) n'est chargé qu'après
   l'accord explicite du visiteur. Le choix est gardé six mois dans le navigateur,
   puis redemandé ; le lien « Cookies » du pied de page permet de le changer. */
(function () {
  "use strict";

  var KEY = "dals-consentement";
  var MAX_AGE = 182 * 24 * 3600 * 1000;
  var CHANNEL = "c51b7722-05b5-40fd-bb7c-3d964bbded1d";
  var banner = document.getElementById("consent");

  function read() {
    try {
      var c = JSON.parse(localStorage.getItem(KEY));
      return c && Date.now() - c.t < MAX_AGE ? c : null;
    } catch (e) {
      return null;
    }
  }
  function save(ok) {
    try { localStorage.setItem(KEY, JSON.stringify({ screeb: ok, t: Date.now() })); } catch (e) { /* navigation privée */ }
  }

  function loadScreeb() {
    if (window.$screeb) return;
    (function (s, c, r, ee, b) {
      s["ScreebObject"] = r;
      s[r] = s[r] || function () {
        var d = arguments;
        return new Promise(function (a, b) {
          (s[r].q = s[r].q || []).push({ v: 1, args: d, ok: a, ko: b });
        });
      };
      b = c.createElement("script");
      b.type = "text/javascript";
      b.id = r;
      b.src = ee;
      b.async = 1;
      c.getElementsByTagName("head")[0].appendChild(b);
    })(window, document, "$screeb", "https://t.screeb.app/tag.js");

    window.$screeb("init", CHANNEL);
  }

  function show(visible) {
    if (banner) banner.hidden = !visible;
  }

  var choice = read();
  if (choice && choice.screeb) loadScreeb();
  if (!choice) show(true);

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-consent]");
    if (!t) return;
    var value = t.getAttribute("data-consent");
    if (value === "ouvrir") {
      show(true);
      if (banner) banner.querySelector("button").focus();
      return;
    }
    var ok = value === "oui";
    save(ok);
    show(false);
    if (ok) loadScreeb();
    else if (window.$screeb) location.reload(); // accord retiré : la page repart sans Screeb
  });
})();
