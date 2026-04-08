let currentSchema = null;
let activeTable = null;
let currentUrl = null;
let currentProjectName = null;
let currentConnectionPayload = null;
let activeMode = 'sqlite';
let currentView = 'grid';
let panZoomInstance = null;
let editingCol = null;

const els = {
    overlay: document.getElementById('connect-overlay'),
    btnOpenConnect: document.getElementById('btn-open-connect'),
    statusBadge: document.getElementById('current-db-status'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    btnBrowse: document.getElementById('btn-browse'),
    btnConnectModal: document.getElementById('btn-connect-modal'),
    sqlitePath: document.getElementById('sqlite-path'),
    dbUrl: document.getElementById('db-uri'),
    
    remoteType: document.getElementById('remote-type'),
    dbHost: document.getElementById('db-host'),
    dbPort: document.getElementById('db-port'),
    dbUser: document.getElementById('db-user'),
    dbPass: document.getElementById('db-pass'),
    dbName: document.getElementById('db-name'),

    viewTabs: document.querySelectorAll('.view-tab'),
    viewPanes: document.querySelectorAll('.view-pane'),

    tableList: document.getElementById('table-list'),
    tableName: document.getElementById('current-table-name'),
    tableDescInput: document.getElementById('table-desc-input'),
    btnSaveTableDesc: document.getElementById('btn-save-table-desc'),
    columnsGrid: document.getElementById('columns-grid'),
    
    mermaidWrapper: document.getElementById('mermaid-wrapper'),
    zoomIn: document.getElementById('zoom-in'),
    zoomOut: document.getElementById('zoom-out'),
    zoomReset: document.getElementById('zoom-reset'),

    editModal: document.getElementById('modal-overlay'),
    modalTitle: document.getElementById('modal-title'),
    modalSubtitle: document.getElementById('modal-subtitle'),
    editDesc: document.getElementById('edit-description'),
    editValues: document.getElementById('edit-values'),
    editRefTable: document.getElementById('edit-ref-table'),
    editRefColumn: document.getElementById('edit-ref-column'),
    btnSaveEdit: document.getElementById('btn-save-modal'),
    btnCloseEdit: document.getElementById('btn-close-modal'),
    tableSearchInput: document.getElementById('table-search-input')
};

lucide.createIcons();
mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });

// ── Init ──
loadRecentConnections();
fetchTemplates();

// ── View Switcher ──
els.viewTabs.forEach(tab => {
    tab.onclick = () => {
        els.viewTabs.forEach(t => t.classList.remove('active'));
        els.viewPanes.forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`${tab.dataset.view}-view`).classList.add('active');
        currentView = tab.dataset.view;
        if (currentView === 'diagram') renderDiagram();
    };
});

// ── Mode Switcher ──
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.mode-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`${btn.dataset.mode}-pane`).classList.add('active');
        activeMode = btn.dataset.mode;
        renderTemplates(); // Re-filter templates on mode change
    };
});

