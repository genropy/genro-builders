# Architecture contract — v0.4.0

> **In vigore dal 2026-05-15.** Questo documento è il **punto di arrivo**
> verso cui il codice deve convergere. Non è la fotografia dello stato
> attuale del codice. La revisione precedente (v0.3) è conservata in
> `roadmap/outdated_versions/architecture-contract-v0.3.md` insieme alla
> sintesi dei cambiamenti che hanno portato al superamento.

## Scopo

Questo documento fissa i contratti architettonici di `genro-builders`.

Il branch `develop` è l'evoluzione controllata di `main`: dal
prototipo precedente abbiamo rimosso le parti che si erano accumulate
senza coerenza strutturale, e stiamo reintroducendo le funzionalità
una per una, ognuna sotto un contratto esplicito.

Il branch `archive/2026-04-blueprint` conserva il prototipo
sperimentale (pointer, reattività, iterate, controller, live, ecc.).
È il riferimento funzionale di **cosa** dobbiamo poter fare; questo
documento dice **come** dobbiamo poterlo fare. Il blueprint è prezioso
perché ha già esplorato quasi tutto lo spazio delle feature; il suo
limite era l'architettura.

Le 12 decisioni qui sotto, seguite dalla sezione "Discussioni aperte",
sono il contratto su cui ogni nuova feature viene reintrodotta su
`develop`. Una rinegoziazione di una decisione si fa **esplicitamente**:
si bump-a la minor del contratto e si conserva la versione superata in
`roadmap/outdated_versions/`.

Per consultare il blueprint:

```bash
git checkout archive/2026-04-blueprint
# oppure tieni un worktree dedicato sotto sub-projects/
```

## Glossario

- **Builder**: è la grammar pura di un dialetto (`HtmlBuilder`,
  `MarkdownBuilder`, `SvgBuilder`, ecc.). Definisce `@element`,
  `@abstract`, `@subbuilder`, `@data_element`, lo schema di
  validazione, le regole di serializzazione del dialetto. Le
  responsabilità di engine vivono sul `BuilderHandler`.
- **BuilderHandler**: è la macchina che consuma un builder. Possiede
  `source`, mappa `node_id`, le due fasi `create`/`render`, e il
  dict `mode → target` dei render.
- **`HtmlBuilderHandler`, `MarkdownBuilderHandler`, ecc.**: preset
  forniti dal pacchetto, sottoclassi di `BuilderHandler` con
  `builder_class` già fissata. L'utente eredita da uno di questi.

## 1. Builder come subclass; estensioni della grammatica via mixin

Ogni builder è una subclass del builder base e definisce al proprio
interno il dialetto (tag, sub_tags, parent_tags, validazione, regole
di render dei nodi). Il pacchetto fornisce mixin opzionali per
**estendere la grammatica** del builder con tag aggiuntivi (puri W3C
nei dialetti standard, oppure tag custom dichiarati da terzi), mentre
il dialetto base resta sempre nel builder.

Il builder è **solo** dichiarazione: tag, validazione
`sub_tags`/`parent_tags`, registry dei renderer del proprio dialetto
(decisione 6). Tutte le responsabilità di engine — `source`, le due
fasi, mappa `node_id`, dict `mode → target` — vivono sul
`BuilderHandler` (decisione 9).

## 2. Sub-builder dichiarati da un decoratore dedicato `@subbuilder`

Se un builder ammette al proprio interno builder diversi (sub-builder),
deve esistere uno specifico tag nel suo dialetto che apra il
sotto-builder. Lo switch di builder a metà albero è sempre dichiarato
esplicitamente, **con un decoratore separato** da `@element`, perché
"definire un tag del proprio dialetto" e "passare il testimone a un
altro builder" sono due responsabilità distinte: il `sub_tags` del
sotto-albero non lo decide più il builder ospite, lo decide il
sub-builder stesso.

Il decoratore si chiama `@subbuilder(BuilderClass)`.

```python
class HtmlBuilder(BagBuilderBase):

    @subbuilder(SvgBuilder)
    def svg(self): ...
```

Da `<svg>` in giù il builder attivo è `SvgBuilder`. Lo switch resta
**dentro lo stesso `BuilderHandler`**: lo stesso handler, la stessa
mappa node_id, lo stesso albero. Cambia solo lo slot `_builder` dei
nodi del sottoalbero (decisione 10).

Il `parent_tags` del builder ospite resta sensato: HTML dichiara dove
`<svg>` può apparire (`body`, `div`, ecc.) — è una regola del dialetto
ospitante. Da `<svg>` in giù la validazione passa allo schema del
sub-builder.

