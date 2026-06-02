# Architecture contract — genro-builders — v0.7.0

**Status**: 🟢 IN VIGORE dal 2026-06-02.
**Sostituisce**: v0.6.0 (archiviata in
`roadmap/outdated_versions/architecture-contract-v0.6.0.md`).

Il diff logico tra versioni del contratto vive in
`roadmap/CONTRACT_CHANGELOG.md`.

**Stato del codice rispetto al contratto**: il codice è allineato sui punti
chiave dell'identità dei nodi, del render subsystem, del data binding
pull-based, dei data-element e del loro compute, e della reattività push di
Livello 0 (`live()`). Sono implementati: la risoluzione lazy dei pointer a
render time (`DAT.2`), i data-element come `@element` marcati (`DAT.3`), il
compute "fetta 1" — primo calcolo in `create()` e singola ondata di ricalcolo
su mutazione (`DAT.4`), e il re-render totale verso target dentro una sezione
`live()` (`RX.1`, Livello 0). Restano da implementare: la cascata reattiva
multi-ondata dei data-element ("fetta 2", `DAT.4`), i livelli di reattività push
con granularità SRC/DATA (`RX`), e l'orchestratore multi-handler (`SUITE`).

---

# PARTE I — PREMESSA

## Scopo

Questo documento fissa i contratti architettonici di `genro-builders`.
È il **punto di arrivo** verso cui il codice converge, non la fotografia
istante-per-istante dello stato (quella vive negli handoff e in git).

Il contratto descrive **come deve essere fatto** il sistema. Quando il
lavoro sarà completo, questo documento coinciderà con la documentazione
architetturale del prodotto: chi lo legge capisce com'è strutturato
genro-builders e perché.

Le decisioni sono organizzate per **aree tematiche**. Ogni decisione è
identificata da un codice `<AREA>.<n>` (es. `HND.1`, `RX.2`). Una
rinegoziazione si fa esplicitamente: si bump-a la minor del contratto, si
conserva la versione superata in `roadmap/outdated_versions/` e si registra il
delta in `roadmap/CONTRACT_CHANGELOG.md`.

## Glossario

- **Builder**: la grammar pura di un dialetto (`HtmlBuilder`,
  `MarkdownBuilder`, `SvgBuilder`, `XsdBuilder`). Definisce `@element`,
  `@abstract`, `@subbuilder`, lo schema di validazione, le regole di
  serializzazione. Solo dichiarazione, nessun engine.
- **BuilderHandler**: la macchina che consuma un builder. Possiede i
  wrapper-root `_sourceroot` / `_dataroot`, le due fasi `create`/`render`,
  il dict `renderers: mode → {target, instance}`, la `pointer_map` e il
  compute dei data-element.
- **Preset** (`HtmlBuilderHandler`, ecc.): sottoclassi di `BuilderHandler`
  con `builder_class` già fissata. L'utente eredita da uno di questi.
- **Source**: il bag (`BuilderSource`) popolato in `create`, serializzato
  in `render`. È la forma unica del documento.
- **Data**: il bag dei dati associato all'handler (`_dataroot["main"]`),
  letto dai pointer a render time e scritto dal compute.
- **Data-element**: un nodo della source che non rappresenta markup ma una
  **logica sui dati** — un valore di seed, una formula, un effetto. Sono
  `@element` ordinari marcati `_meta['data_element']` (`DAT.3`),
  trasparenti al render, eseguiti dal compute (`DAT.4`). I tre kind sono
  `data_setter` / `data_formula` / `data_controller`.
- **Resolver** (pull): nodo con computazione lazy, eseguita alla lettura.
- **Trigger** (push): notifica scatenata da una mutazione verso i
  sottoscrittori. Vive nell'area `RX` e nel sotto-documento
  `roadmap/reactivity/`.
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

`@subbuilder` è **autonomo**: non passa per `__init_subclass__` e non
appare in `_class_schema`; il suo wrapper vive sulla classe builder come
metodo regolare, dispatchato da `_BuilderBagNodeMixin.__getattr__` che
ricade su `_attach_subbuilder`.

### BLD.3 — Builder = grammar pura; renderer come property `renderer_<mode>`

