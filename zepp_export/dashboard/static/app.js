/**
 * zepp-export dashboard -- main app logic.
 * Handles date navigation, data fetching, summary cards, and CSV downloads.
 */

const API = '';  // same-origin

let currentDate = new Date();
currentDate.setHours(0, 0, 0, 0);

// Cached data for CSV downloads
let cachedData = {};

const datePicker = document.getElementById('date-picker');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnToday = document.getElementById('btn-today');
const loadingOverlay = document.getElementById('loading-overlay');
const syncBanner = document.getElementById('sync-banner');

function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function showLoading() { loadingOverlay.classList.remove('hidden'); }
function hideLoading() { loadingOverlay.classList.add('hidden'); }

function setDate(d) {
    currentDate = d;
    datePicker.value = formatDate(d);
    loadAllData();
}

btnPrev.addEventListener('click', () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() - 1);
    setDate(d);
});

btnNext.addEventListener('click', () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + 1);
    setDate(d);
});

btnToday.addEventListener('click', () => setDate(new Date()));

datePicker.addEventListener('change', () => {
    const parts = datePicker.value.split('-');
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    setDate(d);
});

async function fetchJSON(url) {
    try {
        const resp = await fetch(url);
        if (!resp.ok) return null;
        return await resp.json();
    } catch (e) {
        console.error('Fetch error:', url, e);
        return null;
    }
}

// ------------------------------------------------------------------
// Summary cards
// ------------------------------------------------------------------

function updatePrimaryCards(hr, sleep, steps, stress) {
    const valSteps = document.getElementById('val-steps');
    const detailSteps = document.getElementById('detail-steps');
    const valRhr = document.getElementById('val-rhr');
    const valSleep = document.getElementById('val-sleep');
    const detailSleep = document.getElementById('detail-sleep');
    const valStress = document.getElementById('val-stress');
    const detailStress = document.getElementById('detail-stress');

    if (steps && steps.total_steps != null) {
        valSteps.textContent = steps.total_steps.toLocaleString();
        const distKm = ((steps.distance_meters || 0) / 1000).toFixed(1);
        detailSteps.textContent = `${distKm} km \u00B7 ${steps.calories || 0} cal`;
    } else {
        valSteps.textContent = '--';
        detailSteps.textContent = '';
    }

    if (sleep && sleep.resting_hr) {
        valRhr.textContent = sleep.resting_hr;
    } else {
        valRhr.textContent = '--';
    }

    if (sleep && (sleep.sleep_score || sleep.duration_minutes)) {
        valSleep.textContent = sleep.sleep_score || '--';
        const totalMin = sleep.duration_minutes || 0;
        const h = Math.floor(totalMin / 60);
        const m = totalMin % 60;
        detailSleep.textContent = totalMin > 0 ? `${h}h ${m}m total` : '';
    } else {
        valSleep.textContent = '--';
        detailSleep.textContent = '';
    }

    if (stress && stress.avg != null) {
        valStress.textContent = stress.avg;
        const zones = stress.zones || {};
        detailStress.textContent = `${zones.relaxed || 0}% relaxed`;
    } else {
        valStress.textContent = '--';
        detailStress.textContent = '';
    }
}

function updateSecondaryCards(hr, sleep, steps, training) {
    // Calories
    const valCal = document.getElementById('val-calories');
    valCal.textContent = (steps && steps.calories) ? steps.calories.toLocaleString() : '--';

    // Distance
    const valDist = document.getElementById('val-distance');
    valDist.textContent = (steps && steps.distance_meters)
        ? ((steps.distance_meters / 1000).toFixed(1))
        : '--';

    // Deep Sleep
    const valDeep = document.getElementById('val-deep');
    const unitDeep = document.getElementById('unit-deep');
    if (sleep && sleep.deep_minutes) {
        const dm = sleep.deep_minutes;
        if (dm >= 60) {
            valDeep.textContent = `${Math.floor(dm / 60)}h ${dm % 60}`;
            unitDeep.textContent = 'min';
        } else {
            valDeep.textContent = dm;
            unitDeep.textContent = 'min';
        }
    } else {
        valDeep.textContent = '--';
        unitDeep.textContent = 'min';
    }

    // Max HR
    const valMaxHr = document.getElementById('val-maxhr');
    if (hr && Array.isArray(hr) && hr.length > 0) {
        valMaxHr.textContent = Math.max(...hr.map(r => r.bpm));
    } else {
        valMaxHr.textContent = '--';
    }

    // Step Goal
    const valGoal = document.getElementById('val-goal');
    const unitGoal = document.getElementById('unit-goal');
    if (steps && steps.goal && steps.total_steps != null) {
        const pct = Math.round((steps.total_steps / steps.goal) * 100);
        valGoal.textContent = `${pct}%`;
        unitGoal.textContent = `${steps.total_steps.toLocaleString()} / ${steps.goal.toLocaleString()}`;
    } else {
        valGoal.textContent = '--';
        unitGoal.textContent = '';
    }

    // Recovery
    const valRecovery = document.getElementById('val-recovery');
    const unitRecovery = document.getElementById('unit-recovery');
    if (training && Array.isArray(training) && training.length > 0) {
        const latest = training[training.length - 1];
        if (latest.recovery_factor != null) {
            valRecovery.textContent = latest.recovery_factor;
            unitRecovery.textContent = '';
        } else if (latest.tsb != null) {
            valRecovery.textContent = Math.round(latest.tsb);
            unitRecovery.textContent = 'TSB';
        } else {
            valRecovery.textContent = '--';
            unitRecovery.textContent = '';
        }
    } else {
        valRecovery.textContent = '--';
        unitRecovery.textContent = '';
    }
}

