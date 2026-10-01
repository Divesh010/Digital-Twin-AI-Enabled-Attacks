const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const treeKill = require('tree-kill');

const APP_PATH = path.join(__dirname, '..', 'src', 'dashboard', 'app.py');
const PROJECT_ROOT = path.join(__dirname, '..');

let streamlitProcess;
let streamlitPort = 8501;
let isQuitting = false;

app.commandLine.appendSwitch('lang', 'en-US');
console.log("[E1] Electron starting");

let mainWindow;

function pollServer(port, maxRetries = 120) {
    console.log("[E5] Streamlit health check started");
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const interval = setInterval(() => {
            const socket = new net.Socket();
            socket.setTimeout(1000);
            socket.on('connect', () => {
                socket.destroy();
                clearInterval(interval);
                resolve();
            });
            socket.on('timeout', () => { socket.destroy(); });
            socket.on('error', () => { socket.destroy(); });
            socket.connect(port, '127.0.0.1');

            attempts++;
            if (attempts >= maxRetries) {
                clearInterval(interval);
                reject(new Error("Streamlit server failed to start within the expected time."));
            }
        }, 500);
    });
}

function getAvailablePort(startPort) {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.unref();
        server.on('error', (err) => {
            if (err.code === 'EADDRINUSE') {
                resolve(getAvailablePort(startPort + 1));
            } else {
                reject(err);
            }
        });
        server.listen(startPort, '127.0.0.1', () => {
            const port = server.address().port;
            server.close(() => {
                resolve(port);
            });
        });
    });
}

function getPythonExecutable() {
    return process.env.PYTHON_EXE || "C:\\Users\\Dell\\AppData\\Local\\Programs\\Python\\Python312\\python.exe";
}

