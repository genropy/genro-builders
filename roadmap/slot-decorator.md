# `@slot(node_id)` — riempimento per id alla nascita del nodo

**Version**: 0.1.0
**Last Updated**: 2026-06-01
**Status**: 🔴 DA REVISIONARE — modello concettuale, non ancora approvato né implementato

> Meccanismo generico del core genro-builders. Un metodo dell'handler si
> "abbona" a un `node_id`: quando durante la costruzione nasce un nodo con
> quell'id, il framework lo invoca passandogli quel nodo. Documento di sola
> teoria; gli agganci implementativi si fissano in fase TDD. Tutto è proposta
> finché non approvato.

---

## 1. L'idea

Oggi un handler costruisce il documento in `main(self, root)`: un unico metodo
che riceve la radice e scrive tutto. `@slot(node_id)` aggiunge un secondo modo,
**complementare**: un metodo decorato si lega a un `node_id`, e il framework lo
chiama **nell'istante in cui nasce un nodo con quell'id**, passandogli quel nodo
come radice su cui costruire.

```python
class Page(SomeHandler):
    @slot("spa_root")
    def build(self, root):       # root = il nodo con node_id="spa_root"
        root.h1("Titolo")
        root.p("contenuto")
```

Non è un sostituto di `main`: è uno strato di **riempimento per id**. Qualcuno
crea i nodi-con-id (un `main`, un guscio di base, una `@struct_method`, un altro
`@slot`); i metodi `@slot(...)` riempiono quei nodi quando compaiono.

---

## 2. Quando scatta

Lo scatto è legato alla **nascita di un nodo con `node_id` esplicito**:

- durante la costruzione, un nodo riceve un `node_id` esplicito (scritto
  dall'autore o assegnato da una `@struct_method`);
- il framework cerca tra i metodi `@slot(...)` dell'handler uno legato a
  quell'id;
- se esiste, lo invoca **subito**, passandogli il nodo appena creato.

Conseguenze di questo "scatto alla nascita":

- **L'ordine è indotto dalla costruzione, non da decidere.** Un `@slot(X)` gira
  necessariamente *dopo* chi ha creato `X`. Non serve orchestrare una sequenza:
  la dipendenza d'ordine è automatica. La regola operativa è "chiunque crei il
  nodo prima fa scattare il riempitivo".
- **Solo id espliciti.** Le label auto-generate dei nodi non sono `node_id`: un
  nodo senza id esplicito non fa mai scattare nulla. Nessun costo a vuoto sui
  nodi anonimi.
- **Composizione ricorsiva.** Un metodo `@slot("X")` può creare a sua volta nodi
  con id (`Y`, `Z`), e i rispettivi `@slot("Y")`/`@slot("Z")` scattano alla loro
  nascita. Innesto su innesto, senza orchestrazione esplicita.

---

## 3. Match esatto e letterale

`@slot("layout_center")` matcha l'id **esatto e letterale** `layout_center`.
Niente pattern, niente wildcard, niente match "per regione indipendente dal
prefisso".

Questo non è un limite, è il contratto: **l'autore conosce sempre l'id**, in uno
di due modi:

- **lo ha scritto lui** — `container(node_id="miocontainer")`, e sa (perché è
  documentato che `container` genera `<id>_top/left/right/bottom/center`) di
  poter dichiarare `@slot("miocontainer_center")`;
- **è un id fisso documentato** dalla struttura di base — es. un guscio che
  dichiara di creare `spa_root`, e l'autore si abbona con `@slot("spa_root")`.

Il legame tra chi crea i nodi-id e chi li riempie è quindi la **documentazione
dell'id**: parte del contratto dell'elemento che li crea (coerente con il
principio "la grammar è documentazione"). Un id non è mai una sorpresa.

---

## 4. Esempio: container a regioni

```python
class Layout(SomeHandler):
    @slot("spa_root")
    def build(self, root):
        root.container(node_id="main")     # crea main_top, main_left,
                                           # main_right, main_bottom, main_center
    @slot("main_center")
    def center(self, region):              # region = il nodo main_center
        region.h1("Pagamenti")

    @slot("main_top")
    def top(self, region):
        region.span("toolbar")
```

`container` è una `@struct_method` che crea cinque regioni con id derivati dal
proprio (`<id>_<regione>`). Alla nascita di `main_center` scatta `@slot(
"main_center")`; alla nascita di `main_top` scatta `@slot("main_top")`. La
`@struct_method` non sa nulla dei `@slot`: dichiara solo le sue regioni con i
loro id. L'aggancio è del core.

---

## 5. La SPA è il primo cliente (non un caso speciale)

`@slot` nasce dalla discussione su come una pagina SPA riempie il suo contenuto
(vedi genro-ws-web `roadmap/spa-application.md`), ma **non è un meccanismo SPA**:
è del core, valido per ogni handler e ogni dialetto.

La SPA lo *usa*. Un handler SPA di base monta il guscio (documento, `<head>` con
la runtime, bootstrap) e, costruendo la radice logica della pagina, le assegna
un id fisso documentato — es. `spa_root`. Quell'assegnazione fa scattare il
meccanismo generico: se l'autore ha dichiarato `@slot("spa_root")`, viene
invocato su quel nodo. Niente decoratore `@spa`, niente metodo `content`
convenuto: la SPA è solo "un guscio che crea un nodo con id `spa_root`", e
`@slot` fa il resto. `spa_root` è il primo anello della cascata; tutto ciò che
l'autore crea dentro fa scattare gli altri `@slot`.

---

## 6. Relazione con gli altri decoratori

`@slot` è una famiglia diversa da quelli esistenti:

- `@element` / `@abstract` — dichiarano **tag** della grammar (cosa si può
  scrivere nel source).
- `@subbuilder` — un tag che apre un altro dialetto da quel nodo in giù.
- `@data_element` — nodi dati trasparenti (`data`/`data_formula`/
  `data_controller`).
- `@struct_method` — un blocco riusabile di costruzione, invocabile da un nodo.
- **`@slot`** — non dichiara un tag né un blocco: lega un metodo a un `node_id` e
  lo invoca alla nascita di quel nodo. È riempimento per id, non grammatica.

`@struct_method` e `@slot` si compongono bene: una `@struct_method` crea la
struttura coi nodi-id, i `@slot` la riempiono.

---

## 7. Fuori da questo documento (fase TDD)

Decisioni implementative rinviate a quando si scrive il codice:

- punto esatto in cui agganciare l'hook nel ciclo di costruzione del nodo;
- come l'handler raccoglie i metodi `@slot` (sulla falsariga di come oggi
  raccoglie i `@struct_method`);
- come il nodo/grammatica raggiunge l'handler per il lookup, preservando il
  confine grammar/handler;
- firma del decoratore e nome del parametro;
- comportamento se un `@slot(X)` è dichiarato ma `X` non nasce mai (orfano) —
  silenzioso o segnalato.

Questi punti hanno candidati già individuati nel codice durante la discussione,
ma non si fissano qui: vanno decisi e testati in fase di implementazione.

---

## 8. Riferimenti

- genro-ws-web `roadmap/spa-application.md` — la SPA come primo cliente di
  `@slot` (`spa_root`).
- `roadmap/reactivity/data-elements.md`, `architecture-contract.md` — contesto
  del ciclo `create()`/`main` su cui `@slot` si innesta.
- Sessione Claude Code locale che ha generato questo documento:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-06-01).
