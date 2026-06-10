# Design — Reincarnazione del component

**Version**: 1.0.0
**Last Updated**: 2026-06-10
**Status**: 🟢 APPROVATO — confluito nel contratto v0.8.0 (area `CMP`)

> **Nota 2026-06-10 (implementazione)** — la parola `value` delle forme
> di chiamata (D4) è stata rinominata **`store`** (collisione con
> `node_value` e con l'attributo HTML `value`). L'ancoraggio della
> forma a record (punto aperto §4) è stato chiuso: `store` non si
> risolve a valore, è l'ancora — la macchina la stampa come `datapath`
> sul wrapper a perdere, i pointer relativi del body vi risalgono.
> Contratto `CMP.3` aggiornato.

Verbale della discussione di design del 2026-06-10. La forma contrattuale
vive in `architecture-contract.md` (area `CMP`; lo `@slot` complementare
in `PAG.6`); questo documento conserva il ragionamento, l'archeologia e i
punti aperti di dettaglio. La parte reattiva (D9) appartiene al filone RX.

---

## 1. Contesto storico (archeologia verificata)

- **Blueprint (aprile 2026)** — `archive/2026-04-blueprint`: `@component(main_tag=...)`
  con body parametrico, espansione lazy alla build, `iterate="^products"` con
  pointer relativi `^.?attr` e datapath per-item. Funzionante e testato
  (`archive/tests/test_iterate.py`, esempi `05_components`, `07_iterate`).
- **Rimozione (v0.4.0, 2026-05-16, `f2a8dfe`; decisione datata 2026-04-27)** —
  motivazione a verbale (note di revisione in `architecture-contract-v0.3.md`):
  il body Python non è trasportabile in JS → asimmetria "ricetta pulita"
  (component JS) vs "ricetta espansa" (component Python). Ripiego: lato Python
  `@struct_method`, lato JS tag custom dichiarati per nome (mai formalizzati).
- **Reintroduzione a metà (2026-06-06, `e539187`+`2433d18`+`f6751ad`)** —
  `@component` con body callable + `pyrequires`/`include_components`.
  Mai documentata; `pyrequires` morto col vecchio handler (`759343c`);
  l'espansione a render-time mai scritta. Residui nel codice attuale:
  `_decorators.py:268` (@component), `base.py:862` (include_components),
  test-sentinella `test_grammar_export.py:114`, roadmap che dice ancora
  "dropped".

**Cosa scioglie il design nuovo**: l'asimmetria che uccise il component al
v0.4 sparisce perché l'espansione non entra mai nella ricetta — è un fatto del
renderer. Con la decisione cementata "mai runtime misto", la source porta il
nodo **nominato** e ogni interprete (Python oggi, JS domani) espande per conto
suo: stesso nome, un body per runtime. "Un linguaggio, due interpreti."

## 2. Decisioni

### D1 — Il component è un elemento di grammatica nominato, con body

Dichiarato con `@component` in un mixin (es. `CommonComponents`); entra nella
grammatica come un `@element`. Chiamarlo istanzia un **nodo normale nella
source, col nome del component e i suoi attributi**: nessuna espansione a
call-time, la ricetta resta pulita, serializzabile, interpretabile dal gemello
JS. Il nome nel source È il contratto cross-runtime.

### D2 — Espansione solo a render-time, effimera

Quando il walk incontra un nodo component, la macchina crea una **new_root con
tag fisso trasparente a perdere** (costante strutturale, famiglia di
`_root_`/`SOURCE_ROOT`: mai un indirizzo, scartata al render). Il body
costruisce TUTTO dentro di essa, **radice vera inclusa**:

```python
def state_row(self, root, node_label=None):
    row = root.tr(datapath='.' + node_label)
    row.td('^.state_code')
    row.td('^.state_description')
```

La radice del blocco (tag e attributi del `tr`) è competenza dell'autore del
component, non del chiamante e non della macchina. L'espansione si rende e si
butta: la source non la vede mai.

### D3 — Albero, non foresta

Il body deve mettere **esattamente un figlio** nella new_root. Violazione =
errore esplicito (niente recupero silenzioso). Conseguenza: un'espansione = un
elemento DOM → l'identità per path resta sana.

### D4 — Tre forme di chiamata; `value` e `iterate` coesistono, ruoli distinti

1. **Singolo a parametri espliciti** —
   `pane.address_block(company='^.company', zip='^.zipcode')`: gli attributi
   della chiamata saturano la signature del body, già risolti da
   `runtime_values` (pointer ammessi e trasparenti).
2. **Singolo a record** — `pane.address_block(value='^.company_record')`:
   `value` punta a UN nodo dati; il body lavora coi pointer relativi al record.
3. **Multiplo** — `pane.div().state_row(iterate='^.states')`: un'espansione
   per figlio della Bag.

`value` **non itera mai**: la cardinalità non la decide il dato, la dichiara
l'autore con `iterate`. Resta esprimibile il component che riceve un'intera
collezione come valore unico. `iterate`/`value` sono parole della macchina:
consumate, mai passate al body né emesse.

### D5 — Il contenitore esterno è del chiamante

Per l'iterate serve un contenitore (`tbody`, `div`): è grammatica ordinaria,
responsabilità di chi chiama. Nessuna semantica speciale sul contenitore.

### D6 — Algoritmo del renderer

```
render(node):
    calcola runtime attr e value (runtime_values)
    element?    → come oggi
    component?  → trova il callable in grammatica
        con iterate (risolto a una Bag):
            per ogni nodo dell'iterabile:
                chiama il body passando SOLO node.label
                rende l'espansione e continua
        senza iterate:
            chiama il body una volta (kwargs della chiamata)
            prende il contenuto della new_root (l'unico figlio)
            riparte il render da quello
```

La risoluzione runtime avviene PRIMA del branch (così `iterate='^.states'`
arriva già risolto alla Bag vera). Il dispatch component è una terza gamba
accanto a element e subbuilder nel walk per-nodo.

### D7 — Firma del body

`def nome(self, root, node_label=None, **parametri_dichiarati)`.

- **Iterate** → il renderer passa **solo `node.label`**: il body aggancia la
  radice col datapath dell'item (`datapath='.' + node_label`) e dentro usa
  pointer relativi. Nessun parametro.
- **Singolo** → i parametri della chiamata saturano la signature. L'autore
  della chiamata conosce la signature e sa cosa passare.

### D8 — Nessuna validazione per i component

Né di posizionamento (dove il chiamante li mette è responsabilità sua), né sul
tag che il body emette. La grammatica li registra e li dispaccia, punto.
L'unico vincolo è strutturale (D3), non validativo.

### D9 — Reattività dell'iterate: subscription grossa, risoluzione fine

**I pointer interni all'espansione NON entrano mai nella pointer_map**
(sarebbero N×M voci effimere da popolare e ripulire a ogni render). In mappa
c'è solo il nodo component coi suoi pointer dichiarati (`iterate=`, `value=`,
parametri).

