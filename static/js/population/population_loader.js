/**
 * PopulationLoader: orchestrates loading and adding population
 * (fetch display data, render grid, dispatch state, optional genealogy save).
 *
 * Depends on: GridRenderer, DisplayFetcher, PopulationState, GenealogySync, ApiClient
 * and RepresentationRegistry via deps.resolveRepresentation.
 *
 * Exposes: init, loadPopulation, addToPopulation.
 */
let _deps = null;

const noop = () => {};

const stopImageAnimateIfAny = () => {
    if (_deps?.stopImageAnimate) {
        try {
            _deps.stopImageAnimate();
        } catch {
            /* ignore */
        }
        _deps.stopImageAnimate = null;
    }
};

const getSubstrateType = (representation) =>
    representation?.phenotype?.substrate?.type ||
    representation?.phenotype?.substrate ||
    "image";

const canAnimateImage = (representation) =>
    getSubstrateType(representation) === "image" &&
    representation?.capabilities?.animate === true &&
    typeof window.DisplayFetcher?.startImageAnimate === "function";

const getSignalValuesFn = () => _deps?.getSignalValues || (() => ({}));

const imageAnimateIntervalMs = () => _deps?.imageAnimateIntervalMs || 200;

const setGenNumUI = (generationNum) => {
    const genEl = document.getElementById(_deps?.IDS?.genNum);
    if (genEl) genEl.textContent = String(generationNum ?? 0);
};

const updateRepUIs = (representationId) => {
    window.ViewerControls?.updateForRepresentation?.(representationId);
    window.EyecatcherDebug?.updateForRepresentation?.(representationId);
};

const showNoRepresentationError = (representationId) => {
    window.GridRenderer.showGridError(
        `No representation for ${representationId || "?"}. Check config.`,
        false
    );
    _deps?.showLoading?.(false);
    _deps?.state?.dispatch?.({ type: "SET_LOADING", payload: false });
};

const renderPopulation = (population, patternsMap, representationId) => {
    window.GridRenderer.renderGridFromPopulation(
        population,
        _deps.IDS,
        _deps.getGridCallbacks(),
        patternsMap,
        representationId
    );
};

const computeNextNumericId = () => {
    let next = 0;
    (_deps?.state?.organisms || []).forEach((o) => {
        const id = o?.id;
        if (typeof id === "number" && Number.isFinite(id))
            next = Math.max(next, id + 1);
    });
    return next;
};

const warnIfDisplayMismatch = (got, expected) => {
    if (got === expected) return;
    const msg = `Display count mismatch: got ${got} results for ${expected} organisms. Some cards may be broken or missing.`;
    console.error("Add to grid:", msg);
    _deps?.toast?.show?.("Add from community", msg, "error");
};

const warnGridMissingRules = (representation, population, payload) => {
    if (getSubstrateType(representation) !== "grid") return;

    let missingRuleCount = 0;
    population.forEach((p, idx) => {
        if (p?.id == null) {
            console.warn(
                `Add to grid: population[${idx}] missing id (genome key: ${payload[idx]?.key})`
            );
        }
        if (!p?.rule) missingRuleCount++;
    });

    if (missingRuleCount > 0) {
        _deps?.toast?.show?.(
            "Add from community",
            `${missingRuleCount} organism(s) have no rule – cards may show an error.`,
            "error"
        );
    }
};

const warnIfBrokenCards = () => {
    const organisms = _deps?.state?.organisms || [];
    let brokenCount = 0;
    let lostContextCount = 0;

    organisms.forEach((o) => {
        const rt = o?.runtime;
        const gl = rt?.gl;
        if (!rt || !gl) {
            brokenCount++;
            return;
        }
        if (typeof gl.isContextLost === "function" && gl.isContextLost())
            lostContextCount++;
    });

    if (brokenCount === 0 && lostContextCount === 0) return;

    const msg =
        brokenCount > 0 && lostContextCount > 0
            ? `${brokenCount} card(s) without display, ${lostContextCount} lost WebGL (browser limit).`
            : lostContextCount > 0
              ? `${lostContextCount} organism(s) lost display (WebGL context limit). Try fewer cards or refresh.`
              : `${brokenCount} organism(s) could not be displayed (missing rule or WebGL).`;

    console.warn("Add from community:", msg);
    _deps?.toast?.show?.("Add from community", msg, "error");
};

const maybeStartImageAnimate = (representation, genomes, representationId) => {
    if (!canAnimateImage(representation)) return;

    stopImageAnimateIfAny();

    _deps.stopImageAnimate = window.DisplayFetcher.startImageAnimate(
        representation,
        genomes,
        getSignalValuesFn(),
        imageAnimateIntervalMs(),
        (updatedPopulation) => {
            const map = new Map();
            renderPopulation(updatedPopulation, map, representationId);
        }
    );
};

