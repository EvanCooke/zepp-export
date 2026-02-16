/**
 * Training Load chart.
 * ATL (Acute Training Load) vs CTL (Chronic Training Load) with TSB balance.
 * This is the "free TrainingPeaks" killer feature.
 */

let trainingChart = null;

function renderTrainingLoadChart(data) {
    const canvas = document.getElementById('chart-training');

    if (trainingChart) {
        trainingChart.destroy();
        trainingChart = null;
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
        return;
    }

    // Take the most recent entries (up to 90 days)
    const recent = data.slice(-90);

    const labels = recent.map(d => {
        if (d.timestamp) {
            const dt = new Date(d.timestamp);
            return `${dt.getMonth() + 1}/${dt.getDate()}`;
        }
        return '';
    });

    const atlValues = recent.map(d => d.atl != null ? Math.round(d.atl) : null);
    const ctlValues = recent.map(d => d.ctl != null ? Math.round(d.ctl) : null);
    const tsbValues = recent.map(d => d.tsb != null ? Math.round(d.tsb) : null);

    trainingChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'ATL (Fatigue)',
                    data: atlValues,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: 'CTL (Fitness)',
                    data: ctlValues,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: 'TSB (Form)',
                    data: tsbValues,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.08)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    tension: 0.3,
                    fill: true,
                    borderDash: [4, 4],
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#8b8d97',
                        usePointStyle: true,
                        pointStyle: 'line',
                        padding: 16,
                        font: { size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: '#1a1d27',
                    borderColor: '#2a2d3a',
                    borderWidth: 1,
                    titleColor: '#e4e4e7',
                    bodyColor: '#e4e4e7',
                    callbacks: {
                        label: ctx => {
                            const val = ctx.parsed.y;
                            return `${ctx.dataset.label}: ${val}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: '#8b8d97',
                        maxTicksLimit: 15,
                    },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                },
                y: {
                    ticks: { color: '#8b8d97' },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                },
            },
        },
    });
}
