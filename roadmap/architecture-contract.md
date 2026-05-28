# Architecture contract — genro-builders — v0.5.0

**Status**: 🟢 IN VIGORE dal 2026-05-27.
**Sostituisce**: v0.4.0 (archiviata in
`roadmap/outdated_versions/architecture-contract-v0.4.md`).

**Stato del codice di riferimento**: `develop @ 8e61e9f` (= `origin/develop`),
suite **332 test verdi**, coverage 83%. A questa versione il codice è
allineato al contratto sui punti chiave dell'identità dei nodi e del
render subsystem:

- subtask `handler_wrapper_root` (commit `82f4630`..`5086c7e`): wrapper-root,
  subscribe sui wrapper, hook reattivi → `HND.2`, `RX`;
- migrazione `node_id` (commit `9c12d59`): rimossa la mappa `_node_index`,
  lookup walk-based, unicità via `_check_unique_id` → `BAG.4`, `BAG.5`;
- subtask `abs_datapath` (commit `48231bc`..`500ac6b`):
  `BuilderHandler.abs_datapath(node, path)` per la composizione sintattica
  dei path assoluti (no lettura dati) → `DAT.2`;
- refactor render subsystem (commit `8e61e9f`): `self.renderers` come unica
  struttura per-mode (`{target, instance}`), popolata lazy → `HND.3`.

Restano da implementare: generatore di walk in `RendererBase` con `walk()`
+ `rendered_item()` polimorfico, banco di prova XML modalità `xml`
(`render_walk_generator` → `DAT.2`, `BLD.3`), risoluzione pointer a
render time (subtask `data_binding` → `DAT.2`), reattività push (`RX`),
BuilderSuite (`SUITE`).

---

# PARTE I — PREMESSA

## Scopo

Questo documento fissa i contratti architettonici di `genro-builders`.
È il **punto di arrivo** verso cui il codice converge, non la fotografia
dello stato attuale (quella vive in `roadmap/implementation-roadmap.md`).

Il contratto descrive **come deve essere fatto** il sistema. Quando il
lavoro sarà completo, questo documento coinciderà con la documentazione
architetturale del prodotto: chi lo legge capisce com'è strutturato
genro-builders e perché.

Le decisioni sono organizzate per **aree tematiche**. Ogni decisione è
identificata da un codice `<AREA>.<n>` (es. `HND.1`, `RX.2`). Una
rinegoziazione si fa esplicitamente: si bump-a la minor del contratto e
si conserva la versione superata in `roadmap/outdated_versions/`.

## Glossario

- **Builder**: la grammar pura di un dialetto (`HtmlBuilder`,
  `MarkdownBuilder`, `SvgBuilder`, `XsdBuilder`). Definisce `@element`,
  `@abstract`, `@subbuilder`, `@data_element`, lo schema di validazione,
  le regole di serializzazione. Solo dichiarazione, nessun engine.
- **BuilderHandler**: la macchina che consuma un builder. Possiede i
  wrapper-root `_sourceroot` / `_dataroot`, le due fasi `create`/`render`,
  il dict `renderers: mode → {target, instance}`.
- **Preset** (`HtmlBuilderHandler`, ecc.): sottoclassi di `BuilderHandler`
  con `builder_class` già fissata. L'utente eredita da uno di questi.
- **Source**: il bag (`BuilderSource`) popolato in `create`, serializzato
  in `render`. È la forma unica del documento.
- **Data**: il bag dei dati associato all'handler (`_dataroot["main"]`),
  letto dai pointer a render time.
- **Resolver** (pull): nodo con computazione lazy, eseguita alla lettura.
- **Trigger** (push): notifica scatenata da una mutazione verso i
  sottoscrittori. Vive nel sotto-documento `roadmap/reactivity/`.
- **Pointer**: riferimento a un dato (`^path`), risolto a render time
  leggendo la data bag.
- **node_id**: identità opzionale e immutabile di un nodo, come una
  primary key.

## Scenari d'uso

Molte decisioni hanno senso solo riferite a uno scenario. Sono nominati
qui una volta e richiamati dove servono.

- **S1 — Sync one-shot strutturale**: script/batch. Handler costruito,
  renderizzato, scartato. Nessun pointer dinamico, nessun consumer dopo
  `render()`. Es. generazione di un Markdown statico.
