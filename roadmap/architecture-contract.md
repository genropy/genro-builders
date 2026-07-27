# Architecture contract — genro-builders — v0.9.0

**Status**: 🟢 IN VIGORE dal 2026-07-26.
**Sostituisce**: v0.8.0 (archiviata in
`roadmap/outdated_versions/architecture-contract-v0.8.0.md`).

Il diff logico tra versioni del contratto vive in
`roadmap/CONTRACT_CHANGELOG.md`.

**Svolta della v0.9.0 — static first.** Il core è **statico**: un handler
piatto che serve i dati a UN builder. La reattività fine non si ripara in
Python, si rifonda su una **compiled bag** emessa da un render mode
`livehtml` (`RX.5`) — perché l'apparato precedente (identità derivata,
`target_id`, motore di regole, corsia lazy, protocollo di patch) non era
reattività mal collocata: era il **surrogato di una struttura che non
esisteva**, che ricostruiva a posteriori l'identità che un albero
materializzato avrebbe avuto gratis. Multibuilder e segmentazione del
datastore escono con esso: erano la stessa feature del segmento `_`, e un
segmento condiviso non significa nulla senza più builder con cui
condividerlo.

**Stato del codice rispetto al contratto**: il codice è allineato su:
identità dei nodi, render subsystem (walk universale, dispatch per-nodo,
render in due passi), data binding pull-based con registrazione alla
lettura, data-element e compute "fetta 1", **handler statico piatto**
(`HND`: un builder, un datastore senza segmenti), **component** (`CMP`:
singolo/store/iterate/frattale). Il re-render è il modello di
aggiornamento: si mutano i dati e si rende di nuovo. Restano da
implementare: la **compiled bag** e il render mode `livehtml` (`RX.5`,
ricerca, documento di disegno proprio), e con essi ogni reattività fine;
**`@container`** (`CMP.9`, deciso 2026-06-11),
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
  `name` (etichetta, non indirizzo), `source`, `create()`/`render()`.
  Una **pagina** è una subclass di builder con `main(self, root)`.
- **BuilderHandler**: la sorgente dati del builder montato. Possiede UN
  `_dataroot` piatto, monta UN builder (`add_builder`) e possiede la
  `pointer_map`. Non è un render engine; si sottoclassa solo per
  `setup()`.
- **Application**: lo strato fra il mondo esterno (websocket, REPL,
  thread) e l'handler. Accende la tracciatura dei lettori
  (`pointer_map`, `RX.3`); la reattività fine arriverà con `RX.5`.
- **Source**: il bag (`SourceBag`) popolato in `create`, serializzato in
  `render`. Vive sotto il segmento strutturale `SOURCE_ROOT` (`_root_`).
- **Data**: il datastore dell'handler, piatto: `handler.data` e
  `builder.data` sono lo stesso oggetto (`HND.2`).
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
3. **Con re-render** — si mutano i dati e si rende di nuovo (`RX.1`):
   nessuna sezione critica, nessun render automatico. Con
   un'Application la `pointer_map` si popola e dice chi legge cosa; il
   consumatore reattivo di quella mappa arriva con la compiled bag
   (`RX.5`).

Il dettaglio della reattività vive in `roadmap/reactivity/`, **da
rileggere alla luce di `RX.5`**.

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
committati. Lo emette il render che lo chiede (`include_datapath`) su
OGNI elemento; l'id d'autore vince e rinuncia all'indirizzabilità. Il
render statico puro non porta identità: non gli serve.

L'**identità derivata** delle espansioni (`<base>.<label>....<ordinale>`)
esce con la v0.9.0: era la ricostruzione a posteriori di un indirizzo per
nodi che non esistono (`CMP.7`). Nella compiled bag (`RX.5`) al suo posto
c'è un **path**, che ogni nodo di una bag ha per costruzione — ed è la
ragione per cui `id` esce dal core in modo strutturale e non come effetto
collaterale.
[Emendamento 2026-06-11: sostituisce "identità per path" — il path
slittava ad ogni insert, il seriale è inerte.]
[Emendamento 2026-07-26 (v0.9.0): il seriale resta come identità
d'elemento su richiesta; cade l'identità derivata delle espansioni e con
essa la mappa dei figli virtuali.]

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
  del documento. Il sub-builder è solo grammatica: non porta dati propri.
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

