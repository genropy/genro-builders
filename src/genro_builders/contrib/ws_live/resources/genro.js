// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
//
// GenroClient — the ws_live client, on the legacy page cycle refounded:
// the startup page is the same for every page; the client connects the
// websocket, asks `main` for the rendered HTML of the main div, then
// keeps the DOM live by applying the patch batches the server sends
// ({id, op, ...} — id is the node's target_id serial).
//
// The op vocabulary is open: `replace` (outer fragment) is the workhorse,
// `insert`/`remove` are the structural pair (a node attached to or
// dropped from the source); finer ops (set_attrs, set_text) will ride
// the same envelope.

class GenroClient {
  constructor(kw) {
    this.page = kw.page;
    this.pending = {};
    this.nextId = 1;
    this.ws = null;
    // Served at /<mount>/page/<key>: the WSX prefix is everything up to
    // and including the mount (drop "page/<key>").
    var parts = location.pathname.replace(/\/+$/, "").split("/");
    this.wsPrefix = parts.slice(0, -2).join("/") + "/";
    this.ops = {
      // Replace applies BY DIFFERENCE (morph): the existing DOM is
      // updated in place, matched elements survive as objects — an
      // engaged input is never disconnected (the native color picker
      // panel closes on disconnection, transplanting back does not
      // reopen it), an iframe never reloads while its block updates.
      replace: (patch) => {
        var el = document.getElementById(patch.id);
        if (!el) return;
        var tpl = document.createElement("template");
        tpl.innerHTML = patch.html;
        var fresh = tpl.content.firstElementChild;
        if (fresh) this.morph(el, fresh);
      },
      // The new fragment lands before its anchor sibling (`before`),
      // or appended to the container (`id`; null = the main div).
      insert: (patch) => {
        if (patch.before) {
          var ref = document.getElementById(patch.before);
          if (ref) ref.insertAdjacentHTML("beforebegin", patch.html);
          return;
        }
        var container = patch.id
          ? document.getElementById(patch.id) : this.mainWindow();
        if (container) container.insertAdjacentHTML("beforeend", patch.html);
      },
      remove: (patch) => {
        var el = document.getElementById(patch.id);
        if (el) el.remove();
      },
    };
    this._onReady(() => this.connect());
  }

