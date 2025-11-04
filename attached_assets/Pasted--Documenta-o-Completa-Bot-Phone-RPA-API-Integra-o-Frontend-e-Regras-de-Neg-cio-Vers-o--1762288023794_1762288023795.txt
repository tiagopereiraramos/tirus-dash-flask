# 📘 Documentação Completa - Bot Phone RPA API
## Integração Frontend e Regras de Negócio

**Versão:** 2.3.6-processo-status  
**Última Atualização:** Novembro 2024  
**Desenvolvido por:** BRM Solutions

---

## 📋 Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Regras de Negócio](#3-regras-de-negócio)
4. [API e Endpoints](#4-api-e-endpoints)
5. [Modelos de Dados](#5-modelos-de-dados)
6. [Fluxos de Trabalho](#6-fluxos-de-trabalho)
7. [Autenticação e Segurança](#7-autenticação-e-segurança)
8. [Notificações em Tempo Real](#8-notificações-em-tempo-real)
9. [Guia de Integração Frontend](#9-guia-de-integração-frontend)
10. [Exemplos Práticos](#10-exemplos-práticos)
11. [Tratamento de Erros](#11-tratamento-de-erros)
12. [Boas Práticas](#12-boas-práticas)

---

## 1. Visão Geral

### 1.1. O que é o Bot Phone RPA API?

O **Bot Phone RPA API** é uma API REST assíncrona desenvolvida para automatizar processos de extração de faturas de operadoras de telefonia e upload no sistema SAT (Sistema de Automação Tributária).

### 1.2. Principais Funcionalidades

- ✅ **Automação Web (RPA)**: Execução automatizada de tarefas em portais de operadoras
- ✅ **Sistema de Filas Assíncrono**: Processamento em background com monitoramento em tempo real
- ✅ **Múltiplas Operadoras**: Suporte para OI, VIVO, EMBRATEL, DIGITALNET e SAT
- ✅ **Notificações em Tempo Real**: WebSocket e Server-Sent Events para acompanhamento
- ✅ **Integração com Processos**: Atualização automática de status de processos externos
- ✅ **Logs Estruturados**: Rastreabilidade completa de todas as operações
- ✅ **Autenticação JWT**: Sistema seguro de autenticação com tokens de longa duração

### 1.3. Casos de Uso

1. **Download Automático de Faturas**: Automatiza o download de faturas de operadoras de telefonia
2. **Upload no SAT**: Envia faturas processadas para o sistema SAT
3. **Monitoramento de Processos**: Acompanha o status de execuções RPA em tempo real
4. **Integração com Sistemas Externos**: Atualiza status de processos em sistemas externos

---

## 2. Arquitetura do Sistema

### 2.1. Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  (React/Vue/Angular)                                        │
│  - Interface de Usuário                                      │
│  - Dashboard de Monitoramento                               │
│  - Gerenciamento de Jobs                                     │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP/WebSocket
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    BOT PHONE RPA API                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (main.py)                      │  │
│  │  - Endpoints REST                                     │  │
│  │  - Autenticação JWT                                   │  │
│  │  - WebSocket/SSE                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AsyncJobManager                                      │  │
│  │  - Gerenciamento de Filas                             │  │
│  │  - Controle de Estado                                 │  │
│  │  - Worker Assíncrono                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Operadoras RPA                                       │  │
│  │  - OI, VIVO, EMBRATEL, DIGITALNET, SAT               │  │
│  │  - Selenium WebDriver                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  MinIO/S3    │ │  Processo │ │  Notification│
│  (Storage)   │ │  API      │ │  Service     │
└──────────────┘ └──────────┘ └──────────────┘
```

### 2.2. Componentes Principais

#### 2.2.1. FastAPI Application (`app/main.py`)
- **Responsabilidade**: Servir endpoints REST e WebSocket
- **Tecnologias**: FastAPI, Python 3.11+
- **Características**:
  - Endpoints assíncronos
  - Validação de dados com Pydantic
  - Documentação Swagger automática
  - Middleware de logging

#### 2.2.2. AsyncJobManager
- **Responsabilidade**: Gerenciar fila de jobs e processamento assíncrono
- **Características**:
  - Sistema de filas com `asyncio.Queue`
  - Controle de estado com locks thread-safe
  - Worker assíncrono para processar jobs
  - Limpeza automática de jobs antigos (24h)
  - Atualização automática de status de processos

#### 2.2.3. Operadoras RPA
- **Responsabilidade**: Executar automação web para cada operadora
- **Tecnologias**: Selenium WebDriver, Firefox
- **Operadoras Suportadas**:
  - **OI**: `app/operadoras/oi.py`
  - **VIVO**: `app/operadoras/vivo.py`
  - **EMBRATEL**: `app/operadoras/embratel.py`
  - **DIGITALNET**: `app/operadoras/digitalnet.py`
  - **SAT**: `app/operadoras/sat.py`

#### 2.2.4. Notification Service
- **Responsabilidade**: Enviar notificações em tempo real
- **Tecnologias**: WebSocket, Server-Sent Events (SSE)
- **Características**:
  - Notificações de atualização de jobs
  - Logs em tempo real
  - Status do sistema

### 2.3. Fluxo de Dados

```
1. Frontend → POST /executar/{operadora}
   ↓
2. API cria Job → Retorna job_id
   ↓
3. Job entra na Fila (AsyncJobManager)
   ↓
4. Worker processa Job → Executa RPA
   ↓
5. RPA executa automação → Atualiza progresso
   ↓
6. Notificações em tempo real → Frontend
   ↓
7. Job concluído → Atualiza status do processo (se processo_id fornecido)
   ↓
8. Frontend consulta resultado → GET /status/{job_id}
```

---

## 3. Regras de Negócio

### 3.1. Sistema de Jobs

#### 3.1.1. Estados de Job

Os jobs podem estar em um dos seguintes estados:

| Estado | Descrição | Transições Permitidas |
|--------|-----------|----------------------|
| `PENDING` | Job criado, aguardando na fila | → `RUNNING` |
| `RUNNING` | Job em execução | → `COMPLETED`, `FAILED` |
| `COMPLETED` | Job concluído com sucesso | - (final) |
| `FAILED` | Job falhou | - (final) |

**Regras:**
- Jobs são criados no estado `PENDING`
- Transição para `RUNNING` ocorre automaticamente quando o worker inicia
- Transição para `COMPLETED` ou `FAILED` ocorre após conclusão do RPA
- Jobs não podem ser cancelados manualmente (apenas aguardam conclusão)

#### 3.1.2. Progresso de Jobs

- **Progresso**: Numérico de 0 a 100
- **Atualização**: O RPA atualiza o progresso durante a execução
- **Marcos Importantes**:
  - `0%`: Job criado
  - `30%`: RPA iniciado
  - `90%`: RPA executado, finalizando
  - `95%`: Resultado capturado
  - `100%`: Job concluído

#### 3.1.3. Limpeza Automática

- **Regra**: Jobs com mais de 24 horas são removidos automaticamente
- **Frequência**: Limpeza executada a cada 5 minutos
- **Impacto**: Jobs antigos não são mais consultáveis

### 3.2. Operadoras

#### 3.2.1. Operadoras Suportadas

| Operadora | Endpoint | Payload Especial |
|-----------|----------|------------------|
| OI | `/executar/OI` | Padrão |
| VIVO | `/executar/VIVO` | Padrão |
| EMBRATEL | `/executar/EMBRATEL` | Padrão |
| DIGITALNET | `/executar/DIGITALNET` | Padrão |
| SAT | `/executar/sat` | Especial (veja seção 4.2.2) |

#### 3.2.2. Validação de Operadoras

- **Regra**: Operadoras devem ser exatamente como listadas (case-sensitive)
- **Erro**: Se operadora inválida, retorna `404 Not Found`
- **Mensagem**: `"Operadora '{operadora}' não encontrada"`

### 3.3. Atualização de Status de Processos

#### 3.3.1. Campo `processo_id`

- **Obrigatório**: Não (opcional)
- **Formato**: UUID string (ex: `"b4148f5f-e820-408a-b623-8f1ba3fd2578"`)
- **Uso**: Quando fornecido, o sistema tenta atualizar o status do processo relacionado

#### 3.3.2. Atualização Automática

**Regras:**
1. Atualização ocorre apenas após conclusão do job (`COMPLETED` ou `FAILED`)
2. Status atualizado:
   - `COMPLETED` → status do processo = `"COMPLETED"`
   - `FAILED` → status do processo = `"FAILED"`
3. Tentativas de endpoints:
   - `{PROCESSO_API_URL}/api/processos/{processo_id}/status`
   - `{PROCESSO_API_URL}/processos/{processo_id}/status`
   - `{PROCESSO_API_URL}/api/processos/{processo_id}`
4. Timeout: 5 segundos por tentativa
5. Se falhar: Loga warning mas não falha o job

**Configuração:**
- Variável de ambiente: `PROCESSO_API_URL` (padrão: `http://localhost:5050`)

### 3.4. Limites e Concorrência

#### 3.4.1. Limite de Workers

- **Máximo de threads simultâneas**: 5
- **Configuração**: `ThreadPoolExecutor(max_workers=5)`
- **Impacto**: Máximo de 5 jobs executando simultaneamente

#### 3.4.2. Fila de Jobs

- **Tipo**: `asyncio.Queue` (ilimitada)
- **Comportamento**: Jobs são processados na ordem FIFO (First In, First Out)
- **Bloqueio**: Se todos os workers estiverem ocupados, novos jobs aguardam na fila

### 3.5. Resultados e Erros

#### 3.5.1. Resultado de Sucesso

- **Campo**: `result` no status do job
- **Tipo**: String (caminho do arquivo ou URL)
- **Disponibilidade**: Apenas quando `status = "COMPLETED"`
- **Exemplo**: `"faturas/oi_202401.pdf"`

#### 3.5.2. Erros

- **Campo**: `error` no status do job
- **Tipo**: String (mensagem de erro)
- **Disponibilidade**: Apenas quando `status = "FAILED"`
- **Categorias de Erro**:
  - Erro de autenticação na operadora
  - Erro de navegação web
  - Erro de timeout
  - Erro de processamento de arquivo

---

## 4. API e Endpoints

### 4.1. Base URL

```
Produção: http://191.252.218.230:8000
Desenvolvimento: http://localhost:8000
```

### 4.2. Endpoints Principais

#### 4.2.1. Health Check

```http
GET /health
```

**Autenticação**: Não requerida

**Resposta:**
```json
{
  "status": "healthy",
  "message": "API está funcionando",
  "jobs_pending": 0,
  "jobs_active": 1
}
```

**Campos:**
- `status`: Status da API (`"healthy"` ou `"unhealthy"`)
- `message`: Mensagem descritiva
- `jobs_pending`: Número de jobs na fila
- `jobs_active`: Número de jobs em execução

#### 4.2.2. Criar Job RPA

```http
POST /executar/{operadora}
```

**Autenticação**: ✅ Requerida (JWT Bearer Token)

**Parâmetros de URL:**
- `operadora`: `OI` | `VIVO` | `EMBRATEL` | `DIGITALNET`

**Body (JSON):**
```json
{
  "login": "usuario@empresa.com.br",
  "senha": "senha123",
  "filtro": "12345678",
  "cnpj": "12.345.678/0001-90",
  "processo_id": "b4148f5f-e820-408a-b623-8f1ba3fd2578"  // Opcional
}
```

**Resposta de Sucesso (200):**
```json
{
  "job_id": "c489e92d-39ce-48da-a546-97f5a444cbe4",
  "status": "PENDING",
  "message": "Job criado para operadora OI",
  "status_url": "/status/c489e92d-39ce-48da-a546-97f5a444cbe4"
}
```

**Resposta de Erro (404):**
```json
{
  "detail": "Operadora 'INVALID' não encontrada"
}
```

**Resposta de Erro (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "login"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### 4.2.3. Criar Job SAT

```http
POST /executar/sat
```

**Autenticação**: ✅ Requerida (JWT Bearer Token)

**Body (JSON):**
```json
{
  "cnpj": "12.345.678/0001-90",
  "razao": "EMPRESA EXEMPLO LTDA",
  "operadora": "OI",
  "nome_filtro": "OI FIXO",
  "unidade": "UNIDADE CENTRAL",
  "servico": "TELEFONIA",
  "dados_sat": "DADOS_SAT_EXEMPLO",
  "nome_arquivo": "fatura_oi_202401.pdf",
  "data_vencimento": "15/01/2024"
}
```

**Resposta:** Mesma estrutura do endpoint `/executar/{operadora}`

#### 4.2.4. Consultar Status de Job

```http
GET /status/{job_id}
```

**Autenticação**: ✅ Requerida (JWT Bearer Token)

**Parâmetros de URL:**
- `job_id`: UUID do job

**Resposta de Sucesso (200):**
```json
{
  "job_id": "c489e92d-39ce-48da-a546-97f5a444cbe4",
  "operadora": "OI",
  "status": "RUNNING",
  "progress": 75,
  "result": null,
  "error": null,
  "created_at": "2024-01-01T10:00:00",
  "started_at": "2024-01-01T10:00:05",
  "completed_at": null,
  "logs": [
    {
      "timestamp": "2024-01-01T10:00:10",
      "message": "Iniciando processamento da operadora OI"
    },
    {
      "timestamp": "2024-01-01T10:00:15",
      "message": "Executando RPA para OI"
    }
  ]
}
```

**Resposta de Erro (404):**
```json
{
  "detail": "Job 'invalid-job-id' não encontrado"
}
```

#### 4.2.5. Listar Todos os Jobs

```http
GET /jobs
```

**Autenticação**: ✅ Requerida (JWT Bearer Token)

**Resposta:**
```json
{
  "total_jobs": 5,
  "jobs": [
    {
      "job_id": "job-1",
      "operadora": "OI",
      "status": "COMPLETED",
      "progress": 100,
      "created_at": "2024-01-01T10:00:00"
    },
    // ... mais jobs
  ]
}
```

#### 4.2.6. Obter Token JWT

```http
GET /auth/token
```

**Autenticação**: ✅ Requerida (JWT Bearer Token)

**Descrição**: Retorna o token JWT atual (útil para desenvolvimento)

**Resposta:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 525600,
  "message": "Token atual"
}
```

**Nota**: `expires_in` está em minutos (365 dias = 525600 minutos)

### 4.3. Endpoints de Notificações em Tempo Real

#### 4.3.1. Server-Sent Events (SSE) - Logs

```http
GET /events/logs
```

**Autenticação**: Não requerida

**Descrição**: Stream de logs em tempo real de todos os RPAs

**Resposta (Stream):**
```
data: {"type": "connection", "message": "Conectado ao sistema de logs RPA em tempo real", "timestamp": "2024-01-01T10:00:00Z"}

data: {"type": "log", "level": "INFO", "message": "Iniciando execução", "operadora": "VIVO", "job_id": "job-123", "timestamp": "2024-01-01T10:00:01Z"}

data: {"type": "system_status", "jobs_pending": 0, "jobs_active": 1, "jobs_done": 5, "timestamp": "2024-01-01T10:00:04Z"}
```

#### 4.3.2. WebSocket - Notificações

```http
WS /ws/notifications
```

**Autenticação**: Não requerida (mas recomendado validar token na mensagem)

**Descrição**: Conexão WebSocket para notificações em tempo real

**Mensagem de Subscrição:**
```json
{
  "action": "subscribe",
  "job_id": "c489e92d-39ce-48da-a546-97f5a444cbe4"
}
```

**Mensagens Recebidas:**
```json
{
  "type": "job_update",
  "job_id": "c489e92d-39ce-48da-a546-97f5a444cbe4",
  "data": {
    "status": "RUNNING",
    "progress": 75,
    "operadora": "OI"
  }
}
```

```json
{
  "type": "log",
  "job_id": "c489e92d-39ce-48da-a546-97f5a444cbe4",
  "level": "INFO",
  "message": "Executando RPA para OI"
}
```

---

## 5. Modelos de Dados

### 5.1. AutomacaoPayload

Modelo para criação de jobs de operadoras normais.

```typescript
interface AutomacaoPayload {
  login: string;              // Email ou usuário para login
  senha: string;              // Senha para autenticação
  filtro: string;             // Filtro ou código de identificação
  cnpj: string;               // CNPJ (com ou sem formatação)
  processo_id?: string;       // UUID do processo (opcional)
}
```

**Validações:**
- Todos os campos são obrigatórios, exceto `processo_id`
- `cnpj` pode ter formatação ou não
- `processo_id` deve ser um UUID válido quando fornecido

### 5.2. AutomacaoPayloadSat

Modelo para criação de jobs SAT.

```typescript
interface AutomacaoPayloadSat {
  cnpj: string;               // CNPJ da empresa
  razao: string;              // Razão social
  operadora: string;          // Nome da operadora
  nome_filtro: string;        // Nome do filtro SAT
  unidade: string;            // Unidade ou filial
  servico: string;            // Tipo de serviço
  dados_sat: string;          // Dados específicos do SAT
  nome_arquivo: string;       // Nome do arquivo a ser processado
  data_vencimento: string;    // Formato: "DD/MM/YYYY"
}
```

### 5.3. JobResponse

Resposta ao criar um job.

```typescript
interface JobResponse {
  job_id: string;              // UUID do job
  status: "PENDING";           // Status inicial
  message: string;             // Mensagem descritiva
  status_url: string;          // URL para consultar status
}
```

### 5.4. JobStatusResponse

Resposta ao consultar status de um job.

```typescript
interface JobStatusResponse {
  job_id: string;
  operadora: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress: number;            // 0-100
  result?: string | null;      // Caminho do arquivo (se concluído)
  error?: string | null;       // Mensagem de erro (se falhou)
  created_at: string;          // ISO 8601
  started_at?: string | null;  // ISO 8601
  completed_at?: string | null; // ISO 8601
  logs: Array<{
    timestamp: string;         // ISO 8601
    message: string;
  }>;
}
```

### 5.5. HealthResponse

Resposta do health check.

```typescript
interface HealthResponse {
  status: "healthy" | "unhealthy";
  message: string;
  jobs_pending: number;
  jobs_active: number;
}
```

---

## 6. Fluxos de Trabalho

### 6.1. Fluxo Completo: Criar e Monitorar Job

```mermaid
sequenceDiagram
    participant Frontend
    participant API
    participant JobManager
    participant RPA

    Frontend->>API: POST /executar/OI (com token)
    API->>JobManager: Criar job
    JobManager->>Frontend: Retornar job_id
    
    Frontend->>API: GET /status/{job_id} (polling)
    API->>Frontend: Status: PENDING
    
    JobManager->>RPA: Iniciar execução
    RPA->>JobManager: Atualizar progresso
    JobManager->>Frontend: Notificação WebSocket/SSE
    
    Frontend->>API: GET /status/{job_id}
    API->>Frontend: Status: RUNNING, progress: 75
    
    RPA->>JobManager: Job concluído
    JobManager->>API: Atualizar processo (se processo_id)
    JobManager->>Frontend: Notificação: COMPLETED
    
    Frontend->>API: GET /status/{job_id}
    API->>Frontend: Status: COMPLETED, result: "..."
```

### 6.2. Fluxo com Atualização de Processo

```
1. Frontend cria job com processo_id
   ↓
2. Job é processado normalmente
   ↓
3. Quando job conclui (COMPLETED ou FAILED)
   ↓
4. Sistema tenta atualizar processo via API externa
   ↓
5. Se sucesso: Loga informação
   ↓
6. Se falha: Loga warning (job não falha)
```

### 6.3. Fluxo de Notificações em Tempo Real

```
1. Frontend conecta WebSocket ou SSE
   ↓
2. Frontend subscreve job_id específico (WebSocket)
   ↓
3. Durante execução, RPA envia logs
   ↓
4. NotificationService distribui notificações
   ↓
5. Frontend recebe e atualiza UI
```

---

## 7. Autenticação e Segurança

### 7.1. JWT (JSON Web Token)

#### 7.1.1. Configuração

- **Algoritmo**: HS256
- **Expiração**: 365 dias (525600 minutos)
- **Header**: `Authorization: Bearer {token}`

#### 7.1.2. Obtenção de Token

**Opção 1: Endpoint de Desenvolvimento**
```http
GET /auth/token
Authorization: Bearer {token_atual}
```

**Opção 2: Comando no Servidor**
```bash
# No servidor Ubuntu
docker exec bot-phone-rpa-api python3 -m app.auth.jwt_auth renew
```

#### 7.1.3. Validação de Token

O frontend deve:
1. Armazenar token de forma segura (localStorage/sessionStorage)
2. Incluir token em todas as requisições autenticadas
3. Tratar erros 401 (token inválido/expirado)
4. Implementar renovação de token quando necessário

### 7.2. Endpoints Protegidos

**Requerem Autenticação:**
- ✅ `POST /executar/{operadora}`
- ✅ `POST /executar/sat`
- ✅ `GET /status/{job_id}`
- ✅ `GET /jobs`
- ✅ `GET /auth/token`

**Não Requerem Autenticação:**
- ❌ `GET /health`
- ❌ `GET /events/logs` (SSE)
- ❌ `WS /ws/notifications` (WebSocket, mas recomendado validar)

### 7.3. Tratamento de Erros de Autenticação

**Erro 401 Unauthorized:**
```json
{
  "detail": "Token inválido ou expirado"
}
```

**Ações Recomendadas:**
1. Limpar token armazenado
2. Redirecionar para tela de login
3. Solicitar novo token ao administrador

---

## 8. Notificações em Tempo Real

### 8.1. Server-Sent Events (SSE)

**Vantagens:**
- Simples de implementar
- Reconexão automática
- Suporte nativo no navegador

**Implementação JavaScript:**
```javascript
const eventSource = new EventSource('http://localhost:8000/events/logs');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'log') {
    console.log(`[${data.level}] ${data.operadora}: ${data.message}`);
    // Atualizar UI com log
  } else if (data.type === 'system_status') {
    console.log(`Status: ${data.jobs_active} ativos`);
    // Atualizar dashboard
  }
};

eventSource.onerror = (error) => {
  console.error('Erro na conexão SSE:', error);
  // Implementar reconexão
};
```

### 8.2. WebSocket

**Vantagens:**
- Bidirecional (pode enviar mensagens)
- Mais eficiente para múltiplos jobs
- Melhor para aplicações complexas

**Implementação JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

ws.onopen = () => {
  // Subscrever a um job específico
  ws.send(JSON.stringify({
    action: 'subscribe',
    job_id: 'c489e92d-39ce-48da-a546-97f5a444cbe4'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'job_update') {
    console.log('Atualização de job:', data.data);
    // Atualizar UI com status e progresso
  } else if (data.type === 'log') {
    console.log(`[${data.level}] ${data.message}`);
    // Adicionar log à interface
  }
};

ws.onerror = (error) => {
  console.error('Erro WebSocket:', error);
  // Implementar reconexão
};

ws.onclose = () => {
  console.log('Conexão WebSocket fechada');
  // Implementar reconexão
};
```

### 8.3. Polling (Alternativa Simples)

Se SSE ou WebSocket não estiverem disponíveis:

```javascript
async function pollJobStatus(jobId) {
  const interval = setInterval(async () => {
    try {
      const response = await fetch(`http://localhost:8000/status/${jobId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      // Atualizar UI
      updateJobStatus(data);
      
      // Parar polling se job concluído
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        clearInterval(interval);
      }
    } catch (error) {
      console.error('Erro ao consultar status:', error);
    }
  }, 5000); // Poll a cada 5 segundos
}
```

---

## 9. Guia de Integração Frontend

### 9.1. Estrutura de Pastas Recomendada

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts          // Cliente HTTP configurado
│   │   ├── jobs.ts            // Endpoints de jobs
│   │   └── auth.ts             // Endpoints de autenticação
│   ├── services/
│   │   ├── websocket.ts       // Serviço WebSocket
│   │   └── sse.ts             // Serviço SSE
│   ├── hooks/
│   │   ├── useJob.ts          // Hook para gerenciar job
│   │   └── useJobStatus.ts    // Hook para monitorar status
│   ├── types/
│   │   └── api.ts             // Tipos TypeScript
│   └── components/
│       ├── JobCard.tsx         // Card de job
│       └── JobLogs.tsx         // Componente de logs
```

### 9.2. Cliente HTTP Base

**Exemplo com Axios (TypeScript):**
```typescript
// src/api/client.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para tratar erros
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token inválido - limpar e redirecionar
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### 9.3. Serviço de Jobs

```typescript
// src/api/jobs.ts
import { apiClient } from './client';
import type { AutomacaoPayload, JobResponse, JobStatusResponse } from '../types/api';

export const jobsApi = {
  // Criar job para operadora
  createJob: async (operadora: string, payload: AutomacaoPayload): Promise<JobResponse> => {
    const response = await apiClient.post<JobResponse>(`/executar/${operadora}`, payload);
    return response.data;
  },

  // Criar job SAT
  createSatJob: async (payload: AutomacaoPayloadSat): Promise<JobResponse> => {
    const response = await apiClient.post<JobResponse>('/executar/sat', payload);
    return response.data;
  },

  // Consultar status de job
  getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const response = await apiClient.get<JobStatusResponse>(`/status/${jobId}`);
    return response.data;
  },

  // Listar todos os jobs
  listJobs: async (): Promise<{ total_jobs: number; jobs: JobStatusResponse[] }> => {
    const response = await apiClient.get('/jobs');
    return response.data;
  },
};
```

### 9.4. Hook para Gerenciar Job

```typescript
// src/hooks/useJob.ts
import { useState, useEffect } from 'react';
import { jobsApi } from '../api/jobs';
import type { JobStatusResponse } from '../types/api';

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let interval: NodeJS.Timeout;

    const fetchStatus = async () => {
      try {
        setLoading(true);
        const status = await jobsApi.getJobStatus(jobId);
        setJob(status);
        setError(null);

        // Parar polling se job concluído
        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          clearInterval(interval);
        }
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    // Poll inicial
    fetchStatus();

    // Poll a cada 5 segundos
    interval = setInterval(fetchStatus, 5000);

    return () => {
      clearInterval(interval);
    };
  }, [jobId]);

  return { job, loading, error };
}
```

### 9.5. Componente de Job

```tsx
// src/components/JobCard.tsx
import React from 'react';
import { useJob } from '../hooks/useJob';

