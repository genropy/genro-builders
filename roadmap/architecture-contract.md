# Architecture contract — genro-builders — v0.8.0

**Status**: 🟢 IN VIGORE dal 2026-06-10.
**Sostituisce**: v0.7.0 (archiviata in
`roadmap/outdated_versions/architecture-contract-v0.7.0.md`).

Il diff logico tra versioni del contratto vive in
`roadmap/CONTRACT_CHANGELOG.md`.

**Stato del codice rispetto al contratto**: il codice è allineato su:
identità dei nodi, render subsystem (walk universale, dispatch per-nodo,
minimi di cardinalità), data binding pull-based con registrazione alla
lettura, data-element e compute "fetta 1", handler multibuilder
(`add_builder`/`activate`), reattività push Livello 0 con `live()` come
sezione critica e coda di render per mount, **component** (`CMP`:
singolo/store/iterate/frattale, reattività L0), **render parziale**
(`RX.1`: TargetWrapper, busta `replace`/`insert`/`remove`, optimizer di
netting, identità seriale `target_id`). Restano da implementare: la
cascata reattiva multi-ondata dei data-element ("fetta 2", `DAT.4`), i
livelli di reattività con granularità SRC/DATA (`RX`) e il per-riga dei
component (`CMP.7`), **`@container`** (`CMP.9`, deciso 2026-06-11),
`<domain>requires`/`include_components` (`CMP.6`), lo **`@slot`**
(`PAG.6`, design completo, codice assente) e lo strato Application
(`APP`).

---

# PARTE I — PREMESSA

## Scopo

Questo documento fissa i contratti architettonici di `genro-builders`.
È il **punto di arrivo** verso cui il codice converge, non la fotografia
istante-per-istante dello stato (quella vive negli handoff e in git).

Le decisioni sono organizzate per **aree tematiche**, identificate da un
codice `<AREA>.<n>`. Una rinegoziazione si fa esplicitamente: si bump-a
la minor del contratto, si conserva la versione superata in
`roadmap/outdated_versions/` e si registra il delta in
`roadmap/CONTRACT_CHANGELOG.md`.

## Glossario

- **Builder**: la grammar di un dialetto (`HtmlBuilder`, `SvgBuilder`,
  `CssBuilder`, `XsdBuilder`, ...) E l'identità di un documento: porta
  `name` (nome di mount), `source`, `create()`/`render()`. Una **pagina**
  è una subclass di builder con `main(self, root)`.
- **BuilderHandler**: la sorgente dati dei builder montati. Possiede UN
  `_dataroot` segmentato, monta N builder per nome (`add_builder`),
  possiede `pointer_map`, `activate()` e la sezione critica `live()`.
  Non si sottoclassa e non è un render engine.
- **Application**: lo strato fra il mondo esterno (websocket, REPL,
  thread) e l'handler. La reattività live presuppone un'Application
  (`APP`).
- **Source**: il bag (`SourceBag`) popolato in `create`, serializzato in
  `render`. Vive sotto il segmento strutturale `SOURCE_ROOT` (`_root_`).
- **Data**: il datastore segmentato dell'handler; ogni builder montato
  legge/scrive il proprio segmento (`builder.data`), `_` è il comune.
- **Data-element**: `@element` marcato `_meta['data_element']` che porta
  logica sui dati (kind: `data_setter`/`data_formula`/`data_controller`),
  trasparente al render, eseguito dal compute (`DAT.3`/`DAT.4`).
- **Component**: elemento di grammatica **nominato con body** (`CMP`):
  il nodo resta nominato nella source, l'espansione è un fatto effimero
  del render. Autosufficiente e guidato dai dati.
- **Container**: pezzo riusabile che **genera source alla chiamata**
  (`CMP.9`): il body corre una volta e scrive nodi veri, riempibili dal
  chiamante. Erede di `@struct_method` (nome pensionato).
- **Pointer**: riferimento a un dato (`^path` reattivo, `=path`
  passivo), risolto a render time leggendo la data bag.
- **Resolver** (pull): nodo con computazione lazy, eseguita alla lettura.
- **node_id**: identità opzionale e immutabile di un nodo, come una
  primary key; unicità **per documento**, garantita dal root builder
  (`BAG.4`).

## I tre scenari d'uso

1. **Senza dati** — builder nudo: nessun handler, `name` omissibile
   (default: la tipologia del dialetto). Costruisce e rende, nessun
   pointer. Script, generazione statica.
2. **Con dati** — builder montato su un `BuilderHandler` (nessuna
   Application): pointer `^`/`=` risolti al render, data-element,
   compute. Pull-only: nessun auto-render.
3. **Con live** — handler + **Application**: `activate()` arma la
   reattività, le mutazioni avvengono dentro `live()` e producono
   render automatici. Il mondo esterno parla con l'Application.

Il dettaglio per scenario della reattività vive in `roadmap/reactivity/`.

## Principio cross-runtime: un linguaggio, due interpreti

**Mai runtime misto.** O tutto Python (ricetta + render), o ricetta
Python + tutto il resto in JS (bag/builder JS sul client). Conseguenze:

- la macchina reattiva Python è dimensionata sul solo binario
  all-Python;
