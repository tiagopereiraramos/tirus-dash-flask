` tags.

```text
Correcting querySelector errors and adding form element masking functionality.
```

<replit_final_file>
// BRM Theme Toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const mainStyleLink = document.getElementById('main-style-link');

    // Check for saved theme preference or default to light mode
    const savedTheme = localStorage.getItem('brm-theme') || 'light';

    if (themeToggle) {
        if (savedTheme === 'dark') {
            themeToggle.checked = true;
            enableDarkMode();
        }

        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                enableDarkMode();
                localStorage.setItem('brm-theme', 'dark');
            } else {
                enableLightMode();
                localStorage.setItem('brm-theme', 'light');
            }
        });
    }

    function enableDarkMode() {
        document.body.classList.add('dark-mode');
        if (mainStyleLink) {
            mainStyleLink.href = mainStyleLink.href.replace('style.css', 'dark.css');
        }
    }

    function enableLightMode() {
        document.body.classList.remove('dark-mode');
        if (mainStyleLink) {
            mainStyleLink.href = mainStyleLink.href.replace('dark.css', 'style.css');
        }
    }
});

// Script para alternar tema escuro/claro
document.addEventListener('DOMContentLoaded', function() {
    const themeSwitch = document.getElementById('theme-switch');
    const themeIndicator = document.getElementById('theme-indicator');
    const body = document.body;

    if (!themeSwitch || !themeIndicator) {
        console.warn('Elementos de tema não encontrados');
        return;
    }

    // Verificar tema atual no localStorage
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Aplicar tema inicial
    if (currentTheme === 'dark') {
        body.classList.add('dark-mode');
        themeSwitch.checked = true;
        themeIndicator.classList.remove('icon-sun');
        themeIndicator.classList.add('icon-moon');
    } else {
        body.classList.remove('dark-mode');
        themeSwitch.checked = false;
        themeIndicator.classList.remove('icon-moon');
        themeIndicator.classList.add('icon-sun');
    }

    // Event listener para mudança de tema
    themeSwitch.addEventListener('change', function() {
        if (this.checked) {
            // Mudar para modo escuro
            body.classList.add('dark-mode');
            themeIndicator.classList.remove('icon-sun');
            themeIndicator.classList.add('icon-moon');
            localStorage.setItem('theme', 'dark');
        } else {
            // Mudar para modo claro
            body.classList.remove('dark-mode');
            themeIndicator.classList.remove('icon-moon');
            themeIndicator.classList.add('icon-sun');
            localStorage.setItem('theme', 'light');
        }
    });

    // Verificar se existem elementos específicos de páginas antes de tentar usá-los
    const faturaModal = document.getElementById('faturaModal');
    const faturaViewer = document.getElementById('faturaViewer');
    const faturaLoader = document.getElementById('faturaLoader');

    // Só adicionar event listeners se os elementos existirem
    if (faturaModal) {
        // Event listeners para modal de fatura
    }

    // Verificar elementos de formulário
    const formElements = document.querySelectorAll('input[data-mask]');
    if (formElements.length > 0 && typeof $ !== 'undefined' && $.fn.mask) {
        // Aplicar máscaras apenas se jQuery mask estiver disponível
        formElements.forEach(function(element) {
            const mask = element.getAttribute('data-mask');
            if (mask) {
                $(element).mask(mask);
            }
        });
    }
});

// Function to toggle between light and dark themes
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.getElementById('theme-icon');

    if (body.classList.contains('dark-mode')) {
        body.classList.remove('dark-mode');
        if (themeIcon) {
            themeIcon.className = 'feather icon-sun';
        }
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        if (themeIcon) {
            themeIcon.className = 'feather icon-moon';
        }
        localStorage.setItem('theme', 'dark');
    }
}

// Function to toggle between light and dark themes (legacy)
function toggleDarkMode() {
    toggleTheme();
}