- **S2 — Sync con lettura dati (pointer)**: come S1 ma la source contiene
  pointer `^path`; al render si leggono i dati dalla data bag. Nessuna
  reattività. Es. report Word/PDF con campi da un dataset.
- **S3 — Sync con derivazioni**: la data bag contiene resolver/formule
  che si auto-risolvono. Eventuale reattività push interna durante la
  costruzione. Es. lo script che calcola valori derivati prima del render.
- **S4 — Web sync per-request (Gunicorn-style)**: handler isolato per
  request, vita corta. Variante di S1/S2/S3 a seconda dell'uso. Nessuna
  concorrenza sull'handler.
- **S5 — Web sync con handler condiviso**: handler in cache fra request,
  concorrenza reale fra thread. Caso marginale. Sincronizzazione a carico
  dello sviluppatore (vedi `HND.5`).
- **S6 — Async con consumer vivo**: Textual TUI, ASGI websocket/SSE. Il
  loop è il proprietario naturale. Reattività push attiva.
- **S7 — Async + RPC da thread esterno**: come S6 più mutazioni da thread
  fuori dal loop. Richiede marshalling verso il loop.

La reattività push (`RX`) è dettagliata per scenario nel sotto-documento
`roadmap/reactivity/`.

---

# PARTE II — AREE E DECISIONI CHIAVE

## Area BLD — Builder (grammar)

### BLD.1 — Builder come subclass; grammatica estesa via mixin

Ogni builder è una subclass del builder base e definisce il proprio
dialetto (tag, `sub_tags`, `parent_tags`, validazione, regole di render).
Il pacchetto fornisce mixin opzionali per **estendere la grammatica** con
tag aggiuntivi; il dialetto base resta sempre nel builder.

Il builder è **solo** dichiarazione. Tutte le responsabilità di engine
vivono sul `BuilderHandler` (`HND.1`).

### BLD.2 — Sub-builder via decoratore dedicato `@subbuilder`

Lo switch di builder a metà albero è dichiarato esplicitamente con un
decoratore separato da `@element`, perché "definire un tag del proprio
dialetto" e "passare il testimone a un altro builder" sono responsabilità
distinte.

```python
class HtmlBuilder(BagBuilderBase):
    @subbuilder(SvgBuilder)
    def svg(self): ...
```

Da `<svg>` in giù il builder attivo è `SvgBuilder`. Lo switch resta dentro
lo stesso `BuilderHandler`, lo stesso albero, la stessa identità. Cambia
solo lo slot `_builder` dei nodi del sottoalbero (`BAG.3`). Il `parent_tags`
del builder ospite resta valido (HTML dichiara dove `<svg>` può apparire);
da `<svg>` in giù la validazione passa allo schema del sub-builder.

### BLD.3 — Builder = grammar pura; rendering in renderer dedicati

Il builder contiene **solo** la grammar: decoratori, schema, validazione,
registry dei renderer per-istanza (`HND.3`). Il rendering vive in
`RendererBase` e nei concreti (`XmlRenderer`, `HtmlRenderer`, ...). Ogni
renderer concreto serve un singolo mode.

Conseguenze: il builder è testabile in isolamento; aggiungere un mode
significa registrare un renderer, non modificare il builder; estendere un
dialetto è una subclass del builder che registra renderer nel proprio
`__init__`.

---

## Area HND — BuilderHandler (engine)

### HND.1 — Handler gestisce il suo builder; preset per dominio

Ogni `BuilderHandler` gestisce un proprio builder e funziona da solo. Il
pacchetto fornisce un preset per ogni builder (`HtmlBuilderHandler`,
`MarkdownBuilderHandler`, ...) con `builder_class` fissata. L'utente
eredita dal preset e implementa `main(self, root)`.

Se servono più handler coordinati con dati condivisi, si introduce un
**orchestratore** esplicito come strato sopra (area `SUITE`, ancora in
discussione).

### HND.2 — Wrapper-root simmetrico `_sourceroot` / `_dataroot`

Il `BuilderHandler` possiede alla nascita due wrapper strutturali:

- `_sourceroot` — bag wrapper che ospita la source sotto `["main"]`.
- `_dataroot` — bag wrapper che ospita i dati sotto `["main"]`.

Il **payload utente** vive sotto la chiave `["main"]`:

- `_sourceroot["main"]` è la `BuilderSource`;
- `_dataroot["main"]` è la data bag.

L'API utente espone i payload come `handler.source` e `handler.data`.

