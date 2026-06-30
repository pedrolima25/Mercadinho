const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

// Caminho do config (funciona tanto em dev quanto no app empacotado)
const configPath = app.isPackaged
  ? path.join(process.resourcesPath, 'config.json')
  : path.join(__dirname, 'config.json');

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
  } catch {
    return { serverUrl: 'http://localhost:8001', printerName: '', fullscreen: false };
  }
}

function saveConfig(data) {
  fs.writeFileSync(configPath, JSON.stringify(data, null, 2), 'utf8');
}

let mainWindow;
let configWindow;
let config = loadConfig();

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    fullscreen: config.fullscreen || false,
    title: 'Mercadinho PDV',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadURL(config.serverUrl);

  mainWindow.webContents.on('did-fail-load', () => {
    mainWindow.loadFile(path.join(__dirname, 'offline.html'));
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

function createConfigWindow() {
  if (configWindow) { configWindow.focus(); return; }

  configWindow = new BrowserWindow({
    width: 480,
    height: 380,
    resizable: false,
    title: 'Configurações — Mercadinho PDV',
    modal: true,
    parent: mainWindow,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  configWindow.loadFile(path.join(__dirname, 'config-window.html'));
  configWindow.setMenuBarVisibility(false);
  configWindow.on('closed', () => { configWindow = null; });
}

// Menu simples com atalho para configurações
const menu = Menu.buildFromTemplate([
  {
    label: 'PDV',
    submenu: [
      { label: 'Recarregar', accelerator: 'F5', click: () => mainWindow?.reload() },
      { label: 'Tela Cheia', accelerator: 'F11', click: () => {
        if (mainWindow) mainWindow.setFullScreen(!mainWindow.isFullScreen());
      }},
      { type: 'separator' },
      { label: 'Configurações', accelerator: 'Ctrl+,', click: createConfigWindow },
      { type: 'separator' },
      { label: 'Sair', accelerator: 'Alt+F4', click: () => app.quit() },
    ],
  },
]);
Menu.setApplicationMenu(menu);

app.whenReady().then(() => {
  config = loadConfig();

  // Primeira execução: abre config se URL ainda é localhost
  if (!config.serverUrl || config.serverUrl === 'http://localhost:8001') {
    createConfigWindow();
  } else {
    createMainWindow();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ── IPC: impressão silenciosa ─────────────────────────────────────────────────

ipcMain.handle('print-silent', async (event, options) => {
  if (!mainWindow) return { success: false, error: 'Janela não encontrada' };
  return new Promise((resolve) => {
    const printOptions = {
      silent: true,
      printBackground: true,
      deviceName: config.printerName || undefined,
      margins: { marginType: 'none' },
      pageSize: options?.pageSize || 'A4',
    };
    mainWindow.webContents.print(printOptions, (success, errorType) => {
      resolve({ success, error: errorType });
    });
  });
});

ipcMain.handle('get-printers', async () => {
  if (!mainWindow) return [];
  try {
    return await mainWindow.webContents.getPrintersAsync();
  } catch {
    return [];
  }
});

ipcMain.handle('get-config', () => loadConfig());

ipcMain.handle('save-config', (event, newConfig) => {
  saveConfig(newConfig);
  config = newConfig;
  if (mainWindow) {
    mainWindow.loadURL(config.serverUrl);
  } else {
    createMainWindow();
  }
  if (configWindow) configWindow.close();
  return { success: true };
});