`BuilderBase(name=...)`: `name` è l'identità del builder — un'etichetta,
non un indirizzo (il datastore è piatto, `HND.2`). Omesso, default =
tipologia del dialetto (`_name`, es. `"html"`). `add_builder` **legge** il
nome, mai lo assegna; unico vincolo = che ci sia. Una pagina = una
subclass di builder con `main(self, root)`.

### PAG.2 — Source sotto `SOURCE_ROOT` (`_root_`)

La source vive sotto il segmento strutturale `SOURCE_ROOT = "_root_"`
di un wrapper-root: garanzia albero-non-foresta. È una **costante
strutturale, MAI un indirizzo**: la partizione semantica del documento
la decide l'autore col `datapath`, non una segmentazione imposta.
`self.source` è il payload che `main` popola; il wrapper ha il
backref acceso (necessario ad `abs_datapath` e a ogni risalita
ancestor).

### PAG.3 — Lifecycle: `create()` = setup + main + primo calcolo

```python
page = CustomerPage(name="customer")
handler = BuilderHandler()
handler.add_builder(page)        # monta e crea
page.render(target="out.html")
```

`create()` esegue: `setup(self.data)` (semina i dati), `main(self.source)`
(costruisce il documento), poi il **calcolo** di ogni data-element, una
volta, in ordine di documento (via `compute_logic`). Se il
contesto è reattivo (`APP`), `create()` arma anche la subscribe della
**source**, che tiene coerente la `pointer_map` sulle mutazioni di
struttura (`DAT.2`).

Un builder nudo (scenario 1) fa `create()` + `render()` da solo:
`handler=None`, data bag vuota, `setup` innocuo.

### PAG.4 — `render(mode, target, **opts)` sul builder, due passi

Il render appartiene al builder. `mode` default =
`_default_render_mode` del dialetto; `target`: `False` → ritorna la
stringa ignorando i target registrati; falsy → target registrato
(`set_render_target`); truthy → usato direttamente.

**Un gesto, due passi.** `materialize(mode, **opts)` cammina la source e
conserva il risultato in `materialized[mode]` (dict sul builder,
indicizzato per modo, simmetrico a `_default_targets[mode]`); `finalize`
consegna. `render` li compone, e resta l'API di ogni esempio e di ogni
test. Conservare il risultato è la base del render parziale (`RX.5`): una
struttura materializzata sopravvive alla chiamata e può essere
confrontata con la precedente. Un re-render sostituisce la voce.

**Il render non valida.** `materialize` cammina e produce, `finalize`
consegna: nessuno dei due verifica la grammatica. Un metodo che
renderizza *e* valida farebbe pagare a ogni nodo di ogni render un
controllo che l'autore non ha chiesto.

Non esiste un ingresso di render parziale: aggiornare = rendere di nuovo
(`RX.1`). Il render parziale su struttura materializzata è competenza
della compiled bag (`RX.5`).

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

### PAG.7 — `validate_source()`: i minimi di cardinalità si chiedono

Il massimo di cardinalità è verificato all'inserimento; il **minimo** ha
senso solo quando l'autore dichiara finito il documento — e lo dichiara
chiamando `validate_source()`, non renderizzando. Ritorna
`(fullpath, [tag mancanti])` per ogni nodo incompleto, lista vuota se il
documento è completo: **riporta, non solleva** — che farne è del
chiamante.

Ricalcolo fresco a ogni chiamata, NESSUNO stato memorizzato (la rimozione
di un figlio renderebbe stantio qualunque flag). Ogni nodo è verificato
contro la grammatica del **proprio** builder, quindi un sottoalbero
sub-builder è validato dal dialetto che l'ha scritto; i nodi che la
grammatica di contenimento ignora sono esclusi da
`require_sub_tag_validation` (data-element, involucri sub-builder,
component). Per i dialetti XSD è la prima rete strutturale, non
sostituisce la validazione XSD a valle.

