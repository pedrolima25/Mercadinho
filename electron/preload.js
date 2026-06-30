const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Impressão silenciosa (sem diálogo)
  printSilent: (options) => ipcRenderer.invoke('print-silent', options),

  // Lista de impressoras disponíveis
  getPrinters: () => ipcRenderer.invoke('get-printers'),

  // Config
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),

  // Detecta que está rodando dentro do Electron
  isElectron: true,
});
