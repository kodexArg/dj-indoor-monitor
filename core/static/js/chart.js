function normalizeTimestamp(isoString) {
    // Convertir el string ISO a DateTime de Luxon
    let dateTime = luxon.DateTime.fromISO(isoString, { setZone: true });

    // Convertir siempre a la zona horaria local y devolver en formato ISO
    return dateTime.setZone('local').toISO({ suppressMilliseconds: true });
}

async function fetchLatestData(startDate, metric = 't') {
    const url = new URL(`${window.location.origin}/api/sensor-data/latest/`);
    url.searchParams.set('timestamp', startDate);
    url.searchParams.set('metric', metric);

    try {
        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();

        // Normalizar los timestamps en los datos recibidos a la zona horaria local
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

function startAutoUpdate() {
    const timeIncrement = 5000; // 5 segundos en milisegundos

    setInterval(async function() {
        const chartDiv = document.getElementById('chart');

        // Verificar si chartDiv.data tiene datos válidos
        if (!chartDiv.data || chartDiv.data.length <= 0) {
            console.error('No previous data available or data length is invalid');
            return;
        }

        // Obtener el primer y último timestamp del gráfico usando normalizeTimestamp
        let firstTimestamp, lastTimestamp;
        const xData = chartDiv.data[0].x;
        firstTimestamp = normalizeTimestamp(xData[0]);
        lastTimestamp = normalizeTimestamp(xData[xData.length - 1]);

        // Obtener nuevos datos desde el último timestamp
        const newData = await fetchLatestData(lastTimestamp, metric);

        if (newData.length === 0) {
            console.log('No new data available');
            return;
        }

        // Preparar arrays x e y para cada traza
        const sensorIndices = {};
        chartDiv.data.forEach((trace, index) => {
            sensorIndices[trace.name] = index;
        });

        const xUpdate = [];
        const yUpdate = [];

        // Organizar newData por sensor y agregar a xUpdate y yUpdate
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

        // Extender las trazas con los nuevos datos
        Plotly.extendTraces('chart', { x: xUpdate, y: yUpdate }, Object.values(sensorIndices).map(Number));

        // Calcular nuevas horas final e inicial de la ventana del gráfico
        const newRangeEnd = luxon.DateTime.local();
        const newRangeStart = newRangeEnd.minus({ minutes: 5 });

        // Establecer el nuevo rango del eje x
        const xAxisRange = [
            newRangeStart.toISO({ suppressMilliseconds: true }),
            newRangeEnd.toISO({ suppressMilliseconds: true }),
        ];

        Plotly.relayout('chart', {
            'xaxis.range': xAxisRange,
            'xaxis.rangeslider.range': xAxisRange,
        });
    }, timeIncrement);
}

// Start the auto-update loop
document.addEventListener('DOMContentLoaded', function() {
    startAutoUpdate();
});
