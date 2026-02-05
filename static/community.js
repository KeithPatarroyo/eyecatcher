/**
 * Community UI Module for Eyecatcher
 * 
 * Handles community pattern submission, browsing, and admin moderation.
 * 
 * Dependencies:
 * - API_URL global
 * - setupPattern, renderPattern functions for previews
 * - loadFromStatelessGenomes function
 * - addToGrid function (append patterns to current grid)
 */

(function() {
    'use strict';

    // Module state
    let _apiUrl = '';
    let _loadFromStatelessGenomes = null;
    let _addToGrid = null;
    let _getGenomeForPattern = null;
    let _setupPattern = null;
    let _renderPattern = null;
    let _communityPatternsList = [];
    let _submitCommunityGenome = null;
    let _adminKey = '';

    /**
     * Initialize the community UI module.
     * @param {Object} options
     * @param {string} options.apiUrl - Base API URL
     * @param {Function} options.loadFromStatelessGenomes - Function to load genomes into the grid (replace)
     * @param {Function} options.addToGrid - Function to append genomes to the current grid
     * @param {Function} options.getGenomeForPattern - Function to get genome for a pattern ID
     * @param {Function} options.setupPattern - Function to setup WebGL pattern (for previews)
     * @param {Function} options.renderPattern - Function to render a pattern (for previews)
     */
    function init(options) {
        _apiUrl = options.apiUrl || '';
        _loadFromStatelessGenomes = options.loadFromStatelessGenomes;
        _addToGrid = options.addToGrid;
        _getGenomeForPattern = options.getGenomeForPattern;
        _setupPattern = options.setupPattern;
        _renderPattern = options.renderPattern;
    }

    // -------------------------------------------------------------------------
    // Submit to Community
    // -------------------------------------------------------------------------

    async function openSubmitCommunityModal(patternId) {
        document.getElementById('loading').style.display = 'block';
        const genome = _getGenomeForPattern ? await _getGenomeForPattern(patternId) : null;
        document.getElementById('loading').style.display = 'none';
        if (!genome) {
            alert('Could not get pattern data.');
            return;
        }
        _submitCommunityGenome = genome;
        document.getElementById('community-submit-name').value = '';
        document.getElementById('community-submit-creator').value = '';
        document.getElementById('community-submit-modal').classList.add('show');
    }

    function closeSubmitCommunityModal() {
        _submitCommunityGenome = null;
        document.getElementById('community-submit-modal').classList.remove('show');
    }

    async function submitCommunityForm() {
        if (!_submitCommunityGenome) return;
        const name = (document.getElementById('community-submit-name').value || '').trim() || 'Unnamed';
        const creator = (document.getElementById('community-submit-creator').value || '').trim() || 'Anonymous';
        try {
            const r = await fetch(`${_apiUrl}/community/submit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ genome: _submitCommunityGenome, name, creator })
            });
            const d = await r.json().catch(() => ({}));
            if (!r.ok) {
                alert(d.error || 'Submit failed');
                return;
            }
            alert('Submitted! It will be reviewed before appearing in Community.');
            closeSubmitCommunityModal();
        } catch (e) {
            alert('Error: ' + (e.message || String(e)));
        }
    }

    // -------------------------------------------------------------------------
    // Browse Community
    // -------------------------------------------------------------------------

    async function onNewFromCommunityClick() {
        document.getElementById('loading').style.display = 'block';
        try {
            const r = await fetch(_apiUrl + '/community');
            if (!r.ok) { alert('Failed to load community.'); return; }
            const d = await r.json();
            _communityPatternsList = d.patterns || [];
            const ul = document.getElementById('community-list');
            if (!ul) return;
            ul.innerHTML = '';
            const loadSelectedBtn = document.getElementById('community-load-selected-btn');
            const load12Btn = document.getElementById('community-load-12-btn');
            const selectAllBtn = document.getElementById('community-select-all-btn');
            const deselectAllBtn = document.getElementById('community-deselect-all-btn');
            if (!_communityPatternsList.length) {
                ul.innerHTML = '<li style="color:#888;">No approved community patterns yet.</li>';
                if (loadSelectedBtn) loadSelectedBtn.style.display = 'none';
                if (load12Btn) load12Btn.style.display = 'none';
                if (selectAllBtn) selectAllBtn.style.display = 'none';
                if (deselectAllBtn) deselectAllBtn.style.display = 'none';
            } else {
                if (loadSelectedBtn) loadSelectedBtn.style.display = 'inline-block';
                if (load12Btn) load12Btn.style.display = 'inline-block';
                if (selectAllBtn) selectAllBtn.style.display = 'inline-block';
                if (deselectAllBtn) deselectAllBtn.style.display = 'inline-block';
                let shadersByKey = {};
                try {
                    const compilePayload = _communityPatternsList.map(pat => ({ ...pat.genome, key: pat.id, clicks: 0 }));
                    const comp = await fetch(_apiUrl + '/compile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ genomes: compilePayload })
                    });
                    if (comp.ok) {
                        const compData = await comp.json();
                        (compData.shaders || []).forEach(sh => { shadersByKey[sh.id] = sh; });
                    }
                } catch (e) { console.warn('Could not compile community previews:', e); }
                const previewPatternData = [];
                _communityPatternsList.forEach((pat, idx) => {
                    const li = document.createElement('li');
                    li.className = 'community-item';
                    li.dataset.idx = String(idx);
                    const checkWrap = document.createElement('div');
                    checkWrap.className = 'check-wrap';
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.checked = false;
                    checkWrap.appendChild(checkbox);
                    const previewWrap = document.createElement('div');
                    previewWrap.className = 'preview-wrap';
                    const canvas = document.createElement('canvas');
                    canvas.width = 80;
                    canvas.height = 80;
                    previewWrap.appendChild(canvas);
                    const info = document.createElement('div');
                    info.className = 'info';
                    info.textContent = (pat.name || 'Unnamed') + ' by ' + (pat.creator || '?');
                    li.appendChild(checkWrap);
                    li.appendChild(previewWrap);
                    li.appendChild(info);
                    ul.appendChild(li);
                    const shaderInfo = shadersByKey[pat.id];
                    if (shaderInfo && shaderInfo.shader && _setupPattern) {
                        const pd = _setupPattern(canvas, shaderInfo.shader);
                        if (pd) previewPatternData.push(pd);
                    }
                });
                if (_renderPattern) {
                    requestAnimationFrame(() => {
                        previewPatternData.forEach(pd => _renderPattern(pd, 0.5, 0, 0, 0));
                    });
                }
            }
            document.getElementById('community-list-modal').classList.add('show');
        } catch (e) {
            alert('Error: ' + (e.message || e));
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }

    function getCommunitySelectedGenomes() {
        const ul = document.getElementById('community-list');
        if (!ul) return [];
        const checked = ul.querySelectorAll('.community-item input[type="checkbox"]:checked');
        const genomes = [];
        checked.forEach(cb => {
            const li = cb.closest('.community-item');
            const idx = parseInt(li.dataset.idx, 10);
            if (_communityPatternsList[idx]) {
                genomes.push(_communityPatternsList[idx].genome);
            }
        });
        return genomes;
    }

    function onCommunityLoadSelected() {
        const genomes = getCommunitySelectedGenomes();
        if (!genomes.length) {
            alert('No patterns selected.');
            return;
        }
        document.getElementById('community-list-modal').classList.remove('show');
        if (_addToGrid) {
            _addToGrid(genomes);
        }
    }

    function onCommunityLoad12() {
        const first12 = _communityPatternsList.slice(0, 12).map(p => p.genome);
        document.getElementById('community-list-modal').classList.remove('show');
        if (_addToGrid) {
            _addToGrid(first12);
        }
    }

    function onCommunitySelectAll() {
        document.querySelectorAll('#community-list .community-item input[type="checkbox"]').forEach(cb => { cb.checked = true; });
    }

    function onCommunityDeselectAll() {
        document.querySelectorAll('#community-list .community-item input[type="checkbox"]').forEach(cb => { cb.checked = false; });
    }

    // -------------------------------------------------------------------------
    // Admin Moderation
    // -------------------------------------------------------------------------

    function openAdminModal() {
        _adminKey = '';
        document.getElementById('admin-key-input').value = '';
        document.getElementById('admin-key-error').style.display = 'none';
        document.getElementById('admin-key-error').textContent = '';
        document.getElementById('admin-step-key').style.display = 'block';
        document.getElementById('admin-step-list').style.display = 'none';
        document.getElementById('admin-modal').classList.add('show');
    }

    function closeAdminModal() {
        _adminKey = '';
        document.getElementById('admin-modal').classList.remove('show');
    }

    async function submitAdminKey() {
        const key = (document.getElementById('admin-key-input').value || '').trim();
        const errEl = document.getElementById('admin-key-error');
        if (!key) {
            errEl.textContent = 'Please enter the API key.';
            errEl.style.display = 'block';
            return;
        }
        try {
            const r = await fetch(_apiUrl + '/admin/submissions?admin_key=' + encodeURIComponent(key), {
                headers: { 'X-Admin-Key': key }
            });
            if (r.status === 403) {
                errEl.textContent = 'Invalid API key.';
                errEl.style.display = 'block';
                return;
            }
            if (!r.ok) {
                errEl.textContent = 'Request failed (status ' + r.status + ').';
                errEl.style.display = 'block';
                return;
            }
            _adminKey = key;
            const d = await r.json();
            const list = d.submissions || [];
            document.getElementById('admin-step-key').style.display = 'none';
            document.getElementById('admin-step-list').style.display = 'block';
            await renderAdminPendingList(list);
        } catch (e) {
            errEl.textContent = 'Error: ' + (e.message || String(e));
            errEl.style.display = 'block';
        }
    }

    async function renderAdminPendingList(submissions) {
        const ul = document.getElementById('admin-pending-list');
        ul.innerHTML = '';
        if (!submissions.length) {
            ul.innerHTML = '<li style="color:#888;padding:12px;">No pending submissions.</li>';
            return;
        }
        let shadersByKey = {};
        try {
            const compilePayload = submissions.map(s => ({ ...s.genome, key: s.id, clicks: 0 }));
            const comp = await fetch(_apiUrl + '/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ genomes: compilePayload })
            });
            if (comp.ok) {
                const compData = await comp.json();
                (compData.shaders || []).forEach(sh => { shadersByKey[sh.id] = sh; });
            }
        } catch (e) {
            console.warn('Could not compile previews:', e);
        }
        const previewPatternData = [];
        submissions.forEach(sub => {
            const li = document.createElement('li');
            li.className = 'pending-item';
            const previewWrap = document.createElement('div');
            previewWrap.className = 'preview-wrap';
            const canvas = document.createElement('canvas');
            canvas.width = 80;
            canvas.height = 80;
            previewWrap.appendChild(canvas);
            const info = document.createElement('div');
            info.className = 'info';
            info.innerHTML = '<strong>' + (sub.name || 'Unnamed') + '</strong> by ' + (sub.creator || '?');
            const actions = document.createElement('div');
            actions.className = 'actions';
            actions.innerHTML = '<button type="button" class="approve-btn">Approve</button><button type="button" class="reject-btn">Reject</button>';
            li.appendChild(previewWrap);
            li.appendChild(info);
            li.appendChild(actions);
            li.querySelector('.approve-btn').addEventListener('click', () => adminApprove(sub.id, li));
            li.querySelector('.reject-btn').addEventListener('click', () => adminReject(sub.id, li));
            ul.appendChild(li);
            const shaderInfo = shadersByKey[sub.id];
            if (shaderInfo && shaderInfo.shader && _setupPattern) {
                const pd = _setupPattern(canvas, shaderInfo.shader);
                if (pd) previewPatternData.push(pd);
            }
        });
        if (_renderPattern) {
            requestAnimationFrame(() => {
                previewPatternData.forEach(pd => _renderPattern(pd, 0.5, 0, 0, 0));
            });
        }
    }

    async function adminApprove(id, rowEl) {
        try {
            const r = await fetch(_apiUrl + '/admin/approve?admin_key=' + encodeURIComponent(_adminKey), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Admin-Key': _adminKey },
                body: JSON.stringify({ id })
            });
            if (r.status === 403) { alert('Invalid API key.'); return; }
            if (!r.ok) { alert('Approve failed.'); return; }
            rowEl.remove();
        } catch (e) { alert('Error: ' + (e.message || e)); }
    }

    async function adminReject(id, rowEl) {
        try {
            const r = await fetch(_apiUrl + '/admin/reject?admin_key=' + encodeURIComponent(_adminKey), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Admin-Key': _adminKey },
                body: JSON.stringify({ id })
            });
            if (r.status === 403) { alert('Invalid API key.'); return; }
            if (!r.ok) { alert('Reject failed.'); return; }
            rowEl.remove();
        } catch (e) { alert('Error: ' + (e.message || e)); }
    }

    // Export to global namespace
    window.CommunityUI = {
        init: init,
        // Submit
        openSubmitCommunityModal: openSubmitCommunityModal,
        closeSubmitCommunityModal: closeSubmitCommunityModal,
        submitCommunityForm: submitCommunityForm,
        // Browse
        onNewFromCommunityClick: onNewFromCommunityClick,
        getCommunitySelectedGenomes: getCommunitySelectedGenomes,
        onCommunityLoadSelected: onCommunityLoadSelected,
        onCommunityLoad12: onCommunityLoad12,
        onCommunitySelectAll: onCommunitySelectAll,
        onCommunityDeselectAll: onCommunityDeselectAll,
        // Admin
        openAdminModal: openAdminModal,
        closeAdminModal: closeAdminModal,
        submitAdminKey: submitAdminKey
    };
})();
