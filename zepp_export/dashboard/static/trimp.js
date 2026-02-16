/**
 * TRIMP (Training Impulse) chart.
 * Shows daily training stress derived from heart rate data.
 */

let trimpChart = null;

function renderTrimpChart(data) {
    const canvas = document.getElementById('chart-trimp');

    if (trimpChart) {
        trimpChart.destroy();
        trimpChart = null;
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
        return;
    }

    const recent = data.slice(-90);

    const labels = recent.map(d => {
        if (d.timestamp) {
            const dt = new Date(d.timestamp);
            return `${dt.getMonth() + 1}/${dt.getDate()}`;
        }
        return '';
    });

    const trimpValues = recent.map(d => d.trimp != null ? Math.round(d.trimp) : null);
    const atlValues = recent.map(d => d.atl != null ? Math.round(d.atl) : null);
    const ctlValues = recent.map(d => d.ctl != null ? Math.round(d.ctl) : null);

    trimpChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'TRIMP',
                    data: trimpValues,
                    backgroundColor: 'rgba(168, 85, 247, 0.5)',
                    borderRadius: 4,
                    barPercentage: 0.7,
                    order: 2,
                },
                {
                    label: 'ATL',
                    data: atlValues,
                    type: 'line',
                    borderColor: '#ef4444',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false,
                    order: 1,
                },
                {
                    label: 'CTL',
                    data: ctlValues,
                    type: 'line',
                    borderColor: '#3b82f6',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false,
                    order: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#8b8d97',
                        usePointStyle: true,
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
                },
            },
            scales: {
                x: {
                    ticks: { color: '#8b8d97', maxTicksLimit: 15 },
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
