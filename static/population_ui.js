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
 * - getCurrentGenomesForSave function (returns client-held genomes + generation, or null)
 */

(function() {
    'use strict';

    // Module state
    let _apiUrl = '';
    let _loadFromStatelessGenomes = null;
    let _getCurrentGenomesForSave = null;

    /**
     * Initialize the population UI module.
     * @param {Object} options
     * @param {string} options.apiUrl - Base API URL
     * @param {Function} options.loadFromStatelessGenomes - Function to load genomes into the grid
     * @param {Function} options.getCurrentGenomesForSave - Function to get current genomes for saving
     */
    function init(options) {
        _apiUrl = options.apiUrl || '';
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _getCurrentGenomesForSave = options.getCurrentGenomesForSave;
    }

    /**
     * Start a new random population from the server.
     */
    async function startNewRandomPopulation() {
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.style.display = 'block';
        try {
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
                await _loadFromStatelessGenomes(d.genomes || [], 0);
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
            const r = await fetch(_apiUrl + '/seeds');
            if (!r.ok) { alert('Failed to load seeds'); return; }
            const d = await r.json();
            const seeds = d.seeds || [];
            if (!seeds.length) { alert('No seeds available.'); return; }
            if (_loadFromStatelessGenomes) {
                await _loadFromStatelessGenomes(seeds.slice(0, 12).map(s => s.genome || s), 0);
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
     * Export current population to JSON file.
     */
    async function onExportClick() {
        const data = _getCurrentGenomesForSave ? await _getCurrentGenomesForSave() : null;
        if (!data || !data.genomes.length) {
            alert('No population to export. Start with New random population or Load Saved.');
            return;
        }
        const blob = new Blob([JSON.stringify({
            name: 'Exported',
            generation: data.generation,
            genomes: data.genomes,
            exportedAt: new Date().toISOString()
        }, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'eyecatcher-population.json';
        a.click();
        URL.revokeObjectURL(a.href);
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
     * @param {File} file - The imported file
     */
    async function handleImportFile(file) {
        if (!file) return;
        try {
            const json = JSON.parse(await file.text());
            const genomes = json.genomes || [];
            if (!genomes.length) {
                alert('No genomes in file');
                return;
            }
            if (typeof EyecatcherStorage !== 'undefined') {
                await EyecatcherStorage.init();
                await EyecatcherStorage.importPopulation(json);
            }
            if (_loadFromStatelessGenomes) {
                await _loadFromStatelessGenomes(genomes, json.generation != null ? json.generation : 0);
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
        onExportClick: onExportClick,
        onImportClick: onImportClick,
        handleImportFile: handleImportFile
    };
})();