// ------------------------------------------------------------------
// Sync banner
// ------------------------------------------------------------------

function updateSyncBanner(dateStr, hr, sleep, steps, stress, training, sport, phn) {
    const metrics = [
        { name: 'Heart Rate', ok: Array.isArray(hr) && hr.length > 0 },
        { name: 'Steps', ok: steps && steps.total_steps != null && steps.total_steps > 0 },
        { name: 'Calories', ok: steps && steps.calories != null && steps.calories > 0 },
        { name: 'Sleep Score', ok: sleep && sleep.sleep_score != null && sleep.sleep_score > 0 },
        { name: 'Resting HR', ok: sleep && sleep.resting_hr != null && sleep.resting_hr > 0 },
        { name: 'Sleep Stages', ok: sleep && (
            (sleep.stages && sleep.stages.length > 0) ||
            (sleep.nap_stages && sleep.nap_stages.length > 0)
        )},
        { name: 'Deep Sleep', ok: sleep && sleep.deep_minutes != null && sleep.deep_minutes > 0 },
        { name: 'Stress', ok: Array.isArray(stress) && stress.length > 0 },
        { name: 'Activity', ok: steps && steps.stages && steps.stages.length > 0 },
        { name: 'Training Load', ok: Array.isArray(training) && training.length > 0 },
        { name: 'Sport Load', ok: Array.isArray(sport) && sport.length > 0 },
        { name: 'TRIMP', ok: Array.isArray(phn) && phn.length > 0 },
    ];

    const available = metrics.filter(m => m.ok).length;
    const missing = metrics.filter(m => !m.ok);
    const today = formatDate(new Date());
    const isToday = dateStr === today;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    if (available === metrics.length) {
        syncBanner.classList.remove('hidden');
        syncBanner.innerHTML = `
            <span class="sync-text"><span class="sync-dot complete"></span> All ${metrics.length} metrics available</span>
            <span class="sync-meta">Fetched at ${timeStr}</span>
        `;
    } else if (available === 0) {
        syncBanner.classList.remove('hidden');
        const hint = isToday
            ? 'Open the Zepp app and sync your strap to populate today\'s data.'
            : 'This date may not have been synced yet. Try opening the Zepp app.';
        syncBanner.innerHTML = `
            <span class="sync-text"><span class="sync-dot"></span> No data available &mdash; ${hint}</span>
            <span class="sync-meta">Checked at ${timeStr}</span>
        `;
    } else {
        syncBanner.classList.remove('hidden');
        const missingNames = missing.map(m => m.name).join(', ');
        const hint = isToday
            ? 'Today\'s data updates as your Zepp app syncs.'
            : 'Some metrics may need more time to process, or may not exist for this date.';
        syncBanner.innerHTML = `
            <span class="sync-text"><span class="sync-dot"></span> ${available}/${metrics.length} metrics &mdash; missing: ${missingNames}</span>
            <span class="sync-meta">${hint} &middot; ${timeStr}</span>
        `;
    }
}

// ------------------------------------------------------------------
// CSV Downloads
// ------------------------------------------------------------------

function downloadCSV(filename, csvContent) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function generateSummaryCSV() {
    const d = cachedData;
    const dateStr = formatDate(currentDate);
    const hr = d.hr || [];
    const sleep = d.sleep || {};
    const steps = d.steps || {};
    const stress = d.stress;
    const stressDay = Array.isArray(stress) && stress.length > 0 ? stress[0] : {};

    const headers = [
        'date', 'total_steps', 'distance_meters', 'calories', 'step_goal',
        'resting_hr', 'sleep_score', 'sleep_duration_min', 'deep_sleep_min', 'light_sleep_min',
        'hr_readings', 'hr_avg', 'hr_min', 'hr_max',
        'avg_stress', 'max_stress', 'relaxed_pct', 'normal_pct', 'medium_pct', 'high_pct',
    ];

    const bpms = hr.map(r => r.bpm);
    const zones = stressDay.zone_percentages || {};

    const row = [
        dateStr,
        steps.total_steps ?? '',
        steps.distance_meters ?? '',
        steps.calories ?? '',
        steps.goal ?? '',
        sleep.resting_hr ?? '',
        sleep.sleep_score ?? '',
        sleep.duration_minutes ?? '',
        sleep.deep_minutes ?? '',
        sleep.light_minutes ?? '',
        bpms.length,
        bpms.length > 0 ? Math.round(bpms.reduce((a, b) => a + b, 0) / bpms.length) : '',
        bpms.length > 0 ? Math.min(...bpms) : '',
        bpms.length > 0 ? Math.max(...bpms) : '',
        stressDay.avg_stress ?? '',
        stressDay.max_stress ?? '',
        zones.relaxed ?? '',
        zones.normal ?? '',
        zones.medium ?? '',
        zones.high ?? '',
    ];

    return headers.join(',') + '\n' + row.join(',') + '\n';
}

