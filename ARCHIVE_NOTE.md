# Archive — pre-restart blueprint (2026-04)

Questo branch è uno **snapshot prezioso**, non un esperimento fallito.

## Cosa contiene

L'evoluzione di `main` fino al 2026-05-01 (commit `b19780e`). In ~32
commit ha esplorato e fatto funzionare quasi tutte le funzionalità
target di `genro-builders`:

- **Pointer** `^path`, `^.relative`, `^volume:path`, `^path?attr` —
  risoluzione data-driven dei valori e degli attributi.
- **Reattività** pull-based: `data_formula` con `FormulaResolver`,
  subscribe/notify via `BindingManager`, dependency graph,
  partial recompile.
- **Component** `@component` con espansione lazy, slots, main_tag,
  proxy, iterate.
- **Iterate**: replica di un sotto-albero su una collezione di dati.
- **Data elements** (`data_setter`, `data_formula`, controller) con
  routing per volume e datapath gerarchico.
- **Manager** `BuilderManager` / `ReactiveManager` per coordinare più
  builder con dati condivisi.
- **Live** (`contrib/live/`): remote control e CLI per sessioni async.
- **Esempi** (`src/genro_builders/contrib/html/examples/`)
  funzionanti su tutte le feature sopra.

## Perché è in archivio

L'architettura era cresciuta in modo organico: ogni feature aveva
trovato spazio dove c'era posto, non dove sarebbe dovuta stare. Il
risultato era un sistema in cui build, reattività, manager e bag
erano intrecciati in modi che rendevano impossibile aggiungere una
funzionalità senza romperne un'altra. La cartella `temp/` documenta
i tentativi di rifattorizzare in-place, tutti abortiti.

Il 2026-05-03/04 è stato fissato un nuovo contratto architettonico
in 12 punti (poi rinegoziati il 2026-05-08), e il lavoro è ripartito
su `develop` da `b19780e`.

## Che relazione ha con `develop`

- **`develop`**: l'evoluzione *controllata* a partire da `main`, sotto
  il contratto in `docs/architecture-contract.md`. Ogni feature che
  era qui viene reintrodotta una alla volta, sotto il contratto.
- **Questo branch**: il riferimento funzionale che dice *cosa* deve
  poter fare `genro-builders` quando tutto sarà reintrodotto.

## Cosa fare con questo branch

- **Consultare** quando serve capire come una feature è stata
  implementata in passato.
- **Non sviluppare** qui. Niente nuovi commit, niente fix. Se serve un
  intervento sulla feature X, la si reintroduce su `develop` sotto il
  contratto.

## Riferimenti

- Contratto attuale: `docs/architecture-contract.md` su `develop`.
- HEAD di questo branch: `b19780e feat(build): mirror plain html source into built tree`.