Il wrapper-root è **stabile come oggetto** per tutta la vita dell'handler:
il payload sotto `["main"]` può essere sostituito (hot-swap) senza che il
wrapper cambi identità. Questo abilita reset / cambio sessione senza
ricostruire l'handler, e — quando la reattività sarà attiva — fa
sopravvivere le sottoscrizioni fatte sul wrapper.

Gli slot aggiuntivi del wrapper (`["workspace"]`, `["meta"]`, ...) sono
**predisposti** ma non usati nel base. Sono punti di estensione futuri.

**Backref**: entrambi i wrapper-root hanno il backref di `genro_bag`
acceso esplicitamente in `__init__` (`set_backref()`). È parte del
contratto strutturale: serve a `abs_datapath` (`DAT.2`) e a ogni
risalita ancestor sui nodi, indipendentemente dalla reattività.

`HND.2` è puramente strutturale: **non implica** subscribe attivi. La
reattività push è area `RX`. Il backref è acceso anche quando le
subscribe sono spente.

### HND.3 — Render con `mode` e `target`, multipli e nominati

`render` esiste sia sul builder che sull'handler.

**Sul builder** — registry delle classi renderer, per-istanza, popolato
in `__init__` via `register_renderer(name, renderer_class)`. Il base
registra i mode condivisi (`xml`); i dialetti aggiungono i propri.
Override possibile ri-registrando lo stesso nome.

**Sull'handler** — un'unica struttura `self.renderers: dict[str, dict]`
con entry `{"target": ..., "instance": RendererBase}` per ogni mode
attivo sull'handler. La struttura è **popolata lazy** dal helper interno
`_ensure_mode(mode)`: alla prima `set_render_target(mode, ...)` o alla
prima `render(mode=...)`, l'handler legge la classe renderer dal registry
del builder, la istanzia con `self`, e mette l'entry nel dict.
`set_render_target(mode, target, default=False)` riusa la stessa entry
per scrivere il target. Più target sotto mode diversi; un mode marcato
`default=True` diventa il default per `render()` senza argomenti.

Semantica del `target` (invariata da v0.4.0):

- `False` → forza ritorno stringa, ignora target registrato;
- altro falsy (`None`, `""`, `0`) → usa il target registrato sotto il mode;
- truthy → usato direttamente per quella chiamata.

Risoluzione del `mode`: argomento esplicito > `_default_render_mode`
dell'handler > `_default_render_mode` del builder.

Shortcut auto-generati `render_<mode>(target)` per ogni mode registrato.

Sub-builder (BLD.2): `renderer_for(builder)` istanzia il renderer del
sub-builder al volo (mode di default del sub-builder), senza entrare in
`self.renderers`. `self.renderers` riguarda i mode dell'handler primario.

### HND.4 — Due fasi esplicite: create, render

```python
page = CustomerPage()
page.create()                                # main(source) → popola la source
page.set_render_target('html', 'out.html', default=True)
page.render()                                # serializza la source sul target
```

- `create()` chiama `self.main(self.source)`.
- `render(target, mode, **kwargs)` dispatcha al renderer del mode e gli
  affida la source.

Quando un sottoalbero ha un sub-builder (`BLD.2`), il `_builder` sui nodi
del sottoalbero determina quale builder è attivo localmente, e il render
segue automaticamente il builder corretto (`HND.3` + `BAG.3`).

### HND.5 — Thread safety non promessa

`BuilderHandler` e le classi correlate **non sono thread-safe**. La
proprietà è ereditata da `genro_bag.Bag`. Il framework **non introduce
lock** sui mutatori né su `render()`.

Chi condivide un handler fra thread (scenario S5) è responsabile della
sincronizzazione: scelta di lock, granularità, gestione deadlock. I
callback dei trigger sync, quando attivi (`RX`), girano **nel thread del
writer**, sincroni rispetto alla mutazione.

Motivazione: promettere thread-safety senza che `Bag` la garantisca
sarebbe disonesto; il costo zero serve la maggioranza degli scenari
(S1-S4, S6) che non condividono handler; la condivisione fra thread è una
decisione architetturale esplicita.

---

## Area BAG — Bag e nodi

### BAG.1 — BuilderBag e BuilderBagNode via mixin

`BuilderBag` = `Bag` + `_BuilderBagMixin`; `BuilderBagNode` = `BagNode` +
`_BuilderBagNodeMixin`. La logica builder-aware vive nei mixin; le classi
base di `genro-bag` restano intatte.

