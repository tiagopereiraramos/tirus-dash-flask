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
- **Dual user models**: Legacy `Users` + new `Usuario` (being unified)

## External Dependencies

### External RPA API
- **URL**: `http://191.252.218.230:8000` (configurable via `API_EXTERNA_URL`)
- **Authentication**: JWT Bearer token (`API_EXTERNA_TOKEN`)
- **Key Endpoints**:
  - `POST /executar/{operadora}` - Trigger RPA download
  - `GET /jobs/{job_id}` - Poll job status
  - `GET /jobs/{job_id}/logs` - Retrieve execution logs
- **Integration**: `apps/api_externa/services_externos.py`

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

### Configuration
- **Environment**: `.env` file with fallback to defaults
- **Key Settings**:
  - `FLASK_ENV`: Debug/Production mode
  - `SECRET_KEY`: Session encryption
  - `DB_ENGINE`, `DB_USERNAME`, etc.: Database connection
  - `API_EXTERNA_URL`, `API_EXTERNA_TOKEN`: RPA API credentials
  - `GITHUB_ID`, `GITHUB_SECRET`: OAuth (optional)

### Deployment
- **Docker**: `Dockerfile.easypanel` + `docker-compose.yml`
- **Web Server**: Gunicorn (configured in `gunicorn-cfg.py`)
- **Port**: 5050 (configurable)
- **Static Assets**: `/static/assets` directory