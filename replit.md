# BRM Solutions - RPA Dashboard System

## Overview
This Flask-based RPA orchestration system automates invoice downloading from telecom operators and uploading to the SAT (Sistema de Automação Tributária) system for BEG Telecomunicações. It manages Operators, Clients, monthly Processes, RPA job Executions, and Users. The system now includes **manual invoice upload** capabilities with MinIO S3 storage integration (bucket 'beg', folder 'pdfs'). The system's business vision is to streamline invoice management, reduce manual effort, and improve operational efficiency for telecom expense management.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The frontend uses Jinja2 templates with Bootstrap 4 (Datta Able theme), jQuery, custom JavaScript for real-time updates, custom dark mode CSS, and Feather Icons + Font Awesome for iconography, focusing on a responsive design.

### Technical Implementations
- **Backend Framework**: Flask 2.3.3 with a Blueprint-based modular structure (`apps/authentication`, `apps/home`, `apps/operadoras`, `apps/clientes`, `apps/processos`).
- **ORM**: SQLAlchemy 2.0.21.
- **Database**: SQLite for development, PostgreSQL for production.
- **Authentication**: Dual system with Flask-Login for web UI and custom JWT for API endpoints.
- **Key Patterns**: Service layer for business logic, Repository pattern for data access, and UUID primary keys.
- **Core Models**: `Usuario`, `Operadora`, `Cliente`, `Processo`, `Execucao`, `Agendamento`.
- **Business Logic Flow**: Processes are auto-created monthly, external RPA downloads invoices, users manually approve/reject, and approved invoices are uploaded to the SAT system with real-time status tracking via `Execucao` records.
- **Authentication Strategy**: Session-based for UI (Flask-Login) and token-based (custom JWT) for API. A global JWT token is used for external API communication, manageable by administrators.
- **Server-Sent Events (SSE)**: Fully implemented for real-time log streaming from RPA executions, including automatic status updates and re-execution capabilities.
- **Scheduling System**: A background executor manages recurring tasks based on cron expressions, such as automatic monthly process creation and invoice downloads. It uses `croniter` for scheduling and allows configurable concurrency limits for downloads.

### Feature Specifications
- **User Management**: Full CRUD for administrators, including an `api_externa_token` field for external API access.
- **Process Status Flow**: `AGUARDANDO_DOWNLOAD` → `AGUARDANDO_APROVACAO` → `AGUARDANDO_ENVIO_SAT` → `UPLOAD_REALIZADO`.
- **RPA Automation**: Operators can be configured for RPA (`possui_rpa`, `rpa_terceirizado`, `url_endpoint_rpa`).
- **Real-time Monitoring**: SSE provides instant log visibility and automatic status synchronization for RPA jobs.
- **Automated Tasks**: Configurable scheduled tasks for process creation and download initiation.

### System Design Choices
- **Modularity**: Achieved through Flask Blueprints for better organization and scalability.
- **Data Integrity**: UUIDs for primary keys ensure uniqueness across distributed systems.
- **Extensibility**: Service and repository patterns allow for easier modification and extension of business logic and data access layers.
- **High Availability**: Fallback to SQLite if PostgreSQL connection fails.
- **Deployment**: Dockerized deployment with Gunicorn for production.

## External Dependencies

- **External RPA API**: `http://191.252.218.230:8000` for triggering RPA downloads (`POST /executar/{operadora}`), polling job status (`GET /jobs/{job_id}`), and retrieving logs (`GET /jobs/{job_id}/logs`). Authenticated via a global JWT Bearer token.
- **Database**: SQLite (development), PostgreSQL (production).
- **MinIO S3 Storage**: `https://tirus-minio.cqojac.easypanel.host` for storing invoice PDFs. Credentials in `docs/credentials (1).json`, bucket 'beg', folder 'pdfs'.
- **Third-party Libraries**:
    - `Flask-Login`: Session management.
    - `Flask-SQLAlchemy`: ORM.
    - `Flask-Migrate`: Database migrations.
    - `Flask-Minify`: Asset compression.
    - `Flask-Dance`: OAuth (GitHub integration).
    - `python-dotenv`: Environment configuration.
    - `requests`: HTTP client for external API calls.
    - `croniter`: For scheduling recurring tasks.
    - `python-dateutil`: Date manipulation.
    - `pytz`: Timezone handling.
    - `boto3`: AWS S3 SDK for MinIO integration.

## Sistema de Agendamentos Automáticos ✅ (Nov 6, 2025)

### Arquitetura