### BAG.2 — Layering a due livelli

**Livello 1 — base comune**: `BuilderBag`, `BuilderBagNode`. Contengono i
meccanismi condivisi: slot `_builder`/`_handler` (`BAG.3`), dispatch
grammar via `__getattr__`/`__dir__`, accesso ai metadati dell'albero.

**Livello 2 — specializzazioni semantiche**: `BuilderSource` /
`BuilderSourceNode` (il bag della fase create/render). Una futura
`BuilderData` può materializzarsi per dare semantica al payload dati; nel
base sync minimo, `Bag` puro è sufficiente.

Vantaggi del layering: punto di estensione strutturale; tipizzazione
discriminante (il tipo dice il ruolo); predisposizione per mixin di
specializzazione.

### BAG.3 — Ogni bag e nodo ha `_builder` e `_handler`

`BuilderBagNode` e `BuilderBag` hanno due slot:

- `_handler` → il `BuilderHandler` dell'albero. Uno per albero, settato
  all'attach. Serve per accedere all'engine.
- `_builder` → il builder attivo per il nodo. Di default il principale;
  nei sottoalberi `@subbuilder` (`BLD.2`) è il sub-builder. Settato
  all'attach.

Conseguenze: dispatch grammar e render sono O(1) e diretti. I nodi sono
immutabili nel parent dopo l'attach, perché le ref siano sempre coerenti.

### BAG.4 — `node_id` come primary key del nodo

`node_id` è un attributo **opzionale** dei nodi della source. Per
analogia con una primary key, dovrebbe essere unico e stabile. I due
aspetti hanno però trattamento diverso a runtime:

- **Unicità → controllo attivo.** Alla creazione del nodo da grammar
  (in `_command_on_node`, il punto di dispatch unico: copre element di
  schema, data_element e tag fuori schema), se l'attr `node_id` è presente
  si verifica via `BAG.5` che non esista già un nodo con lo stesso id; in
  caso contrario errore esplicito. Motivo: l'unicità è un **presupposto di
  funzionamento** di `node_by_id` (con due id uguali il lookup sarebbe
  ambiguo), non una guardia paternalistica.
  Costo: O(N) solo per gli inserimenti di nodi **che portano un `node_id`**
  (minoranza). Trascurabile.

- **Immutabilità → nessun controllo.** Se il developer muta un `node_id`
  su un nodo esistente, è una sua responsabilità (developer adulto). Il
  framework **non** intercetta `set_attr("node_id", ...)`. La walk è
  stateless (`BAG.5`): non c'è stato derivato da proteggere, la lettura
  successiva trova semplicemente il nuovo valore. Mettere una guardia qui
  aggiungerebbe codice senza prevenire alcuna incoerenza interna.

### BAG.5 — Lookup per `node_id` walk-based, senza indice mantenuto

Il `BuilderHandler` **non mantiene** una mappa cached degli ID.
`handler.node_by_id(node_id)` è un lookup ad albero sulla source via l'API
esistente di `genro_bag`:

```python
def node_by_id(self, node_id):
    node = self.source.get_node_by_attr("node_id", node_id)
    if node is None:
        raise KeyError(f"node_id '{node_id}' not found")
    return node
```

Complessità O(N) sulla dimensione della source. Per source piccole/medie il
costo è invisibile. Un'eventuale ottimizzazione (cache opt-in) si introduce
**senza cambiare l'API** quando uno scenario reale la richiede.

Sub-builder e handler condividono la stessa source: il lookup attraversa
naturalmente l'albero indipendentemente da quale builder controlla quale
sottoalbero.

