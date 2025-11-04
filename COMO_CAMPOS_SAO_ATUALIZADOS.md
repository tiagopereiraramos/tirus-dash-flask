# 📊 Como os Campos São Atualizados na Tela de Processos

## 🎯 Visão Geral

Este documento explica como os dados de execução são atualizados na interface `/processos` quando recebidos da API externa, tanto para casos de **sucesso** quanto de **erro**.

## 🔄 Fluxo de Atualização de Dados

### 1. **Início da Execução**
```python
# apps/api_externa/services_externos.py
execucao = Execucao(
    processo_id=processo.id,
    tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
    status_execucao=StatusExecucao.EXECUTANDO.value,
    classe_rpa_utilizada="API_EXTERNA",
    parametros_entrada={...}
)
```

### 2. **Payload de Sucesso (Exemplo)**
```json
{
  "success": true,
  "message": "Processo concluído com 12 faturas e 12 comprovantes enviados ao SAT.",
  "processes": [
    {
      "hash_execucao": "VIVO-12345678900012-DOWNLOAD-2025-10",
      "status_final": "UPLOADED_SAT",
      "cliente": "BRM Solutions",
      "operadora": "VIVO",
      "servico": "DOWNLOAD_FATURAS",
      "criado_em": "2025-10-15T13:42:51.201Z",
      "finalizado_em": "2025-10-15T14:24:10.558Z",
      "faturas": [
        {
          "caminho": "s3://brm-bucket/VIVO/2025-10/0001.pdf",
          "data_vencimento": "20-10-2025",
          "mes": 10,
          "ano": 2025
        }
      ],
      "metricas": {
        "tempo_execucao_segundos": 187,
        "requisicoes_http": 36,
        "erros_recuperados": 0
      }
    }
  ],
  "timestamp": "2025-10-15T14:24:10.560Z"
}
```

### 3. **Payload de Erro (Exemplo)**
```json
{
  "success": false,
  "message": "Processo interrompido: falha crítica na etapa de autenticação.",
  "processes": [
    {
      "hash_execucao": "CLARO-44556677000188-UPLOAD-2025-10",
      "status_final": "FAILED",
      "cliente": "Clínica Saúde Total",
      "operadora": "CLARO",
      "servico": "UPLOAD_SAT",
      "criado_em": "2025-10-15T13:55:04.918Z",
      "finalizado_em": "2025-10-15T14:29:10.337Z",
      "detalhes": {
        "etapa_falha": "LOGIN_PORTAL",
        "codigo_erro": "AUTH-401",
        "mensagem_erro": "Credenciais inválidas ou sessão expirada.",
        "tentativas": 3,
        "acao_recomendada": "Atualizar senha no portal CLARO e reenfileirar."
      }
    }
  ],
  "timestamp": "2025-10-15T14:29:10.338Z"
}
```

## 📋 Campos Atualizados no Banco de Dados

### **Tabela: `execucao`**
| Campo | Sucesso | Erro | Descrição |
|-------|---------|------|-----------|
| `status_execucao` | `CONCLUIDO` | `FALHOU` | Status final da execução |
| `resultado` | Payload completo | Payload completo | Dados retornados pela API |
| `mensagem_final` | "Execução concluída com sucesso" | Mensagem de erro | Descrição do resultado |
| `data_finalizacao` | Timestamp atual | Timestamp atual | Data/hora de finalização |
| `tempo_execucao_segundos` | Calculado | Calculado | Duração da execução |

### **Tabela: `processo`**
| Campo | Sucesso | Erro | Descrição |
|-------|---------|------|-----------|
| `status_processo` | `DOWNLOAD_CONCLUIDO` | `ERRO_DOWNLOAD` | Status do processo |
| `url_fatura` | `s3://brm-bucket/...` | `NULL` | URL da fatura baixada |
| `data_download` | Timestamp atual | `NULL` | Data do download |
| `valor_fatura` | Extraído do payload | `NULL` | Valor da fatura (se disponível) |

## 🖥️ Atualização na Interface

### **1. Lista de Processos (`/processos`)**
```html
<!-- apps/templates/processos/index.html -->
<td>
    <div class="d-flex flex-column">
        <small><strong>{{ processo.cliente.razao_social[:30] }}</strong></small>
        <small class="text-muted">{{ processo.cliente.operadora.nome }}</small>
    </div>
</td>
<td class="text-center">{{ processo.mes_ano }}</td>
<td>
    {% if processo.status_processo == 'AGUARDANDO_DOWNLOAD' %}
        <span class="badge badge-warning">Aguardando Download</span>
    {% elif processo.status_processo == 'DOWNLOAD_CONCLUIDO' %}
        <span class="badge badge-success">Download Concluído</span>
    {% elif processo.status_processo == 'ERRO_DOWNLOAD' %}
        <span class="badge badge-danger">Erro Download</span>
    {% endif %}
</td>
```

