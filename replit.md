# BRM Solutions - RPA Dashboard System

## Overview

This is a Flask-based RPA (Robotic Process Automation) orchestration system for BEG Telecomunicações that automates invoice downloading from telecom operators and uploading to the SAT (Sistema de Automação Tributária) system.

The application manages:
- **Operators** (Operadoras): Telecom companies like VIVO, EMBRATEL, OI, DIGITALNET
- **Clients** (Clientes): Business customers with subscriptions
- **Processes** (Processos): Monthly invoice download/upload workflows
- **Executions** (Execuções): Individual RPA job runs with status tracking
- **Users** (Usuários): System administrators and operators

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 4 (Datta Able theme)
- **JavaScript**: jQuery + custom scripts for real-time updates
- **CSS**: Custom dark mode + responsive design
- **Icons**: Feather Icons + Font Awesome

### Backend Architecture
- **Framework**: Flask 2.3.3 with Blueprints pattern
- **ORM**: SQLAlchemy 2.0.21 with declarative models
- **Authentication**: Dual system - Flask-Login + custom JWT for API
- **Database**: SQLite (development) with fallback, supports PostgreSQL (production)
- **Key Patterns**:
  - Blueprint-based modular structure (`apps/authentication`, `apps/home`, `apps/operadoras`, `apps/clientes`, `apps/processos`)
  - Service layer for business logic (`apps/api_externa/services_externos.py`)
  - Repository pattern for data access
  - UUID primary keys for all entities

### Core Models & Relationships
```
Usuario (Users)
  ├── has many → Processo (via criado_por)
  
Operadora (Operator)
  ├── has many → Cliente
  └── config: possui_rpa, rpa_terceirizado, url_endpoint_rpa

Cliente (Client)
  ├── belongs to → Operadora
  └── has many → Processo

Processo (Process)
  ├── belongs to → Cliente
  ├── belongs to → Usuario (criado_por)
  ├── has many → Execucao
  └── status flow: AGUARDANDO_DOWNLOAD → AGUARDANDO_APROVACAO → AGUARDANDO_ENVIO_SAT → UPLOAD_REALIZADO

Execucao (Execution)
  ├── belongs to → Processo
  └── tracks RPA job status with logs
```

### Business Logic Flow
1. **Process Creation**: Monthly processes auto-created for active clients
2. **Download Phase**: External RPA API (`http://191.252.218.230:8000`) downloads invoices
3. **Approval Phase**: Manual user approval/rejection
4. **SAT Upload Phase**: Approved invoices uploaded to SAT system
5. **Status Tracking**: Real-time updates via executions table

### Authentication Strategy
- **Session-based**: Flask-Login for web UI (`Users` model in `apps/authentication/models.py`)
- **Token-based**: Custom JWT decorator (`@login_required_api`) for API endpoints
- **User Management**: CRUD completo em `/usuarios` (apenas para administradores)
  - **Modelo**: `Users` (username, email, password, is_admin, api_externa_token)
  - **Acesso**: Menu "Usuários" disponível apenas para is_admin=True
  - **Token da API Externa**: Configurável por usuário no campo `api_externa_token`

## External Dependencies

### External RPA API
- **URL**: `http://191.252.218.230:8000` (configurable via `API_EXTERNA_URL`)
- **Authentication**: JWT Bearer token (`API_EXTERNA_TOKEN` ou `users.api_externa_token`)
- **Key Endpoints**:
  - `POST /executar/{operadora}` - Trigger RPA download
  - `GET /jobs/{job_id}` - Poll job status
  - `GET /jobs/{job_id}/logs` - Retrieve execution logs
- **Integration**: `apps/api_externa/services_externos.py`

**⚠️ IMPORTANTE - Configuração do Token JWT (Global):**

O sistema usa um **token JWT GLOBAL** para autenticar todas as requisições à API externa. Este token é usado por **todos os usuários do sistema**.

### Como o Sistema Funciona:

1. **Token Global**: Um único token JWT é usado por todos os usuários
2. **Gerenciamento**: Apenas **administradores** podem visualizar, renovar ou alterar o token
3. **Prioridade de Token**:
   - 1º: Token salvo no campo `api_externa_token` de qualquer usuário **admin**
   - 2º: Token configurado no `.env` (fallback)

### Renovar Token JWT (Apenas Admins):

