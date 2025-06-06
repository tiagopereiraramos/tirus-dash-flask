
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

// Variáveis globais para o viewer de fatura
window.faturaIframeCarregado = false;

// Funções para visualização de fatura
function visualizarFatura(processoId) {
    // Fazer requisição para obter dados da fatura primeiro
    fetch(`/processos/fatura-dados/${processoId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                exibirFaturaModal(data);
            } else {
                console.error('Erro ao carregar fatura:', data.message);
                alert('Erro ao carregar fatura: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro na requisição:', error);
            alert('Erro ao carregar fatura');
        });
}

function exibirFaturaModal(data) {
    // Verificar se existe jQuery e Bootstrap
    if (typeof $ !== 'undefined' && $.fn.modal) {
        let modalContent = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Cliente:</strong> ${data.cliente}</p>
                    <p><strong>Mês/Ano:</strong> ${data.mes_ano}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Valor:</strong> R$ ${data.valor_fatura || 'N/A'}</p>
                    <p><strong>Vencimento:</strong> ${data.data_vencimento || 'N/A'}</p>
                </div>
            </div>
            <hr>
            <div class="text-center">
                ${data.url_fatura ? 
                    `<iframe id="fatura-iframe-modal" src="${data.url_fatura}" width="100%" height="400px" frameborder="0"></iframe>` :
                    '<p class="text-muted">Fatura não disponível para visualização</p>'
                }
            </div>
        `;

        // Verificar se o modal existe, se não, criar um
        let modal = document.getElementById('faturaModal');
        if (!modal) {
            $('body').append(`
                <div class="modal fade" id="faturaModal" tabindex="-1" role="dialog">
                    <div class="modal-dialog modal-lg" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Visualizar Fatura</h5>
                                <button type="button" class="close" data-dismiss="modal">
                                    <span>&times;</span>
                                </button>
                            </div>
                            <div class="modal-body">
                                <div id="fatura-content"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-dismiss="modal">Fechar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
        }

        $('#fatura-content').html(modalContent);
        $('#faturaModal').modal('show');
        
    } else {
        // Fallback para quando jQuery/Bootstrap não estão disponíveis
        console.warn('jQuery ou Bootstrap não disponível, abrindo fatura em nova aba');
        if (data.url_fatura) {
            window.open(data.url_fatura, '_blank');
        } else {
            alert('Fatura não disponível');
        }
    }
}

// Função para quando o iframe da fatura carrega
function onFaturaLoad() {
    window.faturaIframeCarregado = true;
    const loadingElement = document.getElementById('loading-fatura');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// Função para quando há erro no iframe da fatura
function onFaturaError() {
    const loadingElement = document.getElementById('loading-fatura');
    const erroElement = document.getElementById('erro-fatura');
    
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    if (erroElement) {
        erroElement.classList.remove('d-none');
        erroElement.classList.add('d-flex');
    }
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
        const dataVencimento = document.getElementById('data_vencimento');
        const valorFatura = document.getElementById('valor_fatura');
        const mesAno = document.getElementById('mes_ano');
        
        if (dataVencimento) $('#data_vencimento').mask('00/00/0000');
        if (valorFatura) $('#valor_fatura').mask('#.##0,00', {reverse: true});
        if (mesAno) $('#mes_ano').mask('00/0000');
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
            });
        }
    }, 500);
});
