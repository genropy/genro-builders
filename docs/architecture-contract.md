# Architecture contract

> **Versione vivente.** Aggiornato al 2026-05-08. Le voci storiche
> ("rinegoziazione", "decisioni del 2026-05-03") sono mantenute per
> tracciabilità delle scelte.

## Scopo

Questo documento fissa i contratti architettonici di `genro-builders`.

Il branch `develop` è l'evoluzione controllata di `main`: dal
prototipo precedente abbiamo rimosso le parti che si erano accumulate
senza coerenza strutturale, e stiamo reintroducendo le funzionalità
una per una, ognuna sotto un contratto esplicito.

Il branch `archive/2026-04-blueprint` conserva il prototipo
sperimentale (pointer, reattività, `@component`, iterate, controller,
live, ecc.). È il riferimento funzionale di **cosa** dobbiamo poter
fare; questo documento dice **come** dobbiamo poterlo fare. Il
blueprint è prezioso perché ha già esplorato quasi tutto lo spazio
delle feature; il suo limite era l'architettura.

Le 12 decisioni qui sotto sono il contratto su cui ogni nuova feature
viene reintrodotta su `develop`. Una rinegoziazione di una decisione
si fa **esplicitamente**, modificando questo file con una nota
datata.

Per consultare il blueprint:

```bash
git checkout archive/2026-04-blueprint
# oppure tieni un worktree dedicato sotto sub-projects/
```

## Glossario

- **Builder**: è la grammar pura di un dialetto (`HtmlBuilder`,
  `MarkdownBuilder`, `SvgBuilder`, ecc.). Definisce `@element`,
  `@abstract`, `@component`, lo schema di validazione, le regole di
  serializzazione del dialetto. Le responsabilità di engine vivono
  sul `BuilderHandler`.
- **BuilderHandler**: è la macchina che consuma un builder. Possiede
  `source`, `built`, mappa `node_id`, le tre fasi `create`/`build`/
  `render`, e il `render_target`. Monobuilder per istanza.
- **`HtmlBuilderHandler`, `MarkdownBuilderHandler`, ecc.**: preset
  forniti dal pacchetto, sottoclassi di `BuilderHandler` con
  `builder_class` già fissata. L'utente eredita da uno di questi.

## 1. Builder come subclass; component aggiuntivi via mixin

Ogni builder è una subclass del builder base e definisce al proprio
interno il dialetto (tag, sub_tags, parent_tags, validazione, regole
di build e di render dei nodi). Il pacchetto fornisce mixin
opzionali per aggiungere component al builder, mentre il dialetto
base resta sempre nel builder.

Il builder è **solo** dichiarazione: tag, validazione
`sub_tags`/`parent_tags`, regole di build di un nodo, regole di
render di un nodo nel proprio dialetto (decisione 6). Tutte le
responsabilità di engine — `source`, `built`, le tre fasi, mappa
`node_id`, `render_target` — vivono sul `BuilderHandler`
(decisione 9).

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

## 4. BuilderHandler autonomo monobuilder, orchestratore opzionale

Il `BuilderHandler` è autonomo e monobuilder: possiede un solo
builder e funziona da solo nei casi normali. L'utente sottoclassa
il preset specifico al dominio (es. `HtmlBuilderHandler`) e
implementa `main(self, root)`.

Se servono più handler coordinati (es. una pagina con dati condivisi
tra widget separati), si introduce un **orchestratore** esplicito
come strato sopra, separato dall'handler.

In `__init__` l'handler istanzia il builder e i due bag:

```python
class BuilderHandler:
    builder_class = None  # fissata nelle subclass

    def __init__(self):
        self.builder      = self.builder_class()
        self.source       = BuilderSourceBag(self)
        self.built        = BuilderBuiltBag(self)
        self._node_index  = {}   # node_id → path (vedi decisione 11)
```