### **2. Detalhes do Processo (`/processos/visualizar/<id>`)**
```html
<!-- apps/templates/processos/detalhes.html -->
<!-- Status do Processo -->
{% if processo.status_processo == 'AGUARDANDO_DOWNLOAD' %}
    <span class="badge badge-warning">Aguardando Download</span>
{% elif processo.status_processo == 'DOWNLOAD_CONCLUIDO' %}
    <span class="badge badge-success">Download Concluído</span>
{% elif processo.status_processo == 'ERRO_DOWNLOAD' %}
    <span class="badge badge-danger">Erro Download</span>
{% endif %}

<!-- Histórico de Execuções -->
{% for execucao in execucoes %}
<tr>
    <td>
        <span class="badge badge-info">
            {{ execucao.tipo_execucao }}
        </span>
    </td>
    <td>
        {% if execucao.status_execucao == 'CONCLUIDO' %}
            <span class="badge badge-success">Concluído</span>
        {% elif execucao.status_execucao == 'FALHOU' %}
            <span class="badge badge-danger">Falhou</span>
        {% elif execucao.status_execucao == 'EXECUTANDO' %}
            <span class="badge badge-warning">Executando</span>
        {% endif %}
    </td>
    <td>{{ execucao.data_inicio.strftime('%d/%m/%Y %H:%M') }}</td>
    <td>{{ execucao.data_finalizacao.strftime('%d/%m/%Y %H:%M') if execucao.data_finalizacao else '-' }}</td>
    <td>{{ execucao.tempo_execucao_segundos }}s</td>
</tr>
{% endfor %}
```

## 🔄 Monitoramento em Tempo Real

### **JavaScript de Monitoramento**
```javascript
// apps/static/assets/js/monitoramento-rpa.js
class MonitoramentoRPA {
    async verificarStatus() {
        const response = await fetch(`/api/v2/externos/status/${this.jobId}`);
        const data = await response.json();

        if (data.success) {
            this.processarStatusJob(data.status);
        }
    }

    processarStatusJob(jobStatus) {
        const status = jobStatus.status;
        const progresso = jobStatus.progress || 0;
        const logs = jobStatus.logs || [];

        // Atualizar status visual
        this.atualizarStatus(status);

        // Atualizar progresso
        this.atualizarProgresso(progresso, this.obterTextoStatus(status));

        // Processar logs
        this.processarLogs(logs);

        // Verificar se job foi finalizado
        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status)) {
            this.finalizarMonitoramento(jobStatus);
        }
    }
}
```

## 🎭 Simulador de Dados

### **Script de Simulação**
```bash
# Listar processos disponíveis
python simular_dados_execucao.py listar

# Simular execução com sucesso
python simular_dados_execucao.py sucesso <UUID_PROCESSO>

# Simular execução com erro
python simular_dados_execucao.py erro <UUID_PROCESSO>

# Simular múltiplas execuções
python simular_dados_execucao.py multiplas
```

### **Exemplo de Uso**
```bash
# Simular sucesso
python simular_dados_execucao.py sucesso f38a8be8-16c3-42eb-a218-6670ac5fa477

# Resultado:
✅ Processo f38a8be8-16c3-42eb-a218-6670ac5fa477 - RICAL - RACK INDUSTRIA E COMERCIO DE ARROZ LTDA
   Status: DOWNLOAD_CONCLUIDO
   URL Fatura: s3://brm-bucket/EMBRATEL/2025-10/0001.pdf
   Hash Execução: EMBRATEL-84718741000100-DOWNLOAD-10-2025
```

## 🔧 Endpoints da API

### **1. Executar Processo**
```http
POST /api/v2/externos/executar/<processo_id>
Content-Type: application/json
X-CSRFToken: <token>

{
  "tipo": "rpa",
  "sincrono": false
}
```

### **2. Verificar Status**
```http
GET /api/v2/externos/status/<job_id>
```

### **3. Cancelar Job**
```http
DELETE /api/v2/externos/cancelar/<job_id>
```

## 📊 Mapeamento de Status

| Status API Externa | Status Processo | Status Execução | Badge Visual |
|-------------------|-----------------|-----------------|--------------|
| `UPLOADED_SAT` | `DOWNLOAD_CONCLUIDO` | `CONCLUIDO` | 🟢 Sucesso |
| `FAILED` | `ERRO_DOWNLOAD` | `FALHOU` | 🔴 Erro |
| `RUNNING` | `DOWNLOAD_EM_ANDAMENTO` | `EXECUTANDO` | 🟡 Executando |
| `PENDING` | `AGUARDANDO_DOWNLOAD` | `PENDENTE` | ⚪ Aguardando |

## 🎯 Resumo

1. **Execução Iniciada**: Cria registro na tabela `execucao` com status `EXECUTANDO`
2. **API Externa Responde**: Processa payload de sucesso ou erro
3. **Banco Atualizado**: Atualiza campos nas tabelas `execucao` e `processo`
4. **Interface Atualizada**: JavaScript monitora e atualiza a interface em tempo real
5. **Status Final**: Processo fica com status `DOWNLOAD_CONCLUIDO` ou `ERRO_DOWNLOAD`

O sistema permite acompanhar todo o fluxo de execução desde o início até a finalização, com atualizações em tempo real na interface web.
