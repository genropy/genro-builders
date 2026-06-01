# Reactivity contract — Livello 0

**Status**: 🔴 DA REVISIONARE — non ancora approvato dall'utente.
**Versione**: 0.1.0 (specifica di dettaglio per area `RX` del
contratto principale v0.5.0).
**Sostituisce**: niente (file nuovo).
**Citato da**: `roadmap/architecture-contract.md`, sezione `RX.4`.

## Contesto

Il contratto principale v0.5.0 fissa il perimetro dell'area `RX`
(reattività push) ma rinvia il dettaglio operativo a questa
cartella. Il rebuild di maggio 2026 ha chiuso il livello **pull**
(`DAT.2`): i pointer si risolvono a render time leggendo la data
bag, niente subscribe-driven, niente notifiche.

Resta aperto come emettere verso l'esterno (file, websocket, altro
target) quando la source o la data cambiano: la subscribe interna
del `BuilderHandler` esiste (linee 182-193 di
`builder_handler.py`) ma fa solo manutenzione del `pointer_map`.
Nessuno chiama `render()` automaticamente.

Questo documento descrive il **Livello 0 della reattività push**:
la forma minimale, già implementabile sopra la subscribe esistente,
sufficiente a dimostrare che la pipeline data→render funziona end-to-end
verso un target concreto (es. un file `out.html` su disco, ispezionabile
con qualunque editor o browser). I livelli successivi (dispatch
granulare per-nodo, broadcast WS, ecc.) sono dichiarati fuori scope qui.

## Scenario guida

```python
from genro_builders.contrib.html import HtmlBuilderHandler

class MyPage(HtmlBuilderHandler):
    def main(self, root):
        body = root.body(datapath="page")
        body.h1("^.title")
        body.p("^.message")

page = MyPage()
page.create()                                  # subscribe armata, pull only

with page.live("/tmp/out.html"):               # apre sezione critica
    page.data.set_item("page.title", "Hello")  # scrive /tmp/out.html
    page.data.set_item("page.title", "World")  # riscrive /tmp/out.html
# fuori dal with: il file resta come l'ultima scrittura

page.data.set_item("page.title", "Quiet")      # NIENTE auto-render
```

Caratteristiche:

1. **Esplicito**: la reattività si accende solo dentro `with
   live(...)`. Senza, il handler funziona come oggi.
2. **Atomico sync**: dentro il blocco le mutazioni sono serializzate
   da un lock, niente concorrenza, niente `await`.
3. **Re-render totale**: ogni mutazione (data o source) produce un
   render completo verso il target.
4. **Target opaco**: il target è quello che `RendererBase.finalize_raw`
   sa gestire (path/Path, file-like, callable). Il livello 0 non
   distingue.

## Decisioni

### DR1 — API: context manager `handler.live(target)`

Il punto di ingresso unico è un context manager sincrono:

```python
with handler.live(target) as h:
    ...
```

Non esiste un `async with` né una property `auto_render`. La forma
"sezione di codice live" è esplicita e auto-documentata: vedi le
righe dentro il `with`, sai che lì la reattività è attiva.

### DR2 — Target esplicito, niente fallback

`target=None` solleva `ValueError`. Niente default, niente
"ricordo dell'ultimo target", niente lettura da config.

```python
with handler.live(None):     # ValueError
with handler.live("out.html"):  # ok, target esplicito
```

Conforme a `feedback_no_fallback_no_silent_recovery`.

### DR3 — Re-render totale per ogni mutazione

Ogni `_on_data_event` o `_on_source_event` triggerato dentro la
sezione `live` invoca `self.render(target=self._live_target)`.
Il render è **completo**, non granulare.

Conseguenza: una batch di N mutazioni dentro il `with` produce N
render. Per il livello 0 è accettabile (validare il principio).
Ottimizzazioni (debounce, batch, render parziale) sono lavoro
successivo.

### DR4 — Lock `threading.RLock`, sezione critica sync

