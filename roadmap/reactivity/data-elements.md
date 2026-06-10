# Data elements — `data`, `data_formula`, `data_controller`

**Version**: 0.2.1
**Last Updated**: 2026-06-10
**Status**: 🔴 DA REVISIONARE — fetta 1 (singola ondata) IMPLEMENTATA;
cascata multi-ondata (fetta 2) ancora da implementare; modello non ancora
approvato

> **Nota 2026-06-10 (contratto v0.8.0)** — leggere con due aggiornamenti:
> il compute vive sul **builder** (`compute_logic`; l'handler coordina la
> cascata multi-builder via `execute_logic`), e la `pointer_map` si popola
> **alla lettura** durante il render — il passo `register_pointer` a
> priori citato più sotto non esiste più (`DAT.2` v0.8.0).

> Documento di design dei tre data-element e del loro ciclo di esecuzione.
> È il "documento separato sul dispatch" annunciato da `data-architecture.md`
> §1/§13.1. Compagno di `data-architecture.md` (modello dati statico) e di
> `reactivity/contract.md` (reattività livello 0). Tutto è proposta finché
> non approvato.

---

## 1. I tre data-element

Elementi della grammar che **non producono markup**: sono trasparenti al
renderer. Vivono nel source tree (marcati `_is_data_element`), portano
informazione, e sono **eseguiti** durante il ciclo di mutazione (§4). Nome
storico ancorato a GenroPy (`GnrDomSrc.data`): l'elemento base è `data`, non
`data_setter`.

| Element | Ruolo nel grafo | Azione |
| --- | --- | --- |
| `data` | foglia-input | scrive un valore (server→client) nella data bag; `dict`→`Bag` |
| `data_formula` | nodo intermedio | calcola da pointer-input dichiarati e scrive il risultato |
| `data_controller` | foglia-uscita | side-effect leggendo i suoi input; produttore libero: PUÒ scrivere la bag (0..N path non dichiarati) |

Si dichiarano vicino alla struttura, dentro `main()`:

```python
def main(self, root):
    body = root.body(datapath="x")
    body.data("price", 100)
    body.data("tax", 0.22)
    body.data_formula("total",
        func=lambda price, tax: price * (1 + tax),
        price="^price", tax="^tax")
    body.p("^total")
```

`data` è anche il portatore d'informazione per il futuro **browser-store**:
lo stesso nodo che oggi scrive nella bag server-side, domani (target ws-web)
sarà *trasmesso* allo store del client. Per questo resta un nodo nel source,
non un effetto imperativo che sparisce.

---

## 2. Dipendenze esplicite, niente magia

Le dipendenze di una formula/controller sono i suoi **pointer-argomento
dichiarati**, non un'analisi del codice di `func`. `total` dichiara
`price="^price"`, `tax="^tax"` → dipende dai path `price` e `tax`. Una formula
può dipendere da un'altra (`quadrupled` legge `^doubled`, prodotto da un'altra
formula): l'arco è "X dipende da Y se X legge un path che Y produce".

Conseguenza: le dipendenze sono **esigibili** e ispezionabili. Nessuna
inferenza dal corpo della funzione.

---

## 3. Niente resolver

Il modello **non usa** `BagResolver` né la sua modalità `reactive`. Un
resolver lazy ha senso solo se il valore può non essere ricalcolato (lazy +
cache). Nel modello qui (vedi §4), ad ogni mutazione le derivazioni dipendenti
sono **rieseguite subito** e il loro risultato **scritto** nella bag come dato
concreto. La formula è *codice eseguito*, non un oggetto installato.

Vantaggi: niente threading async, niente scheduling sul tick, niente
distinzione push/pull (vedi §5). Il valore derivato è un dato normale nella
bag — visibile nel data-tree, trasmissibile al browser-store come gli altri.

---

## 4. Il ciclo di mutazione

### Concorrenza: tutto sync sotto lock

