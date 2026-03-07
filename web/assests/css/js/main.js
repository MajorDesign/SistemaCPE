import { getMe } from "./auth.js";

function isLoginPage() {
  const path = (location.pathname || "").toLowerCase();
  return path.endsWith("/login.html") || path.endsWith("/login");
}

async function protectPages() {
  // Se estiver na página de login, não bloqueia
  if (isLoginPage()) return;

  try {
    // Se /api/auth/me retornar OK, segue normal
    const me = await getMe();
    // opcional: expor no window ou atualizar UI
    window.__ME__ = me;
  } catch (e) {
    // Se não estiver autenticado, manda pro login
    window.location.replace("./login.html");
  }
}

// Adiciona o guard global
document.addEventListener("DOMContentLoaded", protectPages);

// Toggle Menu Mobile
document.addEventListener('DOMContentLoaded', function() {
  const menuToggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');

  if (menuToggle) {
    menuToggle.addEventListener('click', function() {
      sidebar.classList.toggle('active');
    });
  }

  // Close sidebar when clicking on a menu item
  const menuLinks = document.querySelectorAll('.menu-link');
  menuLinks.forEach(link => {
    link.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
      }
    });
  });

  // Set active menu item based on current page
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  menuLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });

  // Close sidebar when clicking outside
  document.addEventListener('click', function(event) {
    if (!sidebar.contains(event.target) && !menuToggle.contains(event.target)) {
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
      }
    }
  });
});

// Search functionality
const searchBox = document.querySelector('.search-box input');
if (searchBox) {
  searchBox.addEventListener('input', function(e) {
    const query = e.target.value.toLowerCase();
    const menuItems = document.querySelectorAll('.menu-item');
    
    menuItems.forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(query) ? 'block' : 'none';
    });
  });
}