Cammina la **source**: un component è il singolo nodo che l'autore ha
scritto, la sua espansione è un fatto del render e qui non si vede. La
domanda sul risultato effettivo — espansioni comprese — è
`validate_materialized(mode)`, che arriva col modo di render che emette
dati (`RX.5`): su una lista di chunk di testo non c'è nulla da validare.

---

## Area HND — BuilderHandler (datastore)

### HND.1 — L'handler è la sorgente dati, non un engine

Una pagina è un builder; un builder che legge pointer ha bisogno di una
sorgente dati. Il `BuilderHandler` è quella sorgente: possiede UN
`_dataroot` e monta UN builder su di esso. **Non è un render engine**:
il render vive sul builder. L'handler fornisce i dati e (alla lettura)
traccia chi legge cosa (`pointer_map`). Si sottoclassa solo per
`setup()`, che è un override-point, non un punto di estensione del
comportamento.

Il modulo porta il nome della classe (`builder/builder_handler.py`).

L'orchestratore multi-handler ("SUITE") resta **dissolto**, e con la
v0.9.0 lo è anche il **multibuilder** che lo aveva sostituito: di ~100
call site di `add_builder`, esattamente uno montava più di un builder.
Documenti eterogenei su dati condivisi si compongono con N handler, o —
quando servirà davvero — sopra la compiled bag (`RX.5`).

### HND.2 — `_dataroot` piatto: nessun segmento, nessun `_`

Il datastore è UNA Bag. `handler.data` e `builder.data` sono **lo stesso
oggetto**: non c'è un segmento per builder da distinguere dal tutto, e
non c'è il segmento comune `_` (aveva senso solo fra più builder).
Un path assoluto non porta segmento iniziale: `counter`, non
`page.counter`. `handler.setup(data)` è l'override-point per seminare il
datastore, e riceve la radice. Il backref è acceso alla nascita (parte
del contratto strutturale).

### HND.3 — `add_builder(builder)`: monta e crea

Verifica il nome (assente → errore: un builder senza nome non ha
identità), registra il builder, inietta `handler` e `data` (il datastore
intero), mette l'handler sul source-root (ogni nodo lo raggiunge via
property `handler`, `BAG.3`), e chiama `create()` (`PAG.3`). Montare un
secondo builder è un errore: un handler guida un builder.

Il `name` del builder resta la sua identità — un'etichetta, non un
indirizzo: non è più un segmento di path.

### HND.4 — L'avviamento è il montaggio; il re-render è l'aggiornamento

Non c'è `activate()`: montare crea, e il render si chiede quando serve.
Il modello di aggiornamento del core statico è il **re-render** — si
mutano i dati, si rende di nuovo — e non richiede né sezione critica né
protocollo di patch. La `pointer_map` continua a popolarsi come effetto
della lettura (`DAT.2`) e serve a chi vuole sapere chi legge cosa; il
consumatore reattivo di quella mappa arriverà con la compiled bag
(`RX.5`).

### HND.5 — Thread safety non promessa

`BuilderHandler` e le classi correlate non sono thread-safe (proprietà
ereditata da `genro_bag.Bag`). Il framework non introduce lock sui
mutatori né su `render()`, e non esiste più una sezione critica di
mutazione: chi condivide un handler fra thread sincronizza da sé.

---

## Area APP — Application (da formalizzare in dettaglio)

L'Application è lo strato fra il mondo esterno e l'handler: possiede il
ciclo di vita (websocket, REPL, scheduler), tutto sync. La sua presenza
accende la tracciatura dei lettori (`pointer_map`, `RX.3`); la reattività
fine che la consumerà arriva con la compiled bag (`RX.5`).
L'implementazione di riferimento **non vive più qui**: lo strato
applicativo è migrato in **genro-ws-web** (commit `6d3002a`), che con la
v0.9.0 diventa un ponte fra due compiled bag invece di un produttore di
patch. Il design del livello
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
`^path?attr`. `^` sottoscrive, `=` legge una-tantum. La forma
`volume:field` è **uscita** in v0.9.0 con la segmentazione (`HND.2`):
senza segmenti non c'è un volume da scegliere.