> **Nota di rinegoziazione (2026-05-08)**: la formulazione originale
> diceva "element con `subbuilder=SvgBuilder`" (parametro su
> `@element`). Rinegoziato come decoratore separato `@subbuilder` per
> una responsabilità per decoratore e per evitare l'ambiguità sui
> `sub_tags` dell'element ospite.

## 3. BuilderBag e BuilderBagNode via mixin

`BuilderBag` e `BuilderBagNode` sono ottenuti combinando
rispettivamente `Bag` con `_BuilderBagMixin` e `BagNode` con
`_BuilderBagNodeMixin`. La logica builder-aware vive nei mixin; le
classi base di `genro-bag` restano intatte.

## 4. BuilderHandler gestisce il suo builder, orchestratore opzionale

Ogni `BuilderHandler` gestisce un proprio builder e funziona da solo
nei casi normali. L'utente sottoclassa il preset specifico al
dominio (es. `HtmlBuilderHandler`) e implementa `main(self, root)`.

Se servono più handler coordinati (es. una pagina con dati condivisi
tra widget separati), si introduce un **orchestratore** esplicito
come strato sopra, separato dall'handler.

In `__init__` l'handler istanzia il builder e la source:

```python
class BuilderHandler:
    builder_class = None  # fissata nelle subclass

    def __init__(self):
        self.builder              = self.builder_class()
        self.source               = BuilderSource(self)
        self._render_targets      = {}      # mode → target (vedi decisione 6)
        self._default_render_mode = None
        self._node_index          = {}      # node_id → path (vedi decisione 11)
```

`BuilderSource` riceve l'handler già istanziato come argomento. La
source conosce il proprio handler dalla nascita (e tramite l'handler,
anche il builder).

## 5. Due fasi esplicite: create, render

Il ciclo di vita di un `BuilderHandler` ha due fasi separate,
chiamate esplicitamente dall'utente:

```python
page = CustomerPage()
page.create()                                # main(source) → popola self.source
page.set_render_target('html', 'out.html', default=True)
page.render()                                # serializza self.source sul target default
```

L'handler **orchestra** le fasi delegando al builder le operazioni
specifiche del dialetto.

- `create()` chiama `self.main(self.source)`.
- `render(target=None, mode=None, **kwargs)` dispatcha al renderer
  corrispondente al mode (decisione 6) e gli affida la source.

Quando in un sottoalbero c'è un sub-builder (decisione 2), il
`_builder` settato sui nodi del sottoalbero (decisione 10) determina
quale builder è attivo localmente, così il render segue
automaticamente il builder corretto.

La source è ispezionabile dopo `create` (`page.source`).

Esempio minimo end-to-end:

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.div('aaa')


if __name__ == '__main__':
    page = CustomerPage()
    page.set_render_target('html', 'out.html', default=True)
    page.create()
    page.render()
```

## 6. Render con `mode` e `target`, multipli e nominati

`render` esiste sia sul builder che sull'handler, con responsabilità
distinte.

**Sul builder**: ha un **registry di renderer per-istanza**, popolato
in `__init__` chiamando `self.register_renderer(name, renderer_class)`.
Il base (`BagBuilderBase`) registra i mode condivisi (`xml`, in futuro
`json`); ogni dialetto chiama `super().__init__()` e poi aggiunge i
suoi (es. `HtmlBuilder` registra `html`, `pretty`, `bind`, ...). Una
sub-class può fare **override** chiamando di nuovo
`register_renderer` con lo stesso nome.

```python
class BagBuilderBase:
    def __init__(self):
        self._renderers = {}
        self.register_renderer('xml', XmlRenderer)

    def register_renderer(self, name, renderer_class):
        self._renderers[name] = renderer_class

class HtmlBuilder(BagBuilderBase):
    def __init__(self):
        super().__init__()
        self.register_renderer('html', HtmlRenderer)
        self.register_renderer('pretty', HtmlPrettyRenderer)
        self.register_renderer('bind', HtmlBindRenderer)
