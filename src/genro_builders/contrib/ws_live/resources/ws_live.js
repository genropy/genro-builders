// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
//
// ws_live client — server-side reactive SPA, no iframe, no out.html.
//
// The page arrives already rendered (server-side, first paint). This
// script opens a WebSocket, captures input changes inside the left pane,
// sends them as `mutate` WSX messages, and replaces the left pane content
// with the re-rendered HTML the server returns.
//
// Step one: the server returns the WHOLE document; we extract the
// `.ws-left` subtree from it and swap only that. Partial render (a server
// that returns just the changed fragment) is a later refinement — the swap
// site is already isolated here.

(function () {
  "use strict";

  // The page is served at GET /<mount>/page/<key>, so location.pathname is
  // "/<mount>/page/<key>". The page key is the last segment; the WS prefix
  // is everything up to and including the mount (drop "page/<key>").
  var parts = location.pathname.replace(/\/+$/, "").split("/");
  var pageKey = parts[parts.length - 1];
  var wsPrefix = parts.slice(0, -2).join("/") + "/"; // ".../<mount>/"

  var ws = null;
  var nextId = 1;

  function statusText(t) {
    var el = document.querySelector(".ws-right");
    if (el) el.setAttribute("data-status", t);
  }

  // Apply partial-render patches: each is {id, html} for one node. We
  // find the element by id and swap its outerHTML — but never the element
  // that currently has focus (swapping the live <input type=color> would
  // close the native picker mid-drag). The focused input keeps its own
  // value; the other readers (e.g. the swatch) update.
  function applyPatches(patches) {
    var active = document.activeElement;
    patches.forEach(function (patch) {
      var el = document.getElementById(patch.id);
      if (!el) return;
      if (el === active) return;
      el.outerHTML = patch.html;
    });
    bindInputs();
  }

  // An input change writes its value back to the bound data path. The
  // render emits `data-value-pointer` (absolute datapath) on bound inputs
  // when include_datapath is on; we read it and send a mutate message.
  // We listen on `input` (fires continuously, e.g. while dragging the
  // color picker), debounced by 10ms so a fast drag sends only the last
  // value of each 10ms window instead of flooding the socket.
  var inputTimer = null;
  function onInput(e) {
    var el = e.target;
    if (!el || !el.matches("input, select, textarea")) return;
    var path = el.getAttribute("data-value-pointer");
    if (!path) return;
    var value = el.value;
    if (inputTimer) clearTimeout(inputTimer);
    inputTimer = setTimeout(function () {
      inputTimer = null;
      sendMutate(path, value);
    }, 10);
  }

  function bindInputs() {
    var left = document.querySelector(".ws-left");
    if (!left) return;
    left.removeEventListener("input", onInput);
    left.addEventListener("input", onInput);
  }

  function sendMutate(path, value) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    var id = String(nextId++);
    ws.send("WSX://" + JSON.stringify({
      id: id,
      method: "POST",
      path: wsPrefix + "mutate",
      query: { page: pageKey, path: path, value: value },
    }));
  }

  function onMessage(event) {
    var raw = event.data;
    if (typeof raw !== "string") return;
    if (raw.indexOf("WSX://") === 0) raw = raw.slice(6);
    var msg;
    try { msg = JSON.parse(raw); } catch (err) { return; }
    var data = msg.data;
    if (msg.status !== 200 || !data || data.ok === false) {
      statusText("error");
      return;
    }
    if (Array.isArray(data.patches)) applyPatches(data.patches);
  }

  function connect() {
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    var url = proto + "//" + location.host + wsPrefix;
    statusText("connecting");
    ws = new WebSocket(url);
    ws.onopen = function () { statusText("connected"); };
    ws.onclose = function () {
      statusText("disconnected");
      setTimeout(connect, 2000);
    };
    ws.onerror = function () { statusText("error"); };
    ws.onmessage = onMessage;
  }

  // The script is loaded in <head>, so the <body> may not exist yet:
  // defer the DOM-dependent setup until the document is parsed. The WS
  // connection itself does not need the DOM, but bindInputs() does.
  function start() {
    bindInputs();
    connect();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
