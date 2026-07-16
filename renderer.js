const { ipcRenderer } = require('electron');
let pollInterval = null;

document.getElementById('hide-btn').addEventListener('click', () => { ipcRenderer.send('hide-app'); });

document.getElementById('run-btn').addEventListener('click', async () => {
    const statusText = document.getElementById('status-text');
    const logBox = document.getElementById('log-container');
    const dot = document.getElementById('dot');

    try {
        const response = await fetch('http://127.0.0.1:8000/start-koro');
        const data = await response.json();

        if (data.status === "running" || data.status === "already_running") {
            dot.classList.add('active');
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(async () => {
                try {
                    const res = await fetch('http://127.0.0.1:8000/status');
                    const serverData = await res.json();
                    statusText.innerText = serverData.state;
                    if(logBox.innerText !== serverData.log) {
                        logBox.innerText = serverData.log;
                    }
                } catch (err) {}
            }, 400); 
        }
    } catch (error) {
        statusText.innerText = "Brain Offline";
    }
});

document.getElementById('stop-btn').addEventListener('click', async () => {
    try {
        await fetch('http://127.0.0.1:8000/stop-koro');
        if (pollInterval) clearInterval(pollInterval);
        document.getElementById('status-text').innerText = "Offline";
        document.getElementById('dot').classList.remove('active');
    } catch (error) {}
});

document.getElementById('close-btn').addEventListener('click', async () => {
    try {
        const res = await fetch('http://127.0.0.1:8000/status');
        const data = await res.json();
        if (data.running) {
            alert("Stop Koro first.");
        } else {
            ipcRenderer.send('quit-app');
        }
    } catch (error) { ipcRenderer.send('quit-app'); }
});