- la source è il **contratto semantico** fra gli interpreti: stessa
  ricetta + stesse mutazioni → stesso albero (golden test cross-runtime,
  da costruire);
- i component restano **nominati** nella source: ogni interprete ha la
  propria implementazione del body per quel nome (`CMP.1`).

**Identità per seriale (`target_id`).** Il server è autoritativo;
l'identità di un elemento nel target renderizzato è un **seriale per
documento** (`n1`, `n2`, ...) assegnato al nodo generante alla prima
emissione e conservato sull'oggetto (slot, mai un attributo della bag):
legato all'oggetto e non alla posizione, nessuna mutazione strutturale
lo invalida; deterministico (ordine di render) per i fixture
committati. Il render reattivo lo emette su OGNI elemento (qualunque
elemento può diventare bersaglio, contenitore o ancora a runtime);
l'id d'autore vince e rinuncia all'indirizzabilità. La mutazione
strutturale viaggia come `insert` (frammento nuovo + ancora `before`) /
`remove`; la sostituzione di contenitore resta (per ora) l'unità di
patch per le espansioni component. Le espansioni non ricevono MAI un
seriale proprio (reincarnano): la loro identità è **derivata e
deterministica** — `<base>.<label di iterazione>....<ordinale>`, dove
la base è l'id del nodo component (seriale o d'autore), le label sono
le identità delle righe negli store attraversati e l'ordinale segue
l'ordine di costruzione del body (codice: il rebuild è identico).
Solo nel render reattivo; il render statico non porta identità.
Residui noti: stato client effimero.
[Emendamento 2026-06-11: sostituisce "identità per path" — il path
slittava ad ogni insert, il seriale è inerte.]
[Emendamento 2026-06-11 sera: identità derivata delle espansioni —
vedi CMP.7, mappa dei figli virtuali implementata lato write-back.]

---

# PARTE II — AREE E DECISIONI CHIAVE

## Area BLD — Builder (grammar)

### BLD.1 — Builder come subclass; grammatica estesa via mixin

Ogni builder è una subclass del builder base e definisce il proprio
dialetto (tag, `sub_tags`, `parent_tags`, regole di render). Il
pacchetto fornisce mixin opzionali per estendere la grammatica; il
dialetto base resta sempre nel builder. La grammatica si può arricchire
anche **per istanza** a runtime con i component di un mixin
(`include_components`, `CMP.6`): la schema di classe resta intatta.

### BLD.2 — Sub-builder via decoratore dedicato `@subbuilder`

Lo switch di dialetto a metà albero è dichiarato con un decoratore
separato da `@element`. Da `<svg>` in giù il builder attivo è
`SvgBuilder`; cambia solo lo slot `_builder` dei nodi del sottoalbero
(`BAG.3`).

- **Propagazione dell'handler**: `get_subbuilder` istanzia il
  sub-builder e gli passa l'handler del padre (a cascata sui sub-builder
  annidati), così i pointer del sottoalbero risolvono sugli stessi dati
  del documento. Il sub-builder è solo grammatica: non ha un segmento
  dati proprio.
- **Confine letterale**: il nodo-involucro di confine fra dialetti
  (`svg` dentro html, `foreignObject` dentro svg) emette i propri
  attributi **letterali nei due sensi**: non appartiene per intero a
  nessuno dei due dialetti, quindi nessuna trasformazione
  dialetto-specifica vi si applica.

### BLD.3 — Builder = grammar; renderer come property `renderer_<mode>`

I renderer di un dialetto sono **property `renderer_<mode>`** sulla
classe builder; ogni accesso restituisce un'istanza fresca ed effimera
(vive lo spazio di una `render()`). La base dichiara `renderer_xml` e
`renderer_yaml` (ereditati da ogni dialetto); i concreti aggiungono i
propri (`renderer_html`, `renderer_svg`, `renderer_css`). Alias = una
riga di classe (`renderer_xhtml = renderer_html`). Niente registry: i
mode si scoprono per introspezione dei nomi `renderer_*`; mode
inesistente → errore esplicito.

`render(mode="xml")` è un render vero (pointer risolti, marker
filtrati); la vista grezza della source è `source.to_xml()` — non è un
render mode.

### BLD.4 — Grammatica severa a definizione di classe

Un item di `sub_tags` non riconosciuto dallo schema solleva
`ValueError` **alla definizione della classe** (validazione eager in
`__init_subclass__`, messaggio `Classe.elemento:`). Gli errori di
grammatica sono errori dell'autore del dialetto: emergono subito, non
alla prima chiamata.

---

## Area PAG — Il builder come documento/pagina

### PAG.1 — Il nome appartiene al builder

`BuilderBase(name=...)`: `name` è l'identità di mount verso l'handler
(la label del suo segmento dati). Omesso, default = tipologia del
dialetto (`_name`, es. `"html"`). `add_builder` **legge** il nome, mai
lo assegna; unico vincolo = collisione (e `_`, riservato al segmento
comune). Una pagina = una subclass di builder con `main(self, root)`.

### PAG.2 — Source sotto `SOURCE_ROOT` (`_root_`)

