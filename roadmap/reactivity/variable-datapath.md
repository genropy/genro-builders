# Datapath variabile, collection store e master-detail frattale

**Versione**: 0.2.0
**Ultimo aggiornamento**: 2026-06-06
**Status**: 🔴 DA REVISIONARE — documento di visione. La §11 (esito spike,
registrazione alla lettura) è REALIZZATA e in develop (`45ec6a7`); il resto
(datapath variabile, collection store, master-detail frattale) è ancora visione.

Documento di **design dell'evoluzione futura** del data binding di
genro-builders. Raccoglie la visione discussa: il *datapath variabile*
(indirezione reattiva del datapath), il *collection store*, il pattern
*master-detail frattale* e il ruolo dei *resolver* della Bag. NON descrive
codice esistente — descrive dove vogliamo arrivare e i vincoli che il design
attuale (component, `pyrequires`, gancio renderer) non deve precludere.

L'autorità sullo stato implementato resta `architecture-contract.md` (v0.7.0)
e `reactivity/contract.md`. Questo documento è il loro **orizzonte**.

---

## 1. Il problema: mostrare UNO, non TUTTI

Due esigenze data-driven distinte:

- **iterate** — replicare una struttura per *ogni* elemento di una collezione
  (tutti gli stati in una griglia). Replicazione.
- **master-detail** — mostrare *un solo* elemento, scelto dinamicamente
  (digito un codice, vedo quello stato). Selezione.

L'iterate si risolve con la replicazione a render-time. Il master-detail no:
serve che il **datapath stesso** del contenitore-dettaglio sia dinamico, e che
reagisca quando cambia la selezione. È il *datapath variabile*.

---

## 2. Datapath variabile = indirezione (come un puntatore in C)

Un datapath normale è un **indirizzo diretto**:

```python
div(datapath="states.QLD")     # il mio datapath È states.QLD
```

Un datapath variabile è un **pointer all'indirizzo** — `^` davanti dice "questo
non è il datapath, è *dove trovo* il datapath":

```python
div(datapath="^.current_state")  # il mio datapath è SCRITTO in current_state
```

Per ottenere il datapath reale lo si **dereferenzia**: si legge il valore a
`current_state` (es. `"QLD"`) e *quello* è il datapath effettivo
(`states.QLD`). Analogia C: `T x` (diretto) vs `T *p` (puntatore da
dereferenziare).

Ed essendo `^`, è **reattivo**: se cambia *dove punta* (`current_state` passa a
`"VIC"`), il contenitore si **ri-ancora** a `states.VIC` e tutto il suo
sotto-albero mostra VIC — senza ricostruire i nodi, solo cambiando l'ancora.

`=` vs `^`: entrambi dereferenziano in lettura, ma solo `^` sottoscrive (è
reattivo); `=` è lettura una-tantum (passiva).

---

## 3. Collection store

La sorgente del master-detail è una **collection** caricata **una volta** in
memoria: una Bag dove ogni nodo figlio è una riga (`node.label` = chiave-riga,
`node.attr`/value = colonne). Non si carica una riga alla volta: si carica la
collezione e poi **ci si sposta dentro**.

```python
# setup(): la collezione intera, una volta
for row in righe:
    self.data.set_item(f"states.{row['code']}", SourceBag(row))
```

Il "current" è semplicemente una **chiave dentro la collezione**: non esiste un
simbolo speciale `#current`. Il datapath variabile `^.current_state`
dereferenzia `current_state` → chiave → compone `states.<chiave>`. (Conferma
dal legacy: il detail si ri-sorgenta su `storepath + '.' + <label-riga>`, non
su un simbolo magico.)

---

## 4. Master-detail: grid + selected row → datapath variabile del detail

Il pattern canonico completo:

1. una **grid** visualizza la collection (è un *iterate*);
2. selezionando una **riga**, la sua chiave finisce in un dato (`current_state`);
3. il **detail** ha datapath variabile che dereferenzia quel dato → si ancora
   alla riga selezionata → mostra `^.name`, `^.capital`, ...

La selezione è il **ponte** tra le due metà: la riga cliccata scrive la propria
chiave, il datapath variabile la legge e si sposta. Master-detail in memoria,
zero reload.

Per i test/esempi la grid+click si può **simulare**: un campo dove si digita la
chiave (o una `set_item` diretta) sostituisce la selected-row. Si esercita così
la metà *detail* (il datapath variabile) isolata, senza costruire prima
grid+selezione. È esattamente `australia3` (campo + detail che segue).

---

## 5. Frattale: il detail è a sua volta un master

Il detail **non è una foglia**: può contenere una sotto-grid (un'altra
collection) con la sua selected-row che pilota un sotto-detail, e così via,
ricorsivamente, senza limite.

```
states.QLD                      (detail, datapath variabile ^.current_state)
  └─ cities                     (sotto-collection)
       └─ sotto-grid → current_city
            └─ states.QLD.cities.brisbane   (sotto-detail, ^.current_city)
                 └─ districts ...           (e così via)
```

Conseguenze di design (i vincoli forti):

