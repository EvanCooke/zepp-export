/**
 * Activity Segments chart.
 * Renders walking/running/light activity as a stacked horizontal bar.
 */

let activityChart = null;

const ACTIVITY_COLORS = {
    slow_walking: '#3b82f6',
    fast_walking: '#22c55e',
    running: '#ef4444',
    light_activity: '#f59e0b',
};

const ACTIVITY_LABELS = {
    slow_walking: 'Walking',
    fast_walking: 'Fast Walking',
    running: 'Running',
    light_activity: 'Light Activity',
};

function renderActivityChart(steps) {
    const canvas = document.getElementById('chart-activity');
    const statsEl = document.getElementById('activity-stats');

    if (activityChart) {
        activityChart.destroy();
        activityChart = null;
    }

    statsEl.innerHTML = '';

    if (!steps || !steps.stages || steps.stages.length === 0) {
        statsEl.innerHTML = '<span style="color: var(--text-muted)">No activity data for this date</span>';
        return;
    }

    const totals = {};
    const stepTotals = {};
    steps.stages.forEach(s => {
        const mode = s.mode;
        totals[mode] = (totals[mode] || 0) + (s.end_minute - s.start_minute);
        stepTotals[mode] = (stepTotals[mode] || 0) + (s.steps || 0);
    });

    const modes = Object.keys(totals).sort((a, b) => totals[b] - totals[a]);
    if (modes.length === 0) return;

    const data = modes.map(m => totals[m]);
    const colors = modes.map(m => ACTIVITY_COLORS[m] || '#8b8d97');
    const labels = modes.map(m => ACTIVITY_LABELS[m] || m);

    modes.forEach((m, i) => {
        const mins = totals[m];
        const stps = stepTotals[m] || 0;
        const h = Math.floor(mins / 60);
        const min = mins % 60;
        const timeStr = h > 0 ? `${h}h ${min}m` : `${min}m`;

        const stat = document.createElement('div');
        stat.className = 'sleep-stat';
        stat.innerHTML = `<span class="sleep-dot" style="background: ${colors[i]}"></span> ${labels[i]}: ${timeStr} (${stps.toLocaleString()} steps)`;
        statsEl.appendChild(stat);
    });

    activityChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['Activity'],
            datasets: modes.map((m, i) => ({
                label: labels[i],
                data: [data[i]],
                backgroundColor: colors[i],
                borderRadius: 4,
            })),
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
                            const h = Math.floor(mins / 60);
                            const m = mins % 60;
                            return `${ctx.dataset.label}: ${h > 0 ? h + 'h ' : ''}${m}m`;
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
                    title: { display: true, text: 'Duration', color: '#8b8d97' },
                },
                y: { stacked: true, display: false },
            },
        },
    });
}
