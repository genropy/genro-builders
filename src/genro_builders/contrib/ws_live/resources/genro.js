// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
//
// GenroClient — the ws_live client, on the legacy page cycle refounded:
// the startup page is the same for every page; the client connects the
// websocket, asks `main` for the rendered HTML of the main div, then
// keeps the DOM live by applying the patch batches the server sends
// ({id, op, html} — id is the node's structural path).
//
// The op vocabulary is open: `replace` (outer fragment) is the workhorse;
// finer ops (set_attrs, set_text) will ride the same envelope.

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
      replace: (patch) => {
        var el = document.getElementById(patch.id);
        if (!el || el === document.activeElement) return;
        el.outerHTML = patch.html;
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

  // Apply a patch batch. The element that currently has focus is never
  // swapped (replacing a live <input type=color> would close the native
  // picker mid-drag): its own value is already right, the OTHER readers
  // update.
  applyPatches(patches) {
    patches.forEach((patch) => {
      var op = this.ops[patch.op];
      if (op) op(patch);
    });
    this.bindInputs();
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
    main.removeEventListener("input", this._inputHandler);
    main.addEventListener("input", this._inputHandler);
  }

  onInput(e) {
    var el = e.target;
    if (!el || !el.matches("input, select, textarea")) return;
    var path = el.getAttribute("data-value-pointer");
    if (!path) return;
    var value = el.value;
    if (this._inputTimer) clearTimeout(this._inputTimer);
    this._inputTimer = setTimeout(() => {
      this._inputTimer = null;
      this.setData(path, value);
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

  setData(path, value) {
    this.call("mutate", { page: this.page, path: path, value: value });
  }
}

window.GenroClient = GenroClient;
