# Legacy alignment — i raccordi col GenroPy classico

**Version**: 0.1.0
**Last Updated**: 2026-06-11
**Status**: 🟢 APPROVATO (2026-06-11) — traccia di lavoro.

Esplorazione del 2026-06-11 sui sorgenti legacy, a valle della collezione
widget/containers. Principio guida: **distanza cognitiva minima** — chi
viene da GenroPy deve ritrovare nomi, forme e stratificazioni; il codice
di oggi è provvisorio ma già compatibile con i derivatori (`field`/
`fieldcell`) e con l'ORM nuovo di domani.

Fonti esplorate (path locali):

- `~/Sviluppo/genropy/sourcerer_clones/genropy/genropy/gnrjs/gnr_d11/js/`
  — `genro_frm.js` (GnrValidator), `genro_tree.js`, `genro_grid.js`
- `~/Sviluppo/Genropy/genropy/gnrjs/gnr_d11/js/genro_widgets.js`
  — i wrapper dei widget (opzioni e dtype)
- `.../gnrpy/gnr/web/gnrwebstruct.py` — `field` (2124),
  `prepareFieldAttributes`, `wdgAttributesFromColumn` (2224),
  `fieldcell` (2979), `cell`, `fields`
- `.../gnrpy/gnr/core/gnrclasses.py` — il catalogo dtype (316-369)
- `~/Sviluppo/genropy_projects/genro-sourcerer/docs/`
  `db_wiring_for_genropy_asgi_services.md` — cablaggio GnrWsgiSite
- KB Sourcerer: GroupletGrid struct mode (vocabolario `cell` vigente)

---

## 1. dtype — il catalogo è UNO, e il filo c'è già

Catalogo legacy (`gnrclasses.py`):

| Codice | Python | Alias |
|---|---|---|
| `T` | str | TEXT, P, A |
| `L` | int | I, INT, LONG, INTEGER |
| `R` | float | REAL, FLOAT, F |
| `N` | Decimal | NUMERIC, DECIMAL |
| `B` | bool | BOOL, BOOLEAN |
| `D` | date | DATE |
| `H` | time | TIME, HZ |
| `DH` | datetime | DATETIME, DT, DHZ |
| `TD` | timedelta | — |
| `BAG`/`NN`/`JS`/`RPC`/`CLS` | Bag/None/list-dict/callable/type | — |

Decisioni:

- **DHZ canonico** per i datetime (uso di squadra). genro-tytx già
  normalizza così — verificato dal vivo: un datetime (anche naive) esce
  `"2026-06-11T09:30:00.000Z::DHZ"`; in lettura `::DHZ` → aware UTC,
  `::DH` → naive (compatibilità in ingresso, mai prodotto).
- **TYTX è il formato filo**: `valore::dtype`, stessi codici legacy,
  implementazione esistente (`genro_tytx`, con test cross-language).
- Nel legacy il dtype sulla scrittura lo stampa **il wrapper del widget**
  (`DateTextBox._dtype='D'`, `DatetimeTextBox._dtype='DHZ'`,
  `TimeTextBox` scrive `{dtype:'H'}` via `_doChangeInData`;
  `default_value` convertito col dtype in ingresso). Traduzione NG: il
  widget conosce il suo dtype nativo (dal `kind`) o lo riceve
  (`dtype=`), il render emette `data-dtype` sull'elemento, il client
  spedisce **valore e dtype come parametri distinti** (il suffisso
  in-band `valore::dtype` sarebbe iniettabile da un textbox: un utente
  che digita `45::L` verrebbe convertito), il server converte con
  `genro_tytx.utils.raw_decode(f"{value}::{dtype}")` SOLO quando il
  dtype è dichiarato → **dato tipato nel datastore**; suffisso ignoto →
  errore esplicito. Vuoto → `null` per ogni campo con dtype (parità
  `NumberTextBox.onSettingValueInData` / `DateTextBox.onChanged`).

Mappa dtype→kind (la stessa che `field` userà):

| dtype | kind NG |
|---|---|
| `A`, `T` | textbox |
| `B` | checkbox |
| `L`, `I` | numberbox (places=0, format `#,###`) |
| `R`, `N` | numberbox |
| `D` | datepicker |
| `H` | timepicker |
| `DH`, `DHZ` | datetimepicker (futuro; client converte locale→UTC `Z`) |
| `X`/`BAG` | tree |

## 2. Widget — vocabolario delle opzioni (da genro_widgets.js)

Quello che `field` inietta e l'autore esplicito passa a mano. Due cerchi:

**Cerchio "ora"** (nomi identici, semantica identica):

