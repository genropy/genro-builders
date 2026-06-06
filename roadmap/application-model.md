# Application model — il contesto della reattività

**Versione**: 0.1.0
**Ultimo aggiornamento**: 2026-06-06
**Status**: 🔴 DA REVISIONARE — documento di modello, non ancora approvato.

Spiega cos'è l'**Application** in genro-builders, perché la reattività vive
solo al suo interno, e come si usa in modo canonico (anche nei test).

L'autorità sull'implementato resta `architecture-contract.md`; questo documento
descrive un modello che il contratto recepirà nell'area APP.

---

## 1. Cos'è l'Application

L'**Application** è lo strato tra il mondo esterno e un `BuilderHandler`. Non è
una classe fissa del framework: **può essere qualunque oggetto** — un server
web, una sessione WebSocket, un processo batch, un test bench. Ciò che la rende
un'Application è il **ruolo**, non il tipo:

- **possiede** l'handler e lo crea passandogli sé stessa (dual relationship);
- è il **ponte** tra le mutazioni che arrivano dal mondo (un click, un messaggio
  WS, un comando REPL) e l'handler;
- riceve l'**output** del render (la cosa da mandare al client) e lo instrada.

> La reattività **è** la relazione handler↔application, non un flag interno.
> Un handler creato con `application=None` è un handler **pull-only** (sincrono,
> si interroga); un handler che ha un'application è **reattivo**.

Questo è il motivo per cui `live()` presuppone un'app: senza il contesto
applicativo, "reagire" non ha un destinatario.

## 2. Dual relationship

L'app crea l'handler passandosi:

```python
class MyApp:
    def __init__(self):
        self.handler = MyPage(application=self)   # l'handler conosce l'app
        self.handler.create()                      # costruisce l'albero
```

`BuilderHandler.__init__(self, application=None)` salva `self.application`.
L'handler, da lì, sa di essere reattivo perché ha un'app. Nessun figlio tiene un
generico `_parent`: il nome è semantico (`application`).

## 3. La sezione reattiva: `with handler.live(target)`

Le mutazioni reattive avvengono **dentro** una sezione `live()`:

```python
with self.handler.live(target):
    ...  # ogni mutazione di source/data qui dentro -> re-render verso target
```

Contratto di `live()` (RX livello 0):

- **dentro** il `with`: ogni mutazione instradata da `_on_source_event` /
  `_on_data_event` ri-renderizza (oggi l'intero documento) verso `target`;
- **fuori**: l'handler resta pull-only, nessun auto-render;
- **sincrono e serializzato** da un `RLock` per-handler; la re-entry sullo stesso
  thread è ammessa e lo stato del parent è ripristinato all'uscita;
- **esige `create()`**: `live()` prima di `create()` solleva `RuntimeError`
  (reattività non armata);
- punti di estensione `on_live_enter` / `on_live_exit` (una volta per sezione,
  anche su eccezione).

`target` accetta ciò che accetta `RendererBase.finalize` (path, file-like con
`.write()`, callable); `None` usa il target di default registrato con
`set_render_target`.

## 4. Il primo render fa parte dell'avviamento

Dal modello di registrazione alla lettura (vedi
`reactivity/variable-datapath.md` §11): la `pointer_map` si popola mentre il
primo render legge i pointer. Quindi **una pagina non resa non è reattiva**.

`live()` chiude il cerchio per costruzione: una sezione `live()` rende
all'ingresso/su mutazione, quindi entro l'app il primo render avviene nel ciclo
naturale — non serve un `render()` manuale sparso. È la ragione per cui la
reattività va **sempre** esercitata dentro un'app + `live()`, non con mutazioni
"a mano" sull'handler nudo.

## 5. Accesso mediato: il proxy (opzionale)

Un'app può non esporre mai l'handler nudo. Lo scheletro `MiniApp`
(`tests/reactive_app/app.py`) lo fa via un context manager `session()` che entra
in `live()` e restituisce un **proxy** ad accesso filtrato (whitelist
`source`/`data`, blacklist `create`/`live`/`application`, zona grigia
registrata per scoprire il confine reale). Il proxy è una **convenzione del
modello applicativo**, non un obbligo del framework: un'app più semplice può
esporre azioni curate invece dei bag grezzi. Cosa esporre (bag grezzi vs azioni)
è ancora aperto.

## 6. Uso canonico (anche nei test)

La reattività si testa **sempre** nell'ambito di un'app, dentro `live()`:

```python
app = MyApp()                      # dual relationship + create() nell'__init__
with app.handler.live(target):     # (o app.session() se l'app lo offre)
    app.data.set_item("path", v)   # mutazione canonica
    ...
# fuori dal with: stato quiescente, si leggono i risultati
```

NON canonico (da evitare nei test): `page.create()` seguito da
`page.data.set_item(...)` sull'handler nudo, fuori da `live()` e senza app.
Funziona solo perché la mutazione attraversa comunque gli hook, ma scavalca il
contesto applicativo e l'invariante del primo render. Riferimento dello
scheletro reale: `tests/reactive_app/` (`MiniApp`, `TrianglePage`, `DataLogic`)
e `tests/test_reactive_concurrency.py`.

---

## Riferimenti

- `architecture-contract.md` (area APP, da recepire).
- `reactivity/contract.md`, `reactivity/variable-datapath.md` §11 (primo render
  e registrazione alla lettura).
- Codice: `BuilderHandler.__init__` (dual relationship), `BuilderHandler.live`
  (sezione reattiva), `tests/reactive_app/app.py` (scheletro `MiniApp` + proxy).