Dopo `create()`, **ogni** mutazione di dato o source passa dal context manager
`live` (generalizzazione dell'attuale `live()`, RLock già presente). Chi muta
prende il lock ed esegue **sincronamente** l'intero ciclo, *indipendentemente*
dal fatto che il contesto esterno sia sync o async. Non esiste concorrenza
*dentro* la sezione: niente thread-safety da gestire, niente marshalling verso
un loop. Async/sync è solo il contorno esterno.

(Questo evolve `HND.5`: il lock diventa intrinseco al ciclo di mutazione, non
più "a carico dello sviluppatore". Da riflettere nel contratto.)

### La cascata, non un grafo topologico

Il modello **non** costruisce un grafo statico né riesegue in ordine
topologico. La propagazione è la **cascata** del client JS GenroPy (collaudata
da 20 anni): si **scrive un dato → fira le `subscribe` armate → chi dipende da
quel path scatta → propaga ai suoi dipendenti**. Le dipendenze restano i
pointer-input dichiarati (§2), ma sono consumate via le subscribe sui path, non
via un grafo precompilato. Nessun ordinamento globale da mantenere.

**`reason` = il nodo ORIGINE della cascata.** Si propaga **invariato** lungo
tutta la catena. Serve da anti-ciclo: quando la propagazione ricapita su un
data-element il cui evento ha `reason is self`, la cascata si **ferma** lì (es.
si scrive `peso`; se la catena tornasse a riscrivere `peso`, stop). Niente
fallback silenzioso: un ciclo non auto-terminante resta un errore rumoroso (D7).

### Due piani con cadenze diverse

**Piano dati — ad OGNI mutazione (dentro la sezione):**
- una mutazione cambia un path P, con `reason` = nodo origine;
- le subscribe sui dipendenti di P scattano (formule ricalcolano e scrivono,
  controller eseguono leggendo i loro input);
- la cascata prosegue sui dipendenti dei dipendenti, `reason` invariato,
  fermandosi su `reason is self`;
- al termine di ogni mutazione, data bag e source sono **coerenti**. Le
  derivazioni non "saltano" mai una mutazione.

**Piano markup — all'USCITA della sezione (una volta):**
- il render *totale* si produce una volta, sullo stato finale coerente. Non
  a ogni mutazione: durante la sezione i dati ballano, il markup si fa alla
  fine.

### Render iniziale (a `create()`) — IMPLEMENTATO

Il primo render **non** usa la cascata: `setup()` → `main()` costruiscono
source + dichiarano i data-element; poi `BuilderHandler.data_elements()` (dopo
`register_pointer`, **prima** di `subscribe` — le scritture di seed non firano
la reattività) esegue lineare: `data` scrive **sempre** il proprio valore;
`data_formula`/`data_controller` eseguono **solo** se marcati `_on_start`
(altrimenti dormienti, reagiranno alla cascata). `func` è risolta per nome sul
handler o usata come callable; i binding `^pointer` sono risolti via
`abs_datapath` e passati per nome. Da quel momento la mutazione passa solo da
`live` e innesca la cascata (da implementare).

---

## 5. Push/pull: la distinzione collassa

Storicamente formula e controller erano **push** (cascata attiva alla
mutazione), poi spostati a **pull** per problemi di threading. Nel modello qui
la distinzione **sparisce**: sotto il lock sync c'è solo "muta → riesegui i
dipendenti del path mutato → scrivi". È push nell'effetto (la cascata si
propaga subito, per-mutazione) ma senza i problemi del push concorrente
(perché tutto è sync sotto lock). Non c'è un pull lazy separato: il valore
derivato è sempre già scritto e coerente.

---

## 6. Uscita della sezione: due target

Il **piano dati** (§4) è identico per tutti i target. Cambia solo il consumo
all'uscita:

- **full re-render (core `genro-builders`, sync/batch)**: render totale, una
  volta, sullo stato finale. Una stringa di markup.
- **render parziale (`genro-ws-web`, async)**: invece del render totale, le
  mutazioni prodotte durante la sezione sono **spinte al client
  istantaneamente** come patch (stream), via WebSocket. Niente render totale
  finale; il client patcha il DOM man mano.

In entrambi i casi il core *produce* gli eventi di cambiamento; l'**adattatore
del target** decide come consumarli (accumula e rende tutto | spinge ogni
patch). È la separazione core-generico / adattatore già individuata per il
render parziale (RX.2/RX.4).

---

## 7. Ambito

Tutto **core** (`genro-builders`):
- i tre data-element nella grammar (decoratore unico `@data_element`
  sui metodi `data`/`data_formula`/`data_controller`) — **implementati**
  al primo render;
- la cascata sync su mutazione (subscribe + `reason`) — da implementare;
- il ciclo di mutazione sotto lock via `live`;
- il full re-render all'uscita.

`genro-ws-web` **riusa** la cascata e il ciclo, sostituendo solo il consumo
d'uscita (patch streaming invece di render totale). Non reimplementa il
meccanismo dati.

`data` e `data_formula` chiudono in builders (sync, deterministici).
`data_controller` (side-effect) è dichiarabile e ordinabile nel grafo già in
builders; il suo valore pieno emerge col target reattivo.

---

## 8. Decisioni da confermare / aperte

