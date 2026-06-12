# Contract changelog — genro-builders

Diff logico tra le versioni di `architecture-contract.md`. La versione più
recente è in testa. Il contratto in vigore descrive **lo stato d'arrivo**,
pulito e autoconsistente; questo file racconta **come ci si è arrivati**.

Le versioni superate vivono per intero in `roadmap/outdated_versions/`
(`architecture-contract-v0.3.md` … `-v0.7.0.md`, più l'addendum renderer
consolidato nel v0.8.0); ciascun header archiviato conserva il proprio
"cosa cambia" storico.

---

## v0.8.0 — emendamento del 2026-06-12 notte (coda delle formule con dedup)

Chiude il residuo (1) di CMP.7 (profilato la sera stessa: i lettori
di pagina eseguivano per EVENTO — una sola grand formula portava il
broadcast 1500 righe da 113ms a 2,9s). Design dell'utente: "ogni
formula non esegue ma si accoda in una lista evitando duplicazioni".
Dentro la sezione live le **formule si accodano** (FIFO, dedup sui
pendenti, chiave `(spec, riga)` per le regole component / nodo per i
data-element di pagina, un'unica coda), il **drain corre all'uscita
outermost PRIMA del flush dei render**; il riaccodo dopo l'esecuzione
è permesso (nuovo input nel drain — il dedup è solo sui pendenti).
FIFO = strati: in `_on_data_event` le regole component si accodano
PRIMA dei lettori di pagina, così il grand total esegue per ultimo,
sullo stato assestato — UNA volta per flush. I **controller restano
sincroni** (payload FIRE non persistente + semantica di comando:
due comandi = due esecuzioni). Guardia riga-morta anche nel drain
(la riga può morire tra accodamento e drain). Backstop
`FORMULA_REQUEUE_LIMIT=50` per chiave → errore esplicito col nome
della regola. È il ritorno al design originale della cascata (coda
FIFO, anti-loop, backstop) che l'implementazione aveva scorciato in
profondità. Esempio: `reactive/17_formula_queue`.

---

## v0.8.0 — emendamento del 2026-06-12 notte (motore regole a coordinate)

Diagnosi dell'utente a monte: "chiedersi chi mi legge è inutile" — il
modello a coordinate (àncora → riga → campo, ricorsivo per gli
annidati). Il catalogo per-riga (`expansion_logic`: 12.000 voci a
3000 righe, scansione integrale a ogni scrittura) ERA l'errore di
partenza: la regola è la stessa per ogni riga, materializzarla N
volte costringeva all'appello. Ora: **RuleSpec template
per-component** (binding residualizzati, func risolta alla
registrazione), dispatch per scomposizione del path (hit di
dizionario per prefisso, indice by-field, label = contesto di
esecuzione), binding condivisi come uniche voci assolute (uno spec ×
le righe vive), **RowContext** per i controller (il nodo trattenuto
risolverebbe contro la riga di registrazione), guardia
riga-morta = check di esistenza (sostituisce il purge eager
dell'emendamento del mattino: i template non appartengono alle
righe). Catalogo e costo per evento indipendenti da N.

Misure: broadcast headless 1500 righe 1560ms → **113ms** (14×). Live
a 3000: 36,5s → 24,9s soltanto — profilata la cipolla successiva: i
**lettori di pagina eseguono per evento, non per flush** (un grand
total `^rows` ricalcola N volte O(N) ciascuna: una formula = 113ms →
2,9s a 1500). Registrato a contratto come residuo con direzione
(differire i data-element di pagina al flush, come il micro-batch
legacy); decisione di semantica aperta.

---

## v0.8.0 — emendamento del 2026-06-12 sera (patch di cella: {id, value} anche in discesa)

Annotazione dell'utente a monte: "dovremmo immaginare di inviare solo
delle celle nel caso di ricalcolo su grid grosse". Implementato: la
classificazione scende alla FOGLIA (`cell_upd` con residuo `field`),
il walk di registrazione costruisce il catalogo per-component campo →
ordinale (valore-pointer puro = testo; attributo value = input) e il
flush spedisce op di solo valore (`text`/`attr`) lette dallo store —
niente body, niente render, niente ri-registrazione. Il filo porta
{id, value} in ENTRAMBI i versi. Le celle non coalizzano mai (il
broadcast = N patch minuscole); `CELLS_PER_ROW_LIMIT` collassa la
riga quasi-tutta-riscritta nel suo replace. Fallback al replace di
riga per le foglie fuori catalogo. Esempio 15 riallineato (edit = 3
patch-valore con oracolo; flood = N op `text`); applier di test e
client (genro.js) imparano le due op, con sovranità del controllo a
fuoco.

Scoperta di misura: il broadcast a 3000 righe NON migliora (~36s) —
profilato: il collo è il matching di `_execute_expansion_logic`
(scansione dell'intero catalogo a ogni scrittura: 2.76M `startswith`
a 1500 righe), non il render. Residuo nominato a contratto; fix
progettato: indici al posto delle scansioni (prossima fetta).

---

## v0.8.0 — emendamento del 2026-06-12 (patch per-riga delle espansioni)

Il "per ora" di CMP.7 cade: l'unità di patch delle espansioni iterate
non è più il contenitore ma la SINGOLA riga, indirizzata per identità
derivata (`base.label.1` — l'ordinale 1 è il primo elemento del
body). Classificazione per riga in `_on_data_event` (aritmetica dei
path contro l'àncora; `row_upd`/`row_ins`/`row_del`), voci di coda
`RenderEntry(kind, path, label)`, netting per (path, label) e
coalescenza per densità (`ROW_COALESCE_LIMIT`: il broadcast del
binding condiviso resta UN replace di contenitore). Il frammento esce
da `render_expansion_block` — l'`expand()` del walk promosso a
metodo condiviso (`_expansion_inputs` + `_expand_block`): stessa
strada, l'oracolo dell'esempio 15 impone la non-divergenza dal render
totale. Insert ancorato alla riga successiva nell'ordine della busta;
remove per puro calcolo con purge writeback della riga morta.

Misure (ws-web scale demos, edit di una riga): 300 righe 668ms →
41ms; 3000 righe 30.2s → 88ms (add: 32.9s → 29ms; insert mid: 92ms).
Residuo noto: il re-render COMPLETO del blocco (coalescenza, primo
paint) paga ancora la ri-registrazione quadratica per-riga (scan
della mappa per ogni riga) — fix noto: purge indicizzato per
prefisso.

Companion ws-web: gesto "inserisci sopra questa riga" (FIRE per-riga
con label + `node_position='<label'` della busta: l'identità non è
la posizione), skin gnr-grid con footer sticky e colonna pinnata.

---

## v0.8.0 — emendamento del 2026-06-11, quarta fetta (comando di pagina: la corsia FIRE del filo)

Nato dal task "+/− righe sulla fattura": un click che esegue logica
server con parametri. Decisione: nessuna route nuova — il comando
resta sul filo `{id, value}` come **quarta corsia** del mutate. Il
nodo dichiara `data-fire-pointer` (topic) ed eventualmente
`data-fire-value` (messaggio); il server fira il path (`_fired`, mai
persistito): il datastore è il bus messaggi, il sottoscrittore è un
`data_controller` canonico che esegue l'op strutturale sullo store.
Regola ibrida del payload: nodo → client → `True`; set+fire sullo
stesso nodo = errore d'autore. La writeback map accoglie anche i
click target (`data-set-pointer`/`data-fire-pointer`): il "−" per
riga ha id derivato e porta la label come messaggio baked.

### Nuovo — la cancellazione uccide le regole ancorate (CMP.7, row logic)

Scoperto dallo spike: il `pop` di una riga faceva RISORGERE la riga —
l'evento `del` matchava i binding delle regole della riga morta
("trigger sotto il path mutato"), la regola eseguiva e la sua
scrittura di destination autocreava il path. Semantica fissata: su
`del` l'handler purga (eager, prima dell'esecuzione) ogni regola il
cui ÀNCORA sta al path cancellato o sotto; il criterio è l'àncora,
non il trigger (una regola d'altra riga che legge sotto il path morto
continua a ricalcolare). Eager perché attendere la riespansione
lascerebbe regole stantie vive per il resto della cascata (un binding
condiviso — il cambio in testata — risusciterebbe la riga).

Validazione: esempio `reactive/14_page_command` (assert su id derivati
dei bottoni, del/add con regole vive sulla riga nuova, non-resurrezione
sotto binding condiviso, FIRE non persistito); demo live `invoice` in
genro-ws-web verificata in browser con uso umano concorrente.

---

## v0.8.0 — emendamento del 2026-06-11, terza fetta (row logic: le regole delle righe sono regole di mutazione)

La logica dati dichiarata nei body dei component (per-riga negli
iterate) prende vita — con una decisione di modello netta: **il
documento caricato è fidato** (la fattura arriva coi totali giusti),
quindi il render non calcola MAI; la regola scatta solo alla
mutazione. `_on_start`/`data_setter` in un'espansione → errore
esplicito. Catalogazione nel walk di registrazione
(`handler.expansion_logic`: binding risolto → nodo-regola, purge per
prefisso), esecuzione nella cascata eventi; regola universale: una
riga ricalcola sse il path mutato è tra i SUOI binding risolti —
binding di riga = una riga, binding condiviso (cambio in testata) =
tutte, annidati scopati dalla risoluzione stessa. Companion:
``SourceBagNode.data_handler`` (accesso dati dei nodi d'espansione
via builder; il gate D9 su ``handler`` non si tocca). Validato a
scala: singolo, annidato, iterato + testata→righe, iterati annidati
con testata di gruppo (esempio reactive/13_row_logic).

---

## v0.8.0 — emendamento del 2026-06-11 sera (identità derivata delle espansioni, mappa dei figli virtuali)

Nato dal design del write-back sicuro (le mutazioni dal client devono
risolversi sul server, non fidarsi del filo) e validato con una scala
di prove: component semplice, annidato, iterato su store, iterati
annidati.

### Evoluto — identità delle espansioni (Premessa, CMP.7)

Prima: "le espansioni non hanno identità" (D9), sostituzione del
contenitore come unica unità. Ora: le espansioni non ricevono MAI un
seriale proprio (il principio di D9 resta: reincarnano, nessun
contatore che gira), ma hanno **identità derivata e deterministica**:
`base.label....ordinale` — base = id del nodo component (seriale o
d'autore), label = identità delle righe negli store attraversati,
ordinale = ordine di costruzione del body. Solo render reattivo.

### Implementato — mappa dei figli virtuali, lato write-back (CMP.7)

Il candidato di CMP.7 promosso a meccanica: al render reattivo
dell'espansione gli id derivati vanno sul DOM e i nodi SCRIVIBILI
(pointer su `value`/`checked`) entrano in `builder._writeback_map`.
Il nodo trattenuto è la sede unica di tipizzazione (dtype),
validazione (`validate_*`) e destinazione (pointer → abs_datapath):
il mutate risolve l'id e legge tutto dal nodo — il filo porta solo
`{id, valore}`. Conseguenze: niente più path/dtype dal client
(l'iniezione muore alla radice), la collisione "due widget sullo
stesso path con regole diverse" si dissolve (l'id dice in quale
widget l'utente ha digitato — semantica legacy), e `id` su un
component è macchinario di catena consumato (mai un kwarg del body).
Le patch per-riga sulla stessa identità restano al filone RX.

---

## v0.8.0 — emendamento del 2026-06-11 (identità seriale, op strutturali, `@container`)

Tre cose, tutte figlie della stessa giornata di lavoro (op strutturali
della busta + decisione sulla collezione widget):

### Corretto — identità per seriale (Premessa)

"Identità per path" (l'id DOM = path del nodo generante) è sostituita
da **identità per seriale** (`target_id`: `n1`, `n2`, ... per
documento, assegnato alla prima emissione, slot sul nodo). Ragione: con
le op strutturali (`insert`/`remove`) il path NON è un'identità — un
insert non slitta i path (label-based) ma l'indirizzabilità richiede
id su OGNI elemento, e a quel punto il seriale è più corto, legato
all'oggetto e immune per costruzione a qualunque riorganizzazione. Il
trade-off Hotwire (sostituzione di contenitore) resta solo come unità
per le espansioni component. Implementato (busta
`replace`/`insert`/`remove` con ancora `before`, optimizer di netting,
oracolo esteso, esempio `reactive/11`).

### Aggiunto — `CMP.9 @container`; l'area diventa "Component e Container"

Secondo cittadino dell'area: il pezzo riusabile che **genera source
alla chiamata** (body una volta, nodi veri con `target_id`, riempibile
dal chiamante; ritorna l'handle che sceglie il body). Discriminante a
contratto: riempibile → container, autosufficiente/data-driven →
component. **`@struct_method` pensionato come nome**, parità legacy
conservata sotto `@container`. Glossario e PARTE III aggiornati.

### Corretto — `CMP.4`: pass-through dei kwargs-pointer

I kwargs della chiamata saturavano la firma del body SEMPRE risolti: il
pointer veniva consumato prima del body e l'input dell'espansione
usciva con un letterale — muto al write-back (nessun
`data-value-pointer`, nessun id, nodo emittente già morto: l'indirizzo
esisteva per un solo istante, alla risoluzione). Corretto: un kwarg il
cui crudo è un pointer REATTIVO passa al body come pointer
assolutizzato (`^volume:rest`, context-free perché l'albero-espansione
è staccato); si risolve al render del nodo finale, come un pointer a
mano, ed emette il gancio. Display identico (la risoluzione si sposta
di un gradino, D9 invariato: niente registrazione nell'espansione).
Prerequisito della collezione widget (`HtmlComponentsBase`) e della
futura mappa dei figli virtuali (write-back id-based + per-riga,
`CMP.7`).

### Corretto — `CMP.7` (per-riga) e stato del codice

`CMP.7` prometteva "id DOM = path del component + label": superato
dall'identità seriale — le espansioni non portano `target_id`
(reincarnano), lo schema d'identità per-riga è rimandato al filone RX.
Lo "stato del codice" in testa registra component e render parziale
come implementati.

---

## v0.8.0 — correzione del 2026-06-10 (stessa giornata del bump)

`BAG.4`/`PAG.5` dichiaravano l'unicità di `node_id` "per builder, il
sub-builder ha il suo namespace". Era una finzione mai esistita nel
funzionamento reale: la source del sub-builder è vuota per costruzione
(il check non vi trovava mai nulla → duplicati silenziosi nei
sottoalberi svg), mentre il lookup di pagina e i pointer simbolici
attraversano i confini di dialetto. Corretto in-place: **unicità per
documento, garantita dal root builder**; i sub-builder sono grammatica
senza identità propria, un'istanza per ospite per dialetto cached sul
builder ospite (pattern della cache dei renderer). Implementazione nel
branch `refactor/grammar-dispatch` insieme all'unificazione del
dispatch bag/nodo (wrapper unico di creazione).

---

## v0.7.0 → v0.8.0 (2026-06-10)

Bump **strutturale**: il refactor multibuilder (2026-06-08/09) ha spostato
l'engine dall'handler al builder; il v0.8.0 riallinea il contratto e mette
a verbale le decisioni della sessione di audit/pulizia e il design dei
component. Consolida anche l'addendum renderer del 2026-06-03 (archiviato
in `outdated_versions/contract-addendum-renderer-v0.7.md`).

### Riorganizzato — aree

- Nasce **`PAG`** (il builder come documento/pagina): `name` di mount sul
  builder, source sotto `SOURCE_ROOT = "_root_"`, `create()` =
  setup+main+primo calcolo, `render(mode, target, validate)` con minimi di
  cardinalità nel walk, `node_by_id` per-builder, **`@slot(node_id)`**
  promosso cittadino di prima classe (`PAG.6`, da implementare).
- **`HND` ridefinita**: l'handler è la sorgente dati multibuilder
  (`_dataroot` segmentato + `_` comune, `add_builder(*builders)` monta per
  `builder.name`, `activate()`), non un engine, non si sottoclassa. I
  **preset** (`HtmlBuilderHandler` & co.) escono dal contratto (non
  esistono nel codice; "preset sì/no" è discussione aperta).
- **`SUITE` eliminata**: dissolta nel multibuilder.
- Nascono **`APP`** (Application: live presuppone App, da formalizzare),
  **`CMP`** (component, design completo `roadmap/component-design.md`:
  nodo nominato, espansione effimera a render-time, `iterate`/`value`,
  nessuna validazione, reattività per aritmetica dei path, componibilità
  frattale) e **`RND`** (walk universale, dispatch per-nodo sul dialetto
  del nodo, confine subbuilder letterale, note HTML: booleani per
  presenza, escape `style`, niente auto-px).
- **Premessa**: i **tre scenari** (senza dati / con dati / con live)
  sostituiscono S1-S7 come asse primario; messi a verbale **"mai runtime
  misto"** (un linguaggio, due interpreti, golden test cross-runtime) e
  **identità per path** (server autoritativo, id DOM = path del nodo).

### Riconcettualizzato — pointer (`DAT.2`)

La `pointer_map` non si popola più a priori (`register_pointer` in
`create()` eliminato): **registrazione alla lettura** — `runtime_values`
registra ogni `^` mentre lo legge, `=` non registra. Invariante: il primo
render chiude l'avviamento (per questo `activate()` rende prima di armare
la subscribe dei dati). Asimmetria: add = effetto del render, remove =
azione esplicita su mutazione della source.

### Aggiunto

- **`DAT.5`** presentazione lato dati (`mask` col vocabolario legacy,
  `_wdg` che vince sulla ricetta); **`DAT.6`** template inputs consumati.
- **`BLD.4`** grammatica severa (`sub_tags` sconosciuto → `ValueError` a
  definizione classe).
- **`RX.1` riscritta**: `live()` è LA sezione critica di mutazione (RLock
  preso da `live()`, annidamento stesso-thread fuso, coda di render per
  mount con flush all'uscita esterna, decoratore `@live`); **vietato senza
  Application** (anche per i test si passa dall'App).

### Assorbito / chiuso

- Il ripiego v0.4 "tag custom JS dichiarati per nome / manifest widget" è
  assorbito da `CMP` (blocco con logica client = component con body JS;
  tag nativo opaco = `@element` in mixin).
- Pensionato `contrib/live` (ws_live è la live app).

---

## v0.7.0 + addendum renderer (2026-06-03, non ancora bumpato)

Modifiche al modello di rendering già nel codice, raccolte in
`roadmap/contract-addendum-renderer.md` (status 🟡), da consolidare nel bump
v0.8.0 insieme a sub-builder, eliminazione `render_old` e parte XSD. In sintesi:
`finalize` fuso (niente più dispatch `finalize_<shape>`); `XmlRenderer` è un
render vero (walk universale, pointer risolti, marker filtrati) e **non** un dump
`to_xml` — il raw resta `source.to_xml()` sulla bag; `_node_depth` sulla base via
`fullpath`. Le sezioni rendering/finalize di v0.7.0 sono state corrette in-place.

---

## v0.6.0 → v0.7.0 (2026-06-02)

Bump di **riconciliazione**: il contratto v0.6.0 descriveva un modello dei
data-element che il codice aveva già superato. Il v0.7.0 allinea il contratto
all'implementazione, senza cambiare codice (solo doc + docstring).

### Riconcettualizzato — data-element

- **Prima (v0.6.0)**: decoratore autonomo `@data_element` (modello
  `@subbuilder`, corpo ignorato), sui metodi `data` / `data_formula` /
  `data_controller`; kind dal **nome del metodo**; dispatch dedicato.
- **Dopo (v0.7.0, `DAT.3`)**: i tre data-element sono **`@element` ordinari**
  marcati `_meta={"data_element": True}` su `BagBuilderBase`, iniettati in ogni
  dialetto via `__init_subclass__` (dopo i tag del dialetto → override di
  omonimi). I nomi sono `data_setter` / `data_formula` / `data_controller`;
  il **kind è il `node.node_tag`**; il marker runtime è `_is_data_element`,
  settato in `element_call`; il dispatch passa per lo stesso `_command_on_node`
  degli element normali (niente più `_attach_data_element`/`_data_element_meta`).
  Il `value` del `data_setter` è un **attributo piatto** (non `node.value`),
  per non catturare il backref di una Bag dell'utente.

### Aggiunto — compute dei data-element (`DAT.4`)

Nuova decisione, assente dal v0.6.0. Esecutore unico `compute_logic(nodes)`
con due entry point (primo calcolo via `source.query` in `create()`; cascata
via `_nodes_to_compute`); `_compute_node` `match node_tag` sui tre kind;
`_bindings` via `runtime_values`; `data_logic` (property lazy, default
`[self]`) + `_resolve_logic_func` (func = `@staticmethod` per nome, sx→dx
prima-vince); `data_formula` pura, `data_controller` con `node`; macro
reattive `SET`/`GET`/`PUT`/`FIRE`. **Fetta 1** (una ondata) implementata;
**fetta 2** (cascata FIFO multi-ondata, anti-loop, ContextVar) rinviata.

### Promosso a implementato — reattività push Livello 0 (`RX.1`)

- **Prima (v0.6.0)**: `RX.1` dichiarava la reattività push "ammessa, non
  implementata".
- **Dopo (v0.7.0)**: il **Livello 0** (`handler.live(target)` context manager,
  re-render totale verso target su ogni mutazione, `RLock`, hook
  `on_live_enter`/`on_live_exit`, flag `_live_enabled`) è **implementato**.
  Restano rinviati la cascata fetta 2 (`DAT.4`) e i livelli con granularità
  SRC/DATA (`RX.4`).

### Corretto

- **`HND.4`**: `create()` non è più "setup() → main()" ma i **sei passi**
  reali (setup → main → register_pointer → primo calcolo → subscribe →
  `_live_enabled`).
- **Glossario / `BLD.1`**: rimosso il riferimento a `@data_element` dalla voce
  *Builder*; aggiunta la voce *data-element* nella forma corretta.
- **`DAT.2`**: tolto lo status interno "🔴 da progettare" (i pointer e la
  `pointer_map` sono implementati, mapkeep automatico incluso).
- **Documento pulito**: rimosso il blocco "Cosa cambia da vX" dall'intestazione
  del contratto (il delta vive qui); rimosso lo stato-codice inchiodato a
  hash/conteggio test (invecchia a ogni commit), sostituito da uno stato
  qualitativo.

### Invariato

`BLD.2`/`BLD.3`, `HND.1`/`HND.2`/`HND.3`/`HND.5`, tutta l'area `BAG`
(`BAG.4` cita `_command_on_node` — verificato corretto), `DAT.1`,
`RX.2`/`RX.4`, `SUITE`.
