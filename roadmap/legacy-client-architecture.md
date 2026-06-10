# Legacy client architecture — studio di riferimento

**Version**: 1.0.0
**Last Updated**: 2026-06-10
**Status**: 🟢 RIFERIMENTO — studio del client legacy GenroPy (gnrjs) e del
ciclo pagina, a supporto del design di ws_live e del gemello JS
("un linguaggio, due interpreti", contratto v0.8 premessa).

Sorgenti esaminate: `genropy/gnrjs/gnr_d11/js/` (~50.000 righe, 27
moduli) e `genropy/gnrpy/gnr/web/`. I riferimenti file:riga sono
relativi a quel repo.

---

## 1. L'oggetto `genro` (gnr.GenroClient)

Facce specializzate istanziate in `genro.js:217-228`:

| Faccia | Classe | Ruolo |
|---|---|---|
| `genro.rpc` | GnrRpcHandler | RPC verso il server (HTTP, opz. WSK) |
| `genro.src` | GnrSrcHandler | source→DOM: build/rebuild dei nodi |
| `genro.wdg` | GnrWdgHandler | creazione widget (dijit) |
| `genro.dom` | GnrDomHandler | manipolazione DOM, CSS, eventi |
| `genro.wsk` | GnrWebSocketHandler | canale websocket (push server→client) |
| `genro.dlg`/`toast`/`dev`/`vld`/`som` | — | dialoghi, notifiche, debug, validazione, shared objects |

Metodi-dato diretti su `genro`: `setData`/`getData`/`getDataNode`
(`genro.js:1653-1760`), `fireDataTrigger` (1613), `publish`/`subscribe`
(pub/sub dojo), `dataTrigger` (1565, lo smistatore dei trigger).

## 2. Il doppio albero: GnrBag + GnrDomSource

- **`genro._data` è una GnrBag** (`gnrbag.js`): `setItem`/`getItem`/
  `getNode`, trigger nativi su `setValue` (`gnrbag.js:256-320` —
  evento `{evt: ins|upd|del, node, pathlist, oldvalue, value, reason,
  fired}`), resolver lazy client-side.
- **La pagina è una GnrDomSource, SOTTOCLASSE di GnrBag**
  (`gnrdomsource.js:28`): i nodi-source si "buildano" in widget
  (`build`, riga 929). Datapath e pointer risolti client-side:
  `absDatapath` risale gli antenati (688-729), `^` relativo (634),
  `==` formula (589). Attributi dinamici registrati al build
  (`registerNodeDynAttr`, 871-892) e sottoscritti al topic globale
  `_trigger_data`.

## 3. La catena mutazione→DOM e le tre granularità

```
setInClientData (ws) / setData (locale)
  → GnrBag.setItem → node.setValue → onNodeTrigger
  → genro.dataTrigger (genro.js:1565)
      - se NON serverChange: traccia in _serverstore_changes (per il server)
      - dojo.publish('_trigger_data')
  → ogni GnrDomSourceNode sottoscritto:
      getTriggerReason(path) → 'node' | 'container' | 'child'
      → updateAttrBuiltObj (gnrdomsource.js:1290+)
```

Le **tre granularità di aggiornamento** (`doUpdateAttrBuiltObj`, 1306):

1. **valore** → `widget.setValue(...)` (1463) — niente rebuild;
2. **attributo fine** → `setAttribute` — niente rebuild;
3. **strutturale** (es. cambia uno storepath pointer) → `rebuild()`
   (927): distruggi e ricostruisci il widget (`genro_src.js:89-259`
   per ins/upd/del dei nodi source).

**Convergenza notevole**: `node/container/child` è la STESSA
tripartizione di `_relevant_nodes` in genro-builders, ottenuta
indipendentemente — la classificazione è intrinseca al problema.

Identificazione dei nodi: `nodeId` + registry (`genro.src._index`,
`gnrdomsource.js:990-998`), backref `widget.sourceNode`, `datapath`
sugli antenati. (Nel modello nuovo: identità per path.)

## 4. Il canale websocket (gnrwebsocket.js)

Envelope a **comandi dichiarati** (`do_<command>`, righe 106-119 —
nessuna RPC arbitraria): `set`, `setInClientData` (148: path, value,
attributes, fired, reason, noTrigger), `datachanges`, `publish`,
`alert`. Client→server con token (`wstk_<n>`) e deferred.
ReconnectingWebSocket + ping. Il server spinge **DATI**, mai HTML: il
client ri-rende localmente.

