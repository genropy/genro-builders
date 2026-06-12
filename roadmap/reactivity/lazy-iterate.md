# Lazy iterate — la pigrizia sta nel dato

**Versione**: 0.3.0
**Ultimo aggiornamento**: 2026-06-12
**Status**: 🔴 DA REVISIONARE — formalizza le decisioni D1-D4 condivise il
2026-06-12, riviste in revisione lo stesso giorno: il fill spinto a
lotti dal server è SUPERATO dal modello a scroll virtuale guidato dal
client (§5); la v0.3.0 elimina anche il roundtrip di mount — query al
primo render, pagina 0 inline, conteggio baked. I punti aperti della
§7 sono risolti o decaduti.

Design del riempimento pigro delle collezioni iterate. Obiettivo: primo
paint indipendente da N, e costo server proporzionale a ciò che
l'utente GUARDA — le pagine mai scrollate non si rendono mai. Il
documento resta vivo tra una pagina e l'altra: ogni richiesta è una
transazione a sé.

L'autorità sullo stato implementato resta `architecture-contract.md`
(area `CMP`, in particolare `CMP.7`). Questo documento è il design del
prossimo passo.

---

## 1. Il problema: il primo paint paga tutte le righe

Dopo coda formule e purge indicizzato (CMP.7, 2026-06-12) il primo
render headless è LINEARE puro: 750/1500/3000 righe =
1,53/3,09/6,20 s, ~2,1 ms/riga. La costante è piena — il body riesegue
per ogni riga attraverso la macchina grammaticale (~1/3), risoluzione
pointer e composizione (~1/3) — e il documento viaggia come HTML intero
(3,7 MB a 3000 righe). Client e calcoli sono innocenti (parse 56 ms +
layout 340 ms; calcoli 0,07 s).

A 3000 righe l'utente fissa una pagina bianca per 6 secondi. Il lazy
iterate attacca QUESTO: il contenitore esce subito, le righe arrivano
a pagine, su richiesta dello scroll, mentre il documento è già vivo.

**Decisione cementata a monte**: un chunk-fill ad-hoc (spezzare il
render in chunk sulla corsia insert, senza toccare il dato) è stato
SCARTATO a favore del resolver — stessa percezione, ma il concetto è
già della bag, e in più porta lock per lotto, `read_only` a perdere,
viewport/paging gratis.

---

## 2. D1 — la pigrizia sta nel DATO, non nell'iterate

Il lazy NON è un modo del renderer: è la natura del nodo àncora della
collezione. Sul nodo sta un **resolver di genro-bag** (`BagResolver`,
genro-bag `resolver.py`) con `read_only=True`: dichiara DA DOVE
vengono le righe, e quando viene eseguito il risultato NON si deposita
in `node._value` — lo store non contiene mai la collezione.

La query gira **UNA volta, al primo render**: il walk arriva sul
component lazy e risolve l'àncora — è l'unica esecuzione del resolver
(`read_only`: niente deposito) — e la macchina dell'iterate
**parcheggia** il risultato nel dict di deposito, già diviso in pagine
(§5). Da lì in poi il resolver non si ri-esegue mai: le richieste di
pagina leggono il PARCHEGGIO. Re-render del documento = ri-query (D3).

L'**iterate resta stupido**: espande la sola pagina 0 più il
marcatore (§5); per il resto della collezione non esiste espansione —
la stessa terminazione data-driven che oggi ferma il component
auto-ricorsivo alle foglie, applicata a "tutto ciò che non è
pagina 0".

---

## 3. D2 — `lazy=True`, parametro dell'iterate, opt-in

```python
pane.invoice_row(iterate='^.rows', lazy=True)
```

Opt-in esplicito del componente: il default resta l'eager di oggi,
nessun comportamento esistente cambia. `lazy` è parola di macchinario
(consumata come `iterate`/`store`/`id`, mai un kwarg del body).

---

## 4. D3 — mutabilità = natura del resolver

La distinzione mutabile/immutabile non è un flag nostro: è il
`read_only` del resolver (semantica già in genro-bag).

