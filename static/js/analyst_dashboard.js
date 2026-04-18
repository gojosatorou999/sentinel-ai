// ============================================================
// Analyst Dashboard — Full JS (Leaflet maps, Charts, APWRIMS Live Maps,
//                              Risk Graph, WhatsApp Alerts)
// ============================================================

// ========== SECTION 1: Incident/Warning Leaflet Maps ==========
(function () {
    'use strict';

    let hMap, wMap;
    let weatherMarkers = [], hazardMarkers = [], hazardHeatLayer = null;

    function initGodMode() {
        if (typeof DASHBOARD_DATA === 'undefined') {
            console.error('DASHBOARD_DATA not found');
            return;
        }
        setTimeout(initializeMaps, 500);
        setTimeout(initializeCharts, 800);
    }
    
    // Execute immediately safely
    setTimeout(initGodMode, 100);

    function initializeMaps() {
        if (typeof L === 'undefined') { console.error('Leaflet not loaded'); return; }

        try {
            const heatmapEl = document.getElementById('heatmapMap');
            if (heatmapEl) {
                hMap = L.map('heatmapMap').setView([15.9, 79.7], 6);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(hMap);
                setTimeout(() => hMap.invalidateSize(), 200);

                if (DASHBOARD_DATA.reports && DASHBOARD_DATA.reports.length > 0) {
                    const heatPoints = DASHBOARD_DATA.reports.map(r => [r.latitude, r.longitude, r.confidence_score || 0.5]);
                    if (typeof L.heatLayer !== 'undefined') {
                        L.heatLayer(heatPoints, {
                            radius: 35, blur: 15, maxOpacity: 0.8,
                            gradient: { 0.0: '#3b82f6', 0.25: '#06b6d4', 0.5: '#eab308', 0.75: '#f59e0b', 1.0: '#ef4444' }
                        }).addTo(hMap);
                        const bounds = L.latLngBounds(heatPoints.map(p => [p[0], p[1]]));
                        hMap.fitBounds(bounds.pad(0.2));
                    } else {
                        DASHBOARD_DATA.reports.forEach(r => {
                            L.circleMarker([r.latitude, r.longitude], {
                                radius: 8, fillColor: '#ef4444', color: '#fff', weight: 1, fillOpacity: 0.6
                            }).bindPopup(`<b>${r.hazard_type}</b><br>${r.location}`).addTo(hMap);
                        });
                    }
                }
            }

            const warningEl = document.getElementById('warningMap');
            if (warningEl) {
                wMap = L.map('warningMap').setView([15.9, 79.7], 6);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap'
                }).addTo(wMap);
                setTimeout(() => wMap.invalidateSize(), 200);
                updateLiveHazards();
                setInterval(updateLiveHazards, 5000);
            }
        } catch (err) { console.error('Map init error:', err); }
    }

    async function updateLiveHazards() {
        if (!wMap) return;
        try {
            if (hazardHeatLayer) wMap.removeLayer(hazardHeatLayer);
            weatherMarkers.forEach(m => wMap.removeLayer(m));
            hazardMarkers.forEach(m => wMap.removeLayer(m));
            weatherMarkers = []; hazardMarkers = [];

            const [iRes, gRes] = await Promise.all([
                fetch('/api/live_hazard_incidents'),
                fetch('/api/live_govt_hazards')
            ]);
            const incidents   = await iRes.json();
            const govtHazards = await gRes.json();

            if (incidents.incidents && incidents.incidents.length > 0 && typeof L.heatLayer !== 'undefined') {
                const pts = incidents.incidents.map(i => [i.latitude, i.longitude, i.confidence_score || 0.5]);
                hazardHeatLayer = L.heatLayer(pts, {
                    radius: 35, blur: 20, maxOpacity: 0.8,
                    gradient: { 0.0: '#3b82f6', 0.25: '#06b6d4', 0.5: '#eab308', 0.75: '#f59e0b', 1.0: '#ef4444' }
                }).addTo(wMap);
            }

            if (govtHazards.hazards && govtHazards.hazards.length > 0) {
                govtHazards.hazards.forEach(h => {
                    const color = h.severity === 'critical' ? '#dc2626' :
                                  h.severity === 'high' ? '#ea580c' :
                                  h.severity === 'medium' ? '#f59e0b' : '#06b6d4';
                    const m = L.circle([h.latitude, h.longitude], {
                        radius: h.radius * 1000, color, fillColor: color,
                        fillOpacity: 0.15, weight: 3, dashArray: '10,5'
                    }).bindPopup(`<b>⚠️ ${h.type}</b><br>Severity: <b>${h.severity.toUpperCase()}</b><br>${h.description}`);
                    m.addTo(wMap);
                    hazardMarkers.push(m);
                });
            }
        } catch (err) { console.error('Hazard update error:', err); }
    }

    function initializeCharts() {
        if (typeof Chart === 'undefined') { console.error('Chart.js not loaded'); return; }

        try {
            const hazardEl = document.getElementById('hazardDistributionChart');
            if (hazardEl && DASHBOARD_DATA.hazards) {
                new Chart(hazardEl, {
                    type: 'pie',
                    data: { labels: Object.keys(DASHBOARD_DATA.hazards), datasets: [{
                        data: Object.values(DASHBOARD_DATA.hazards),
                        backgroundColor: ['#0ea5e9','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6']
                    }] },
                    options: { responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom', labels: { color: '#fff', font: { size: 10 } } } } }
                });
            }

            const timelineEl = document.getElementById('reportsTimelineChart');
            if (timelineEl && DASHBOARD_DATA.timeline) {
                new Chart(timelineEl, {
                    type: 'line',
                    data: { labels: DASHBOARD_DATA.timeline.labels, datasets: [{
                        data: DASHBOARD_DATA.timeline.data, borderColor: '#0ea5e9',
                        backgroundColor: 'rgba(14,165,233,0.2)', fill: true, tension: 0.4
                    }] },
                    options: { responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#fff' }, grid: { display: false } },
                            y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                        } }
                });
            }

            const userEl = document.getElementById('userEngagementChart');
            if (userEl && DASHBOARD_DATA.users) {
                new Chart(userEl, {
                    type: 'bar',
                    data: { labels: ['Total Users', 'Active Users'],
                        datasets: [{ data: [DASHBOARD_DATA.users.total, DASHBOARD_DATA.users.active],
                            backgroundColor: ['#0ea5e9', '#10b981'] }] },
                    options: { responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { color: '#fff' }, grid: { display: false } },
                            y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                        } }
                });
            }
        } catch (err) { console.error('Chart init error:', err); }
    }
})();


