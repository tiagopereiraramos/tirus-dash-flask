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
});

// Variáveis globais para o sistema
window.sistemaRPA = window.sistemaRPA || {};
window.sistemaRPA.faturaCarregada = false;

// Remover todas as funções duplicadas que causam conflitos
// As funções específicas da página de detalhes ficam no template da página

// Função global removida para evitar conflitos - agora gerenciada pela página específica

// Function to toggle between light and dark themes (legacy support)
window.toggleTheme = function() {
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
};

// Function to toggle between light and dark themes (legacy)
window.toggleDarkMode = function() {
    window.toggleTheme();
};

// Função para aplicar máscaras nos campos
function aplicarMascaras() {
    // Aguardar jQuery e plugin mask estarem disponíveis
    if (typeof $ !== 'undefined' && typeof $.fn.mask !== 'undefined') {
        $('[data-mask]').each(function() {
            const mask = $(this).attr('data-mask');
            if (mask) {
                $(this).mask(mask);
            }
        });

        // Aplicar máscaras específicas
        const mesAno = document.getElementById('mes_ano');

        if (mesAno) $('#mes_ano').mask('00/0000');

        console.log('Máscaras aplicadas com sucesso');
    } else {
        // Tentar novamente após um pequeno delay
        setTimeout(aplicarMascaras, 200);
    }
}

// Aguardar jQuery estar disponível antes de aplicar máscaras
document.addEventListener('DOMContentLoaded', function() {
    // Aguardar um pouco para jQuery carregar
    setTimeout(function() {
        if (typeof $ !== 'undefined') {
            $(document).ready(function() {
                aplicarMascaras();

                // Inicializar tooltips apenas se a função existir
                if (typeof $.fn.tooltip !== 'undefined') {
                    $('[data-toggle="tooltip"]').tooltip();
                }
            });
        }
    }, 1000);
});