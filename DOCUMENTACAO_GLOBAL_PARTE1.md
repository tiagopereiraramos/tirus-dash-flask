# DOCUMENTAÇÃO GLOBAL COMPLETA - PARTE 1
## Sistema de Orquestração RPA BEG Telecomunicações - Tirus Dashboard Flask

**Versão:** 1.0.0
**Data:** 2025-01-14
**Autor:** Sistema de Documentação Automatizada
**Propósito:** Transferência completa de contexto para refinamento do projeto

---

## ÍNDICE GERAL

### PARTE 1 (Este Documento)
1. [Visão Geral Executiva](#1-visão-geral-executiva)
2. [Arquitetura de Alto Nível](#2-arquitetura-de-alto-nível)
3. [Setup e Deploy](#3-setup-e-deploy)
4. [Inventário de Módulos Flask](#4-inventário-de-módulos-flask)
5. [Domínio e Modelagem de Dados](#5-domínio-e-modelagem-de-dados)

### PARTE 2 (Documento Separado)
6. Integrações e APIs Externas
7. Plataforma RPA
8. Processos de Negócio
9. Frontend e UX
10. Jobs, Scripts e Ferramentas Auxiliares
11. Monitoramento, Logs e Notificações
12. Segurança e Compliance
13. Qualidade e Testes
14. Governança de Código
15. Roadmap e Histórico

---

## 1. VISÃO GERAL EXECUTIVA

### 1.1 Objetivo do Sistema

O **Tirus Dashboard Flask** é um sistema de orquestração RPA (Robotic Process Automation) desenvolvido para automatizar o processo de download de faturas de telecomunicações de múltiplas operadoras e envio automático para o sistema SAT (Sistema de Apuração de Tributos) da BEG Telecomunicações.

**Escopo Principal:**
- Download automatizado de faturas de telecomunicações (Embratel, Vivo, Oi, DigitalNet)
- Gestão de processos mensais por cliente
- Aprovação manual de faturas antes do envio
- Upload automatizado para sistema SAT
- Monitoramento em tempo real de execuções RPA
- Integração com APIs externas de RPA terceirizado

### 1.2 Stakeholders e Usuários

**Perfis de Usuário:**
1. **ADMINISTRADOR**
   - Gerenciamento completo do sistema
   - Criação/manutenção de usuários, operadoras e clientes
   - Configuração de parâmetros globais
   - Acesso a logs e relatórios de auditoria

2. **APROVADOR**
   - Aprovação/rejeição de processos de faturamento
   - Validação de dados antes do envio ao SAT
   - Monitoramento de status de processos

3. **OPERADOR**
   - Execução manual de operações RPA
   - Upload manual de faturas quando necessário
   - Visualização de processos

### 1.3 Status Atual do Sistema

**Versão:** 1.0.0 (Beta)
**Ambiente de Produção:** Ativo
**Banco de Dados:** PostgreSQL (produção) / SQLite (desenvolvimento)
**Framework:** Flask 2.3.3
**Python:** 3.11+

**Funcionalidades Implementadas:**
- ✅ Gestão completa de clientes, operadoras e processos
- ✅ Sistema de autenticação e autorização por perfis
- ✅ Integração com RPA terceirizado via API externa
- ✅ Monitoramento em tempo real de jobs RPA
- ✅ Sistema de agendamentos para execução automática
- ✅ Dashboard de monitoramento e estatísticas
- ✅ Logs detalhados de execuções
- ✅ Upload automatizado para SAT

**Funcionalidades Pendentes/Em Refinamento:**
- ⏳ Sistema de notificações omnicanal (Slack, Telegram, Email)
- ⏳ Testes automatizados completos
- ⏳ Otimização de queries e cache
- ⏳ Documentação de API REST completa

### 1.4 Tecnologias Principais

**Backend:**
- Flask 2.3.3 (Framework web)
- SQLAlchemy 2.0.21 (ORM)
- PostgreSQL (banco de dados produção)
- SQLite (desenvolvimento)
- Flask-Login (autenticação)
- Flask-WTF (formulários e CSRF)
- Celery + Redis (tarefas assíncronas - planejado)
- Pydantic (validação de dados)

**Frontend:**
- Jinja2 (templates)
- Bootstrap 4 (CSS framework)
- jQuery (JavaScript)
- Feather Icons (ícones)
- Toastr (notificações)
- Datta Able Theme (template base)

**RPA e Automação:**
- Selenium 4.15.0 (automação web)
- WebDriver Manager (gerenciamento de drivers)
- Requests (HTTP)
- BeautifulSoup4 (parsing HTML)

**DevOps:**
- Docker + Docker Compose
- Gunicorn (WSGI server)
- Nginx (proxy reverso)
- Traefik (load balancer - opcional)

---

## 2. ARQUITETURA DE ALTO NÍVEL

### 2.1 Diagrama Arquitetural

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Templates  │  │   JavaScript │  │     CSS      │     │
│  │    Jinja2    │  │   (jQuery)   │  │  (Bootstrap) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APLICAÇÃO                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Flask Application (apps/)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │   Home   │ │   Auth   │ │Processos │ │ Clientes │ │  │
│  │  │   Blueprint         │ │   Blueprint        │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │Operadoras│ │Agendamentos│ │API Externa│ │  RPA   │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE SERVIÇOS                        │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  API Externa    │  │   Serviço RPA    │                │
│  │    Service      │  │   Concentrador    │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Monitoramento    │  │   Agendamentos  │                │
│  │    Tempo Real     │  │      Service     │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE DADOS                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           SQLAlchemy ORM (apps/models/)              │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │ Processo │ │ Cliente  │ │ Operadora│          │  │
│  │  └──────────┘ └──────────┘ └──────────┘          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │ Execucao │ │ Agendamento│ │ Usuario  │          │  │
│  │  └──────────┘ └──────────┘ └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE PERSISTÊNCIA                   │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   PostgreSQL    │  │   MinIO/S3       │                │
│  │   (Produção)    │  │   (Armazenamento)│                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA EXTERNA                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  API Externa RPA │  │   Sistema SAT    │                │
│  │  (Terceirizado)  │  │   (BEG)          │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Fluxos Principais

#### 2.2.1 Fluxo de Download de Fatura

```
1. Processo criado (automático ou manual)
   ↓
2. Status: AGUARDANDO_DOWNLOAD
   ↓
3. Usuário inicia download ou agendamento executa
   ↓
4. Sistema verifica operadora (RPA interno ou terceirizado)
   ↓
5. Se terceirizado: Envia payload para API externa
   Se interno: Executa RPA local (Selenium)
   ↓
6. Cria registro de Execução
   ↓
7. Aguarda resultado (polling ou webhook)
   ↓
8. Atualiza Processo com dados da fatura
   ↓
9. Status: AGUARDANDO_APROVACAO
```

#### 2.2.2 Fluxo de Aprovação e Envio SAT

```
1. Processo com status AGUARDANDO_APROVACAO
   ↓
2. Aprovador visualiza fatura e dados
   ↓
3. Aprova ou rejeita
   ↓
4a. Se aprovado:
   - Status: AGUARDANDO_ENVIO_SAT
   - Usuário pode enviar para SAT
   ↓
4b. Se rejeitado:
   - Status: AGUARDANDO_DOWNLOAD
   - Retorna para novo download
   ↓
5. Envio para SAT (RPA terceirizado)
   ↓
6. Status: UPLOAD_REALIZADO
```

### 2.3 Decisões Arquiteturais Importantes

**1. Uso de Blueprints Flask**
- Modularização clara por domínio
- Facilita manutenção e testes
- Permite versionamento de APIs

**2. Modelos SQLAlchemy com GUID**
- Identificadores únicos universais (UUID)
- Compatibilidade PostgreSQL/SQLite
- Facilita migrações e integrações

**3. RPA Terceirizado como Padrão**
- Maioria das operadoras usa API externa
- RPA interno apenas para casos específicos
- Facilita escalabilidade

**4. Status-Based Workflow**
- Estados explícitos facilitam rastreamento
- Transições controladas via métodos do modelo
- Auditoria completa de mudanças

**5. Execuções como Entidade Separada**
- Histórico completo de tentativas
- Permite análise de falhas
- Suporte a retry automático

---

## 3. SETUP E DEPLOY

### 3.1 Requisitos do Sistema

**Hardware Mínimo:**
- CPU: 2 cores
- RAM: 4GB
- Disco: 20GB

**Software:**
- Python 3.11 ou superior
- PostgreSQL 12+ (produção) ou SQLite (desenvolvimento)
- Redis 6+ (opcional, para Celery)
- Docker 20+ e Docker Compose (recomendado)

**Dependências Python:**
- Ver `requirements.txt` e `pyproject.toml`
- Principais: Flask 2.3.3, SQLAlchemy 2.0.21, Selenium 4.15.0

### 3.2 Setup Local (Desenvolvimento)

**1. Clonar repositório:**
```bash
git clone <repository-url>
cd tirus-dash-flask
```

**2. Criar ambiente virtual:**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

**3. Instalar dependências:**
```bash
pip install -r requirements.txt
# ou usando uv (recomendado)
uv pip install -r requirements.txt
```

**4. Configurar variáveis de ambiente:**
```bash
cp env.sample .env
# Editar .env com suas configurações
```

**5. Inicializar banco de dados:**
```bash
python create_tables.py
# ou
python inicializar_banco.py
```

**6. Criar usuário inicial:**
```bash
python criar_usuario_teste.py
```

**7. Executar aplicação:**
```bash
python run.py
# ou
flask run
```

A aplicação estará disponível em `http://localhost:5050`

### 3.3 Setup com Docker

**1. Build da imagem:**
```bash
docker-compose build
```

**2. Iniciar serviços:**
```bash
docker-compose up -d
```

**3. Ver logs:**
```bash
docker-compose logs -f
```

**4. Parar serviços:**
```bash
docker-compose down
```

### 3.4 Deploy em Produção

#### 3.4.1 Variáveis de Ambiente Críticas

```bash
# .env (produção)
DEBUG=False
FLASK_ENV=production
SECRET_KEY=<gerar-chave-segura-aleatoria>

# Banco de Dados
DB_ENGINE=postgresql
DB_HOST=<host-postgres>
DB_NAME=tirus_production
DB_USERNAME=<usuario>
DB_PASS=<senha-forte>
DB_PORT=5432

# API Externa
API_EXTERNA_URL=http://191.252.218.230:8000
API_EXTERNA_TOKEN=<token-jwt>
API_EXTERNA_USERNAME=<username>
API_EXTERNA_PASSWORD=<password>

# Assets
ASSETS_ROOT=/static/assets
```

#### 3.4.2 Deploy com Docker Compose (Produção)

```bash
# Usar docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d --build
```

#### 3.4.3 Deploy Manual (Servidor)

**1. Instalar dependências do sistema:**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv postgresql nginx
```

**2. Configurar PostgreSQL:**
```bash
sudo -u postgres psql
CREATE DATABASE tirus_production;
CREATE USER tirus_user WITH PASSWORD 'senha_segura';
GRANT ALL PRIVILEGES ON DATABASE tirus_production TO tirus_user;
```

**3. Configurar Nginx:**
```bash
sudo cp nginx/appseed-app.conf /etc/nginx/sites-available/tirus
sudo ln -s /etc/nginx/sites-available/tirus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**4. Configurar Gunicorn:**
```bash
gunicorn --config gunicorn-cfg.py run:app
```

**5. Criar serviço systemd:**
```bash
sudo nano /etc/systemd/system/tirus.service
```

Conteúdo do serviço:
```ini
[Unit]
Description=Tirus Dashboard Flask
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tirus-dash-flask
Environment="PATH=/opt/tirus-dash-flask/venv/bin"
ExecStart=/opt/tirus-dash-flask/venv/bin/gunicorn --config gunicorn-cfg.py run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**6. Ativar serviço:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tirus
sudo systemctl start tirus
```

### 3.5 Scripts de Deploy Disponíveis

- `deploy_manual.sh` - Deploy manual passo a passo
- `deploy_ssh.sh` - Deploy via SSH
- `build.sh` - Build da aplicação
- `build-easypanel.sh` - Build para Easypanel
- `forcar_recarregamento.sh` - Forçar reload da aplicação

### 3.6 Migrações e Atualizações

**Executar migrações:**
```bash
flask db upgrade
```

**Criar nova migração:**
```bash
flask db migrate -m "descricao da migracao"
```

**Scripts de migração disponíveis:**
- `migrar_banco_usuarios.py` - Migração de usuários
- `migrar_agendamentos_operadora.py` - Agendamentos por operadora
- `migrar_operadoras_rpa_terceirizado.py` - Configuração RPA terceirizado
- `migrar_sat_como_operadora.py` - SAT como operadora
- `migrar_remover_campos_obsoletos.py` - Limpeza de campos obsoletos

---

## 4. INVENTÁRIO DE MÓDULOS FLASK

### 4.1 Estrutura de Blueprints

Todos os blueprints são registrados em `apps/__init__.py`:

```python
from apps.home import home_bp
from apps.authentication import init_app as init_auth
from apps.clientes import clientes_bp
from apps.operadoras import operadoras_bp
from apps.processos import processos_bp
from apps.usuarios import usuarios_bp
from apps.agendamentos import agendamentos_bp
from apps.api_externa.routes import bp as api_externa_bp
from apps.api_externa.routes_externos import bp_externos as api_externos_bp
from apps.api_externa.routes_avancadas import bp_avancadas as api_avancadas_bp
from apps.api_externa.routes_monitoramento import bp_monitoramento as api_monitoramento_bp
from apps.api_externa.routes_tempo_real import api_tempo_real_bp
from apps.api_externa.routes_logs_tempo_real import api_logs_tempo_real_bp
```

### 4.2 Módulos Principais

#### 4.2.1 `apps/home/`

**Responsabilidade:** Dashboard principal e páginas estáticas

**Rotas:**
- `GET /` - Página inicial (dashboard)
- `GET /index` - Alias para página inicial

**Templates:**
- `templates/home/index.html` - Dashboard principal
- `templates/home/page-404.html` - Página 404
- `templates/home/page-500.html` - Página 500

**Dependências:** Nenhuma específica

#### 4.2.2 `apps/authentication/`

**Responsabilidade:** Autenticação e autorização de usuários

**Rotas:**
- `GET/POST /login` - Login de usuário
- `GET/POST /register` - Registro de novo usuário
- `GET /logout` - Logout
- `GET /github` - OAuth GitHub (opcional)

**Formulários:**
- `LoginForm` - Formulário de login
- `RegisterForm` - Formulário de registro

**Modelos:**
- Usa `apps.models.usuario.Usuario` (modelo principal)
- `apps.authentication.models.Users` (legado, não usado)

**Dependências:**
- Flask-Login para gerenciamento de sessão
- Flask-WTF para CSRF protection
- Werkzeug para hash de senhas

#### 4.2.3 `apps/clientes/`

**Responsabilidade:** Gestão de clientes

**Rotas:**
- `GET /clientes` - Listagem de clientes
- `GET /clientes/novo` - Formulário de novo cliente
- `POST /clientes/novo` - Criar cliente
- `GET /clientes/<id>` - Detalhes do cliente
- `GET /clientes/<id>/editar` - Formulário de edição
- `POST /clientes/<id>/editar` - Atualizar cliente
- `POST /clientes/<id>/excluir` - Excluir cliente
- `GET/POST /clientes/importar` - Importar clientes via CSV

**Formulários:**
- `ClienteForm` - Formulário de cliente

**Modelos:**
- `apps.models.cliente.Cliente`

**Dependências:**
- `apps.models.operadora.Operadora`

#### 4.2.4 `apps/operadoras/`

**Responsabilidade:** Gestão de operadoras de telecomunicações

**Rotas:**
- `GET /operadoras` - Listagem de operadoras
- `GET /operadoras/novo` - Formulário de nova operadora
- `POST /operadoras/novo` - Criar operadora
- `GET /operadoras/<id>` - Detalhes da operadora
- `GET /operadoras/<id>/editar` - Formulário de edição
- `POST /operadoras/<id>/editar` - Atualizar operadora
- `POST /operadoras/<id>/excluir` - Excluir operadora

**Formulários:**
- `OperadoraForm` - Formulário de operadora

**Modelos:**
- `apps.models.operadora.Operadora`

**Dependências:** Nenhuma

#### 4.2.5 `apps/processos/`

**Responsabilidade:** Gestão de processos mensais de faturamento

**Rotas Principais:**
- `GET /processos` - Listagem de processos (com filtros)
- `GET /processos/novo` - Formulário de novo processo
- `POST /processos/novo` - Criar processo
- `GET /processos/<id>` - Detalhes do processo
- `GET /processos/<id>/editar` - Formulário de edição
- `POST /processos/<id>/editar` - Atualizar processo
- `POST /processos/<id>/aprovar` - Aprovar processo
- `POST /processos/<id>/rejeitar` - Rejeitar processo
- `POST /processos/<id>/download-rpa` - Executar download RPA
- `POST /processos/<id>/enviar-sat` - Enviar para SAT
- `GET /processos/<id>/execucoes` - Listar execuções do processo
- `GET /processos/criar-mensais` - Criar processos mensais em lote
- `GET /processos/dashboard-monitoramento` - Dashboard de monitoramento
- `GET /processos/dashboard-api-externa` - Dashboard API externa

**Formulários:**
- `ProcessoForm` - Formulário de processo
- `CriarProcessosMensaisForm` - Formulário para criação em lote

**Modelos:**
- `apps.models.processo.Processo`
- `apps.models.execucao.Execucao`

**Dependências:**
- `apps.models.cliente.Cliente`
- `apps.rpa.base.ServicoRPA`
- `apps.api_externa.services.APIExternaService`

#### 4.2.6 `apps/usuarios/`

**Responsabilidade:** Gestão de usuários do sistema

**Rotas:**
- `GET /usuarios` - Listagem de usuários (apenas admin)
- `GET /usuarios/novo` - Formulário de novo usuário
- `POST /usuarios/novo` - Criar usuário
- `GET /usuarios/<id>` - Detalhes do usuário
- `GET /usuarios/<id>/editar` - Formulário de edição
- `POST /usuarios/<id>/editar` - Atualizar usuário
- `POST /usuarios/<id>/excluir` - Excluir usuário
- `GET /usuarios/perfil` - Perfil do usuário logado
- `GET/POST /usuarios/alterar-senha` - Alterar senha

**Formulários:**
- `UsuarioForm` - Formulário de usuário
- `AlterarSenhaForm` - Formulário de alteração de senha

**Modelos:**
- `apps.models.usuario.Usuario`

**Dependências:** Nenhuma

#### 4.2.7 `apps/agendamentos/`

**Responsabilidade:** Gestão de agendamentos para execução automática

**Rotas:**
- `GET /agendamentos` - Listagem de agendamentos
- `GET /agendamentos/novo` - Formulário de novo agendamento
- `POST /agendamentos/novo` - Criar agendamento
- `GET /agendamentos/<id>` - Detalhes do agendamento
- `GET /agendamentos/<id>/editar` - Formulário de edição
- `POST /agendamentos/<id>/editar` - Atualizar agendamento
- `POST /agendamentos/<id>/ativar` - Ativar agendamento
- `POST /agendamentos/<id>/desativar` - Desativar agendamento
- `POST /agendamentos/<id>/executar` - Executar agendamento manualmente

**Formulários:**
- `AgendamentoForm` - Formulário de agendamento

**Modelos:**
- `apps.models.agendamento.Agendamento`

**Dependências:**
- `apps.models.operadora.Operadora` (opcional)

#### 4.2.8 `apps/api_externa/`

**Responsabilidade:** Integração com API externa de RPA terceirizado

**Sub-módulos:**
- `routes.py` - Rotas básicas da API externa
- `routes_externos.py` - Rotas para operações externas
- `routes_avancadas.py` - Rotas avançadas
- `routes_monitoramento.py` - Rotas de monitoramento
- `routes_tempo_real.py` - Rotas de monitoramento em tempo real
- `routes_logs_tempo_real.py` - Rotas de logs em tempo real
- `services.py` - Serviços principais de integração
- `services_externos.py` - Serviços funcionais externos
- `client.py` - Cliente HTTP para API externa
- `auth.py` - Autenticação na API externa
- `cache.py` - Sistema de cache
- `monitor.py` - Monitoramento de jobs
- `monitor_tempo_real.py` - Monitoramento em tempo real
- `settings.py` - Configurações da API externa
- `models.py` - Modelos Pydantic para payloads
- `reports.py` - Relatórios e estatísticas
- `notifications.py` - Sistema de notificações

**Rotas Principais:**
- `POST /api/externa/executar-rpa` - Executar RPA externo
- `POST /api/externa/executar-sat` - Executar upload SAT
- `GET /api/externa/status/<job_id>` - Status de job
- `GET /api/externa/monitoramento` - Monitoramento geral
- `GET /api/externa/tempo-real/status` - Status em tempo real
- `GET /api/externa/logs/<job_id>` - Logs de execução

**Dependências:**
- `requests` para HTTP
- `pydantic` para validação
- `redis` para cache (opcional)

#### 4.2.9 `apps/rpa/`

**Responsabilidade:** Sistema RPA interno (quando não usa terceirizado)

**Estrutura:**
```
apps/rpa/
├── __init__.py
├── base.py              # Classe base e concentrador
├── rpa_base.py          # Implementação base RPA
├── routes.py            # Rotas RPA (se houver)
└── rpas/
    ├── __init__.py
    ├── embratel_rpa.py   # RPA Embratel
    ├── vivo_rpa.py       # RPA Vivo
    ├── oi_rpa.py         # RPA Oi
    ├── digitalnet_rpa.py # RPA DigitalNet
    └── sat_rpa.py        # RPA SAT (upload)
```

**Classes Principais:**
- `RPABase` - Classe abstrata base para todos os RPAs
- `ConcentradorRPA` - Registra e gerencia todos os RPAs
- `ServicoRPA` - Serviço que integra RPA com processos
- Implementações específicas por operadora

**Dependências:**
- `selenium` para automação web
- `webdriver-manager` para gerenciamento de drivers

---

## 5. DOMÍNIO E MODELAGEM DE DADOS

### 5.1 Diagrama Entidade-Relacionamento

```
┌──────────────┐         ┌──────────────┐
│   Usuario    │         │  Operadora   │
│──────────────│         │──────────────│
│ id (GUID)    │◄──┐     │ id (GUID)    │◄──┐
│ nome         │   │     │ codigo       │   │
│ email        │   │     │ nome         │   │
│ username     │   │     │ possui_rpa   │   │
│ perfil       │   │     │ rpa_terceirizado│
│ status_ativo │   │     │ url_endpoint_rpa│
└──────────────┘   │     │ status_ativo │   │
       │           │     └──────────────┘   │
       │           │            │           │
       │           │            │ 1:N       │
       │           │            │           │
       │           │            ▼           │
       │           │     ┌──────────────┐   │
       │           │     │   Cliente    │   │
       │           │     │──────────────│   │
       │           │     │ id (GUID)    │   │
       │           │     │ razao_social │   │
       │           │     │ cnpj         │   │
       │           │     │ operadora_id │───┘
       │           │     │ login_portal │
       │           │     │ senha_portal │
       │           │     │ status_ativo │
       │           │     └──────────────┘
       │           │            │
       │           │            │ 1:N
       │           │            │
       │           │            ▼
       │           │     ┌──────────────┐
       │           │     │   Processo   │
       │           │     │──────────────│
       │           │     │ id (GUID)    │
       │           │     │ cliente_id   │───┘
       │           │     │ mes_ano      │
       │           │     │ status       │
       │           │     │ url_fatura   │
       │           │     │ valor_fatura │
       │           │     │ aprovado_por │───┐
       │           │     └──────────────┘   │
       │           │            │           │
       │           │            │ 1:N       │
       │           │            │           │
       │           │            ▼           │
       │           │     ┌──────────────┐   │
       │           │     │  Execucao    │   │
       │           │     │──────────────│   │
       │           │     │ id (GUID)    │   │
       │           │     │ processo_id  │───┘
       │           │     │ tipo_execucao│
       │           │     │ status       │
       │           │     │ executado_por│───┘
       │           │     │ resultado    │
       │           │     └──────────────┘
       │           │
       │           │
       │           │     ┌──────────────┐
       │           │     │ Agendamento  │
       │           │     │──────────────│
       │           │     │ id (GUID)    │
       │           │     │ nome         │
       │           │     │ cron_expr    │
       │           │     │ tipo         │
       │           │     │ operadora_id │───┐
       │           │     │ status_ativo │   │
       │           │     └──────────────┘   │
       │           │                         │
       └───────────┴─────────────────────────┘
```

### 5.2 Modelos Principais

#### 5.2.1 `BaseModel` (apps/models/base.py)

**Propósito:** Classe base para todos os modelos

**Campos Herdados:**
- `id` (GUID) - Identificador único universal
- `data_criacao` (DateTime) - Data de criação
- `data_atualizacao` (DateTime) - Data de última atualização

**Métodos:**
- `to_dict()` - Serialização para dicionário

#### 5.2.2 `Usuario` (apps/models/usuario.py)

**Tabela:** `usuarios`

**Campos:**
- `nome_completo` (String) - Nome completo
- `email` (String, unique) - Email
- `username` (String, unique) - Nome de usuário
- `password_hash` (String) - Hash da senha
- `telefone` (String, optional) - Telefone
- `perfil_usuario` (String) - ADMIN, APROVADOR, OPERADOR
- `status_ativo` (Boolean) - Status ativo/inativo

**Relacionamentos:**
- `processos_aprovados` - Processos aprovados por este usuário
- `execucoes_realizadas` - Execuções realizadas por este usuário

**Métodos Importantes:**
- `check_password(password)` - Verifica senha
- `set_password(password)` - Define senha
- `get_permissoes()` - Retorna lista de permissões
- `tem_permissao(permissao)` - Verifica permissão específica

#### 5.2.3 `Operadora` (apps/models/operadora.py)

**Tabela:** `operadoras`

**Campos:**
- `nome` (String, unique) - Nome da operadora
- `codigo` (String, unique) - Código (EMBRATEL, VIVO, OI, etc.)
- `possui_rpa` (Boolean) - Possui RPA interno
- `rpa_terceirizado` (Boolean) - Usa RPA terceirizado
- `url_endpoint_rpa` (String, optional) - URL do endpoint RPA
- `rpa_auth_token` (String, optional) - Token de autenticação
- `url_portal` (String, optional) - URL do portal
- `configuracao_rpa` (JSON, optional) - Configurações JSON
- `status_ativo` (Boolean) - Status ativo/inativo

**Relacionamentos:**
- `clientes` - Clientes desta operadora
- `agendamentos` - Agendamentos para esta operadora

**Propriedades:**
- `tem_rpa_configurado` - Verifica se tem RPA configurado
- `endpoint_rpa_ativo` - Retorna endpoint ativo

#### 5.2.4 `Cliente` (apps/models/cliente.py)

**Tabela:** `clientes`

**Campos:**
- `hash_unico` (String, unique) - Hash único do cliente
- `razao_social` (String) - Razão social
- `nome_sat` (String) - Nome no sistema SAT
- `cnpj` (String) - CNPJ
- `operadora_id` (GUID, FK) - Operadora associada
- `filtro` (String, optional) - Filtro para busca
- `servico` (String) - Tipo de serviço
- `dados_sat` (Text, optional) - Dados para SAT
- `unidade` (String) - Unidade/filial
- `login_portal` (String, optional) - Login do portal
- `senha_portal` (String, optional) - Senha do portal
- `cpf` (String, optional) - CPF adicional
- `status_ativo` (Boolean) - Status ativo/inativo
- `vinculado_sat` (Boolean) - Vinculado ao SAT

**Constraints:**
- Unique: `cnpj + operadora_id + unidade + servico`

**Relacionamentos:**
- `operadora` - Operadora associada
- `processos` - Processos deste cliente

**Métodos:**
- `gerar_hash_unico()` - Gera hash único
- `atualizar_hash()` - Atualiza hash

#### 5.2.5 `Processo` (apps/models/processo.py)

**Tabela:** `processos`

**Campos:**
- `cliente_id` (GUID, FK) - Cliente associado
- `mes_ano` (String) - Mês/ano no formato MM/AAAA
- `status_processo` (String) - Status atual
- `url_fatura` (String, optional) - URL da fatura
- `caminho_s3_fatura` (String, optional) - Caminho S3
- `data_vencimento` (Date, optional) - Data de vencimento
- `valor_fatura` (DECIMAL, optional) - Valor da fatura
- `aprovado_por_usuario_id` (GUID, FK, optional) - Usuário aprovador
- `data_aprovacao` (DateTime, optional) - Data de aprovação
- `enviado_para_sat` (Boolean) - Enviado para SAT
- `data_envio_sat` (DateTime, optional) - Data de envio
- `upload_manual` (Boolean) - Upload manual
- `criado_automaticamente` (Boolean) - Criado automaticamente
- `observacoes` (Text, optional) - Observações

**Constraints:**
- Unique: `cliente_id + mes_ano`

**Status Possíveis:**
- `AGUARDANDO_DOWNLOAD` - Aguardando download
- `AGUARDANDO_APROVACAO` - Aguardando aprovação
- `AGUARDANDO_ENVIO_SAT` - Aguardando envio SAT
- `UPLOAD_REALIZADO` - Upload realizado

**Relacionamentos:**
- `cliente` - Cliente associado
- `aprovador` - Usuário que aprovou
- `execucoes` - Execuções do processo

**Métodos Importantes:**
- `aprovar(usuario_id, observacoes)` - Aprova processo
- `rejeitar(observacoes)` - Rejeita processo
- `marcar_download_completo()` - Marca download completo
- `enviar_para_sat()` - Marca como enviado para SAT
- `pode_transicionar_para(novo_status)` - Valida transição

#### 5.2.6 `Execucao` (apps/models/execucao.py)

**Tabela:** `execucoes`

**Campos:**
- `processo_id` (GUID, FK) - Processo associado
- `tipo_execucao` (String) - DOWNLOAD_FATURA, UPLOAD_SAT, UPLOAD_MANUAL
- `status_execucao` (String) - Status atual
- `classe_rpa_utilizada` (String, optional) - Classe RPA usada
- `parametros_entrada` (JSON, optional) - Parâmetros de entrada
- `resultado_saida` (JSON, optional) - Resultado da execução
- `data_inicio` (DateTime) - Data de início
- `data_fim` (DateTime, optional) - Data de fim
- `mensagem_log` (Text, optional) - Log detalhado
- `url_arquivo_s3` (String, optional) - URL do arquivo
- `numero_tentativa` (Integer) - Número da tentativa
- `detalhes_erro` (JSON, optional) - Detalhes do erro
- `executado_por_usuario_id` (GUID, FK, optional) - Usuário executor
- `ip_origem` (String, optional) - IP de origem
- `user_agent` (Text, optional) - User agent

**Status Possíveis:**
- `EXECUTANDO` - Em execução
- `CONCLUIDO` - Concluído com sucesso
- `FALHOU` - Falhou
- `TENTANDO_NOVAMENTE` - Tentando novamente
- `CANCELADO` - Cancelado
- `TIMEOUT` - Timeout

**Relacionamentos:**
- `processo` - Processo associado
- `executor` - Usuário que executou

**Métodos:**
- `finalizar_com_sucesso(resultado, mensagem)` - Finaliza com sucesso
- `finalizar_com_erro(erro, detalhes)` - Finaliza com erro
- `marcar_timeout()` - Marca como timeout

#### 5.2.7 `Agendamento` (apps/models/agendamento.py)

**Tabela:** `agendamentos`

**Campos:**
- `nome_agendamento` (String, unique) - Nome único
- `descricao` (Text, optional) - Descrição
- `cron_expressao` (String) - Expressão cron
- `tipo_agendamento` (String) - Tipo do agendamento
- `status_ativo` (Boolean) - Status ativo/inativo
- `proxima_execucao` (DateTime, optional) - Próxima execução
- `ultima_execucao` (DateTime, optional) - Última execução
- `operadora_id` (GUID, FK, optional) - Operadora associada
- `parametros_execucao` (JSON, optional) - Parâmetros JSON

**Tipos Possíveis:**
- `CRIAR_PROCESSOS_MENSAIS` - Cria processos mensais
- `EXECUTAR_DOWNLOADS` - Executa downloads
- `ENVIAR_RELATORIOS` - Envia relatórios
- `LIMPEZA_LOGS` - Limpeza de logs
- `BACKUP_DADOS` - Backup de dados

**Relacionamentos:**
- `operadora` - Operadora associada (opcional)

**Métodos:**
- `validar_cron_expressao()` - Valida expressão cron
- `marcar_execucao(proxima_execucao)` - Marca execução
- `ativar()` / `desativar()` - Ativa/desativa

### 5.3 Enums e Constantes

**StatusProcesso:**
```python
AGUARDANDO_DOWNLOAD = "AGUARDANDO_DOWNLOAD"
AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
AGUARDANDO_ENVIO_SAT = "AGUARDANDO_ENVIO_SAT"
UPLOAD_REALIZADO = "UPLOAD_REALIZADO"
```

**TipoExecucao:**
```python
DOWNLOAD_FATURA = "DOWNLOAD_FATURA"
UPLOAD_SAT = "UPLOAD_SAT"
UPLOAD_MANUAL = "UPLOAD_MANUAL"
```

**StatusExecucao:**
```python
EXECUTANDO = "EXECUTANDO"
CONCLUIDO = "CONCLUIDO"
FALHOU = "FALHOU"
TENTANDO_NOVAMENTE = "TENTANDO_NOVAMENTE"
CANCELADO = "CANCELADO"
TIMEOUT = "TIMEOUT"
```

**PerfilUsuario:**
```python
ADMIN = "ADMIN"
APROVADOR = "APROVADOR"
OPERADOR = "OPERADOR"
```

### 5.4 Regras de Integridade

**1. Unicidade de Processo:**
- Um cliente só pode ter um processo por mês/ano
- Constraint: `uq_processo_cliente_mes_ano`

**2. Unicidade de Cliente:**
- CNPJ + Operadora + Unidade + Serviço deve ser único
- Constraint: `uq_cliente_cnpj_operadora_unidade_servico`

**3. Hash Único do Cliente:**
- Cada cliente tem hash único baseado em dados-chave
- Usado para detectar duplicatas

**4. Cascata de Exclusão:**
- Excluir cliente → exclui processos → exclui execuções
- Excluir operadora → restringe exclusão (RESTRICT em clientes)
- Excluir processo → exclui execuções (CASCADE)

**5. Validação de Status:**
- Transições de status são controladas por métodos
- Propriedades verificam se transição é válida

---

## PRÓXIMOS PASSOS

**Leia a PARTE 2** (`DOCUMENTACAO_GLOBAL_PARTE2.md`) para:
- Integrações e APIs Externas
- Plataforma RPA detalhada
- Processos de Negócio completos
- Frontend e UX
- Scripts e ferramentas
- Monitoramento e logs
- Segurança
- Testes
- Governança
- Roadmap

---

**Fim da Parte 1**