// ── Recent Connections ──
async function loadRecentConnections() {
    try {
        const resp = await fetch('/api/connections');
        const connections = await resp.json();
        const container = document.getElementById('recent-connections');
        const list = document.getElementById('recent-list');
        
        if (connections.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        list.innerHTML = '';
        
        connections.forEach(conn => {
            const date = new Date(conn.last_connected).toLocaleString();
            let iconClass = 'other';
            let iconLetter = 'DB';
            
            if (conn.mode === 'sqlite') { iconClass = 'sqlite'; iconLetter = 'SQ'; }
            else if (conn.db_type === 'postgresql') { iconClass = 'postgresql'; iconLetter = 'PG'; }
            else if (conn.db_type === 'mysql') { iconClass = 'mysql'; iconLetter = 'MY'; }
            else if (conn.db_type === 'mssql') { iconClass = 'mssql'; iconLetter = 'MS'; }

            const card = document.createElement('div');
            card.className = 'recent-card';
            card.innerHTML = `
                <div class="recent-icon ${iconClass}">${iconLetter}</div>
                <div class="recent-info">
                    <div class="recent-name">${conn.name}</div>
                    <div class="recent-meta">
                        <span>${conn.table_count} tables</span>
                        <span>•</span>
                        <span>${date}</span>
                    </div>
                </div>
                <button class="recent-delete" title="Remove connection">
                    <i data-lucide="trash-2"></i>
                </button>
            `;

            // Auto-connect on click
            card.onclick = (e) => {
                if (e.target.closest('.recent-delete')) return;
                
                // Set form payload manually from saved data
                const payload = { 
                    mode: conn.mode,
                    project_name: conn.name
                };
                if (conn.mode === 'sqlite') payload.path = conn.path;
                else if (conn.mode === 'uri') {
                    if (conn.connection_url && conn.connection_url.includes(':***@')) {
                        const pass = prompt(`This connection requires a password.\nURI: ${conn.connection_url.replace(':***@', ':_____@')}\nPlease enter the database password:`);
                        if (pass === null) return;
                        payload.uri = conn.connection_url.replace(':***@', `:${encodeURIComponent(pass)}@`);
                    } else {
                        payload.uri = conn.connection_url;
                    }
                }
                else {
                    payload.type = conn.db_type;
                    payload.host = conn.host;
                    payload.port = conn.port;
                    payload.user = conn.username;
                    payload.name = conn.db_name;
                    // Ask user for the remote password since history doesn't save it
                    const pass = prompt(`Enter database password for ${conn.username}@${conn.host}:`);
                    if (pass === null) return;
                    payload.pass = pass;
                }
                
                // Set the input visually as well
                document.getElementById('project-name').value = conn.name;
                
                // Directly execute connect with payload
                executeConnect(payload);
            };

            // Delete connection
            const btnDelete = card.querySelector('.recent-delete');
            btnDelete.onclick = async (e) => {
                e.stopPropagation();
                if (confirm('Remove this saved connection?')) {
                    await fetch(`/api/connections/${conn.id}`, { method: 'DELETE' });
                    loadRecentConnections();
                }
            };
            
            list.appendChild(card);
        });
        lucide.createIcons();
    } catch (e) { console.error("Could not load recent connections:", e); }
}

// ── Zoom & Utils ──
els.zoomIn.onclick = () => panZoomInstance && panZoomInstance.zoomIn();
els.zoomOut.onclick = () => panZoomInstance && panZoomInstance.zoomOut();
els.zoomReset.onclick = () => panZoomInstance && panZoomInstance.reset();

els.btnOpenConnect.onclick = () => els.overlay.classList.remove('hidden');

els.btnBrowse.onclick = async () => {
    const resp = await fetch('/api/browse-file');
    const data = await resp.json();
    if (data.path) els.sqlitePath.value = data.path;
};

let allTemplates = [];
async function fetchTemplates() {
    try {
        const resp = await fetch('/api/templates');
        const data = await resp.json();
        allTemplates = data.templates || [];
        renderTemplates();
    } catch (e) { console.warn("Templates could not be loaded", e); }
}

function renderTemplates() {
    const select = document.getElementById('template-select');
    if (!select) return;

    // Determine target DB types based on active mode
    let compatibleTypes = [];
    if (activeMode === 'sqlite') compatibleTypes = ['sqlite'];
    else if (activeMode === 'remote') {
        const remoteType = document.getElementById('remote-type').value;
        compatibleTypes = [remoteType];
    } else {
        // URI mode is tricky, show all for now or try to parse protocol
        compatibleTypes = ['mysql', 'postgresql', 'mssql', 'sqlite'];
    }

    select.innerHTML = '<option value="">— Start Empty —</option>';
    
    allTemplates.forEach(t => {
        // Check intersection between template db_types and compatibleTypes
        const isCompatible = t.db_types.some(type => compatibleTypes.includes(type));
        
        if (isCompatible) {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = `${t.name} (${t.annotation_count} rules)`;
            opt.title = t.description;
            select.appendChild(opt);
        }
    });

    // Handle remote type change listener if not added
    const remoteTypeSelect = document.getElementById('remote-type');
    if (remoteTypeSelect && !remoteTypeSelect.dataset.listener) {
        remoteTypeSelect.onchange = () => renderTemplates();
        remoteTypeSelect.dataset.listener = "true";
    }
}

// ── Connect ──
els.btnConnectModal.onclick = async () => {
    const projectName = document.getElementById('project-name').value.trim();
    if (!projectName) {
        alert("Please enter a Project / Connection Name.");
        return;
    }

    const templateId = document.getElementById('template-select').value;
    if (templateId) {
        try {
            await fetch('/api/apply-template', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_id: templateId, project_name: projectName })
            });
        } catch (e) { console.error("Template application failed", e); }
    }

    let payload = { mode: activeMode, project_name: projectName };
    if (activeMode === 'sqlite') payload.path = els.sqlitePath.value;
    else if (activeMode === 'uri') payload.uri = els.dbUrl.value;
    else {
        payload.type = els.remoteType.value;
        payload.host = els.dbHost.value;
        payload.port = els.dbPort.value;
        payload.user = els.dbUser.value;
        payload.pass = els.dbPass.value;
        payload.name = els.dbName.value;
    }
    executeConnect(payload);
};

