# Contract changelog — genro-builders

Diff logico tra le versioni di `architecture-contract.md`. La versione più
recente è in testa. Il contratto in vigore descrive **lo stato d'arrivo**,
pulito e autoconsistente; questo file racconta **come ci si è arrivati**.

Le versioni superate vivono per intero in `roadmap/outdated_versions/`
(`architecture-contract-v0.3.md` … `-v0.6.0.md`); ciascun header archiviato
conserva il proprio "cosa cambia" storico.

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
