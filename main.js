const { app, BrowserWindow, Tray, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let tray = null;
let backendProcess = null;

function startBackend() {
    if (backendProcess) return;

    backendProcess = spawn('python', ['main.py'], {
        cwd: __dirname,
        windowsHide: true,
        stdio: 'ignore'
    });

    backendProcess.on('exit', () => {
        backendProcess = null;
    });
}

function stopBackend() {
    if (!backendProcess) return;

    backendProcess.kill();
    backendProcess = null;
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 300, height: 400,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        webPreferences: { nodeIntegration: true, contextIsolation: false }
    });

    mainWindow.loadFile('index.html');

    const { nativeImage } = require('electron');
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    
    const contextMenu = Menu.buildFromTemplate([
        { label: 'Show Koro', click: () => mainWindow.show() },
        { label: 'Quit', click: () => app.quit() }
    ]);
    tray.setToolTip('Koro Assistant');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show());
}

ipcMain.on('hide-app', () => mainWindow.hide());

ipcMain.on('quit-app', () => {
    app.quit();
});

app.whenReady().then(() => {
    startBackend();
    createWindow();
});

app.on('before-quit', stopBackend);