- **Composizione, non assoluto**: il datapath variabile di un livello si
  risolve *relativamente al datapath già dereferenziato del livello padre*.
  `^.current_city` del sotto-detail si compone su `states.QLD` →
  `states.QLD.cities.${current_city}`. La dereferenziazione è **annidata**: per
  comporre il path di un livello devo prima dereferenziare i datapath variabili
  dei suoi antenati.
- **Reattività a cascata**: quando cambia un master in alto (`current_state`),
  tutto il sotto-albero frattale sotto quel detail deve ri-ancorarsi — incluse
  sotto-grid e sotto-detail, che ora puntano a una collection diversa (le città
  del *nuovo* stato).

La camminata che già impila i datapath degli antenati
(`_compose_relative_datapath`) è ricorsiva per natura: la dereferenziazione
`^` si innesta *dentro* quel loop, quindi la ricorsione del frattale è "gratis"
se la dereferenziazione avviene nel punto giusto.

---

## 6. Registrazione dinamica alla lettura (il modello reattivo proposto)

Oggi la `pointer_map` si popola **a priori**, in `create()`
(`register_pointer` cammina tutto l'albero una volta). Questo presuppone che
tutti i nodi esistano già — falso per nodi effimeri (component a render-time) e
per dati prodotti da resolver (esistono solo quando letti).

Modello proposto (signals-like, stile Vue 3 / MobX): **non mappare a priori.**
La mappa si auto-popola come **effetto della lettura**:

- nella risoluzione di un segmento di datapath / pointer, se il valore inizia
  con `^` → leggo **e registro** il nodo (sottoscrizione: riavvisami se cambia);
- se inizia con `=` → leggo **e basta** (passivo).

Per il datapath variabile, la registrazione `^` non avvisa *un nodo* ma **il
sotto-albero** ancorato a quel datapath (se cambia dove punto, tutto sotto si
sposta). È il `fireDataTrigger(absDatapath)` del legacy, qui esteso a cascata
sui livelli del frattale.

**Nota onesta sul legacy**: nel legacy JS la registrazione NON era alla
lettura — era **statica al build** del nodo (`registerNodeDynAttr` +
`_setDynAttributes`, solo per `^`), e la dereferenziazione del datapath
variabile viveva in `absDatapath` (`isPointerPath` →
`getAttributeFromDatasource('datapath')`). Quindi il "track alla lettura" è un
modello **nuovo**, non un ritorno al legacy. Il legacy resta riferimento per la
*dereferenziazione* e per la *cascata sul sotto-albero*, non per il *momento*
della registrazione.

### Punti che la registrazione dinamica deve risolvere

- **cleanup / re-subscription**: ri-renderizzando un nodo si rileggono i suoi
  `^` e ci si ri-registra; le registrazioni vecchie vanno azzerate prima
  (registrazione per `id(node)` → idempotente per natura, da verificare).
- **primo render**: la mappa è vuota finché non si legge → serve almeno un
  render prima della prima mutazione (dentro `live()` il render all'ingresso lo
  garantisce — da confermare).
- **purezza di `abs_datapath`**: oggi è dichiarato puro ("never reads the
  datastore"). Dereferenziare un segmento `^` lo rende impuro (legge + side
  effect). È un cambio di natura DELIBERATO e di FASE — non si fa in questo
  giro, ma il design attuale non deve precluderlo.

---

## 7. Resolver come sorgente lazy

`genro-bag` offre già resolver lazy (`BagResolver`): `OpenApiResolver`
(monta una spec OpenAPI — es. petstore — come Bag navigabile),
`DirectoryResolver` (monta un filesystem come Bag, carica solo all'accesso),
`UrlResolver`, `FileResolver`, `EnvResolver`, `UuidResolver`.

Il resolver è **dato che esiste solo quando lo leggi** → stesso istante della
registrazione dinamica e della dereferenziazione. È quindi il banco di prova
più vero del modello: con un resolver non c'è un albero pre-popolato da mappare
a priori — `register_pointer` non avrebbe nemmeno cosa mappare. Il resolver
dimostra da solo perché la mappa a-priori non basta.

Per i **test**: resolver **locale deterministico** (es. `DirectoryResolver` o
custom in-process) — lazy vero, senza rete. Per gli **esempi/demo**:
`OpenApiResolver` su petstore — realistico, ma con dipendenza di rete (non in
suite).

---

## 8. Ordine dei gradini (visione → implementazione)

1. **gancio renderer del component singolo** — espansione a render-time
   (`new_root` → invoca il corpo → sourcebag come `item`). Vedi piano operativo.
2. **datapath variabile / master-detail** (single level) — `australia3` con
   campo + detail `^.current_state`. Prima dell'iterate.
3. **datapath variabile annidato** (frattale) — almeno 2 livelli
   (state → city): prova che *compone* e che la reattività *cascata*.
4. **iterate** — `div(value='^path', iterate='component')`, scalare/Bag.
5. **grid + selezione** — la riga selezionata scrive il current (la grid vera
   sopra il master-detail).
6. **component di default `grid` / `tree`** — l'iterate senza component esplicito
   usa un component predefinito del dialetto (vista di default). Stesso
   meccanismo dell'iterate, override possibile.

---

## 9. Vincoli di non-preclusione per il design attuale

Mentre implementiamo component / `pyrequires` / gancio renderer, NON
precludere il futuro datapath variabile. Da verificare (analisi, non codice):

1. il sotto-albero di un component è una **regione delimitata** con un'ancora
   (serve per "riavvisa il mio sotto-albero")?
2. `abs_datapath` resta il **punto unico** di composizione del datapath (il
   component non compone datapath a mano bypassandolo)?
3. l'**handler** è raggiungibile dal punto di risoluzione (la registrazione
   futura della sottoscrizione richiede `pointer_map`; `new_root` nasce con
   `handler=None`)?
4. una registrazione **a regione** (sotto-albero, non singolo nodo) è
   esprimibile nella struttura di `pointer_map` (`id(node) → node`)?

---

## 10. Spike di validazione (`spike/dynamic_pointer`)

Branch dedicato per validare la **registrazione dinamica alla lettura** SENZA
introdurre i component. Piano:

1. registrazione dinamica del `^` alla lettura (`runtime_values` /
   `_compose_relative_datapath`), invece che a priori in `create()`;
2. test che la reattività esistente regga col modello dinamico (oracolo: suite
   reattiva attuale + test mirato);
3. test `australia3` con datapath **fisso** `.QLD` (già supportato — verde);
4. test con datapath **variabile** `^.current_state` (il caso nuovo), incluso
   un caso **annidato** (state → city) per provare composizione + cascata.

Sorgente dei test: collection caricata una volta + dato `current_state`
scrivibile (campo / `set_item`); resolver lazy come variante.

---

## 11. Esito dello spike (2026-06-06) — PROMOSSO, in develop

Il punto 1 del piano è stato realizzato e **promosso in develop** (commit
`45ec6a7`). I punti 3-4 (datapath variabile vero) restano evoluzione futura;
lo spike ha validato il *meccanismo di registrazione* che li abiliterà.

Cosa è entrato:

- **registrazione alla lettura**: `runtime_values` registra ogni `^` mentre lo
  legge (`handler.register_path(node, abs_path)`); `=` viene letto ma NON
  registrato. Tolta la walk a-priori `register_pointer` in `create()`.
- **`render()` registra anche i data-element**: la riga `runtime_values` è stata
  spostata PRIMA del `return None` della trasparenza data-element, così anche un
  data-element registra i suoi pointer quando il ramo viene reso.
- **invariante nuovo**: una pagina **deve fare il primo render per finire
  l'avviamento**. Finché non ha reso, `pointer_map` è vuota e non è reattiva. Il
  render avviene comunque (è l'output da mandare al client), quindi la
  registrazione non è un giro extra: è effetto di ciò che si fa già.

Asimmetria scoperta (il cuore del risultato):

- **aggiungere** alla mappa = effetto del render (il render sa cosa esiste *ora*,
  perché lo legge);
- **togliere** dalla mappa = azione **esplicita** su mutazione di source (il
  render NON sa cosa esisteva *prima*: i nodi spariti non li visita più).

Conseguenza per il refactor futuro della reattività (NON ancora fatto):
`register_pointer` lato *add* è superfluo; di quella macchina serve solo il lato
**unregister**. `_on_upd_value`/`_on_upd_attrs` si riducono al solo ramo di
de-registrazione del ramo vecchio; la ri-registrazione la fa il re-render del
ramo (quando esisterà il render parziale di regione; oggi `live()` rende tutto,
quindi la ri-registrazione avviene comunque rileggendo l'intero documento).

Prova in positivo: `create()` + `render()` + tre `set_item` su una dipendenza →
la `data_formula` ricalcola (`area == 60`). I test che mutavano senza rendere
sono stati adeguati (render prima della mutazione); l'errore di pointer relativo
senza ancora ora emerge al render, non al `create()`.

Cleanup di leggibilità entrati con lo spike (a comportamento invariato):
`SourceBagNode.pointer_type` (→ `^`/`=`/`None`), `fixed_attr_items`,
`runtime_to_evaluate`; `runtime_values` legge via `get_relative_data` con un
unico flusso attr+value.

---

## Riferimenti

- `architecture-contract.md` v0.7.0 (aree DAT, RX, autorità sull'implementato).
- `reactivity/contract.md`, `reactivity/data-elements.md`.
- Legacy GenroPy JS (`genropy/gnrjs/gnr_d11/js/`): `gnrdomsource.js`
  (`absDatapath` 688-729, `isPointerPath` 634-636,
  `getAttributeFromDatasource`/`currentFromDatasource` 573-618, trigger
  datapath 1346-1351), `genro_grid.js` (`mixin__gnrUpdateSelect` 1459-1521),
  `genro_components.js` (`_Collection` 6555+, detail re-source 1871).
- `genro-bag` resolver: `resolvers/openapi_resolver.py`,
  `resolvers/directory_resolver.py`.
