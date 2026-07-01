const { ipcRenderer } = require('electron');

window.electronAPI = {
  printSilent: (options) => ipcRenderer.invoke('print-silent', options),
  getPrinters: () => ipcRenderer.invoke('get-printers'),
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  openConfig: () => ipcRenderer.invoke('open-config'),
  isElectron: true,
};
