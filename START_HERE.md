# Start here



- **Run an experiment** — `make docker-up`, then open http://localhost:5001. Local Python: [README.md#running-the-project](README.md#running-the-project).
- **Change representation or add a new one** — Preset: [config/experiments.json](config/experiments.json) (`"representation"` key). To scaffold: `make new-representation name=<name>` (e.g. name=my_rep), then `make generate`. You declare a **phenotype** (e.g. `Phenotype(substrate="shader")`) in Python; no JavaScript for standard substrates (shader, grid, image). Full checklist: [RESEARCHER_GUIDE.md#add-a-new-representation](RESEARCHER_GUIDE.md#add-a-new-representation).
- **Add or change a signal** — [RESEARCHER_GUIDE.md#add-or-change-a-signal-inputoutput](RESEARCHER_GUIDE.md#add-or-change-a-signal-inputoutput). Edit [signals/catalog.py](src/eyecatcher/signals/catalog.py), then `make generate`.
- **Add a fitness** — [RESEARCHER_GUIDE.md#batch-evolution-representation-agnostic](RESEARCHER_GUIDE.md#batch-evolution-representation-agnostic). Registry: [evolution/fitness.py](src/eyecatcher/evolution/fitness.py).
- **Where config lives** — One table; "where do I set X?" → run `python -m eyecatcher config --show` or GET `/api/config?provenance=1` to see effective values and which layer each came from.

| Layer | Source | Purpose |
|-------|--------|---------|
| Defaults | [config/evolution_defaults.json](config/evolution_defaults.json) | Base values for population_size, crossover_probability, etc. |
| Preset | [config/experiments.json](config/experiments.json) (env `EXPERIMENT_CONFIG`) | Override representation, NEAT paths, evolution params per named experiment. |
| Runtime | PATCH `/api/config` or in-memory | Override population_size, max_population_size, crossover_probability without restart. |

Frontend sync and NEAT: [RESEARCHER_GUIDE.md#keeping-frontend-in-sync](RESEARCHER_GUIDE.md#keeping-frontend-in-sync).

**Deep dives:** [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md) (evolution, representation, signals, API). [README.md](README.md) (running, deploy, layout). [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) (tests, style).
