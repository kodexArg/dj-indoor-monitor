function normalizeTimestamp(isoString) {
    let dateTime = luxon.DateTime.fromISO(isoString, { setZone: true });
    return dateTime.setZone('local').toISO({ suppressMilliseconds: true });
}

async function fetchLatestData(startDate, metric = 't') {
    const url = new URL(`${window.location.origin}/api/sensor-data/latest/`);
    url.searchParams.set('timestamp', startDate);
    url.searchParams.set('metric', metric);

    try {
        const response = await fetch(url.toString());
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        data.forEach(item => {
            if (item.timestamp) {
                item.timestamp = normalizeTimestamp(item.timestamp);
            }
        });

        return data;
    } catch (error) {
        console.error('Error fetching latest data:', error);
        return [];
    }
}

let autoUpdateInterval;

function setTimeframe(timeframe) {
    const url = new URL(window.location.href);
    url.searchParams.set('timeframe', timeframe);
    window.location.href = url.toString();
}

function setMetric(metric) {
    const url = new URL(window.location.href);
    url.searchParams.set('metric', metric);
    window.location.href = url.toString();
}

function initializeChart(data) {
    const layout = {
        xaxis: {
            rangeslider: { visible: selectedTimeframe !== '5s' }
        }
    };
    Plotly.newPlot('chart', data, layout);
}

function startAutoUpdate() {
    const timeIncrement = 5000;

    autoUpdateInterval = setInterval(async function() {
        const chartDiv = document.getElementById('chart');
        if (!chartDiv.data || chartDiv.data.length <= 0) {
            console.error('No previous data available or data length is invalid');
            return;
        }

        let firstTimestamp, lastTimestamp;
        const xData = chartDiv.data[0].x;
        firstTimestamp = normalizeTimestamp(xData[0]);
        lastTimestamp = normalizeTimestamp(xData[xData.length - 1]);

        const newData = await fetchLatestData(lastTimestamp, metric);
        if (newData.length === 0) return;

        const sensorIndices = {};
        chartDiv.data.forEach((trace, index) => {
            sensorIndices[trace.name] = index;
        });

        const xUpdate = [];
        const yUpdate = [];

        newData.forEach(item => {
            const sensor = item.sensor;
            const index = sensorIndices[sensor];
            if (index !== undefined) {
                if (!xUpdate[index]) {
                    xUpdate[index] = [];
                    yUpdate[index] = [];
                }
                xUpdate[index].push(item.timestamp);
                yUpdate[index].push(item[metric]);
            }
        });

        Plotly.extendTraces('chart', { x: xUpdate, y: yUpdate }, Object.values(sensorIndices).map(Number));

        const newRangeEnd = luxon.DateTime.local();
        const newRangeStart = newRangeEnd.minus({ minutes: 5 });

        const xAxisRange = [
            newRangeStart.toISO({ suppressMilliseconds: true }),
            newRangeEnd.toISO({ suppressMilliseconds: true }),
        ];

        Plotly.relayout('chart', {
            'xaxis.range': xAxisRange,
            'xaxis.rangeslider.visible': false,
        });
    }, timeIncrement);
}

function stopAutoUpdate() {
    clearInterval(autoUpdateInterval);
}

document.addEventListener('DOMContentLoaded', function() {
    if (selectedTimeframe === '5s') {
        startAutoUpdate();
    } else {
        stopAutoUpdate();
    }
});
