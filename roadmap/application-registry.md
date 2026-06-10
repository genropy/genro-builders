# Application registry — il desktop, il registro delle pagine vive, il filo unico

**Version**: 1.0.0
**Last Updated**: 2026-06-10
**Status**: 🟢 APPROVATO — design dell'area `APP` (contratto v0.8.0);
implementazione da fare. Verbale della discussione del 2026-06-10
(sera), a valle della rifondazione di ws_live sul ciclo legacy
(`legacy-client-architecture.md`).

---

## 1. Il desktop (l'index del legacy, rifondato)

Il pattern utente tipico: una **index page** con il menu di
navigazione ad albero a sinistra e a destra uno **stack container**
(tab): ogni voce di menu apre un pane con la pagina scelta (una
webpage di un package).

Decisioni:

- **I pane sono IFRAME, per ora**: ogni pane ospita una pagina
  indipendente. L'iframe è anche il **veicolo di migrazione**: un pane
  può ospitare una pagina genropy LEGACY accanto alle pagine nuove —
  la shell nuova è il guscio dentro cui l'app legacy migra pezzo per
  pezzo. I pane *nativi* (builder montati sullo stesso handler — il
  multibuilder è nato per questo) sono l'evoluzione, non il primo
  passo.
- La **shell** è una pagina ws_live: i suoi punti di riempimento
  (menu, stack, header...) sono il caso guida di `@slot` (`PAG.6`);
  il menu ad albero è un component ricorsivo su una bag-menu
  (`tree_item(iterate="^menu")`, cfr. esempio `with_data/11`).

## 2. Il registro delle pagine vive (il gnrdaemon dissolto)

Nel legacy la pagina **moriva a ogni richiesta**: ogni RPC
re-istanziava la `GnrWebPage`; lo stato viveva nel site register via
**gnrdaemon** (i worker WSGI erano processi separati) e ogni giro
pagava ricostruzione + serializzazione + viaggio verso il daemon.

In async il prezzo sparisce alla radice: un processo, un loop,
**oggetti vivi**. La pagina non si ricostruisce: builder (source +
data) e handler restano in memoria, una chiamata è l'invocazione di
un metodo su un oggetto vivo. Il registro È l'Application:

```
Application
└── registro pagine vive: {chiave → (builder: source+data, handler)}
        oggi:   per-connessione (ws.state.pages — già in ws_live)
        domani: per-SESSIONE (chiave stabile, es. page_id)
```

- **Scope per-connessione** (primo passo, già implementato in
  ws_live): cade il socket → pagine perse, il client riparte da
  ``main``.
- **Scope per-sessione** (evoluzione): chiave stabile data allo
  startup → il client che si riconnette **si riattacca alla pagina
  viva** (source e dati intatti, full render corrente e si riparte).
  È il "resume" che il legacy comprava col daemon, gratis e senza
  serializzare.
- Il prezzo da progettare è il **ciclo di vita**: chiusura pane
  dichiarata dal client (unregister del satellite, §3), timeout di
  sessione, eviction a memoria.

## 3. Un solo websocket: master e satelliti

**Un filo per desktop.** L'index possiede l'UNICO websocket (client
master); le pagine negli iframe sono **satelliti**: al boot scoprono
`window.parent.genro` (stessa origin — l'aggancio che il legacy già
usa in `genro.js:618-626` per il cross-window) e vi si registrano;
le loro `call` passano dal master, le patch tornano instradate.

- la **busta guadagna la chiave di routing** (`page`/mount): il
  master smista al satellite giusto — ed è la stessa chiave che
  servirà ai pane nativi: il protocollo non cambierà nella
  migrazione iframe→nativo;
- **lato server**: una connessione = un desktop intero; il registro
  di connessione contiene tutte le pagine vive di quel browser tab,
  e il push server-initiated raggiunge qualunque pagina su un filo
  solo;
- la comunicazione **tra pagine** (l'erede di `genro.som`): segmento
  `_` sul server, o direttamente dal master client;
- **lifecycle**: iframe chiuso → unregister del satellite → il
  server smonta la pagina (il "chi muore e quando" del §2, risolto
  dal canale stesso);
- se muore l'index muore tutto: accettabile, È il desktop.

**Nota storica (verificata 2026-06-10)**: il legacy attuale NON tiene
il ws solo sull'index — ogni pagina wsk-abilitata apre il proprio
socket (`gnrwebpage.py:1330` setta `websockets_url` per ogni pagina;
`genro.js:590` fa `wsk.create()` incondizionato). Dal parent passano
publish/eventi/shared objects, non il filo col server. Il
master/satelliti è quindi un **miglioramento**, non un porting.

**Simmetria**: il satellite-routing è la versione client del
multibuilder — N pagine, un canale, segmenti. Stessa forma ai due
capi del filo.

## 4. Ordine di lavoro

1. Push sulla connessione (ponte flush-sync → send-async): le patch
   da qualunque `live()` raggiungono il client senza richiesta.
2. Shell desktop: index ws_live con tree (component ricorsivo) +
   stack a iframe; busta con chiave di routing; satelliti.
3. Registro per-sessione (riattacco) + lifecycle.
4. Pane nativi (multibuilder sullo stesso handler; id DOM
   qualificati per mount) — quando i casi d'uso lo chiederanno.

## Riferimenti

- `legacy-client-architecture.md` — lo studio del client e del ciclo
  pagina legacy.
- Contratto v0.8.0, aree `APP`, `PAG.6`, `CMP`, `RX`.
- Sessione (Claude Code): `a47d7ab4-be22-42aa-b2e9-bb0e198e6b40`
  (2026-06-10).
