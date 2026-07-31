# ConfigBuilder — configurazione come grammatica distribuita

**Version**: 0.4.0 · **Last Updated**: 2026-07-31 · **Status**: 🟢 APPROVATO

> v0.4.0 (ricette parent): `ConfigHandler(source, parents=[...])` — la
> config parte da una base e la aggiorna, il meccanismo legacy
> `instanceconfig.xml`-sopra-default ricostruito su ricette ESEGUITE
> piegate con `Bag.update` (§2.7, emendamento della voce «Merge/layering»
> in §4). Poggia sul fix genro-bag `e26c7e8` (`update` trasporta
> `node_tag`/`xml_tag`).
>
> v0.3.1 (Fase 2, gate di esecuzione): l'elemento radice si chiama
> `configuration` (non `config`, che è il nome del DIALETTO) e le
> collezioni sono sempre esplicite — `applications` è il container
> omogeneo con `collection_key="code"`, `application` il membro. La
> delega app-side prende il prefisso esplicito `applications.` (§2.3);
> i path in §4 sono aggiornati di conseguenza.

Discussione del 2026-07-28, estesa il 2026-07-29 con il modello delle
preferenze (§6) e — nella stessa giornata, sessione successiva — chiusa
su tutti i punti aperti: il primitivo sub-builder `kwarg:attr` è MERGED
su main (`27e86fc`), e la porta di lettura è decisa (`ConfigHandler`
callable, §2.3–2.4). Ogni affermazione sul codice esistente è verificata
eseguendo o leggendo; non restano punti marcati **APERTO**.

---

## 1. Il problema

Le configurazioni si scrivono in YAML, e un YAML **non sa esprimere una
grammatica**: non conosce i tag ammessi, la cardinalità, i tipi, né quali
classi consumeranno i valori. Lo schema, se c'è, vive in un terzo posto e
diverge.

Il tentativo in genro-asgi (dialetto `asgiconfig`, ~1100 righe) ha
mostrato che la strada funziona, e ha isolato il concetto che vale:
**la grammatica di configurazione è distribuita nelle classi che
consumano la configurazione**. `TaskMixin` possiede sia il kwarg `tasks=`
che sbuccia, sia l'elemento `tasks()` che lo produce. Aggiungi il mixin
al runtime e il vocabolario di config cresce con esso.

Questo è ciò che un file non può fare per costruzione.

## 2. Il modello

### 2.1 Il contratto: l'attributo `grammar`, niente mixin

Una classe qualunque diventa configurabile esponendo `grammar`:

```python
class MyClassGrammar:
    @element(sub_tags="pool[0:1]")
    def connection(self, host=None, port=None): ...

class MyClass:
    grammar = MyClassGrammar
```

- **Niente classe base obbligatoria.** Il contratto è il solo attributo
  `grammar` (duck typing): il primitivo merged lo prova —
  `_resolve_subbuilder_reference` legge `grammar` sull'oggetto passato,
  qualunque ne sia la classe. Un `Configurable` da ereditare non esiste
  e non serve.
- **`grammar` è un attributo esplicito**, non una convenzione sul nome.
  Motivo: un riferimento è risolto dall'import e sbagliarlo è un errore
  immediato, mentre `MyClass` → cercare `MyClassGrammar` per nome
  richiederebbe di sapere *in quale modulo* cercare, e fallirebbe in
  silenzio a ogni rinomina. Soprattutto, l'attributo **eredita per
  MRO**: `class Car(Vehicle)` senza dichiarazioni usa `Vehicle.grammar`
  gratis, mentre la ricerca per nome dovrebbe reimplementare la risalita.
- **`<NomeClasse>Grammar` resta la convenzione di naming raccomandata**,
  applicata dalla documentazione e non dal codice.
- Il nome è `grammar`, non `config_grammar` (asgi): allineato al
  vocabolario di genro-builders, dove "grammar" è già la parola per
  questo concetto.
- Terminologia: `<Nome>Grammar`, **non** `<Nome>Elements` come in asgi —
  "Elements" descrive il contenuto, "Grammar" il ruolo.