- **`read_only=True` ⇒ dati a perdere.** Il valore risolto NON si
  deposita mai in `node._value` (genro-bag `resolver.py`). È il caso
  delle collezioni immutabili — un listino dal DB, un catalogo: le
  pagine attraversano il render e muoiono. Conseguenze, tutte GIUSTE per dati
  immutabili:
  - niente writeback, niente regole di riga, niente catalogo celle —
    non c'è nulla da scrivere né da ricalcolare;
  - la selezione (click su una riga) viaggia per **label nel DOM**
    (baked all'espansione, corsia FIRE), non per writeback;
  - re-render = ri-query: il refresh è rieseguire il resolver, non
    patchare lo store.
  - Coerente con genro-bag: `read_only=True` è già incompatibile con
    `reactive`/`interval` (validato alla costruzione del resolver).
- **Mutabile ⇒ di norma eager.** Una collezione editabile è di norma
  piccola (decine di righe): l'eager di oggi va bene così. Se mutabile
  e grossa, il problema non è il primo paint: è il costo totale, e la
  risposta è il grid data-widget (§8).

---

## 5. D4 (rivisto) — scroll virtuale: le pagine le chiede il client

Il fill spinto dal server (lotti in sequenza dentro la stessa
richiesta) è SUPERATO in revisione: **il padrone del tempo è il
browser**. Ogni richiesta di pagina è un messaggio a sé — la sua
sezione `live()`, il suo lock — e gli edit dell'utente si infilano tra
una pagina e l'altra senza meccanica nuova. La richiesta viaggia sulla
corsia FIRE esistente (CMP.7); il vocabolario nuovo è minimo e tutto
in discesa: gli attributi `data-lazy-*` baked sul marcatore e l'op
`page`.

1. **Primo paint** — la query gira (§2) e le righe vanno nel **dict
   di deposito sull'handler** (chiave = id del nodo richiedente,
   valore = le righe divise in **pagine da 100**); l'iterate rende
   **la pagina 0 inline** (~0,2 s) più il **marcatore**, che porta
   baked il `data-fire-pointer` (la corsia per chiedere il resto) e
   il **conteggio totale** come attributo. Il marcatore veste lo
   STESSO tag della radice dei blocchi riga (un `tr` tra i `tr`, un
   `li` tra i `li`: validità del DOM, nessun marcatore per-dialetto),
   scoperto con una sonda di solo build del body — costruire è
   struttura, niente pointer, niente render. L'HTML arriva già
   giusto: un solo viaggio, nessun roundtrip di mount.
2. **Il client fabbrica i placeholder** — disegna la pagina 0, ne
   misura l'**altezza media reale**, e fabbrica gli N−100 domnode
   vuoti con `min-height` = quella media: scrollbar onesta da subito,
   zero costo server, zero peso sul filo. Ogni placeholder porta il
   proprio indice; un IntersectionObserver li osserva.
