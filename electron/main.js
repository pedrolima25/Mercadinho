// Garante que o Electron rode como processo desktop (não como Node.js puro)
// O VSCode e alguns terminais definem ELECTRON_RUN_AS_NODE=1, o que impede
// o modo de browser/main process de inicializar corretamente.
delete process.env.ELECTRON_RUN_AS_NODE;

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
    title: 'Mercadinho PDV',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: false,
      sandbox: false,
    },
    autoHideMenuBar: true,
  });

  mainWindow.maximize();
  mainWindow.loadURL(config.serverUrl);

  // Injeta o preload em todos os popups (ex: PDV abre via window.open)
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    return {
      action: 'allow',
      overrideBrowserWindowOptions: {
        autoHideMenuBar: true,
        show: false,
        webPreferences: {
          preload: path.join(__dirname, 'preload.js'),
          nodeIntegration: false,
          contextIsolation: false,
          sandbox: false,
        },
      },
    };
  });

  // Maximiza o popup ao ser criado via did-create-window
  mainWindow.webContents.on('did-create-window', (win) => {
    win.maximize();
    win.show();
  });

  mainWindow.webContents.on('did-fail-load', () => {
    mainWindow.loadFile(path.join(__dirname, 'offline.html'));
    // Abre a janela de configurações automaticamente se falhar na primeira carga
    setTimeout(() => createConfigWindow(), 800);
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

function createConfigWindow() {
  if (configWindow) { configWindow.focus(); return; }

  configWindow = new BrowserWindow({
    width: 520,
    height: 520,
    resizable: false,
    title: 'Configurações — Mercadinho PDV',
    modal: mainWindow ? true : false,
    parent: mainWindow || undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: false,
    },
  });

  configWindow.loadFile(path.join(__dirname, 'config-window.html'));
  configWindow.setMenuBarVisibility(false);
  configWindow.on('closed', () => { configWindow = null; });
}

// Menu simples com atalho para configurações
// Permissão para Web Serial API (balança conectada via USB/serial)
app.on('ready', () => {
  const { session } = require('electron');
  session.defaultSession.on('select-serial-port', (event, portList, webContents, callback) => {
    event.preventDefault();
    if (portList.length > 0) {
      callback(portList[0].portId);
    } else {
      callback('');
    }
  });
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'serial') callback(true);
    else callback(true);
  });
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    if (permission === 'serial') return true;
    return true;
  });
});

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

function isPrimeiraVez() {
  const url = config.serverUrl || '';
  return !url || url.includes('SEU_IP') || url === 'http://localhost:8000' || url === 'http://localhost:8001';
}

app.whenReady().then(() => {
  config = loadConfig();

  if (isPrimeiraVez()) {
    // Primeira execução ou não configurado: mostra só a tela de configuração
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
  const sender = event.sender; // janela que chamou (PDV popup ou main)
  return new Promise((resolve) => {
    const printOptions = {
      silent: true,
      printBackground: true,
      deviceName: config.printerName || undefined,
      margins: { marginType: 'none' },
      pageSize: options?.pageSize || 'A4',
    };
    sender.print(printOptions, (success, errorType) => {
      resolve({ success, error: errorType });
    });
  });
});

ipcMain.handle('get-printers', async (event) => {
  try {
    return await event.sender.getPrintersAsync();
  } catch {
    return [];
  }
});

ipcMain.handle('get-config', () => loadConfig());

ipcMain.handle('open-config', () => createConfigWindow());

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
