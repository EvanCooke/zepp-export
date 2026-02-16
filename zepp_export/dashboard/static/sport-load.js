/**
 * Sport Load chart.
 * Shows daily and weekly training load with optimal range bands.
 */

let sportLoadChart = null;

function renderSportLoadChart(data) {
    const canvas = document.getElementById('chart-sport-load');

    if (sportLoadChart) {
        sportLoadChart.destroy();
        sportLoadChart = null;
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
        return;
    }

    const labels = data.map(d => d.date || '');
    const weeklyLoad = data.map(d => d.weekly_load);
    const optMin = data.map(d => d.optimal_min);
    const optMax = data.map(d => d.optimal_max);
    const dailyLoad = data.map(d => d.daily_load);

    sportLoadChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Weekly Load',
                    data: weeklyLoad,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHitRadius: 8,
                    tension: 0.3,
                    fill: false,
                },
                {
                    label: 'Optimal Max',
                    data: optMax,
                    borderColor: 'rgba(34, 197, 94, 0.4)',
                    backgroundColor: 'rgba(34, 197, 94, 0.08)',
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    fill: '+1',
                },
                {
                    label: 'Optimal Min',
                    data: optMin,
                    borderColor: 'rgba(34, 197, 94, 0.4)',
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 0,
                    fill: false,
                },
                {
                    label: 'Daily Load',
                    data: dailyLoad,
                    type: 'bar',
                    backgroundColor: 'rgba(99, 102, 241, 0.3)',
                    borderRadius: 4,
                    barPercentage: 0.6,
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
                        pointStyle: 'line',
                        padding: 16,
                        font: { size: 12 },
                        filter: item => item.text !== 'Optimal Min',
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