La source vive sotto il segmento strutturale `SOURCE_ROOT = "_root_"`
di un wrapper-root: garanzia albero-non-foresta. È una **costante
strutturale, MAI un indirizzo**: la partizione semantica del documento
è il primo livello della DATA bag (nomi di mount + `_`), non della
source. `self.source` è il payload che `main` popola; il wrapper ha il
backref acceso (necessario ad `abs_datapath` e a ogni risalita
ancestor).

### PAG.3 — Lifecycle: `create()` = setup + main + primo calcolo

```python
page = CustomerPage(name="customer")
handler = BuilderHandler()
handler.add_builder(page)        # monta, semina il segmento, crea
page.render(target="out.html")
```

`create()` esegue: `setup(self.data)` (semina i dati del segmento),
`main(self.source)` (costruisce il documento), poi il **primo calcolo**
(ogni `data_setter` + formula/controller marcati `_on_start`, via
`compute_logic`). Se il contesto è reattivo (`APP`), `create()` arma
anche la subscribe della **source**; la subscribe dei **dati** la arma
`activate()` sull'handler (`HND.4`) — dopo il primo render, perché la
`pointer_map` si popola leggendo (`DAT.2`).

Un builder nudo (scenario 1) fa `create()` + `render()` da solo:
`handler=None`, data bag vuota, `setup` innocuo.

### PAG.4 — `render(mode, target, validate=True, **opts)` sul builder

Il render appartiene al builder. `mode` default =
`_default_render_mode` del dialetto; `target`: `False` → ritorna la
stringa ignorando i target registrati; falsy → target registrato
(`set_render_target`); truthy → usato direttamente.

**Minimi di cardinalità verificati nel walk pre-render**: il walk
ricalcola fresco per nodo i figli minimi richiesti (NESSUNO stato
memorizzato: la rimozione di un figlio renderebbe stantio qualunque
flag). Un solo errore con l'elenco completo dei nodi incompleti.
`validate=False` emette deliberatamente un documento parziale. Per i
dialetti XSD è la prima rete strutturale, non sostituisce la
validazione XSD a valle. (Il massimo di cardinalità è verificato
all'inserimento.)

`render_nodes(nodes, **opts)` è l'ingresso del flush di `live()`:
al passo uno ignora la lista e rende tutto il builder; il render
parziale per nodo è un raffinamento successivo (`RX.1`).

### PAG.5 — `node_by_id` sul builder; l'unicità la garantisce il root builder

Il lookup `node_by_id` vive **sul builder di pagina** e attraversa i
confini di dialetto (cammina la source vera del documento, sottoalberi
sub-builder inclusi). L'unicità di `node_id` ha lo stesso perimetro: **un
namespace per documento, garantito dal root builder** — il check alla
creazione interroga il root builder dell'albero di destinazione,
qualunque dialetto o punto d'ingresso crei il nodo. La stessa pagina
montata due volte non collide con se stessa su handler diversi. Lookup
walk-based senza indice mantenuto (`BAG.5`); il riferimento simbolico
`^#<id>.path` risolve nello stesso perimetro.

I sub-builder non hanno un namespace proprio: sono grammatica, non
identità — un'istanza per ospite per dialetto, **cached** sul builder
ospite (stesso pattern della cache dei renderer, `RND.1`), così ogni
sottoalbero `<svg>` del documento condivide lo stesso `SvgBuilder` e la
cache dei renderer (chiave `id(builder)`) li serve con un solo
sub-renderer.

### PAG.6 — `@slot(node_id)`: riempimento per id alla nascita (da implementare)

Complementare di `main`: un metodo della **pagina** (builder) decorato
`@slot("<node_id>")` viene invocato dal framework nell'istante in cui,
durante la costruzione, nasce un nodo con quel `node_id` esplicito — il
nodo è la radice su cui il metodo costruisce. Match esatto e letterale
(l'id è documentato da chi crea la struttura: "la grammar è
documentazione"); ordine indotto dalla costruzione (chi crea il nodo fa
scattare il riempitivo); composizione ricorsiva (uno slot crea nodi-id
che fanno scattare altri slot); le label auto-generate non scattano mai.

Caso guida: la **cornice** di una live app (`contrib/ws_live`) dichiara
i suoi punti di riempimento con id documentati (`ws-header`, `ws-left`,
`ws-footer`, ...); la pagina si abbona solo a quelli che le servono —
con un solo punto basta l'override di `main`, con N punti l'override
unico non scala. Inversione del controllo speculare al component
(`CMP`): il component è una struttura riusabile che l'autore piazza;
lo slot riempie un punto di una struttura creata da altri.

Spec di dettaglio: `roadmap/slot-decorator.md` (da riallineare: scritta
quando i metodi vivevano sull'handler; oggi vivono sulla pagina).
Decisioni implementative (punto di aggancio dell'hook, raccolta dei
metodi, comportamento dello slot orfano) in fase TDD.

---

## Area HND — BuilderHandler (datastore)

### HND.1 — L'handler è la sorgente dati, non un engine

Una pagina è un builder; un builder che legge pointer ha bisogno di una
sorgente dati. Il `BuilderHandler` è quella sorgente: possiede UN
`_dataroot` segmentato e monta i builder per nome consegnando a ognuno
il proprio segmento. **Non si sottoclassa e non è un render engine**:
il render vive sul builder. L'handler fornisce i dati e (alla lettura)
traccia chi legge cosa (`pointer_map`).

L'orchestratore multi-handler ("SUITE") è **dissolto**: il caso che lo
motivava (documenti eterogenei su dati condivisi — excel+word,
traefik/compose/k8s) è coperto dal multibuilder (N builder su segmenti
+ `_` comune).

### HND.2 — `_dataroot` segmentato; `_` è il segmento comune

Primo livello del datastore = nomi di mount + `_` (creato alla nascita,
spazio condiviso fra i builder montati). `handler.data` espone l'intero
datastore segmentato; `builder.data` il proprio segmento.
`handler.setup(data)` è l'override-point per seminare il comune.
Il backref è acceso alla nascita (parte del contratto strutturale).

### HND.3 — `add_builder(*builders)`: monta per nome e crea

Per ogni builder: verifica il nome (assente → errore; `_` → errore;
duplicato → errore), registra, crea il segmento, inietta `handler` e
`data` (il segmento), mette l'handler sul source-root (ogni nodo lo
raggiunge via property `handler`, `BAG.3`), e chiama `create()`
(`PAG.3`). Il primo builder montato è il default.

### HND.4 — `activate()`: chiude l'avviamento

`activate()` rende ogni builder montato (il **primo render popola la
pointer_map**, `DAT.2`), poi — se c'è un'Application — arma la
subscribe dei **dati** e accende `_live_enabled`. `live()` prima di
`activate()` → `RuntimeError` (una pagina mai resa non è reattiva:
mappa vuota, nulla reagirebbe).

### HND.5 — Thread safety non promessa; `live()` è l'unica serializzazione

`BuilderHandler` e le classi correlate non sono thread-safe (proprietà
ereditata da `genro_bag.Bag`). Il framework non introduce lock sui
mutatori né su `render()`; l'unica eccezione è l'`RLock` che fa di
`live()` la sezione critica di mutazione (`RX.1`). Chi condivide un
handler fra thread muta **dentro `live()`**; la sincronizzazione di
ogni altro accesso è responsabilità sua.

---

## Area APP — Application (da formalizzare in dettaglio)

L'Application è lo strato fra il mondo esterno e l'handler: possiede il
ciclo di vita (websocket, REPL, scheduler), incanala ogni mutazione
dentro `live()` (il lock lo prende `live()`, l'Application non lo tocca
mai), tutto sync. La reattività live **presuppone** un'Application
(`activate()` arma la subscribe dei dati solo se presente).
L'implementazione di riferimento attuale è `contrib/ws_live` (live app
su websocket, script `genro-ws-live`). Il design del livello
applicativo — desktop a pane-iframe, registro delle pagine vive (il
gnrdaemon dissolto dall'async), websocket unico master/satelliti con
chiave di routing — è approvato in `roadmap/application-registry.md`
(2026-06-10). La formalizzazione fine dell'area (API, hook,
multi-sessione) è rimandata a quando ws_live si stabilizza.

