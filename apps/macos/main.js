const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

const isDev = !app.isPackaged;
const WEB_PORT = 3000;

let mainWindow;
let webServer;

// ── Start the bundled Next.js server (production) ─────────────────────────────
function startWebServer() {
  return new Promise((resolve, reject) => {
    const serverScript = path.join(process.resourcesPath, 'web', 'server.js');
    webServer = spawn(process.execPath, [serverScript], {
      env: {
        ...process.env,
        PORT: WEB_PORT,
        NODE_ENV: 'production',
        HOSTNAME: '127.0.0.1',
      },
      stdio: 'pipe',
    });

    webServer.stdout.on('data', d => {
      if (d.toString().includes('Ready')) resolve();
    });
    webServer.stderr.on('data', d => console.error('[web]', d.toString()));
    webServer.on('error', reject);

    // Fallback: wait up to 8s for server to come up
    let attempts = 0;
    const poll = setInterval(() => {
      http.get(`http://127.0.0.1:${WEB_PORT}`, () => {
        clearInterval(poll);
        resolve();
      }).on('error', () => {
        if (++attempts > 40) { clearInterval(poll); reject(new Error('Server start timeout')); }
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

// ── Create main window ────────────────────────────────────────────────────────
async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0D1117',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  buildMenu();

  const url = isDev
    ? `http://localhost:${WEB_PORT}`
    : `http://127.0.0.1:${WEB_PORT}`;

  // Show loading screen while server boots
  mainWindow.loadURL(`data:text/html,<html style="background:#0D1117;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:#F0B429;font-size:24px;font-weight:800">慧股AI 启动中…</html>`);

  if (!isDev) {
    try {
      await startWebServer();
    } catch (e) {
      console.error('Failed to start web server:', e);
    }
  }

  mainWindow.loadURL(url);

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  webServer?.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (!mainWindow) createWindow();
});

app.on('before-quit', () => {
  webServer?.kill();
});
