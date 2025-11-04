/**
 * Sistema de Monitoramento RPA em Tempo Real
 *
 * Este arquivo implementa um sistema de monitoramento transparente para operações RPA,
 * permitindo que o usuário acompanhe em tempo real o progresso das execuções.
 */

class MonitoramentoRPA {
    constructor() {
        this.jobId = null;
        this.processId = null;
        this.intervalId = null;
        this.autoScroll = true;
        this.startTime = null;
        this.isActive = false;
        this.ultimoLogProgresso = null;
        this.logsProcessados = new Set();
        this.statusAnterior = null;

        this.init();
    }

    init() {
        // Configurar event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Fechar modal quando clicar no X
        $('#modalMonitoramentoRPA').on('hidden.bs.modal', () => {
            this.pararMonitoramento();
        });

        // Prevenir fechamento acidental durante execução
        $('#modalMonitoramentoRPA').on('hide.bs.modal', (e) => {
            if (this.isActive && !confirm('A execução ainda está em andamento. Deseja realmente fechar?')) {
                e.preventDefault();
                return false;
            }
        });
    }

    /**
     * Inicia o monitoramento de um job RPA
     * @param {string} jobId - ID do job a ser monitorado
     * @param {string} processId - ID do processo
     * @param {object} processInfo - Informações do processo
     */
    iniciarMonitoramento(jobId, processId, processInfo = {}) {
        this.jobId = jobId;
        this.processId = processId;
        this.startTime = new Date();
        this.isActive = true;

        // Limpar logs processados para novo monitoramento
        this.logsProcessados = new Set();

        // Preencher informações iniciais
        this.preencherInformacoesIniciais(processInfo);

        // Mostrar modal
        $('#modalMonitoramentoRPA').modal('show');

        // Tentar usar SSE para logs em tempo real primeiro
        if (this.iniciarMonitoramentoLogsTempoReal()) {
            console.log(`Monitoramento de logs em tempo real iniciado para job ${jobId}`);
        } else {
            // Fallback para polling tradicional
            this.iniciarPolling();
            console.log(`Monitoramento por polling iniciado para job ${jobId}`);
        }

        // Adicionar log inicial
        this.adicionarLog('info', `Monitoramento iniciado para Job ID: ${jobId}`);
        this.adicionarLog('info', `Processo ID: ${processId}`);
    }

    /**
     * Preenche as informações iniciais do processo
     */
    preencherInformacoesIniciais(processInfo) {
        document.getElementById('processo-id-monitor').textContent = this.processId;
        document.getElementById('job-id').textContent = this.jobId || '-';
        document.getElementById('operadora-nome').textContent = processInfo.operadora || '-';
        document.getElementById('cliente-nome').textContent = processInfo.cliente || '-';
        document.getElementById('mes-ano').textContent = processInfo.mesAno || '-';
        document.getElementById('timestamp-inicio').textContent = this.startTime.toLocaleString('pt-BR');

        // Resetar progresso
        this.atualizarProgresso(0, 'Iniciando...');
    }

    /**
     * Inicia o monitoramento de logs em tempo real via Server-Sent Events
     * @returns {boolean} True se conseguiu iniciar, False caso contrário
     */
    iniciarMonitoramentoLogsTempoReal() {
        try {
            // Verificar se o navegador suporta EventSource
            if (typeof EventSource === 'undefined') {
                console.warn('EventSource não suportado, usando polling');
                return false;
            }

            // Criar conexão SSE para logs em tempo real via endpoint local
            const url = `/api/v2/logs-tempo-real/stream/${this.jobId}`;

            this.eventSourceLogs = new EventSource(url);

            // Configurar handlers para logs
            this.eventSourceLogs.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.processarLogTempoReal(data);
                } catch (e) {
                    console.error('Erro ao processar evento de log:', e);
                }
            };