interface JobCardProps {
  jobId: string;
  onComplete?: (job: JobStatusResponse) => void;
}

export const JobCard: React.FC<JobCardProps> = ({ jobId, onComplete }) => {
  const { job, loading, error } = useJob(jobId);

  useEffect(() => {
    if (job && (job.status === 'COMPLETED' || job.status === 'FAILED')) {
      onComplete?.(job);
    }
  }, [job, onComplete]);

  if (loading) return <div>Carregando...</div>;
  if (error) return <div>Erro: {error.message}</div>;
  if (!job) return null;

  return (
    <div className="job-card">
      <h3>Job: {job.operadora}</h3>
      <div className="status">Status: {job.status}</div>
      <div className="progress">
        <div className="progress-bar" style={{ width: `${job.progress}%` }} />
        <span>{job.progress}%</span>
      </div>
      {job.error && <div className="error">{job.error}</div>}
      {job.result && <div className="result">Resultado: {job.result}</div>}
      <div className="logs">
        {job.logs.map((log, index) => (
          <div key={index} className="log">
            [{log.timestamp}] {log.message}
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 10. Exemplos Práticos

### 10.1. Exemplo Completo: Criar e Monitorar Job

```typescript
// Criar job
const createAndMonitorJob = async () => {
  try {
    // 1. Criar job
    const jobResponse = await jobsApi.createJob('OI', {
      login: 'usuario@empresa.com.br',
      senha: 'senha123',
      filtro: '12345678',
      cnpj: '12.345.678/0001-90',
      processo_id: 'b4148f5f-e820-408a-b623-8f1ba3fd2578', // Opcional
    });

    console.log('Job criado:', jobResponse.job_id);

    // 2. Monitorar status (polling)
    const pollStatus = async () => {
      const status = await jobsApi.getJobStatus(jobResponse.job_id);
      
      console.log(`Status: ${status.status}, Progresso: ${status.progress}%`);

      if (status.status === 'COMPLETED') {
        console.log('Job concluído! Resultado:', status.result);
        return;
      }

      if (status.status === 'FAILED') {
        console.error('Job falhou:', status.error);
        return;
      }

      // Continuar polling
      setTimeout(pollStatus, 5000);
    };

    // Iniciar polling após 2 segundos
    setTimeout(pollStatus, 2000);
  } catch (error) {
    console.error('Erro ao criar job:', error);
  }
};
```

### 10.2. Exemplo com WebSocket

```typescript
const monitorJobWithWebSocket = (jobId: string) => {
  const ws = new WebSocket('ws://localhost:8000/ws/notifications');

  ws.onopen = () => {
    ws.send(JSON.stringify({
      action: 'subscribe',
      job_id: jobId,
    }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'job_update':
        console.log('Atualização:', data.data);
        // Atualizar UI com status e progresso
        updateUI(data.data);
        break;

      case 'log':
        console.log(`[${data.level}] ${data.message}`);
        // Adicionar log à interface
        addLog(data);
        break;

      default:
        console.log('Mensagem desconhecida:', data);
    }
  };

  ws.onerror = (error) => {
    console.error('Erro WebSocket:', error);
  };

  ws.onclose = () => {
    console.log('Conexão fechada. Tentando reconectar...');
    // Implementar reconexão
    setTimeout(() => monitorJobWithWebSocket(jobId), 5000);
  };
};
```

### 10.3. Exemplo com React Hook

```tsx
import React, { useState } from 'react';
import { jobsApi } from './api/jobs';
import { JobCard } from './components/JobCard';

export const JobManager: React.FC = () => {
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCreateJob = async () => {
    try {
      setLoading(true);
      const response = await jobsApi.createJob('OI', {
        login: 'usuario@empresa.com.br',
        senha: 'senha123',
        filtro: '12345678',
        cnpj: '12.345.678/0001-90',
        processo_id: 'b4148f5f-e820-408a-b623-8f1ba3fd2578',
      });
      setJobId(response.job_id);
    } catch (error) {
      console.error('Erro ao criar job:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleCreateJob} disabled={loading}>
        {loading ? 'Criando...' : 'Criar Job'}
      </button>
      {jobId && <JobCard jobId={jobId} />}
    </div>
  );
};
```

---

## 11. Tratamento de Erros

### 11.1. Códigos de Status HTTP

| Código | Significado | Ação Recomendada |
|--------|------------|-----------------|
| 200 | Sucesso | Processar resposta normalmente |
| 401 | Não autorizado | Limpar token, redirecionar para login |
| 404 | Não encontrado | Exibir mensagem "Job não encontrado" |
| 422 | Dados inválidos | Exibir erros de validação |
| 500 | Erro interno | Exibir mensagem genérica, tentar novamente |

### 11.2. Erros Comuns

#### 11.2.1. Token Inválido ou Expirado

```json
{
  "detail": "Token inválido ou expirado"
}
```

**Solução:**
1. Limpar token armazenado
2. Solicitar novo token ao administrador
3. Redirecionar para tela de login

#### 11.2.2. Operadora Não Encontrada

```json
{
  "detail": "Operadora 'INVALID' não encontrada"
}
```

**Solução:**
- Verificar se operadora está na lista: `OI`, `VIVO`, `EMBRATEL`, `DIGITALNET`
- Verificar se está em maiúsculas

#### 11.2.3. Job Não Encontrado

```json
{
  "detail": "Job 'invalid-job-id' não encontrado"
}
```

**Possíveis Causas:**
- Job foi removido (limpeza automática após 24h)
- Job ID inválido
- Job nunca existiu

**Solução:**
- Verificar se job_id está correto
- Informar que job pode ter sido removido

### 11.3. Tratamento de Erros no Frontend

```typescript
// Wrapper para tratar erros
const handleApiError = (error: any) => {
  if (error.response) {
    // Erro da API
    switch (error.response.status) {
      case 401:
        // Token inválido
        localStorage.removeItem('jwt_token');
        window.location.href = '/login';
        break;
      case 404:
        // Recurso não encontrado
        showNotification('Job não encontrado', 'error');
        break;
      case 422:
        // Erro de validação
        const errors = error.response.data.detail;
        showValidationErrors(errors);
        break;
      case 500:
        // Erro interno
        showNotification('Erro interno do servidor. Tente novamente.', 'error');
        break;
      default:
        showNotification('Erro desconhecido', 'error');
    }
  } else if (error.request) {
    // Erro de rede
    showNotification('Erro de conexão. Verifique sua internet.', 'error');
  } else {
    // Erro desconhecido
    showNotification('Erro inesperado', 'error');
  }
};
```

---

## 12. Boas Práticas

### 12.1. Autenticação

- ✅ **Armazenar token de forma segura**: Use `localStorage` ou `sessionStorage`
- ✅ **Incluir token em todas as requisições**: Use interceptors
- ✅ **Tratar expiração**: Implemente renovação automática ou aviso ao usuário
- ✅ **Não expor token**: Não logar token em console em produção

### 12.2. Gerenciamento de Jobs

- ✅ **Polling inteligente**: Use intervalos adequados (5-10 segundos)
- ✅ **Parar polling quando concluído**: Evite requisições desnecessárias
- ✅ **Implementar cache**: Armazene status localmente para evitar requisições
- ✅ **Usar WebSocket/SSE quando possível**: Mais eficiente que polling

### 12.3. UX/UI

- ✅ **Feedback visual**: Mostre progresso e status claramente
- ✅ **Logs em tempo real**: Exiba logs de forma organizada
- ✅ **Tratamento de erros**: Mensagens claras e acionáveis
- ✅ **Loading states**: Indique quando operações estão em andamento

### 12.4. Performance

- ✅ **Debounce em inputs**: Evite requisições excessivas
- ✅ **Cache de resultados**: Armazene jobs consultados recentemente
- ✅ **Lazy loading**: Carregue jobs sob demanda
- ✅ **Paginação**: Se listar muitos jobs, implemente paginação

### 12.5. Segurança

- ✅ **Validar dados no frontend**: Mas não confiar apenas nisso
- ✅ **HTTPS em produção**: Sempre use HTTPS
- ✅ **Sanitizar inputs**: Evite XSS
- ✅ **Não armazenar senhas**: Nunca armazene senhas em texto plano

---

## 13. Checklist de Integração

### 13.1. Configuração Inicial

- [ ] Configurar URL base da API
- [ ] Configurar token JWT
- [ ] Configurar cliente HTTP (Axios/Fetch)
- [ ] Configurar interceptors de autenticação
- [ ] Configurar tratamento de erros global

### 13.2. Funcionalidades Básicas

- [ ] Criar job para operadora
- [ ] Criar job SAT
- [ ] Consultar status de job
- [ ] Listar todos os jobs
- [ ] Health check

### 13.3. Funcionalidades Avançadas

- [ ] Notificações WebSocket
- [ ] Server-Sent Events (SSE)
- [ ] Atualização automática de status
- [ ] Integração com processo_id

### 13.4. UI/UX

- [ ] Dashboard de jobs
- [ ] Cards de jobs com progresso
- [ ] Logs em tempo real
- [ ] Tratamento de erros
- [ ] Loading states
- [ ] Feedback visual

### 13.5. Testes

- [ ] Testar criação de jobs
- [ ] Testar monitoramento de status
- [ ] Testar notificações em tempo real
- [ ] Testar tratamento de erros
- [ ] Testar autenticação

---

## 14. Recursos Adicionais

### 14.1. Documentação Swagger

Acesse a documentação interativa da API:
```
http://localhost:8000/docs
```

### 14.2. Schema OpenAPI

Obtenha o schema completo:
```
http://localhost:8000/openapi.json
```

### 14.3. Exemplos de Código

- `exemplo_uso_api_assincrona.py`: Exemplo Python completo
- Documentação Swagger: Exemplos interativos

---

## 15. Suporte e Contato

**Desenvolvido por:** BRM Solutions  
**Versão da API:** 2.3.6-processo-status  
**Última Atualização:** Novembro 2024

Para suporte técnico ou dúvidas sobre a integração, entre em contato com a equipe de desenvolvimento.

---

**Fim da Documentação**

