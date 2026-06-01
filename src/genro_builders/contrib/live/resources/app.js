// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
// SPA client for the live HTML demo.
//
// Opens a WebSocket to the same server, parses REPL commands into WSX
// messages, sends them, and updates the right-hand iframe whenever the
// server's response includes an "html" field. It also renders the
// "source" and "data" trees as expand/collapse views.

(function () {
  "use strict";

  const $iframe = document.getElementById("render-iframe");
  const $sourceTree = document.getElementById("source-tree");
  const $dataTree = document.getElementById("data-tree");
  const $history = document.getElementById("history");
  const $cmd = document.getElementById("cmd");
  const $status = document.getElementById("status");

  // The SPA shell is served by the mounted app at
  //   GET /<mount>/index
  // so location.pathname is "/<mount>/index". Stripping "/index" leaves
  // the URL prefix we need to talk to the same app's routes (HTTP and
  // WebSocket alike). Defaults to "/" when no /index segment is present.
  const APP_PREFIX = (function () {
    const p = location.pathname.replace(/\/index\/?$/, "");
    return p.endsWith("/") ? p : p + "/";
  })();

  // Pending WSX requests indexed by id, so we can label responses with
  // the original command line in the history pane.
  const pending = new Map();
  let ws = null;
  let nextId = 1;

  // Expanded-state sets keyed by stable tree-path strings. Survive
  // re-renders so a mutation does not collapse every open node.
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
  // Command line parser
  //
  // Token rules:
  //   - whitespace separates tokens
  //   - "..." groups a single token (\\\" inside escapes the quote)
  //   - foo=bar makes a named argument; quoted RHS allowed (foo="x y")
  //   - bare 42 / true / false / null are coerced to their literals
  // -----------------------------------------------------------

  function tokenize(line) {
    const tokens = [];
    let i = 0;
    while (i < line.length) {
      while (i < line.length && /\s/.test(line[i])) i++;
      if (i >= line.length) break;
      let token = "";
      if (line[i] === '"') {
        i++;
        while (i < line.length && line[i] !== '"') {
          if (line[i] === "\\" && i + 1 < line.length) { token += line[i + 1]; i += 2; }
          else { token += line[i]; i++; }
        }
        i++; // closing "
        tokens.push({ raw: token, quoted: true });
      } else {
        while (i < line.length && !/\s/.test(line[i])) { token += line[i]; i++; }
        tokens.push({ raw: token, quoted: false });
      }
    }
    return tokens;
  }

  function coerce(tok) {
    if (tok.quoted) return tok.raw;
    const s = tok.raw;
    if (s === "true") return true;
    if (s === "false") return false;
    if (s === "null") return null;
    if (/^-?\d+$/.test(s)) return parseInt(s, 10);
    if (/^-?\d+\.\d+$/.test(s)) return parseFloat(s);
    return s;
  }

  function parseLine(line) {
    const tokens = tokenize(line);
    if (tokens.length === 0) return null;
    const cmd = tokens[0].raw;
    const positional = [];
    const named = {};
    for (let i = 1; i < tokens.length; i++) {
      const tok = tokens[i];
      const eq = tok.quoted ? -1 : tok.raw.indexOf("=");
      if (eq > 0) {
        const k = tok.raw.slice(0, eq);
        const rest = tok.raw.slice(eq + 1);
        named[k] = coerce({ raw: rest, quoted: false });
      } else {
        positional.push(coerce(tok));
      }
    }
    return { cmd, positional, named };
  }

  // Map positional args to named parameters so `set_data page.title "ciao"`
  // works without remembering keyword names. Unknown commands forward
  // positional args under p1/p2/... so the server can return a clean 404.
  const POSITIONAL_SCHEMAS = {
    render:        [],
    set_data:      ["path", "value"],
    get_data:      ["path"],
    keys:          ["path"],
    set_attr:      ["node_id", "attr", "value"],
    set_value:     ["node_id", "value"],
    add_child:     ["parent_id", "tag", "text"],
    remove_child:  ["parent_id", "label"],
    tree_source:   [],
    tree_data:     [],
  };

  function buildQuery(parsed) {
    const schema = POSITIONAL_SCHEMAS[parsed.cmd];
    const query = Object.assign({}, parsed.named);
    if (schema) {
      parsed.positional.forEach(function (val, i) {
        if (i < schema.length) query[schema[i]] = val;
      });
    } else {
      parsed.positional.forEach(function (val, i) { query["p" + (i + 1)] = val; });
    }
    return query;
  }

  // -----------------------------------------------------------
  // Tree renderer (source and data share the same building blocks)
  //
  // Expand/collapse state is keyed by a stable path string built from
  // the tree structure. Re-rendering keeps the open nodes open.
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
        // Local rebuild only — full re-render would lose user scroll.
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
  // WebSocket lifecycle and message handlers
  // -----------------------------------------------------------

  function send(line) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      appendEntry('<span class="entry-err">not connected</span>');
      return;
    }
    const parsed = parseLine(line);
    if (!parsed) return;
    const id = String(nextId++);
    const wsx = {
      id: id,
      method: "POST",
      path: APP_PREFIX + parsed.cmd,
      query: buildQuery(parsed),
    };
    pending.set(id, { cmd: parsed.cmd, line: line });
    ws.send("WSX://" + JSON.stringify(wsx));
    appendEntry('<span class="entry-cmd">&gt; ' + escapeHtml(line) + "</span>");
  }

  function applyResponseData(data) {
    if (!data || typeof data !== "object") return;
    if (typeof data.html === "string") $iframe.srcdoc = data.html;
    if (data.source) renderSourceTree($sourceTree, data.source);
    if (data.data) renderDataTree($dataTree, data.data);
  }

  function handleResponse(msg) {
    pending.delete(msg.id);
    const data = msg.data;
    if (msg.status !== 200) {
      const err = data && data.error ? data.error : "status " + msg.status;
      appendEntry('<span class="entry-err">! ' + escapeHtml(err) + "</span>");
      return;
    }
    applyResponseData(data);
    const summary = Object.keys(data || {})
      .filter(function (k) { return k !== "html" && k !== "source" && k !== "data"; })
      .map(function (k) { return k + "=" + JSON.stringify(data[k]); })
      .join(" ");
    appendEntry('<span class="entry-ok">' +
      (summary ? escapeHtml(summary) : "ok") + "</span>");
  }

  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = proto + "//" + location.host + APP_PREFIX;
    setStatus("connecting…", false);
    ws = new WebSocket(url);
    ws.onopen = function () {
      setStatus("connected", true);
      seedDefaultExpansion();
      // Pull initial state so the iframe and trees are populated.
      send("render");
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

  $cmd.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    const line = $cmd.value.trim();
    $cmd.value = "";
    if (line) send(line);
  });

  $cmd.focus();
  connect();
})();