async function executeConnect(payload) {
    els.btnConnectModal.textContent = "Connecting...";
    try {
        const resp = await fetch('/api/connect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        currentSchema = data.schema;
        currentUrl = payload.path || payload.uri || data.url_info;
        currentProjectName = data.project_name;
        currentConnectionPayload = payload;
        
        els.statusBadge.textContent = "Connected: " + currentProjectName;
        els.statusBadge.classList.add('connected');
        els.overlay.classList.add('hidden');
        renderTableList();
        if (currentSchema.tables.length > 0) selectTable(currentSchema.tables[0].name);
        
        // Refresh recent connections silently
        loadRecentConnections();
    } catch (e) { alert("Connection failed: " + e.message); } finally {
        els.btnConnectModal.textContent = "Connect to Database";
        lucide.createIcons();
    }
}

// ── Table List ──
function renderTableList() {
    els.tableList.innerHTML = '';
    const query = (els.tableSearchInput?.value || '').toLowerCase();
    
    currentSchema.tables.forEach(table => {
        if (query && !table.name.toLowerCase().includes(query)) return;
        
        const li = document.createElement('li');
        li.textContent = table.name;
        li.onclick = () => selectTable(table.name);
        if (activeTable === table.name) li.classList.add('active');
        els.tableList.appendChild(li);
    });
}

// ── Table Search Event ──
if (els.tableSearchInput) {
    els.tableSearchInput.addEventListener('input', () => {
        renderTableList();
    });
}

// ── Select Table (Grid View) ──
function selectTable(name) {
    activeTable = name;
    els.tableName.textContent = name;
    renderTableList();
    const tableData = currentSchema.tables.find(t => t.name === name);
    els.tableDescInput.value = tableData.description || '';
    renderSqlBoxes(tableData.sql_examples);
    document.getElementById('column-count').textContent = tableData.columns.length;
    document.getElementById('column-search-input').value = '';
    
    els.columnsGrid.innerHTML = '';
    tableData.columns.forEach(col => {
        const card = document.createElement('div');
        card.className = 'column-card';
        card.dataset.name = col.name.toLowerCase();

        // Determine FK badges: real FK or virtual FK from annotations
        let fkBadge = '';
        if (col.is_foreign_key && col.ref_table) {
            fkBadge = `<span class="badge fk">FK: ${col.ref_table}</span>`;
        } else if (col.annotations?.ref_table) {
            fkBadge = `<span class="badge virtual-fk">→ ${col.annotations.ref_table}</span>`;
        }

        card.innerHTML = `<div class="col-head"><span class="col-name">${col.name}</span><span class="col-type">${col.data_type}</span></div>
            <div class="badges">${col.is_primary_key ? '<span class="badge pk">PK</span>' : ''}${fkBadge}</div>
            <div class="col-desc">${col.description || 'No description provided'}</div>
            <button class="btn-edit" onclick="openModal('${col.name}')">Annotate</button>`;
        els.columnsGrid.appendChild(card);
    });
}

// ── Column Search ──
document.getElementById('column-search-input').addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase();
    const cards = els.columnsGrid.querySelectorAll('.column-card');
    cards.forEach(card => {
        if (card.dataset.name.includes(q)) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
});

// ── Dynamic SQL Boxes ──
function renderSqlBoxes(sqlArray) {
    const container = document.getElementById('sql-boxes-container');
    container.innerHTML = '';
    if (!sqlArray || sqlArray.length === 0) {
        addSqlBox('');
    } else {
        sqlArray.forEach(sql => addSqlBox(sql));
    }
}

function addSqlBox(initialValue = '') {
    const container = document.getElementById('sql-boxes-container');
    const boxId = 'sql-box-' + Date.now() + Math.floor(Math.random() * 1000);
    const box = document.createElement('div');
    box.style.marginBottom = '12px';
    box.innerHTML = `
        <div style="display: flex; justify-content: flex-end; gap: 5px; margin-bottom: 3px;">
            <button class="mini-button btn-test-sql" data-target="${boxId}" title="Test Query if it's a SQL statement"><i data-lucide="play" style="width: 12px; height: 12px;"></i> Test Query</button>
            <button class="mini-button" onclick="this.closest('div').parentElement.remove()" title="Delete" style="color: #ff6b6b;"><i data-lucide="trash-2" style="width: 12px; height: 12px;"></i></button>
        </div>
        <textarea id="${boxId}" placeholder="Enter a business rule, usage note, or a SQL query...&#10;(e.g., 'Users are soft-deleted' or 'SELECT * FROM users')" style="width: 100%; height: 60px; font-family: 'Courier New', monospace; font-size: 0.85rem; border-style: dashed; padding: 8px; border-radius: 4px; border: 1px dashed var(--border); background: rgba(255,255,255,0.02); resize: vertical; color: var(--text);">${initialValue}</textarea>
        <div id="res-${boxId}" style="display:none; font-family: monospace; font-size: 0.8rem; margin-top: 5px; padding: 8px; background: rgba(0,0,0,0.5); border-radius: 4px; color: #a0a0b0; max-height: 150px; overflow-y: auto;"></div>
    `;
    container.appendChild(box);
    lucide.createIcons();
    
    // Attach event to the Test button
    box.querySelector('.btn-test-sql').onclick = async (e) => {
        const query = document.getElementById(boxId).value.trim();
        if (!query) return alert("Please enter a SQL query to test.");
        if (!currentConnectionPayload) return alert("Not connected to a database.");

        const btn = e.currentTarget;
        const resBox = document.getElementById('res-' + boxId);
        btn.innerHTML = '<i data-lucide="loader"></i> ...';
        lucide.createIcons();

        try {
            const resp = await fetch('/api/test-sql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...currentConnectionPayload, project_name: currentProjectName, query: query })
            });
            const data = await resp.json();
            
            resBox.style.display = 'block';
            if (data.error) {
                resBox.style.color = '#ff6b6b';
                resBox.textContent = "Error: " + data.error;
            } else {
                resBox.style.color = '#51cf66';
                const table = data.result.map(row => JSON.stringify(row)).join('\n');
                resBox.textContent = `Success! First ${data.result.length} rows preview:\n${table || 'No rows returned.'}`;
            }
        } catch(err) {
            resBox.style.display = 'block';
            resBox.style.color = '#ff6b6b';
            resBox.textContent = "Test failed: " + err.message;
        } finally {
            btn.innerHTML = '<i data-lucide="play" style="width: 12px; height: 12px;"></i> Test';
            lucide.createIcons();
        }
    };
}

