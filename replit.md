# BRM Solutions - RPA Dashboard System

## Overview
This Flask-based RPA orchestration system automates invoice downloading from telecom operators and uploading to the SAT (Sistema de Automação Tributária) system for BEG Telecomunicações. It manages Operators, Clients, monthly Processes, RPA job Executions, and Users. The system includes manual invoice upload with MinIO S3 storage and automated SAT upload via an external RPA API with real-time log tracking via SSE. The business vision is to streamline invoice management, reduce manual effort, and improve operational efficiency for telecom expense management.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The frontend uses Jinja2 templates with Bootstrap 4 (Datta Able theme), jQuery, custom JavaScript for real-time updates, custom dark mode CSS, and Feather Icons + Font Awesome for iconography, focusing on a responsive design.

### Technical Implementations
- **Backend Framework**: Flask 2.3.3 with a Blueprint-based modular structure.
- **ORM**: SQLAlchemy 2.0.21.
- **Database**: SQLite for development, PostgreSQL for production.
- **Authentication**: Dual system with Flask-Login for web UI and custom JWT for API endpoints.
- **Key Patterns**: Service layer for business logic, Repository pattern for data access, and UUID primary keys.
- **Core Models**: `Usuario`, `Operadora`, `Cliente`, `Processo`, `Execucao`, `Agendamento`.
- **Business Logic Flow**: Processes are auto-created monthly, external RPA downloads invoices, users manually approve/reject, and approved invoices are uploaded to the SAT system with real-time status tracking via `Execucao` records.
- **Server-Sent Events (SSE)**: Fully implemented for real-time log streaming from RPA executions, including automatic status updates and re-execution capabilities.
- **Scheduling System**: A background executor manages recurring tasks based on cron expressions, such as automatic monthly process creation and invoice downloads, using `croniter`.

### Feature Specifications
- **User Management**: Full CRUD for administrators, including an `api_externa_token` field for external API access.
- **Process Status Flow**: `AGUARDANDO_DOWNLOAD` → `AGUARDANDO_APROVACAO` → `AGUARDANDO_ENVIO_SAT` → `UPLOAD_REALIZADO`.
- **RPA Automation**: Operators can be configured for RPA (`possui_rpa`, `rpa_terceirizado`, `url_endpoint_rpa`).
- **Real-time Monitoring**: SSE provides instant log visibility and automatic status synchronization for RPA jobs.
- **Automated Tasks**: Configurable scheduled tasks for process creation and download initiation.
- **Manual Upload**: Allows manual PDF invoice upload to MinIO, updating process status and metadata.
- **Automated SAT Upload**: Processes are uploaded to SAT via an external RPA API, with real-time log tracking and automatic status updates.

### System Design Choices
- **Modularity**: Achieved through Flask Blueprints.
- **Data Integrity**: UUIDs for primary keys.
- **Extensibility**: Service and repository patterns.
- **High Availability**: Fallback to SQLite if PostgreSQL connection fails.
- **Deployment**: Dockerized deployment with Gunicorn for production.
- **Scheduling Architecture**: A background thread daemon (`executor.py`) checks and executes scheduled tasks (e.g., `CRIAR_PROCESSOS_MENSAIS`, `EXECUTAR_DOWNLOADS`) using cron expressions. Each task's execution is tracked and its next run time calculated.
- **SAT Upload Architecture**: Uses `AutomacaoPayloadSat` to structure data for the external RPA API, with a `JobMonitor` for polling job status and SSE for real-time log streaming, automatically updating process status upon completion or failure.

## External Dependencies

- **External RPA API**: `http://191.252.218.230:8000` for triggering RPA downloads (`POST /executar/{operadora}`), polling job status (`GET /jobs/{job_id}`), retrieving logs (`GET /jobs/{job_id}/logs`), and uploading to SAT (`POST /executar/sat`). Authenticated via a global JWT Bearer token.
- **Database**: SQLite (development), PostgreSQL (production).
- **MinIO S3 Storage**: `https://tirus-minio.cqojac.easypanel.host` for storing invoice PDFs in bucket 'beg', folder 'pdfs'.
- **Third-party Libraries**:
    - `Flask-Login`: Session management.
    - `Flask-SQLAlchemy`: ORM.
    - `croniter`: For scheduling recurring tasks.
    - `boto3`: AWS S3 SDK for MinIO integration.