1. Acesse `/usuarios` como administrador
2. Edite um usuário com perfil **admin** (ex: seu próprio usuário)
3. No campo "Token JWT da API Externa (Global)":
   - **Opção 1**: Cole manualmente um token JWT válido
   - **Opção 2**: Clique no botão **"Obter Novo JWT (Global)"** para gerar automaticamente
4. Salve o usuário
5. O token será usado por **todo o sistema**

### Obter Novo Token Automaticamente:

O botão **"Obter Novo JWT (Global)"** conecta na API externa e:
- Usa a senha configurada em `BRM_TOKEN_PASSWORD` (secret)
- Chama o endpoint `/auth/refresh` da API externa
- Gera um novo token JWT válido por **365 dias**
- Salva automaticamente no banco de dados
- O novo token é usado por **todos os usuários** imediatamente

**Erro "Token inválido ou expirado"**: 
- Acesse o cadastro de usuários como admin
- Edite um usuário admin
- Clique em "Obter Novo JWT (Global)"
- O sistema gera automaticamente um novo token válido

### Database
- **Development**: SQLite (`apps/db.sqlite3`)
- **Production**: PostgreSQL (optional, via environment variables)
- **Migrations**: Flask-Migrate support available
- **Auto-fallback**: Switches to SQLite if PostgreSQL connection fails

### Third-party Libraries
- **Flask-Login** (0.6.3): Session management
- **Flask-SQLAlchemy** (3.0.5): ORM
- **Flask-Migrate** (4.0.5): Database migrations
- **Flask-Minify** (0.42): Asset compression
- **Flask-Dance** (7.0.0): OAuth (GitHub integration)
- **python-dotenv** (1.0.0): Environment configuration
- **requests**: HTTP client for external API calls

### Server-Sent Events (SSE) - Logs em Tempo Real

O sistema possui integração **cirúrgica** com a API externa para receber logs em tempo real via SSE.

#### Endpoints Disponíveis:

1. **`GET /api/v2/logs-tempo-real/stream/<job_id>`**
   - Stream de logs filtrados por ID do job
   - Retorna eventos SSE em tempo real
   - Formato: `data: {JSON}\n\n`
   - Autenticação: Token JWT global do sistema

2. **`GET /api/v2/logs-tempo-real/teste-conexao`**
   - Testa conexão com a API externa de logs
   - Retorna status da conexão e validade do token

#### Como Consumir (Frontend):

```javascript
// Conectar ao stream de logs
const eventSource = new EventSource(`/api/v2/logs-tempo-real/stream/${jobId}`);

// Receber logs
eventSource.onmessage = function(event) {
    const log = JSON.parse(event.data);
    console.log(`[${log.level}] ${log.message}`);
    
    // Processar diferentes tipos de eventos
    switch(log.type) {
        case 'connection':
            console.log('Conectado ao stream!');
            break;
        case 'log':
            // Mostrar log na tela
            displayLog(log);
            break;
        case 'error':
            console.error('Erro:', log.message);
            break;
    }
};

// Tratar erros de conexão
eventSource.onerror = function(event) {
    console.error('Erro no SSE. Reconectando...');
    eventSource.close();
};
```

#### Formato dos Logs (JSON):

```json
{
  "type": "log",
  "level": "INFO",
  "message": "Processando RPA...",
  "operadora": "VIVO",
  "job_id": "abc-123",
  "timestamp": "2025-11-05T01:53:35.123Z",
  "service": "rpa-api",
  "logger": "app.main"
}
```

#### Integração com API Externa:

- **Endpoint da API**: `http://191.252.218.230:8000/events/logs`
- **Autenticação**: Usa token JWT global do sistema (via admin)
- **Filtros**: Logs são filtrados automaticamente por `job_id`
- **Reconexão**: Automática pelo navegador

### Configuration
- **Environment**: `.env` file with fallback to defaults
- **Key Settings**:
  - `FLASK_ENV`: Debug/Production mode
  - `SECRET_KEY`: Session encryption
  - `DB_ENGINE`, `DB_USERNAME`, etc.: Database connection
  - `API_EXTERNA_URL`, `API_EXTERNA_TOKEN`: RPA API credentials
  - `BRM_TOKEN_PASSWORD`: Senha para renovação de token JWT
  - `GITHUB_ID`, `GITHUB_SECRET`: OAuth (optional)

### Deployment
- **Docker**: `Dockerfile.easypanel` + `docker-compose.yml`
- **Web Server**: Gunicorn (configured in `gunicorn-cfg.py`)
- **Port**: 5050 (configurable)
- **Static Assets**: `/static/assets` directory