La granularità per-riga si ricava con l'**aritmetica dei path**: evento dati
sotto la radice dell'iterate → si sottrae il path della subscription → il
primo segmento residuo è la **label del child** (= quale riga), il resto è
cosa è cambiato dentro. Ri-chiamata del body con quella sola label, rimpiazzo
del solo blocco (indirizzo DOM = path del nodo component + label). Eventi
strutturali con la stessa aritmetica: residuo = sola label → blocco
aggiunto/rimosso; evento sulla radice → re-render completo del nodo component.

Coerente col principio già a verbale: terminazione della cascata via
pointer_map + filtro path, non registrazione capillare.

**Meccanica RX da implementare nel filone reactivity** (area RX del contratto).

### D10 — Componibilità frattale

Il body di un component (normale o iterate) può usare al suo interno altri
component (normali o iterate), ricorsivamente, senza limite. Requisito di
design, non feature aggiuntiva: deve venire gratis dalla meccanica, e va
accertato con test dedicati (matrice: normale-in-normale, iterate-in-normale,
normale-in-iterate, iterate-in-iterate, auto-ricorsione su dati ad albero).

Le tre meccaniche coinvolte:

1. **Walk**: il render del contenuto di espansione passa dallo STESSO dispatch
   del source (element/component/subbuilder) → l'annidamento è la normale
   ricorsione di D6. Da garantire: nessun percorso speciale per l'espansione.