O sistema possui um executor de agendamentos que roda em background via thread daemon, verificando e executando tarefas recorrentes automaticamente.

**Componentes:**
- **Modelo Agendamento** (`apps/models/agendamento.py`): Configurações e histórico de agendamentos
- **Executor** (`apps/agendamentos/executor.py`): Thread background que verifica agendamentos a cada 60s
- **Interface Web** (`/agendamentos`): CRUD completo para gerenciar agendamentos
- **Integração**: `run.py` inicializa executor automaticamente com contexto Flask

### Tipos de Agendamento

1. **CRIAR_PROCESSOS_MENSAIS**: Cria processos mensais para todos clientes ativos
   - Função: `criar_processos_mensais_automatico()` em `apps/processos/routes.py`
   - Exemplo: `0 0 1 * *` (todo dia 1º às 00:00)

2. **EXECUTAR_DOWNLOADS**: Downloads automáticos de faturas pendentes
   - Integração com API externa (`http://191.252.218.230:8000`)
   - Parâmetros: `apenas_processos_pendentes`, `limite_execucoes_simultaneas` (padrão: 5)
   - Exemplo: `0 2 * * *` (diariamente às 02:00)

3. **ENVIAR_RELATORIOS**: Envio de relatórios por email (em desenvolvimento)
4. **LIMPEZA_LOGS**: Limpeza automática de logs (em desenvolvimento)
5. **BACKUP_DADOS**: Backup do banco de dados (em desenvolvimento)

### Lifecycle do Executor

**Inicialização:**
1. `run.py` chama `iniciar_executor(app)` ao iniciar Flask
2. Executor cria thread daemon com contexto Flask (`app.app_context()`)
3. Thread entra em loop de verificação a cada 60 segundos
4. Mantém contexto de aplicação para acesso ao banco de dados

**Execução:**
1. Busca agendamentos ativos com `proxima_execucao <= agora`
2. Executa tarefa conforme tipo (CRIAR_PROCESSOS, EXECUTAR_DOWNLOADS, etc.)
3. Calcula próxima execução usando `croniter` baseado na expressão cron
4. Atualiza registro com nova `proxima_execucao` e incrementa `total_execucoes`
5. Commit no banco de dados após cada execução

**Shutdown Gracioso:**
- `parar_executor()` aceita chamadas sem app (evita ValueError)
- Thread daemon termina automaticamente com processo principal
- Logs de shutdown/warning para troubleshooting

### Coordenação e Fila

**Modelo Simples (Sem Fila Complexa):**
- Cada agendamento executa diretamente quando atinge horário
- Downloads criam jobs independentes na API externa (assíncrona)
- Limite de concorrência via `limite_execucoes_simultaneas` (padrão: 5)
- API externa gerencia seus próprios jobs em paralelo

**Controle de Transações:**
- Cada processo tem commit/rollback individual
- Falha em um processo não afeta outros da mesma execução
- Status do processo atualizado automaticamente pela API externa após job concluir

### Recovery e Tratamento de Erros

**Estratégias:**
1. **Erro em verificação**: Logged mas executor continua (próximo ciclo em 60s)
2. **Erro em execução específica**: Rollback do processo, próximos continuam
3. **Contexto perdido**: Verifica `self.app` antes de entrar em loop
4. **Agendamento falho**: Próxima execução ainda é calculada e atualizada

**Monitoramento:**
- Todos erros loggados com stack trace completo
- Logs indicam job_id para correlação com API externa
- Contadores de sucesso/falha por execução de agendamento

### Expressões Cron Suportadas

Formato: `minuto hora dia mês dia_da_semana`

**Exemplos:**
```
0 0 1 * *      # Dia 1º às 00:00 (processos mensais)
0 2 * * *      # Diariamente às 02:00 (downloads)
0 9 * * 1      # Segundas às 09:00 (relatórios semanais)
*/30 * * * *   # A cada 30 minutos
0 */6 * * *    # A cada 6 horas
```

**Cálculo:**
- Usa biblioteca `croniter` para precisão
- Fallback: +24h se expressão inválida
- Timezone: UTC (padrão servidor)

### Troubleshooting

**"Working outside of application context":**
- ✅ Corrigido: executor mantém `app.app_context()` durante thread
- Verificar que `iniciar_executor(app)` recebe instância Flask

**Agendamento não executa:**
- Verificar `status_ativo = True`
- Confirmar `proxima_execucao <= agora`
- Checar logs para erros de execução