Il builder contiene **solo** la grammar: decoratori, schema, validazione.
I renderer disponibili per quel dialetto sono dichiarati come
**property `renderer_<mode>`** sulla classe builder. Ogni accesso alla
property restituisce un'**istanza fresca** del renderer concreto, legata
al builder via `builder=self`. Le istanze sono pensate per essere
**effimere**: vivono lo spazio di una `handler.render(...)` e poi sono
scartate.

Il rendering vive in `RendererBase` e nei concreti (`XmlRenderer`,
`HtmlRenderer`, `SvgRenderer`, `CssRenderer`). `BagBuilderBase`
dichiara `renderer_xml` (ereditato da ogni dialetto); i builder
concreti aggiungono i propri (`HtmlBuilder.renderer_html`,
`SvgBuilder.renderer_svg`, `CssBuilder.renderer_css`).

Aliasare un mode su un renderer esistente è una riga di classe:
`renderer_xhtml = renderer_html`. L'utente che vuole esporre un mode
in più sul proprio subbuilder usa lo stesso pattern (descriptor
sharing).

Niente registry `_renderers` né metodo `register_renderer`: la lista
dei mode supportati si scopre per introspezione dei nomi che iniziano
per `renderer_` sulla classe builder. Errore esplicito
(`AttributeError`/`KeyError`) quando il mode richiesto non corrisponde
ad alcuna property.

Conseguenze: il builder è testabile in isolamento; aggiungere un mode
significa aggiungere una property o un alias, non un metodo
imperativo; estendere un dialetto è una subclass del builder con
property aggiuntive.

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
ricostruire l'handler, e fa sopravvivere le sottoscrizioni fatte sul
wrapper.

Gli slot aggiuntivi del wrapper (`["workspace"]`, `["meta"]`, ...) sono
**predisposti** ma non usati nel base. Sono punti di estensione futuri.

**Backref**: entrambi i wrapper-root hanno il backref di `genro_bag`
acceso esplicitamente in `__init__` (`set_backref()`). È parte del
contratto strutturale: serve a `abs_datapath` (`DAT.2`) e a ogni
risalita ancestor sui nodi, indipendentemente dalla reattività.

`HND.2` è puramente strutturale: il backref è acceso sempre. L'armamento
delle subscribe push avviene in `create()` (`HND.4`), non in `__init__`.

### HND.3 — Render con `mode` e `target`, multipli e nominati

`render` esiste sia sul builder che sull'handler.

**Sul builder** — property `renderer_<mode>` per ogni mode supportato
(`BLD.3`). `BagBuilderBase` dichiara `renderer_xml` (ereditato); i
dialetti aggiungono i propri (`renderer_html`, `renderer_svg`,
`renderer_css`). Niente registry imperativo.

**Sull'handler** — `self.renderers: dict[str, dict]` con entry
`{"target": ..., "instance": RendererBase}` per ogni mode toccato
dall'handler. Popolata lazy dall'helper interno `_ensure_mode(mode)`:
alla prima `set_render_target(mode, ...)` o alla prima `render(mode=...)`,
l'handler accede alla property `builder.renderer_<mode>` (via
class-level descriptor, per bypassare il dispatch grammar che
intercetta gli attributi sul nodo), inietta `self` come `handler` e
salva l'entry. `set_render_target(mode, target, default=False)` riusa
la stessa entry per scrivere il target.

Semantica del `target`:

- `False` → forza ritorno stringa, ignora target registrato;
- altro falsy (`None`, `""`, `0`) → usa il target registrato sotto il mode;
- truthy → usato direttamente per quella chiamata.

Risoluzione del `mode`: argomento esplicito > `_default_render_mode`
dell'handler > `_default_render_mode` del builder.

**Flusso di `handler.render(startnode=None, mode=None, target=None, **opts)`**:

1. risolve `effective_mode` e `effective_target` come sopra;
2. recupera R₀ via `_ensure_mode(effective_mode)` (l'istanza è cached
   per mode in `self.renderers`);
3. setta `r0.mode = effective_mode` e `r0.add_render(self.builder, r0)`
   (seed della cache di R₀ con sé stesso);
4. chiama `result = r0.render(startnode or self.source, **opts)`;
5. chiama `r0.finalize(result, effective_target)`.

`r0.render` è il walk universale di `RendererBase`: per ogni nodo
chiama `node.runtime_values()`, ricorre sui figli, e produce il
frammento locale tramite `rendered_item(node, item, runtime_attrs,
**opts)`. La cache `renders` di R₀ (chiave `id(builder)`) gestisce
i sub-builder polimorfici.