L'implementazione usa `threading.RLock`:

- **sync**: chi entra in `live(...)` da un thread blocca chiunque
  altro provi a entrare (anche task asyncio nello stesso event
  loop) fino all'uscita
- **re-entry permessa**: lo stesso thread può entrare in `live(...)`
  in modo annidato (un metodo del handler chiamato dentro il `with`
  che a sua volta entra in `live(...)`) — niente deadlock; lo stato
  del padre viene salvato e ripristinato dal `finally`
- **niente `await` dentro**: il blocco è sincrono per costruzione
  (`@contextmanager`, non `@asynccontextmanager`); chi prova a fare
  `await` deve uscire dalla sezione

Funziona in qualunque contesto. Dentro un event loop asyncio
l'event loop si blocca durante la sezione critica — è esattamente
il comportamento voluto dall'utente: dentro `live`, **nessuno
muta altro**.

### DR5 — `create()` deve essere stato chiamato prima

`live(...)` fallisce con `RuntimeError` se `create()` non è stato
invocato. Lifecycle e reattività sono separati: prima si costruisce
(`create()`), poi si entra in modalità reattiva (`live()`).

### DR6 — Default: niente reattività

Senza un `with handler.live(...)` il handler funziona esattamente
come oggi. Nessun render automatico, nessun side effect su un
target. Pull-based puro.

### DR7 — Niente flag `auto_render` pubblico

L'unico modo di abilitare la reattività è il context manager. Non
esiste `handler.auto_render = True`. Motivazione: lo scope esplicito
del `with` è più robusto di un flag globale (cleanup garantito su
eccezione, niente stato condiviso fra parti di codice).

Variabili interne `_live_active`/`_live_target` esistono come
private; non sono parte dell'API.

### DR8 — Allineamento col contratto principale

**Vs `RX.2`** (capability del base, scheduling sync vs async): il
livello 0 è il caso sync. I callback del trigger girano "immediato
nel writer thread", esattamente come `RX.2` prescrive.

**Vs `RX.3`** (flag `_subscriptions_enabled` per attivazione per
handler): il flag concettuale del contratto principale è realizzato
qui via context manager invece che property persistente. La
subscribe interna è già attiva dopo `create()` (oggi); cambia solo
se emette verso un target.

**Vs `RX.4`** (SourceDispatcher / DataDispatcher distinti): il
livello 0 li fonde in un unico re-render totale. È un compromesso
esplicito: la separazione granulare è giusta come arrivo, ma
richiede infrastruttura (chi notifica quale path, chi accumula
diffs, chi emette patch sull'HTML). Il livello 0 è il primo gradino
che dimostra la pipeline. La separazione `RX.4` resta valida come
specifica del **livello successivo**.

**Drift contratto principale → codice** (segnalazione laterale):
`DAT.2` linea 527-529 dice che `pointer_map` "non si auto-popola
alla creazione". Il codice esistente la popola in `create()` (linea
181 di `builder_handler.py`). L'utente ha confermato che il codice
è la verità. Questo va riallineato in un commit separato del
contratto principale, fuori scope del livello 0.

## API surface

