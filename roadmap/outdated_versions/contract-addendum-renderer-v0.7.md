# Nota integrativa al contratto v0.7.0 — renderer XML & finalize

**Status**: 🟡 NOTA INTEGRATIVA — da consolidare in v0.8.0.
**Last Updated**: 2026-06-03.
**Riferisce**: `architecture-contract.md` v0.7.0 (sezioni rendering / finalize).

Questa nota raccoglie le modifiche al modello di rendering già **atterrate nel
codice** ma non ancora promosse a bump formale del contratto. Il bump a v0.8.0
le consoliderà insieme alla reintroduzione dei sub-builder, all'eliminazione di
`render_old` e alla parte XSD (`XsdBuilderBase` / `XsdHandler`).

## 1. `finalize` fuso (niente più dispatch `finalize_<shape>`)

- **Prima**: `r0.finalize` dispatchava via
  `getattr(self, f"finalize_{self.finalize_method}")`; tutti i renderer erano
  `finalize_method = "raw"` ed ereditavano `finalize_raw`.
- **Dopo**: `finalize(result, target, **opts)` è un metodo **unico** su
  `RendererBase`. Compone la lista (`"".join`) e consuma il target (path /
  file-like / callable / `None`→ritorna). Eliminati `finalize_method` e lo
  shim morto `_write_or_return`. I dialetti object-based sovrascrivono
  `finalize` con la propria composizione.
- Gli `**opts` del render raggiungono **sia il walk** (opzioni per-nodo, es.
  `pretty`) **sia `finalize`** (opzioni di documento). La base `finalize` li
  ignora; un dialetto che ne ha uno proprio lo dichiara nell'override.

## 2. `XmlRenderer` è un render vero, non un dump

- **Prima**: `XmlRenderer.render` override-ava il walk e delegava a
  `Bag.to_xml` → introspezione grezza, **pointer non risolti**, marker di
  framework (`node_id`, …) visibili. Era il bug "xml-raw-vs-render".
- **Dopo**: `XmlRenderer` cavalca il walk universale di `RendererBase` (come
  Html/Svg): `runtime_values` risolve i pointer e filtra i marker. Override
  solo `rendered_item` (regole XML: nessun void-tag, escape, `pretty` indenta
  per profondità) e `finalize` (per `doc_header`, opzione di documento).
- **Il raw NON è un render mode**: la vista strutturale grezza della source —
  marker e pointer non risolti inclusi — si ottiene chiamando
  `source.to_xml()` **direttamente sulla bag**. Quindi
  `render(mode="xml")` ≠ `source.to_xml()`.
- Conseguenza sul live demo: `out.xml` (vista debug raw) è prodotto da
  `source.to_xml(pretty=True)`, non più da `render(mode="xml")`.

## 3bis. Modello XSD: `XsdBuilderBase` / `XsdHandler` + codegen a due classi

- `XsdBuilderBase(BagBuilderBase)` e `XsdHandler(BuilderHandler)` (in
  `contrib/xsd/xsd_builder.py`) sono le basi dei dialetti-da-XSD: leggere,
  perché il render XML vero è nel core. `XsdBuilderBase` fissa `xml` come
  default mode; gli `@element` di dominio stanno nel figlio generato.
- La codegen (`PythonGenerator.render(model, dialect_name)`) genera **un
  modulo per schema con DUE classi**: `<Dialect>Builder(XsdBuilderBase)` +
  `<Dialect>Handler(XsdHandler)` con `builder_class` esplicito. NIENTE più
  mixin piatto su `object` accoppiato a mano. Import dal modulo base
  (`contrib.xsd.xsd_builder`), non dal package (evita ciclo). Il package
  `contrib.xsd` esporta solo `XsdBuilderBase`/`XsdHandler`; gli esempi si
  importano dal proprio modulo.
- CLI: `--dialect-name` (era `--class-name`).
- #30 risolto: un pattern XSD che Python `re` non compila (proprietà di
  blocco Unicode `\p{Is...}`) NON è emesso come `Regex` attivo (esploderebbe
  a costruzione); è **commentato** con `# NOTE: ... refine by hand`. La
  codegen produce una *base da affinare*, non un dialetto completo.
- Esempi: `examples/sitemap/` (nuovo, schema modellato sulla spec pubblica
  Sitemaps 0.9) e `examples/fatturapa/` (riposizionato: `FatturaElettronicaBuilder`/
  `FatturaElettronicaHandler` in `fattura_elettronica.py`; rimossi il vecchio
  mixin `fatturapa_elements.py` e il `builder.py` a mano).

## 3. `_node_depth` sulla base, via `fullpath`

- `_node_depth` promosso da `HtmlRenderer` a `RendererBase` (serve anche a
  `XmlRenderer` per `pretty`). Implementato leggendo `node.fullpath`:
  `fullpath.count(".") - 1` (il wrapper `main` è il segmento di testa; backref
  sempre attivo). Usato **solo** per l'indentazione `pretty`: un label con un
  punto sfaserebbe l'indentazione di un livello, mai la correttezza.

## Riferimenti

Modifiche prodotte nella sessione Claude Code locale del 2026-06-03 (id sessione
`ab92032f-f111-4bc9-9429-1f095d897a3e`), sopra il checkpoint `c0b915e`.
