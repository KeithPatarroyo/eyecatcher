/**
 * Population UI Module for Eyecatcher
 * 
 * Handles client-side storage interactions (IndexedDB via EyecatcherStorage)
 * and population save/load/export/import functionality.
 * 
 * Dependencies:
 * - EyecatcherStorage (from storage.js)
 * - API_URL global
 * - loadFromStatelessGenomes function
 * - addToGrid function (append patterns to current grid)
 * - getCurrentGenomesForSave function (returns client-held genomes + generation, or null)
 */

(function() {
    'use strict';

    // Module state
    let _apiUrl = '';
    let _loadFromStatelessGenomes = null;
    let _addToGrid = null;
    let _getCurrentGenomesForSave = null;

    /**
     * Initialize the population UI module.
     * @param {Object} options
     * @param {string} options.apiUrl - Base API URL
     * @param {Function} options.loadFromStatelessGenomes - Function to load genomes into the grid (replace)
     * @param {Function} options.addToGrid - Function to append genomes to the current grid
     * @param {Function} options.getCurrentGenomesForSave - Function to get current genomes for saving
     */
    function init(options) {
        _apiUrl = options.apiUrl || '';
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _addToGrid = options.addToGrid;
        _getCurrentGenomesForSave = options.getCurrentGenomesForSave;
    }

    /**
     * Start a new random population from the server.
     */
    async function startNewRandomPopulation() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.style.display = 'block';
        try {
            // Clear any existing session data when starting fresh
            sessionStorage.removeItem('current_population_data');
            sessionStorage.removeItem('current_population_id');
            sessionStorage.removeItem('has_population');
            
            const r = await fetch(`${_apiUrl}/random`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ size: 12 })
            });
            if (!r.ok) {
                const d = await r.json().catch(() => ({}));
                alert(d.error || 'Failed to create random population');
                return;
            }
            const d = await r.json();
            if (_loadFromStatelessGenomes) {
                // Pass saveToGenealogy = true to auto-save new random populations
                await _loadFromStatelessGenomes(d.genomes || [], 0, true);
            }
        } catch (error) {
            console.error('Error starting random population:', error);
            alert('Error: ' + (error.message || String(error)));
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    /**
     * Load population from curated seeds.
     */
    async function onNewFromSeedsClick() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.style.display = 'block';
        try {
            // Clear any existing session data when starting fresh
            sessionStorage.removeItem('current_population_data');
            sessionStorage.removeItem('current_population_id');
            sessionStorage.removeItem('has_population');
            
            const r = await fetch(_apiUrl + '/seeds');
            if (!r.ok) { alert('Failed to load seeds'); return; }
            const d = await r.json();
            const seeds = d.seeds || [];
            if (!seeds.length) { alert('No seeds available.'); return; }
            if (_loadFromStatelessGenomes) {
                // Pass saveToGenealogy = true for seeds too (creates new branch)
                await _loadFromStatelessGenomes(seeds.slice(0, 12).map(s => s.genome || s), 0, true);
            }
        } catch (e) {
            alert('Error: ' + (e.message || e));
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    /**
     * Open the load saved populations modal.
     */
    async function onLoadSavedClick() {
        try {
            if (typeof EyecatcherStorage === 'undefined') {
                alert('Storage not loaded. Check that storage.js is served.');
                return;
            }
            await EyecatcherStorage.init();
            const list = await EyecatcherStorage.listPopulations();
            const ul = document.getElementById('load-list');
            if (!ul) return;
            ul.innerHTML = '';
            if (!list.length) {
                ul.innerHTML = '<li style="color:#888;">No saved populations</li>';
            } else {
                list.forEach(pop => {
                    const li = document.createElement('li');
                    li.textContent = (pop.name || 'Unnamed') + ' (gen ' + (pop.generation || 0) + ', ' + (pop.genomes || []).length + ' patterns)';
                    li.onclick = async () => {
                        document.getElementById('load-list-modal').classList.remove('show');
                        if (_loadFromStatelessGenomes) {
                            await _loadFromStatelessGenomes(pop.genomes || [], pop.generation || 0);
                        }
                    };
                    ul.appendChild(li);
                });
            }
            document.getElementById('load-list-modal').classList.add('show');
        } catch (e) {
            alert('Error: ' + (e.message || e));
        }
    }

    /**
     * Save current population to IndexedDB.
     */
    async function onSaveCurrentClick() {
        if (typeof EyecatcherStorage === 'undefined') {
            alert('Storage not loaded.');
            return;
        }
        const data = _getCurrentGenomesForSave ? await _getCurrentGenomesForSave() : null;
        if (!data || !data.genomes.length) {
            alert('No population to save. Start with New random population or Load Saved.');
            return;
        }
        const name = prompt('Name this population:', 'Session ' + new Date().toLocaleDateString());
        if (name == null) return;
        try {
            await EyecatcherStorage.init();
            await EyecatcherStorage.savePopulation((name.trim() || 'Unnamed'), data.genomes, data.generation);
            alert('Saved.');
        } catch (e) {
            alert('Error: ' + (e.message || e));
        }
    }

    /**
     * Trigger file input for import.
     */
    function onImportClick() {
        const input = document.getElementById('import-file');
        if (input) input.click();
    }

    /**
     * Handle imported file (call this from the file input's change handler).
     * Supports .zip (saved pattern with genome_*.json) or .json (population with genomes array).
     * Adds patterns to the current grid without replacing.
     * @param {File} file - The imported file
     */
    async function handleImportFile(file) {
        if (!file) return;
        const name = (file.name || '').toLowerCase();
        try {
            let genomes = [];
            if (name.endsWith('.zip')) {
                if (typeof JSZip === 'undefined') {
                    alert('Import failed: JSZip not loaded. Check script for jszip.min.js.');
                    return;
                }
                const zip = await JSZip.loadAsync(file);
                const genomeFiles = Object.keys(zip.files).filter(n => /^genome_.*\.json$/i.test(n));
                if (!genomeFiles.length) {
                    alert('No genome JSON found in zip (expected genome_*.json).');
                    return;
                }
                for (const entry of genomeFiles) {
                    const text = await zip.files[entry].async('string');
                    const genome = JSON.parse(text);
                    if (genome && genome.visual && genome.time_signal) {
                        genomes.push(genome);
                    }
                }
            } else {
                const json = JSON.parse(await file.text());
                genomes = json.genomes || [];
                if (genomes.length && typeof EyecatcherStorage !== 'undefined') {
                    await EyecatcherStorage.init();
                    await EyecatcherStorage.importPopulation(json);
                }
            }
            if (!genomes.length) {
                alert('No genomes in file');
                return;
            }
            if (_addToGrid) {
                await _addToGrid(genomes);
            }
        } catch (err) {
            alert('Import failed: ' + (err.message || err));
        }
    }

    // Export to global namespace
    window.PopulationUI = {
        init: init,
        startNewRandomPopulation: startNewRandomPopulation,
        onNewFromSeedsClick: onNewFromSeedsClick,
        onLoadSavedClick: onLoadSavedClick,
        onSaveCurrentClick: onSaveCurrentClick,
        onImportClick: onImportClick,
        handleImportFile: handleImportFile
    };
})();