**Downloads não atualizam status:**
- API externa atualiza status via SSE quando job termina
- Executor apenas inicia downloads, atualização é assíncrona
- Verificar conexão com API externa e token JWT válido

## Sistema de Upload Manual de Faturas ✅ (Nov 6, 2025)

### Arquitetura

O sistema permite upload manual de faturas em PDF diretamente para o MinIO S3, oferecendo flexibilidade quando o RPA automático não consegue baixar a fatura ou para processos urgentes.

**Componentes:**
- **MinIO Service** (`apps/services/minio_service.py`): Service layer para interação com MinIO S3
- **Rotas de Upload** (`apps/processos/routes.py`): `/upload_fatura/<id>` e `/upload_sat/<id>`
- **Interface Web** (`/processos/editar/<id>`): Cards de upload manual e envio SAT
- **Storage**: MinIO S3 no bucket 'beg', pasta 'pdfs'

### Configuração MinIO

**Endpoint:** `https://tirus-minio.cqojac.easypanel.host`
**Credenciais:** Configuradas via variáveis de ambiente (`.env` ou Replit Secrets)
- `MINIO_ACCESS_KEY`: Chave de acesso S3
- `MINIO_SECRET_KEY`: Chave secreta S3
- `MINIO_ENDPOINT`: URL do servidor MinIO (opcional, padrão: https://tirus-minio.cqojac.easypanel.host)
- Bucket: `beg`
- Pasta: `pdfs`

**Valores originais em:** `docs/credentials (1).json` (não versionado)

### Fluxo de Upload Manual

1. **Seleção de Arquivo**: Usuário seleciona PDF na tela de edição do processo
2. **Upload para MinIO**: Arquivo enviado para `pdfs/{operadora}/{cliente}_{ano}_{mes}_{timestamp}_{filename}.pdf`
3. **Atualização de Status**: Processo muda automaticamente para `AGUARDANDO_APROVACAO`
4. **Metadados Salvos**: `fatura_s3_key`, `fatura_filename`, `url_fatura`, `data_upload_manual`
5. **Aprovação**: Processo segue fluxo normal (aprovação → envio SAT)

### Campos Adicionados ao Modelo Processo

```python
fatura_s3_key: String(500)          # Chave do arquivo no S3
fatura_filename: String(255)        # Nome original do arquivo
data_upload_manual: DateTime        # Data/hora do upload manual
```

### Upload para SAT

**Botão disponível quando:**
- Status: `AGUARDANDO_ENVIO_SAT` ou `APROVADO`
- Tem fatura (manual ou RPA)

**Ação:**
- Muda status para `UPLOAD_REALIZADO`
- Registra `data_envio_sat`
- TODO: Implementar integração real com SAT (atualmente apenas atualiza status)

### Validações e Regras

1. **Tipo de Arquivo**: Apenas PDFs são aceitos
2. **Vínculos Preservados**: Cliente e operadora mantidos do processo original
3. **Unicidade**: Arquivo nomeado com timestamp para evitar conflitos
4. **Segurança**: Upload requer autenticação (decorator `@verify_user_jwt`)

### Organização no MinIO

```
bucket: beg
└── pdfs/
    ├── OI/
    │   ├── ClienteA_2025_10_20251106_143052_fatura.pdf
    │   └── ClienteB_2025_10_20251106_151233_invoice.pdf
    ├── VIVO/
    │   └── ClienteC_2025_11_20251106_160415_conta.pdf
    └── EMBRATEL/
        └── ClienteD_2025_11_20251106_171045_billing.pdf
```

### Integração com Fluxo RPA

- **Upload Manual** e **Download RPA** usam os mesmos campos no modelo `Processo`
- Ambos resultam em status `AGUARDANDO_APROVACAO`
- Sistema de aprovação não diferencia origem da fatura
- Histórico preservado via campo `data_upload_manual` (NULL para RPA)

### Troubleshooting

**Erro ao conectar MinIO:**
- Verificar endpoint: `https://tirus-minio.cqojac.easypanel.host`
- Confirmar que variáveis `MINIO_ACCESS_KEY` e `MINIO_SECRET_KEY` estão configuradas
- Verificar se bucket 'beg' existe
- Checar logs para erro específico de conexão S3

**Upload falha:**
- Validar tipo de arquivo (apenas PDF)
- Verificar permissões S3 (write access ao bucket)
- Checar logs para erro específico do boto3

**Arquivo não aparece:**
- Confirmar que `fatura_s3_key` foi salvo no banco
- Verificar pasta correta: `pdfs/{operadora}/`
- Usar ferramenta MinIO console para inspeção direta