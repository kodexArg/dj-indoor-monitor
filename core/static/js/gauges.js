function normalizeTimestamp(isoString) {
    let dateTime = luxon.DateTime.fromISO(isoString, { setZone: true });
    return dateTime.setZone('local').toISO({ suppressMilliseconds: true });
}

async function fetchLatestData() {
    try {
        const resp = await fetch('/api/sensor-data/latest/?seconds=30');
        if (!resp.ok) throw new Error('Network response was not ok');
        const data = await resp.json();
        return data.map(item => ({
            ...item,
            timestamp: normalizeTimestamp(item.timestamp)
        }));
    } catch (error) {
        console.error('Error fetching gauge data:', error);
        return [];
    }
}

async function updateGauges() {
    console.log('Updating gauges...');  // Debug log
    try {
        const data = await fetchLatestData();
        if (!data.length) {
            console.log('No data received');  // Debug log
            return;
        }

        console.log('Data received:', data);  // Debug log

        const latestReadings = {};
        data.forEach(reading => {
            if (!latestReadings[reading.sensor] || 
                reading.timestamp > latestReadings[reading.sensor].timestamp) {
                latestReadings[reading.sensor] = reading;
            }
        });

        Object.entries(latestReadings).forEach(([sensor, reading], idx) => {
            if (reading.t !== undefined) {
                Plotly.restyle('gauges-container', {
                    value: [reading.t]
                }, 2 * idx);
                console.log(`Updated temperature gauge for ${sensor}: ${reading.t.toFixed(1)}°C`);
            }
            if (reading.h !== undefined) {
                Plotly.restyle('gauges-container', {
                    value: [reading.h]
                }, 2 * idx + 1);
                console.log(`Updated humidity gauge for ${sensor}: ${reading.h.toFixed(1)}%`);
            }
        });
    } catch(e) {
        console.error('Gauge update error:', e);
    }
}

console.log('Gauges script loaded');  // Debug log

// Start updates when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('DOM Content Loaded - Starting updates');  // Debug log
        const updateInterval = setInterval(updateGauges, 5000);
        updateGauges();

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                clearInterval(updateInterval);
            }
        });
    });
} else {
    console.log('DOM already loaded - Starting updates immediately');  // Debug log
    const updateInterval = setInterval(updateGauges, 5000);
    updateGauges();

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(updateInterval);
        }
    });
}
