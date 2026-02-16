/**
 * Heart Rate timeline chart.
 * Renders minute-by-minute HR as a line chart with zone-based coloring.
 */

let hrChart = null;

function getHRZoneColor(bpm) {
    if (bpm < 60) return '#3b82f6';   // resting - blue
    if (bpm < 100) return '#22c55e';  // normal - green
    if (bpm < 140) return '#f59e0b';  // elevated - orange
    if (bpm < 170) return '#ef4444';  // high - red
    return '#dc2626';                  // max - dark red
}

function renderHeartRateChart(data) {
    const canvas = document.getElementById('chart-hr');
    const legend = document.getElementById('hr-legend');

    if (hrChart) {
        hrChart.destroy();
        hrChart = null;
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
        legend.textContent = 'No heart rate data for this date';
        return;
    }

    const labels = data.map(r => r.time);
    const values = data.map(r => r.bpm);
    const colors = values.map(v => getHRZoneColor(v));

    const avg = Math.round(values.reduce((a, b) => a + b, 0) / values.length);
    const min = Math.min(...values);
    const max = Math.max(...values);
    legend.textContent = `${data.length} readings \u00B7 avg ${avg} \u00B7 min ${min} \u00B7 max ${max} bpm`;

    hrChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Heart Rate',
                data: values,
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderWidth: 1.5,
                pointRadius: 0,
                pointHitRadius: 8,
                fill: true,
                tension: 0.3,
                segment: {
                    borderColor: ctx => {
                        const v = ctx.p1.parsed.y;
                        return getHRZoneColor(v);
                    },
                },
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1d27',
                    borderColor: '#2a2d3a',
                    borderWidth: 1,
                    titleColor: '#e4e4e7',
                    bodyColor: '#e4e4e7',
                    callbacks: {
                        label: ctx => `${ctx.parsed.y} bpm`,
                    },
                },
            },
            scales: {
                x: {
                    ticks: {
                        color: '#8b8d97',
                        maxTicksLimit: 24,
                        callback: function(val, idx) {
                            const label = this.getLabelForValue(val);
                            return label && label.endsWith(':00') ? label : '';
                        },
                    },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                },
                y: {
                    min: Math.max(30, min - 10),
                    max: max + 10,
                    ticks: { color: '#8b8d97' },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                },
            },
        },
    });
}
