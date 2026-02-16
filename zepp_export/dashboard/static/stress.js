/**
 * Stress Timeline chart.
 * Renders 5-minute stress readings with colored zones.
 */

let stressChart = null;

function getStressZoneColor(val) {
    if (val <= 25) return '#22c55e';   // relaxed - green
    if (val <= 50) return '#3b82f6';   // normal - blue
    if (val <= 75) return '#f59e0b';   // medium - orange
    return '#ef4444';                   // high - red
}

function renderStressChart(data) {
    const canvas = document.getElementById('chart-stress');

    if (stressChart) {
        stressChart.destroy();
        stressChart = null;
    }

    if (!data || !Array.isArray(data) || data.length === 0) {
        return;
    }

    const dayData = data[0];
    const readings = dayData.readings || [];

    if (readings.length === 0) return;

    const labels = readings.map(r => {
        if (typeof r.time === 'number') {
            const d = new Date(r.time);
            return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        }
        return r.time || '';
    });
    const values = readings.map(r => r.value || 0);

    stressChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Stress',
                data: values,
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                borderWidth: 1.5,
                pointRadius: 0,
                pointHitRadius: 8,
                fill: true,
                tension: 0.3,
                segment: {
                    borderColor: ctx => {
                        const v = ctx.p1.parsed.y;
                        return getStressZoneColor(v);
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
                        label: ctx => {
                            const v = ctx.parsed.y;
                            let zone = 'Relaxed';
                            if (v > 75) zone = 'High';
                            else if (v > 50) zone = 'Medium';
                            else if (v > 25) zone = 'Normal';
                            return `Stress: ${v} (${zone})`;
                        },
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
                    min: 0,
                    max: 100,
                    ticks: {
                        color: '#8b8d97',
                        stepSize: 25,
                        callback: (val) => {
                            const labels = { 0: '0', 25: 'Relaxed', 50: 'Normal', 75: 'Medium', 100: 'High' };
                            return labels[val] || val;
                        },
                    },
                    grid: { color: 'rgba(42, 45, 58, 0.5)' },
                },
            },
        },
    });
}