async function createWindow() {
    console.log("[E7] Creating BrowserWindow");
    mainWindow = new BrowserWindow({
        width: 1600,
        height: 1000,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.setMenu(null);
    mainWindow.webContents.openDevTools();
    console.log("[E8] BrowserWindow created");

    const loadingHtml = `
    <html>
    <body style="font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background-color: #f0f2f6; margin: 0;">
        <h2>Starting Smart Campus Digital Twin...</h2>
        <p>Connecting to local Digital Twin server...</p>
    </body>
    </html>
    `;
    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml)}`);

    mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
        console.log(`[BROWSER][Level ${level}][${sourceId}:${line}] ${message}`);
    });
    mainWindow.webContents.on('render-process-gone', (event, details) => {
        console.log(`[RENDER-GONE] reason: ${details.reason}, exitCode: ${details.exitCode}`);
    });
    mainWindow.webContents.on('unresponsive', () => {
        console.log(`[UNRESPONSIVE] Renderer became unresponsive`);
    });
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
        console.log(`[FAIL-LOAD] code: ${errorCode}, desc: ${errorDescription}, url: ${validatedURL}`);
    });

    mainWindow.webContents.on('did-finish-load', () => {
        const url = mainWindow.webContents.getURL();
        if (url.startsWith('http')) {
            console.log("[E10] Dashboard did-finish-load");
            
            const targetPage = process.env.TEST_TARGET;
            if (targetPage) {
                console.log(`[TEST] Starting sequence for ${targetPage}`);
                setTimeout(async () => {
                    try {
                        await mainWindow.webContents.executeJavaScript(`
                            const links = Array.from(document.querySelectorAll('a'));
                            const link = links.find(l => l.textContent.includes('${targetPage}'));
                            if(link) {
                                link.click();
                                console.log('Navigated to ${targetPage}');
                            } else {
                                console.log('Target link not found');
                            }
                        `);
                        
                        const checkDom = async (timeMark) => {
                            try {
                                const domSize = await mainWindow.webContents.executeJavaScript(`document.querySelector('.stApp') ? document.querySelector('.stApp').innerHTML.length : 0`);
                                console.log(`[TEST] DOM SIZE at ${timeMark}s: ${domSize}`);
                            } catch(e) {
                                console.log(`[TEST] Error checking DOM at ${timeMark}s: ${e.message}`);
                            }
                        };
                        
                        setTimeout(() => checkDom(1), 1000);
                        setTimeout(() => checkDom(3), 3000);
                        setTimeout(() => checkDom(5), 5000);
                        setTimeout(() => {
                            checkDom(10).then(() => {
                                console.log("[TEST] Sequence complete. Quitting.");
                                app.quit();
                            });
                        }, 10000);
                    } catch (e) {
                        console.log("[TEST] Execution error: " + e.message);
                        app.quit();
                    }
                }, 3000); // 3 seconds to let Streamlit settle
            }
        }
    });

    mainWindow.webContents.session.clearCache();
    mainWindow.webContents.session.clearStorageData();

    mainWindow.on('closed', function () {
        console.log("[E11] BrowserWindow closed");
        mainWindow = null;
    });

    try {
        streamlitPort = await getAvailablePort(8501);
        const pythonExe = getPythonExecutable();
        
        const { execSync } = require('child_process');
        try {
            console.log('[E_CHECK] Verifying Streamlit with python:', pythonExe);
            execSync('"' + pythonExe + '" -m streamlit --version');
        } catch (e) {
            console.error('FAILED to verify Streamlit in python:', pythonExe);
            process.exit(1);
        }
        const env = Object.assign({}, process.env, {
            PYTHONPATH: path.join(PROJECT_ROOT, 'src')
        });

        console.log("[E3] Starting Streamlit");
        streamlitProcess = spawn(pythonExe, [
            '-m', 'streamlit', 'run', APP_PATH,
            '--server.headless', 'true',
            '--server.address', '127.0.0.1',
            '--server.port', streamlitPort.toString(),
            '--global.developmentMode', 'false'
        ], {
            cwd: PROJECT_ROOT,
            env: env,
            windowsHide: true
        });

        console.log(`[E4] Streamlit PID = ${streamlitProcess.pid}`);

        streamlitProcess.stdout.on('data', (data) => console.log(`Streamlit: ${data}`));
        streamlitProcess.stderr.on('data', (data) => console.error(`Streamlit Error: ${data}`));

        streamlitProcess.on('exit', (code) => {
            console.log(`Streamlit exited with code ${code}`);
            if (!isQuitting) {
                dialog.showErrorBox('Streamlit Error', `Streamlit process exited unexpectedly with code ${code}.`);
                app.quit();
            }
        });

        await pollServer(streamlitPort);
        
        console.log("[E6] Streamlit ready");
        console.log(`[E9] Loading dashboard URL`);
        console.log(`Electron loading http://127.0.0.1:${streamlitPort}`);
        
        mainWindow.loadURL(`http://127.0.0.1:${streamlitPort}`);

    } catch (err) {
        console.error("Startup error:", err);
        dialog.showErrorBox('Startup Error', `Failed to start the Digital Twin server:\n\n${err.message}`);
        app.quit();
    }
}

app.whenReady().then(() => {
    console.log("[E2] app ready");
    createWindow();

    app.on('activate', function () {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

let cleanupDone = false;
function cleanupStreamlit() {
    if (cleanupDone) return;
    cleanupDone = true;
    
    if (streamlitProcess && streamlitProcess.pid) {
        console.log("[E13] Killing Streamlit");
        console.log(`Terminating Streamlit process tree for PID ${streamlitProcess.pid}...`);
        try {
            if (process.platform === 'win32') {
                const { execSync } = require('child_process');
                execSync(`taskkill /PID ${streamlitProcess.pid} /T /F`, { stdio: 'ignore' });
            } else {
                treeKill(streamlitProcess.pid, 'SIGKILL');
            }
            console.log("Streamlit process tree terminated successfully.");
        } catch (e) {
            console.error("Failed to kill Streamlit process:", e.message);
        }
    }
}

app.on('before-quit', () => {
    console.log("[E12] before-quit");
    isQuitting = true;
    cleanupStreamlit();
});

app.on('quit', () => {
    console.log("[E14] Electron exiting");
});

app.on('window-all-closed', function () {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});