```python
# In src/genro_builders/builder_handler.py

import threading
from contextlib import contextmanager
from typing import Any, Iterator

class BuilderHandler:
    # ... slot esistenti ...
    _live_target: Any
    _live_active: bool
    _live_lock: threading.RLock
    _lifecycle_started: bool

    def __init__(self) -> None:
        # ... __init__ esistente ...
        self._live_target = None
        self._live_active = False
        self._live_lock = threading.RLock()
        self._lifecycle_started = False

    def create(self) -> None:
        # ... corpo esistente ...
        self._lifecycle_started = True

    @contextmanager
    def live(self, target: Any) -> Iterator["BuilderHandler"]:
        """Open a critical section where every source/data mutation
        triggers a fresh render to ``target``.

        Args:
            target: Render target. Must be non-None. Accepts everything
                ``RendererBase.finalize_raw`` accepts: a filesystem path
                (str or Path), a writable file-like with .write(),
                or a callable.

        Raises:
            ValueError: target is None.
            RuntimeError: create() not called.
        """
        if target is None:
            raise ValueError("live() requires a non-None target")
        if not self._lifecycle_started:
            raise RuntimeError(
                "live() called before create(); call create() first"
            )
        with self._live_lock:
            prev_active = self._live_active
            prev_target = self._live_target
            self._live_active = True
            self._live_target = target
            try:
                yield self
            finally:
                self._live_active = prev_active
                self._live_target = prev_target

    def _on_data_event(self, node, evt, **kw):
        # ... pointer_map maintenance esistente ...
        if self._live_active:
            self.render(target=self._live_target)

    def _on_source_event(self, node, evt, **kw):
        # ... pointer_map maintenance esistente ...
        if self._live_active:
            self.render(target=self._live_target)
```

## Fuori scope (livello 0)

I seguenti temi sono ammessi dall'architettura ma rinviati a livelli
successivi:

- **Push WS verso un browser** come target diretto. Il livello 0 fa
  da plumbing: lo si fa scrivendo un callable target che pubblica su
  un canale WS. La forma "broadcast WS" come API di prima classe
  richiede uno scenario d'uso reale che la disegni.
- **Batch / debounce**. Oggi N mutazioni → N render. Una API
  `with handler.live(target, batch=True)` che accumula e re-rendera
  una sola volta all'uscita è un livello successivo.
- **Dispatch granulare per nodo** (SourceDispatcher /
  DataDispatcher distinti di `RX.4`). Il livello 0 fonde i due in un
  re-render totale.
- **Multi-target**. Un singolo `live(target)` ha un solo target. Per
  scrivere su due target diversi servono due `with` annidati con due
  callable target che fan-out al loro interno.
- **Cancellazione / timeout**. Una mutazione che resta dentro `live`
  per minuti blocca chiunque altro. Per il livello 0 è accettabile;
  i pattern di backpressure arrivano dopo.
- **Async scheduling** (`RX.2` "scheduling dei callback schedulato
  nel loop"). Il livello 0 è puramente sync. Async è un'API
  parallela, non un'estensione.

## Test contract

Validati da `tests/test_live_context.py`:

1. `handler.live(None)` → `ValueError`.
2. `handler.live("...")` prima di `create()` → `RuntimeError`.
3. Senza `with`: una mutazione `data.set_item(...)` non scrive il
   target.
4. Dentro `with live("out.html")`: `data.set_item("page.title", "X")`
   → il file `out.html` esiste e contiene "X" nel render.
5. Dentro `with live("out.html")`: `node.set_attr({"style": "color:red"})`
   → il file contiene il nuovo attributo.
6. Re-entry: dentro `with live(t1)` chiamo un metodo che a sua volta
   entra in `with live(t2)`. Non deadlocka, l'attivo è `t2`. All'uscita
   dell'inner torna `t1`.

Test di concorrenza multi-thread (due thread che entrano in `live`
simultaneamente) rinviato — la serializzazione è una conseguenza di
`threading.RLock`, non un comportamento da contrattualizzare al
livello 0.

## Riferimenti

- Contratto principale: `roadmap/architecture-contract.md` v0.5.0,
  sezioni `RX.1`/`RX.2`/`RX.3`/`RX.4`/`HND.2`/`HND.5`/`DAT.2`.
- Commit preparatorio: `d7056a5` (fix BAG.3 wrapper-root) — apre la
  strada usando `BuilderBag` per `_sourceroot`/`_dataroot`,
  necessario perché `parent_node` sia un `BuilderBagNode` con il
  mixin.
- Workspace di discussione: `temp/subtask/reactivity/startdoc.md`
  (vivo).
- Sessione Claude Code locale di questa pianificazione:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-05-31/06-01).