const maybeSaveToGenealogy = async ({
    genomes,
    generationNum,
    branchName,
    parentId,
    patternsMap,
    population,
    representationId,
}) => {
    const gs = window.GenealogySync;
    if (!gs?.saveCurrentPopulationToGenealogy) return null;

    const fitnessData = population.map((p) => patternsMap.get(p.id)?.fitness || 0);

    try {
        const data = await gs.saveCurrentPopulationToGenealogy(
            _deps.API_URL,
            genomes,
            generationNum,
            branchName,
            parentId,
            fitnessData,
            representationId
        );

        if (data?.population_id != null) {
            _deps.state.dispatch({
                type: "SET_GENEALOGY",
                payload: { populationId: data.population_id, branchName },
            });
            gs.syncCurrentPopulationIdToStorage?.(data.population_id);
        }

        return data;
    } catch (e) {
        console.warn("Genealogy save failed:", e);
        return null;
    }
};

// ---- Public API ----

const init = (deps) => {
    _deps = deps;
};

/**
 * Load a population from genomes:
 * 1) resolve representation
 * 2) fetch display data
 * 3) render grid
 * 4) optionally save to genealogy
 * 5) dispatch LOAD_POPULATION
 */
const loadPopulation = async (
    genomes,
    generationNum,
    representationId,
    options = {}
) => {
    const saveToGenealogy = options.saveToGenealogy === true;
    if (!_deps || !Array.isArray(genomes) || genomes.length === 0) return;

    const resolved = _deps.resolveRepresentation(representationId, genomes);
    const repId = resolved.representationId;
    const representation = resolved.representation;

    if (!representation) return showNoRepresentationError(repId);

    await window.Utils.withLoading(async () => {
        stopImageAnimateIfAny();
        window.GridRenderer.clearGrid(_deps.IDS);

        const displayResult = await window.DisplayFetcher.fetchDisplayData(
            representation,
            genomes,
            {
                colorMode: _deps.getColorMode(),
            }
        );

        const population = displayResult.population || displayResult.rules || [];
        if (!population.length) {
            window.GridRenderer.showGridError(
                "No patterns returned from server.",
                true
            );
            _deps.state.dispatch({
                type: "LOAD_POPULATION",
                payload: {
                    population: [],
                    genomes,
                    generationNum,
                    representationId: repId,
                },
            });
            setGenNumUI(generationNum);
            _deps.updateStats?.();
            return;
        }

        const patternsMap = new Map();
        renderPopulation(population, patternsMap, repId);

        maybeStartImageAnimate(representation, genomes, repId);

        // Genealogy bookkeeping for “new branch on gen0” behaviour
        let branchName = _deps?.state?.getState?.()?.genealogy?.branchName || "main";
        let parentId = _deps?.state?.getState?.()?.genealogy?.populationId ?? null;

        if (saveToGenealogy) {
            if (generationNum === 0) {
                parentId = null;
                window.GenealogySync?.syncCurrentPopulationIdToStorage?.(null);

                const counter =
                    window.GenealogySync?.getGenealogyBranchCounter?.() ?? 1;
                branchName = counter === 1 ? "main" : `branch-${counter}`;
                window.GenealogySync?.setGenealogyBranchCounter?.(counter + 1);

                _deps.state.dispatch({
                    type: "SET_GENEALOGY",
                    payload: { populationId: null, branchName },
                });
            }

            await maybeSaveToGenealogy({
                genomes,
                generationNum,
                branchName,
                parentId,
                patternsMap,
                population,
                representationId: repId,
            });
        }

        _deps.state.dispatch({
            type: "LOAD_POPULATION",
            payload: {
                population,
                genomes,
                generationNum,
                patternsMap,
                representationId: repId,
            },
        });

        updateRepUIs(repId);
        setGenNumUI(generationNum);
        _deps.updateStats?.();
    }).catch((e) => {
        window.GridRenderer.showGridError(e?.message || "Failed to compile", true);
    });
};

/**
 * Add genomes to current population (community add, etc).
 * Fetch display data, append to grid, dispatch ADD_TO_POPULATION.
 */
const addToPopulation = async (genomes) => {
    if (!_deps || !Array.isArray(genomes) || genomes.length === 0) return;

    const resolved = _deps.resolveRepresentation(_deps.state.representationId, genomes);
    const representation = resolved.representation;
    if (!representation) return;

    // Make new unique numeric keys (backend uses .key)
    let nextKey = computeNextNumericId();
    const payload = genomes.map((g) => ({ ...g, key: nextKey++, fitness: 0 }));

    await window.Utils.withLoading(async () => {
        const displayResult = await window.DisplayFetcher.fetchDisplayData(
            representation,
            payload,
            {
                colorMode: _deps.getColorMode(),
            }
        );

        const population = displayResult.population || [];
        warnIfDisplayMismatch(population.length, payload.length);

        warnGridMissingRules(representation, population, payload);

        const newPatternsMap = new Map();
        window.GridRenderer.appendCardsToGrid(
            population,
            _deps.IDS,
            _deps.getGridCallbacks(),
            newPatternsMap,
            _deps.state.representationId
        );

        _deps.state.dispatch({
            type: "ADD_TO_POPULATION",
            payload: {
                genomes: payload,
                population,
                patternsMap: newPatternsMap,
                representationId: resolved.representationId,
            },
        });

        warnIfBrokenCards();
        updateRepUIs(resolved.representationId);
        _deps.updateStats?.();
    }).catch((e) => {
        console.error(e);
        _deps?.toast?.show?.("Add failed", e?.message || "Failed to compile", "error");
    });
};

window.PopulationLoader = { init, loadPopulation, addToPopulation };