`r0.finalize` dispatcha via `getattr(self, f"finalize_{self.finalize_method}")`.
Tutti i renderer attuali (HTML/SVG/CSS/XML) sono `finalize_method = "raw"`
ed ereditano `finalize_raw` dalla base (writeable target → file
path, file-like o callable; `None` → ritorna il valore).

L'API utente è **una sola**: `handler.render(startnode, mode, target, **kw)`.
Niente shortcut `render_<mode>(...)`.

Sub-builder (BLD.2): il sub-renderer è risolto dal walk universale
via `RendererBase.get_render(builder)` di R₀ — accesso alla property
`builder.renderer_<default_mode>` del sub-builder, iniezione
dell'handler, memoizzazione nella cache `renders` di R₀ con chiave
`id(builder)`. Non entra in `self.renderers` (che riguarda solo i
mode del builder primario).

### HND.4 — Lifecycle: `create()` in sei passi, poi `render()`

```python
page = CustomerPage()
page.create()                                # vedi i sei passi sotto
page.set_render_target('html', 'out.html', default=True)
page.render()                                # serializza la source sul target
```

`create()` esegue, in ordine:

1. **`setup()`** — override-point (no-op di default): popola i dati
   iniziali **prima** che `main` costruisca la struttura, così `main`
   può leggere `self.data` (es. ciclare sulle chiavi per generare
   struttura ripetuta). Tiene i dati (setup) e la struttura (main) come
   due passi nettamente separati.
2. **`main(self.source)`** — costruisce il documento. Le subscribe non
   sono ancora attive: gli insert dell'API builder **non** dispatchano a
   `on_source_change`.
3. **`register_pointer(self.source.parent_node)`** — cammina il sottoalbero
   della source e popola `self.pointer_map` una volta (`DAT.2`).
4. **Primo calcolo** — interroga la source per i data-element da eseguire
   allo start, via `source.query`: ogni `data_setter` (semina il dato) più
   ogni `data_formula` / `data_controller` marcato `_on_start`; li esegue
   con `compute_logic` (`DAT.4`). Le subscribe non sono ancora armate, così
   queste scritture seminano i dati **senza** innescare una cascata reattiva.
5. **Subscribe** — `_sourceroot` / `_dataroot` vengono sottoscritti: da qui
   in poi ogni mutazione fluisce a `on_source_change` / `on_data_change` e,
   sul lato data, al compute reattivo (`DAT.4`).
6. **`_live_enabled = True`** — la reattività è armata; `live()` è ammesso
   (`RX.1`).

`render(startnode, mode, target, **kwargs)` dispatcha al renderer del mode
e gli affida la source (`HND.3`).

Quando un sottoalbero ha un sub-builder (`BLD.2`), il `_builder` sui nodi
del sottoalbero determina quale builder è attivo localmente, e il render
segue automaticamente il builder corretto (`HND.3` + `BAG.3`).

### HND.5 — Thread safety non promessa

`BuilderHandler` e le classi correlate **non sono thread-safe**. La
proprietà è ereditata da `genro_bag.Bag`. Il framework **non introduce
lock** sui mutatori né su `render()` (l'unica eccezione è l'`RLock` che
serializza le sezioni `live()`, `RX.1`).

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
  schema, data-element e tag fuori schema), se l'attr `node_id` è presente
  si verifica via `BAG.5` (`node._check_unique_id`) che non esista già un
  nodo con lo stesso id; in caso contrario errore esplicito. Motivo:
  l'unicità è un **presupposto di funzionamento** di `node_by_id` (con due
  id uguali il lookup sarebbe ambiguo), non una guardia paternalistica.
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
        raise KeyError(node_id)
    return node