```

Lo storage è **per-istanza**: due `HtmlBuilder` diversi possono avere
registry diversi (estensione runtime, override per scenario).

I `**kwargs` opzionali su `render(mode, target, **kwargs)` sono
parametri specifici del renderer (es. `pretty=True`). Il dispatch li
filtra in base alla firma del `render_<mode>` dispatch-ato: i kwarg
che il renderer non dichiara vengono silenziosamente ignorati.

**Sull'handler**: tiene un dict `mode → target` valorizzato via
`set_render_target(mode, target, default=False)`. Più target possono
coesistere sotto mode diversi; un mode è marcato come **default** per
le chiamate `render()` senza argomenti.

```python
class BuilderHandler:
    def __init__(self):
        self._render_targets = {}     # mode → target
        self._default_render_mode = None
        # ... resto init

    def set_render_target(self, mode, target, default=False):
        self._render_targets[mode] = target
        if default:
            self._default_render_mode = mode

    def render(self, target=None, mode=None, **kwargs):
        if mode is None:
            mode = self._default_render_mode
        if target is False:
            effective_target = None
        elif target is not None:
            effective_target = target
        else:
            effective_target = self._render_targets.get(mode)
        renderer_cls = self.builder._renderers[mode]
        return renderer_cls(self).render(
            self.source, target=effective_target, **kwargs,
        )
```

Comportamento dei casi notevoli:

- `page.render()` → mode = default, target = quello registrato sotto
  il mode default.
- `page.render(mode='xml')` → mode = xml, target = quello registrato
  sotto `'xml'` (o `None` se non registrato → ritorna stringa).
- `page.render(mode='xml', target='other.xml')` → override locale del
  target solo per quella chiamata.
- `page.render(mode='xml', target=False)` → forza ritorno stringa,
  ignora il target registrato per `xml`.

L'handler espone anche **shortcut auto-generati** `render_<mode>()`
per ogni mode registrato sul builder. La chiamata
`page.render_xml('out.xml')` è equivalente a
`page.render(mode='xml', target='out.xml')`.

**Esempio**:

```python
class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.div('aaa')


page = CustomerPage()
page.set_render_target('xml', 'snapshot.xml')
page.set_render_target('bind', dom_node, default=True)
page.create()

page.render()                      # usa 'bind' → si aggancia a dom_node
page.render(mode='xml')            # usa 'xml' → scrive su snapshot.xml
page.render(mode='xml', target='other.xml')  # override locale
text = page.render(mode='xml', target=False) # forza stringa
page.render_xml('snapshot.xml')    # shortcut equivalente
```

**Responsabilità divise**:

- L'handler tiene il dict `mode → target` e dispatcha al renderer
  appropriato; gestisce il mode di default.
- Il builder mantiene il registry dei renderer disponibili per il
  dialetto (ereditari + locali + eventuali override per istanza).
- Il renderer concreto sa serializzare il proprio mode, accetta il
  target e ci scrive (oppure accumula in stringa).

## 7. Render con switch del builder al confine del sub-builder

Senza una fase intermedia, la source è la **forma unica** del
documento. Il render cammina la source nodo per nodo e serializza nel
dialetto attivo. Non c'è dispatch per tipo di element: i tipi
grammaticali (`@element`, `@abstract`, `@subbuilder`,
`@data_element`) determinano la validazione al call-time, non
un'azione diversa al render-time.

L'unica differenza che il render osserva è il **builder attivo sul
nodo** (decisione 10). Quando il walker incontra un nodo il cui
`_builder` è diverso dal builder ospite, **delega** al renderer del
sub-builder per quel sub-tree:

- nodo con `_builder` == builder corrente → serializzazione normale
  nel proprio dialetto;
- nodo con `_builder` != builder corrente (cioè un `@subbuilder`
  attivato al call-time) → il renderer ospite chiede al
  `BuilderHandler.renderer_for(sub_builder)` il renderer del
  sub-dialetto e gli affida il sub-tree.

Conseguenze:

- L'utente costruisce la source con le chiamate `root.div(...)`,
  `root.svg(...)` ecc. Lo switch di builder avviene al call-time del
  decoratore `@subbuilder` (decisione 2): il nodo del sub-tree riceve
  `_builder = sub_builder` immediatamente.
- La source resta serializzabile senza perdita: chi la trasforma in
  XML ottiene esattamente quello che l'utente ha scritto in `main`.
- I sub-builder sono autonomi nel render: ogni dialetto governa il
  proprio sub-tree.

## 8. Builder = grammar pura; rendering in renderer dedicati

Il `Builder` (es. `HtmlBuilder`, `SvgBuilder`) contiene **solo** la
grammar:

- `@element`, `@abstract`, `@subbuilder`, `@data_element` decorati.
- Schema di tag/sub_tags/parent_tags raccolto da `__init_subclass__`.
- Validazione di scrittura nei nodi.
- **Registry di renderer per-istanza** (decisione 6): popolato in
  `__init__` chiamando `self.register_renderer(name, renderer_class)`.

**Il rendering vive in `RendererBase` e nei suoi concreti**
(`XmlRenderer`, `HtmlRenderer`, `SvgRenderer`, `HtmlBindRenderer`,
...). Ogni renderer concreto serve **un singolo mode**; il dispatch
mode → renderer avviene consultando il registry del builder
(decisione 6).

I mode condivisi (`xml`, in futuro `json`) sono registrati dal base
in `BagBuilderBase.__init__`; i mode dialect-specific sono aggiunti
dalle subclass del builder. I mode "vivi" (es. `bind`, che aggancia
il documento a un oggetto DOM/widget) sono semplici renderer nel
registry, non un piano separato di "compilation".

Le responsabilità di engine — `source`, le due fasi
`create`/`render` (decisione 5), dict `mode → target` (decisione 6),
mappa `node_id` (decisione 11) — vivono sul `BuilderHandler`.
`handler.render(...)` consulta il registry del builder, istanzia il
renderer del mode richiesto e gli affida la source.

Conseguenze:

- Il builder è testabile in isolamento (lo schema esiste
  indipendentemente da una macchina), e può essere riusato in
  contesti diversi (test, documentazione, sub-builder).
- I renderer condividono `RendererBase` per la logica trasversale
  (gestione target, escape XML, ecc.).
- Aggiungere un nuovo modo di render a un dialetto significa
  registrare un renderer con un nuovo nome via `register_renderer`,
  non modificare il builder.
- Estendere un dialetto con un mode aggiuntivo (es. plugin esterno)
  significa una subclass del builder che chiama
  `register_renderer` nel proprio `__init__`.

## 9. BuilderHandler = engine; preset per dominio

`BuilderHandler` è la macchina. Possiede `source`, mappa
`node_id` (decisione 11), la fase `create` (decisione 5) seguita
da `render` (decisione 6), dict `mode → target` (decisione 6).

Il pacchetto fornisce un preset per ogni builder:

```python
class HtmlBuilderHandler(BuilderHandler):
    builder_class = HtmlBuilder