---

## Area BAG — Bag e nodi

### BAG.1 — SourceBag e SourceBagNode via mixin

`SourceBag` = `Bag` + mixin; `SourceBagNode` = `BagNode` + mixin. La
logica builder-aware vive nei mixin; le classi di `genro-bag` restano
intatte.

### BAG.2 — Layering

Base comune (dispatch grammar, metadati) + specializzazione semantica
della fase create/render. La data bag è `Bag` pura.

### BAG.3 — `_builder` slot; `handler`/`root_builder` property via root

Il nodo porta il solo slot `_builder` (il builder attivo: il principale,
o il sub-builder nei sottoalberi `@subbuilder`). **Niente slot
`_handler` sui nodi**: `handler`, `root_builder` e `root_builder_name`
sono property che risalgono a `Bag.root` — l'handler è unico per
documento e vive sul source-root (`HND.3`). Nodi leggeri: nessun dato
duplicato, si risale la catena ancestor.

### BAG.4 — `node_id` come primary key, unicità per documento

- **Unicità → controllo attivo** alla creazione da grammar (nel wrapper
  unico di creazione), nel perimetro del documento = root builder
  (`PAG.5`): con due id uguali `node_by_id` sarebbe ambiguo. Costo O(N)
  solo per i nodi che portano un `node_id`.
- **Immutabilità → nessun controllo**: mutare un `node_id` esistente è
  responsabilità del developer (walk stateless, nessuno stato derivato
  da proteggere).

### BAG.5 — Lookup walk-based, senza indice mantenuto

`node_by_id` è un lookup ad albero via `get_node_by_attr`; miss →
`KeyError`. Nessuna mappa cached: per source piccole/medie il costo è
invisibile; un'eventuale cache opt-in si introduce senza cambiare
l'API. L'assenza di indici rende sicuro by design l'hot-swap del
payload.

---

## Area DAT — Dati, pointer, data-element, presentazione

### DAT.1 — Resolver come capability del base

Un nodo può portare una computazione lazy (`BagResolver`), eseguita
alla lettura, sempre supportata (sync e async). Con dispatcher push
attivo i resolver possono diventare dependency-tracked.

### DAT.2 — Pointer risolti a render time; registrazione alla lettura

