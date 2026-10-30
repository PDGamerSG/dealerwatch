/* DealerWatch investigator UI.
 * Vanilla JS, no dependencies, no external requests. All DOM is built with
 * createElement / createElementNS and textContent: data (transcripts, names,
 * summaries) is never parsed as HTML.
 */
"use strict";
(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);
  const nfInt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
  const nf2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const MIN = 60000;

  const CHAIN_LABELS = {
    order: "Fund order", pre_trade: "Pre-order trades", post_trade: "Post-order trades",
    profit: "Profit", pattern: "Repeat pattern", link_path: "Link path",
    call_in_window: "Call in window", leak_cue: "Leak cue", clause: "Clause mapped",
  };
  const ACTION_LABELS = {
    start_review: "Start review", request_info: "Request info",
    approve_escalation: "Approve escalation", dismiss: "Dismiss",
  };
  const TERMINAL = new Set(["ESCALATED", "CLOSED"]);
  const CITE_RE = /\[([otuacl]):([^\]\s]+)\]/g;
  const INJECTION_RE = /ignore (all |any )?(previous|prior|above|earlier) instructions|mark (this|it) as no violation|disregard (all |the )?(rules|instructions)|system prompt/i;
  const REVIEWER_KEY = "dw.reviewer";

  const state = {
    cases: [], selectedId: null, detail: null, activeCall: null,
    uttRows: new Map(), uttData: new Map(), cited: new Set(),
    tab: "cases", busy: false,
    ledgerOffset: 0, ledgerLimit: 100, ledgerCount: 0, ledgerBase: 1, verify: null, expanded: new Set(),
    evalLoaded: false, session: null, sessionBusy: false,
    queueRequest: 0, queueLoading: false, queueError: "", queueTotal: 0, queueParams: "",
    decisionBusy: false, decisionAttempt: null, dataBusy: false,
    runs: [], activeRun: null, runTimer: 0, runPollErrors: 0, runStarting: false, runsRequest: 0,
  };
  const canRead = () => Boolean(state.session && (!state.session.auth_required || state.session.authenticated));
  const canAdmin = () => canRead() && state.session.role === "admin";
  const runInProgress = () => state.activeRun && ["QUEUED", "RUNNING"].includes(state.activeRun.status);

  // ---------- DOM helpers ----------
  function setProps(node, props) {
    if (!props) return;
    for (const [key, value] of Object.entries(props)) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "text") node.textContent = String(value);
      else if (key === "dataset") Object.assign(node.dataset, value);
      else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : String(value));
    }
  }
  function addKids(node, kids) {
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false) continue;
      node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
  }
  function h(tag, props, ...kids) {
    const node = document.createElement(tag);
    setProps(node, props);
    addKids(node, kids);
    return node;
  }
  function s(tag, props, ...kids) {
    const node = document.createElementNS(SVG_NS, tag);
    setProps(node, props);
    addKids(node, kids);
    return node;
  }
  function restartClass(node, cls, ms) {
    node.classList.remove(cls);
    void node.getBoundingClientRect();
    node.classList.add(cls);
    if (ms) setTimeout(() => node.classList.remove(cls), ms);
  }
  const trunc = (text, max) => (text.length > max ? text.slice(0, Math.max(1, max - 1)) + "…" : text);

  // ---------- formatting ----------
  const fmtInr = (v) => (v < 0 ? "-" : "") + "₹" + nfInt.format(Math.abs(Math.round(v)));
  const fmtQty = (v) => nfInt.format(v);
  const fmtPrice = (v) => nf2.format(v);
  const hhmm = (iso) => String(iso || "").slice(11, 16);
  const dateTime = (iso) => String(iso || "").replace("T", " ").slice(0, 16);
  const toMs = (iso) => Date.parse(iso); // naive ISO -> local; only differences and HH:MM are used
  const minutesFrom = (fromIso, toIso) => Math.round((toMs(toIso) - toMs(fromIso)) / MIN);
  function mmss(ms) {
    const t = Math.max(0, Math.floor(ms / 1000));
    return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0");
  }
  function duration(sec) {
    const m = Math.floor(sec / 60), r = sec % 60;
    return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`;
  }
  const label = (id) => (state.detail && state.detail.node_labels && state.detail.node_labels[id]) || id;
  const recBadge = (rec) => h("span", { class: `badge rec-${rec}`, text: rec });
  const statusBadge = (st) => h("span", { class: `badge st-${st}`, text: String(st).replace(/_/g, " ") });

  // ---------- API ----------
  function responseError(res, data) {
    let detail = res.statusText || `HTTP ${res.status}`;
    if (data && data.detail) {
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((item) => item.msg || item.message || "Invalid input").join("; ");
      else if (Array.isArray(data.detail.issues)) detail = "Dataset validation failed. Review the issues below.";
      else detail = JSON.stringify(data.detail);
    }
    const err = new Error(detail);
    err.status = res.status;
    err.data = data;
    return err;
  }
  async function api(path, opts = {}) {
    const init = { method: opts.method || "GET", credentials: "same-origin", headers: { Accept: "application/json", ...opts.headers } };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, init);
    const text = await res.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch { data = text; }
    }
    if (!res.ok) {
      if (res.status === 401 && path !== "/api/session" && state.session && state.session.auth_required) {
        state.session.authenticated = false;
        clearTimeout(state.runTimer);
        $("session-status").textContent = "Your session has ended. Sign in to continue.";
        applyAccess();
      }
      throw responseError(res, data);
    }
    return opts.withResponse ? { data, response: res } : data;
  }
  async function download(path, filename) {
    try {
      const res = await fetch(path, { credentials: "same-origin" });
      if (!res.ok) {
        let data = null;
        try { data = await res.json(); } catch { /* use status text */ }
        throw responseError(res, data);
      }
      const url = URL.createObjectURL(await res.blob());
      const link = h("a", { href: url, download: filename });
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      toast(`Download failed: ${e.message}`, true);
    }
  }
  function actionKey() {
    if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  }

  // ---------- overlays ----------
  let toastTimer = 0;
  function toast(message, isError = false) {
    const node = $("toast");
    node.textContent = message;
    node.className = "toast" + (isError ? " error" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.add("hidden"), isError ? 6500 : 3500);
  }
  function confirmDialog(title, text, okLabel) {
    const dlg = $("confirm");
    $("confirm-title").textContent = title;
    $("confirm-text").textContent = text;
    $("confirm-ok").textContent = okLabel || "Confirm";
    return new Promise((resolve) => {
      dlg.addEventListener("close", () => resolve(dlg.returnValue === "ok"), { once: true });
      dlg.returnValue = "";
      dlg.showModal();
    });
  }
  function placeTip(evt) {
    const tip = $("tooltip");
    const pad = 14;
    const rect = tip.getBoundingClientRect();
    let x = evt.clientX + pad, y = evt.clientY + pad;
    if (x + rect.width > window.innerWidth - 8) x = evt.clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = evt.clientY - rect.height - pad;
    tip.style.left = `${Math.max(4, x)}px`;
    tip.style.top = `${Math.max(4, y)}px`;
  }
  function showTip(evt, text) {
    const tip = $("tooltip");
    tip.textContent = text;
    tip.classList.remove("hidden");
    placeTip(evt);
  }
  const hideTip = () => $("tooltip").classList.add("hidden");
  function tipOn(node, text) {
    node.addEventListener("mouseenter", (e) => showTip(e, text));
    node.addEventListener("mousemove", placeTip);
    node.addEventListener("mouseleave", hideTip);
  }

  // ---------- routing ----------
  function setHash(hash) {
    if (location.hash !== hash) history.replaceState(null, "", hash);
  }
  function showTab(tab, updateHash = true, refresh = true) {
    state.tab = tab;
    for (const btn of document.querySelectorAll(".tab")) {
      const on = btn.dataset.tab === tab;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
      btn.tabIndex = on ? 0 : -1;
    }
    for (const view of document.querySelectorAll(".view")) view.classList.toggle("active", view.id === `view-${tab}`);
    hideTip();
    if (canRead() && refresh) {
      if (tab === "cases" && state.detail) renderCharts();
      if (tab === "overview") loadOverview();
      if (tab === "data") loadDataReport();
      if (tab === "runs") loadRuns();
      if (tab === "ledger") loadLedger().catch((e) => toast(`Ledger: ${e.message}`, true));
      if (tab === "eval" && !state.evalLoaded) loadEval(false);
    }
    if (updateHash) setHash(tab === "cases" ? (state.selectedId ? `#/cases/${state.selectedId}` : "#/cases") : `#/${tab}`);
  }

  // ---------- health / busy ----------
  async function loadHealth() {
    try {
      const hl = await api("/api/health");
      $("env-pill").textContent = `LLM ${hl.llm} · ASR ${hl.asr} · ${hl.cases} cases`;
    } catch (e) {
      $("env-pill").textContent = "API unavailable";
    }
  }
  function setBusy(busy, message) {
    state.busy = busy;
    applyAccess();
    if (busy) $("env-pill").textContent = message || "Working…";
    if (state.detail) renderDecisionBar(state.detail);
  }

  // ---------- session ----------
  function applyAccess() {
    const session = state.session;
    const allowed = canRead(), admin = canAdmin();
    $("main-views").classList.toggle("hidden", !allowed);
    $("login-form").classList.toggle("hidden", !session || !session.auth_required || session.authenticated);
    $("logout-btn").classList.toggle("hidden", !session || !session.auth_required || !session.authenticated);
    $("login-btn").disabled = state.sessionBusy;
    $("logout-btn").disabled = state.sessionBusy;
    for (const node of document.querySelectorAll("[data-admin]")) {
      node.disabled = !admin || state.sessionBusy || state.busy || state.dataBusy || state.runStarting || Boolean(runInProgress());
    }
    for (const node of document.querySelectorAll("[data-admin-panel]")) node.classList.toggle("hidden", !admin);
    for (const node of document.querySelectorAll("[data-demo]")) node.classList.toggle("hidden", !admin || !session.demo_enabled);
    $("reviewer").readOnly = Boolean(session && session.auth_required);
    if (session && session.auth_required && session.reviewer) $("reviewer").value = session.reviewer;
    $("run-btn").textContent = state.runStarting ? "Starting pipeline…" : runInProgress() ? "Pipeline running…" : "Re-run pipeline";
    if (state.detail) renderDecisionBar(state.detail);
  }
  async function loadSession() {
    $("session-error").textContent = "";
    $("session-retry").classList.add("hidden");
    try {
      state.session = await api("/api/session");
      const session = state.session;
      $("session-status").textContent = !session.auth_required
        ? (session.public_role ? `Open access · ${session.public_role}` : "Local · administrator")
        : session.authenticated ? `${session.reviewer || session.role} · ${session.role}`
          : "Sign in to open the investigations";
      applyAccess();
      return canRead();
    } catch (e) {
      state.session = null;
      $("session-status").textContent = "Cannot connect to DealerWatch.";
      $("session-error").textContent = e.message;
      $("session-retry").classList.remove("hidden");
      applyAccess();
      return false;
    }
  }
  async function signIn(event) {
    event.preventDefault();
    if (state.sessionBusy) return;
    state.sessionBusy = true;
    $("session-error").textContent = "";
    applyAccess();
    try {
      await api("/api/session", { method: "POST", body: { token: $("session-token").value } });
      if (await loadSession()) {
        await loadWorkspace();
        document.querySelector(`.tab[data-tab="${state.tab}"]`).focus();
      }
    } catch (e) {
      $("session-error").textContent = `Sign in failed: ${e.message}`;
      $("session-token").focus();
    } finally {
      $("session-token").value = "";
      state.sessionBusy = false;
      applyAccess();
    }
  }
  async function signOut() {
    if (state.sessionBusy) return;
    state.sessionBusy = true;
    applyAccess();
    try {
      await api("/api/session", { method: "DELETE" });
      clearTimeout(state.runTimer);
      state.activeRun = null;
      state.evalLoaded = false;
      state.cases = [];
      state.queueTotal = 0;
      state.queueLoading = false;
      state.queueRequest += 1;
      state.runsRequest += 1;
      state.verify = null;
      state.decisionAttempt = null;
      clearCase();
      renderQueue();
      $("note").value = "";
      $("dataset-json").value = "";
      $("dataset-file").value = "";
      for (const id of ["overview-body", "data-report", "data-candidate-report", "run-history", "run-progress", "ledger-rows", "eval-body"]) $(id).replaceChildren();
      await loadSession();
      if (!canRead()) $("session-token").focus();
    } catch (e) {
      $("session-error").textContent = `Sign out failed: ${e.message}`;
    } finally {
      state.sessionBusy = false;
      applyAccess();
    }
  }

  // ---------- queue ----------
  function filteredCases() {
    return state.cases;
  }
  function queueParams() {
    const params = new URLSearchParams();
    for (const [name, id] of [["q", "filter-query"], ["scrip", "filter-scrip"], ["dealer_id", "filter-dealer"],
      ["recommendation", "filter-rec"], ["status", "filter-status"]]) {
      const value = $(id).value.trim();
      if (value) params.set(name, value);
    }
    return params.toString();
  }
  function queueItem(c) {
    return h("li", { class: "queue-item", role: "button", tabindex: 0, "aria-label": `Open case ${c.case_id}, ${c.scrip}, ${c.status}`,
      title: c.case_id, dataset: { caseId: c.case_id }, onclick: () => selectCase(c.case_id), onkeydown: (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectCase(c.case_id); }
      } },
      h("div", { class: "qi-row" },
        h("span", { class: "qi-main" }, c.scrip, " ", h("span", { class: "qi-who", text: `${c.account_id} ${c.holder_name}` })),
        recBadge(c.recommendation)),
      h("div", { class: "qi-row" },
        h("span", { class: "qi-sub", text: `${c.dealer_id} · score ${c.score.toFixed(2)} · ${fmtInr(c.profit_inr)}` }),
        statusBadge(c.status)));
  }
  function renderQueue() {
    const list = $("queue-list");
    const items = filteredCases();
    list.replaceChildren(...items.map(queueItem));
    if (!items.length) {
      list.append(h("li", { class: "queue-empty", text: state.queueError || (state.queueLoading ? "Loading cases…"
        : state.queueParams ? "No cases match the filters."
          : "No cases yet. Import a dataset, then click Re-run pipeline.") }));
    }
    $("queue-count").textContent = state.queueLoading ? "(loading…)" : `(${nfInt.format(state.queueTotal)})`;
    $("queue-list").setAttribute("aria-busy", String(state.queueLoading));
    markSelected(false);
  }
  function markSelected(scroll = true) {
    for (const li of $("queue-list").querySelectorAll(".queue-item")) {
      const on = li.dataset.caseId === state.selectedId;
      li.classList.toggle("selected", on);
      li.setAttribute("aria-current", on ? "true" : "false");
      if (on && scroll) li.scrollIntoView({ block: "nearest" });
    }
  }
  function moveSelection(step) {
    const list = filteredCases();
    if (!list.length) return;
    let i = list.findIndex((c) => c.case_id === state.selectedId);
    i = i < 0 ? 0 : Math.max(0, Math.min(list.length - 1, i + step));
    if (list[i].case_id !== state.selectedId) selectCase(list[i].case_id);
  }
  async function loadCases(preferId) {
    const request = ++state.queueRequest;
    const params = queueParams();
    state.queueLoading = true;
    state.queueError = "";
    renderQueue();
    try {
      const result = await api(`/api/cases${params ? `?${params}` : ""}`, { withResponse: true });
      if (request !== state.queueRequest || !canRead()) return;
      state.cases = result.data;
      const total = Number(result.response.headers.get("X-Total-Count"));
      state.queueTotal = Number.isFinite(total) && result.response.headers.has("X-Total-Count") ? total : state.cases.length;
      state.queueParams = params;
    } catch (e) {
      if (request !== state.queueRequest || !canRead()) return;
      state.cases = [];
      state.queueTotal = 0;
      state.queueError = `Could not load cases: ${e.message}. Use Search to retry.`;
      toast(`Could not load cases: ${e.message}`, true);
    }
    if (request !== state.queueRequest) return;
    state.queueLoading = false;
    renderQueue();
    const pick = state.cases.some((c) => c.case_id === preferId)
      ? preferId : (filteredCases()[0] || state.cases[0] || {}).case_id;
    if (pick) await selectCase(pick, state.tab !== "cases");
    else clearCase(state.queueError || "No cases to display. Update the filters or run the pipeline.");
  }

  // ---------- case view ----------
  function clearCase(message = "Select a case from the alert queue.") {
    for (const audio of $("call-audio").querySelectorAll("audio")) audio.pause();
    state.selectedId = null;
    state.detail = null;
    $("case-body").classList.add("hidden");
    $("case-empty").classList.remove("hidden");
    $("case-empty").textContent = message;
    $("decision-bar").classList.add("hidden");
  }
  async function selectCase(id, keepHash = false) {
    if (!canRead()) return;
    for (const audio of $("call-audio").querySelectorAll("audio")) audio.pause();
    state.selectedId = id;
    state.detail = null;
    $("case-body").classList.add("hidden");
    $("decision-bar").classList.add("hidden");
    $("case-empty").classList.remove("hidden");
    $("case-empty").textContent = `Loading ${id}…`;
    markSelected();
    if (!keepHash) setHash(`#/cases/${id}`);
    let detail;
    try {
      detail = await api(`/api/cases/${encodeURIComponent(id)}`);
    } catch (e) {
      if (state.selectedId !== id) return;
      $("case-empty").textContent = `Could not load ${id}: ${e.message}. Select the case to retry.`;
      toast(`Could not load ${id}: ${e.message}`, true);
      return;
    }
    if (state.selectedId !== id || !canRead()) return; // a newer selection won
    state.detail = detail;
    const cueCalls = detail.cues.map((c) => c.call_id);
    const best = detail.call_details.find((c) => cueCalls.includes(c.call_id)) || detail.call_details[0];
    state.activeCall = best ? best.call_id : null;
    state.cited = citedUtterances(detail);
    renderCase();
    $("case-scroll").scrollTop = 0;
  }
  function citedUtterances(d) {
    const ids = new Set();
    for (const cue of d.cues) for (const u of cue.utterance_ids) ids.add(u);
    for (const m of d.summary.matchAll(CITE_RE)) if (m[1] === "u") ids.add(m[2]);
    for (const link of d.chain) for (const raw of link.evidence_ids) {
      const c = parseCite(raw);
      if (c.kind === "u") ids.add(c.id);
    }
    return ids;
  }
  function renderCase() {
    const d = state.detail;
    $("case-empty").classList.add("hidden");
    $("case-body").classList.remove("hidden");
    renderHeader(d);
    renderChain(d);
    renderSummary(d);
    renderClauses(d);
    renderCalls(d);
    renderHistory(d);
    renderDecisionBar(d);
    renderCharts();
  }
  function renderCharts() {
    if (!state.detail) return;
    renderTimeline(state.detail);
    renderGraph(state.detail);
  }
  function kpi(name, value, cls) {
    return h("div", { class: "kpi" }, h("div", { class: "kpi-label", text: name }),
      h("div", { class: `kpi-value ${cls || ""}`, text: value, title: value }));
  }
  function renderHeader(d) {
    const c = d.candidate, o = d.order, a = d.account, dl = d.dealer;
    const okCount = d.chain.filter((x) => x.ok).length;
    $("case-header").replaceChildren(
      h("div", { class: "ch-top" },
        h("span", { class: "ch-title" }, `${c.scrip} · front-running alert`, h("span", { class: "mono", text: d.case_id })),
        recBadge(d.recommendation), statusBadge(d.status)),
      h("div", { class: "ch-line" }, "Fund order ",
        h("strong", { text: `${o.order_id} ${o.side} ${fmtQty(o.qty)} ${o.scrip}` }),
        ` · ${o.scheme} · received ${dateTime(o.order_time)} · executed ${hhmm(o.exec_start)}–${hhmm(o.exec_end)}`),
      h("div", { class: "ch-line" }, "Account ",
        h("strong", { text: `${a.account_id} ${a.holder_name}` }), ` (PAN ${a.pan_masked}) · Dealer `,
        h("strong", { text: `${dl.dealer_id} ${dl.name}` }), ` · detected ${dateTime(d.created_at)}`),
      h("div", { class: "kpis" },
        kpi("Score", c.score.toFixed(2)),
        kpi("Profit", fmtInr(c.profit_inr), c.profit_inr > 0 ? "pos" : ""),
        kpi("Pre / post qty", `${fmtQty(c.pre_qty)} / ${fmtQty(c.post_qty)}`),
        kpi("Lead time", `${Math.round(c.minutes_before)} min`),
        kpi("Orders sandwiched", String(c.hit_count)),
        kpi("Evidence chain", `${okCount} / ${d.chain.length}`)));
  }

  // ---------- overview / datasets ----------
  function countGroup(title, groups, withProfit = false) {
    const entries = Object.entries(groups || {});
    if (!entries.length) return section(title, h("p", { class: "muted", text: "No cases yet." }));
    return section(title, table(withProfit ? ["Group", "Cases", "Profit (INR)"] : ["Group", "Cases"], entries.map(([name, value]) => {
      const count = typeof value === "number" ? value : value.count;
      return cellsRow(withProfit ? [name, count, fmtInr(value.profit_inr || 0)] : [name.replace(/_/g, " "), count]);
    })));
  }
  async function loadOverview() {
    const body = $("overview-body");
    body.replaceChildren(h("p", { class: "muted", text: "Loading overview…" }));
    $("overview-refresh").disabled = true;
    try {
      const data = await api("/api/dashboard");
      if (!canRead()) return;
      const latest = data.latest_run;
      body.replaceChildren(
        h("div", { class: "kpis overview-kpis" }, kpi("Cases", fmtQty(data.cases || 0)),
          kpi("Estimated profit across case versions", fmtInr(data.total_profit_inr || 0)),
          kpi("Latest run", latest ? latest.status || "Available" : "None")),
        h("div", { class: "basic-grid" }, countGroup("Recommendations", data.by_recommendation), countGroup("Reviewer status", data.by_status),
          countGroup("By scrip", data.by_scrip, true), countGroup("By dealer", data.by_dealer, true)));
    } catch (e) {
      body.replaceChildren(h("p", { class: "reject", text: `Overview unavailable: ${e.message}. Use Refresh overview to retry.` }));
    } finally {
      $("overview-refresh").disabled = false;
    }
  }
  function renderDataReport(target, report, imported = false) {
    const counts = Object.entries(report.counts || {});
    const issues = Array.isArray(report.issues) ? report.issues : [];
    const children = [h("p", { class: report.valid ? "metric-best" : "fail", text: imported ? "Dataset imported and activated."
      : report.valid ? "Dataset is valid." : "Dataset is invalid." })];
    if (report.source) children.push(h("p", { class: "small", text: `Source: ${report.source}` }));
    if (report.fingerprint) children.push(h("p", { class: "small mono break-text", text: `Fingerprint: ${report.fingerprint}` }));
    if (report.date_range) children.push(h("p", { class: "small", text: `Date range: ${fmtVal(report.date_range)}` }));
    if (counts.length) children.push(table(["Records", "Count"], counts.map(([name, count]) => cellsRow([name, count]))));
    if (report.label_counts && Object.keys(report.label_counts).length) {
      children.push(section("Evaluation labels", table(["Label", "Count"], Object.entries(report.label_counts).map(([name, count]) => cellsRow([name, count])))));
    }
    if (issues.length) children.push(section(`Validation issues (${issues.length})`,
      table(["Severity", "Location", "Message"], issues.map((issue) => cellsRow([issue.severity, issue.location, issue.message], 3)), 3)));
    else children.push(h("p", { class: "muted small", text: "No validation issues." }));
    if (imported) children.push(h("p", { text: "Use Re-run pipeline to investigate this dataset." }));
    target.replaceChildren(...children);
  }
  async function loadDataReport() {
    $("data-report").replaceChildren(h("p", { class: "muted", text: "Loading dataset report…" }));
    $("data-refresh").disabled = true;
    try {
      const report = await api("/api/data");
      if (canRead()) renderDataReport($("data-report"), report);
    } catch (e) {
      $("data-report").replaceChildren(h("p", { class: "reject", text: `Dataset report unavailable: ${e.message}. Use Refresh dataset report to retry.` }));
    } finally {
      $("data-refresh").disabled = false;
    }
  }
  async function readDatasetFile() {
    const file = $("dataset-file").files[0];
    if (!file) return;
    try {
      $("dataset-json").value = await file.text();
      $("data-candidate-report").replaceChildren(h("p", { class: "muted", text: `${file.name} loaded. Validate JSON before importing.` }));
    } catch (e) {
      $("data-candidate-report").replaceChildren(h("p", { class: "reject", text: `Cannot read file: ${e.message}` }));
    }
  }
  async function submitDataset(importing) {
    if (!canAdmin() || state.dataBusy || runInProgress() || state.busy) return;
    const target = $("data-candidate-report");
    let bundle;
    try {
      bundle = JSON.parse($("dataset-json").value);
      if (!bundle || typeof bundle !== "object" || Array.isArray(bundle)) throw new Error("The bundle must be a JSON object.");
    } catch (e) {
      target.replaceChildren(h("p", { class: "reject", text: `Invalid JSON: ${e.message}` }));
      $("dataset-json").focus();
      return;
    }
    state.dataBusy = true;
    applyAccess();
    target.replaceChildren(h("p", { class: "muted", text: importing ? "Importing dataset…" : "Validating dataset…" }));
    try {
      const report = await api(importing ? "/api/data/import" : "/api/data/validate", { method: "POST", body: bundle });
      renderDataReport(target, report, importing && report.imported);
      if (importing && report.imported) {
        await loadDataReport();
        toast("Dataset imported. Run the pipeline to investigate it.");
      }
    } catch (e) {
      const report = e.data && (e.data.detail || e.data);
      if (report && Array.isArray(report.issues)) renderDataReport(target, report);
      else target.replaceChildren(h("p", { class: "reject", text: `${importing ? "Import" : "Validation"} failed: ${e.message}` }));
    } finally {
      state.dataBusy = false;
      applyAccess();
    }
  }

  // ---------- citations ----------
  function parseCite(raw) {
    const m = /^([otuacl]):(.+)$/.exec(raw);
    if (m) return { kind: m[1], id: m[2] };
    if (/^O-\d+$/.test(raw)) return { kind: "o", id: raw };
    if (/^T-\d+$/.test(raw)) return { kind: "t", id: raw };
    if (/^C-\d+-u\d+$/.test(raw)) return { kind: "u", id: raw };
    if (/^C-\d+$/.test(raw)) return { kind: "c", id: raw };
    if (/^A-\d+$/.test(raw)) return { kind: "a", id: raw };
    if (/^(P-\d+|D\d+)$/.test(raw) || raw.includes(":")) return { kind: "n", id: raw };
    return { kind: "l", id: raw };
  }
  function findUtterance(d, id) {
    for (const call of d.call_details) for (const u of call.utterances) if (u.id === id) return u;
    return null;
  }
  function citeInfo(kind, id) {
    const d = state.detail;
    if (kind === "o") return id === d.order.order_id ? `Fund order ${id}: ${d.order.side} ${fmtQty(d.order.qty)} ${d.order.scrip}` : null;
    if (kind === "t") {
      const t = d.trades.find((x) => x.trade_id === id);
      return t ? `Trade ${id}: ${t.side} ${fmtQty(t.qty)} ${t.scrip} @ ₹${fmtPrice(t.price)} at ${hhmm(t.time)}` : null;
    }
    if (kind === "u") {
      const u = findUtterance(d, id);
      return u ? `${id} [${mmss(u.start_ms)}] ${u.speaker}: ${trunc(u.text, 140)}` : null;
    }
    if (kind === "c") return d.call_details.some((c) => c.call_id === id) ? `Call ${id}` : null;
    if (kind === "a" || kind === "n") {
      const nodes = graphPath(d).nodes;
      return nodes.includes(id) || id === d.account.account_id ? `${id}: ${label(id)}` : null;
    }
    if (kind === "l") return d.clause_ids.includes(id) ? `Clause ${id}` : null;
    return null;
  }
  function citeChip(raw, text) {
    const { kind, id } = parseCite(raw);
    const info = citeInfo(kind, id);
    const chip = h("button", { type: "button", class: `chip k-${kind}${info ? "" : " dead"}`,
      text: text || `${kind}:${id}`, title: info || `${id} (not in this case's evidence)` });
    if (info) chip.addEventListener("click", () => followCite(kind, id));
    return chip;
  }
  function focusCard(cardId) {
    const card = $(cardId);
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    restartClass(card, "flash", 1500);
  }
  function pulseWhere(container, attr, id) {
    for (const node of $(container).querySelectorAll(`[data-${attr}]`)) {
      const key = attr.replace(/-([a-z])/g, (_, ch) => ch.toUpperCase());
      if (node.dataset[key] === id) restartClass(node, "pulse", 1800);
    }
  }
  function followCite(kind, id) {
    if (kind === "u") return jumpToUtterance(id);
    if (kind === "c") { setActiveCall(id); return focusCard("card-calls"); }
    if (kind === "t") { focusCard("card-timeline"); return pulseWhere("timeline", "trade-id", id); }
    if (kind === "o") {
      focusCard("card-timeline");
      const mark = $("timeline").querySelector(".order-mark");
      if (mark) restartClass(mark, "pulse-order", 1800);
      return undefined;
    }
    if (kind === "a" || kind === "n") { focusCard("card-graph"); return pulseWhere("graph", "node", id); }
    focusCard("card-clauses");
    return pulseWhere("clauses", "clause-id", id);
  }

  // ---------- evidence chain ----------
  function renderChain(d) {
    const ok = d.chain.filter((x) => x.ok).length;
    $("chain-score").textContent = `${ok} of ${d.chain.length} links hold → ${d.recommendation}`;
    $("chain").replaceChildren(...d.chain.map((link) => h("li", { class: `chain-row ${link.ok ? "ok" : "bad"}`, dataset: { key: link.key } },
      h("span", { class: "chain-icon", "aria-label": link.ok ? "satisfied" : "not satisfied", text: link.ok ? "✓" : "✗" }),
      h("div", { class: "chain-key" }, CHAIN_LABELS[link.key] || link.key, h("span", { class: "mono", text: link.key })),
      h("div", {},
        h("div", { class: "chain-detail", text: link.detail }),
        link.evidence_ids.length ? h("div", { class: "chain-ids" }, link.evidence_ids.map((id) => citeChip(id, id))) : null))));
  }

  // ---------- summary + clauses ----------
  function renderSummary(d) {
    const p = $("summary");
    p.replaceChildren();
    let last = 0;
    for (const m of d.summary.matchAll(CITE_RE)) {
      if (m.index > last) p.append(d.summary.slice(last, m.index));
      p.append(citeChip(`${m[1]}:${m[2]}`));
      last = m.index + m[0].length;
    }
    if (last < d.summary.length) p.append(d.summary.slice(last));
    const isLlm = d.summary_source === "llm";
    $("summary-badge").replaceChildren(h("span", { class: `badge ${isLlm ? "src-llm" : "src-template"}`,
      text: isLlm ? "LLM" : "template", title: isLlm ? "Written by the LLM and passed the grounding check" : "Deterministic template narrative" }));
    const rej = $("summary-reject");
    const reason = d.summary_rejected_reason;
    if (reason) {
      rej.textContent = /^llm unavailable/i.test(reason)
        ? `LLM not used (${reason}). The deterministic template narrative is shown.`
        : `LLM draft rejected by the grounding check: ${reason}. The template narrative is shown instead.`;
      rej.classList.remove("hidden");
    } else {
      rej.classList.add("hidden");
    }
  }
  function sourceLink(url) {
    if (/^https:\/\/[^\s"'<>]+$/i.test(url)) return h("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: url });
    return document.createTextNode(url);
  }
  function renderClauses(d) {
    const box = $("clauses");
    const byId = new Map(d.clauses.map((c) => [c.clause_id, c]));
    const items = d.clause_ids.map((id) => byId.get(id) || { clause_id: id, title: "", text: "", source_url: "" });
    if (!items.length) {
      box.replaceChildren(h("div", { class: "empty-note", text: "No clause mapped for this case." }));
      return;
    }
    box.replaceChildren(...items.map((cl) => h("div", { class: "clause", dataset: { clauseId: cl.clause_id } },
      h("div", {}, h("span", { class: "clause-id", text: cl.clause_id }), " ", h("span", { class: "clause-title", text: cl.title })),
      cl.text ? h("div", { class: "clause-text", text: cl.text }) : null,
      cl.source_url ? h("div", { class: "clause-src" }, sourceLink(cl.source_url)) : null)));
  }

  // ---------- timeline ----------
  function niceStep(raw) {
    const p = 10 ** Math.floor(Math.log10(raw));
    const f = raw / p;
    return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
  }
  function renderTimeline(d) {
    const box = $("timeline");
    const W = Math.max(560, Math.floor(box.clientWidth || 900));
    const H = 260;
    const M = { l: 64, r: 18, t: 46, b: 30 };
    const t0 = toMs(d.order.order_time);
    const x0 = t0 - 120 * MIN, x1 = t0 + 120 * MIN;
    const pts = d.prices.map((p) => ({ t: toMs(p.time), v: p.close, iso: p.time })).filter((p) => p.t >= x0 && p.t <= x1);
    const pre = new Set(d.candidate.pre_trade_ids);
    const trades = d.trades.map((tr) => ({ ...tr, t: toMs(tr.time), phase: pre.has(tr.trade_id) ? "pre" : "post" }));
    const vals = pts.map((p) => p.v).concat(trades.map((tr) => tr.price));
    const root = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": `${d.order.scrip} price from two hours before to two hours after the fund order, with trades` });
    if (!vals.length) {
      root.append(s("text", { class: "svg-empty", x: W / 2, y: H / 2, "text-anchor": "middle", text: "No price data for this window." }));
      box.replaceChildren(root);
      return;
    }
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = (hi - lo) * 0.14 || hi * 0.005 || 1;
    lo -= pad; hi += pad;
    const plotW = W - M.l - M.r, yTop = M.t, yBot = H - M.b;
    const X = (t) => M.l + ((t - x0) / (x1 - x0)) * plotW;
    const Y = (v) => yTop + (1 - (v - lo) / (hi - lo)) * (yBot - yTop);

    // windows
    const band = (from, to, cls, text) => {
      const a = X(Math.max(x0, from)), b = X(Math.min(x1, to));
      root.append(s("rect", { class: cls, x: a, y: yTop, width: Math.max(0, b - a), height: yBot - yTop }));
      root.append(s("text", { class: "svg-band-label", x: (a + b) / 2, y: yBot - 6, "text-anchor": "middle", text }));
    };
    band(t0 - 60 * MIN, t0, "svg-band-pre", "pre-order window 60 min");
    band(t0, t0 + 90 * MIN, "svg-band-post", "post-order window 90 min");

    // y grid
    const step = niceStep((hi - lo) / 4);
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) {
      root.append(s("line", { class: "svg-grid", x1: M.l, x2: W - M.r, y1: Y(v), y2: Y(v) }));
      root.append(s("text", { class: "svg-tick", x: M.l - 8, y: Y(v) + 4, "text-anchor": "end", text: fmtPrice(v) }));
    }
    // x ticks every 30 min on local half hours
    const first = new Date(x0);
    first.setSeconds(0, 0);
    first.setMinutes(first.getMinutes() + ((30 - (first.getMinutes() % 30)) % 30));
    for (let t = first.getTime(); t <= x1; t += 30 * MIN) {
      const dt = new Date(t);
      const txt = `${String(dt.getHours()).padStart(2, "0")}:${String(dt.getMinutes()).padStart(2, "0")}`;
      root.append(s("line", { class: "svg-axis", x1: X(t), x2: X(t), y1: yBot, y2: yBot + 4 }));
      root.append(s("text", { class: "svg-tick", x: X(t), y: yBot + 17, "text-anchor": "middle", text: txt }));
    }
    root.append(s("line", { class: "svg-axis", x1: M.l, x2: W - M.r, y1: yBot, y2: yBot }));
    root.append(s("line", { class: "svg-axis", x1: M.l, x2: M.l, y1: yTop, y2: yBot }));

    // price line
    if (pts.length) {
      const path = pts.map((p, i) => `${i ? "L" : "M"}${X(p.t).toFixed(1)},${Y(p.v).toFixed(1)}`).join("");
      root.append(s("path", { class: "svg-price", d: path }));
    }

    // crosshair overlay (below markers so markers keep their own hover)
    const hair = s("line", { class: "svg-hair hidden", y1: yTop, y2: yBot });
    const dot = s("circle", { class: "svg-hair-dot hidden", r: 3.5 });
    const overlay = s("rect", { class: "svg-overlay", x: M.l, y: yTop, width: plotW, height: yBot - yTop });
    overlay.addEventListener("mousemove", (evt) => {
      if (!pts.length) return;
      const rect = root.getBoundingClientRect();
      const px = (evt.clientX - rect.left) * (W / rect.width);
      const t = x0 + ((px - M.l) / plotW) * (x1 - x0);
      let loI = 0, hiI = pts.length - 1;
      while (hiI - loI > 1) { const mid = (loI + hiI) >> 1; if (pts[mid].t < t) loI = mid; else hiI = mid; }
      const p = Math.abs(pts[loI].t - t) <= Math.abs(pts[hiI].t - t) ? pts[loI] : pts[hiI];
      for (const n of [hair, dot]) n.classList.remove("hidden");
      hair.setAttribute("x1", X(p.t)); hair.setAttribute("x2", X(p.t));
      dot.setAttribute("cx", X(p.t)); dot.setAttribute("cy", Y(p.v));
      const rel = Math.round((p.t - t0) / MIN);
      showTip(evt, `${hhmm(p.iso)}  close ₹${fmtPrice(p.v)}\n${rel === 0 ? "at" : `${Math.abs(rel)} min ${rel < 0 ? "before" : "after"}`} the fund order`);
    });
    overlay.addEventListener("mouseleave", () => { hair.classList.add("hidden"); dot.classList.add("hidden"); hideTip(); });
    root.append(overlay, hair, dot);

    // fund execution bar and order marker
    const o = d.order;
    const order = s("g", { class: "order-mark" });
    if (o.exec_start && o.exec_end) {
      const a = X(Math.max(x0, toMs(o.exec_start))), b = X(Math.min(x1, toMs(o.exec_end)));
      const exec = s("rect", { class: "svg-band-exec", x: a, y: yTop - 10, width: Math.max(2, b - a), height: 5, rx: 2 });
      tipOn(exec, `Fund execution ${hhmm(o.exec_start)}–${hhmm(o.exec_end)} (${o.side} ${fmtQty(o.qty)} ${o.scrip})`);
      order.append(exec);
    }
    const ox = X(t0);
    order.append(s("line", { class: "svg-order", x1: ox, x2: ox, y1: yTop - 18, y2: yBot }));
    const orderText = `Fund ${o.side} ${fmtQty(o.qty)} · ${hhmm(o.order_time)}`;
    const anchor = ox < M.l + 90 ? "start" : ox > W - M.r - 90 ? "end" : "middle";
    order.append(s("text", { class: "svg-order-label", x: ox, y: yTop - 24, "text-anchor": anchor, text: orderText }));
    tipOn(order, `${o.order_id} ${o.scheme}\n${o.side} ${fmtQty(o.qty)} ${o.scrip}, received ${hhmm(o.order_time)} by ${o.dealer_id}`);
    root.append(order);

    // trade markers sized by qty
    const maxQty = Math.max(1, ...trades.map((tr) => tr.qty));
    for (const tr of trades.sort((a, b) => b.qty - a.qty)) {
      const cx = X(Math.min(x1, Math.max(x0, tr.t))), cy = Y(tr.price);
      const r = 4 + 9 * Math.sqrt(tr.qty / maxQty);
      const mins = Math.round((tr.t - t0) / MIN);
      const marker = s("circle", { class: `svg-marker ${tr.phase}`, cx, cy, r, dataset: { tradeId: tr.trade_id },
        "aria-label": `${tr.phase}-order trade ${tr.trade_id}` });
      tipOn(marker, `${tr.trade_id} · ${tr.phase === "pre" ? "pre-order" : "post-order"} trade\n` +
        `${tr.side} ${fmtQty(tr.qty)} ${tr.scrip} @ ₹${fmtPrice(tr.price)}\n` +
        `${hhmm(tr.time)} · ${Math.abs(mins)} min ${mins < 0 ? "before" : "after"} the fund order`);
      root.append(marker);
      root.append(s("text", { class: `svg-marker-label ${tr.phase}`, x: cx, y: cy - r - 4, "text-anchor": "middle",
        text: `${mins < 0 ? "−" : "+"}${Math.abs(mins)}m` }));
    }
    box.replaceChildren(root);
  }

  // ---------- link graph ----------
  function graphPath(d) {
    const nodes = [d.dealer.dealer_id];
    let cur = d.dealer.dealer_id;
    for (const link of d.link_path) {
      const next = link.src === cur ? link.dst : link.dst === cur ? link.src : link.dst;
      nodes.push(next);
      cur = next;
    }
    return { nodes, edges: d.link_path };
  }
  function nodeType(id, d) {
    if (id === d.dealer.dealer_id || /^D\d+$/.test(id)) return "dealer";
    if (id === d.account.account_id || /^A-\d+$/.test(id)) return "account";
    if (/^P-\d+$/.test(id)) return "person";
    if (id.includes(":")) return "attribute";
    return "other";
  }
  function renderGraph(d) {
    const box = $("graph");
    const W = Math.max(560, Math.floor(box.clientWidth || 900));
    const H = 132, cy = 70;
    let { nodes, edges } = graphPath(d);
    const missing = !edges.length;
    if (missing) nodes = [d.dealer.dealer_id, d.account.account_id];
    const n = nodes.length;
    const side = 16;
    const slot = (W - 2 * side) / n;
    const boxW = Math.max(92, Math.min(136, slot * 0.46));
    const cx = (i) => side + slot * i + slot / 2;
    const root = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": missing ? "No link path between dealer and account" : `Link path ${nodes.join(" to ")}` });
    const defs = s("defs", {}, s("marker", { id: "dw-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" },
      s("path", { class: "g-arrow", d: "M0,0 L10,5 L0,10 z" })));
    root.append(defs);

    const gap = slot - boxW;
    if (missing) {
      root.append(s("line", { class: "g-edge missing", x1: cx(0) + boxW / 2, x2: cx(1) - boxW / 2, y1: cy, y2: cy }));
      root.append(s("text", { class: "g-edge-kind", x: (cx(0) + cx(1)) / 2, y: cy - 8, "text-anchor": "middle", text: "no link found in the graph" }));
    }
    edges.forEach((link, i) => {
      const a = cx(i) + boxW / 2, b = cx(i + 1) - boxW / 2, mid = (a + b) / 2;
      const g = s("g", { class: "g-edge-group" });
      g.append(s("line", { class: "g-edge", x1: a + 2, x2: b - 3, y1: cy, y2: cy, "marker-end": "url(#dw-arrow)" }));
      const maxChars = Math.max(4, Math.floor((gap - 8) / 6.7));
      g.append(s("text", { class: "g-edge-kind", x: mid, y: cy - 8, "text-anchor": "middle", text: trunc(link.kind, maxChars) }));
      g.append(s("text", { class: "g-edge-value", x: mid, y: cy + 16, "text-anchor": "middle", text: trunc(link.value, maxChars) }));
      g.append(s("text", { class: "g-edge-src", x: mid, y: cy + 30, "text-anchor": "middle", text: trunc(link.source, maxChars) }));
      tipOn(g, `${link.kind}: ${link.value}\n${link.src} → ${link.dst}\nsource: ${link.source}`);
      root.append(g);
    });
    nodes.forEach((id, i) => {
      const type = nodeType(id, d);
      const isAttr = type === "attribute";
      const top = isAttr ? id.split(":")[0] : id;
      const sub = isAttr ? id.slice(id.indexOf(":") + 1) : label(id).replace(/\s*\(.*\)$/, "");
      const chars = Math.floor((boxW - 12) / 6.4);
      const g = s("g", { class: `g-node ${type}`, dataset: { node: id } });
      g.append(s("text", { class: "g-type", x: cx(i), y: cy - 30, "text-anchor": "middle", text: type }));
      g.append(s("rect", { x: cx(i) - boxW / 2, y: cy - 21, width: boxW, height: 42, rx: 6 }));
      g.append(s("text", { class: "g-id", x: cx(i), y: cy - 4, "text-anchor": "middle", text: trunc(top, chars) }));
      g.append(s("text", { class: "g-name", x: cx(i), y: cy + 12, "text-anchor": "middle", text: trunc(sub, chars) }));
      tipOn(g, `${id}\n${label(id)}`);
      root.append(g);
    });
    $("graph-note").textContent = missing
      ? `No path from ${d.dealer.dealer_id} to ${d.account.account_id}`
      : `${edges.length} hop${edges.length === 1 ? "" : "s"}: ${nodes.join(" → ")}`;
    box.replaceChildren(root);
  }

  // ---------- calls + transcript ----------
  function renderCalls(d) {
    const tabs = $("call-tabs");
    const count = d.call_details.length;
    $("calls-note").textContent = count
      ? `${count} call${count === 1 ? "" : "s"} by ${d.dealer.dealer_id} to the account's network · ${d.cues.length} grounded cue${d.cues.length === 1 ? "" : "s"}`
      : "";
    if (!count) {
      tabs.replaceChildren();
      $("call-meta").replaceChildren(h("div", { class: "empty-note",
        text: `No call by ${d.dealer.dealer_id} ${d.dealer.name} to a number in the account's link network within the 180-minute lookback window.` }));
      $("call-audio").replaceChildren();
      $("cues").replaceChildren();
      $("transcript").replaceChildren();
      $("transcript").classList.add("hidden");
      state.uttRows = new Map();
      state.uttData = new Map();
      return;
    }
    $("transcript").classList.remove("hidden");
    tabs.replaceChildren(...d.call_details.map((c) => {
      const cues = d.cues.filter((q) => q.call_id === c.call_id).length;
      return h("button", { type: "button", class: `call-tab${c.call_id === state.activeCall ? " active" : ""}`,
        text: `${c.call_id} · ${hhmm(c.start_time)} · ${cues} cue${cues === 1 ? "" : "s"}`,
        onclick: () => setActiveCall(c.call_id) });
    }));
    renderActiveCall(d);
  }
  function setActiveCall(id) {
    if (!state.detail || !state.detail.call_details.some((c) => c.call_id === id)) return;
    state.activeCall = id;
    renderCalls(state.detail);
  }
  function renderActiveCall(d) {
    const call = d.call_details.find((c) => c.call_id === state.activeCall) || d.call_details[0];
    state.activeCall = call.call_id;
    const lead = minutesFrom(call.start_time, d.order.order_time);
    $("call-meta").replaceChildren(
      h("strong", { text: call.call_id }), ` · ${call.dealer_id} ${label(call.dealer_id)} → `,
      h("strong", { text: call.counterparty_number }),
      label(call.counterparty_number) !== call.counterparty_number ? ` ${label(call.counterparty_number)}` : "",
      ` · ${dateTime(call.start_time)} · ${duration(call.duration_s)} · ${Math.abs(lead)} min ${lead >= 0 ? "before" : "after"} the fund order`);

    const audioBox = $("call-audio");
    let audio = null;
    if (call.has_audio) {
      audio = h("audio", { controls: true, preload: "metadata", src: `/audio/${encodeURIComponent(call.call_id)}?case_id=${encodeURIComponent(d.case_id)}` });
      audioBox.replaceChildren(audio);
    } else {
      audioBox.replaceChildren(h("div", { class: "no-audio", text: "No audio rendered for this call; showing the replayed transcript." }));
    }

    const cues = d.cues.filter((q) => q.call_id === call.call_id);
    $("cues").replaceChildren(...cues.map((cue) => {
      const tags = [cue.scrip, cue.side, cue.qty_hint, cue.time_hint].filter(Boolean);
      return h("button", { type: "button", class: "cue", title: `Grounded to ${cue.utterance_ids.join(", ")} (${cue.extractor} extractor)`,
        onclick: () => jumpToUtterance(cue.utterance_ids[0]) },
        h("span", { class: "cue-tags" }, tags.map((t) => h("span", { class: "cue-tag", text: t })), h("span", { class: "cue-tag", text: cue.extractor })),
        h("span", { class: "cue-quote", text: `“${cue.quote}”` }),
        h("span", { class: "utt-id", text: cue.utterance_ids.join(", ") }));
    }));

    state.uttRows = new Map();
    state.uttData = new Map();
    const rows = call.utterances.map((u) => {
      const isDealer = u.speaker === call.dealer_id;
      const row = h("div", { class: `utt${state.cited.has(u.id) ? " cited" : ""}`, dataset: { uid: u.id },
        onclick: () => { state.uttRows.forEach((r) => r.classList.remove("flash")); seekAudio(u); } },
        h("span", { class: "utt-ts", text: `[${mmss(u.start_ms)}]` }),
        h("span", { class: `utt-spk ${isDealer ? "dealer" : "other"}`, text: u.speaker, title: label(u.speaker) }),
        h("span", { class: "utt-text" }, u.text,
          INJECTION_RE.test(u.text) ? h("span", { class: "inject", text: "instruction-like text, treated as data",
            title: "This utterance contains text addressed to an AI system. The pipeline treats transcripts as evidence only." }) : null,
          h("span", { class: "utt-id", text: u.id })));
      state.uttRows.set(u.id, row);
      state.uttData.set(u.id, u);
      return row;
    });
    $("transcript").replaceChildren(...rows);
    $("transcript").scrollTop = 0;

    if (audio) {
      audio.addEventListener("timeupdate", () => {
        const ms = audio.currentTime * 1000;
        for (const u of call.utterances) {
          const row = state.uttRows.get(u.id);
          if (row) row.classList.toggle("playing", ms >= u.start_ms && ms < u.end_ms);
        }
      });
    }
  }
  function seekAudio(u) {
    const audio = $("call-audio").querySelector("audio");
    if (!audio || !u) return;
    const go = () => {
      audio.currentTime = u.start_ms / 1000;
      audio.play().catch(() => {});
    };
    if (audio.readyState >= 1) go();
    else audio.addEventListener("loadedmetadata", go, { once: true });
  }
  function jumpToUtterance(uid) {
    const d = state.detail;
    const callId = uid.replace(/-u\d+$/, "");
    if (callId !== state.activeCall) setActiveCall(callId);
    const row = state.uttRows.get(uid);
    if (!row) {
      toast(`Utterance ${uid} is not in this case's calls.`, true);
      return;
    }
    if (!d) return;
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    restartClass(row, "flash", 1700);
    seekAudio(state.uttData.get(uid));
  }

  // ---------- decisions ----------
  function renderHistory(d) {
    const ol = $("history");
    if (!d.decisions.length) {
      ol.replaceChildren(h("li", { class: "empty-note", text: "No decisions yet. Nothing is escalated automatically; a reviewer must act." }));
      return;
    }
    ol.replaceChildren(...d.decisions.slice().reverse().map((x) => h("li", {},
      h("span", { class: "h-time", text: dateTime(x.time) }),
      h("span", { class: "h-action", text: ACTION_LABELS[x.action] || x.action }),
      h("span", { text: x.reviewer }),
      h("span", { class: "muted", text: x.note || "—" }))));
  }
  function renderDecisionBar(d) {
    $("decision-bar").classList.remove("hidden");
    const terminal = TERMINAL.has(d.status);
    const disabled = !canRead() || terminal || state.busy || state.decisionBusy || state.sessionBusy;
    for (const btn of document.querySelectorAll("#decision-bar [data-action]")) btn.disabled = disabled;
    $("reviewer").disabled = state.decisionBusy;
    $("note").disabled = state.decisionBusy;
    $("decision-state").textContent = terminal
      ? `${d.case_id} is ${d.status} (final).`
      : state.decisionBusy ? "Recording decision…" : `${d.case_id} status: ${d.status.replace(/_/g, " ")}`;
  }
  async function decide(action) {
    const d = state.detail;
    if (!d || !canRead() || state.decisionBusy || state.busy || TERMINAL.has(d.status)) return;
    const reviewer = $("reviewer").value.trim();
    if (!reviewer) {
      toast("Enter the reviewer name first.", true);
      $("reviewer").focus();
      return;
    }
    const note = $("note").value.trim();
    state.decisionBusy = true;
    renderDecisionBar(d);
    try {
      if (action === "approve_escalation" || action === "dismiss") {
        const escalate = action === "approve_escalation";
        const ok = await confirmDialog(escalate ? "Approve escalation?" : "Dismiss this case?",
          `${d.case_id} (${d.candidate.scrip}, ${d.account.account_id} ${d.account.holder_name}) will move to ` +
          `${escalate ? "ESCALATED" : "CLOSED"}. This is final and is recorded in the ledger under "${reviewer}".`,
          ACTION_LABELS[action]);
        if (!ok) return;
      }
      const body = { action, reviewer, note, expected_revision: d.revision };
      const signature = JSON.stringify([d.case_id, body]);
      if (!state.decisionAttempt || state.decisionAttempt.signature !== signature) {
        state.decisionAttempt = { signature, key: actionKey() };
      }
      const updated = await api(`/api/cases/${encodeURIComponent(d.case_id)}/decision`,
        { method: "POST", body, headers: { "Idempotency-Key": state.decisionAttempt.key } });
      state.decisionAttempt = null;
      if (state.detail && state.detail.case_id === d.case_id) {
        state.detail.status = updated.status;
        state.detail.decisions = updated.decisions;
        state.detail.revision = updated.revision;
        renderHeader(state.detail);
        renderHistory(state.detail);
        $("note").value = "";
      }
      await loadCases(state.selectedId);
      toast(`${ACTION_LABELS[action]} recorded for ${d.case_id}; status is now ${updated.status}.`);
    } catch (e) {
      if (e.status && e.status < 500) state.decisionAttempt = null;
      if (e.status === 409) {
        await loadCases(state.selectedId);
        toast(`Decision not recorded: ${e.message}. The latest case state has been loaded.`, true);
      } else {
        toast(`Decision failed: ${e.message}${e.status ? "" : ". Retry the same action to check its result safely."}`, true);
      }
    } finally {
      state.decisionBusy = false;
      if (state.detail) renderDecisionBar(state.detail);
    }
  }

  // ---------- background investigation runs ----------
  function renderRunProgress() {
    const run = state.activeRun;
    if (!run) {
      $("run-progress").replaceChildren(h("p", { class: "muted", text: "No investigation runs yet. Use Re-run pipeline to start one." }));
      return;
    }
    const completed = Number(run.completed) || 0, total = Number(run.total) || 0;
    const children = [h("p", { class: "break-text", text: `${run.run_id} · ${run.status} · ${run.stage || "waiting"}` })];
    if (runInProgress()) {
      const progress = h("progress", { max: Math.max(total, 1), "aria-label": "Investigation progress" });
      if (total > 0) progress.value = Math.min(completed, total);
      children.push(progress, h("span", { class: "small", text: total ? ` ${completed} of ${total}` : " Waiting for progress…" }));
    }
    if (run.stats) children.push(h("p", { text: `${fmtVal(run.stats.cases)} cases · ${fmtVal(run.stats.escalate)} escalate · ${fmtVal(run.stats.review)} review · ${fmtVal(run.stats.dismiss)} dismiss · ${fmtVal(run.stats.total_ms)} ms` }));
    if (run.error) children.push(h("p", { class: "reject", text: `Run failed: ${run.error}` }));
    if (state.runPollErrors) children.push(h("p", { class: "fail", text: "Run updates are unavailable. The investigation may still be running." }));
    $("run-progress").replaceChildren(...children);
  }
  function renderRunHistory() {
    if (!state.runs.length) {
      $("run-history").replaceChildren(h("p", { class: "muted", text: "No investigation runs have been recorded." }));
      return;
    }
    $("run-history").replaceChildren(table(["Run", "Status", "Stage", "Progress", "Started", "Finished", "Result"], state.runs.map((run) =>
      cellsRow([run.run_id, run.status, run.stage || "—", `${run.completed || 0} / ${run.total || 0}`,
        dateTime(run.started_at || run.created_at), dateTime(run.finished_at) || "—",
        run.error || (run.stats ? `${fmtVal(run.stats.cases)} cases, ${fmtVal(run.stats.total_ms)} ms` : "—")], 7)), 7));
  }
  function scheduleRunPoll() {
    clearTimeout(state.runTimer);
    if (canRead() && runInProgress()) state.runTimer = setTimeout(pollRun, 1000);
  }
  async function loadRuns() {
    const request = ++state.runsRequest;
    $("runs-refresh").disabled = true;
    if (!state.runs.length) $("run-history").replaceChildren(h("p", { class: "muted", text: "Loading run history…" }));
    try {
      const runs = await api("/api/runs");
      if (request !== state.runsRequest || !canRead()) return;
      const wasRunning = Boolean(runInProgress());
      state.runs = runs;
      state.activeRun = runs.find((run) => ["QUEUED", "RUNNING"].includes(run.status)) || runs[0] || null;
      state.runPollErrors = 0;
      $("run-retry-poll").classList.add("hidden");
      renderRunProgress();
      renderRunHistory();
      applyAccess();
      scheduleRunPoll();
      if (wasRunning && !runInProgress()) {
        await loadCases(state.selectedId);
        await loadHealth();
      }
    } catch (e) {
      $("run-history").replaceChildren(h("p", { class: "reject", text: `Run history unavailable: ${e.message}. Use Refresh run history to retry.` }));
    } finally {
      if (request === state.runsRequest) $("runs-refresh").disabled = false;
    }
  }
  async function pollRun() {
    const id = state.activeRun && state.activeRun.run_id;
    if (!id || !canRead()) return;
    clearTimeout(state.runTimer);
    try {
      const run = await api(`/api/runs/${encodeURIComponent(id)}`);
      if (!canRead() || !state.activeRun || state.activeRun.run_id !== id) return;
      state.activeRun = run;
      state.runs = [run, ...state.runs.filter((item) => item.run_id !== id)];
      state.runPollErrors = 0;
      $("run-retry-poll").classList.add("hidden");
      renderRunProgress();
      renderRunHistory();
      applyAccess();
      if (runInProgress()) {
        scheduleRunPoll();
      } else {
        if (run.status === "SUCCEEDED") {
          state.verify = null;
          renderVerify();
          await loadCases(state.selectedId);
          if (state.tab === "overview") await loadOverview();
          if (state.tab === "ledger") await loadLedger();
          toast(`Pipeline completed: ${run.stats ? fmtVal(run.stats.cases) : "new"} cases. Reviewer decisions were preserved.`);
        } else toast(`Pipeline failed: ${run.error || "See run history for details."}`, true);
        await loadHealth();
      }
    } catch (e) {
      state.runPollErrors += 1;
      renderRunProgress();
      if (state.runPollErrors < 3) scheduleRunPoll();
      else {
        $("run-retry-poll").classList.remove("hidden");
        toast(`Run updates paused: ${e.message}. Use Resume run updates to reconnect.`, true);
      }
    }
  }
  async function rerunPipeline() {
    if (!canAdmin() || state.busy || state.dataBusy || state.runStarting || runInProgress()) return;
    state.runStarting = true;
    applyAccess();
    try {
      const run = await api("/api/runs", { method: "POST" });
      state.runsRequest += 1;
      $("runs-refresh").disabled = false;
      state.activeRun = run;
      state.runs = [run, ...state.runs.filter((item) => item.run_id !== run.run_id)];
      state.runPollErrors = 0;
      renderRunProgress();
      renderRunHistory();
      showTab("runs", true, false);
      scheduleRunPoll();
      toast("Investigation queued. Reviewer decisions will be preserved.");
    } catch (e) {
      if (e.status === 409) { showTab("runs"); await loadRuns(); }
      toast(`Could not start pipeline: ${e.message}`, true);
    } finally {
      state.runStarting = false;
      applyAccess();
    }
  }

  // ---------- ledger ----------
  function shortHash(hash) { return hash ? `${hash.slice(0, 10)}…` : ""; }
  async function loadLedger() {
    const data = await api(`/api/ledger?limit=${state.ledgerLimit}&offset=${state.ledgerOffset}`);
    if (!canRead()) return data;
    state.ledgerCount = data.count;
    if (state.ledgerOffset === 0 && data.entries.length) state.ledgerBase = data.entries[0].seq;
    $("ledger-head").textContent = data.head ? `head ${data.head.slice(0, 16)}… · ${data.count} entries` : `${data.count} entries`;
    const from = data.count ? state.ledgerOffset + 1 : 0;
    const to = Math.min(data.count, state.ledgerOffset + data.entries.length);
    $("ledger-range").textContent = `${from}–${to} of ${data.count}`;
    $("ledger-prev").disabled = state.ledgerOffset === 0;
    $("ledger-next").disabled = state.ledgerOffset + state.ledgerLimit >= data.count;
    const seqInput = $("tamper-seq");
    if (!seqInput.value && data.entries.length) {
      const pick = data.entries.find((e) => e.action === "case.created") || data.entries[Math.min(4, data.entries.length - 1)];
      seqInput.value = String(pick.seq);
    }
    const v = state.verify;
    const bad = v && !v.ok ? v.first_bad_seq : null;
    const rows = [];
    for (const e of data.entries) {
      const cls = ["entry"];
      if (bad !== null && e.seq === bad) cls.push("bad");
      else if (bad !== null && e.seq > bad) cls.push("after-bad");
      const payload = JSON.stringify(e.payload);
      const tr = h("tr", { class: cls.join(" "), tabindex: 0, "aria-label": `Ledger entry ${e.seq}, ${e.action}`, dataset: { seq: String(e.seq) } },
        h("td", { class: "num mono", text: e.seq }),
        h("td", { class: "mono", text: String(e.ts || "").replace("T", " ").slice(0, 19) }),
        h("td", { text: e.actor }),
        h("td", {}, h("span", { class: `action-tag${String(e.action).startsWith("decision.") ? " decision" : ""}`, text: e.action })),
        h("td", { class: "payload", text: payload, title: trunc(payload, 600) }),
        h("td", { class: "hash", text: shortHash(e.hash), title: e.hash }),
        h("td", { class: "hash", text: shortHash(e.prev_hash), title: e.prev_hash }));
      const toggleEntry = () => {
        if (state.expanded.has(e.seq)) state.expanded.delete(e.seq); else state.expanded.add(e.seq);
        loadLedger().then(() => {
          const row = [...$("ledger-rows").querySelectorAll("tr.entry")].find((item) => item.dataset.seq === String(e.seq));
          if (row) row.focus({ preventScroll: true });
        }).catch((error) => toast(`Ledger: ${error.message}`, true));
      };
      tr.addEventListener("click", toggleEntry);
      tr.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggleEntry(); }
      });
      rows.push(tr);
      if (state.expanded.has(e.seq)) {
        rows.push(h("tr", { class: "detail" }, h("td", { colspan: 7 },
          h("pre", { text: `payload_hash ${e.payload_hash}\nprev_hash    ${e.prev_hash}\nhash         ${e.hash}\n\n${JSON.stringify(e.payload, null, 2)}` }))));
      }
    }
    if (!rows.length) rows.push(h("tr", {}, h("td", { colspan: 7, class: "muted", text: "Ledger is empty. Run the pipeline." })));
    $("ledger-rows").replaceChildren(...rows);
    return data;
  }
  function renderVerify() {
    const banner = $("verify-banner");
    const v = state.verify;
    if (!v) { banner.classList.add("hidden"); return; }
    banner.className = `banner ${v.ok ? "ok" : "bad"}`;
    if (v.ok) {
      banner.replaceChildren(h("span", { class: "big", text: "✓ Chain intact" }),
        h("span", { text: `${v.checked} entries checked; every hash links to the previous one.` }));
    } else {
      banner.replaceChildren(h("span", { class: "big", text: `✗ Tampering detected at seq ${v.first_bad_seq}` }),
        h("span", { text: `${v.reason || "hash mismatch"} · ${v.checked} entries checked before the break.` }),
        h("button", { type: "button", class: "btn btn-small", text: `Show seq ${v.first_bad_seq}`, onclick: () => gotoSeq(v.first_bad_seq) }));
    }
  }
  async function gotoSeq(seq) {
    if (seq === null || seq === undefined) return;
    state.ledgerOffset = Math.max(0, Math.floor((seq - state.ledgerBase) / state.ledgerLimit) * state.ledgerLimit);
    await loadLedger();
    const row = [...$("ledger-rows").querySelectorAll("tr.entry")].find((r) => r.dataset.seq === String(seq));
    if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  async function verifyLedger() {
    try {
      state.verify = await api("/api/ledger/verify");
      renderVerify();
      if (state.verify.ok) await loadLedger(); else await gotoSeq(state.verify.first_bad_seq);
    } catch (e) {
      toast(`Verify failed: ${e.message}`, true);
    }
  }
  async function tamperLedger() {
    if (!canAdmin() || !state.session.demo_enabled || state.busy || runInProgress()) return;
    const seq = parseInt($("tamper-seq").value, 10);
    if (!Number.isFinite(seq)) { toast("Pick a seq to tamper with.", true); return; }
    const ok = await confirmDialog("Tamper with the ledger? (demo)",
      `Edits the payload of entry ${seq} in place without recomputing its hash, as an insider editing the database would. Verify should then fail at seq ${seq}.`,
      "Tamper");
    if (!ok) return;
    try {
      state.verify = await api("/api/ledger/tamper-demo", { method: "POST", body: { seq } });
      renderVerify();
      await gotoSeq(state.verify.ok ? seq : state.verify.first_bad_seq);
      toast(state.verify.ok ? "Ledger still verifies." : `Verify now fails at seq ${state.verify.first_bad_seq}.`, !state.verify.ok);
    } catch (e) {
      toast(`Tamper demo failed: ${e.message}`, true);
    }
  }
  async function restoreLedger() {
    if (!canAdmin() || !state.session.demo_enabled || state.busy || runInProgress()) return;
    const ok = await confirmDialog("Reset cases and restore a clean ledger?",
      "This destructive demo reset rebuilds cases and the ledger from the active dataset. All recorded reviewer decisions and the existing audit history are cleared. Ordinary pipeline reruns preserve them.", "Reset demo data");
    if (!ok) return;
    setBusy(true, "Rebuilding ledger…");
    try {
      const res = await api("/api/ledger/restore", { method: "POST" });
      state.verify = res.verify;
      state.ledgerOffset = 0;
      state.expanded.clear();
      renderVerify();
      await loadLedger();
      await loadCases(state.selectedId);
      state.evalLoaded = false;
      toast(res.verify.ok ? `Ledger rebuilt: ${res.verify.checked} entries verify.` : "Ledger rebuilt but does not verify.", !res.verify.ok);
    } catch (e) {
      toast(`Restore failed: ${e.message}`, true);
    } finally {
      setBusy(false);
      loadHealth();
    }
  }

  // ---------- eval ----------
  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
  function fmtVal(v) {
    if (typeof v === "number") {
      if (Number.isInteger(v)) return nfInt.format(v);
      return Math.abs(v) <= 1 ? v.toFixed(3) : v.toFixed(1);
    }
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (v === null || v === undefined) return "—";
    if (Array.isArray(v)) return v.map(fmtVal).join(", ");
    if (isObj(v)) return JSON.stringify(v);
    return String(v);
  }
  const pct = (v) => (typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—");
  function table(head, rows, numericFrom = 1) {
    return h("div", { class: "table-wrap" }, h("table", { class: "table" },
      h("thead", {}, h("tr", {}, head.map((c, i) => h("th", { class: i >= numericFrom ? "num" : "", text: c })))),
      h("tbody", {}, rows)));
  }
  function cellsRow(values, numericFrom = 1, classes = []) {
    return h("tr", {}, values.map((v, i) => {
      const cls = `${i >= numericFrom ? "num" : ""} ${classes[i] || ""}`;
      return v instanceof Node ? h("td", { class: cls }, v) : h("td", { class: cls, text: fmtVal(v) });
    }));
  }
  function section(title, ...kids) {
    return h("div", { class: "eval-section" }, h("h3", { text: title }), kids);
  }
  function confusion(name, cm) {
    const cell = (cls, v, tip) => h("div", { class: `v ${cls}`, text: fmtVal(v), title: tip });
    return h("div", {}, h("div", { class: "muted small", text: name }), h("div", { class: "cm" },
      h("div", { class: "h", text: "" }), h("div", { class: "h", text: "truth ESCALATE" }), h("div", { class: "h", text: "truth not" }),
      h("div", { class: "h", text: "predicted ESCALATE" }), cell("tp", cm.tp, "true positives"), cell("fp", cm.fp, "false positives"),
      h("div", { class: "h", text: "predicted not" }), cell("fn", cm.fn, "false negatives"), cell("tn", cm.tn, "true negatives")));
  }
  function metricsTable(dw, base) {
    const systems = [["DealerWatch", dw], ["Rules-only baseline", base]];
    const best = {};
    for (const k of ["precision", "recall", "f1"]) best[k] = Math.max(dw[k], base[k]);
    return table(["System", "TP", "FP", "FN", "TN", "Precision", "Recall", "F1"], systems.map(([name, m]) =>
      cellsRow([name, m.tp, m.fp, m.fn, m.tn, m.precision.toFixed(3), m.recall.toFixed(3), m.f1.toFixed(3)], 1,
        ["", "", "", "", "", m.precision === best.precision ? "metric-best" : "",
          m.recall === best.recall ? "metric-best" : "", m.f1 === best.f1 ? "metric-best" : ""])));
  }
  function verdict(produced, expected) {
    return h("span", { class: produced === expected ? "metric-best" : "fail", text: `${produced} ${produced === expected ? "✓" : "✗"}` });
  }
  function openCaseButton(caseId, evaluationCaseId) {
    if (!caseId) return h("span", { class: "muted", text: evaluationCaseId ? "No published case" : "no candidate" });
    return h("button", { type: "button", class: "chip", text: caseId, title: "Open this case",
      onclick: () => { showTab("cases"); selectCase(caseId); } });
  }
  function renderEval(ev) {
    const body = $("eval-body");
    if (!isObj(ev) || !isObj(ev.escalate)) {
      body.replaceChildren(h("pre", { class: "mono small", text: JSON.stringify(ev, null, 2) }));
      return;
    }
    const dw = ev.escalate.dealerwatch, base = ev.escalate.baseline;
    const acc = ev.accuracy_planted || {}, lat = ev.latency_ms || {}, fa = ev.false_alarms || {}, run = ev.run || {};
    const kpis = h("div", { class: "kpis" },
      kpi("DealerWatch F1", dw.f1.toFixed(3), "pos"), kpi("Baseline F1", base.f1.toFixed(3)),
      kpi("Planted accuracy", `${pct(acc.dealerwatch)} vs ${pct(acc.baseline)}`),
      kpi("REVIEW (abstain) rate", pct(ev.review_rate)),
      kpi("Latency p50 / p95", `${fmtVal(lat.p50)} / ${fmtVal(lat.p95)} ms`),
      kpi("Population", `${fmtVal(ev.population)} pairs`));
    const perLabel = table(["Label", "Expected", "n", "DW ESCALATE", "DW REVIEW", "DW DISMISS", "DW correct", "Baseline ESCALATE", "Baseline correct"],
      (ev.per_label || []).map((r) => cellsRow([r.label, r.expected.join(" / "), r.n, r.dealerwatch.ESCALATE, r.dealerwatch.REVIEW,
        r.dealerwatch.DISMISS, `${r.dealerwatch_correct} / ${r.n}`, r.baseline_escalate, `${r.baseline_correct} / ${r.n}`], 2)), 2);
    const other = table(["Metric", "Value"], [
      cellsRow(["Planted-case accuracy, DealerWatch / baseline", `${pct(acc.dealerwatch)} / ${pct(acc.baseline)}`]),
      cellsRow(["REVIEW rate, all candidates", pct(ev.review_rate)]),
      cellsRow(["REVIEW rate, planted cases", pct(ev.review_rate_planted)]),
      cellsRow(["Non-planted (background) candidates", fa.non_planted_candidates]),
      cellsRow(["False alarms: DealerWatch ESCALATE / REVIEW", `${fmtVal(fa.dealerwatch_escalate)} / ${fmtVal(fa.dealerwatch_review)}`]),
      cellsRow(["False alarms: baseline ESCALATE", fa.baseline_escalate]),
      cellsRow(["Case latency p50 / p95 / max", `${fmtVal(lat.p50)} / ${fmtVal(lat.p95)} / ${fmtVal(lat.max)} ms (n ${fmtVal(lat.n)})`]),
      cellsRow(["Pipeline total", `${fmtVal(run.total_ms)} ms`]),
    ]);
    const runInfo = table(["Run", "Value"], [
      cellsRow(["Generated", dateTime(ev.generated_at)]),
      cellsRow(["Candidates / planted / planted without candidate", `${fmtVal(ev.candidates)} / ${fmtVal(ev.planted)} / ${fmtVal(ev.planted_without_candidate)}`]),
      cellsRow(["Orders / trades / calls", `${fmtVal(run.orders)} / ${fmtVal(run.trades)} / ${fmtVal(run.calls)}`]),
      cellsRow(["LLM provider (calls, fallbacks)", `${run.llm_provider} (${fmtVal(run.llm_calls)}, ${fmtVal(run.llm_fallbacks)})`]),
      cellsRow(["ASR provider", run.asr_provider]),
    ]);
    const planted = (ev.rows || []).filter((r) => r.label);
    const rows = table(["Order", "Account", "Label", "Expected", "DealerWatch", "Baseline", "Score", "Case"],
      planted.map((r) => cellsRow([r.order_id, r.account_id, r.label, r.expected, verdict(r.produced, r.expected),
        verdict(r.baseline, r.expected), r.score === null ? "—" : r.score.toFixed(2), openCaseButton(r.case_id, r.evaluation_case_id)], 6)));
    body.replaceChildren(kpis,
      h("div", { class: "eval-grid" },
        section("ESCALATE: DealerWatch vs rules-only baseline", metricsTable(dw, base)),
        section("Confusion counts (ESCALATE)", h("div", { class: "cm-pair" }, confusion("DealerWatch", dw), confusion("Rules-only baseline", base)))),
      section("Per label (planted cases)", perLabel),
      h("div", { class: "eval-grid" }, section("Abstain, false alarms, latency", other), section("Run", runInfo)),
      section(`Planted cases (${planted.length})`, rows));
  }
  async function loadEval(refresh) {
    if (!canRead() || (refresh && (!canAdmin() || state.busy || runInProgress()))) return;
    const body = $("eval-body");
    body.replaceChildren(h("div", { class: "muted", text: refresh ? "Re-running evaluation…" : "Loading evaluation…" }));
    if (refresh) setBusy(true, "Running eval…");
    try {
      const ev = await api(`/api/eval${refresh ? "?refresh=true" : ""}`);
      if (!canRead()) return;
      state.evalLoaded = true;
      renderEval(ev);
    } catch (e) {
      body.replaceChildren(h("div", { class: "reject", text: `Evaluation unavailable: ${e.message}` }));
    } finally {
      if (refresh) { setBusy(false); loadHealth(); }
    }
  }

  // ---------- wiring ----------
  function readReviewer() {
    try { return localStorage.getItem(REVIEWER_KEY) || "Compliance Officer"; } catch { return "Compliance Officer"; }
  }
  function saveReviewer(value) {
    try { localStorage.setItem(REVIEWER_KEY, value); } catch { /* storage unavailable */ }
  }
  function wire() {
    const tabs = [...document.querySelectorAll(".tab")];
    for (const btn of tabs) {
      btn.id = `tab-${btn.dataset.tab}`;
      btn.setAttribute("aria-controls", `view-${btn.dataset.tab}`);
      const panel = $(`view-${btn.dataset.tab}`);
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", btn.id);
      btn.addEventListener("click", () => showTab(btn.dataset.tab));
      btn.addEventListener("keydown", (event) => {
        const index = tabs.indexOf(btn);
        const next = event.key === "ArrowRight" ? (index + 1) % tabs.length
          : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length
            : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
        if (next >= 0) { event.preventDefault(); tabs[next].focus(); showTab(tabs[next].dataset.tab); }
      });
    }
    $("login-form").addEventListener("submit", signIn);
    $("logout-btn").addEventListener("click", signOut);
    $("session-retry").addEventListener("click", async () => { if (await loadSession()) await loadWorkspace(); });
    $("queue-search").addEventListener("submit", (event) => { event.preventDefault(); loadCases(state.selectedId); });
    $("filter-rec").addEventListener("change", () => loadCases(state.selectedId));
    $("filter-status").addEventListener("change", () => loadCases(state.selectedId));
    $("queue-clear").addEventListener("click", () => {
      for (const id of ["filter-query", "filter-scrip", "filter-dealer", "filter-rec", "filter-status"]) $(id).value = "";
      loadCases(state.selectedId);
    });
    $("queue-export").addEventListener("click", () => download(`/api/export/cases.csv${state.queueParams ? `?${state.queueParams}` : ""}`, "dealerwatch-cases.csv"));
    $("case-export").addEventListener("click", () => {
      if (state.detail) download(`/api/cases/${encodeURIComponent(state.detail.case_id)}/export`, `${state.detail.case_id}-evidence.json`);
    });
    $("overview-refresh").addEventListener("click", loadOverview);
    $("data-refresh").addEventListener("click", loadDataReport);
    $("data-export").addEventListener("click", () => download("/api/data/export", "dealerwatch-dataset.json"));
    $("dataset-file").addEventListener("change", readDatasetFile);
    $("dataset-json").addEventListener("input", () => $("data-candidate-report").replaceChildren());
    $("data-validate").addEventListener("click", () => submitDataset(false));
    $("data-import").addEventListener("click", () => submitDataset(true));
    $("runs-refresh").addEventListener("click", loadRuns);
    $("run-retry-poll").addEventListener("click", () => { state.runPollErrors = 0; pollRun(); });
    $("run-btn").addEventListener("click", rerunPipeline);
    for (const btn of document.querySelectorAll("#decision-bar [data-action]")) btn.addEventListener("click", () => decide(btn.dataset.action));
    const reviewer = $("reviewer");
    reviewer.value = readReviewer();
    reviewer.addEventListener("change", () => saveReviewer(reviewer.value.trim()));
    $("ledger-verify").addEventListener("click", verifyLedger);
    $("ledger-tamper").addEventListener("click", tamperLedger);
    $("ledger-restore").addEventListener("click", restoreLedger);
    $("ledger-prev").addEventListener("click", () => { state.ledgerOffset = Math.max(0, state.ledgerOffset - state.ledgerLimit); loadLedger().catch((e) => toast(e.message, true)); });
    $("ledger-next").addEventListener("click", () => { state.ledgerOffset += state.ledgerLimit; loadLedger().catch((e) => toast(e.message, true)); });
    $("eval-refresh").addEventListener("click", () => loadEval(true));
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || state.tab !== "cases" || $("confirm").open) return;
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        moveSelection(e.key === "j" ? 1 : -1);
      }
    });
    let resizeTimer = 0;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => { if (state.tab === "cases") renderCharts(); }, 150);
    });
  }
  async function loadWorkspace(wanted = null) {
    const tasks = [loadHealth(), loadCases(wanted || state.selectedId), loadRuns()];
    if (state.tab === "overview") tasks.push(loadOverview());
    if (state.tab === "data") tasks.push(loadDataReport());
    if (state.tab === "ledger") tasks.push(loadLedger().catch((e) => toast(`Ledger: ${e.message}`, true)));
    if (state.tab === "eval") tasks.push(loadEval(false));
    await Promise.all(tasks);
  }
  async function init() {
    wire();
    const parts = location.hash.replace(/^#\/?/, "").split("/");
    const tab = ["overview", "cases", "data", "runs", "ledger", "eval"].includes(parts[0]) ? parts[0] : "cases";
    let wanted = null;
    try { wanted = tab === "cases" && parts[1] ? decodeURIComponent(parts[1]) : null; } catch { /* ignore a malformed bookmark */ }
    showTab(tab, false);
    if (await loadSession()) await loadWorkspace(wanted);
  }
  init().catch((error) => toast(`Could not start the interface: ${error.message}`, true));
})();
