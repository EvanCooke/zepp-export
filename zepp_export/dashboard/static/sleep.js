/**
 * Sleep Architecture chart.
 * Renders overnight sleep and naps as separate stacked horizontal bars.
 */

let sleepChart = null;

const SLEEP_COLORS = {
    deep: '#6366f1',
    light: '#818cf8',
    rem: '#06b6d4',
    awake: '#f59e0b',
};

const STAGE_ORDER = ['deep', 'light', 'rem', 'awake'];
const STAGE_LABELS = ['Deep', 'Light', 'REM', 'Awake'];

function computeTotals(stages) {
    const totals = { deep: 0, light: 0, rem: 0, awake: 0 };
    if (!stages) return totals;
    stages.forEach(s => {
        const key = s.stage;
        if (key in totals) {
            totals[key] += s.duration_minutes;
        }
    });
    return totals;
}

function formatDuration(mins) {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
}

function renderSleepChart(sleep) {
    const canvas = document.getElementById('chart-sleep');
    const statsEl = document.getElementById('sleep-stats');

    if (sleepChart) {
        sleepChart.destroy();
        sleepChart = null;
    }

    statsEl.innerHTML = '';

    const hasMain = sleep && sleep.stages && sleep.stages.length > 0;
    const hasNaps = sleep && sleep.nap_stages && sleep.nap_stages.length > 0;

    if (!hasMain && !hasNaps) {
        statsEl.innerHTML = '<span style="color: var(--text-muted)">No sleep data for this date</span>';
        return;
    }

    const mainTotals = hasMain ? computeTotals(sleep.stages) : null;
    const napTotals = hasNaps ? computeTotals(sleep.nap_stages) : null;

    const chartLabels = [];
    if (hasMain) chartLabels.push('Overnight');
    if (hasNaps) chartLabels.push('Naps');

    const datasets = STAGE_ORDER.map((k, i) => ({
        label: STAGE_LABELS[i],
        data: [
            ...(hasMain ? [mainTotals[k]] : []),
            ...(hasNaps ? [napTotals[k]] : []),
        ],
        backgroundColor: SLEEP_COLORS[k],
        borderRadius: 4,
    }));

    // Stats beneath chart
    const allTotals = { deep: 0, light: 0, rem: 0, awake: 0 };
    if (mainTotals) STAGE_ORDER.forEach(k => allTotals[k] += mainTotals[k]);
    if (napTotals) STAGE_ORDER.forEach(k => allTotals[k] += napTotals[k]);

    STAGE_ORDER.forEach((k, i) => {
        const mins = allTotals[k];
        if (mins === 0) return;

        const stat = document.createElement('div');
        stat.className = 'sleep-stat';
        stat.innerHTML = `<span class="sleep-dot" style="background: ${SLEEP_COLORS[k]}"></span> ${STAGE_LABELS[i]}: ${formatDuration(mins)}`;
        statsEl.appendChild(stat);
    });

    const totalAll = STAGE_ORDER.reduce((sum, k) => sum + allTotals[k], 0);
    if (totalAll > 0) {
        const totalStat = document.createElement('div');
        totalStat.className = 'sleep-stat';
        totalStat.style.color = 'var(--text-muted)';
        totalStat.textContent = `Total: ${formatDuration(totalAll)}`;
        statsEl.appendChild(totalStat);
    }

    sleepChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: chartLabels,
            datasets: datasets,
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d27',
                    borderColor: '#2a2d3a',
                    borderWidth: 1,
                    titleColor: '#e4e4e7',
                    bodyColor: '#e4e4e7',
                    callbacks: {
                        label: ctx => {
                            const mins = ctx.parsed.x;
                            if (mins === 0) return null;
                            return `${ctx.dataset.label}: ${formatDuration(mins)}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        color: '#8b8d97',
                        callback: val => {
                            const h = Math.floor(val / 60);
                            const m = val % 60;
                            return h > 0 ? `${h}h` : `${m}m`;
                        },
                    },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                    title: {
                        display: true,
                        text: 'Duration',
                        color: '#8b8d97',
                    },
                },
                y: {
                    stacked: true,
                    ticks: { color: '#8b8d97' },
                },
            },
        },
    });
}