// ========== SECTION 2: AP District Intelligence Maps (Real Leaflet) ==========
(function () {
    'use strict';

    function rainfallColor(mm) {
        if (mm >= 60) return '#1e3a8a';
        if (mm >= 30) return '#2563eb';
        if (mm >= 10) return '#3b82f6';
        if (mm >=  2) return '#93c5fd';
        return '#dbeafe';
    }
    function soilColor(pct) {
        if (pct >= 80) return '#14532d';
        if (pct >= 60) return '#15803d';
        if (pct >= 40) return '#22c55e';
        if (pct >= 20) return '#86efac';
        return '#dcfce7';
    }
    function reservoirColor(pct) {
        if (pct >= 80) return '#92400e';
        if (pct >= 60) return '#b45309';
        if (pct >= 40) return '#f59e0b';
        if (pct >= 20) return '#fcd34d';
        return '#fef9c3';
    }
    function dynRadius(val, max) {
        return Math.max(18000, Math.min(65000, 18000 + (val / Math.max(max, 1)) * 47000));
    }

    let _districtData = null;
    const _maps  = {};
    const _inited = {};

    function buildMap(mapType, data) {
        const el = document.getElementById('apwrimsMap-' + mapType);
        if (!el) return;

        // Destroy old map instance
        if (_maps[mapType]) { try { _maps[mapType].remove(); } catch(e) {} delete _maps[mapType]; }

        // Ensure the div has height before Leaflet touches it
        el.style.height = '500px';

        const map = L.map(el, { scrollWheelZoom: false, zoomControl: true }).setView([15.5, 79.5], 7);
        _maps[mapType] = map;

        // OpenStreetMap tiles — no retina param, always works
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);

        const getValue = d =>
            mapType === 'rainfall' ? d.rainfall : mapType === 'soil' ? d.soil_moisture : d.reservoir_level;
        const getColor = v =>
            mapType === 'rainfall' ? rainfallColor(v) : mapType === 'soil' ? soilColor(v) : reservoirColor(v);
        const unit  = mapType === 'rainfall' ? 'mm' : '%';
        const lbl   = mapType === 'rainfall' ? 'Rainfall' : mapType === 'soil' ? 'Soil Moisture' : 'Reservoir Level';
        const maxVal = Math.max(...data.map(getValue), 1);

        data.forEach(function(d) {
            const val   = getValue(d);
            const color = getColor(val);

            L.circle([d.lat, d.lon], {
                radius: dynRadius(val, maxVal),
                color: color, fillColor: color, fillOpacity: 0.65, weight: 2
            }).bindPopup(
                '<div style="font-family:system-ui,sans-serif;min-width:170px;font-size:13px">' +
                '<b style="font-size:14px">📍 ' + d.name + '</b>' +
                '<hr style="margin:5px 0;border-color:#ccc">' +
                '<span style="color:#1d4ed8;font-weight:700">' + lbl + ': ' + val + ' ' + unit + '</span><br>' +
                '🌡️ Temp: ' + d.temperature + '°C<br>' +
                '💨 Wind: ' + d.windspeed + ' km/h<br>' +
                '🌧️ Rainfall: ' + d.rainfall + ' mm<br>' +
                '🌱 Soil: ' + d.soil_moisture + '%<br>' +
                '💧 Reservoir: ' + d.reservoir_level + '%</div>'
            ).addTo(map);

            L.marker([d.lat, d.lon], {
                icon: L.divIcon({
                    className: '',
                    html: '<div style="pointer-events:none;text-align:center;white-space:nowrap">' +
                          '<span style="color:#111;font-weight:700;font-size:10px;background:rgba(255,255,255,.75);padding:1px 4px;border-radius:3px">' + d.name + '</span><br>' +
                          '<span style="color:#b45309;font-weight:700;font-size:10px">' + val + unit + '</span></div>',
                    iconAnchor: [28, -4]
                }),
                interactive: false
            }).addTo(map);
        });

        // Colour legend
        const legend = L.control({ position: 'bottomright' });
        legend.onAdd = function() {
            const div = L.DomUtil.create('div');
            div.style.cssText = 'background:rgba(255,255,255,.92);color:#111;border:1px solid #ccc;border-radius:8px;padding:8px 12px;font-size:11px;font-family:system-ui,sans-serif;min-width:130px;';
            var rows;
            if (mapType === 'rainfall') {
                rows = [['#1e3a8a','≥60mm Extreme'],['#2563eb','30–60mm Heavy'],['#3b82f6','10–30mm Moderate'],['#93c5fd','2–10mm Light'],['#dbeafe','&lt;2mm Trace']];
                div.innerHTML = '<b>🌧️ Rainfall (mm)</b><br>' + rows.map(function(r){return '<div style="display:flex;align-items:center;gap:5px;margin:2px 0"><div style="width:11px;height:11px;border-radius:50%;background:'+r[0]+'"></div>'+r[1]+'</div>';}).join('');
            } else if (mapType === 'soil') {
                rows = [['#14532d','≥80% Saturated'],['#15803d','60–80% High'],['#22c55e','40–60% Medium'],['#86efac','20–40% Low'],['#dcfce7','&lt;20% Dry']];
                div.innerHTML = '<b>🌱 Soil Moisture (%)</b><br>' + rows.map(function(r){return '<div style="display:flex;align-items:center;gap:5px;margin:2px 0"><div style="width:11px;height:11px;border-radius:50%;background:'+r[0]+'"></div>'+r[1]+'</div>';}).join('');
            } else {
                rows = [['#92400e','≥80% Overflow Risk'],['#b45309','60–80% High'],['#f59e0b','40–60% Medium'],['#fcd34d','20–40% Low'],['#fef9c3','&lt;20% Minimal']];
                div.innerHTML = '<b>💧 Reservoir Level (%)</b><br>' + rows.map(function(r){return '<div style="display:flex;align-items:center;gap:5px;margin:2px 0"><div style="width:11px;height:11px;border-radius:50%;background:'+r[0]+'"></div>'+r[1]+'</div>';}).join('');
            }
            return div;
        };
        legend.addTo(map);

        // Force redraw — Leaflet needs this after the tab pane becomes visible
        setTimeout(function() { map.invalidateSize(); }, 200);
        setTimeout(function() { map.invalidateSize(); }, 600);
    }

    async function fetchAndRender() {
        try {
            var res  = await fetch('/api/ap_district_map_data');
            var json = await res.json();
            if (!json.districts || json.districts.length === 0) throw new Error('Empty data');
            _districtData = json.districts;
            buildMap('rainfall', json.districts);
            _inited['rainfall'] = true;
        } catch(err) {
            console.error('APWRIMS fetch error:', err);
        }
    }

    window.apwrimsForceRefresh = function() {
        _districtData = null;
        Object.keys(_inited).forEach(function(k){ _inited[k] = false; });
        fetchAndRender();
    };

    function initApwrims() {
        // Fetch immediately — parallel backend, fast response
        fetchAndRender();

        document.querySelectorAll('#apwrimsTabs .nav-link').forEach(function(tab) {
            tab.addEventListener('shown.bs.tab', function() {
                var mapType = tab.dataset.maptype;
                if (!_inited[mapType] && _districtData) {
                    buildMap(mapType, _districtData);
                    _inited[mapType] = true;
                } else if (_maps[mapType]) {
                    setTimeout(function(){ _maps[mapType].invalidateSize(); }, 100);
                }
            });
        });
    }

    setTimeout(initApwrims, 200);
})();