### 2.2 L'element che porta una classe — MERGED (`27e86fc`)

Quello che in v0.2.0 era il "modello nuovo" è ora il meccanismo di core,
rilasciato su main e normato dal contratto: **BLD.2**
([architecture-contract.md:148](architecture-contract.md#L148)).
Il marker `_meta['subbuilder']` ha due forme, entrambe stringhe:

- **Nome di registro** (senza `:`): il nome canonico di un dialetto
  registrato (`"svg"`, `"html"`).
- **Riferimento di parametro** (`kwarg:attr`): la grammatica arriva dal
  call-site. `@element(_meta={"subbuilder": "app:grammar"})` su
  `application(code=, app=)` legge: *il valore che la ricetta passa come
  `app` porta in `grammar` la classe-grammatica del sottoalbero*. Una
  dichiarazione nel dialetto host, la derivazione alla riga della
  ricetta.

Nel codice: il call-site è
[_grammar.py:128-132](../src/genro_builders/builder/_grammar.py#L128-L132),
la risoluzione del riferimento è `_resolve_subbuilder_reference`
([_grammar.py:137](../src/genro_builders/builder/_grammar.py#L137)).
La classe referenziata è un **mixin di grammatica** (stile
`Html5Elements`), non un builder: `get_subbuilder`
([base.py:464](../src/genro_builders/builder/base.py#L464)) fabbrica la
classe builder `(grammar, BuilderBase)` una volta per classe-grammatica
e la memoizza in `_grammar_builders`
([base.py:109](../src/genro_builders/builder/base.py#L109)); una classe
che è GIÀ sottoclasse di `BuilderBase` è usata as-is. La
composizione/specializzazione di grammatiche è normale ereditarietà
Python (decide l'MRO).

Proprietà che il modello config usa direttamente:

- **La commutazione è immediata**, alla scrittura del recipe: da quel
  nodo in giù i figli sono validati contro la grammatica di quella
  classe, esattamente come `<svg>` dentro HTML. L'errore compare dove lo
  scrivi.
- **Kwarg assente → nessuno switch**: il nodo resta nel dialetto host e,
  da nodo marcato subbuilder, è trasparente alla containment — non fa
  polizia sui figli.
- **Errori rumorosi alla riga della ricetta**: attributo dichiarato
  mancante, attributo non-classe, classe senza elementi.
- **Propagazione del datastore**: il sub-builder riceve il DATASTORE del
  padre, a cascata sui nidificati, risincronizzato a ogni hit. Il
  sub-builder è solo grammatica: non porta dati propri.
- Il documento di grammatica esporta il riferimento verbatim, **senza
  promessa di ricostruzione** per il consumer (GRAMMAR_FORMAT §4, nota
  v1.x —
  [GRAMMAR_FORMAT.md:192](../src/genro_builders/builder/GRAMMAR_FORMAT.md#L192)).

Esempio funzionante:
`contrib/html/examples/no_data/10_subbuilder_by_reference/`.

### 2.3 `ConfigHandler` — la porta di lettura callable

**Decisione 2026-07-29** (supersede il `self.config`-come-sottoalbero di
v0.2.0): la lettura passa da UN oggetto, il **`ConfigHandler`**, che è
un **callable** — `handler(path, default=...)`.

Costruzione, tre sorgenti:

1. **un path a `config.py`** — la via canonica dell'istanza. Convenzione
   di modulo: `config.py` definisce **esattamente UNA** sottoclasse di
   `ConfigBuilder`; zero o più di una è un errore rumoroso.
2. **una classe builder** — uso programmatico e test.
3. **un'istanza builder** — idem, quando l'albero è già stato costruito.

Il handler esegue `create()` e possiede l'albero. La ricetta produce la
source; il handler è l'unica porta dalla quale il runtime la legge.

Delega lato applicazione — il pattern documentato, due righe, relazione
duale (il figlio conosce il padre):

```python
class Application:
    def config(self, path, default=None):
        return self.server.config(f"applications.{self.code}.{path}", default=default)
```

L'applicazione prefissa la collezione e il proprio `code` e rimbalza al
padre: non conosce la propria posizione assoluta nell'albero, conosce
solo il proprio nome (il prefisso `applications.` è esplicito — niente
magia nel handler). Questo SUPERSEDE i candidati `configure(node)` e
`get_config`-sul-nodo di v0.2.0. Niente `branch()` (un handler ritagliato
su un sottoalbero) in v1: la delega per prefisso basta.

### 2.4 La pila di lettura a quattro strati

`handler(path, default=...)` risolve nell'ordine:

1. **valore scritto** — ciò che la ricetta ha passato (`?attr` sulla
   source; con genro-bag `0.19.1` un `BagResolver` come valore di
   attributo si risolve qui, trasparente al chiamante).
2. **default di firma** — risolto **A LETTURA**, nel handler: dal nodo si
   risale al builder (`node._resolve_builder()`) e si legge il default
   dichiarato nella firma dell'element
   (`_get_schema_info(tag)["call_args_validations"]`, tuple
   `(base_type, validators, default)` —
   [base.py:653](../src/genro_builders/builder/base.py#L653)). Nessuna
   materializzazione al `create()`: **la source resta pura** — un dump
   mostra solo ciò che la ricetta ha scritto. Lo strato richiede che il
   **nodo esista**: un nodo mai scritto salta agli strati 3/4 (oltre un
   mount la risoluzione statica è impossibile per costruzione — la
   grammatica è un VALORE di call-site). Il dispatch è deterministico,
   mai un fallback: gli argomenti propri di un punto di passaggio
   (l'envelope del mount) appartengono alla grammatica di partenza —
   solo i figli vivono nella sub-grammatica.
3. **`default=` di chiamata** — il default del call-site; la sua
   presenza SOPPRIME lo strato d'errore.
4. **errore rumoroso** — `KeyError` che porta il path completo
   (precedente legacy: il `mandatoryMsg` di
   `getPreference(path, pkg, dflt, mandatoryMsg)`).

I tipi arrivano convertiti dalla validazione di firma: `port=8000` letto
dal handler torna `8000` intero, non `"8000"`. Per la lettura
"tutti gli attributi veri di un nodo" resta il primitivo
`dict(node.fixed_attr_items())`
([source_bag.py:190](../src/genro_builders/builder/source_bag.py#L190)),
che salta i meta-attributi strutturali e canonicalizza le forme keyword —
è la meccanica sotto il handler, non una seconda porta.

### 2.5 Niente pointer: i resolver stanno dove il valore vive

**Decisione**: le grammatiche di configurazione non usano `^pointer`.
Un valore che viene da fuori (env, file, url) è un `BagResolver` messo
direttamente nella source.

Costo del modello precedente: due dichiarazioni (il resolver nel
`setup()`, il pointer nel `main()`) e una lettura che passa da
`runtime_values`. Con il resolver in-loco la dichiarazione è **una**, nel
punto dove il valore vive, e **il consumatore non distingue** un valore
risolto da un letterale — verificato: `c['server.key']` restituisce
`'s3cr3t'` e `c['server.dsn']` restituisce `'pg://plain'`, con la stessa
sintassi.

Cade con i pointer il `resolve_pointers` di asgi. La regola sostanziale
che portava — *un valore di configurazione che risolve vuoto è un errore
rumoroso, non un `None` silenzioso* — resta valida e vive nello **strato
d'errore della pila di lettura** (§2.4, strato 4): un path senza valore,
senza default di firma e senza `default=` di chiamata solleva. CHIUSO.

#### Un resolver isolato è di prima classe

Verificato, e smentisce l'ipotesi iniziale di un "resolver degradato":

- funziona senza nodo: `EnvResolver('X')()` → il valore, con
  `parent_node = None`;
- `read_only` si deriva da sé (`True` senza cache né trigger);
- **la cache vive nel resolver, non nel nodo**: un resolver isolato con
  `cache_time=3` misurato su 9 letture a 0.5 s dà `[0.0 ×6, 3.02 ×3]` —
  il TTL funziona senza nodo.

Quindi un resolver in un attributo non perde niente di essenziale, e il
rischio "ricalcola a ogni lettura" è governato dall'autore con
`cache_time`, come per un resolver su nodo.

#### Le due modifiche che servivano — FATTE

- **genro-builders** — `runtime_values` risolve pointer **e** resolver:
  rilasciato in `c784104` (7 test in `test_resolver_values.py`).
  Generico: vale anche per `div(width=SomeResolver(...))` in HTML.
- **genro-bag** — la sintassi `?attr` risolve un resolver trovato come
  valore di attributo: rilasciato in genro-bag `0.19.1` (su PyPI; il
  minimo va dichiarato in `pyproject.toml` quando `contrib/config` lo
  usa).

### 2.6 Niente Projection

Il taglio per-ruolo di asgi (`Projection`, 261 righe) **non entra** nel
modello. Era l'alternativa di quel repo al layering; qui non serve.

### 2.7 Ricette parent — la config parte da una base (v0.4.0)

Il meccanismo legacy di `GnrApp.load_instance_config` (gnrapp.py:936-961:
`default.xml` → template → `instanceconfig.xml`, catena di `Bag.update`,
l'istanza per ultima vince) ricostruito sul modello attuale:

```python
config = ConfigHandler(InstanceConfig, parents=[DefaultsConfig])
```

- **I parent sono RICETTE nelle stesse tre forme della source** (path a
  `config.py`, classe, istanza builder). Ogni strato viene ESEGUITO
  (`create()`, regola exactly-one-root per ricetta), poi le source si
  piegano con `Bag.update` in ordine di dichiarazione: primo parent più
  in basso, la ricetta principale applicata per ultima. Gli attributi si
  fondono per nome (riscrivi ciò che nomini, il resto si eredita), le
  collezioni esplicite si fondono per chiave.
- **Mai documenti materializzati**: l'XML emesso non fa round-trip
  dell'identità grammaticale (`node_tag`, `_meta`, label di collezione —
  `shop` tornerebbe `application_1`). Un albero eseguito porta tutto, e
  il risultato fuso continua a rendere e a risolvere i default di firma
  su ogni nodo (richiede genro-bag con `update` che trasporta
  `node_tag`/`xml_tag` — fix `e26c7e8`).
- **Ereditare, mai cancellare**: un element senza figli in uno strato
  alto ha valore `None`; il fold usa `ignore_none=True`, così una
  sezione vuota eredita il sottoalbero inferiore invece di azzerarlo.
- Il datastore (`builder.data`) NON si fonde: la configurazione è
  attributi statici. La convenzione di path dei default
  (`.genro_asgi/defaults/config.py`) vive nel repo applicativo, che
  passa `parents=[...]`.

Esempio: `contrib/config/examples/02_parent_config/`.

## 3. Cosa NON si riusa da genro-asgi

Il tentativo asgi era **piatto** (verificato: zero `subbuilder` in tutto
`config/`): le grammatiche si componevano per ereditarietà Python in
**una** grammatica, quindi aggiungere una classe configurabile
richiedeva di modificare la grammatica primaria. Il modello ad albero non
ne ha bisogno: la classe arriva come valore di un parametro.

- **`element_kwargs` non si estrae.** Valida i figli contro
  `owner_class.config_grammar` e **vieta i nipoti** (un solo livello):
  scritto per il modello piatto, dove l'annidamento non esiste. Qui i
  nipoti sono la norma. Inoltre traduce il nodo in kwargs del
  costruttore, mentre qui la classe **legge** dal handler.
- **`resolve_pointers`** cade con i pointer (§2.5).
- **`declared_elements`** (MRO scan dei marcatori `_decorator`) è l'unico
  pezzo riusabile così com'è, se serve introspezione.
- Tutto `elements.py`, i ruoli, gli `_apply_*` sono specifici di ASGI.

## 4. Punti aperti — tutti CHIUSI

- **I figli della radice non hanno label stabile — CHIUSO (via *a*).**
  `server_0` invece di `server`, perché il padre è il wrapper
  strutturale che non dichiara cardinalità: la regola singleton di
  `0.21.1` non ha un `max` da leggere. Per una config navigabile per
  path è un requisito: ogni path deve essere scrivibile a mano.
  Decisione ratificata in sessione `e01ae0d2` ("niente eccezioni
  speciali per la radice — il dialetto corretto ha un elemento
  documento", come `html`, `stylesheet`, `FatturaElettronica`), e
  RAFFINATA al gate della Fase 2 (v0.3.1): l'elemento radice si chiama
  **`configuration`** — `config` è il nome del DIALETTO, non un
  elemento — e le collezioni sono sempre esplicite: `configuration`
  dichiara le sezioni con le cardinalità
  (`server[0:1],applications[0:1]`), `applications` è il container
  omogeneo con `collection_key="code"`, `application` il membro che
  monta la grammatica → path stabili e scrivibili a mano
  (`configuration.server`, `configuration.applications.shop`).
  Realizzato nella Fase 2 del workflow `config-builder-core`.
- **I default della firma non arrivano al nodo — CHIUSO (§2.4).**
  Sono lo strato 2 della pila di lettura, risolti a lettura nel handler
  da `call_args_validations`; nessuna materializzazione al `create()`,
  la source resta pura.
- **Dove vive "risolve vuoto = errore" — CHIUSO (§2.4, strato 4)**: nel
  handler, `KeyError` col path completo, `mandatoryMsg` legacy come
  precedente.
- **Come una classe non-server riceve la config — CHIUSO (§2.3)**: non
  riceve un sottoalbero; delega al padre con il metodo due-righe che
  prefissa il proprio `code` (relazione duale). `configure(node)` è
  superseded; niente `branch()` in v1.
- **Dump/round-trip — CHIUSO in gran parte (§6.4)**: `to_xml`/
  `from_xml` verificati con tipi conservati; `renderer_yaml` esiste su
  ogni builder. Il diff resta non progettato (fuori scope v1).
- **Merge/layering — CHIUSO (§6), EMENDATO in v0.4.0**: niente profili
  arbitrari; gli strati sono config → preferenza di applicazione →
  preferenza utente, con ponte dichiarato per-elemento. L'emendamento
  sancisce UN layering in più, dentro il solo strato config: le ricette
  parent (§2.7) — il meccanismo legacy `instanceconfig.xml`-sopra-default,
  ricostruito su ricette ESEGUITE e piegate con `Bag.update`. Restano
  esclusi i profili arbitrari e il merge di documenti materializzati.

## 5. Ordine di lavoro — stato

1. ~~La label stabile per i figli della radice~~ **ASSORBITO nella
   Fase 2** del workflow `config-builder-core`: è l'elemento documento
   del dialetto (§4), non una modifica al core.
2. ~~`runtime_values` risolve i resolver~~ **FATTO** (`c784104`,
   7 test in `test_resolver_values.py`).
3. ~~`?attr` risolve i resolver~~ **FATTO** (genro-bag `0.19.1` su
   PyPI; il requisito minimo si dichiara in `pyproject.toml` nella
   Fase 2).
4. ~~Il sub-builder con la classe come parametro~~ **FATTO** (MERGED
   `27e86fc`: contratto BLD.2, GRAMMAR_FORMAT §4, esempio
   `10_subbuilder_by_reference`).
5. ~~I default della firma~~ **CHIUSO**: risoluzione a lettura nel
   handler (§2.4), niente materializzazione.

Il lavoro residuo è il dialetto `contrib/config` col suo
`ConfigHandler`, end-to-end: Fase 2 del workflow `config-builder-core`.

## 6. Configurazione e preferenze (decisioni 2026-07-29)

### 6.1 Due mondi, tre grammatiche

**La configurazione vive col codice, le preferenze vivono nello store.**
Cambiare la config è un deploy; cambiare una preferenza è un atto di
amministrazione (o dell'utente) a runtime, senza deploy.

- **Config** — parte da `config.py` dell'istanza: il file può non essere
  unico, ma **il run è unico** (se servono altre config è lui che
  importa e collega; composizione per import esplicito, mai
  auto-discovery). Il run produce l'albero.
- **Preferenze di applicazione** — ciò che l'amministratore regola.
- **Preferenze utente** — ciò che ogni utente regola per sé.

**Tre grammatiche SCRITTE, tre alberi, tre builder.** Le preferenze NON
sono una proiezione della config (ipotesi valutata e scartata: le
preferenze sono in massima parte un dominio proprio — aspetto,
comportamento, notifiche — che nella config non esiste, e i due alberi
servono due pubblici diversi). La sovrapposizione è la fetta piccola,
ed è **dichiarata dal lato preferenza**: l'elemento di preferenza che
ombreggia un valore di config dichiara *dove* vive il suo default (un
path di config); lo stesso schema lega preferenza utente → preferenza
di applicazione. Dove non c'è dichiarazione, i mondi non si parlano.

### 6.2 Le due porte di lettura

Decisione: **separazione, non composizione invisibile** (valutata e
scartata la porta unica; precedente legacy: `getPreference(path, pkg,
dflt, mandatoryMsg)` / `getUserPreference`, verificati su gnrapp/
gnrwebpage).

- **La porta config È il `ConfigHandler`** (§2.3–2.4) — la verità del
  recipe, pura, deploy-bound. Le preferenze non la toccano mai. La porta
  usata nel codice È la dichiarazione d'intento: ciò che si legge da qui
  (la chiave di encrypt) non è regolabile a runtime per costruzione.
- **`PreferenceHandler`** — la porta simmetrica futura, stessa forma
  callable, con la catena: valore nello store → il default dichiarato
  (path nello strato sotto, se l'elemento lo dichiara) → il default
  della firma dell'elemento. Fuori scope del workflow corrente.

Regole comuni alle due porte: i **default della firma sono il pavimento
della pila**; un path che dopo tutti gli strati non produce niente è
**errore rumoroso**, e vive nel handler (il `mandatoryMsg` legacy ne è
il precedente).

### 6.3 Lifecycle

Il server esiste per conto suo, la config lo nutre (non lo crea). Primo
atto del lifecycle: il run di `config.py` → l'albero → il
`ConfigHandler` del server. Le preferenze di applicazione si montano
nello stesso punto, quando arriveranno. Le altre classi configurabili
non ricevono un ramo: delegano al padre col metodo due-righe (§2.3),
stesso contratto a ogni livello.

### 6.4 Lo store e la GUI

- **Store = XML**: verificato, genro-bag ha `to_xml`/`from_xml` e il
  round-trip **conserva i tipi** (`port=25` torna `int`).
- **Il pannello è un render del pref builder.** Le firme degli element
  portano già tutto ciò che serve a un form: `Literal[...]` → tendina,
  `Annotated[..., Range(ge,le)]` → numero coi limiti, `bool` →
  checkbox, cardinalità → campo singolo vs lista. In scrittura vale la
  stessa validazione di firma del recipe. Pezzo NUOVO da scrivere: il
  form-renderer (walker grammatica+valori → form).
- **Limite verificato**: l'export JSON `to_grammar` v1.0 non porta i
  tipi (`attributes` sempre `null`, riservato v1.x). GUI server-side
  possibile oggi (introspezione Python); GUI client-side (genro-dom-js
  che legge il JSON) richiede prima i tipi nell'export.

## Riferimenti

Sessione `e01ae0d2-0ea9-4996-85a3-08916c7a2b4a` (2026-07-28, il modello);
sessione `91496a9b-d4c7-4c97-a8ca-08929fb82ca6` (2026-07-29, §6:
preferenze, le due porte, lifecycle, store XML, GUI-come-render);
sessione `b5d13f14-69aa-40fc-b4b8-4e6af98d4fb3` (2026-07-29, v0.3.0:
`ConfigHandler` callable e pila a quattro strati, niente mixin, delega
app-side due-righe, chiusura di tutti i punti aperti; il primitivo
`kwarg:attr` era stato merged in `27e86fc` nella sessione precedente).
Tentativo di riferimento: `genro-asgi/src/genro_asgi/config/` (branch
`main`), con `configurable.py` che dichiara la propria EXTRACTION
BOUNDARY alle righe 54-57. Regola singleton rilasciata in `0.21.1`
(commit `8e925cd`, `de156a4`).
