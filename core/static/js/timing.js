const TimingManager = (function() {
    // Almacena múltiples mediciones usando Map
    const measurements = new Map();
    
    // Genera IDs únicos para cada medición
    const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    return {
        startTiming: function() {
            const id = generateId();
            measurements.set(id, {
                startTime: performance.now(),
                element: document.getElementById('total-time')
            });
            return id;
        },
        
        endTiming: function(id) {
            try {
                const measurement = measurements.get(id);
                if (!measurement) {
                    console.warn('Medición no encontrada:', id);
                    return;
                }
                
                const endTime = performance.now();
                const totalTime = ((endTime - measurement.startTime) / 1000).toFixed(3);
                
                if (measurement.element) {
                    measurement.element.textContent = totalTime + ' s';
                }
                
                // Limpieza
                measurements.delete(id);
                
                return totalTime;
            } catch (error) {
                console.error('Error en timing:', error);
                return '0.000';
            }
        },
        
        // Para debugging
        getMeasurements: () => measurements
    };
})();

// Integración con HTMX
document.addEventListener('htmx:beforeRequest', function(evt) {
    const id = TimingManager.startTiming();
    evt.detail.requestTimingId = id;
});

document.addEventListener('htmx:afterSettle', function(evt) {
    const id = evt.detail.requestTimingId;
    if (id) {
        TimingManager.endTiming(id);
    }
});

// Ya no necesitamos exponer globalmente
window.TimingManager = TimingManager;