```

Complessità O(N) sulla dimensione della source. Per source piccole/medie il
costo è invisibile. Un'eventuale ottimizzazione (cache opt-in) si introduce
**senza cambiare l'API** quando uno scenario reale la richiede.

Sub-builder e handler condividono la stessa source: il lookup attraversa
naturalmente l'albero indipendentemente da quale builder controlla quale
sottoalbero.

---

## Area DAT — Dati, resolver, pointer, data-element

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

### DAT.2 — Pointer risolti a render time

Il framework abilita la **risoluzione lazy dei pointer a render time**. Un
nodo della source può contenere un pointer (es. `^customer.name`); al
render, il renderer interpreta il pointer e legge dalla data bag
(`_dataroot["main"]`) il valore.

Questo livello **non è reattività**: è lookup di dati al momento del
render. Copre gli scenari S2 e gran parte di S3/S4 senza subscribe,
callback o cascate.

Sintassi: copre **l'intera tassonomia** dei pointer, riprendendo le forme
del legacy JS:

- assoluti: `^path` (dalla radice della data bag);
- relativi: `^.x`, `^..x`, `^...x` (datapath contestuale e risalita);
- simbolici: `^#node_id.path` (cross-tree, usano `BAG.5` per il lookup),
  e gli scope `^#FORM.x`, `^#ANCHOR.x`, `^#ROW.x`, `^#WORKSPACE.x`;