Un nodo della source può contenere un pointer; al render si legge dalla
data bag. Tassonomia completa: assoluti `^path`; relativi `^.x`/`^..x`;
simbolici `^#node_id.path` e scope `^#FORM.x` ecc.; con attributo
`^path?attr`. `^` sottoscrive, `=` legge una-tantum.

**La risoluzione vive sul builder** (`builder.runtime_values(node)`,
che raggiunge l'handler via `self.handler`); il nodo è il soggetto
(`abs_datapath` compone i path assoluti anteponendo segmento e volume,
`#parent` collassato). Il trigger è la **walk del render**: il walk
universale di `RendererBase` chiama `runtime_values` per ogni nodo; un
renderer speciale può guidare la propria walk.

**Registrazione alla lettura (signals-like).** La `pointer_map`
dell'handler (`dict[abs_path, dict[id(node), node]]`) NON si popola a
priori: si auto-popola come **effetto della lettura** — `runtime_values`
registra ogni `^` mentre lo legge (`handler._register_path`); `=` viene
letto e basta. Invariante: **una pagina deve fare il primo render per
finire l'avviamento** (per questo `activate()` rende prima di armare,
`HND.4`). Asimmetria strutturale: *aggiungere* alla mappa = effetto del
render; *togliere* = azione esplicita su mutazione della source (il
render non sa cosa esisteva prima).

**Macro reattive sul nodo**: `SET` (scrive, reason default) / `PUT`
(scrive, `reason=False`) / `FIRE` (evento, `fired=True`, non persiste)
/ `GET` (legge) — alias maiuscoli di `set/get_relative_data`,
marcatura deliberata di un DSL reattivo.

### DAT.3 — Data-element come `@element` marcati

Un data-element porta logica sui dati invece di markup: `@element`
ordinario marcato `_meta={"data_element": True}`; kind dal `node_tag`
(`data_setter`/`data_formula`/`data_controller`); iniettati in ogni
dialetto da `__init_subclass__` (dopo gli element propri: un
data-element può overridare un tag omonimo); trasparenti al render;
positional mappati sui field della firma; il `value` del setter resta
attributo piatto (mai `node.value`), anche quando è una Bag.

### DAT.4 — Compute dei data-element

Esecutore unico `compute_logic(nodes)` **sul builder**; l'handler
coordina la cascata multi-builder (`execute_logic` raggruppa i nodi
toccati per builder e delega). Primo calcolo in `create()` (`PAG.3`).
`_compute_node` dispatcha sul kind: setter → seed; formula **pura**
`func(**bindings)` → scrive `destination`; controller →
`func(node, **bindings)` (effetti). I binding si risolvono sempre via
`runtime_values` (stesso risolutore di ogni reader). `func` =
`@staticmethod` risolta **per nome** via `data_logic` (sx→dx,
prima-vince, errori espliciti — forma canonica per il cross-runtime: la
source serializza il nome, non il callable).

Granularità della raccolta (`_relevant_nodes`): match node / container
/ child contro la `pointer_map`; si tengono solo i data-element; dedup.
**Fetta 1 (implementata)**: una sola ondata. **Fetta 2 (rinviata)**:
coda FIFO breadth-first, anti-loop (dict node→input + backstop),
cascata completa.

### DAT.5 — Presentazione lato dati: `mask` e `_wdg`

Il dato sa presentarsi. Sul **nodo dati** (non sulla ricetta):

- `mask` — maschera col vocabolario legacy di gnrformatter (`%s` = il
  valore), applicata al valore risolto;
- `_wdg` — dict di attributi-eccezione che **viaggiano col dato** e si
  depositano sul nodo lettore, **vincendo** sulla ricetta (l'eccezione
  batte il default statico). Solo letture di valore.

Solo presentazione: mai sui binding delle formule (vogliono il dato
crudo), mai sulle letture `?attr`, mai su valori Bag.

### DAT.6 — Template inputs consumati

Un attributo referenziato da un template `${...}` **dello stesso nodo**
è un input del template: una volta espanso è stato consumato e non
viene emesso da nessun renderer. La regola è il **consumo**, non un
prefisso: il nome è libero, è l'uso — visibile nella ricetta — che lo
marca. Idioma canonico "dato calcolato + unità d'autore":
`div(w='^mywidth', width='${w}px')`. Un attributo che deve essere sia
emesso sia riusato passa anch'esso da template.

---

## Area CMP — Component e Container

Design dei component del 2026-06-10 (verbale:
`roadmap/component-design.md`, decisioni D1-D10; qui la forma
contrattuale; implementato salvo `CMP.6` e il per-riga di `CMP.7`).
Risolve l'asimmetria che fece rimuovere i component alla v0.4:
l'espansione non entra mai nella ricetta.

L'area ospita **due cittadini** (emendamento 2026-06-11), distinti dal
discriminante della **riempibilità**:

- **`@component`** — vive nel *render*: espansione effimera che rinasce
  coi dati. Autosufficiente: il chiamante lo parametrizza, non ci mette
  contenuto. (`CMP.1`-`CMP.8`)
- **`@container`** — vive nella *source*: il body corre UNA volta alla
  chiamata e genera nodi veri, che il chiamante riempie. (`CMP.9`)

