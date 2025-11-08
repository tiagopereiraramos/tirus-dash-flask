# MANUAL TÉCNICO COMPLETO
## Sistema de Orquestração RPA - BEG Telecomunicações

**Versão:** 2.0  
**Última Atualização:** 08/11/2025  
**Autor:** Equipe Técnica BRM Solutions

---

## ÍNDICE

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura Técnica](#2-arquitetura-técnica)
3. [Modelos de Banco de Dados](#3-modelos-de-banco-de-dados)
4. [Estrutura de Pastas e Arquivos](#4-estrutura-de-pastas-e-arquivos)
5. [Fluxo de Dados](#5-fluxo-de-dados)
6. [Guia de Modificação por Módulo](#6-guia-de-modificação-por-módulo)
7. [Sistema de Autenticação](#7-sistema-de-autenticação)
8. [Integração com API Externa](#8-integração-com-api-externa)
9. [Upload Manual e MinIO](#9-upload-manual-e-minio)
10. [Sistema de Agendamentos](#10-sistema-de-agendamentos)
11. [Server-Sent Events (SSE)](#11-server-sent-events-sse)
12. [Troubleshooting e Debugging](#12-troubleshooting-e-debugging)

---

## 1. VISÃO GERAL DO SISTEMA

### 1.1 Propósito

O sistema automatiza o download de faturas de operadoras de telecomunicações (OI, VIVO, EMBRATEL, DigitalNet) e o envio para o sistema SAT (Sistema de Automação Tributária) da BEG Telecomunicações.

### 1.2 Tecnologias Principais

| Componente | Tecnologia | Versão |
|-----------|-----------|--------|
| **Backend** | Flask | 2.3.3 |
| **ORM** | SQLAlchemy | 2.0.21 |
| **Database Dev** | SQLite | 3.x |
| **Database Prod** | PostgreSQL | 14+ |
| **Frontend** | Jinja2 + Bootstrap 4 | - |
| **Storage** | MinIO S3 | Latest |
| **Auth Web** | Flask-Login | 0.6.2 |
| **Auth API** | JWT Custom | - |
| **Scheduling** | croniter | 1.4.1 |
| **Real-time** | SSE (Server-Sent Events) | - |

### 1.3 Conceitos-Chave

- **Processo**: Representa o ciclo completo de uma fatura (download → aprovação → upload SAT)
- **Execução**: Tentativa individual de executar uma etapa do processo
- **Cliente**: Empresa que possui faturas a serem processadas
- **Operadora**: Empresa de telecomunicações (Vivo, Oi, etc)
- **Agendamento**: Tarefa recorrente automatizada (criar processos mensais, downloads)

---

## 2. ARQUITETURA TÉCNICA

### 2.1 Padrões de Projeto

#### Blueprint Pattern (Flask)
Cada módulo é isolado em um Blueprint:
```python
# apps/processos/__init__.py
from flask import Blueprint

bp = Blueprint('processos', __name__, url_prefix='/processos')
```

#### Service Layer Pattern
Lógica de negócio separada das rotas:
```
Route (Controller) → Service (Business Logic) → Model (Data)
```

#### Repository Pattern
Acesso ao banco de dados centralizado nos modelos:
```python
# Model
class Cliente(BaseModel):
    @classmethod
    def buscar_ativos(cls):
        return cls.query.filter_by(status_ativo=True).all()
```

### 2.2 Estrutura em Camadas

```
┌─────────────────────────────────────┐
│      FRONTEND (Jinja2 + JS)         │
│   - Templates HTML                   │
│   - Bootstrap 4 (Datta Able)        │
│   - JavaScript (jQuery, SSE)        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         ROUTES (Controllers)        │
│   - Validação de entrada            │
│   - Autenticação (@login_required)  │
│   - Renderização de templates       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│       SERVICES (Business Logic)     │
│   - Regras de negócio               │
│   - Orquestração de operações       │
│   - Integração API Externa          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│         MODELS (Data Layer)         │
│   - SQLAlchemy ORM                  │
│   - Validações de dados             │
│   - Relacionamentos                 │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     DATABASE (SQLite/PostgreSQL)    │
└─────────────────────────────────────┘
```

### 2.3 Fluxo de Dados Completo

```
API Externa (RPA)
       ↓
JobMonitor (Polling)
       ↓
SSE (Real-time logs)
       ↓
Frontend (JavaScript)
       ↓
Update UI
```

---

## 3. MODELOS DE BANCO DE DADOS

### 3.1 Diagrama de Relacionamentos

```
┌─────────────────┐
│    Usuario      │
│                 │
│ • id (PK)       │
│ • email         │
│ • perfil        │
└─────────────────┘
        │
        │ 1:N (aprovador)
        ↓
┌─────────────────┐      1:N       ┌─────────────────┐
│    Processo     │◄────────────────│    Execucao     │
│                 │                 │                 │
│ • id (PK)       │                 │ • id (PK)       │
│ • cliente_id(FK)│                 │ • processo_id(FK)│
│ • mes_ano       │                 │ • tipo_execucao │
│ • status        │                 │ • job_id        │
└─────────────────┘                 └─────────────────┘
        ↑
        │ N:1
        │
┌─────────────────┐      N:1       ┌─────────────────┐
│    Cliente      │─────────────────│   Operadora     │
│                 │                 │                 │
│ • id (PK)       │                 │ • id (PK)       │
│ • hash_unico    │                 │ • codigo        │
│ • cnpj          │                 │ • possui_rpa    │
│ • operadora_id(FK)│               └─────────────────┘
└─────────────────┘

┌─────────────────┐
│  Agendamento    │
│                 │
│ • id (PK)       │
│ • cron_expressao│
│ • tipo          │
│ • parametros(JSON)│
└─────────────────┘
```

### 3.2 Modelo: Usuario

**Arquivo:** `apps/models/usuario.py`

```python
class Usuario(BaseModel):
    __tablename__ = 'usuarios'
    
    # Campos
    nome_completo: str          # Nome completo
    email: str (unique)         # Login
    telefone: str               # Notificações
    perfil_usuario: str         # ADMINISTRADOR, APROVADOR, OPERADOR
    status_ativo: bool          # Ativo/Inativo
    
    # Relacionamentos
    processos_aprovados → Processo.aprovador
    execucoes_realizadas → Execucao.executor
```

**Perfis de Usuário:**
- `ADMINISTRADOR`: Acesso total
- `APROVADOR`: Pode aprovar processos
- `OPERADOR`: Pode executar operações

**Onde Modificar:**
- **CRUD completo**: `apps/usuarios/routes_simple.py`
- **Formulários**: `apps/usuarios/forms.py`
- **Templates**: `apps/templates/usuarios/`

### 3.3 Modelo: Operadora

**Arquivo:** `apps/models/operadora.py`

```python
class Operadora(BaseModel):
    __tablename__ = 'operadoras'
    
    # Campos principais
    nome: str (unique)          # Ex: "Vivo", "Oi"
    codigo: str (unique)        # Ex: "VIVO", "OI"
    possui_rpa: bool            # Tem RPA configurado?
    status_ativo: bool          # Ativa?
    
    # RPA
    url_portal: str             # Portal da operadora
    classe_rpa: str             # Classe Python do RPA
    configuracao_rpa: JSON      # Config específica
    
    # Relacionamentos
    clientes → Cliente.operadora
```

**Onde Modificar:**
- **CRUD**: `apps/operadoras/routes.py`
- **Formulários**: `apps/operadoras/forms.py`
- **Templates**: `apps/templates/operadoras/`

### 3.4 Modelo: Cliente

**Arquivo:** `apps/models/cliente.py`

```python
class Cliente(BaseModel):
    __tablename__ = 'clientes'
    
    # Identificação única
    hash_unico: str (unique)    # Hash SHA-256 dos dados
    
    # Dados principais
    razao_social: str           # Razão social
    nome_sat: str               # Nome no SAT
    cnpj: str                   # CNPJ sem formatação
    
    # Relacionamento
    operadora_id: UUID (FK)     # Operadora associada
    
    # Dados de processamento
    filtro: str                 # Filtro de busca
    servico: str                # Tipo de serviço
    dados_sat: str              # Dados SAT
    unidade: str                # Unidade/Filial
    
    # Credenciais portal
    login_portal: str
    senha_portal: str
    cpf: str                    # CPF quando necessário
    
    # Relacionamentos
    operadora → Operadora.clientes
    processos → Processo.cliente
```

**Unicidade:**
```sql
UNIQUE(cnpj, operadora_id, unidade, servico)
```

**Onde Modificar:**
- **CRUD**: `apps/clientes/routes.py`
- **Importação CSV**: `scripts/importar_clientes_csv.py`
- **Templates**: `apps/templates/clientes/`

### 3.5 Modelo: Processo

**Arquivo:** `apps/models/processo.py`

```python
class Processo(BaseModel):
    __tablename__ = 'processos'
    
    # Identificação
    cliente_id: UUID (FK)
    mes_ano: str                # Formato: "MM/AAAA"
    
    # Status (Enum)
    status_processo: str
    # - AGUARDANDO_DOWNLOAD
    # - AGUARDANDO_APROVACAO
    # - AGUARDANDO_ENVIO_SAT
    # - UPLOAD_REALIZADO
    
    # Fatura
    url_fatura: str             # URL original
    caminho_s3_fatura: str      # Caminho MinIO
    fatura_s3_key: str          # Key S3
    fatura_filename: str        # Nome arquivo
    data_vencimento: date
    valor_fatura: decimal
    
    # Aprovação
    aprovado_por_usuario_id: UUID (FK)
    data_aprovacao: datetime
    
    # SAT
    enviado_para_sat: bool
    data_envio_sat: datetime
    
    # Retry
    tentativas_download: int
    tentativas_upload_sat: int
    
    # Flags
    upload_manual: bool
    criado_automaticamente: bool
    
    # Relacionamentos
    cliente → Cliente.processos
    aprovador → Usuario.processos_aprovados
    execucoes → Execucao.processo
```

**Unicidade:**
```sql
UNIQUE(cliente_id, mes_ano)
```

**Fluxo de Status:**
```
AGUARDANDO_DOWNLOAD
        ↓
AGUARDANDO_APROVACAO
        ↓
AGUARDANDO_ENVIO_SAT
        ↓
UPLOAD_REALIZADO
```

**Onde Modificar:**
- **CRUD**: `apps/processos/routes.py`
- **Aprovação**: `apps/processos/views.py`
- **Upload Manual**: `apps/processos/routes.py` (função `upload_manual_fatura`)
- **Templates**: `apps/templates/processos/`

### 3.6 Modelo: Execucao

**Arquivo:** `apps/models/execucao.py`

```python
class Execucao(BaseModel):
    __tablename__ = 'execucoes'
    
    # Identificação
    processo_id: UUID (FK)
    
    # Tipo (Enum)
    tipo_execucao: str
    # - DOWNLOAD_FATURA
    # - UPLOAD_SAT
    # - UPLOAD_MANUAL
    
    # Status (Enum)
    status_execucao: str
    # - EXECUTANDO
    # - CONCLUIDO
    # - FALHOU
    # - TENTANDO_NOVAMENTE
    # - CANCELADO
    # - TIMEOUT
    
    # RPA
    classe_rpa_utilizada: str
    job_id: str                 # ID para SSE
    
    # Dados JSON
    parametros_entrada: JSON
    resultado_saida: JSON
    detalhes_erro: JSON
    
    # Timestamps
    data_inicio: datetime
    data_fim: datetime
    
    # Logs
    mensagem_log: text
    url_arquivo_s3: str
    
    # Controle
    numero_tentativa: int
    
    # Auditoria
    executado_por_usuario_id: UUID (FK)
    ip_origem: str
    user_agent: str
    
    # Relacionamentos
    processo → Processo.execucoes
    executor → Usuario.execucoes_realizadas
```

**Onde Modificar:**
- **Listagem**: `apps/execucoes/routes.py`
- **Serviços**: `apps/execucoes/services.py`
- **Templates**: `apps/templates/execucoes/`

### 3.7 Modelo: Agendamento

**Arquivo:** `apps/models/agendamento.py`

```python
class Agendamento(BaseModel):
    __tablename__ = 'agendamentos'
    
    # Identificação
    nome_agendamento: str (unique)
    descricao: text
    
    # Cron
    cron_expressao: str         # Ex: "0 8 * * 1-5"
    
    # Tipo (Enum)
    tipo_agendamento: str
    # - CRIAR_PROCESSOS_MENSAIS
    # - EXECUTAR_DOWNLOADS
    # - ENVIAR_RELATORIOS
    # - LIMPEZA_LOGS
    # - BACKUP_DADOS
    
    # Status
    status_ativo: bool
    
    # Execução
    proxima_execucao: datetime
    ultima_execucao: datetime
    
    # Parâmetros
    parametros_execucao: JSON   # Operadora, etc
```

**Onde Modificar:**
- **CRUD**: `apps/agendamentos/routes.py`
- **Executor**: `apps/agendamentos/executor.py`
- **Templates**: `apps/templates/agendamentos/`

---

## 4. ESTRUTURA DE PASTAS E ARQUIVOS

### 4.1 Estrutura Geral

```
workspace/
├── apps/                       # Código principal da aplicação
│   ├── __init__.py             # Factory do Flask
│   ├── config.py               # Configurações
│   ├── db.sqlite3              # SQLite (dev)
│   │
│   ├── models/                 # Modelos de banco
│   │   ├── __init__.py
│   │   ├── base.py             # BaseModel com UUID
│   │   ├── usuario.py
│   │   ├── operadora.py
│   │   ├── cliente.py
│   │   ├── processo.py
│   │   ├── execucao.py
│   │   ├── agendamento.py
│   │   └── notificacao.py
│   │
│   ├── authentication/         # Login/Logout
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── models.py
│   │
│   ├── home/                   # Dashboard principal
│   │   ├── routes.py
│   │   └── __init__.py
│   │
│   ├── usuarios/               # CRUD Usuários
│   │   ├── routes_simple.py   # Rotas principais
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── operadoras/             # CRUD Operadoras
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── clientes/               # CRUD Clientes
│   │   ├── routes.py
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── processos/              # CRUD Processos
│   │   ├── routes.py           # CRUD + Upload Manual
│   │   ├── views.py            # Aprovação
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── execucoes/              # Módulo Execuções
│   │   ├── routes.py           # Listagem, filtros, detalhes
│   │   ├── services.py         # Lógica de negócio
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── agendamentos/           # Sistema de agendamentos
│   │   ├── routes.py           # CRUD agendamentos
│   │   ├── executor.py         # Background executor
│   │   ├── forms.py
│   │   └── __init__.py
│   │
│   ├── api_externa/            # Integração RPA Externa
│   │   ├── auth.py             # JWT Token
│   │   ├── client.py           # Cliente HTTP
│   │   ├── services.py         # Serviços principais
│   │   ├── monitor.py          # Job Monitor
│   │   ├── routes_logs_tempo_real.py  # SSE
│   │   └── models.py           # Payloads
│   │
│   ├── services/               # Serviços auxiliares
│   │   └── minio_service.py    # Upload/Download S3
│   │
│   ├── templates/              # Templates Jinja2
│   │   ├── layouts/
│   │   │   └── base.html       # Layout base
│   │   ├── includes/
│   │   │   ├── sidebar.html    # Menu lateral
│   │   │   └── scripts.html    # Scripts JS
│   │   ├── home/
│   │   │   └── index.html      # Dashboard
│   │   ├── usuarios/
│   │   ├── operadoras/
│   │   ├── clientes/
│   │   ├── processos/
│   │   ├── execucoes/
│   │   └── agendamentos/
│   │
│   └── static/                 # Arquivos estáticos
│       └── assets/
│           ├── css/
│           │   ├── style.css
│           │   ├── dark.css
│           │   └── brm-theme.css
│           ├── js/
│           │   ├── dark-mode.js
│           │   └── monitoramento-rpa.js
│           ├── fonts/
│           └── images/
│
├── scripts/                    # Scripts utilitários
│   ├── importar_clientes_csv.py
│   └── criar_agendamentos_padrao.py
│
├── docs/                       # Documentação
│   └── SSE_LOGS_TEMPO_REAL.md
│
├── run.py                      # Entrypoint
├── requirements.txt            # Dependências Python
├── replit.md                   # Memória do projeto
└── MANUAL_TECNICO_COMPLETO.md  # Este arquivo
```

---

## 5. FLUXO DE DADOS

### 5.1 Fluxo de Download Automático

```
1. AGENDAMENTO EXECUTA (cron)
   └─> apps/agendamentos/executor.py

2. BUSCA PROCESSOS PENDENTES
   └─> Processo.query.filter_by(status='AGUARDANDO_DOWNLOAD')

3. CHAMA API EXTERNA
   └─> apps/api_externa/services.py
       └─> POST http://191.252.218.230:8000/executar/{operadora}

4. CRIA EXECUÇÃO
   └─> Execucao(tipo='DOWNLOAD_FATURA', job_id=response.job_id)

5. MONITORA JOB (SSE)
   └─> apps/api_externa/monitor_tempo_real.py
       └─> GET /jobs/{job_id}/logs (polling)

6. ATUALIZA STATUS
   └─> Quando job completa:
       - processo.status = AGUARDANDO_APROVACAO
       - processo.url_fatura = resultado.url
       - execucao.status = CONCLUIDO
```

### 5.2 Fluxo de Upload Manual

```
1. USUÁRIO ACESSA PROCESSO
   └─> GET /processos/visualizar/{id}

2. USUÁRIO SELECIONA PDF
   └─> Frontend: <input type="file" accept=".pdf">

3. ENVIA PARA BACKEND
   └─> POST /processos/upload-manual-fatura
       └─> apps/processos/routes.py

4. UPLOAD PARA MINIO
   └─> apps/services/minio_service.py
       └─> bucket: 'beg', folder: 'pdfs/'

5. ATUALIZA PROCESSO
   └─> processo.caminho_s3_fatura = 'pdfs/arquivo.pdf'
       processo.fatura_s3_key = 'arquivo.pdf'
       processo.upload_manual = True
       processo.status = AGUARDANDO_APROVACAO

6. CRIA EXECUÇÃO
   └─> Execucao(tipo='UPLOAD_MANUAL', status='CONCLUIDO')
```

### 5.3 Fluxo de Aprovação

```
1. USUÁRIO VISUALIZA PROCESSO
   └─> GET /processos/visualizar/{id}
       └─> Verifica: processo.status == AGUARDANDO_APROVACAO

2. USUÁRIO APROVA
   └─> POST /processos/aprovar/{id}
       └─> apps/processos/views.py

3. VALIDA PERMISSÃO
   └─> if not current_user.pode_aprovar_processos:
           flash('Sem permissão', 'error')

4. ATUALIZA PROCESSO
   └─> processo.aprovar(usuario_id=current_user.id)
       └─> processo.status = AGUARDANDO_ENVIO_SAT
           processo.aprovado_por_usuario_id = current_user.id
           processo.data_aprovacao = now()

5. REDIRECT
   └─> redirect(url_for('processos.index'))
```

### 5.4 Fluxo de Upload SAT

```
1. USUÁRIO ACIONA UPLOAD
   └─> POST /processos/enviar-para-sat/{id}

2. VALIDA PROCESSO
   └─> if processo.status != AGUARDANDO_ENVIO_SAT:
           flash('Processo não aprovado', 'error')

3. MONTA PAYLOAD
   └─> apps/api_externa/models.py
       └─> AutomacaoPayloadSat(
               cnpj=cliente.cnpj,
               razao=cliente.razao_social,
               operadora=operadora.codigo,
               ...
           )

4. CHAMA API EXTERNA
   └─> POST http://191.252.218.230:8000/executar/sat
       Headers: {'Authorization': 'Bearer {token}'}

5. CRIA EXECUÇÃO
   └─> Execucao(
           tipo='UPLOAD_SAT',
           job_id=response.job_id,
           parametros_entrada=payload.dict()
       )

6. MONITORA VIA SSE
   └─> Frontend: EventSource(/api/v2/logs-tempo-real/stream/{job_id})
       └─> Exibe logs em tempo real

7. ATUALIZA QUANDO COMPLETA
   └─> processo.enviar_para_sat()
       └─> processo.status = UPLOAD_REALIZADO
           processo.data_envio_sat = now()
       execucao.finalizar_com_sucesso()
```

---

## 6. GUIA DE MODIFICAÇÃO POR MÓDULO

### 6.1 Adicionar Novo Campo ao Modelo

**Exemplo: Adicionar campo "observacoes_internas" ao Processo**

#### Passo 1: Modificar o Modelo
```python
# apps/models/processo.py

observacoes_internas = Column(
    Text,
    nullable=True,
    comment="Observações internas não visíveis ao cliente"
)
```

#### Passo 2: Atualizar o Formulário
```python
# apps/processos/forms.py

from wtforms import TextAreaField

class ProcessoForm(FlaskForm):
    # ... campos existentes
    observacoes_internas = TextAreaField('Observações Internas')
```

#### Passo 3: Atualizar Template
```html
<!-- apps/templates/processos/form.html -->

<div class="form-group">
    {{ form.observacoes_internas.label }}
    {{ form.observacoes_internas(class="form-control") }}
</div>
```

#### Passo 4: Migrar Banco de Dados
```bash
# Se SQLite (dev)
python
>>> from apps import db, create_app
>>> app = create_app()
>>> with app.app_context():
>>>     db.create_all()

# Se PostgreSQL (prod)
# Use Alembic ou adicione coluna manualmente via SQL
```

### 6.2 Criar Nova Rota

**Exemplo: Adicionar rota de relatório mensal**

#### Passo 1: Criar Rota
```python
# apps/processos/routes.py

@bp.route('/relatorio-mensal/<mes_ano>')
@login_required
def relatorio_mensal(mes_ano):
    """Gera relatório mensal de processos"""
    
    # Validar formato
    if not Processo.validar_formato_mes_ano(mes_ano):
        flash('Formato inválido', 'error')
        return redirect(url_for('processos.index'))
    
    # Buscar processos
    processos = Processo.query.filter_by(mes_ano=mes_ano).all()
    
    # Calcular estatísticas
    total = len(processos)
    concluidos = sum(1 for p in processos if p.esta_concluido)
    
    return render_template(
        'processos/relatorio_mensal.html',
        mes_ano=mes_ano,
        processos=processos,
        total=total,
        concluidos=concluidos
    )
```

#### Passo 2: Criar Template
```html
<!-- apps/templates/processos/relatorio_mensal.html -->

{% extends "layouts/base.html" %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h3>Relatório Mensal - {{ mes_ano }}</h3>
        <p>Total: {{ total }} | Concluídos: {{ concluidos }}</p>
        
        <table class="table">
            {% for processo in processos %}
            <tr>
                <td>{{ processo.cliente.razao_social }}</td>
                <td>{{ processo.status_processo }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
```

#### Passo 3: Adicionar Link no Menu
```html
<!-- apps/templates/includes/sidebar.html -->

<li class="nav-item">
    <a href="{{ url_for('processos.relatorio_mensal', mes_ano='11/2025') }}">
        <i data-feather="file-text"></i>
        <span>Relatório Mensal</span>
    </a>
</li>
```

### 6.3 Adicionar Novo Tipo de Agendamento

**Exemplo: Agendamento de backup diário**

#### Passo 1: Adicionar ao Enum
```python
# apps/models/agendamento.py

class TipoAgendamento(Enum):
    CRIAR_PROCESSOS_MENSAIS = "CRIAR_PROCESSOS_MENSAIS"
    EXECUTAR_DOWNLOADS = "EXECUTAR_DOWNLOADS"
    ENVIAR_RELATORIOS = "ENVIAR_RELATORIOS"
    LIMPEZA_LOGS = "LIMPEZA_LOGS"
    BACKUP_DADOS = "BACKUP_DADOS"
    BACKUP_DIARIO_BD = "BACKUP_DIARIO_BD"  # NOVO
```

#### Passo 2: Criar Função de Execução
```python
# apps/agendamentos/executor.py

def executar_backup_diario_bd(agendamento):
    """Executa backup diário do banco de dados"""
    try:
        import subprocess
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_bd_{timestamp}.sql'
        
        # Executar pg_dump
        cmd = [
            'pg_dump',
            '-h', 'localhost',
            '-U', 'postgres',
            '-d', 'brm_db',
            '-f', filename
        ]
        
        subprocess.run(cmd, check=True)
        
        # Upload para S3
        from apps.services.minio_service import MinioService
        minio = MinioService()
        minio.upload_file(filename, 'backups', filename)
        
        logger.info(f"Backup realizado: {filename}")
        
    except Exception as e:
        logger.error(f"Erro no backup: {e}")
```

#### Passo 3: Registrar Executor
```python
# apps/agendamentos/executor.py

EXECUTORES_POR_TIPO = {
    'CRIAR_PROCESSOS_MENSAIS': executar_criacao_processos,
    'EXECUTAR_DOWNLOADS': executar_downloads,
    'ENVIAR_RELATORIOS': executar_envio_relatorios,
    'LIMPEZA_LOGS': executar_limpeza_logs,
    'BACKUP_DADOS': executar_backup_dados,
    'BACKUP_DIARIO_BD': executar_backup_diario_bd,  # NOVO
}
```

#### Passo 4: Adicionar ao Formulário
```python
# apps/agendamentos/forms.py

tipo_agendamento = SelectField(
    'Tipo de Agendamento',
    choices=[
        ('CRIAR_PROCESSOS_MENSAIS', 'Criar Processos Mensais'),
        ('EXECUTAR_DOWNLOADS', 'Executar Downloads'),
        ('BACKUP_DIARIO_BD', 'Backup Diário BD'),  # NOVO
    ]
)
```

---

## 7. SISTEMA DE AUTENTICAÇÃO

### 7.1 Autenticação Web (Flask-Login)

**Arquivo:** `apps/authentication/routes.py`

```python
from flask_login import login_user, logout_user, login_required

@blueprint.route('/login', methods=['POST'])
def login():
    # Buscar usuário
    user = Usuario.query.filter_by(email=email).first()
    
    # Validar senha (implementar hash)
    if user and user.senha == senha:
        login_user(user)
        return redirect(url_for('home_bp.index'))
```

**Proteger Rotas:**
```python
from flask_login import login_required

@bp.route('/processos/')
@login_required  # ← Requer autenticação
def index():
    pass
```

### 7.2 Autenticação API (JWT)

**Arquivo:** `apps/api_externa/auth.py`

```python
# Token global configurado
GLOBAL_TOKEN = os.getenv('BRM_TOKEN_PASSWORD')

def get_auth_headers():
    """Retorna headers de autenticação"""
    return {
        'Authorization': f'Bearer {GLOBAL_TOKEN}',
        'Content-Type': 'application/json'
    }
```

**Configurar Token:**
```bash
# Secrets do Replit
BRM_TOKEN_PASSWORD=seu_token_jwt_aqui
```

---

## 8. INTEGRAÇÃO COM API EXTERNA

### 8.1 Cliente HTTP

**Arquivo:** `apps/api_externa/client.py`

```python
class APIExternaClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
    
    def executar_download(self, operadora: str, payload: dict):
        """Executa download via RPA"""
        url = f"{self.base_url}/executar/{operadora}"
        
        response = requests.post(
            url,
            json=payload,
            headers={'Authorization': f'Bearer {self.token}'}
        )
        
        return response.json()
```

### 8.2 Serviços Principais

**Arquivo:** `apps/api_externa/services.py`

```python
class APIExternaService:
    def executar_automacao_sat(self, processo: Processo):
        """Envia processo para SAT"""
        
        # Montar payload
        payload = AutomacaoPayloadSat(
            cnpj=processo.cliente.cnpj,
            razao=processo.cliente.razao_social,
            operadora=processo.cliente.operadora.codigo,
            # ... outros campos
        )
        
        # Chamar API
        response = self.client.executar_sat(payload.dict())
        
        # Criar execução
        execucao = Execucao(
            processo_id=processo.id,
            tipo_execucao='UPLOAD_SAT',
            job_id=response['job_id']
        )
        
        db.session.add(execucao)
        db.session.commit()
        
        return execucao
```

### 8.3 Payloads

**Arquivo:** `apps/api_externa/models.py`

```python
from pydantic import BaseModel

class AutomacaoPayloadSat(BaseModel):
    """Payload para upload SAT"""
    cnpj: str
    razao: str
    operadora: str
    nome_filtro: str
    unidade: str
    servico: str
    dados_sat: str
    nome_arquivo: str
    data_vencimento: str
```

---

## 9. UPLOAD MANUAL E MINIO

### 9.1 Configuração MinIO

**Arquivo:** `apps/services/minio_service.py`

```python
class MinioService:
    def __init__(self):
        self.endpoint = "tirus-minio.cqojac.easypanel.host"
        self.access_key = os.getenv('MINIO_ACCESS_KEY')
        self.secret_key = os.getenv('MINIO_SECRET_KEY')
        self.bucket = 'beg'
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=True
        )
```

### 9.2 Upload de Arquivo

```python
def upload_file(self, file, folder: str, filename: str):
    """Upload arquivo para MinIO"""
    
    # Caminho completo
    object_name = f"{folder}/{filename}"
    
    # Upload
    self.client.put_object(
        bucket_name=self.bucket,
        object_name=object_name,
        data=file,
        length=file.content_length,
        content_type=file.content_type
    )
    
    return object_name
```

### 9.3 Download de Arquivo

```python
def download_file(self, object_name: str):
    """Download arquivo do MinIO"""
    
    response = self.client.get_object(
        bucket_name=self.bucket,
        object_name=object_name
    )
    
    return response.read()
```

### 9.4 Fluxo Completo Upload Manual

```python
# apps/processos/routes.py

@bp.route('/upload-manual-fatura', methods=['POST'])
@login_required
def upload_manual_fatura():
    # 1. Receber arquivo
    file = request.files.get('fatura_pdf')
    processo_id = request.form.get('processo_id')
    
    # 2. Validar
    if not file or file.filename == '':
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(...)
    
    # 3. Upload para MinIO
    minio = MinioService()
    filename = secure_filename(file.filename)
    s3_path = minio.upload_file(file, 'pdfs', filename)
    
    # 4. Atualizar processo
    processo = Processo.query.get(processo_id)
    processo.caminho_s3_fatura = s3_path
    processo.fatura_s3_key = filename
    processo.upload_manual = True
    processo.status_processo = 'AGUARDANDO_APROVACAO'
    processo.data_upload_manual = datetime.now()
    
    # 5. Criar execução
    execucao = Execucao(
        processo_id=processo.id,
        tipo_execucao='UPLOAD_MANUAL',
        status_execucao='CONCLUIDO',
        executado_por_usuario_id=current_user.id
    )
    
    db.session.add(execucao)
    db.session.commit()
    
    flash('Upload realizado com sucesso!', 'success')
    return redirect(...)
```

---

## 10. SISTEMA DE AGENDAMENTOS

### 10.1 Executor Background

**Arquivo:** `apps/agendamentos/executor.py`

```python
import threading
from croniter import croniter
from datetime import datetime

class AgendamentoExecutor:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """Inicia o executor em background"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(
                target=self._run_loop,
                daemon=True
            )
            self.thread.start()
    
    def _run_loop(self):
        """Loop principal do executor"""
        while self.running:
            # Buscar agendamentos ativos
            agendamentos = Agendamento.query.filter_by(
                status_ativo=True
            ).all()
            
            for agendamento in agendamentos:
                if agendamento.deve_executar_agora:
                    self._executar_agendamento(agendamento)
            
            # Dormir 60 segundos
            time.sleep(60)
```

### 10.2 Expressões Cron

**Formato:** `minuto hora dia mês dia_semana`

**Exemplos:**
```
"0 8 * * *"        # Todo dia às 08:00
"0 8 * * 1-5"      # Segunda a sexta às 08:00
"0 6 1 * *"        # Todo dia 1º às 06:00
"*/30 * * * *"     # A cada 30 minutos
"0 */2 * * *"      # A cada 2 horas
```

### 10.3 Calcular Próxima Execução

```python
from croniter import croniter

def calcular_proxima_execucao(cron_expressao: str):
    """Calcula próxima execução baseada no cron"""
    cron = croniter(cron_expressao, datetime.now())
    return cron.get_next(datetime)
```

---

## 11. SERVER-SENT EVENTS (SSE)

### 11.1 Backend (Streaming)

**Arquivo:** `apps/api_externa/routes_logs_tempo_real.py`

```python
from flask import Response, stream_with_context

@api_logs_tempo_real_bp.route('/stream/<job_id>')
def stream_logs(job_id):
    """Stream de logs em tempo real via SSE"""
    
    def generate():
        # Enviar evento de conexão
        yield f"data: {json.dumps({'type': 'connection'})}\n\n"
        
        # Loop de polling
        while True:
            # Buscar logs da API externa
            logs = api_service.get_job_logs(job_id)
            
            # Enviar cada log
            for log in logs:
                yield f"data: {json.dumps(log)}\n\n"
            
            # Dormir 2 segundos
            time.sleep(2)
            
            # Verificar se job finalizou
            status = api_service.get_job_status(job_id)
            if status in ['completed', 'failed']:
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
```

### 11.2 Frontend (JavaScript)

**Template:** `apps/templates/processos/visualizar.html`

```javascript
// Criar EventSource
const eventSource = new EventSource(
    `/api/v2/logs-tempo-real/stream/${jobId}`
);

// Listener para mensagens
eventSource.addEventListener('message', (event) => {
    const data = JSON.parse(event.data);
    
    // Adicionar log ao container
    const logContainer = document.getElementById('logs-container');
    logContainer.innerHTML += `
        <div class="log-entry ${data.level}">
            [${data.timestamp}] ${data.message}
        </div>
    `;
    
    // Scroll automático
    logContainer.scrollTop = logContainer.scrollHeight;
});

// Listener para erros
eventSource.addEventListener('error', () => {
    console.error('Erro no SSE');
    eventSource.close();
});
```

### 11.3 Atualização Automática de Status

```javascript
// Quando receber evento de conclusão
if (data.type === 'job_completed') {
    // Atualizar status do processo na UI
    document.getElementById('status-badge').innerHTML = 
        '<span class="badge badge-success">Concluído</span>';
    
    // Fechar EventSource
    eventSource.close();
    
    // Recarregar página após 2 segundos
    setTimeout(() => {
        location.reload();
    }, 2000);
}
```

---

## 12. TROUBLESHOOTING E DEBUGGING

### 12.1 Problemas Comuns

#### Erro: "operadora_id is an invalid keyword argument"

**Causa:** Tentando passar campo inexistente ao modelo  
**Solução:** Campos JSON devem ir em `parametros_execucao`

```python
# ❌ ERRADO
agendamento = Agendamento(
    operadora_id='123'  # Campo não existe!
)

# ✅ CORRETO
agendamento = Agendamento(
    parametros_execucao={'operadora_id': '123'}
)
```

#### Erro: Servidor não reinicia após mudanças

**Causa:** Cache ou processo travado  
**Solução:**
```bash
# Matar processo Flask
pkill -f "python run.py"

# Reiniciar
python run.py
```

#### Erro: Template not found

**Causa:** Caminho incorreto do template  
**Solução:** Verificar estrutura:
```python
# Caminho relativo a apps/templates/
render_template('processos/index.html')  # ✅
render_template('/processos/index.html') # ❌
```

#### Erro: 403 Forbidden em rotas

**Causa:** Falta decorador `@login_required`  
**Solução:**
```python
@bp.route('/processos/')
@login_required  # ← Adicionar
def index():
    pass
```

### 12.2 Ativando Logs Detalhados

```python
# apps/config.py

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Em rotas específicas
logger = logging.getLogger(__name__)

@bp.route('/teste')
def teste():
    logger.debug("Entrando na rota teste")
    logger.info(f"Dados: {request.args}")
    logger.error("Erro capturado")
```

### 12.3 Inspecionando Banco de Dados

```bash
# SQLite
sqlite3 apps/db.sqlite3
> .tables
> SELECT * FROM processos LIMIT 5;
> .quit

# PostgreSQL
psql -U postgres -d brm_db
> \dt
> SELECT * FROM processos LIMIT 5;
> \q
```

### 12.4 Verificando Execuções com Erro

```python
# Script de debug
from apps import db, create_app, Execucao

app = create_app()
with app.app_context():
    # Buscar execuções falhadas
    falhas = Execucao.query.filter_by(
        status_execucao='FALHOU'
    ).order_by(
        Execucao.data_inicio.desc()
    ).limit(10).all()
    
    for exec in falhas:
        print(f"ID: {exec.id}")
        print(f"Tipo: {exec.tipo_execucao}")
        print(f"Erro: {exec.detalhes_erro}")
        print("---")
```

### 12.5 Testando API Externa

```python
# Script de teste
import requests
import os

BASE_URL = "http://191.252.218.230:8000"
TOKEN = os.getenv('BRM_TOKEN_PASSWORD')

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Testar health
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.status_code}")

# Testar execução SAT
payload = {
    "cnpj": "12345678000190",
    "razao": "Teste SA",
    # ... outros campos
}

response = requests.post(
    f"{BASE_URL}/executar/sat",
    json=payload,
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

---

## APÊNDICES

### A. Comandos Úteis

```bash
# Criar banco de dados
python
>>> from apps import db, create_app
>>> app = create_app()
>>> with app.app_context():
>>>     db.create_all()

# Importar clientes via CSV
python scripts/importar_clientes_csv.py exemplo_clientes.csv

# Criar agendamentos padrão
python criar_agendamentos_padrao.py

# Verificar estrutura do banco
python check_db.py

# Limpar banco mantendo usuários
python limpar_banco_manter_usuarios.py
```

### B. Variáveis de Ambiente

```bash
# .env (Replit Secrets)
BRM_TOKEN_PASSWORD=jwt_token_api_externa
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key
DATABASE_URL=postgresql://...  # (Prod)
```

### C. Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Dashboard principal |
| GET | `/processos/` | Listar processos |
| GET | `/processos/visualizar/{id}` | Detalhes processo |
| POST | `/processos/aprovar/{id}` | Aprovar processo |
| POST | `/processos/enviar-para-sat/{id}` | Enviar para SAT |
| POST | `/processos/upload-manual-fatura` | Upload manual |
| GET | `/execucoes/` | Listar execuções |
| GET | `/execucoes/detalhes/{id}` | Detalhes execução |
| GET | `/agendamentos/` | Listar agendamentos |
| GET | `/api/v2/logs-tempo-real/stream/{job_id}` | SSE logs |

---

**FIM DO MANUAL TÉCNICO**

Para dúvidas ou suporte técnico, consulte a equipe de desenvolvimento.