function generateRawCSV() {
    const d = cachedData;
    const dateStr = formatDate(currentDate);
    const rows = [];
    const headers = ['date', 'type', 'time', 'value', 'unit'];
    rows.push(headers.join(','));

    // Heart rate readings
    if (d.hr && Array.isArray(d.hr)) {
        d.hr.forEach(r => {
            rows.push([dateStr, 'heart_rate', r.time, r.bpm, 'bpm'].join(','));
        });
    }

    // Stress readings
    if (d.stress && Array.isArray(d.stress) && d.stress.length > 0) {
        const readings = d.stress[0].readings || [];
        readings.forEach(r => {
            let timeStr = '';
            if (typeof r.time === 'number') {
                const dt = new Date(r.time);
                timeStr = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
            } else {
                timeStr = r.time || '';
            }
            rows.push([dateStr, 'stress', timeStr, r.value, 'stress_level'].join(','));
        });
    }

    // Sleep stages
    if (d.sleep) {
        const allStages = [
            ...(d.sleep.stages || []).map(s => ({ ...s, source: 'overnight' })),
            ...(d.sleep.nap_stages || []).map(s => ({ ...s, source: 'nap' })),
        ];
        allStages.forEach(s => {
            rows.push([dateStr, `sleep_${s.stage}`, `min ${s.start_minute}-${s.end_minute}`, s.duration_minutes, `minutes (${s.source})`].join(','));
        });
    }

    // Steps summary
    if (d.steps && d.steps.total_steps != null) {
        rows.push([dateStr, 'steps', '', d.steps.total_steps, 'steps'].join(','));
        rows.push([dateStr, 'distance', '', d.steps.distance_meters, 'meters'].join(','));
        rows.push([dateStr, 'calories', '', d.steps.calories, 'kcal'].join(','));
    }

    // Activity stages
    if (d.steps && d.steps.stages) {
        d.steps.stages.forEach(s => {
            rows.push([dateStr, `activity_${s.mode}`, `min ${s.start_minute}-${s.end_minute}`, s.steps, 'steps'].join(','));
        });
    }

    return rows.join('\n') + '\n';
}

document.getElementById('btn-dl-summary').addEventListener('click', () => {
    const dateStr = formatDate(currentDate);
    downloadCSV(`zepp_summary_${dateStr}.csv`, generateSummaryCSV());
});

document.getElementById('btn-dl-raw').addEventListener('click', () => {
    const dateStr = formatDate(currentDate);
    downloadCSV(`zepp_raw_${dateStr}.csv`, generateRawCSV());
});

// ------------------------------------------------------------------
// Data loading
// ------------------------------------------------------------------

async function loadAllData() {
    const dateStr = formatDate(currentDate);
    showLoading();

    try {
        const [hr, sleep, steps, stressData, trainingData, sportData, phnData] = await Promise.all([
            fetchJSON(`${API}/api/heart-rate/${dateStr}`),
            fetchJSON(`${API}/api/sleep/${dateStr}`),
            fetchJSON(`${API}/api/steps/${dateStr}`),
            fetchJSON(`${API}/api/stress/${dateStr}`),
            fetchJSON(`${API}/api/training-load`),
            fetchJSON(`${API}/api/sport-load/${dateStr}`),
            fetchJSON(`${API}/api/phn/${dateStr}`),
        ]);

        // Cache for CSV downloads
        cachedData = { hr, sleep, steps, stress: stressData, training: trainingData, sport: sportData, phn: phnData };

        const stress = Array.isArray(stressData) && stressData.length > 0 ? {
            avg: stressData[0].avg_stress,
            max: stressData[0].max_stress,
            zones: stressData[0].zone_percentages,
            readings: stressData[0].readings || [],
        } : null;

        updatePrimaryCards(hr, sleep, steps, stress);
        updateSecondaryCards(hr, sleep, steps, trainingData);
        updateSyncBanner(dateStr, hr, sleep, steps, stressData, trainingData, sportData, phnData);

        try { renderHeartRateChart(hr); } catch (e) { console.error('HR chart error:', e); }
        try { renderSleepChart(sleep); } catch (e) { console.error('Sleep chart error:', e); }
        try { renderStressChart(stressData); } catch (e) { console.error('Stress chart error:', e); }
        try { renderActivityChart(steps); } catch (e) { console.error('Activity chart error:', e); }
        try { renderTrainingLoadChart(trainingData); } catch (e) { console.error('Training chart error:', e); }
        try { renderSportLoadChart(sportData); } catch (e) { console.error('Sport load chart error:', e); }
        try { renderTrimpChart(phnData); } catch (e) { console.error('TRIMP chart error:', e); }
    } catch (e) {
        console.error('Failed to load data:', e);
    } finally {
        hideLoading();
    }
}

// Initialize
datePicker.value = formatDate(currentDate);
loadAllData();