`BuilderSourceBag` e `BuilderBuiltBag` ricevono l'handler già
istanziato come argomento. La bag conosce il proprio handler dalla
nascita (e tramite l'handler, anche il builder).

## 5. Tre fasi esplicite: create, build, render

Il ciclo di vita di un `BuilderHandler` ha tre fasi separate,
chiamate esplicitamente dall'utente:

```python
page = CustomerPage()
page.create()    # main(source) → popola self.source
page.build()     # source → self.built (espansione component, ecc.)
print(page.render())  # serializza self.built
```

L'handler **orchestra** le fasi delegando al builder le operazioni
specifiche del dialetto.

- `create()` chiama `self.main(self.source)`.
- `build()` chiama `self.builder.build(self.source, self.built)`. Il
  builder è responsabile di produrre la built a partire dalla source.
- `render()` chiama `self.builder.render(mode, render_target=...)`
  (vedi decisione 6 per i parametri). Il builder è responsabile della
  serializzazione del proprio dialetto.

Quando in un sottoalbero c'è un sub-builder (decisione 2), il
`_builder` settato sui nodi del sottoalbero (decisione 10) determina
quale builder è attivo localmente, così build/render seguono
automaticamente il builder corretto.

Ogni fase è ispezionabile (`page.source` dopo `create`, `page.built`
dopo `build`).

Esempio minimo end-to-end:

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.div('aaa')


if __name__ == '__main__':
    page = CustomerPage()
    page.create()
    page.build()
    print(page.render())
```

## 6. Render con `mode` e `render_target`

`render` esiste sia sul builder che sull'handler, con responsabilità
distinte.

**Sul builder**: ha più metodi di render, uno per modalità del
dialetto (`render_html`, `render_xml`, `render_pretty`, ecc.). Il
metodo `render(mode=None, render_target=None, **kwargs)` instrada
alla modalità richiesta; se `mode` è `None`, usa il modo primario
del dialetto (es. per `HtmlBuilder` è `render_html`).

I `**kwargs` opzionali sono parametri specifici del modo (es.
`xml=True/False` per `render_html`, `pretty=True` per
`render_pretty`). Il dispatch li filtra in base alla firma del
`render_<mode>` dispatch-ato: i kwarg che il metodo non dichiara
vengono silenziosamente ignorati. Non sono errori — un kwarg di un
modo (es. `xml`) può non avere senso per un altro (es. Markdown).

**Sull'handler**: espone una property `render_target` (con storage
interno `_render_target`, default `None`) che l'utente può
valorizzare. `handler.render(mode=None, **kwargs)` delega:

```python
class BuilderHandler:
    _render_target = None

    @property
    def render_target(self):
        return self._render_target

    @render_target.setter
    def render_target(self, value):
        self._render_target = value

    def render(self, mode=None, **kwargs):
        return self.builder.render(
            mode, render_target=self.render_target, **kwargs,
        )
```

Il **render target** decide **dove** va l'output:

- `render_target is None` → il builder accumula la stringa e la
  ritorna.
- `render_target` valorizzato (file, stream, websocket, oggetto DOM,
  …) → il builder scrive direttamente su quel target durante il walk.

L'oggetto render target concreto è scelto dall'utente nella sua
subclass: il pacchetto consente qualunque tipo, purché il builder sia
in grado di scriverci.

Esempio:

```python
class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.div('aaa')


page = CustomerPage()
page.create()
page.build()

# default: ritorna stringa
print(page.render())

# render in modalità diversa
print(page.render('xml'))

# render su file
with open('out.html', 'w') as f:
    page.render_target = f
    page.render()
```

**Responsabilità divise**:

- L'handler tiene il render target e lo passa al builder.
- Il builder conosce le modalità, sa serializzare nel proprio
  dialetto, accetta il render target e ci scrive (oppure accumula
  in stringa).

## 7. Source preserva la ricetta dell'utente: component lazy

I component dichiarati con `@component` **restano opachi nella
source**. La source è la ricetta dell'utente e deve essere
serializzabile senza perdita semantica: se la trasformo in XML deve
restare identica a quello che l'utente ha scritto in `main`. Quando
l'utente fa `page.login_form()`, nella source resta un nodo
`login_form`, non i suoi nodi interni.

L'espansione dei component è proprietà della **build**, mentre la
source resta la ricetta. La build prende la source (con i component
opachi) e produce una `built` in cui i component sono materializzati
nei loro element interni.

Conseguenze:

- L'espansione avviene solo durante la build, mai al call-time.
- La source può essere serializzata, salvata, ricaricata: resta
  sempre la ricetta originale.
- Il meccanismo concreto (proxy, resolver, walk) è dettaglio
  implementativo dello step di build, e resta interno al builder.

## 8. Builder = grammar pura; rendering e compilation in classi dedicate

Il `Builder` (es. `HtmlBuilder`, `SvgBuilder`) contiene **solo** la
grammar:

- `@element`, `@abstract`, `@component` decorati.
- Schema di tag/sub_tags/parent_tags raccolto da `__init_subclass__`.
- Validazione di scrittura nei nodi.
- Regole di **build** di un nodo (come materializzarlo dalla source
  alla built).
- Bindings al renderer e al compiler del dialetto:
  `_renderer_class = HtmlRenderer`, `_compiler_class = HtmlCompiler`
  (con default `RendererBase` / `CompilerBase` sul base).
- `_default_render_mode` che selezione la modalità di default per
  `render(mode=None)`.

**Il rendering vive in `RendererBase` e nei suoi concreti**
(`HtmlRenderer`, `SvgRenderer`, ...). Un renderer espone uno o più
metodi `render_<mode>`. Il dispatch (`renderer.render(mode, ...)`)
trova il metodo via MRO e filtra i `**kwargs` opzionali in base alla
sua signature (decisione 6).

**La compilation vive in `CompilerBase` e nei suoi concreti**
(`HtmlCompiler`, ...). Il compiler produce oggetti live (widget,
runtime, ASGI handler). Le implementazioni concrete sono
posticipate; oggi il base alza `NotImplementedError`.

Le responsabilità di engine — `source`, `built`, le tre fasi
`create`/`build`/`render` (decisione 5), gestione del `render_target`
(decisione 6), mappa `node_id` (decisione 11) — vivono sul
`BuilderHandler`, che istanzia il renderer e il compiler in lazy mode
e li espone come property (`handler.renderer`, `handler.compiler`).
`handler.render(...)` e `handler.compile(...)` sono shortcut che
delegano alle istanze.

Conseguenze:

- Il builder è testabile in isolamento (lo schema esiste
  indipendentemente da una macchina), e può essere riusato in
  contesti diversi (test, documentazione, sub-builder).
- I renderer condividono `RendererBase` per la logica trasversale
  (gestione `render_target`, escape XML, render XML di default).
- Aggiungere un nuovo modo di render a un dialetto significa
  aggiungere un metodo `render_<mode>` al suo renderer, non
  modificare il builder.

> **Nota di rinegoziazione (2026-05-12)**: la formulazione originale
> diceva "il builder contiene anche le regole di render". La
> separazione completa rendering/grammar è stata adottata per
> ridurre il volume del builder, eliminare la duplicazione fra
> dialetti, e preparare lo strato parallelo del compiler.

## 9. BuilderHandler = engine; preset per dominio

`BuilderHandler` è la macchina. Possiede `source`, `built`, mappa
`node_id` (decisione 11), le tre fasi `create`/`build`/`render`
(decisione 5), gestione del `render_target` (decisione 6).

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
- La build mantiene la stessa struttura della source, conservando i
  path di ogni nodo. Quindi la stessa mappa serve sia per accedere ai
  nodi della source sia per quelli della built.
- Lookup: `handler.node_by_id('form_main', stage='source')` o
  `stage='built'`. Internamente prende il path dalla mappa e lo applica
  al bag corrispondente.
- Errore esplicito su collisioni di `node_id`.

I sub-builder (decisione 2) condividono la **stessa mappa**
dell'handler: il sub-builder cambia il builder attivo per il
sottoalbero, mentre l'identità dell'albero resta una sola.

## 12. Layering a due livelli per bag e nodi

Le classi bag/nodo del pacchetto sono organizzate su due livelli.

**Livello 1 — base comune** (decisione 3):

- `BuilderBag` = `Bag` + `_BuilderBagMixin`
- `BuilderBagNode` = `BagNode` + `_BuilderBagNodeMixin`

Contengono i meccanismi condivisi tra source e built: slot
`_builder`/`_handler` (decisione 10), dispatch grammar via
`__getattr__`/`__dir__`, accesso ai metadati dell'albero.

**Livello 2 — specializzazione di fase**:

- `BuilderSourceBag` (sottoclasse di `BuilderBag`) e
  `BuilderSourceBagNode` (sottoclasse di `BuilderBagNode`).
- `BuilderBuiltBag` (sottoclasse di `BuilderBag`) e
  `BuilderBuiltBagNode` (sottoclasse di `BuilderBagNode`).

La distinzione è di fase: la source è popolata dall'utente (grammar
attiva), la built è prodotta dal builder durante la fase di build.

Anche quando le sottoclassi del livello 2 sono vuote (o quasi), la
loro presenza ha tre vantaggi:

- crea il punto di estensione strutturale (override mirato senza
  toccare il livello 1);
- tipizzazione discriminante: il tipo dice "source" o "built" senza
  bisogno di flag;
- predispone il pattern per eventuali mixin di specializzazione
  (`_BuilderSourceBagMixin`, `_BuilderBuiltBagMixin`, ecc.) quando
  servisse aggiungere semantica per la fase.
