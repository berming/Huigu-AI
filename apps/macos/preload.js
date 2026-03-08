const { contextBridge, ipcRenderer } = require('electron');

// Expose a minimal, safe API surface to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  version: process.env.npm_package_version,
});