            // Configurar handler de erro
            this.eventSourceLogs.onerror = (event) => {
                console.error('Erro na conexão SSE de logs:', event);
                this.fecharConexaoLogsTempoReal();
                // Fallback para polling
                this.iniciarPolling();
            };

            // Configurar handler de abertura
            this.eventSourceLogs.onopen = (event) => {
                console.log('Conexão SSE de logs estabelecida');
                this.adicionarLog('info', '🔗 Conectado aos logs em tempo real');
            };

            // Iniciar polling para status (complementar com logs em tempo real)
            this.iniciarPolling();

            return true;

        } catch (error) {
            console.error('Erro ao iniciar monitoramento de logs em tempo real:', error);
            return false;
        }
    }

    /**
     * Processa um log recebido via SSE
     * @param {object} data - Dados do log
     */
    processarLogTempoReal(data) {
        // Verificar se é um log válido
        if (data.type !== 'log' || !data.message) {
            return;
        }

        // Verificar se o log é para o job atual
        if (data.job_id && data.job_id !== this.jobId) {
            return;
        }

        // Criar chave única para evitar duplicatas
        const logKey = `${data.timestamp}_${data.message}`;

        if (this.logsProcessados.has(logKey)) {
            return; // Log já processado
        }

        this.logsProcessados.add(logKey);

        // Determinar nível do log
        let level = 'info';
        if (data.level) {
            level = data.level.toLowerCase();
        } else if (data.message.toLowerCase().includes('erro') || data.message.toLowerCase().includes('error')) {
            level = 'error';
        } else if (data.message.toLowerCase().includes('warning') || data.message.toLowerCase().includes('aviso')) {
            level = 'warning';
        }

        // Adicionar log com timestamp
        const timestamp = data.timestamp ? new Date(data.timestamp) : new Date();
        this.adicionarLog(level, data.message, timestamp);

        // Atualizar informações do job se disponíveis
        if (data.operadora && data.operadora !== 'UNKNOWN') {
            document.getElementById('operadora-nome').textContent = data.operadora;
        }
    }

    /**
     * Fecha conexão de logs em tempo real
     */
    fecharConexaoLogsTempoReal() {
        if (this.eventSourceLogs) {
            this.eventSourceLogs.close();
            this.eventSourceLogs = null;
            console.log('Conexão SSE de logs fechada');
        }
    }

    /**
     * Inicia o polling para verificar status do job
     */
    iniciarPolling() {
        // Primeira verificação imediata
        this.verificarStatus();

        // Configurar polling a cada 2 segundos
        this.intervalId = setInterval(() => {
            this.verificarStatus();
        }, 2000);
    }

    /**
     * Verifica o status atual do job
     */
    async verificarStatus() {
        if (!this.jobId) return;

        try {
            const response = await fetch(`/api/v2/externos/status/${this.jobId}`, {
                headers: {
                    'X-CSRFToken': this.obterCSRFToken()
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.processarStatusJob(data.status);
                } else {
                    this.adicionarLog('error', `Erro ao obter status: ${data.message}`);
                }
            } else {
                this.adicionarLog('error', `Erro HTTP ${response.status} ao verificar status`);
            }
        } catch (error) {
            this.adicionarLog('error', `Erro de conexão: ${error.message}`);
        }
    }

    /**
     * Processa o status recebido do job
     */
    processarStatusJob(jobStatus) {
        const status = jobStatus.status;
        const progresso = jobStatus.progress || 0;
        const logs = jobStatus.logs || [];

        // Atualizar status
        this.atualizarStatus(status);

        // Atualizar progresso
        this.atualizarProgresso(progresso, this.obterTextoStatus(status));

        // Processar novos logs
        this.processarLogs(logs);

        // Adicionar log de progresso se não há logs específicos
        if (logs.length === 0) {
            this.adicionarLogProgresso(status, progresso);
        }

        // Atualizar timestamps
        this.atualizarTimestamps(jobStatus);

        // Verificar se job foi finalizado
        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status)) {
            this.finalizarMonitoramento(jobStatus);
        }
    }

    /**
     * Atualiza o status visual
     */
    atualizarStatus(status) {
        const statusElement = document.getElementById('status-atual');
        const statusTexto = document.getElementById('status-texto');

        // Remover classes anteriores
        statusElement.className = 'alert';

        // Aplicar classe baseada no status
        switch (status) {
            case 'PENDING':
                statusElement.classList.add('alert-warning');
                statusTexto.textContent = 'Aguardando execução...';
                break;
            case 'RUNNING':
                statusElement.classList.add('alert-info');
                statusTexto.textContent = 'Executando...';
                break;
            case 'COMPLETED':
                statusElement.classList.add('alert-success');
                statusTexto.textContent = 'Concluído com sucesso!';
                break;
            case 'FAILED':
                statusElement.classList.add('alert-danger');
                statusTexto.textContent = 'Falhou na execução';
                break;
            case 'CANCELLED':
                statusElement.classList.add('alert-secondary');
                statusTexto.textContent = 'Cancelado';
                break;
            default:
                statusElement.classList.add('alert-info');
                statusTexto.textContent = status;
        }
    }

    /**
     * Atualiza a barra de progresso
     */
    atualizarProgresso(percentual, texto) {
        const progressoBarra = document.getElementById('progresso-barra');
        const progressoTexto = document.getElementById('progresso-texto');

        progressoBarra.style.width = `${percentual}%`;
        progressoBarra.setAttribute('aria-valuenow', percentual);
        progressoTexto.textContent = `${percentual}% - ${texto}`;

        // Remover animação se concluído
        if (percentual >= 100) {
            progressoBarra.classList.remove('progress-bar-animated');
        }
    }

    /**
     * Processa logs recebidos
     */
    processarLogs(logs) {
        if (!Array.isArray(logs)) {
            return;
        }

        // Inicializar array de logs processados se não existir
        if (!this.logsProcessados) {
            this.logsProcessados = new Set();
        }

        logs.forEach(log => {
            if (log.timestamp && log.message) {
                // Criar chave única para o log
                const logKey = `${log.timestamp}_${log.message}`;

                // Só adicionar se não foi processado antes
                if (!this.logsProcessados.has(logKey)) {
                    this.logsProcessados.add(logKey);
                    this.adicionarLog(
                        log.level?.toLowerCase() || 'info',
                        log.message,
                        new Date(log.timestamp)
                    );
                }
            }
        });
    }

    /**
     * Adiciona log de progresso para jobs em execução
     */
    adicionarLogProgresso(status, progresso) {
        const agora = new Date();
        const tempoDecorrido = Math.floor((agora - this.startTime) / 1000);
        const minutos = Math.floor(tempoDecorrido / 60);
        const segundos = tempoDecorrido % 60;

        let mensagem = '';
        let level = 'info';

        switch (status) {
            case 'RUNNING':
                if (progresso > 0) {
                    mensagem = `🔄 Executando RPA... ${progresso}% concluído (${minutos}m ${segundos}s)`;
                } else {
                    mensagem = `🔄 Iniciando execução RPA... (${minutos}m ${segundos}s)`;
                }
                break;
            case 'PENDING':
                mensagem = `⏳ Aguardando execução... (${minutos}m ${segundos}s)`;
                level = 'warning';
                break;
            case 'COMPLETED':
                mensagem = `✅ Execução concluída com sucesso! (${minutos}m ${segundos}s)`;
                level = 'success';
                break;
            case 'FAILED':
                mensagem = `❌ Execução falhou (${minutos}m ${segundos}s)`;
                level = 'error';
                break;
            case 'CANCELLED':
                mensagem = `⏹️ Execução cancelada (${minutos}m ${segundos}s)`;
                level = 'warning';
                break;
            default:
                mensagem = `📊 Status: ${status} - ${progresso}% (${minutos}m ${segundos}s)`;
        }

        // Só adicionar se passou tempo suficiente desde o último log de progresso
        // ou se o status mudou
        const statusMudou = this.statusAnterior !== status;
        const tempoSuficiente = !this.ultimoLogProgresso || (agora - this.ultimoLogProgresso) > 15000; // 15 segundos

        if (statusMudou || tempoSuficiente) {
            this.ultimoLogProgresso = agora;
            this.statusAnterior = status;
            this.adicionarLog(level, mensagem, agora);
        }
    }

    /**
     * Adiciona um log ao container
     */
    adicionarLog(level, mensagem, timestamp = null) {
        const container = document.getElementById('logs-container');
        const timestampFinal = timestamp || new Date();

        // Verificar se já existe um log idêntico recente (últimos 5 segundos)
        const recentLogs = container.querySelectorAll('.log-entry');
        const now = new Date();

        for (let i = recentLogs.length - 1; i >= Math.max(0, recentLogs.length - 10); i--) {
            const logEntry = recentLogs[i];
            const logMessage = logEntry.querySelector('.log-message');
            if (logMessage && logMessage.textContent === mensagem) {
                // Verificar se é muito recente (menos de 5 segundos)
                const logTime = logEntry.querySelector('.log-timestamp');
                if (logTime) {
                    const timeText = logTime.textContent.replace(/[\[\]]/g, '');
                    const logDate = new Date();
                    const [time, period] = timeText.split(' ');
                    const [hours, minutes, seconds] = time.split(':');
                    logDate.setHours(parseInt(hours) + (period === 'PM' && hours !== '12' ? 12 : 0));
                    logDate.setMinutes(parseInt(minutes));
                    logDate.setSeconds(parseInt(seconds));

                    const diffSeconds = (now - logDate) / 1000;
                    if (diffSeconds < 5) {
                        // Log muito recente, não adicionar
                        return;
                    }
                }
            }
        }

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${level}`;

        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestampFinal.toLocaleTimeString('pt-BR')}]</span>
            <span class="log-message">${mensagem}</span>
        `;

        container.appendChild(logEntry);

        // Auto-scroll se habilitado
        if (this.autoScroll) {
            container.scrollTop = container.scrollHeight;
        }
    }

    /**
     * Atualiza timestamps
     */
    atualizarTimestamps(jobStatus) {
        const timestampAtualizacao = document.getElementById('timestamp-atualizacao');
        const duracao = document.getElementById('duracao');

        timestampAtualizacao.textContent = new Date().toLocaleString('pt-BR');

        if (this.startTime) {
            const duracaoMs = new Date() - this.startTime;
            const duracaoSegundos = Math.floor(duracaoMs / 1000);
            const minutos = Math.floor(duracaoSegundos / 60);
            const segundos = duracaoSegundos % 60;

            duracao.textContent = `${minutos}m ${segundos}s`;
        }
    }

    /**
     * Finaliza o monitoramento
     */
    finalizarMonitoramento(jobStatus) {
        this.isActive = false;

        // Fechar conexão SSE de logs
        this.fecharConexaoLogsTempoReal();

        // Parar polling
        this.pararPolling();

        // Mostrar resultado final
        this.mostrarResultadoFinal(jobStatus);

        // Atualizar botões
        document.getElementById('btn-cancelar').style.display = 'none';
        document.getElementById('btn-atualizar-processo').style.display = 'inline-block';

        // Adicionar log final
        this.adicionarLog('success', 'Monitoramento finalizado');
    }

    /**
     * Mostra o resultado final
     */
    mostrarResultadoFinal(jobStatus) {
        const container = document.getElementById('resultado-container');
        const conteudo = document.getElementById('resultado-conteudo');

        let html = '';

        if (jobStatus.status === 'COMPLETED') {
            html = `
                <div class="alert alert-success">
                    <h6><i class="feather icon-check-circle"></i> Execução Concluída com Sucesso!</h6>
                    <p class="mb-0">O job foi executado com sucesso.</p>
                </div>
            `;

            if (jobStatus.result) {
                html += `
                    <div class="mt-3">
                        <h6>Resultado:</h6>
                        <pre class="bg-light p-3 rounded">${JSON.stringify(jobStatus.result, null, 2)}</pre>
                    </div>
                `;
            }
        } else if (jobStatus.status === 'FAILED') {
            html = `
                <div class="alert alert-danger">
                    <h6><i class="feather icon-x-circle"></i> Execução Falhou</h6>
                    <p class="mb-0">O job falhou durante a execução.</p>
                </div>
            `;

            if (jobStatus.error) {
                html += `
                    <div class="mt-3">
                        <h6>Erro:</h6>
                        <pre class="bg-light p-3 rounded text-danger">${jobStatus.error}</pre>
                    </div>
                `;
            }
        } else if (jobStatus.status === 'CANCELLED') {
            html = `
                <div class="alert alert-warning">
                    <h6><i class="feather icon-stop-circle"></i> Execução Cancelada</h6>
                    <p class="mb-0">O job foi cancelado.</p>
                </div>
            `;
        }

        conteudo.innerHTML = html;
        container.style.display = 'block';
    }

    /**
     * Para o monitoramento
     */
    pararMonitoramento() {
        this.isActive = false;

        // Fechar conexão SSE de logs
        this.fecharConexaoLogsTempoReal();

        // Parar polling
        this.pararPolling();
    }

    /**
     * Para o polling
     */
    pararPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Cancela o job atual
     */
    async cancelarJob() {
        if (!this.jobId || !confirm('Tem certeza que deseja cancelar este job?')) {
            return;
        }

        try {
            const response = await fetch(`/api/v2/externos/cancelar/${this.jobId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.obterCSRFToken()
                }
            });

            if (response.ok) {
                this.adicionarLog('warning', 'Solicitação de cancelamento enviada...');
            } else {
                this.adicionarLog('error', 'Erro ao cancelar job');
            }
        } catch (error) {
            this.adicionarLog('error', `Erro ao cancelar job: ${error.message}`);
        }
    }

    /**
     * Atualiza o processo na interface principal
     */
    atualizarProcesso() {
        if (this.processId) {
            // Recarregar a página para mostrar mudanças
            window.location.reload();
        }
    }

    /**
     * Obtém o texto do status
     */
    obterTextoStatus(status) {
        const statusMap = {
            'PENDING': 'Aguardando',
            'RUNNING': 'Executando',
            'COMPLETED': 'Concluído',
            'FAILED': 'Falhou',
            'CANCELLED': 'Cancelado'
        };
        return statusMap[status] || status;
    }

    /**
     * Obtém o token CSRF
     */
    obterCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

}

// Funções globais para compatibilidade
let monitoramentoRPA = null;

function iniciarMonitoramentoRPA(jobId, processId, processInfo = {}) {
    if (!monitoramentoRPA) {
        monitoramentoRPA = new MonitoramentoRPA();
    }
    monitoramentoRPA.iniciarMonitoramento(jobId, processId, processInfo);
}

function limparLogs() {
    const container = document.getElementById('logs-container');
    container.innerHTML = '<div class="text-muted">Logs limpos...</div>';
}

function toggleAutoScroll() {
    if (monitoramentoRPA) {
        monitoramentoRPA.autoScroll = !monitoramentoRPA.autoScroll;
        const icon = document.getElementById('auto-scroll-icon');
        icon.className = monitoramentoRPA.autoScroll ? 'feather icon-arrow-down' : 'feather icon-arrow-up';
    }
}

function cancelarJob() {
    if (monitoramentoRPA) {
        monitoramentoRPA.cancelarJob();
    }
}

function atualizarProcesso() {
    if (monitoramentoRPA) {
        monitoramentoRPA.atualizarProcesso();
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function () {
    monitoramentoRPA = new MonitoramentoRPA();
});
