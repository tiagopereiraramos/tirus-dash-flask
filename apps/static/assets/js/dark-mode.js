
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
});

// Funções para visualização de fatura
function visualizarFatura(processoId) {
    const modal = document.getElementById('faturaModal');
    if (!modal) {
        console.error('Modal de fatura não encontrado');
        return;
    }

    // Mostrar loading
    const faturaViewer = document.getElementById('faturaViewer');
    const faturaLoader = document.getElementById('faturaLoader');
    
    if (faturaLoader) {
        faturaLoader.style.display = 'block';
    }
    if (faturaViewer) {
        faturaViewer.style.display = 'none';
    }

    // Fazer requisição para obter dados da fatura
    fetch(`/processos/fatura-dados/${processoId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                faturaCarregada(data);
            } else {
                console.error('Erro ao carregar fatura:', data.message);
                alert('Erro ao carregar fatura: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro na requisição:', error);
            alert('Erro ao carregar fatura');
        })
        .finally(() => {
            if (faturaLoader) {
                faturaLoader.style.display = 'none';
            }
        });

    // Mostrar modal
    if (typeof $ !== 'undefined' && $.fn.modal) {
        $(modal).modal('show');
    } else {
        modal.style.display = 'block';
    }
}

function faturaCarregada(data) {
    const faturaViewer = document.getElementById('faturaViewer');
    if (!faturaViewer) {
        console.error('Viewer de fatura não encontrado');
        return;
    }

    // Configurar viewer baseado no tipo de arquivo
    if (data.url_fatura) {
        const fileExtension = data.url_fatura.split('.').pop().toLowerCase();
        
        if (fileExtension === 'pdf') {
            faturaViewer.innerHTML = `<iframe src="${data.url_fatura}" width="100%" height="500px" frameborder="0"></iframe>`;
        } else if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) {
            faturaViewer.innerHTML = `<img src="${data.url_fatura}" class="img-fluid" alt="Fatura">`;
        } else {
            faturaViewer.innerHTML = `<p>Arquivo não pode ser visualizado diretamente. <a href="${data.url_fatura}" target="_blank">Clique aqui para baixar</a></p>`;
        }
    } else {
        faturaViewer.innerHTML = '<p>Fatura não disponível</p>';
    }

    faturaViewer.style.display = 'block';
}

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

// Função para aplicar máscaras nos campos (se jQuery mask estiver disponível)
function aplicarMascaras() {
    if (typeof $ !== 'undefined' && $.fn.mask) {
        $('[data-mask]').each(function() {
            const mask = $(this).attr('data-mask');
            if (mask) {
                $(this).mask(mask);
            }
        });
    }
}

// Chamar aplicarMascaras quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', aplicarMascaras);