### CMP.1 — Elemento di grammatica nominato, con body

`@component` in un mixin (es. `CommonComponents`) entra in grammatica
come un element. Chiamarlo istanzia un **nodo normale nella source, col
nome del component e i suoi attributi**: nessuna espansione a
call-time. Il nome nella source è il contratto cross-runtime: ogni
interprete (Python oggi, JS domani) ha la propria implementazione del
body per quel nome.

### CMP.2 — Espansione solo a render-time, effimera

Il walk incontra il nodo component → crea una **new_root con tag fisso
trasparente a perdere** (costante strutturale, scartata al render) → il
body costruisce TUTTO dentro di essa, radice vera inclusa (tag e
attributi della radice = competenza dell'autore del component).
**Albero, non foresta**: esattamente un figlio nella new_root,
violazione = errore esplicito. L'espansione si rende e si butta.

### CMP.3 — Tre forme di chiamata; `store` e `iterate` distinti

1. singolo a parametri: `pane.address_block(company='^.company', ...)`;
2. singolo a record: `pane.address_block(store='^sender')` — `store` è
   **l'ancora dati** del component (rinominato da `value` il
   2026-06-10: evita la collisione con `node_value` e con l'attributo
   HTML `value`);
3. multiplo: `pane.div().state_row(iterate='^.states')` — un'espansione
   per figlio della Bag.

`store` non itera MAI: la cardinalità la dichiara l'autore con
`iterate`. Il contenitore esterno dell'iterate è del chiamante
(grammatica ordinaria). `iterate`/`store` sono parole della macchina:
consumate, mai passate al body né emesse. `store` non si risolve a
valore: è un path — la macchina lo stampa come `datapath` sul wrapper
a perdere dell'espansione (oggetto SUO), e i pointer relativi del body
(`^.company`) vi si ancorano per la normale risalita. Due piani:
contesto-base sul wrapper (macchina), ancoraggio fine nel body (la
label nell'iterate, niente nel singolo). I `^` dell'espansione si
risolvono al render ma NON si registrano (`CMP.7`); in pointer_map
resta il nodo component col suo `store` — al cambio del record il
blocco si ri-rende.

### CMP.4 — Dispatch nel walk e firma del body

`render(node)`: runtime_values PRIMA del branch; poi element (come
oggi) / **component** (terza gamba) / subbuilder. Component con
`iterate` risolto a Bag → un giro per figlio passando **solo
`node.label`**; senza → un giro coi kwargs della chiamata che saturano
la firma. Firma: `def nome(self, root, node_label=None, **parametri)`
(`node_label` solo nei component iterabili; un singolo non lo
dichiara). Il body aggancia la radice al dato (`datapath` dalla label,
relativa all'ancora `store`/`iterate` sul wrapper) e dentro usa
pointer relativi.

**Pass-through dei kwargs-pointer** (emendamento 2026-06-11): un kwarg
il cui valore crudo è un **pointer reattivo** satura la firma come
**pointer assolutizzato** (sintassi `^volume:rest`, context-free), non
come valore risolto. L'indirizzo deve raggiungere il nodo finale che
il body costruisce: lì si risolve come un pointer scritto a mano ed
emette il gancio di write-back (`data-value-pointer`) — risolverlo
prima del body lo consumerebbe (input muto). I valori non-pointer e i
pointer passivi (`=`) restano risolti. Vincolo: il body costruisce
struttura coi kwargs-pointer, non computa sul valore — la logica sui
dati appartiene ai data-element.

### CMP.5 — Nessuna validazione

Né di posizionamento né sul tag emesso dal body. La grammatica registra
e dispaccia. L'unico vincolo è strutturale (CMP.2).

### CMP.6 — Arricchimento per istanza

`include_components(*mixins)` inietta i component di un mixin nella
copia per-istanza dello schema (la classe resta intatta). La famiglia
`<domain>requires` sulla pagina (`pyrequires` per i component Python,
js/css a seguire) è da ricostruire sul modello attuale (era
sull'handler pensionato).

### CMP.7 — Reattività: subscription grossa, risoluzione fine

I pointer interni alle espansioni **non entrano mai** nella
pointer_map. In mappa c'è solo il nodo component (i suoi pointer
dichiarati). La granularità per-riga si ricava con l'**aritmetica dei
path**: evento sotto la radice dell'iterate → residuo → primo segmento
= label del child (quale blocco), resto = cosa è cambiato. Eventi
strutturali con la stessa aritmetica. L'**identità dell'unità
per-riga**: le espansioni non portano `target_id` per costruzione
(reincarnano) — la loro identità è DERIVATA (Premessa: catena
`base.label....ordinale`). La **mappa dei figli virtuali** è
IMPLEMENTATA lato write-back (2026-06-11, verificata su semplice/
annidato/iterato/iterato-annidato): al render reattivo dell'espansione
il renderer stampa l'id derivato su ogni nodo (id d'autore del
component = base della catena; `id` è macchinario consumato, mai un
kwarg del body) e registra in `builder._writeback_map` i soli nodi
SCRIVIBILI (pointer su `value`/`checked` — i lettori puri no):
`{id derivato → nodo}`. Il nodo trattenuto è la sede di tipizzazione
(dtype), validazione (`validate_*`) e destinazione (pointer →
`abs_datapath`): il mutate risolve l'id e legge TUTTO dal nodo —
niente path né dtype dal filo. La ri-espansione purga il proprio
prefisso (coerente con l'effimero). Le patch per-riga sulla stessa
identità restano da implementare nel filone RX.

**Row logic (implementata 2026-06-11).** I data-element dichiarati nel
body di un component sono **regole di MUTAZIONE**: il documento
caricato è fidato così com'è (il render non calcola MAI nulla;
`_on_start` e `data_setter` in un body d'espansione → errore
esplicito). Lo stesso walk di registrazione li CATALOGA invece di
renderli: per ogni riga, i binding risolti in path assoluti entrano in
`handler.expansion_logic` (`{path trigger → nodo-regola}`, purge per
prefisso di riga). Una riga ricalcola **sse il path mutato è tra i
SUOI binding risolti**: il binding di riga accende una riga, il
binding condiviso (cambio in testata) le accende tutte, l'annidato si
scopa da solo (il binding di gruppo risolve dentro il proprio
gruppo). L'esecuzione sta nella cascata eventi (stessa coda,
anti-loop); le scritture rientrano e concatenano (qty → total →
controvalore). I nodi d'espansione accedono al datastore via
``data_handler`` (l'handler è unico per documento; ``handler`` resta
None — il gate D9 non si tocca).