document.getElementById('btn-add-sql').onclick = () => addSqlBox('');

// ── Open Modal (for Column Annotation) ──
function openModal(colName) {
    const tableData = currentSchema.tables.find(t => t.name === activeTable);
    if (!tableData) return;
    const col = tableData.columns.find(c => c.name === colName);
    if (!col) return;
    editingCol = col;
    els.modalTitle.textContent = `Column: ${colName}`;
    els.modalSubtitle.textContent = `Table: ${activeTable}`;
    els.editDesc.value = col.description || '';
    els.editValues.value = col.annotations?.values ? JSON.stringify(col.annotations.values, null, 2) : '';

    // Set FROM label
    document.getElementById('relation-from').textContent = `${activeTable}.${colName}`;

    // Use live DOM references for the relation selectors
    const refTableSelect = document.getElementById('edit-ref-table');
    const refColumnSelect = document.getElementById('edit-ref-column');

    // Populate relation column helper
    const updateRefColumns = (tableName, selectedCol = 'id') => {
        refColumnSelect.innerHTML = '';
        const tObj = currentSchema.tables.find(t => t.name === tableName);
        if (tObj) {
            tObj.columns.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.name;
                opt.textContent = c.name;
                refColumnSelect.appendChild(opt);
            });
            refColumnSelect.value = selectedCol;
        } else {
            const opt = document.createElement('option');
            opt.value = 'id';
            opt.textContent = 'id';
            refColumnSelect.appendChild(opt);
        }
    };

    // Table change listener
    refTableSelect.onchange = (e) => updateRefColumns(e.target.value);

    // Populate reference table dropdown with all tables
    refTableSelect.innerHTML = '<option value="">— No Relation —</option>';
    currentSchema.tables.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.name;
        opt.textContent = t.name;
        refTableSelect.appendChild(opt);
    });
    
    // Set current values if any
    let targetCol = 'id';

    if (col.is_foreign_key && col.ref_table) {
        refTableSelect.value = col.ref_table;
        targetCol = col.ref_column || 'id';
    } else if (col.annotations?.ref_table) {
        refTableSelect.value = col.annotations.ref_table;
        targetCol = col.annotations.ref_column || 'id';
    } else {
        refTableSelect.value = '';
    }

    updateRefColumns(refTableSelect.value, targetCol);

    els.editModal.classList.remove('hidden');
    lucide.createIcons();
}