3. **Pagina k a richiesta** — placeholder non pieno in viewport → il
   client fira `indice // 100` sul marcatore. Il sottoscrittore è
   MACCHINARIO (l'autore scrive solo `lazy=True` e il resolver
   sull'àncora): rende i 100 blocchi della pagina k dal deposito e li
   manda con l'op `page`; il client li infila nei placeholder
   k·100…k·100+99. La scrollbar si fa AFFERRARE: saltare a metà
   documento chiede la pagina 17 senza aver mai chiesto le prime 16.

**A perdere — il transito silenzioso.** Il render dei blocchi risolve
i pointer (`^.name`) leggendo lo store: la pagina vi TRANSITA, in
silenzio, con la sola API canonica —
`set_item(àncora, pagina, resolver=False, do_trigger=False)` (la bag
sgancia il resolver e non emette eventi: `bag/_core.py:375-487`,
guardia resolver esplicita e traversata che non risolve mai in
scrittura), render dei blocchi, poi
`set_item(àncora, None, resolver=<quello di prima>, do_trigger=False)`
a ripristinare. Niente cascata, niente `row_ins` spurie, il resolver
torna al suo posto. API verificata in lettura; la prova è l'esempio
`reactive/18_lazy_iterate`. Il DOM è il deposito. Coerente con
`read_only` (§4): niente regole, niente writeback; la selezione via
label baked sopravvive (la wmap trattiene i nodi d'espansione, non lo
store).

**Il parcheggio è un'interfaccia, non un dict.** Il motore vi accede
con tre verbi sull'handler — parcheggia lo snapshot, dammi la pagina
k, butta — mai col dict nudo: il backend è sostituibile. Oggi
in-process; domani Redis, per multi-worker (senza stickiness WS), per
l'eviction in memoria, per snapshot condivisi tra utenti (la chiave
diventerebbe l'hash della query) e per la sopravvivenza al restart.
Le Bag si serializzano già tipizzate; il roundtrip (~ms) è nulla
rispetto ai ~0,2 s di render della pagina.

**Altezze libere.** I placeholder usano `min-height`: la riga vera si
gonfia, il browser rifà il layout e la scrollbar si riadatta da sola.
La mappa scroll→pagina non fa aritmetica su scrollTop: l'observer
nomina il placeholder, il placeholder porta l'indice — le altezze
possono variare. Residui cosmetici: la scrollbar "respira" mentre le
pagine si riempiono; il gonfiarsi sopra la viewport è compensato dallo
scroll anchoring (Chrome/Firefox di default; Safari ne è privo).

---

## 6. Guadagni

- **Primo paint indipendente da N** (costante: la pagina 0, ~0,2 s):
  le prime 100 righe sono già nell'HTML del primo viaggio, il resto è
  un conteggio.
- **Costo proporzionale al GUARDATO**: le pagine mai scrollate non si
  rendono mai — i ~2,1 ms/riga si pagano solo per ciò che entra in
  viewport.
- **Documento vivo tra le pagine**: ogni richiesta è una transazione
  a sé — niente lock lungo, gli edit si infilano in mezzo.
- **Memoria piatta**: le righe grezze stanno nel dict di parcheggio,
  lo store non cresce; il DOM è il deposito del renderizzato.
- **Scroll virtuale vero**: scrollbar onesta e afferrabile dal primo
  giro, salto in qualunque punto del documento.

---

## 7. Punti aperti — esito della revisione 2026-06-12

1. **Taglia delle pagine** — DECISO: **100 righe**, costante di motore
   per il primo giro; la forma parametrica (`lazy=N`) è rinviata a
   quando un caso la chieda.
2. **Segnale di completamento** — DECADUTO: il conteggio totale è
   baked nel primo paint (§5), il client sa da subito quante pagine
   esistono — niente spinner da inventare.
3. **Proprietà dei label** — DECADUTO nel caso `read_only`: una
   collezione immutabile non ha `add_row` concorrente, i label sono
   del resolver e basta. Si ripresenterebbe solo per un eventuale
   lazy+mutabile, fuori dal primo giro (§8).

---

## 8. Non-obiettivi

- **Non riduce il costo per riga** (~2,1 ms di body+pointer+
  composizione): lo evita per le pagine mai guardate, ma ogni pagina
  richiesta lo paga intero. Per le grid grosse EDITABILI la risposta
  resta il **grid data-widget JS** (value = proiezione JSON dello
  store, catalogo colonne sul nodo): il server manda la proiezione,
  non l'HTML.
- **Non copre il lazy+mutabile**: collezione editabile ⇒ eager (poche
  righe) o data-widget (tante); il lazy di questo documento è per gli
  immutabili.
- **Non cambia l'eager**: default invariato, `lazy=True` è opt-in.

---

## Riferimenti

- Genealogia: il dict di parcheggio (snapshot stabile della query,
  servito a pagine) corrisponde alla **freezed selection** del legacy
  GenroPy.

- `architecture-contract.md` `CMP.7` (patch per-riga/cella, coda
  formule, purge indicizzato, corsia FIRE) — lo stato su cui questo
  design poggia.
- genro-bag `src/genro_bag/resolver.py` (`BagResolver`, `read_only`,
  `static`) e `bagnode.py:221` (`get_value(static=True)`).
- Misure: genro-ws-web `temp/baseline_scale_2026-06-12.md` (DOPO-3/4/5);
  spike `temp/spike_first_paint.py`.
- Design discusso il 2026-06-12 nella sessione Claude Code locale
  `88398e49-fa7b-4bdd-b7db-f726444506a8`; documento redatto e rivisto
  (modello a scroll virtuale) nella sessione
  `26ca5509-f801-4809-a94e-a947700d96ed`.