| Opzione | Dove | Note |
|---|---|---|
| `value` | tutti | pointer |
| `dtype` | tutti | esplicito o implicito dal kind |
| `format` | tutti | display |
| `lbl` | labeled_field | etichetta |
| `ghost` | textbox-like | → placeholder |
| `trim` | textbox | **default True** |
| `min`, `max`, `places` | numberbox | constraints |
| `label`, `toggle` | checkbox | label affiancata; interruttore |
| `validate_*` | tutti | trattenuti sul nodo, MAI emessi in HTML |
| vuoto→null | numerici | parità legacy |

**Cerchio "dopo"** (registrati, non implementati): `switch_*`,
`shortcuts`, `multivalue`, `displayFormattedValue`, `mask` lato widget
(da raccordare con la `mask` lato dati, DAT.5), `popup`/`noIcon`
(inutili coi picker nativi), `maxLength` dalla size, `_autoselect`.

## 3. Validazioni — il vocabolario GnrValidator

Da `genro_frm.js` (GnrValidator, 2133-2270):

- Tag: `notnull, empty, case, len, min, max, email, regex, select,
  call, remote, nodup, gridnodup, exist`.
- Modificatori uniformi: `<tag>_error` / `<tag>_warning` (messaggi,
  templated con dataTemplate), `<tag>_if` (condizionale),
  `<tag>_iswarning`.
- Semantica: catena nell'ordine dei tag; il primo **errore** ferma, i
  **warning** si accumulano; un validatore può **modificare il valore**
  (`validate_case='l'` minuscolizza — coercizione integrata) e produrre
  `datachanges`; hook `onAccept`/`onReject`.

Architettura NG (differenza dichiarata col legacy, che valida solo
client):

1. `validate_*` viaggiano come **attributi del nodo widget**, trattenuti
   (famiglia strutturale, non emessi in HTML).
2. **Il server è autoritativo**: alla mutazione, i lettori registrati
   del path (pointer_map) portano i loro `validate_*`; il server valuta
   la catena; l'esito (valore eventualmente modificato, `gnr-invalid` +
   messaggio sul campo) torna come patch.
3. Il validatore client veloce (porting del vocabolario in genro.js) è
   il raffinamento successivo; il browser dà già metà gratis
   (constraint API) per min/max/required/pattern.
4. La grafica dello stato invalido è design da fare (qui il colore può
   suggerire errore; il focus resta azzurro).

## 4. field / fieldcell — i derivatori

Stratificazione legacy (da `gnrwebstruct.py`):

```
field('col')      → risolve colonna dal modello → wdgAttributesFromColumn
                  → {tag per dtype, lbl da name_long, validate_* dalla
                     colonna, format, size→width, permessi→readOnly}
                  → value='^.col' → dispatch: getattr(self, tag)(**attrs)

fieldcell('col')  → cellFromField(colonna) → cellpars → cell(field, **pars)
```

I `validate_*` dichiarati SUL MODELLO fluiscono al widget
(`dictExtract(fldattr,'validate_')`); FK → DbSelect (+zoom); colonna con
`values` → filteringselect/combobox.

Regole NG:

- Lo strato esplicito di oggi (`labeled_field`, i widget, `cell`) È la
  forma ricevente: `field`/`fieldcell` saranno SOLO derivatori sopra.
- Il derivatore è **duck-typed sull'oggetto-colonna** (`dtype`,
  `name_long`, `attributes`, `relatedColumn()`): oggi mangia colonne
  legacy (via GnrWsgiSite), domani colonne genro-orm — i widget sotto
  non cambiano.
- `labeled_field` accetta `dtype=` e ne deriva `kind` (mappa §1).

## 5. Tree — l'albero itera la bag

API legacy (menu.py, genro_tree.js):

```python
pane.tree(storepath='gnr.appmenu.root', labelAttribute='label',
          hideValues=True, selected_file='gnr.filepath',
          openOnClick=True, autoCollapse=True)
```

- L'albero **itera la bag**: rami = nodi con valore Bag, foglie =
  scalari (`hideValues` le nasconde), label = `attr[labelAttribute]`
  con fallback sulla label del nodo. NIENTE campo `children`.
- Selezione = famiglia di write-back: `selectedPath` (fullpath),
  `selectedLabel`, `selectedItem`, **`selected_<attr>`** (scrive
  quell'attributo dell'item cliccato), `onSelectedFire`.

Proposta NG: `tree(store="^menu", label_attribute="caption",
hide_values=True, selected_path="^ui.sel", selected_<attr>=...)` —
component ricorsivo sulla bag; il click multiplo viaggia con un
attributo `data-set` (lista `[{path, value}, ...]`) che generalizza il
click binding (`data-set-pointer` resta per il caso singolo).