- **D1** — nome `data` (non `data_setter`): confermato dal lessico storico.
- **D2** — dipendenze dai pointer-input dichiarati, non dall'analisi della
  `func`: confermato (§2).
- **D3** — niente resolver nel modello (§3): confermato in linea teorica.
- **D4** — `live` come unico cancello di mutazione post-create: confermato.
- **D5** — derivazioni per-mutazione, render/patch a fine sezione: confermato.
- **D6** — firma dei data-element. *Confermato:*

  | element | firma |
  | --- | --- |
  | `data` | `data(path, value)` |
  | `data_formula` | `data_formula(path, func, **bindings)` |
  | `data_controller` | `data_controller(func, **bindings)` — nessun path dichiarato; `func` PUÒ scrivere la bag liberamente (0..N path) |

  - **path** (1° posizionale di `data`/`data_formula`): dove va il risultato,
    assoluto o relativo (`".total"` relativo al datapath del nodo, composto da
    `abs_datapath` come i pointer). `data_controller` non ha path **dichiarato**:
    è un produttore libero che può scrivere la bag su 0..N path scelti da
    `func` (il grafo guarda solo gli INPUT/binding, non gli output).
  - **func** (posizionale: 2° per la formula, 1° per il controller): un
    callable. **Forma canonica suggerita: il nome di un metodo dell'handler**
    (`func="compute_total"`), risolto a runtime via `getattr(self, ...)` — come
    `@struct_method` lega un nome a un metodo. La lambda inline e la funzione
    modulo restano **ammesse** (comode per formule brevi), ma non sono
    equivalenti: vedi la nota di serializzabilità sotto.
  - **bindings** (kwargs): i pointer-input, **sempre espliciti** (mai dedotti
    dai nomi-parametro — §2, "niente magia"). Passati al callable **per nome**:
    `func(price=<val di ^price>, tax=<val di ^tax>)`. Quindi i nomi dei
    binding-kwarg devono corrispondere ai nomi dei parametri del callable. Con
    un metodo `self.xxx`, `self` è già legato (metodo bound) e i binding
    riempiono gli altri parametri per nome.

  **Nota di serializzabilità (suggerimento, non vincolo).** Il *corpo* di una
  funzione non si serializza mai: né in XML (non può salvare il corpo di una
  lambda), né con pickle (la lambda è rifiutata; un metodo salva solo un
  riferimento qualificato, il cui corpo deve già esistere nel processo che
  ricarica). Conseguenza:

  - **`func` = nome di metodo dell'handler** → la pagina è **serializzabile**
    (il nome è una stringa nel source; il corpo vive nel codice della classe).
    Regge la persistenza su Redis e la ricostruzione dopo riavvio/crash del
    processo. È la forma **suggerita** per pagine durature.
  - **`func` = lambda / callable inline** → **ammessa**, ma rende la pagina
    **non-serializzabile**: non sopravvive a un riavvio del processo, non è
    ricostruibile, non adatta a scenari multi-processo con durabilità. Va bene
    per pagine effimere, demo, sviluppo, single-process.

  Idealmente, una pagina con `func` inline che si tenti di persistere produce un
  **errore rumoroso** (non un salvataggio silenziosamente incompleto). Vedi
  l'analisi di scala/durabilità in genro-ws-web `roadmap/scalability.md` §8.
- **D7 (aperta)** — gestione dei cicli nella cascata: l'anti-ciclo è
  `reason is self → stop`; un ciclo che non si auto-termina resta un errore
  rumoroso, niente fallback silenzioso.
- **D8 (aperta)** — quando la **source** cambia dentro la sezione (non solo i
  dati): i data-element nuovi vanno integrati (nuove subscribe da armare).
- **D9 (parziale)** — interazione con il contratto: il bump a **v0.6.0**
  (2026-06-01) ha registrato il decoratore unico `@data_element` e il primo render
  (glossario `BLD`, `BAG.4`, blocco stato-codice → `DAT.2`). Restano da
  riflettere quando la cascata sarà implementata: `HND.5` (lock intrinseco al
  ciclo di mutazione) e il render a fine sezione (area `RX`).

---

## 9. Riferimenti

- `data-architecture.md` — modello dati statico (storage, pointer, datapath).
- `reactivity/contract.md` — reattività livello 0 (DR1-DR9, `live()`, RLock).
- `architecture-contract.md` — aree HND/DAT/RX, scenari S1-S7.
- Lessico storico `data`: GenroPy `gnr/web/gnrwebstruct/base.py` `GnrDomSrc.data`.
- Sessione Claude Code locale che ha generato questo documento:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-06-01).