class MarkdownBuilderHandler(BuilderHandler):
    builder_class = MarkdownBuilder

class SvgBuilderHandler(BuilderHandler):
    builder_class = SvgBuilder
# ...
```

L'utente eredita dal preset:

```python
class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.div('aaa')
```

`HtmlBuilderHandler` istanzia un `HtmlBuilder` come `self.builder` in
`__init__`. L'istanziazione del builder è interna all'handler;
l'utente interagisce solo con l'handler.

## 10. Ogni nodo ha `_builder` e `_handler`

`BuilderBagNode` (decisione 3) ha due slot:

- `_handler` → il `BuilderHandler` dell'albero. Uno solo per albero,
  immutabile dopo l'attach. Serve per accedere alla mappa `node_id`
  e all'engine in generale.
- `_builder` → il builder attivo per questo nodo. Di default è quello
  principale del handler; nei sottoalberi aperti da un element con
  `subbuilder=...` (decisione 2) è il sub-builder. Settato al momento
  dell'attach, immutabile.

`BuilderBag` (decisione 3) ha gli stessi slot.

Conseguenze:

- `node.__getattr__(name)` consulta `self._builder._schema` per
  validare e dispatchare la creazione del figlio. O(1).
- Durante il walk del render, l'handler invoca sul nodo il metodo del
  builder corrispondente alla modalità richiesta (decisione 6),
  passandogli il nodo. O(1).
- Il `_builder` di ogni nodo è settato una volta all'attach; gli
  accessi a runtime sono O(1) e diretti.

Vincolo strutturale: i nodi sono immutabili nel parent dopo l'attach.
Il vincolo è necessario perché le ref siano sempre coerenti.

## 11. Mappa `node_id` sull'handler, indicizzata per path

L'handler mantiene un'unica mappa `_node_index: dict[str, str]` che
associa `node_id` → `path` (stringa).

- `node_id` è un parametro opzionale alla scrittura del nodo nella
  source.
- La mappa è univoca entro l'handler.
- Lookup: `handler.node_by_id('form_main')`. Internamente prende
  il path dalla mappa e lo applica alla source.
- Errore esplicito su collisioni di `node_id`.

I sub-builder (decisione 2) condividono la **stessa mappa**
dell'handler: il sub-builder cambia il builder attivo per il
sottoalbero, mentre l'identità dell'albero resta una sola.

## 12. Layering a due livelli per bag e nodi

Le classi bag/nodo del pacchetto sono organizzate su due livelli.

**Livello 1 — base comune** (decisione 3):

- `BuilderBag` = `Bag` + `_BuilderBagMixin`
- `BuilderBagNode` = `BagNode` + `_BuilderBagNodeMixin`

Contengono i meccanismi condivisi tra tutte le specializzazioni: slot
`_builder`/`_handler` (decisione 10), dispatch grammar via
`__getattr__`/`__dir__`, accesso ai metadati dell'albero.

**Livello 2 — specializzazioni semantiche**:

- `BuilderSource` (sottoclasse di `BuilderBag`) e
  `BuilderSourceNode` (sottoclasse di `BuilderBagNode`) — il bag
  popolato in fase `create` (decisione 5), serializzato in fase
  `render` (decisione 6).
- Specializzazioni future (es. `BuilderData` per la builder data bag)
  ricalcano lo stesso pattern.

Anche quando una sottoclasse del livello 2 è vuota (o quasi), la sua
presenza ha tre vantaggi:

- crea il punto di estensione strutturale (override mirato senza
  toccare il livello 1);
- tipizzazione discriminante: il tipo dice il ruolo della bag
  (source, data, ecc.) senza bisogno di flag;
- predispone il pattern per eventuali mixin di specializzazione
  (`_BuilderSourceMixin`, `_BuilderDataMixin`, ecc.) quando servisse
  aggiungere semantica per quel ruolo.

## Discussioni aperte

Le voci sotto sono **piste emerse** in fase di brainstorming ma non
ancora formalizzate come decisioni. Sono citate qui per dare un
orizzonte al lettore e per essere riprese nei prossimi step. Ciascuna
chiude con "da formalizzare in step successivo".

### `@struct_method` sull'handler

Pattern ergonomico per "blocchi riusabili lato Python": un metodo
decorato sull'handler diventa invocabile come fosse un tag del
builder (es. `root.miablock(...)` nel `main` della pagina). Il
dispatch via `__getattr__` del bag, non trovando il nome nello schema
del builder, cerca sull'handler e invoca il metodo con il bag come
primo argomento. Il metodo modifica direttamente la source; il
"blocco" si dissolve nei suoi figli — niente identità persistente
nel bag, niente espansione differita. Pattern già validato per anni
nel GenroPy legacy (`struct_method` su `GnrDomSrc`).

Da formalizzare in step successivo.

### Tag custom in mixin separati

I "blocchi riusabili condivisi con JS" sono **tag custom dichiarati
per nome** (Web Component nativi `<my-widget>`, oppure widget JS
proprietari). Lato Python sono opachi: solo signature, niente body.
La materializzazione visiva è responsabilità del runtime di
destinazione. Vivono in **mixin separati** dal dialetto puro
(es. `Html5Elements` resta W3C, `MyWidgetsMixin` aggiunge tag
custom). Decoratore distinto da `@element` per marcare la natura
diversa (nome candidato non scelto: `@widget`, `@custom_element`,
ecc.).

Da formalizzare in step successivo.

### `requires` sulla pagina

Analogo del `js_requires` legacy. La pagina (handler) dichiara
staticamente quali mixin di tag custom le servono, e il framework li
mescola nel builder dell'istanza. Il momento e il meccanismo
(arricchimento di `self._schema` per istanza, oppure magia nel
`__getattr__`) sono entrambi praticabili e da decidere quando si
implementa.

Da formalizzare in step successivo.

### Manifest dei widget JS

Per evitare la doppia dichiarazione (un mixin Python + un widget
JS), ogni widget JS può portare un proprio **manifest dichiarativo**
(nome tag, attributi, vincoli, doc). Python legge il manifest e
genera al volo il mixin di tag custom; JS lo legge per registrare
l'implementazione runtime. Fonte di verità condivisa, niente
duplicazione.

Da formalizzare in step successivo.

### `schema_export` / `from_grammar`

Exporter `.gnrbld.json` della grammatica di un dialetto in forma
neutra, dichiarativa, indipendente dal linguaggio. Punto di
stabilità che disaccoppia builder Python da consumer futuri (builder
JS, transpiler XSD, transpiler JSON Schema, ecc.). Dual `from_grammar`
per ricostruire un builder dinamico a partire dal file.

Da formalizzare in step successivo.

### Orchestratore / commander multi-handler

La decisione 4 prevede già che, quando servono più handler coordinati,
si introduca un **orchestratore** esplicito come strato sopra,
separato dall'handler. La forma concreta (nome candidato:
`BuilderCommander`, `BuilderOrchestrator`, o altro), il suo contratto
e la sua API restano da definire quando l'esigenza emerge:
condivisione dati fra handler, dispatch eventi, render coordinato
multi-documento, ecc.

Da formalizzare in step successivo.