## 6. Grid — lo struct con cell()

Il vocabolario cognitivo della griglia genropy (identico da `gnr.Grid`
a `groupletGrid` di oggi):

```python
def struct(struct):
    r = struct.view().rows()
    r.cell('qty', name='Qty', width='5em', dtype='L', edit=True)
    r.cell('unit_price', name='Unit price', width='7em', dtype='N',
           edit=True, format='#,###.00')
    r.cell('line_total', name='Total', width='8em', dtype='N',
           formula='qty*unit_price', totalize='.total')
```

Proposta NG: `grid(store="^.rows", struct=my_struct)` — la callable
passa al body (un attributo porta qualunque valore); mini-builder
`view().rows().cell(...)` fornito da noi; pars di cell: `field, name,
width, dtype, edit, format, validate_*, formula, totalize` (formula e
totalize in fetta successiva). Edit inline = i widget della collezione
nelle celle (write-back già funzionante); il per-riga (CMP.7, mappa dei
figli virtuali) è il raffinamento che la grid metterà sotto carico
(economics: ~50B vs ~2KB già misurati).

## 7. DB legacy nel binario nuovo — GnrWsgiSite

Dal doc sourcerer (`db_wiring_for_genropy_asgi_services.md`):

- `GnrWsgiSite('istanza')` **una volta per processo** (caro: carica il
  modello intero) → `site.db` → infilato nell'oggetto radice; i tool ci
  arrivano per riferimento.
- Connessione **unica, condivisa, non thread-safe**:
  `db.closeConnection()` nel `finally` di OGNI ramo di uscita (pena
  `idle in transaction`); scritture collaterali via `deferToCommit`,
  mai `commit()` diretto; dispatch di fatto serializzato.
- Due vie sulla stessa connessione: `db.table().query()` (nominale,
  idiomatica) e cursor crudo dell'adapter (per SQL speciale).

Piano NG: la nostra Application fa identico in `on_init`; le pagine
arrivano a `self.db` via `handler.application`; **un'app legacy serve
le due GUI sulla stessa istanza** (webpage vecchie dal WSGI, pagine
nuove dall'ASGI). Con i worker thread di ws_live la non-thread-safety
va trattata esplicitamente (serializzare gli accessi db; il lock
dell'handler copre le live section, l'accesso db è un piano in più).

## 8. Dove vive il codice — builders vs genro-ws-web

Confine dichiarato (README genro-ws-web): builders = dialetto HTML +
reattività L0; genro-asgi = server; **genro-ws-web = SPA framework**
(pagine Python, client fisso, partial re-render, eventi, widget
runtime).

Decisione operativa (delegata, 2026-06-11):

- **Si resta in builders** finché il lavoro è prevalentemente
  grammatica/render/collezioni: fetta dtype, validate_* server-side,
  tree, grid. Le collezioni (components/containers) sono mixin di
  dialetto: markup puro, casa naturale builders.
- **Trigger del trasloco**: quando il lavoro diventa prevalentemente
  strato-applicazione — cablaggio `GnrWsgiSite`, `field`/`fieldcell` su
  istanza vera, auth/sessione, la shell desktop come prodotto. A quel
  punto si fa nascere genro-ws-web col seme di `contrib/ws_live`
  (app, GenroClient, target wrapper, pagine demo) e da lì in poi le
  modifiche a builders passano per **issue** sul suo repo.
- Restano in builders per sempre: dialetto, collezioni di grammatica,
  la meccanica del render parziale (busta, optimizer, target_id) — è
  il L0+ che il contratto già copre.

## 9. Ordine di lavoro

1. **dtype/TYTX write-back** (mappa dtype→kind, `dtype=` sui widget,
   `data-dtype`, `valore::dtype` sul filo, `from_tytx` al mutate,
   vuoto→null) + vocabolario cerchio "ora" (§2).
2. **`validate_*` server-side** (attributi trattenuti, catena
   GnrValidator sul server, stato `gnr-invalid` come patch).
3. **`tree`** (§5) — sblocca il menu della shell.
4. **`grid`** (§6) — mette sotto carico per-riga e op fini.
5. **`GnrWsgiSite` + `field`/`fieldcell`** su istanza legacy (§7) —
   probabile innesco del trasloco (§8).

## Riferimenti

- Contratto v0.8.0 (aree CMP/RND/RX), `roadmap/component-design.md`,
  `roadmap/application-registry.md`, `roadmap/legacy-client-architecture.md`.
- Sessione (Claude Code) del 2026-06-11.