// ========== SECTION 3: District Disaster Risk Probability Graph ==========
let _riskChart = null;

window.loadRiskData = async function () {
    const spinner    = document.getElementById('riskSpinner');
    const chartWrap  = document.getElementById('riskChartWrapper');
    const tableWrap  = document.getElementById('riskTableWrapper');
    const lastUpdEl  = document.getElementById('riskLastUpdated');
    const refreshBtn = document.getElementById('riskRefreshBtn');

    if (!spinner) return;
    spinner.style.display  = 'block';
    if (chartWrap)  chartWrap.style.display  = 'none';
    if (tableWrap)  tableWrap.style.display  = 'none';
    if (refreshBtn) refreshBtn.disabled = true;

    try {
        const res  = await fetch('/api/ap_district_risk_scores');
        const json = await res.json();
        if (!res.ok || !json.districts || json.districts.length === 0)
            throw new Error(json.error || 'No risk data returned');

        const districts = json.districts; // descending by score
        const labels = districts.map(d => d.name);
        const scores = districts.map(d => d.risk_score);
        const colors = districts.map(d => d.color);

        const canvas = document.getElementById('riskBarChart');
        if (canvas && typeof Chart !== 'undefined') {
            if (_riskChart) { _riskChart.destroy(); _riskChart = null; }
            _riskChart = new Chart(canvas, {
                type: 'bar',
                data: { labels, datasets: [{
                    label: 'Risk Score (0–100)',
                    data: scores,
                    backgroundColor: colors,
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 18,
                }] },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15,23,42,0.95)',
                            borderColor: 'rgba(255,255,255,0.15)',
                            borderWidth: 1,
                            titleColor: '#e5e7eb',
                            bodyColor: '#9ca3af',
                            callbacks: {
                                label: ctx => `  Score: ${ctx.parsed.x}/100`,
                                afterBody: (items) => {
                                    const d = districts[items[0].dataIndex];
                                    return [
                                        `  Risk Level: ${d.risk_level}`,
                                        `  Primary Hazard: ${d.primary_hazard}`,
                                        `  Rainfall: ${d.parameters.rainfall} mm`,
                                        `  Wind: ${d.parameters.windspeed} km/h`,
                                        `  Soil Moisture: ${d.parameters.soil_moisture}%`,
                                        `  Temperature: ${d.parameters.temperature}°C`,
                                        `  Reservoir Level: ${d.parameters.reservoir_level}%`,
                                    ];
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            min: 0, max: 100,
                            ticks: { color: '#94a3b8', callback: v => v + '%' },
                            grid: { color: 'rgba(255,255,255,0.06)' }
                        },
                        y: {
                            ticks: { color: '#e5e7eb', font: { size: 11 } },
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        const tbody = document.getElementById('riskTableBody');
        if (tbody) {
            const lc = { 'High Risk': '#ef4444', 'Moderate Risk': '#f97316', 'Low Risk': '#eab308', 'Minimal Risk': '#22c55e' };
            tbody.innerHTML = districts.map(d => {
                const c = lc[d.risk_level] || '#94a3b8';
                return `<tr>
                    <td class="fw-bold">${d.name}</td>
                    <td><strong style="color:${d.color};font-size:15px">${d.risk_score}</strong></td>
                    <td><span class="risk-badge" style="background:${c}22;color:${c};border:1px solid ${c}55">${d.risk_level}</span></td>
                    <td>${d.primary_hazard}</td>
                    <td>${d.parameters.rainfall} mm</td>
                    <td>${d.parameters.windspeed} km/h</td>
                    <td>${d.parameters.soil_moisture}%</td>
                    <td>${d.parameters.temperature}°C</td>
                    <td>${d.parameters.reservoir_level}%</td>
                </tr>`;
            }).join('');
        }

        if (chartWrap) chartWrap.style.display = 'block';
        if (tableWrap) tableWrap.style.display  = 'block';
        if (lastUpdEl && json.last_updated) {
            const ts = new Date(json.last_updated);
            lastUpdEl.textContent = `Last updated: ${ts.toLocaleTimeString()}${json.cached ? ' (cached)' : ' (live)'}`;
        }

    } catch (err) {
        console.error('Risk data load error:', err);
        if (lastUpdEl) lastUpdEl.textContent = '⚠️ Failed to load risk data: ' + err.message;
    } finally {
        if (spinner)    spinner.style.display = 'none';
        if (refreshBtn) refreshBtn.disabled = false;
    }
};

function initRiskAndWhatsApp() {
    setTimeout(window.loadRiskData, 1500);
    setInterval(window.loadRiskData, 30 * 60 * 1000);

    const alertTypeEl = document.getElementById('waAlertType');
    const messageEl   = document.getElementById('waMessage');
    if (alertTypeEl && messageEl) {
        const defaults = {
            'Flood Warning':           'Severe flooding risk detected in your district. Evacuate low-lying areas immediately and move to higher ground. Avoid crossing flooded roads.',
            'Cyclone Alert':           'A tropical cyclone is approaching your district. Secure property, stay indoors, and follow evacuation instructions from local authorities.',
            'Heavy Rainfall Advisory': 'Heavy to very heavy rainfall is expected in your district. Avoid waterlogged areas and do not venture near streams or rivers.',
            'Reservoir Overflow':      'A reservoir in your district is nearing overflow capacity. Downstream areas must evacuate immediately. Follow official instructions.',
            'General Advisory':        'An official advisory has been issued for your district. Stay alert and follow instructions from local disaster management authorities.',
        };
        messageEl.value = defaults[alertTypeEl.value] || '';
        alertTypeEl.addEventListener('change', () => { messageEl.value = defaults[alertTypeEl.value] || ''; });
    }
}

setTimeout(initRiskAndWhatsApp, 300);

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast-custom';
    toast.innerHTML = `<strong>${type === 'success' ? '✅' : '❌'}</strong> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0'; toast.style.transition = 'opacity .4s';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

window.sendDistrictAlert = async function () {
    const distSel  = document.getElementById('waDistrictSelect');
    const alertEl  = document.getElementById('waAlertType');
    const msgEl    = document.getElementById('waMessage');
    const sendBtn  = document.getElementById('waSendBtn');

    const selectedDistricts = distSel ? Array.from(distSel.selectedOptions).map(o => o.value) : [];
    const alertType = alertEl ? alertEl.value : 'General Advisory';
    const message   = msgEl   ? msgEl.value.trim() : '';

    if (!selectedDistricts.length) { showToast('Please select at least one district.', 'error'); return; }
    if (!message)                  { showToast('Please enter a message.', 'error'); return; }

    if (sendBtn) { sendBtn.disabled = true; sendBtn.textContent = '⏳ Sending…'; }

    try {
        const res  = await fetch('/api/send_district_whatsapp_alert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ districts: selectedDistricts, alert_type: alertType, message })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(
                `Alert sent to <strong>${data.sent}</strong> user(s) across <strong>${data.districts_targeted.length}</strong> district(s).` +
                (data.failed > 0 ? ` (${data.failed} failed)` : ''),
                'success'
            );
        } else {
            showToast(`Error: ${data.error || 'Send failed'}`, 'error');
        }
    } catch (err) {
        showToast(`Network error: ${err.message}`, 'error');
    } finally {
        if (sendBtn) { sendBtn.disabled = false; sendBtn.textContent = '🚨 Send WhatsApp Alert'; }
    }
};