// ── Render ER Diagram (View-Only, Zoom & Pan) ──
async function renderDiagram() {
    if (!currentSchema) return;
    let mermaidCode = 'erDiagram\n';
    currentSchema.tables.forEach(table => {
        table.columns.forEach(col => {
            // Real FK
            if (col.is_foreign_key && col.ref_table) {
                mermaidCode += `    ${table.name} }o--|| ${col.ref_table} : "${col.name}"\n`;
            }
            // Virtual FK from annotations
            else if (col.annotations?.ref_table) {
                mermaidCode += `    ${table.name} }o..|| ${col.annotations.ref_table} : "${col.name}"\n`;
            }
        });
        mermaidCode += `    ${table.name} {\n`;
        table.columns.forEach(col => {
            const cleanType = col.data_type.split('(')[0].toLowerCase();
            const pk = col.is_primary_key ? ' PK' : '';
            const fk = (col.is_foreign_key || col.annotations?.ref_table) ? ' FK' : '';
            mermaidCode += `        ${cleanType} ${col.name}${pk}${fk}\n`;
        });
        mermaidCode += '    }\n';
    });

    const { svg } = await mermaid.render('mermaid-svg', mermaidCode);
    els.mermaidWrapper.innerHTML = svg;
    const svgEl = els.mermaidWrapper.querySelector('svg');
    svgEl.style.width = '100%';
    svgEl.style.height = '100%';
    panZoomInstance = svgPanZoom(svgEl, { zoomEnabled: true, controlIconsEnabled: false, fit: true, center: true });
}

// ── Modal Close/Save ──
els.btnCloseEdit.onclick = () => els.editModal.classList.add('hidden');

els.btnSaveEdit.onclick = async () => {
    const desc = els.editDesc.value;
    let vals = {};
    try { if (els.editValues.value) vals = JSON.parse(els.editValues.value); } catch (e) { alert("Invalid JSON"); return; }
    
    const refTable = document.getElementById('edit-ref-table').value || null;
    const refColumn = document.getElementById('edit-ref-column').value || null;

    const resp = await fetch('/api/save-annotation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_name: currentProjectName,
            table: activeTable,
            column: editingCol.name,
            description: desc,
            values: vals,
            ref_table: refTable,
            ref_column: refColumn
        })
    });
    if (resp.ok) {
        editingCol.description = desc;
        if (!editingCol.annotations) editingCol.annotations = {};
        editingCol.annotations.values = vals;
        editingCol.annotations.ref_table = refTable;
        editingCol.annotations.ref_column = refColumn;
        selectTable(activeTable);
        els.editModal.classList.add('hidden');
        
        // Check for stale exports after change
        checkIfExportsAreStale();
    }
};