### CMP.8 — Componibilità frattale

Component dentro component (normali/iterate, anche auto-ricorsivi su
dati ad albero), senza limite: stesso dispatch del walk per le
espansioni, datapath che si compongono attraverso i livelli,
subscription solo sul component più esterno (correttezza minima =
ri-rendi il blocco esterno). Terminazione data-driven; eventuale
backstop a contatore da decidere all'implementazione.

Complemento di selezione (master-detail, datapath variabile
`datapath="^..."`): `roadmap/reactivity/variable-datapath.md`.

### CMP.9 — `@container`: il pezzo riusabile che genera source

Deciso il 2026-06-11. `@container` in un mixin entra in grammatica come
un element (stesso dispatch `__getattr__` di `@component`), ma il body
corre **una volta, alla chiamata**, e scrive **nodi sorgente veri**:
con `target_id`, patchabili uno a uno, riempibili dal chiamante. Il
body riceve il nodo su cui è invocato e ritorna l'handle che ritiene
utile (la zona center, un oggetto-zone, la radice generata).

Il **discriminante** fra i due cittadini è la riempibilità: *il
chiamante ci mette contenuto suo?* → `@container`; *è autosufficiente
e guidato dai dati?* → `@component`. La conseguenza meccanica è
l'identità: un contenitore che ospita pane (es. iframe nel desktop)
DEVE essere fatto di nodi veri — un'espansione effimera non ha
indirizzabilità interna e degraderebbe ogni cambiamento a replace del
blocco intero.

`@struct_method` è **pensionato come nome**: la sua meccanica (parità
utente col legacy gnrwebstruct: firma `def nome(self, pane, **kwargs)`,
strip del prefisso, dispatch su nodo e bag) vive sotto `@container`.
Nessun periodo di doppio nome: i chiamanti migrano con il rename.

---

## Area RND — Renderer

### RND.1 — Walk universale, dispatch per-nodo sul dialetto del nodo

`RendererBase` offre il walk condiviso: per ogni nodo risolve
`runtime_values` e produce il frammento via `rendered_item`. **Ogni
fase per-nodo gira sul renderer del dialetto del nodo** (il `_builder`
del nodo decide, anche a metà albero); la cache dei sub-renderer è per
builder. `finalize(result, target, **opts)` compone e consuma il
target (writeable/callable/path; `None` → ritorna). Gli `**opts`
raggiungono walk e finalize. I dialetti object-based sovrascrivono la
composizione.

### RND.2 — Note di dialetto HTML

- **Booleani nativi per presenza**: per gli attributi booleani HTML
  (`disabled`, `checked`, ...) `True` → attributo nudo, `False` →
  assente (così `disabled='^locked'` reattivo funziona); `data-*` e gli
  altri attributi restano literal (`"true"`/`"false"`).
- **Escape del valore `style`** al punto di immersione nel markup (non
  nella normalizzazione).
- **Unità CSS = responsabilità dell'autore**: il renderer è un
  serializzatore, non un validatore CSS — niente auto-`px`, niente
  controlli sui numerici.

### RND.3 — CssRenderer legge gli attributi crudi

Il CSS oggi non è reattivo: `CssRenderer` legge `node.attr` crudo
(niente pointer/keyword). Quando il CSS diventerà reattivo, passerà a
`runtime_values` come gli altri.

---

## Area RX — Reattività push

### RX.1 — `live()` è LA sezione critica di mutazione (Livello 0+)

Chi muta il documento (source o data) lo fa dentro
`with handler.live():` — entrare = acquisire l'`RLock` dell'handler
(prendere il lock = entrare nella sezione). Le sezioni di altri thread
si accodano; la cascata reattiva gira **dentro** la sezione (stesso
stack, nessuna ri-acquisizione). L'annidamento stesso-thread si
**fonde** nella sezione esterna: una coda, un solo flush all'uscita
esterna, `target` vietato alla sezione annidata (il target della
sezione vince sul default registrato, per quella sezione sola).

