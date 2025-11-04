/**
 * API Externa Funcional - JavaScript
 * Gerencia execuções e monitoramento de jobs da API externa
 */

class APIExternaFuncional {
    constructor() {
        this.baseUrl = '/api/v2/externos';
        this.csrfToken = this.getCSRFToken();
        this.activeJobs = new Map();
        this.pollingIntervals = new Map();

        // Configurações
        this.config = {
            pollInterval: 5000, // 5 segundos
            maxPollTime: 300000, // 5 minutos
            timeout: 90000 // 90 segundos
        };

        this.init();
    }

    /**
     * Inicializa o módulo
     */
    init() {
        console.log('🚀 API Externa Funcional inicializada');
        this.setupEventListeners();
        this.loadActiveJobs();
    }

    /**
     * Obtém o token CSRF
     */
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
            document.querySelector('input[name="csrf_token"]')?.value ||
            '';
    }

    /**
     * Configura event listeners
     */
    setupEventListeners() {
        // Botões de execução RPA
        document.querySelectorAll('[data-action="executar-rpa-externo"]').forEach(btn => {
            btn.addEventListener('click', (e) => this.executarRPA(e));
        });

        // Botões de execução SAT
        document.querySelectorAll('[data-action="executar-sat-externo"]').forEach(btn => {
            btn.addEventListener('click', (e) => this.executarSAT(e));
        });

        // Botões de cancelamento
        document.querySelectorAll('[data-action="cancelar-job"]').forEach(btn => {
            btn.addEventListener('click', (e) => this.cancelarJob(e));
        });

        // Botões de visualizar payload
        document.querySelectorAll('[data-action="visualizar-payload"]').forEach(btn => {
            btn.addEventListener('click', (e) => this.visualizarPayload(e));
        });

        // Botões de logs
        document.querySelectorAll('[data-action="visualizar-logs"]').forEach(btn => {
            btn.addEventListener('click', (e) => this.visualizarLogs(e));
        });

        // Atualizar status periodicamente
        setInterval(() => this.atualizarStatusJobs(), this.config.pollInterval);
    }

    /**
     * Executa RPA para um processo
     */
    async executarRPA(event) {
        const button = event.target.closest('button');
        const processoId = button.dataset.processoId;
        const sincrono = button.dataset.sincrono === 'true';

        if (!processoId) {
            this.showError('ID do processo não encontrado');
            return;
        }

        try {
            this.setButtonLoading(button, true);

            const response = await this.makeRequest(`${this.baseUrl}/executar/${processoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    tipo: 'rpa',
                    sincrono: sincrono
                })
            });

            if (response.success) {
                if (sincrono) {
                    this.showSuccess('RPA executado com sucesso!');
                    this.reloadPage();
                } else {
                    this.showSuccess(`Job RPA criado: ${response.job_id}`);
                    this.monitorarJob(response.job_id, processoId, 'RPA');
                }
            } else {
                this.showError(response.message || 'Erro ao executar RPA');
            }

        } catch (error) {
            console.error('Erro ao executar RPA:', error);
            this.showError('Erro ao executar RPA: ' + error.message);
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Executa SAT para um processo
     */
    async executarSAT(event) {
        const button = event.target.closest('button');
        const processoId = button.dataset.processoId;
        const sincrono = button.dataset.sincrono === 'true';

        if (!processoId) {
            this.showError('ID do processo não encontrado');
            return;
        }

        try {
            this.setButtonLoading(button, true);

            const response = await this.makeRequest(`${this.baseUrl}/executar/${processoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    tipo: 'sat',
                    sincrono: sincrono
                })
            });

            if (response.success) {
                if (sincrono) {
                    this.showSuccess('SAT executado com sucesso!');
                    this.reloadPage();
                } else {
                    this.showSuccess(`Job SAT criado: ${response.job_id}`);
                    this.monitorarJob(response.job_id, processoId, 'SAT');
                }
            } else {
                this.showError(response.message || 'Erro ao executar SAT');
            }

        } catch (error) {
            console.error('Erro ao executar SAT:', error);
            this.showError('Erro ao executar SAT: ' + error.message);
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Monitora um job
     */
    async monitorarJob(jobId, processoId, tipo) {
        try {
            const response = await this.makeRequest(`${this.baseUrl}/monitorar/${jobId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    processo_id: processoId,
                    max_wait: this.config.maxPollTime / 1000,
                    poll_interval: this.config.pollInterval / 1000
                })
            });

            if (response.success) {
                this.atualizarStatusJob(jobId, response.status);

                if (response.concluido) {
                    this.showSuccess(`${tipo} concluído com sucesso!`);
                    this.pararMonitoramento(jobId);
                    this.reloadPage();
                }
            } else {
                this.showError(`Erro ao monitorar ${tipo}: ${response.message}`);
            }

        } catch (error) {
            console.error(`Erro ao monitorar job ${jobId}:`, error);
            this.showError(`Erro ao monitorar ${tipo}: ${error.message}`);
        }
    }

    /**
     * Cancela um job
     */
    async cancelarJob(event) {
        const button = event.target.closest('button');
        const jobId = button.dataset.jobId;
        const processoId = button.dataset.processoId;

        if (!jobId) {
            this.showError('ID do job não encontrado');
            return;
        }

        if (!confirm('Tem certeza que deseja cancelar este job?')) {
            return;
        }

        try {
            this.setButtonLoading(button, true);

            const response = await this.makeRequest(`${this.baseUrl}/cancelar/${jobId}?processo_id=${processoId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.success) {
                this.showSuccess('Job cancelado com sucesso!');
                this.pararMonitoramento(jobId);
                this.reloadPage();
            } else {
                this.showError(response.message || 'Erro ao cancelar job');
            }

        } catch (error) {
            console.error('Erro ao cancelar job:', error);
            this.showError('Erro ao cancelar job: ' + error.message);
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Visualiza payload de um processo
     */
    async visualizarPayload(event) {
        const button = event.target.closest('button');
        const processoId = button.dataset.processoId;
        const tipo = button.dataset.tipo || 'rpa';

        if (!processoId) {
            this.showError('ID do processo não encontrado');
            return;
        }

        try {
            this.setButtonLoading(button, true);

            const response = await this.makeRequest(`${this.baseUrl}/payload/${processoId}?tipo=${tipo}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.success) {
                this.mostrarModalPayload(response.payload, tipo, processoId);
            } else {
                this.showError(response.message || 'Erro ao gerar payload');
            }

        } catch (error) {
            console.error('Erro ao visualizar payload:', error);
            this.showError('Erro ao visualizar payload: ' + error.message);
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Visualiza logs de um job
     */
    async visualizarLogs(event) {
        const button = event.target.closest('button');
        const jobId = button.dataset.jobId;

        if (!jobId) {
            this.showError('ID do job não encontrado');
            return;
        }

        try {
            this.setButtonLoading(button, true);

            const response = await this.makeRequest(`${this.baseUrl}/logs/${jobId}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.success) {
                this.mostrarModalLogs(response.logs, jobId);
            } else {
                this.showError(response.message || 'Erro ao obter logs');
            }

        } catch (error) {
            console.error('Erro ao visualizar logs:', error);
            this.showError('Erro ao visualizar logs: ' + error.message);
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Consulta status de um job
     */
    async consultarStatusJob(jobId, processoId = '') {
        try {
            const url = processoId
                ? `${this.baseUrl}/status/${jobId}?processo_id=${processoId}`
                : `${this.baseUrl}/status/${jobId}`;

            const response = await this.makeRequest(url, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.success) {
                return response.status;
            }

            return null;

        } catch (error) {
            console.error(`Erro ao consultar status do job ${jobId}:`, error);
            return null;
        }
    }

    /**
     * Atualiza status de todos os jobs ativos
     */
    async atualizarStatusJobs() {
        for (const [jobId, jobInfo] of this.activeJobs) {
            try {
                const status = await this.consultarStatusJob(jobId, jobInfo.processoId);
                if (status) {
                    this.atualizarStatusJob(jobId, status);

                    // Se job concluído, parar monitoramento
                    if (status.status === 'COMPLETED' || status.status === 'FAILED') {
                        this.pararMonitoramento(jobId);
                        this.reloadPage();
                    }
                }
            } catch (error) {
                console.error(`Erro ao atualizar status do job ${jobId}:`, error);
            }
        }
    }

    /**
     * Atualiza interface com status do job
     */
    atualizarStatusJob(jobId, status) {
        // Atualizar elemento de status se existir
        const statusElement = document.querySelector(`[data-job-id="${jobId}"] .job-status`);
        if (statusElement) {
            statusElement.textContent = this.getStatusText(status.status);
            statusElement.className = `job-status ${this.getStatusClass(status.status)}`;
        }

        // Atualizar barra de progresso se existir
        const progressElement = document.querySelector(`[data-job-id="${jobId}"] .job-progress`);
        if (progressElement && status.progress !== undefined) {
            progressElement.style.width = `${status.progress}%`;
            progressElement.setAttribute('aria-valuenow', status.progress);
        }

        // Atualizar informações do job
        this.activeJobs.set(jobId, {
            ...this.activeJobs.get(jobId),
            status: status.status,
            progress: status.progress,
            lastUpdate: new Date()
        });
    }

    /**
     * Carrega jobs ativos da página
     */
    loadActiveJobs() {
        document.querySelectorAll('[data-job-id]').forEach(element => {
            const jobId = element.dataset.jobId;
            const processoId = element.dataset.processoId;
            const tipo = element.dataset.tipo || 'RPA';

            if (jobId) {
                this.activeJobs.set(jobId, {
                    processoId,
                    tipo,
                    status: 'PENDING',
                    progress: 0,
                    lastUpdate: new Date()
                });
            }
        });
    }

    /**
     * Para monitoramento de um job
     */
    pararMonitoramento(jobId) {
        this.activeJobs.delete(jobId);

        const interval = this.pollingIntervals.get(jobId);
        if (interval) {
            clearInterval(interval);
            this.pollingIntervals.delete(jobId);
        }
    }

    /**
     * Faz requisição HTTP
     */
    async makeRequest(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();

        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('Timeout na requisição');
            }

            throw error;
        }
    }

    /**
     * Define loading state do botão
     */
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.textContent;
        }
    }

    /**
     * Mostra modal com payload
     */
    mostrarModalPayload(payload, tipo, processoId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Payload ${tipo.toUpperCase()} - Processo ${processoId}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <pre class="bg-light p-3 rounded"><code>${JSON.stringify(payload, null, 2)}</code></pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * Mostra modal com logs
     */
    mostrarModalLogs(logs, jobId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Logs do Job ${jobId}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>Level</th>
                                        <th>Mensagem</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${logs.map(log => `
                                        <tr class="${this.getLogRowClass(log.level)}">
                                            <td>${log.timestamp || '-'}</td>
                                            <td><span class="badge ${this.getLogBadgeClass(log.level)}">${log.level}</span></td>
                                            <td>${log.message || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * Obtém texto do status
     */
    getStatusText(status) {
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
     * Obtém classe CSS do status
     */
    getStatusClass(status) {
        const classMap = {
            'PENDING': 'text-warning',
            'RUNNING': 'text-info',
            'COMPLETED': 'text-success',
            'FAILED': 'text-danger',
            'CANCELLED': 'text-secondary'
        };
        return classMap[status] || 'text-muted';
    }

    /**
     * Obtém classe da linha de log
     */
    getLogRowClass(level) {
        const classMap = {
            'ERROR': 'table-danger',
            'WARNING': 'table-warning',
            'INFO': 'table-info',
            'DEBUG': 'table-secondary'
        };
        return classMap[level] || '';
    }

    /**
     * Obtém classe do badge de log
     */
    getLogBadgeClass(level) {
        const classMap = {
            'ERROR': 'bg-danger',
            'WARNING': 'bg-warning',
            'INFO': 'bg-info',
            'DEBUG': 'bg-secondary'
        };
        return classMap[level] || 'bg-secondary';
    }

    /**
     * Mostra mensagem de sucesso
     */
    showSuccess(message) {
        if (typeof toastr !== 'undefined') {
            toastr.success(message);
        } else {
            alert('✅ ' + message);
        }
    }

    /**
     * Mostra mensagem de erro
     */
    showError(message) {
        if (typeof toastr !== 'undefined') {
            toastr.error(message);
        } else {
            alert('❌ ' + message);
        }
    }

    /**
     * Recarrega a página
     */
    reloadPage() {
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    }
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.apiExternaFuncional = new APIExternaFuncional();
});