// ── Table Description Save ──
els.btnSaveTableDesc.onclick = async () => {
    const desc = els.tableDescInput.value;
    const sqls = [];
    document.querySelectorAll('#sql-boxes-container textarea').forEach(txt => {
        if (txt.value.trim()) sqls.push(txt.value.trim());
    });
    
    document.getElementById('btn-save-table-desc').innerHTML = '<i data-lucide="loader"></i>';
    lucide.createIcons();

    const resp = await fetch('/api/save-table-annotation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: currentProjectName, table: activeTable, description: desc, sql_examples: sqls })
    });
    if (resp.ok) {
        const tableData = currentSchema.tables.find(t => t.name === activeTable);
        tableData.description = desc;
        tableData.sql_examples = sqls;
        
        // Check for stale exports after change
        checkIfExportsAreStale();
        
        alert("Table info & queries saved!");
    }
    document.getElementById('btn-save-table-desc').innerHTML = '<i data-lucide="save"></i>';
    lucide.createIcons();
};

async function checkIfExportsAreStale() {
    if (!currentConnectionPayload || !currentProjectName) return;
    try {
        const res = await fetch('/api/schema-hash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...currentConnectionPayload, project_name: currentProjectName })
        });
        const { schema_hash } = await res.json();

        ['export', 'rag', 'finetune'].forEach(type => {
            const savedHash = sessionStorage.getItem(`last_export_hash_${type}`);
            const badge = document.getElementById(`stale-warning-${type}`);
            if (badge) {
                if (savedHash && savedHash !== schema_hash) {
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        });
    } catch (e) { console.warn('Stale check failed:', e); }
}

// ── Exports (Context, RAG, Fine-Tune) ──
async function handleExport(type, endpoint, ext, mimeType, btnId) {
    if (!currentConnectionPayload) return alert("Please connect to a database first.");
    
    const btn = document.getElementById(btnId);
    const originalHtml = btn.innerHTML;
    btn.textContent = "Exporting...";
    
    try {
        const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...currentConnectionPayload, project_name: currentProjectName })
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        // Store hash for stale detection
        const hash = data.schema_hash || (data.meta ? data.meta.schema_hash : null);
        if (hash) {
            sessionStorage.setItem(`last_export_hash_${type}`, hash);
            const badge = document.getElementById(`stale-warning-${type}`);
            if (badge) badge.style.display = 'none';
        }

        const content = data.content || data.markdown || JSON.stringify(data.json || data.chunks, null, 2);
        
        // Trigger native download
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        const safeName = currentProjectName.replace(/[^a-zA-Z0-9]/g, '');
        a.download = `ai_${type}_${safeName}.${ext}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch(e) {
        alert(type.toUpperCase() + " Export failed: " + e.message);
    } finally {
        btn.innerHTML = originalHtml;
        lucide.createIcons();
    }
}

document.getElementById('btn-export').onclick = () => handleExport('context', '/api/export', 'md', 'text/markdown', 'btn-export');
document.getElementById('btn-export-rag').onclick = () => handleExport('rag', '/api/export-rag', 'json', 'application/json', 'btn-export-rag');
document.getElementById('btn-export-finetune').onclick = () => handleExport('finetune', '/api/export-finetune', 'jsonl', 'application/jsonlines', 'btn-export-finetune');

// ── Connection Tab Switching ──
els.tabBtns.forEach(btn => {
    btn.onclick = () => {
        els.tabBtns.forEach(b => b.classList.remove('active'));
        els.tabContents.forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-content-${btn.dataset.type}`).classList.add('active');
        activeMode = btn.dataset.type;
    };
});

// ── Import Annotations ──
document.getElementById('btn-import-docs').onclick = () => {
    if (!currentProjectName) return alert("Please connect to a project first.");
    document.getElementById('import-file-input').click();
};

document.getElementById('import-file-input').onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
        const content = event.target.result;
        const btn = document.getElementById('btn-import-docs');
        btn.innerHTML = '<i data-lucide="loader"></i> Importing...';
        lucide.createIcons();

        try {
            const resp = await fetch('/api/import-annotations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: currentProjectName, content: content })
            });
            const data = await resp.json();
            if (data.success) {
                alert("Import successful! Please reconnect to see updated annotations.");
                location.reload(); // Refresh to ensure schema is re-enriched
            } else {
                alert("Import failed: " + data.error);
            }
        } catch(err) {
            alert("Error: " + err.message);
        } finally {
            btn.innerHTML = '<i data-lucide="upload"></i> Import Docs';
            lucide.createIcons();
            e.target.value = ''; // Reset input
        }
    };
    reader.readAsText(file);
};