**La risoluzione vive sul builder** (`builder.runtime_values(node)`,
che raggiunge l'handler via `self.handler`); il nodo è il soggetto
(`abs_datapath` compone i path assoluti, `#parent` collassato — nessun
segmento anteposto). Il trigger è la **walk del render**: il walk
universale di `RendererBase` chiama `runtime_values` per ogni nodo; un
renderer speciale può guidare la propria walk.

**Registrazione alla lettura (signals-like).** La `pointer_map`
dell'handler (`dict[abs_path, dict[id(node), node]]`) NON si popola a
priori: si auto-popola come **effetto della lettura** — `runtime_values`
registra ogni `^` mentre lo legge (`handler._register_path`); `=` viene
letto e basta. Corollario: **la mappa esiste solo dopo un render** — una
pagina mai resa non sa chi legge cosa. La registrazione è opt-in
sull'Application: senza, un render one-shot non paga la mappa.
Asimmetria strutturale: *aggiungere* alla mappa = effetto del render;
*togliere* = azione esplicita su mutazione della source (il render non sa
cosa esisteva prima).

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

Esecutore unico `compute_logic(nodes)` **sul builder**. Calcolo in
`create()` (`PAG.3`): girano **tutti** i data-element, una volta, in
ordine di documento. `_compute_node` dispatcha sul kind: setter → seed;
formula **pura** `func(**bindings)` → scrive `destination`; controller →
`func(node, **bindings)` (effetti). I binding si risolvono sempre via
`runtime_values` (stesso risolutore di ogni reader). `func` =
`@staticmethod` risolta **per nome** via `data_logic` (sx→dx,
prima-vince, errori espliciti — forma canonica per il cross-runtime: la
source serializza il nome, non il callable).

**Calcola-poi-renderizza, una passata sola.** Non esiste flag per
chiedere l'esecuzione: tutti e tre i kind calcolano al `create()`, in
ordine di documento (la `query(deep=True)` percorre l'albero dall'alto in
basso). Quando `render()` parte il datastore è **completo**, quindi un
nodo può leggere un valore che un data-element scrive più in BASSO nel
documento. Corollario: `render()` resta **puro** — legge il datastore e
produce una stringa, non calcola nulla; due render dello stesso documento
danno lo stesso risultato.

È **una sola passata e non c'è ricalcolo**: una formula che legge un
valore scritto da una formula successiva vede il valore precedente, in
silenzio. Ordinare i calcoli è responsabilità dell'autore, esattamente
come in uno script — l'ordinamento per dipendenze è motore reattivo, non
statico. `data_logic` / `_build_data_logic` / `_resolve_logic_func`
restano intatti: sono la macchina che la compiled bag (`RX.5`)
riprenderà.

[Emendamento 2026-07-27: prima di questa revisione formula e controller
calcolavano solo se marcati `_on_start=True`, e il renderer emetteva un
`UserWarning` su ognuno che incontrava in un documento non reattivo. Il
flag è stato **rimosso** (oggi è un attributo non dichiarato, quindi un
errore) e il warning con esso: si accendeva su tutti e 3 i punti della
suite, tutti falsi positivi — pagine corrette che avevano già calcolato.]

La cascata — raccolta per granularità contro la `pointer_map`, coda FIFO
breadth-first, anti-loop, ondate multiple — appartiene alla compiled bag
e non vive più in Python: la vecchia "fetta 2" non è rinviata, è
**ricollocata** (`RX.5`).

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
**pointer assolutizzato**, non come valore risolto — ed essendo assoluto
è context-free da sé (non inizia con `.`, quindi sopravvive al rientro in
`abs_datapath` su un nodo d'espansione). L'indirizzo deve raggiungere il nodo finale che
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

### CMP.7 — L'espansione è effimera: corretta senza reattività, reale nella compiled bag

I pointer interni alle espansioni **non entrano mai** nella
pointer_map. In mappa c'è solo il nodo component (i suoi pointer
dichiarati). Con `iterate` i nodi ripetuti **non esistono**: la source
tiene UN nodo component (la ricetta), gli N blocchi sono un fatto del
render, gettato dopo l'uso — i nodi reincarnano a ogni render.

**Senza reattività questo è corretto e basta.** Nulla deve raggiungere
l'espansione: i pointer si risolvono come lettura a tempo di
composizione, e il blocco si rifà quando si rifà il render (`RX.1`).
L'espansione effimera non è un compromesso, è la forma giusta di una
ricetta.

**Storia, e perché la v0.9.0 la riscrive.** La v0.8.0 costruiva sopra
questa clausola un apparato per dare identità fine a nodi che non ce
l'hanno: identità derivata (catena `base.label....ordinale`), mappa dei
figli virtuali per il write-back, patch per-riga e di cella, catalogo
campo→ordinale, coda delle formule con dedup, indice di purge del
writeback, corsia lazy, motore di regole a coordinate. Funzionava ed era
profilato (vedi sotto). Ma era il **surrogato di una struttura che non
esisteva**: ricostruiva a posteriori l'identità che un albero
materializzato avrebbe avuto gratis. Aprire il "gate D9" (registrare i
pointer interni) richiedeva o riferimenti a nodi morti nella
pointer_map, o innestare l'espansione nella source — cioè materializzare
come struttura ciò che il modello definisce come output di render.

La risposta non è dentro `iterate`: è la **compiled bag** (`RX.5`), dove
le righe esistono come entità indirizzabili con fullpath propri, senza
toccare la source. La domanda "i nodi dell'espansione esistono?" ha
risposta diversa sui due lati, e questa è la soluzione, non il problema.
Tutto l'apparato è depositato in `genro-ws-web@c88c6e6`
(`attic/partial-render/`); la sua specifica è
`roadmap/render-layer-html-ws.md`.

**Numeri da conservare** (misurati il 2026-06-12, baseline per chi
costruirà il grid data-widget e la compiled bag): coda delle formule —
un grand total con binding `^rows` su broadcast di 1500 righe passava da
2,9s a 113ms eseguendo una volta per flush invece di N; purge
indicizzato — la ri-registrazione scandiva la wmap per ogni riga (15,8M
di `startswith` a 1500 righe, 36M su un broadcast a 3000), e l'indice a
segmenti ha reso il primo paint lineare puro (750/1500/3000 =
1,53/3,09/6,20s, ~2,1 ms/riga). Il costo residuo era la costante
lineare: il body riesegue per ogni riga attraverso la macchina
grammaticale (~1/3), risoluzione e composizione dei pointer (~1/3), e il
documento viaggia come HTML intero (3,7MB a 3000 righe — il client è
innocente: parse 56ms, layout 340ms). Direzioni nominate allora e ancora
valide: riempimento progressivo a chunk (percezione) e grid data-widget
JS che riceve la proiezione JSON invece dell'HTML (costo).

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
builder. Il walk **non valida** (`PAG.7`) e non compone: accoda i
frammenti in una lista, qualunque cosa siano.
`finalize(result, target, **opts)` compone e consuma il target
(writeable/callable/path; `None` → ritorna) — è il secondo passo di
`PAG.4`, chiamabile su un risultato già materializzato. Gli `**opts`
raggiungono walk e finalize; quelli di documento (`doc_header`) li
dichiara il finalize del dialetto. I dialetti object-based
sovrascrivono la composizione.

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

## Area RX — Reattività

### RX.1 — Il re-render è il modello di aggiornamento del core statico

Si mutano i dati, si rende di nuovo. Nessuna sezione critica, nessuna
coda di render, nessun protocollo di patch: il render è già la funzione
che porta i dati nel documento, e rifarlo è la via più corta e sempre
corretta per rifletterne il cambio.

Escono con la v0.9.0, e con essi il `target_id`, l'identità derivata,
l'optimizer di netting e la busta `replace`/`insert`/`remove`: la
`live()` come sezione critica, il decoratore `@live`, la coda per mount
(`add_render_path`), `render_nodes`, la corsia lazy e il catalogo delle
regole di riga. Il materiale è depositato in
`genro-ws-web@c88c6e6` (`attic/partial-render/`) e la sua specifica di
ricostruzione resta `roadmap/render-layer-html-ws.md`.

### RX.2 — Il dispatcher push è capability del base

Non esclusivo di una sottoclasse async; la differenza sync/async è solo
lo scheduling dei callback (immediato nel writer thread vs schedulato
nel loop). Il `Bag` porta gli eventi nativi (`ins`/`upd`/`del` su un
path): sono il vocabolario su cui la compiled bag (`RX.5`) si costruirà.

### RX.3 — La `pointer_map` è opt-in sull'Application

`_register_path` è no-op senza Application: un render one-shot non paga
la tracciatura. Con Application la mappa si popola alla lettura
(`DAT.2`) e dice chi legge cosa — il suo consumatore reattivo arriva con
`RX.5`.

### RX.4 — Organizzazione di `roadmap/reactivity/`

SourceDispatcher (topology) e DataDispatcher (valori) restano macchine
distinte nei livelli con granularità. Specifiche di dettaglio:
`reactivity/contract.md`, `reactivity/data-elements.md`,
`reactivity/variable-datapath.md` (visione: datapath variabile,
master-detail, collection store). **Tutte da rileggere alla luce di
`RX.5`**: descrivono l'apparato Python uscito con la v0.9.0.

### RX.5 — La reattività fine si rifonda su una compiled bag (ricerca)

Senza reattività la source è una **ricetta** e il render è il piatto: i
pointer funzionano come lettura a tempo di composizione, e l'espansione
effimera di `iterate`/`@component` è corretta perché nulla deve
raggiungerla (`CMP.7`).

Con reattività serve un terzo oggetto fra ricetta e piatto: una
**compiled bag**, la forma espansa e materializzata della source. Non il
piatto (la stringa HTML) ma la struttura che *tiene* i punti reattivi —
è lei il target, porta la mappa, reagisce alle mutazioni, e si collega
al mondo (nodi DOM, widget). Là l'espansione di `iterate` è **reale
senza toccare la source**: le righe esistono come entità indirizzabili,
con fullpath propri e pointer registrati. Il gate D9 non va aperto: la
domanda "i nodi dell'espansione esistono?" ha semplicemente risposta
diversa sui due lati, e va bene così.

Dove vive la scelta: **un render mode**, come sempre in questo sistema
(`renderer_<mode>`). `html` emette chunk di testo e `finalize` produce la
stringa; `livehtml` emette dict e `finalize` costruisce la compiled bag.
Il walk non cambia — è già agnostico, e cosa *sia* un frammento è sempre
stata decisione del renderer di dialetto. Corollari: il render statico non
paga nulla; la granularità è per-render, non per-documento; nessun
`StaticHandler`/`ReactiveHandler`.

Sul filo passano **mutazioni di bag** (`ins`/`upd`/`del` su un path), non
operazioni DOM: Python dice *cosa è cambiato nella struttura*, il client
decide *come diventa DOM*. È così che `id` esce dal core in modo
strutturale — una mutazione indirizza un **path**, che ogni nodo ha. E per
la stessa ragione sblocca il render a oggetti di genro-sql.

**Stato: ricerca, non implementazione** — progettarla mentre si
implementa è come è nato l'apparato scartato. Documento di disegno
proprio: `temp/design_static_first_compiled_bag_2026-07-26.md`
(🔴 DA REVISIONARE), con le questioni aperte (dove vive `.compiled[mode]`,
cosa significa "proxied", `render` monolitico o in due passi, opts di
documento, contratto di forma con `bag-js`).

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

- **SUITE dissolta** nel multibuilder handler (v0.8.0), e il
  multibuilder a sua volta dissolto nell'handler singolo (v0.9.0,
  `HND.1`): un handler, un builder, un datastore piatto.
- **Reattività fine ricollocata** sulla compiled bag (`RX.5`): non si
  ripara in Python, e l'apparato v0.8.0 era il surrogato di una
  struttura mancante (`CMP.7`).
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
- **Render in due passi**: `materialize` cammina e conserva in
  `materialized[mode]`, `finalize` consegna; `render` li compone
  (`PAG.4`).
- **Minimi di cardinalità: si chiedono, non si subiscono** — ricalcolo
  fresco in `validate_source()`, mai stato memorizzato, mai implicati dal
  render (`PAG.7`).
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