**Coda di render unificata**: ogni evento source/data registra il path
toccato per mount (`add_render_path(builder_name, path)`); fuori
sezione non si accoda nulla (nessun flush in arrivo). Il flush rende
ogni builder con almeno un nodo toccato. Al passo uno il flush fa un
render totale per builder (`render_nodes` ignora la lista);
`_optimize_render` è pass-through — render parziale per nodo e
riduzione della lista sono il raffinamento successivo.

Decoratore **`@live`** (esportato da `genro_builders.builder`): avvolge
un metodo nella sezione (`self` handler, o `self.handler`).

Richiede Application + `activate()` (`HND.4`): senza, `RuntimeError`.
**Vietato il live senza Application** — varrebbe come sezione che gira a
vuoto (nessuna subscribe armata): anche i test passano dall'App.

### RX.2 — Il dispatcher push è capability del base

Non esclusivo di una sottoclasse async; la differenza sync/async è solo
lo scheduling dei callback (immediato nel writer thread vs schedulato
nel loop).

### RX.3 — Attivazione per handler

`_live_enabled` default `False` (l'handler nasce strutturale); lo
accende `activate()` dopo il primo render. Nessun costo per chi non usa
la reattività.

### RX.4 — Organizzazione di `roadmap/reactivity/`

SourceDispatcher (topology) e DataDispatcher (valori) restano macchine
distinte nei livelli con granularità; il Livello 0 le fonde di
proposito. Specifiche di dettaglio: `reactivity/contract.md`,
`reactivity/data-elements.md`, `reactivity/variable-datapath.md`
(visione: datapath variabile, master-detail, collection store).

---

# PARTE III — DISCUSSIONI APERTE

Aperte:

- **Preset sì/no**: il pacchetto deve fornire pagine-preset pronte
  (`HtmlPage`-style) o l'utente parte sempre da `HtmlBuilder` +
  subclass? (Decide la riscrittura di README/docs.)
- **`<domain>requires`** sulla pagina (`pyrequires` per i component,
  js/css per il layer web) — da ricostruire sul modello attuale
  (`CMP.6`).
- **Component**: ancoraggio datapath nella forma `value=`; backstop
  della ricorsione frattale (`CMP.8`).
- **`format` v2**: maschere per dtype/locale col contratto di
  formattazione cross-runtime (il legacy ha già il vocabolario,
  `gnrformatter`).
- **Application**: formalizzazione fine (`APP`).
- **from_grammar** Python loader (companion di `to_grammar`).

Chiuse (per memoria):

- **SUITE dissolta** nel multibuilder handler (`HND.1`).
- **Component reintrodotti** col design `CMP` (la rimozione v0.4 è
  superata: l'asimmetria Python/JS è sciolta dal nodo nominato +
  espansione effimera per interprete). Il ripiego v0.4 "tag custom JS
  dichiarati per nome / manifest dei widget" è **assorbito**: il blocco
  con logica client è un component con body JS (`CMP.1`), il tag nativo
  opaco è un normale `@element` in un mixin (`BLD.1`).
- **`@struct_method`** pensionato come nome (2026-06-11): la meccanica
  (zucchero, parità legacy) vive come **`@container`** (`CMP.9`);
  **`to_grammar`** export.
- **Unicità/immutabilità `node_id`** asimmetriche, per documento
  (root builder) (`BAG.4`/`PAG.5`).
- **Registrazione alla lettura** (niente walk a priori; invariante del
  primo render) (`DAT.2`).
- **Template inputs per consumo** (non per prefisso) (`DAT.6`).
- **Presentazione lato dati** col vocabolario legacy: `mask`/`_wdg`,
  l'eccezione batte il default (`DAT.5`).
- **Minimi di cardinalità: ricalcolo nel walk, mai stato memorizzato**
  (`PAG.4`).
- **Pensionamento `contrib/live`**: ws_live è la live app.
- **No difensivo**: condizioni impossibili → errore esplicito; niente
  fallback silenziosi; `getattr` difensivo solo su duck-typing di API
  pubblica e oggetti di librerie terze.

---

## Riferimenti

Bozza v0.8.0 prodotta il 2026-06-10 nella sessione Claude Code locale
`a47d7ab4-be22-42aa-b2e9-bb0e198e6b40`, a valle del refactor
multibuilder (2026-06-08/09), della sessione di audit e pulizia
(2026-06-09/10) e della digressione di design dei component
(2026-06-10). Versione precedente: v0.7.0 (2026-06-02, sessione
`fc44e7ee-ee56-4600-89f6-1bf5dcf2f5f3`).

Contesto:

- `roadmap/CONTRACT_CHANGELOG.md` — diff logico tra versioni.
- `roadmap/component-design.md` — verbale D1-D10
  dei component (confluito nell'area `CMP`).
- `roadmap/reactivity/` — specifiche di dettaglio della reattività.
- `src/genro_builders/builder/base.py`,
  `src/genro_builders/builder/data_handler.py`,
  `src/genro_builders/builder/source_bag.py`,
  `src/genro_builders/renderer/base.py` — implementazione di
  riferimento.
