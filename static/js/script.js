function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update Queues
            const totalVehicles = data.queues.reduce((a, b) => a + b, 0);
            document.getElementById('total-vehicles').innerText = totalVehicles;

            // Update Green Lane
            document.getElementById('current-green').innerText = `Lane ${data.current_green}`;

            // Update Timer
            document.getElementById('timer').innerText = data.timer;

            // Update Mode
            document.getElementById('mode-display').innerText = data.mode;
        })
        .catch(error => console.error('Error fetching stats:', error));
}

function setMode(mode) {
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'set_mode', mode: mode }),
    });
}

function switchLane(laneId) {
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'switch_lane', lane: laneId }),
    });
}

// Poll stats every 200ms for smoother updates
setInterval(updateStats, 200);
updateStats(); // Initial call
