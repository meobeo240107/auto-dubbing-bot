const { app, BrowserWindow, ipcMain, dialog, protocol, net, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

protocol.registerSchemesAsPrivileged([
  { scheme: 'local', privileges: { supportFetchAPI: true, bypassCSP: true, secure: true, corsEnabled: true } }
]);


let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 720,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
    title: "Auto Video Editor - Dubbing",
    backgroundColor: '#1E1E1E',
    alwaysOnTop: true
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    mainWindow.setAlwaysOnTop(false);
  });

  // Setup CSP
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': ["default-src 'self' 'unsafe-inline' data: blob: http: https: ws: wss: local:;"]
      }
    });
  });

  // Load React App
  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  // Start Python backend
  const pythonExecutable = path.join(__dirname, '..', 'backend', 'venv', 'Scripts', 'python.exe');
  const backendMain = path.join(__dirname, '..', 'backend', 'main.py');
  
  // Note: we're using spawn to run the fastapi server in the background
  try {
      pythonProcess = spawn(pythonExecutable, [backendMain], {
          cwd: path.join(__dirname, '..', 'backend'),
          windowsHide: true
      });
      pythonProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
      pythonProcess.stderr.on('data', (data) => console.error(`Backend Err: ${data}`));
  } catch (e) {
      console.error("Failed to start python backend", e);
  }
}

app.whenReady().then(() => {
  protocol.handle('local', (request) => {
    const filePath = request.url.replace(/^local:\/\/\/?/, '');
    return net.fetch('file:///' + decodeURIComponent(filePath));
  });

  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
  if (pythonProcess) pythonProcess.kill();
});

const fs = require('fs');

// IPC handler to open folder dialog
ipcMain.handle('dialog:openDirectory', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    if (canceled) {
        return null;
    } else {
        const folderPath = filePaths[0];
        try {
            const files = fs.readdirSync(folderPath);
            // Filter video files
            const videoFiles = files.filter(f => f.match(/\.(mp4|mkv|mov|avi|webm)$/i)).map(f => {
                return {
                    name: f,
                    path: 'local:///' + path.join(folderPath, f).replace(/\\/g, '/')
                };
            });
            return { folderPath, videoFiles };
        } catch (e) {
            console.error("Error reading directory:", e);
            return { folderPath, videoFiles: [] };
        }
    }
});

// IPC handler to open file dialog (select individual video files)
ipcMain.handle('dialog:openFiles', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'Video Files', extensions: ['mp4', 'mkv', 'mov', 'avi', 'webm'] }
        ]
    });
    if (canceled || filePaths.length === 0) {
        return null;
    }
    const videoFiles = filePaths.map(fp => ({
        name: path.basename(fp),
        path: 'local:///' + fp.replace(/\\/g, '/')
    }));
    return { folderPath: path.dirname(filePaths[0]), videoFiles };
});

