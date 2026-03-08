const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// ── Single instance lock ───────────────────────────────────────────────────────
// Prevents multiple Electron processes (and thus multiple windows) from launching.
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
  process.exit(0);
}

const isDev = !app.isPackaged;
const WEB_PORT = 3000;

let mainWindow = null;
let webServer = null;
let isCreatingWindow = false; // guard against concurrent createWindow calls

// ── Start the bundled Next.js server (production) ─────────────────────────────
function startWebServer() {
  return new Promise((resolve, reject) => {
    const serverScript = path.join(process.resourcesPath, 'web', 'server.js');
    webServer = spawn(process.execPath, [serverScript], {
      env: {
        ...process.env,
        ELECTRON_RUN_AS_NODE: '1', // run Electron binary as plain Node.js
        PORT: String(WEB_PORT),
        NODE_ENV: 'production',
        HOSTNAME: '127.0.0.1',
        // Forward API key so Next.js AI routes can call Claude
        ...(process.env.ANTHROPIC_API_KEY ? { ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY } : {}),
      },
      stdio: 'pipe',
    });

    let resolved = false;
    const done = (err) => {
      if (resolved) return;
      resolved = true;
      clearInterval(poll);
      if (err) reject(err); else resolve();
    };

    webServer.stdout.on('data', d => {
      const text = d.toString();
      console.log('[web]', text.trim());
      if (text.includes('Ready') || text.includes('ready')) done();
    });
    webServer.stderr.on('data', d => console.error('[web]', d.toString().trim()));
    webServer.on('error', err => done(err));
    webServer.on('exit', (code) => {
      if (!resolved) done(new Error(`server exited with code ${code}`));
    });

    // Fallback: poll HTTP until server responds
    let attempts = 0;
    const poll = setInterval(() => {
      http.get(`http://127.0.0.1:${WEB_PORT}`, (res) => {
        res.resume(); // drain
        done();
      }).on('error', () => {
        if (++attempts > 50) done(new Error('Server start timeout'));
      });
    }, 200);
  });
}

// ── macOS native menu ─────────────────────────────────────────────────────────
function buildMenu() {
  const template = [
    {
      label: app.name,
      submenu: [
        { label: '关于 慧股AI', role: 'about' },
        { type: 'separator' },
        { label: '偏好设置…', accelerator: 'Cmd+,', click: () => mainWindow?.loadURL(`http://127.0.0.1:${WEB_PORT}/profile`) },
        { type: 'separator' },
        { label: '退出', role: 'quit' },
      ],
    },
    {
      label: '查看',
      submenu: [
        { label: '行情', accelerator: 'Cmd+1', click: () => mainWindow?.loadURL(`http://127.0.0.1:${WEB_PORT}/`) },
        { label: '热议', accelerator: 'Cmd+2', click: () => mainWindow?.loadURL(`http://127.0.0.1:${WEB_PORT}/sentiment`) },
        { label: 'AI投研', accelerator: 'Cmd+3', click: () => mainWindow?.loadURL(`http://127.0.0.1:${WEB_PORT}/research`) },
        { type: 'separator' },
        { label: '重新加载', role: 'reload' },
        { label: '开发者工具', role: 'toggleDevTools', visible: isDev },
        { type: 'separator' },
        { label: '实际大小', role: 'resetZoom' },
        { label: '放大', role: 'zoomIn' },
        { label: '缩小', role: 'zoomOut' },
        { type: 'separator' },
        { label: '全屏', role: 'togglefullscreen' },
      ],
    },
    {
      label: '窗口',
      role: 'windowMenu',
    },
    {
      label: '帮助',
      role: 'help',
      submenu: [
        { label: '关于慧股AI', click: () => shell.openExternal('https://github.com') },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── Error page ────────────────────────────────────────────────────────────────
function errorPage(msg) {
  return `data:text/html;charset=utf-8,<html style="background:%230D1117;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:%23e6edf3;gap:16px">
<div style="font-size:48px">⚠️</div>
<div style="font-size:20px;font-weight:700">启动失败</div>
<div style="font-size:14px;color:%238b949e;max-width:480px;text-align:center">${encodeURIComponent(msg)}</div>
<button onclick="location.reload()" style="margin-top:12px;padding:8px 24px;background:%23F0B429;border:none;border-radius:6px;font-size:14px;cursor:pointer">重试</button>
</html>`;
}

// ── Create main window ────────────────────────────────────────────────────────
async function createWindow() {
  if (isCreatingWindow || mainWindow) return;
  isCreatingWindow = true;

  try {
    mainWindow = new BrowserWindow({
      width: 1280,
      height: 800,
      minWidth: 900,
      minHeight: 600,
      titleBarStyle: 'hiddenInset',
      backgroundColor: '#0D1117',
      show: false, // show after ready-to-show to avoid flash
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    // Prevent renderer from opening any new windows (stops infinite-window bug)
    mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));

    // Show window once first paint is ready (no white/black flash)
    mainWindow.once('ready-to-show', () => mainWindow?.show());

    buildMenu();

    // Show loading screen immediately
    mainWindow.loadURL(
      `data:text/html;charset=utf-8,<html style="background:%230D1117;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:%23F0B429;font-size:24px;font-weight:800">慧股AI 启动中…</html>`
    );

    if (!isDev) {
      try {
        await startWebServer();
      } catch (e) {
        console.error('Failed to start web server:', e);
        mainWindow?.loadURL(errorPage(String(e)));
        return;
      }
    }

    mainWindow.loadURL(
      isDev ? `http://localhost:${WEB_PORT}` : `http://127.0.0.1:${WEB_PORT}`
    );

    mainWindow.on('closed', () => { mainWindow = null; });
  } finally {
    isCreatingWindow = false;
  }
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(createWindow);

// When a second instance tries to launch, focus the existing window instead
app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.on('window-all-closed', () => {
  webServer?.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (!mainWindow && !isCreatingWindow) createWindow();
});

app.on('before-quit', () => {
  webServer?.kill();
});