> **Storia della decisione**: la decisione 11 di v0.4.0 prevedeva una mappa
> `_node_index` (`node_id → path`, poi `→ node`), popolata via subscription
> sulla source (`aeb9272`) e ricablata dal subtask HWR dentro
> `_on_source_event`. v0.5.0 ha **eliminato** la mappa (commit `9c12d59`):
> `node_by_id` è ora walk-based via `get_node_by_attr`, il controllo
> unicità vive in `_command_on_node` tramite `_check_unique_id` (`BAG.4`),
> wrapper-root/subscribe/hook reattivi di HWR restano intatti.
>
> Motivazioni dell'eliminazione: la walk è stateless, non c'è stato
> derivato da sincronizzare; spariscono i problemi di coerenza su
> `pop`/`clear` e il rischio di nodi referenziati che non muoiono col GC
> (cosa che rende sicuro l'hot-swap, `HND.2`). Il costo O(N) del lookup è
> accettabile per source piccole/medie; un'eventuale cache opt-in si
> reintrodurrebbe senza cambiare l'API solo a fronte di un costo misurato.

---

## Area DAT — Dati, resolver e pointer

### DAT.1 — Resolver come capability del base, ortogonali ai trigger

Un nodo può portare una computazione lazy (`BagResolver` di genro_bag),
eseguita alla lettura. I resolver sono supportati **sempre** (sync e
async), indipendentemente dalla reattività.

- In modalità **sync senza dispatcher push**: resolver "stateless" — ogni
  lettura ricalcola, o il resolver gestisce internamente la propria cache.
  Nessun tracking automatico di dipendenze.
- In modalità **con dispatcher push attivo** (`RX`): i resolver possono
  diventare **dependency-tracked** — il dispatcher invalida e ricalcola i
  resolver che dipendono dai dati mutati.

La scelta sync vs async non influisce sulla presenza dei resolver, solo
sul loro grado di sofisticazione.

### DAT.2 — Pointer risolti a render time (Livello 1)

> **Status interno**: 🔴 da progettare in dettaglio. Le decisioni qui sono
> il perimetro concordato; la specifica di sintassi va maturata in una
> sezione/sotto-documento dedicato prima dell'implementazione.

Prima di qualsiasi reattività push, il framework abilita la **risoluzione
lazy dei pointer a render time**. Un nodo della source può contenere un
pointer (es. `^customer.name`); al render, il renderer interpreta il
pointer e legge dalla data bag (`_dataroot["main"]`) il valore.

Questo livello **non è reattività**: è lookup di dati al momento del
render. Copre gli scenari S2 e gran parte di S3/S4 senza subscribe,
callback o cascate.

Sintassi: il Livello 1 punta a coprire **l'intera tassonomia** dei
pointer (non un sottoinsieme minimo), riprendendo le forme del legacy JS:

- assoluti: `^path` (dalla radice della data bag);
- relativi: `^.x`, `^..x`, `^...x` (datapath contestuale e risalita);
- simbolici: `^#node_id.path` (cross-tree, usano `BAG.5` per il lookup),
  e gli scope `^#FORM.x`, `^#ANCHOR.x`, `^#ROW.x`, `^#WORKSPACE.x`;
- con attributo: `^path?attr` (accesso all'attributo invece che al valore).

**Dove avviene la risoluzione** — il trigger è la **walk del render**
(`BLD.3`/`HND.4`: è il renderer che cammina l'albero ed emette). Per non
duplicare la logica in ogni dialetto:

- `RendererBase` **offre** un generatore di walk condiviso e un helper di
  risoluzione pointer (parsing del prefisso `^`, lettura da
  `_dataroot["main"]`). È un **servizio opzionale**, non una gabbia.
- Il renderer concreto **normale** consuma la walk offerta → la traversata
  non è reimplementata e i pointer arrivano già risolti.
- Un renderer con esigenze speciali (visita non standard, doppia passata)
  **può** guidare la propria walk e chiamare l'helper di risoluzione dove
  serve.
- **Sempre** del renderer concreto resta l'**emissione del nodo nel
  proprio dialetto** (markup, escape, open/close, formattazione).

La distinzione fra pointer e valore stringa normale la fa l'helper di
risoluzione riconoscendo il prefisso `^` al momento di emettere
valore/attributo.

---

## Area RX — Reattività push (rinviata)

### RX.1 — Reattività push ammessa, implementazione rinviata

Il contratto **ammette** la reattività push (trigger, dispatcher,
subscribe utente, resolver dependency-tracked) come architettura, ma
**non la implementa** in questa versione. `RX` fissa il perimetro
concettuale; il dettaglio operativo vive in `roadmap/reactivity/`,
organizzato **per scenario d'uso** (S1-S7).

### RX.2 — Il dispatcher push è capability del base, non solo async

Quando sarà implementato, il dispatcher push **non sarà esclusivo di una
sottoclasse async**. Sarà capability del base, perché lo scenario S3 (sync
con derivazioni che si auto-risolvono durante `main()`) lo richiede. La
sola differenza fra sync e async è lo **scheduling dei callback**:
immediato nel writer thread (sync) vs schedulato nel loop (async).

### RX.3 — Attivazione per handler

La presenza/assenza del dispatcher è governata da un flag per handler
(naming provvisorio `_subscriptions_enabled`). Default **`False`**:
l'handler nasce strutturale (S1/S2/S4), e la reattività push è un opt-in
esplicito delle sottoclassi che la usano (S3/S6/S7). Coerente con il
principio "nessun costo per chi non lo usa".

### RX.4 — Organizzazione di `roadmap/reactivity/`

Ogni scenario documenta: setup, garanzie del framework, responsabilità
dello sviluppatore, caveat, esempio canonico. La separazione concettuale
chiave (dall'analisi del legacy JS): **SourceDispatcher** (mutazioni della
topology → mount/unmount/rebuild) e **DataDispatcher** (mutazioni di
valore → aggiornamento proprietà) restano **macchine distinte**, non fuse.

---

## Area SUITE — Orchestratore multi-handler (in discussione)

Livello 2 architettura: orchestratore di N handler con dati condivisi
(caso guida: un report con più documenti eterogenei). Non formalizzato in
v0.5.0. Resta nel workspace di discussione `temp/subtask/builder_suite/`
con 7 domande aperte. Citato qui per dare orizzonte.

---

# PARTE III — DISCUSSIONI APERTE

Eredità da v0.4.0 (restano aperte): `@struct_method` sull'handler — tag
custom in mixin separati — `requires` sulla pagina — manifest dei widget
JS — `schema_export` / `from_grammar` — orchestratore multi-handler.

Nuove di v0.5.0:

- ~~**Q-BAG5-dup**~~ **chiusa**: l'unicità è garantita alla creazione
  (`BAG.4`, check in `_command_on_node`), quindi `node_by_id` può fermarsi
  al primo match senza cercare duplicati durante il lookup.
- ~~**Q-BAG4-uniqueness**~~ **chiusa**: trattamento asimmetrico.
  **Unicità = controllo attivo** alla creazione (`_command_on_node`):
  presupposto di funzionamento di `node_by_id`. **Immutabilità = nessun
  controllo**: developer adulto, la walk stateless non ha stato da
  proteggere (`BAG.4`).
- ~~**Q-RX-flag**~~ **chiusa**: `_subscriptions_enabled` default **`False`**
  (handler strutturale di default, reattività opt-in).
- ~~**Q-PTR-sintassi**~~ **chiusa**: il Livello 1 copre **l'intera
  tassonomia** dei pointer (assoluti, relativi, simbolici, con attributo).
- ~~**Q-HND2-hotswap**~~ **chiusa**: l'hot-swap è supportato e sicuro
  by design. Sostituire `_sourceroot["main"]` stacca la vecchia source,
  che muore col GC insieme ai suoi figli (nessun leak, grazie all'assenza
  di mappa — `BAG.5`). Nessun meccanismo dedicato necessario.
- ~~**Q-PTR-punto**~~ **chiusa**: il trigger è la walk del render.
  `RendererBase` **offre** una walk condivisa + helper di risoluzione
  pointer (servizio opzionale, non imposto). Renderer normale la consuma
  (pointer risolti gratis); renderer speciale fa la propria walk e chiama
  l'helper. L'emissione nel dialetto resta sempre del renderer (`DAT.2`).

---

## Riferimenti

Contratto v0.5.0 prodotto nella sessione coordinatore Claude Code locale
del 2026-05-26/27 e promosso in vigore il 2026-05-27, su
`genro-builders develop@9c12d59` (300 test verdi), partendo dal contratto
v0.4.0 (in vigore dal 2026-05-15, archiviato). Contesto:

- `roadmap/architecture-contract.md` (v0.4.0) — base delle aree BLD/HND/BAG.
- `genro-textual/temp/subtask/upgrade_to_v0.4.0/REACTIVE_MODEL_JS.md`
  §1bis/§10/§11 — analisi legacy JS, fonte di HND.2, RX.2, RX.4, DAT.2.
- `temp/subtask/data_binding/startdoc.md`,
  `temp/subtask/builder_suite/startdoc.md` — workspace di discussione.
- `temp/handoff_coordinator_2026-05-26.md` — handoff coordinatore.
- Memorie: `feedback_no_fallback_no_silent_recovery`,
  `feedback_use_existing_apis`, `project_contract_v0_3_0_validated`.