- con attributo: `^path?attr` (accesso all'attributo invece che al valore).

**Soggetto della risoluzione — il nodo.** `abs_datapath(path)` e
`runtime_values()` vivono su `_BuilderBagNodeMixin`: il nodo compone i
propri path assoluti e risolve i propri valori runtime (pointer + template
`${name}`), restituendo `(runtime_value, runtime_attrs)`. L'handler resta
proprietario di `pointer_map`/`register_pointer` e della data bag.

**Dove avviene la risoluzione** — il trigger è la **walk del render**
(`BLD.3`/`HND.4`):

- `RendererBase` **offre** un generatore di walk condiviso; il nodo
  fornisce la risoluzione via `runtime_values()`. È un **servizio**, non
  una gabbia.
- Il renderer concreto **normale** consuma la walk offerta → la traversata
  non è reimplementata e i pointer arrivano già risolti.
- Un renderer con esigenze speciali (visita non standard, doppia passata)
  **può** guidare la propria walk e chiamare `runtime_values()` dove serve.
- **Sempre** del renderer concreto resta l'**emissione del nodo nel
  proprio dialetto** (markup, escape, open/close, formattazione).

**Mappa dipendenze pointer (`self.pointer_map`)** — l'handler espone

```python
self.pointer_map: dict[str, dict[int, BuilderBagNode]]
```

popolata da `register_pointer(node, unregister=False)`. Il metodo
cammina il sottoalbero a partire da `node` e per ogni pointer trovato
costruisce la chiave secondo la regola **per-attributo**:

- pointer su `node.value`    → chiave = `node.abs_datapath(pointer)`;
- pointer su `node.attr[a]`  → chiave = `node.abs_datapath(pointer) + "?" + a`.

La granularità per-attributo è il payload operativo per il consumatore
reattivo: quando arriva la notifica "è cambiato `path?color`", l'handler sa
esattamente quale attributo aggiornare sul nodo, senza ricostruire. Il
valore interno è `dict[int, BuilderBagNode]` indicizzato per `id(node)`
perché `BuilderBagNode` non è hashable; più nodi possono dipendere dalla
stessa chiave.

La ricorsione di `register_pointer` scende **solo** dentro la struttura
builder (`BuilderBag`), mai dentro una `Bag` plain usata come valore (es. il
payload di un `data_setter`, `DAT.3`): i figli di quella sono `BagNode`
plain senza `pointers()`.

`register_pointer(..., unregister=True)` è la simmetrica: rimuove le
entry, prune dei path che diventano vuoti, **silenzioso** su nodi/path
non registrati (tollera scenari di registrazione parziale).

La mappa è mantenuta coerente automaticamente sugli eventi della source:
`_on_source_event` chiama register/unregister su `ins`/`del`, e su `upd`
dispatcha via `_on_upd_value` (matrice 9-casi scalar/pointer/bag ×
scalar/pointer/bag) e `_on_upd_attrs` (per-attributo). Questo mantiene la
`pointer_map` allineata anche quando un valore o un attributo cambia natura
a runtime.

### DAT.3 — Data-element come `@element` marcati

Un data-element è un nodo della source che porta **logica sui dati** invece
di markup. Non è un binario separato: è un **`@element` ordinario** marcato
`_meta={"data_element": True}`. I tre kind sono dichiarati su `BagBuilderBase`:

```python
@element(_meta={"data_element": True})
def data_setter(self, destination: str, value: Any): ...

@element(_meta={"data_element": True})
def data_formula(self, destination: str, func: str | Callable, **kwargs): ...

@element(_meta={"data_element": True})
def data_controller(self, func: str | Callable, **kwargs): ...
```

- **Iniezione in ogni dialetto.** `__init_subclass__` li inserisce nello
  schema di ogni dialetto via `_iter_data_element_methods`, **dopo** gli
  element propri del dialetto: così un data-element (es. `data`) può
  overridare un tag omonimo del dialetto (es. l'HTML `<data>`). Nessun
  dialetto deve ri-dichiararli.
- **Kind dal `node_tag`.** Il tipo del data-element è il tag del nodo
  (`data_setter` / `data_formula` / `data_controller`); non esiste un
  parametro `kind` né un decoratore per-kind.
- **Marker runtime `_is_data_element`.** Quando l'utente chiama
  `node.data_setter(...)`, `element_call` riconosce `_meta['data_element']`,
  mappa i positional sui field dichiarati dalla firma, setta
  `_is_data_element = True` sul nodo, e passa per lo stesso `_command_on_node`
  degli element normali (nessun dispatch dedicato).
- **Trasparenza al render.** I renderer saltano i nodi `_is_data_element`:
  un data-element non emette markup.
- **Value del setter come attributo.** Il `value` del `data_setter` resta
  un **attributo piatto** (non `node.value`), anche quando è una `Bag`.
  Motivo: un attributo che contiene una Bag non viene attraversato dalla
  walk della source, quindi il payload-dati non viene catturato nell'albero
  source (nessuna cattura del backref della Bag dell'utente); inoltre la
  `query(deep=True)` non scende nel payload e la validazione trova `value`
  tra gli attributi.

### DAT.4 — Compute dei data-element

I data-element sono eseguiti dal **compute**, un meccanismo unico con due
punti d'ingresso.

- **Esecutore unico `compute_logic(nodes)`.** Riceve una **lista di nodi**
  (non un path) e li esegue uno per uno via `_compute_node`. La raccolta sta
  nel chiamante:
  - *primo calcolo* (`create()`, `HND.4` passo 4):
    `source.query(what="#n", deep=True, condition=...)` — ogni `data_setter`,
    più formula/controller marcati `_on_start`;
  - *cascata reattiva* (`_on_data_event`): `_nodes_to_compute(path)`.
- **`_compute_node(node)`** dispatcha `match node.node_tag`:
  - `data_setter` → `node.set_relative_data(destination, value)` (seed; value
    è l'attributo piatto, può essere Bag);
  - `data_formula` → `set_relative_data(destination, func(**bindings))`
    (func **pura**);
  - `data_controller` → `func(node, **bindings)` (node esplicito, effetti
    collaterali).
- **`_bindings(node)`** risolve i binding **sempre** via
  `node.runtime_values()` — lo stesso risolutore unico (`^`/`=` pointer,
  template `${}`, futuri default) che usa ogni reader — poi toglie i field
  dello schema (`destination`/`func`/`value`) e i marker `_...`; ciò che
  resta sono i binding passati alla func per nome.
- **`func` = `@staticmethod` per NOME.** La property `data_logic` (lazy +
  cached, default `[self]`, override `_build_data_logic` per restituire una
  logica dedicata o una lista) elenca le sorgenti. `_resolve_logic_func(name)`
  cerca sx→dx, **prima-vince**, via `inspect.getattr_static`: sorgente che
  non possiede il nome → skip; possiede ma **non** come `staticmethod` →
  `TypeError`; miss su tutte → `AttributeError`. Nessun fallback silenzioso.
  Forma canonica per il futuro cross-language (il source serializza il nome,
  non il callable).
- **`data_formula` PURA** `func(**bindings)` (niente `node`); il
  **`data_controller`** riceve `func(node, **bindings)` (node esplicito; se
  serve l'handler: `node._resolve_handler()`).
- **Aggancio reattivo (`_on_data_event`).** Su `upd` compute su
  `path = pathlist[1:]`; su `ins` di foglia su
  `path = pathlist[1:] + node.label`; **skip** se `reason == "autocreate"`
  (nascita di un contenitore intermedio strutturale, da non far reagire
  finché le foglie non esistono). `del` fuori scope.

**Granularità della raccolta (`_nodes_to_compute`).** Tre match contro la
`pointer_map` (chiavi = path assoluti, eventualmente `?attr`), confrontando
la parte-path `kp = key.split("?",1)[0]` col `path` mutato:

- *node* — `kp == path`: legge esattamente il dato mutato;
- *container* — `kp.startswith(path + ".")`: legge una foglia dentro il
  contenitore mutato;
- *child* — `path.startswith(kp + ".")`: legge un contenitore di cui è
  cambiato un figlio.

Si tengono solo i nodi `_is_data_element` (un div che legge lo stesso path
non viene ricalcolato); i `data_setter` non portano pointer `^`, quindi non
sono mai in `pointer_map` ed escono per costruzione. Dedup per `id(node)`.

**Fetta 1 (implementata) vs fetta 2 (rinviata).** Oggi il compute è "fetta 1":
una sola ondata. La ri-entranza sincrona di `genro_bag` propaga le catene
quando i valori intermedi esistono (la scrittura di un `_compute_node`
ri-fira `_on_data_event`, ma la collect annidata filtra `_is_data_element` e,
nello scope di questa fetta, restituisce lista vuota → passata inerte).
La **fetta 2** — coda **FIFO** breadth-first, anti-loop (dict
node→(input, count) + backstop `DEFAULT_MAX_NODE_RUNS`), `ContextVar` per la
cascata — è rinviata.

### Macro reattive sul nodo (`SET` / `GET` / `PUT` / `FIRE`)

`_BuilderBagNodeMixin` espone quattro macro **maiuscole** (marcatura
deliberata di un DSL reattivo), alias di `set_relative_data` /
`get_relative_data`:

- `SET` → scrittura con reason di default;
- `PUT` → scrittura con `reason=False`;
- `FIRE` → scrittura con `fired=True` (trigger esplicito);
- `GET` → lettura.

`set_relative_data` normalizza `reason None → True` (parità col legacy
`gnrdomsource.js`). Altri valori di `reason` sono lasciati liberi finché un
consumatore (lato widget/client) non li esiga.

---

## Area RX — Reattività push

### RX.1 — Livello 0 (`live()`) implementato; livelli successivi rinviati

Il contratto **ammette** la reattività push (trigger, dispatcher,
subscribe utente, resolver dependency-tracked). Il **Livello 0** è
implementato; il dettaglio dei livelli successivi vive in
`roadmap/reactivity/`, organizzato **per scenario d'uso** (S1-S7).

**Livello 0 — `handler.live(target)` (implementato).** Un context manager
che apre una sezione critica in cui ogni mutazione su source o data scatena
un **re-render totale** verso il target:

```python
with page.live("out.html"):
    page.data["title"] = "Updated"   # → render automatico su out.html
```

- Dentro il `with`, `_on_source_event` / `_on_data_event` chiamano
  `render(target=self._live_target)` dopo aver mantenuto la `pointer_map`
  (source) o eseguito il compute (data). Con `target` esplicito il render va
  lì; senza, ricade sul target di default (`set_render_target`).
- Fuori dal blocco l'handler resta **pull-only**: nessun auto-render.
- La sezione è **sincrona** e serializzata da un `RLock`; la re-entry sullo
  stesso thread è ammessa e lo stato del parent è ripristinato all'uscita.
- Hook `on_live_enter` / `on_live_exit` (no-op di default; `on_live_exit`
  gira anche se il corpo solleva, dal `finally`) per setup/teardown
  per-sezione.
- Richiede `_live_enabled` (acceso da `create()`, `HND.4` passo 6):
  `live()` prima di `create()` solleva `RuntimeError`.

Il Livello 0 è un **compromesso esplicito** rispetto alla separazione
SRC/DATA descritta in `RX.4`: fonde i due dispatch in un unico re-render
totale; la granularità è obiettivo dei livelli successivi (inclusa la
cascata fetta 2 dei data-element, `DAT.4`).

### RX.2 — Il dispatcher push è capability del base, non solo async

Il dispatcher push **non è esclusivo di una sottoclasse async**. È
capability del base, perché lo scenario S3 (sync con derivazioni che si
auto-risolvono durante `main()`) lo richiede. La sola differenza fra sync e
async è lo **scheduling dei callback**: immediato nel writer thread (sync)
vs schedulato nel loop (async).

### RX.3 — Attivazione per handler

La reattività è governata da un flag per handler, `_live_enabled`. Default
**`False`**: l'handler nasce strutturale (S1/S2/S4); `create()` lo accende
dopo aver armato le subscribe. Coerente col principio "nessun costo per chi
non lo usa".

### RX.4 — Organizzazione di `roadmap/reactivity/`

Ogni scenario documenta: setup, garanzie del framework, responsabilità
dello sviluppatore, caveat, esempio canonico. La separazione concettuale
chiave (dall'analisi del legacy JS): **SourceDispatcher** (mutazioni della
topology → mount/unmount/rebuild) e **DataDispatcher** (mutazioni di
valore → aggiornamento proprietà) restano **macchine distinte** nei livelli
con granularità, non fuse — il Livello 0 (`RX.1`) le fonde di proposito.

**Specifica di dettaglio in lavorazione**: `roadmap/reactivity/contract.md`
(Livello 0, `live()`) e `roadmap/reactivity/data-elements.md` (cascata dei
data-element, fetta 2).

---

## Area SUITE — Orchestratore multi-handler (in discussione)

Livello 2 architettura: orchestratore di N handler con dati condivisi
(caso guida: un report con più documenti eterogenei). Non formalizzato.
Resta nel workspace di discussione `temp/subtask/builder_suite/` con
domande aperte. Citato qui per dare orizzonte.

---

# PARTE III — DISCUSSIONI APERTE

Restano aperte: tag custom in mixin separati — `requires` sulla pagina —
manifest dei widget JS — `from_grammar` Python loader (companion del
producer `to_grammar`, già implementato) — orchestratore multi-handler
(= `SUITE`).

Chiuse (cite per memoria):

- `@struct_method` sull'handler — `schema_export` producer
  (`BagBuilderBase.to_grammar(path)`, formato in
  `src/genro_builders/builder/GRAMMAR_FORMAT.md`).
- **Unicità/immutabilità `node_id`**: trattamento asimmetrico —
  unicità = controllo attivo alla creazione (`_command_on_node`),
  immutabilità = nessun controllo (developer adulto, walk stateless)
  (`BAG.4`).
- **`node_by_id` walk-based** senza indice mantenuto (`BAG.5`).
- **Tassonomia pointer completa** (`DAT.2`).
- **Punto di risoluzione pointer = walk del render** (`DAT.2`).
- **Hot-swap** del payload sotto `["main"]` supportato e sicuro by design
  (nessun leak grazie all'assenza di mappa, `BAG.5` + `HND.2`).
- **Data-element come `@element` marcati**: niente decoratore autonomo, kind
  dal `node_tag`, value del setter come attributo (`DAT.3`).
- **Compute fetta 1**: esecutore unico, primo calcolo in `create()`,
  `func` = `@staticmethod` per nome via `data_logic`, formula pura /
  controller con node, singola ondata (`DAT.4`).
- **Reattività push Livello 0** (`live()` context manager, re-render totale
  verso target) implementata (`RX.1`).

---

## Riferimenti

Contratto v0.7.0 prodotto e promosso in vigore il 2026-06-02 nella sessione
Claude Code locale `fc44e7ee-ee56-4600-89f6-1bf5dcf2f5f3`, partendo dal
contratto v0.6.0 (in vigore dal 2026-06-01, archiviato). Il bump riconcilia
il contratto con lo stato del codice: data-element come `@element` marcati
(`DAT.3`), compute dei data-element fetta 1 (`DAT.4`), reattività push
Livello 0 (`RX.1`), `create()` in sei passi (`HND.4`).

Contesto:

- `roadmap/outdated_versions/architecture-contract-v0.6.0.md` — versione
  precedente.
- `roadmap/CONTRACT_CHANGELOG.md` — diff logico tra versioni.
- `roadmap/reactivity/contract.md`, `roadmap/reactivity/data-elements.md` —
  specifiche di dettaglio della reattività.
- `src/genro_builders/builder_handler.py`,
  `src/genro_builders/builder_bag.py`,
  `src/genro_builders/builder/base.py` — implementazione di riferimento.
- Memorie: `feedback_no_fallback_no_silent_recovery`,
  `feedback_use_existing_apis`, `feedback_cite_session_id_in_docs`,
  `project_data_elements_model`, `project_data_logic_resolution`,
  `project_reactive_macros_set_put_fire`.
