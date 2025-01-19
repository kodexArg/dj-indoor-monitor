function normalizeTimestamp(isoString) {
    let dateTime = luxon.DateTime.fromISO(isoString, { setZone: true });
    return dateTime.setZone('local').toLocaleString(luxon.DateTime.DATETIME_MED);
}

async function fetchLatestData(metric = 't') {
    const url = new URL(`${window.location.origin}/api/sensor-data/latest/`);
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

function update_debug_info() {
    fetchLatestData().then(data => {
        if (data.length > 0) {
            document.getElementById('last-reading').textContent = `${data[0].t}°C`;
        }
    });
}

function startAutoUpdate() {
    autoUpdateInterval = setInterval(() => {
        update_debug_info();
    }, 5000);
}

function stopAutoUpdate() {
    if (autoUpdateInterval) {
        clearInterval(autoUpdateInterval);
        autoUpdateInterval = null;
    }
}

let autoUpdateInterval;

document.addEventListener('DOMContentLoaded', function() {
    if (typeof online !== 'undefined' && online === true) {
        startAutoUpdate();
    } else {
        stopAutoUpdate();
    }
});
