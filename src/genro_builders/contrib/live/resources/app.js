// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
// SPA client for the live HTML demo.
//
// Opens a WebSocket to the same server, sends the editor's Python snippet
// to the `repl` route, and on each successful response reloads the
// rendered document in the left iframe (served as out.html) and redraws
// the source/data trees. The editor is a plain <textarea>, optionally
// upgraded to CodeMirror when that library is reachable (progressive
// enhancement with a clean fallback).

(function () {
  "use strict";

  const $iframe = document.getElementById("render-iframe");
  const $sourceTree = document.getElementById("source-tree");
  const $dataTree = document.getElementById("data-tree");
  const $history = document.getElementById("history");
  const $editor = document.getElementById("editor");
  const $run = document.getElementById("run");
  const $status = document.getElementById("status");
  const $demoSelect = document.getElementById("demo-select");
  const $render = document.getElementById("render");
  const $tabRendered = document.getElementById("tab-rendered");
  const $tabRaw = document.getElementById("tab-raw");
  const $tabSource = document.getElementById("tab-source");
  const $rawView = document.getElementById("raw-view");
  const $sourceView = document.getElementById("source-view");

  // The SPA shell is served by the mounted app at GET /<mount>/index, so
  // location.pathname is "/<mount>/index". Stripping "/index" leaves the
  // URL prefix to talk to the same app's routes (HTTP and WebSocket).
  const APP_PREFIX = (function () {
    const p = location.pathname.replace(/\/index\/?$/, "");
    return p.endsWith("/") ? p : p + "/";
  })();

  const pending = new Map();
  let ws = null;
  let nextId = 1;

  // CodeMirror instance, set if the enhancement loads. Null → use textarea.
  let cm = null;

  const sourceExpanded = new Set();
  const dataExpanded = new Set();

  // -----------------------------------------------------------
  // Status bar
  // -----------------------------------------------------------

  function setStatus(text, ok) {
    $status.textContent = text;
    $status.classList.toggle("disconnected", !ok);
  }

  // -----------------------------------------------------------
  // History (terminal-style: append at the bottom, auto-scroll)
  // -----------------------------------------------------------

  function appendEntry(html) {
    const div = document.createElement("div");
    div.className = "entry";
    div.innerHTML = html;
    $history.appendChild(div);
    $history.scrollTop = $history.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // -----------------------------------------------------------
  // Editor — textarea, optionally upgraded to CodeMirror
  // -----------------------------------------------------------

  function editorValue() {
    return cm ? cm.getValue() : $editor.value;
  }

  function clearEditor() {
    if (cm) cm.setValue("");
    else $editor.value = "";
  }

  // Try to upgrade the textarea to CodeMirror. If the library is not
  // present (CDN unreachable, offline), this is a no-op and the plain
  // textarea keeps working.
  function tryEnhanceEditor() {
    if (typeof window.CodeMirror !== "function") return;
    cm = window.CodeMirror.fromTextArea($editor, {
      mode: "python",
      lineNumbers: true,
      indentUnit: 4,
      theme: "default",
    });
    cm.setSize("100%", "100%");
    // Ctrl/Cmd+Enter runs from inside CodeMirror.
    cm.setOption("extraKeys", {
      "Ctrl-Enter": runSnippet,
      "Cmd-Enter": runSnippet,
    });
  }

  // Read-only viewers: 'raw' (current document as XML) and 'source' (the
  // demo's Python). Upgrade to CodeMirror when available; otherwise the
  // readonly <textarea>s show the text. The CodeMirror wrapper gets a
  // cm-raw/cm-source class so the stylesheet can show one at a time.
  let rawCm = null;
  let sourceCm = null;

  function _enhance(textarea, mode, cssClass) {
    if (typeof window.CodeMirror !== "function") return null;
    const cm = window.CodeMirror.fromTextArea(textarea, {
      mode: mode, lineNumbers: true, readOnly: true, theme: "default",
    });
    cm.setSize("100%", "100%");
    cm.getWrapperElement().classList.add(cssClass);
    return cm;
  }

  function tryEnhanceViewers() {
    rawCm = _enhance($rawView, "xml", "cm-raw");
    sourceCm = _enhance($sourceView, "python", "cm-source");
  }

  function setRawText(text) {
    if (rawCm) { rawCm.setValue(text); if ($render.classList.contains("show-raw")) rawCm.refresh(); }
    else $rawView.value = text;
  }

  function setSourceText(text) {
    if (sourceCm) { sourceCm.setValue(text); if ($render.classList.contains("show-source")) sourceCm.refresh(); }
    else $sourceView.value = text;
  }

  // Fetch the current document as raw XML (out_xml route) and show it.
  function fetchRaw() {
    fetch(APP_PREFIX + "out_xml?t=" + Date.now())
      .then(function (r) { return r.text(); })
      .then(setRawText)
      .catch(function () { /* offline / route missing: leave as-is */ });
  }

  function showTab(which) {
    $render.classList.toggle("show-raw", which === "raw");
    $render.classList.toggle("show-source", which === "source");
    $tabRendered.classList.toggle("active", which === "rendered");
    $tabRaw.classList.toggle("active", which === "raw");
    $tabSource.classList.toggle("active", which === "source");
    if (which === "raw" && rawCm) rawCm.refresh();
    if (which === "source" && sourceCm) sourceCm.refresh();
  }

  // -----------------------------------------------------------
  // Tree renderer (source and data share the same building blocks)
  //
  // Expand/collapse state is keyed by a stable path string built from the
  // tree structure. Re-rendering keeps the open nodes open.
  // -----------------------------------------------------------

  function renderSourceTree(container, root) {
    container.innerHTML = "";
    const ul = document.createElement("ul");
    (root.children || []).forEach(function (node, idx) {
      ul.appendChild(buildSourceNode(node, idx + "", sourceExpanded));
    });
    container.appendChild(ul);
  }

  function renderDataTree(container, root) {
    container.innerHTML = "";
    const ul = document.createElement("ul");
    (root.children || []).forEach(function (entry, idx) {
      ul.appendChild(buildDataEntry(entry, idx + "", dataExpanded));
    });
    container.appendChild(ul);
  }

  function buildSourceNode(node, path, openSet) {
    const li = document.createElement("li");
    const hasChildren = node.value && node.value.kind === "bag";
    const open = openSet.has(path);
    const caret = document.createElement("span");
    caret.className = "caret" + (hasChildren ? "" : " empty");
    caret.textContent = hasChildren ? (open ? "▼" : "▶") : "·";
    if (hasChildren) {
      caret.addEventListener("click", function () {
        if (openSet.has(path)) openSet.delete(path);
        else openSet.add(path);
        const newLi = buildSourceNode(node, path, openSet);
        li.replaceWith(newLi);
      });
    }
    li.appendChild(caret);

    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = " " + node.tag;
    li.appendChild(tag);

    const label = document.createElement("span");
    label.className = "label";
    label.textContent = "  " + node.label;
    li.appendChild(label);

    Object.keys(node.attrs || {}).forEach(function (k) {
      const ak = document.createElement("span");
      ak.className = "attr-k";
      ak.textContent = "  " + k + "=";
      li.appendChild(ak);
      const av = document.createElement("span");
      av.className = "attr-v";
      av.textContent = JSON.stringify(node.attrs[k]);
      li.appendChild(av);
    });

    if (node.value && node.value.kind === "pointer") {
      const p = document.createElement("span");
      p.className = "pointer";
      p.textContent = "  " + node.value.raw;
      li.appendChild(p);
    } else if (node.value && node.value.kind === "literal") {
      const t = document.createElement("span");
      t.className = "literal";
      t.textContent = "  " + JSON.stringify(node.value.raw);
      li.appendChild(t);
    }

    if (hasChildren && open) {
      const ul = document.createElement("ul");
      (node.children || []).forEach(function (child, idx) {
        ul.appendChild(buildSourceNode(child, path + "/" + idx, openSet));
      });
      li.appendChild(ul);
    }
    return li;
  }

  function buildDataEntry(entry, path, openSet) {
    const li = document.createElement("li");
    const hasChildren = entry.kind === "bag";
    const open = openSet.has(path);
    const caret = document.createElement("span");
    caret.className = "caret" + (hasChildren ? "" : " empty");
    caret.textContent = hasChildren ? (open ? "▼" : "▶") : "·";
    if (hasChildren) {
      caret.addEventListener("click", function () {
        if (openSet.has(path)) openSet.delete(path);
        else openSet.add(path);
        const newLi = buildDataEntry(entry, path, openSet);
        li.replaceWith(newLi);
      });
    }
    li.appendChild(caret);

    const key = document.createElement("span");
    key.className = "key";
    key.textContent = " " + entry.key;
    li.appendChild(key);

    if (!hasChildren) {
      const val = document.createElement("span");
      val.className = "scalar";
      val.textContent = ": " + JSON.stringify(entry.value);
      li.appendChild(val);
    }

    if (hasChildren && open) {
      const ul = document.createElement("ul");
      (entry.children || []).forEach(function (child, idx) {
        ul.appendChild(buildDataEntry(child, path + "/" + idx, openSet));
      });
      li.appendChild(ul);
    }
    return li;
  }

  // Open the root paths by default so the first render shows content
  // without requiring a manual click.
  function seedDefaultExpansion() {
    sourceExpanded.add("0");
    dataExpanded.add("0");
  }

  // -----------------------------------------------------------
  // Iframe reload — the rendered HTML lives in out.html, which
  // page.live() rewrites on every mutation. We just reload it.
  // -----------------------------------------------------------

  function reloadIframe() {
    $iframe.src = APP_PREFIX + "out?t=" + Date.now();
    fetchRaw();
  }

  // Two-way binding. The rendered document carries data-<name>-pointer
  // attributes (emitted when include_datapath is on). On `change` of an
  // edited control we read the pointer holding the absolute data path and
  // write the new value back via the set_value route. `change` (not
  // `input`) fires on blur, so the iframe reload does not steal focus
  // mid-typing. Re-bound on every reload because the iframe swaps document.
  function bindIframeInputs() {
    const doc = $iframe.contentDocument;
    if (!doc) return;
    doc.addEventListener("change", function (e) {
      const el = e.target;
      const ds = el.dataset || {};
      if (ds.checkedPointer) {
        sendCommand("set_value", { path: ds.checkedPointer, value: el.checked });
      } else if (ds.valuePointer) {
        sendCommand("set_value", { path: ds.valuePointer, value: el.value });
      }
    });
  }
  $iframe.addEventListener("load", bindIframeInputs);

  // -----------------------------------------------------------
  // WebSocket lifecycle and message handlers
  // -----------------------------------------------------------

  function runSnippet() {
    const source = editorValue();
    if (!source.trim()) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      appendEntry('<span class="entry-err">not connected</span>');
      return;
    }
    const id = String(nextId++);
    const wsx = {
      id: id,
      method: "POST",
      path: APP_PREFIX + "repl",
      query: { source: source },
    };
    pending.set(id, { source: source });
    ws.send("WSX://" + JSON.stringify(wsx));
    appendEntry('<span class="entry-cmd">&gt; ' +
      escapeHtml(source) + "</span>");
    clearEditor();
  }

  // Fire-and-track a WSX command (menu/select/tree_*) with no editor echo.
  function sendCommand(cmd, query) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const id = String(nextId++);
    ws.send("WSX://" + JSON.stringify({
      id: id, method: "POST", path: APP_PREFIX + cmd, query: query || {},
    }));
  }

  function applyTrees(data) {
    if (!data || typeof data !== "object") return;
    if (data.source) renderSourceTree($sourceTree, data.source);
    if (data.data) renderDataTree($dataTree, data.data);
  }

  function populateMenu(data) {
    $demoSelect.innerHTML = "";
    (data.demos || []).forEach(function (d) {
      const opt = document.createElement("option");
      opt.value = d.key;
      opt.textContent = d.title;
      if (d.key === data.current) opt.selected = true;
      $demoSelect.appendChild(opt);
    });
  }

  function handleResponse(msg) {
    pending.delete(msg.id);
    const data = msg.data;
    if (msg.status !== 200 || (data && data.ok === false)) {
      const err = data && data.error ? data.error : "status " + msg.status;
      appendEntry('<span class="entry-err">! ' + escapeHtml(err) + "</span>");
      return;
    }
    // A menu response carries the demo list.
    if (data && data.demos) {
      populateMenu(data);
      return;
    }
    // A source_code response carries the current demo's Python source.
    if (data && typeof data.source_code === "string") {
      setSourceText(data.source_code);
      return;
    }
    applyTrees(data);
    reloadIframe();
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = proto + "//" + location.host + APP_PREFIX;
    setStatus("connecting…", false);
    ws = new WebSocket(url);
    ws.onopen = function () {
      setStatus("connected", true);
      seedDefaultExpansion();
      reloadIframe();
      // Populate the demo menu, the current demo's trees and source.
      sendCommand("menu");
      sendCommand("tree_source");
      sendCommand("tree_data");
      sendCommand("source_code");
    };
    ws.onclose = function () {
      setStatus("disconnected — retrying in 2s", false);
      setTimeout(connect, 2000);
    };
    ws.onerror = function () {
      setStatus("error", false);
    };
    ws.onmessage = function (event) {
      let raw = event.data;
      if (typeof raw !== "string") return;
      if (raw.startsWith("WSX://")) raw = raw.slice(6);
      try {
        const msg = JSON.parse(raw);
        if (msg.id != null) handleResponse(msg);
      } catch (e) {
        appendEntry('<span class="entry-err">parse error: ' +
          escapeHtml(String(e)) + "</span>");
      }
    };
  }

  // Demo selector: switching re-renders the chosen demo and refreshes
  // trees and source.
  $demoSelect.addEventListener("change", function () {
    sendCommand("select", { key: $demoSelect.value });
    sendCommand("source_code");
    appendEntry('<span class="entry-meta">— switched to ' +
      escapeHtml($demoSelect.value) + " —</span>");
  });

  // Left-pane tabs: Rendered (iframe) | Source (read-only Python).
  $tabRendered.addEventListener("click", function () { showTab("rendered"); });
  $tabRaw.addEventListener("click", function () { showTab("raw"); });
  $tabSource.addEventListener("click", function () { showTab("source"); });

  // Run button + Ctrl/Cmd+Enter on the plain textarea.
  $run.addEventListener("click", runSnippet);
  $editor.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      runSnippet();
    }
  });

  tryEnhanceEditor();
  tryEnhanceViewers();
  connect();
})();
