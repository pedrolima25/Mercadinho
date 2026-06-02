// Relógio no topbar
function updateClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
updateClock();
setInterval(updateClock, 1000);

// Toggle sidebar
function toggleSidebar() {
  if (window.innerWidth <= 768) {
    document.body.classList.toggle('sidebar-open');
    return;
  }
  document.body.classList.toggle('sidebar-collapsed');
  localStorage.setItem('sidebarCollapsed', document.body.classList.contains('sidebar-collapsed'));
}

// Restaurar estado da sidebar
if (localStorage.getItem('sidebarCollapsed') === 'true') {
  document.body.classList.add('sidebar-collapsed');
}

// Auto-dismiss alerts after 5s
document.querySelectorAll('.alert:not(.alert-permanent)').forEach(function(el) {
  setTimeout(function() {
    var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    bsAlert.close();
  }, 5000);
});

// Confirm delete helper
document.querySelectorAll('[data-confirm]').forEach(function(el) {
  el.addEventListener('click', function(e) {
    if (!confirm(this.dataset.confirm)) e.preventDefault();
  });
});

// Format currency inputs on blur
document.querySelectorAll('input[data-currency]').forEach(function(el) {
  el.addEventListener('blur', function() {
    const val = parseFloat(this.value);
    if (!isNaN(val)) this.value = val.toFixed(2);
  });
});

// Active nav highlight fix for nested paths
document.querySelectorAll('.nav-item').forEach(function(el) {
  const href = el.getAttribute('href');
  if (href && href !== '/' && window.location.pathname.startsWith(href)) {
    el.classList.add('active');
  }
  el.addEventListener('click', function() {
    if (window.innerWidth <= 768) document.body.classList.remove('sidebar-open');
  });
});

document.querySelectorAll('[data-sidebar-close]').forEach(function(el) {
  el.addEventListener('click', function() {
    document.body.classList.remove('sidebar-open');
  });
});

window.addEventListener('resize', function() {
  if (window.innerWidth > 768) document.body.classList.remove('sidebar-open');
});