## 5. Il ciclo pagina (lato server, gnrpy/gnr/web)

1. **Dispatch** — `gnrwsgisite.py:1211` (`_dispatcher`) → `UrlInfo`
   (90-155) risolve l'URL in `packages/<pkg>/webpages/<pagina>.py`
   (cache dei path); `ResourceLoader` (`gnrresourceloader.py:72-110`)
   importa e clona la classe pagina (`GnrWebPage`,
   `gnrwebpage.py:122`).
2. **Skeleton unico** — `gnr_d11/tpl/standard.tpl`: per tutte le
   pagine solo `<div id="mainWindow">` + `gnr_header.tpl`, che cicla
   `js_requires`/`css_requires` (dichiarati sulla classe pagina,
   estratti in `gnrresourceloader.py:155-165`) e istanzia il client
   inline: `var genro = new gnr.GenroClient({page_id: ...})`
   (`gnr_header.tpl:107-109`).
3. **La ricetta viaggia UNA volta** — al DOM ready `genro.start()`
   (`genro.js:571`) → `genro.src.getMainSource()` →
   `remoteCall('main')` (`genro_src.js:52`). Server: `rpc_main`
   (`gnrwebpage.py:2338`) → `self.main(rootwdg, **kwargs)` (2506, il
   `main` della webpage popola la Bag-ricetta) → `toXml`
   (`rpc.py:82`). Client: `genro.src.startUp(mainBagPage)` → build.
4. **Eventi → RPC → DB** — POST con `method=<nome>` → dispatch per
   prefisso `rpc_<nome>` (`getPublicMethod('rpc', ...)`,
   `gnrwebpage.py:1250`) → `self.db.table(...).insert/commit` →
   risultato Bag→XML.
5. **Websocket: opzionale** — fuori dal giro base; push server→client
   o `httpMethod='WSK'` sul componente (`genro_rpc.js:493`).

## 6. Corrispondenze col modello genro-builders

| Legacy | Modello nuovo |
|---|---|
| dispatcher + packages/webpages | Application + route (genro-asgi) |
| skeleton unico + `js/css_requires` | cornice di `WsLivePage` + famiglia `<domain>requires` (l'erede diretto, anche nel nome) |
| `rpc('main')` → ricetta XML → client costruisce | binario-ricetta del gemello JS |
| GnrBag client + trigger | la GnrBag moderna JS: il PRIMO mattone del gemello |
| GnrDomSource (sottoclasse della bag) | conferma: il dom-building discende dalla bag, non viceversa |
| `getTriggerReason` node/container/child | `_relevant_nodes` kinds (convergenza indipendente) |
| setValue / setAttribute / rebuild | op della busta patch: `set_text` / `set_attrs` / `replace` |
| `setInClientData` (comando dichiarato) | envelope patch del TargetWrapper (vocabolario `op` aperto) |
| `rpc_*` + `self.db` | metodi dell'Application |

## 7. Giudizio e implicazioni di design

**Da tenere** (il disegno): la ricetta che viaggia una volta; il
doppio albero con datapath/pointer client-side; le tre granularità di
aggiornamento; i comandi dichiarati sul ws; `requires` dichiarativi.

**Da non portare** (l'impasto): l'oggetto-dio monolitico;
l'accoppiamento dojo/dijit; i topic globali in broadcast (O(N) per
mutazione); Bag→XML→parse a ogni giro (oggi: JSON); la semantica
senza contratto formale (50K righe come unica specifica).

**Strategia**: i due binari non competono — ws_live (render Python,
client stupido a patch) dà valore subito con un client minimo; il
gemello JS (il modello legacy rifondato) cresce incrementalmente
sotto il contratto, partendo dalla **GnrBag moderna** (bag + trigger
+ datapath), non dal dom-building. Il `TargetWrapper` è la cucitura:
stesso flush, payload diversi (patch HTML oggi; dati/ricetta domani).
Il client legacy può fare da **oracolo dei golden test** del gemello:
semantica provata in produzione. Cautela: niente macchina-widget
dell'era dojo — i body JS dei component + DOM moderno bastano.

## Riferimenti

- Contratto v0.8.0 (premessa "un linguaggio, due interpreti";
  `CMP`; `RX`), `roadmap/component-design.md`,
  `roadmap/reactivity/variable-datapath.md` (cita gli stessi punti
  legacy per il datapath variabile).
- Sessione di studio (Claude Code):
  `a47d7ab4-be22-42aa-b2e9-bb0e198e6b40` (2026-06-10).