  _onReady(cb) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", cb);
    } else {
      cb();
    }
  }

  // ---------------------------------------------------------------- dom
  mainWindow() {
    return document.getElementById("mainWindow");
  }

  setStatus(t) {
    document.body.setAttribute("data-gnr-status", t);
  }

  // Apply a patch batch. Replaces are morphed (see ops.replace): the
  // element the user is interacting with is never disconnected, so
  // focus, caret and the native picker panel survive every round-trip
  // and intermediate drag events keep flowing by default.
  applyPatches(patches) {
    patches.forEach((patch) => {
      var op = this.ops[patch.op];
      if (op) op(patch);
    });
    this.bindInputs();
  }

  // ---------------------------------------------------------------- morph
  // In-place DOM update: el is mutated to match `fresh`, preserving
  // every element object it can. Children are matched by id — the
  // reactive render puts a target_id serial on EVERY element, so the
  // match is identity-driven, not heuristic. The focused form control
  // is SOVEREIGN: its value/checked are never touched (its own edits
  // are already the truth; everything else around it updates).
  morph(el, fresh) {
    if (el.tagName !== fresh.tagName) {
      el.replaceWith(fresh);
      return;
    }
    var sovereign = el === document.activeElement
      && el.matches("input, select, textarea");
    this.syncAttrs(el, fresh, sovereign);
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      if (!sovereign) {
        el.value = fresh.value;
        if (el.type === "checkbox") el.checked = fresh.checked;
      }
      return;
    }
    this.morphChildren(el, fresh);
    if (el.tagName === "SELECT" && !sovereign) el.value = fresh.value;
  }

  syncAttrs(el, fresh, sovereign) {
    var skip = (name) =>
      sovereign && (name === "value" || name === "checked");
    Array.from(el.attributes).forEach((attr) => {
      if (!fresh.hasAttribute(attr.name) && !skip(attr.name)) {
        el.removeAttribute(attr.name);
      }
    });
    Array.from(fresh.attributes).forEach((attr) => {
      if (skip(attr.name)) return;
      if (el.getAttribute(attr.name) !== attr.value) {
        el.setAttribute(attr.name, attr.value);
      }
    });
  }

  morphChildren(el, fresh) {
    var oldById = {};
    for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
      if (c.id) oldById[c.id] = c;
    }
    var current = el.firstChild;
    var target = fresh.firstChild;
    while (target) {
      var next = target.nextSibling;
      var matched = null;
      if (target.nodeType === 1 && target.id && oldById[target.id]) {
        matched = oldById[target.id];
      } else if (
        current && current.nodeType === target.nodeType
        && (target.nodeType !== 1
            || (!target.id && !current.id
                && current.tagName === target.tagName))
      ) {
        matched = current;
      }
      if (matched) {
        if (matched === current) {
          current = current.nextSibling;
        } else {
          el.insertBefore(matched, current);   // pulled into position
        }
        if (matched.nodeType === 1) {
          this.morph(matched, target);
        } else if (matched.nodeValue !== target.nodeValue) {
          matched.nodeValue = target.nodeValue;
        }
      } else {
        el.insertBefore(target, current);      // adopt the fresh node
      }
      target = next;
    }
    while (current) {                          // leftovers: server truth
      var nextOld = current.nextSibling;
      el.removeChild(current);
      current = nextOld;
    }
  }

  // An input change writes its value back to the bound data path: the
  // render emits `data-value-pointer` (absolute datapath) on bound
  // inputs. Debounced by 10ms so a fast drag sends only the last value
  // of each window.
  bindInputs() {
    var main = this.mainWindow();
    if (!main) return;
    if (!this._inputHandler) {
      this._inputHandler = (e) => this.onInput(e);
    }
    if (!this._clickHandler) {
      this._clickHandler = (e) => this.onClick(e);
    }
    main.removeEventListener("input", this._inputHandler);
    main.addEventListener("input", this._inputHandler);
    main.removeEventListener("click", this._clickHandler);
    main.addEventListener("click", this._clickHandler);
  }

  // A click on an element carrying `data-set-pointer` writes
  // `data-set-value` to that path: the click IS a mutation, riding the
  // same single road as the inputs (tab strips, menus, buttons).
  onClick(e) {
    var el = e.target.closest ? e.target.closest("[data-set-pointer]") : null;
    if (!el) return;
    this.setData(el.getAttribute("data-set-pointer"),
                 el.getAttribute("data-set-value"));
  }

  onInput(e) {
    var el = e.target;
    if (!el || !el.matches("input, select, textarea")) return;
    // A checkbox binds its state through `checked`, not `value` — and
    // el.checked is already typed (boolean), no dtype on the wire.
    var checkbox = el.type === "checkbox";
    var path = el.getAttribute(
      checkbox ? "data-checked-pointer" : "data-value-pointer");
    if (!path) return;
    var value, dtype = null;
    if (checkbox) {
      value = el.checked;
    } else {
      value = el.value;
      // Text trims by default (legacy TextBox trim=true); data-trim
      // ="false" opts out, passwords never trim.
      if (el.type !== "password"
          && el.getAttribute("data-trim") !== "false") {
        value = value.trim();
      }
      // The widget's declared dtype travels as a separate parameter
      // (an in-band value::dtype suffix would be injectable from a
      // textbox); an emptied typed field means "no datum" -> null.
      dtype = el.getAttribute("data-dtype");
      if (dtype && value === "") value = null;
    }
    if (this._inputTimer) clearTimeout(this._inputTimer);
    this._inputTimer = setTimeout(() => {
      this._inputTimer = null;
      this.setData(path, value, dtype);
    }, 10);
  }

  // ---------------------------------------------------------------- wsk
  connect() {
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    this.setStatus("connecting");
    this.ws = new WebSocket(proto + "//" + location.host + this.wsPrefix);
    this.ws.onopen = () => {
      this.setStatus("connected");
      this.main();
    };
    this.ws.onclose = () => {
      this.setStatus("disconnected");
      setTimeout(() => this.connect(), 2000);
    };
    this.ws.onerror = () => this.setStatus("error");
    this.ws.onmessage = (event) => this.onMessage(event);
  }

  call(method, params, cb) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    var id = String(this.nextId++);
    if (cb) this.pending[id] = cb;
    this.ws.send("WSX://" + JSON.stringify({
      id: id,
      method: "POST",
      path: this.wsPrefix + method,
      query: params,
    }));
  }

  onMessage(event) {
    var raw = event.data;
    if (typeof raw !== "string") return;
    if (raw.indexOf("WSX://") === 0) raw = raw.slice(6);
    var msg;
    try { msg = JSON.parse(raw); } catch (err) { return; }
    if (msg.status && msg.status !== 200) {
      this.setStatus("error");
      return;
    }
    var data = msg.data || {};
    var cb = msg.id && this.pending[msg.id];
    if (cb) {
      delete this.pending[msg.id];
      cb(data);
    }
    // Patches apply whatever the message: a mutate response today, a
    // server-initiated push tomorrow — same envelope, same road.
    if (Array.isArray(data.patches)) this.applyPatches(data.patches);
  }

  // ----------------------------------------------------------- lifecycle
  main() {
    this.call("main", { page: this.page }, (data) => {
      var main = this.mainWindow();
      main.innerHTML = data.html || "";
      main.classList.remove("waiting");
      this.bindInputs();
      this.setStatus("ready");
    });
  }

  setData(path, value, dtype) {
    var params = { page: this.page, path: path, value: value };
    if (dtype) params.dtype = dtype;
    this.call("mutate", params);
  }
}

window.GenroClient = GenroClient;