2. **Datapath**: la composizione impila i livelli attraversando le espansioni
   (wrapper trasparenti inclusi): source → datapath del tr esterno (`.QLD`) →
   `iterate='^.cities'` relativo → tr interno (`.brisbane`) → ...
3. **Reattività (D9 ricorsivo)**: i component interni vivono solo
   nell'espansione → nemmeno i loro pointer entrano in mappa; l'unica
   subscription resta sul component più esterno (quello nel source).
   Correttezza minima garantita: l'aritmetica dei path individua il blocco
   esterno da ri-rendere; granularità più fine = stessa aritmetica applicata
   ricorsivamente, ottimizzazione non requisito.

Nota: la terminazione della ricorsione è **data-driven** — un component
auto-ricorsivo (directory, org chart) è legittimo e termina con i dati;
l'auto-referenza che non consuma dati va in loop al render. Eventuale backstop
a contatore (come per la cascata reattiva), da decidere all'implementazione.

## 3. Raccordo col datapath variabile (`roadmap/reactivity/variable-datapath.md`)

Il documento del 2026-06-06 (v0.2.0, 🔴 DA REVISIONARE) è il complemento di
questo design: **iterate = replicazione** (tutti gli elementi), **datapath
variabile = selezione** (un elemento, scelto dinamicamente, `datapath="^..."`
dereferenziato e reattivo). Master-detail = grid (iterate) + selected row +
detail (datapath variabile); frattale su entrambi i lati.

- La **registrazione alla lettura** (§11, realizzata, `45ec6a7`) era motivata
  proprio dai nodi effimeri dei component: D9 ne è il completamento (i pointer
  delle espansioni non si registrano affatto).
- I **vincoli di non-preclusione §9** trovano risposta in questo design: la
  regione-con-ancora è il nodo component stesso (che sta nel source, non
  nell'espansione); `abs_datapath` resta il punto unico di composizione (il
  body usa la grammatica normale, mai composizione a mano).
- **SUPERATA la §8.4**: la sintassi lì prevista (`div(value='^path',
  iterate='component')` — component come stringa sul contenitore) è stata
  scartata oggi a favore di `pane.div().state_row(iterate='^.states')`
  (binding sul nodo component, contenitore ordinario). Anche i riferimenti a
  `pyrequires` (§8.1) sono superati: morto col vecchio handler, da rifare
  (nota datata in variable-datapath.md).

## 4. Punti deliberatamente aperti

- **Ancoraggio datapath nella forma a record** (`value='^.company_record'`):
  nel caso iterate il body riceve la label; nel caso value il contesto per i
  pointer relativi del body va specificato (analogo meccanismo? datapath del
  nodo component?). Da chiudere all'implementazione.
- **Recupero dei resti del 6 giugno**: rifare `pyrequires` sul nuovo
  `BuilderHandler` (famiglia `<domain>requires`), rimuovere il test-sentinella
  `test_no_components_section_post_v0_4_0`, allineare
  `implementation-roadmap.md` (dice ancora "dropped: not heading toward a
  re-introduction"), verificare che `@component`/`include_components`
  superstiti combacino col design qui sopra.
- **Body JS gemello**: fuori scope qui; vincolato dal contratto semantico
  "un linguaggio, due interpreti" + golden test cross-runtime.

## 5. Riferimenti

- Storia: blueprint `archive/2026-04-blueprint` (esempi 05/07, test_iterate);
  rimozione `f2a8dfe` + note di revisione in
  `roadmap/outdated_versions/architecture-contract-v0.3.md` (righe 510-532);
  drop dalla roadmap `0baa919`; reintroduzione parziale `e539187`/`2433d18`/
  `f6751ad`; morte di pyrequires `759343c`.
- Sessione di brainstorming della rimozione v0.4:
  `71614fbd-6220-41bd-8775-c262ced8e0d4`.
- Questa sessione (Claude Code): `a47d7ab4-be22-42aa-b2e9-bb0e198e6b40`.
