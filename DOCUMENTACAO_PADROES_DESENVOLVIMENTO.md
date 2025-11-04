# DOCUMENTAÇÃO DE PADRÕES DE DESENVOLVIMENTO - SISTEMA BRM SOLUTIONS

## ÍNDICE
1. [PADRÕES FRONTEND](#padrões-frontend)
2. [PADRÕES BACKEND](#padrões-backend)
3. [ARQUITETURA GERAL](#arquitetura-geral)
4. [CONVENÇÕES E BOAS PRÁTICAS](#convenções-e-boas-práticas)

---

## PADRÕES FRONTEND

### 1. ESTRUTURA DE TEMPLATES

#### 1.1 Layout Base (`apps/templates/layouts/base.html`)
- **Extensão obrigatória**: Todos os templates devem estender `base.html`
- **Meta tags padrão**: Incluir charset UTF-8, viewport responsivo, compatibilidade IE
- **CSS obrigatório**:
  - `style.css` (tema principal)
  - `dark.css` (modo escuro)
  - `brm-theme.css` (customizações BRM)
  - `toastr.min.css` (notificações)
- **JavaScript obrigatório**:
  - `pcoded.min.js` (funcionalidades do dashboard)
  - `vendor-all.min.js` (bibliotecas)
  - `toastr.min.js` (notificações)

#### 1.2 Estrutura de Páginas
```html
{% extends "layouts/base.html" %}

{% block title %} Nome da Página {% endblock %}

{% block stylesheets %}
<!-- CSS específico da página -->
{% endblock stylesheets %}

{% block content %}
<div class="pcoded-main-container">
    <div class="pcoded-wrapper">
        <div class="pcoded-content">
            <div class="pcoded-inner-content">
                <!-- Breadcrumb -->
                <div class="page-header">
                    <div class="page-block">
                        <div class="row align-items-center">
                            <div class="col-md-12">
                                <div class="page-header-title">
                                    <h5 class="m-b-10">Título da Página</h5>
                                </div>
                                <ul class="breadcrumb">
                                    <li class="breadcrumb-item">
                                        <a href="{{ url_for('home.index') }}">
                                            <i class="feather icon-home"></i>
                                        </a>
                                    </li>
                                    <li class="breadcrumb-item active">Página Atual</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Conteúdo Principal -->
                <div class="main-body">
                    <div class="page-wrapper">
                        <!-- Cards e Conteúdo -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock content %}
```

### 2. COMPONENTES CSS

#### 2.1 Sistema de Grid
- **Bootstrap 4**: Utilizar classes `col-md-*`, `col-lg-*`, `col-sm-*`
- **Responsividade**: Sempre considerar mobile-first
- **Espaçamentos**: Usar classes utilitárias `p-*`, `m-*` (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50)

#### 2.2 Cards
```html
<div class="card">
    <div class="card-header">
        <h5>Título do Card</h5>
    </div>
    <div class="card-body">
        <!-- Conteúdo -->
    </div>
</div>
```

#### 2.3 Botões
- **Primário**: `btn btn-primary`
- **Secundário**: `btn btn-secondary`
- **Sucesso**: `btn btn-success`
- **Perigo**: `btn btn-danger`
- **Aviso**: `btn btn-warning`
- **Info**: `btn btn-info`
- **Tamanhos**: `btn-sm`, `btn-lg`
- **Ícones**: Sempre usar `feather icon-*` antes do texto

#### 2.4 Formulários
```html
<div class="form-group">
    {{ form.campo.label(class="form-label") }}
    {{ form.campo(class="form-control") }}
    {% if form.campo.errors %}
        {% for error in form.campo.errors %}
            <small class="text-danger">{{ error }}</small>
        {% endfor %}
    {% endif %}
</div>
```

#### 2.5 Tabelas
```html
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th>Coluna 1</th>
                <th>Coluna 2</th>
                <th class="text-center">Ações</th>
            </tr>
        </thead>
        <tbody>
            <!-- Dados -->
        </tbody>
    </table>
</div>
```

#### 2.6 Badges e Status
- **Sucesso**: `badge badge-success`
- **Perigo**: `badge badge-danger`
- **Aviso**: `badge badge-warning`
- **Info**: `badge badge-info`
- **Tamanhos**: `badge-sm`, `badge-lg`

### 3. JAVASCRIPT E INTERATIVIDADE

#### 3.1 CSRF Token
```html
<!-- Sempre incluir em formulários -->
<form style="display: none;" id="csrf-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
</form>
```

#### 3.2 Notificações Toastr
```javascript
// Sucesso
toastr.success('Operação realizada com sucesso!');

// Erro
toastr.error('Erro ao realizar operação');

// Aviso
toastr.warning('Atenção!');

// Info
toastr.info('Informação importante');
```

#### 3.3 Confirmações
```javascript
if (confirm('Tem certeza que deseja excluir?')) {
    // Ação de exclusão
}
```

#### 3.4 AJAX com Fetch
```javascript
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        toastr.success(data.message);
        location.reload();
    } else {
        toastr.error(data.message);
    }
})
.catch(error => {
    console.error('Erro:', error);
    toastr.error('Erro interno do servidor');
});
```

### 4. ÍCONES E ELEMENTOS VISUAIS

#### 4.1 Feather Icons (Padrão)
- **Home**: `feather icon-home`
- **Adicionar**: `feather icon-plus`
- **Editar**: `feather icon-edit`
- **Excluir**: `feather icon-trash-2`
- **Visualizar**: `feather icon-eye`
- **Buscar**: `feather icon-search`
- **Limpar**: `feather icon-x`
- **Download**: `feather icon-download`
- **Upload**: `feather icon-upload`
- **Configurações**: `feather icon-settings`
- **Usuário**: `feather icon-user`
- **Sair**: `feather icon-log-out`

#### 4.2 Cores do Tema
- **Primária**: `#4680ff` (azul BRM)
- **Sucesso**: `#51bb25` (verde)
- **Perigo**: `#dc3545` (vermelho)
- **Aviso**: `#ffc107` (amarelo)
- **Info**: `#17a2b8` (azul claro)

### 5. RESPONSIVIDADE

#### 5.1 Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 991px
- **Desktop**: 992px - 1199px
- **Large**: ≥ 1200px

#### 5.2 Classes Responsivas
- **Ocultar em mobile**: `d-none d-md-block`
- **Mostrar apenas em mobile**: `d-block d-md-none`
- **Colunas responsivas**: `col-12 col-md-6 col-lg-4`

---

## PADRÕES BACKEND

### 1. ESTRUTURA DE MÓDULOS

#### 1.1 Organização de Arquivos
```
apps/
├── modulo/
│   ├── __init__.py          # Registro do blueprint
│   ├── routes.py            # Rotas e controladores
│   ├── forms.py             # Formulários WTForms
│   ├── models.py            # Modelos específicos (se houver)
│   └── services.py          # Lógica de negócio
```

#### 1.2 Blueprint Registration
```python
# apps/modulo/__init__.py
from flask import Blueprint

modulo_bp = Blueprint('modulo', __name__)

from . import routes
```

### 2. MODELOS DE DADOS

#### 2.1 Herança de BaseModel
```python
from apps.models.base import BaseModel, GUID
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class MeuModelo(BaseModel):
    __tablename__ = 'meu_modelo'

    # Campos obrigatórios (já herdados):
    # - id (GUID)
    # - data_criacao
    # - data_atualizacao

    nome = Column(String(100), nullable=False, comment="Nome do registro")
    status_ativo = Column(Boolean, default=True, nullable=False)

    # Relacionamentos
    outro_id = Column(GUID, ForeignKey('outro_modelo.id'), nullable=True)
    outro = relationship("OutroModelo", back_populates="meus_modelos")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, nome='{self.nome}')>"
```

#### 2.2 Enums para Status
```python
from enum import Enum

class StatusModelo(Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    PENDENTE = "PENDENTE"

    @classmethod
    def choices(cls):
        return [(status.value, status.name) for status in cls]
```

### 3. FORMULÁRIOS WTForms

#### 3.1 Estrutura Padrão
```python
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length, Regexp

class MeuFormulario(FlaskForm):
    nome = StringField(
        'Nome',
        validators=[
            DataRequired(message='Nome é obrigatório'),
            Length(max=100, message='Nome deve ter no máximo 100 caracteres')
        ],
        render_kw={'placeholder': 'Digite o nome...'}
    )

    status = SelectField(
        'Status',
        choices=StatusModelo.choices(),
        validators=[DataRequired()]
    )

    observacoes = TextAreaField(
        'Observações',
        validators=[Optional()],
        render_kw={'rows': 4, 'placeholder': 'Observações...'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carregar dados dinâmicos se necessário
```

### 4. ROTAS E CONTROLADORES

#### 4.1 Estrutura de Rotas
```python
import logging
import traceback
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError

from .forms import MeuFormulario
from apps import db
from apps.models import MeuModelo

logger = logging.getLogger(__name__)
modulo_bp = Blueprint('modulo', __name__)

@modulo_bp.route('/')
@login_required
def index():
    """Listagem principal com filtros"""
    try:
        # Lógica de filtros
        filtros = request.args
        query = MeuModelo.query

        # Aplicar filtros
        if filtros.get('busca'):
            termo = filtros.get('busca').strip()
            query = query.filter(
                or_(
                    MeuModelo.nome.like(f'%{termo}%'),
                    MeuModelo.descricao.like(f'%{termo}%')
                )
            )

        # Ordenação
        query = query.order_by(desc(MeuModelo.data_criacao))

        # Paginação
        page = request.args.get('page', 1, type=int)
        per_page = 20
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template(
            'modulo/index.html',
            items=pagination.items,
            pagination=pagination
        )

    except Exception as e:
        logger.error(f"Erro na listagem: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Erro interno do servidor', 'error')
        return redirect(url_for('home.index'))

@modulo_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo registro"""
    try:
        form = MeuFormulario()

        if form.validate_on_submit():
            novo_item = MeuModelo(
                nome=form.nome.data,
                status=form.status.data,
                observacoes=form.observacoes.data
            )

            db.session.add(novo_item)
            db.session.commit()

            flash('Registro criado com sucesso!', 'success')
            return redirect(url_for('modulo.index'))

        return render_template('modulo/form.html', form=form, titulo='Novo Registro')

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erro de banco: {str(e)}")
        flash('Erro ao salvar no banco de dados', 'error')
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        flash('Erro interno do servidor', 'error')

    return render_template('modulo/form.html', form=form, titulo='Novo Registro')
```

#### 4.2 Rotas AJAX/API
```python
@modulo_bp.route('/api/buscar', methods=['POST'])
@login_required
def buscar_api():
    """Endpoint para busca via AJAX"""
    try:
        data = request.get_json()
        termo = data.get('termo', '').strip()

        if not termo:
            return jsonify({'success': False, 'message': 'Termo de busca obrigatório'})

        resultados = MeuModelo.query.filter(
            MeuModelo.nome.like(f'%{termo}%')
        ).limit(10).all()

        return jsonify({
            'success': True,
            'data': [{'id': str(r.id), 'nome': r.nome} for r in resultados]
        })

    except Exception as e:
        logger.error(f"Erro na busca API: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro interno'})
```

### 5. SERVIÇOS E LÓGICA DE NEGÓCIO

#### 5.1 Classes de Serviço
```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class FiltrosBusca:
    """Classe para organizar filtros de busca"""
    termo: Optional[str] = None
    status: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None

class MeuServico:
    """Serviço para operações com MeuModelo"""

    @staticmethod
    def aplicar_filtros(query, filtros: FiltrosBusca):
        """Aplica filtros na query"""
        if filtros.termo:
            query = query.filter(
                or_(
                    MeuModelo.nome.like(f'%{filtros.termo}%'),
                    MeuModelo.descricao.like(f'%{filtros.termo}%')
                )
            )

        if filtros.status:
            query = query.filter(MeuModelo.status == filtros.status)

        return query

    @staticmethod
    def criar_payload(item: MeuModelo) -> Dict[str, Any]:
        """Cria payload para API externa"""
        return {
            'id': str(item.id),
            'nome': item.nome,
            'status': item.status,
            'data_criacao': item.data_criacao.isoformat()
        }
```

### 6. LOGGING E TRATAMENTO DE ERROS

#### 6.1 Configuração de Logging
```python
import logging

logger = logging.getLogger(__name__)

# Sempre usar logger com contexto
logger.debug("Iniciando operação com parâmetros: %s", parametros)
logger.info("Operação realizada com sucesso")
logger.warning("Atenção: %s", mensagem)
logger.error("Erro na operação: %s", str(e))
logger.error("Traceback: %s", traceback.format_exc())
```

#### 6.2 Tratamento de Exceções
```python
try:
    # Operação que pode falhar
    resultado = operacao_risco()

except SQLAlchemyError as e:
    db.session.rollback()
    logger.error(f"Erro de banco: {str(e)}")
    flash('Erro no banco de dados', 'error')

except ValueError as e:
    logger.error(f"Erro de validação: {str(e)}")
    flash('Dados inválidos', 'error')

except Exception as e:
    logger.error(f"Erro inesperado: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    flash('Erro interno do servidor', 'error')
```

### 7. VALIDAÇÕES E SEGURANÇA

#### 7.1 Validações de Formulário
```python
from wtforms.validators import DataRequired, Optional, Length, Regexp, NumberRange

class FormularioValidado(FlaskForm):
    nome = StringField(
        'Nome',
        validators=[
            DataRequired(message='Nome é obrigatório'),
            Length(min=2, max=100, message='Nome deve ter entre 2 e 100 caracteres'),
            Regexp(r'^[a-zA-ZÀ-ÿ\s]+$', message='Nome deve conter apenas letras')
        ]
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email é obrigatório'),
            Email(message='Email inválido')
        ]
    )

    valor = DecimalField(
        'Valor',
        validators=[
            Optional(),
            NumberRange(min=0, message='Valor deve ser positivo')
        ],
        places=2
    )
```

#### 7.2 Sanitização de Dados
```python
import bleach

def sanitizar_texto(texto: str) -> str:
    """Remove HTML e caracteres perigosos"""
    return bleach.clean(texto, strip=True)

def validar_cnpj(cnpj: str) -> bool:
    """Valida formato de CNPJ"""
    import re
    cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
    return len(cnpj_limpo) == 14
```

---

## ARQUITETURA GERAL

### 1. ESTRUTURA DO PROJETO
```
tirus-dash-flask/
├── apps/                    # Aplicação principal
│   ├── __init__.py         # Configuração Flask
│   ├── config.py           # Configurações
│   ├── models/             # Modelos de dados
│   ├── authentication/     # Autenticação
│   ├── home/              # Página inicial
│   ├── processos/         # Módulo processos
│   ├── clientes/          # Módulo clientes
│   ├── operadoras/        # Módulo operadoras
│   ├── usuarios/          # Módulo usuários
│   ├── agendamentos/      # Módulo agendamentos
│   ├── rpa/              # Módulo RPA
│   ├── api_externa/      # API externa
│   ├── static/           # Arquivos estáticos
│   └── templates/        # Templates HTML
├── requirements.txt       # Dependências Python
├── run.py               # Script de execução
└── Dockerfile           # Containerização
```

### 2. TECNOLOGIAS UTILIZADAS

#### 2.1 Backend
- **Framework**: Flask 2.x
- **ORM**: SQLAlchemy 1.4+
- **Banco**: PostgreSQL (produção) / SQLite (desenvolvimento)
- **Autenticação**: Flask-Login
- **Formulários**: WTForms
- **Validação**: Marshmallow (opcional)
- **Logging**: Python logging
- **Testes**: pytest

#### 2.2 Frontend
- **Template Engine**: Jinja2
- **CSS Framework**: Bootstrap 4
- **Ícones**: Feather Icons
- **JavaScript**: jQuery + Vanilla JS
- **Notificações**: Toastr
- **Tema**: Datta Able (customizado)

#### 2.3 DevOps
- **Containerização**: Docker
- **Orquestração**: Docker Compose
- **Proxy Reverso**: Nginx
- **Process Manager**: Gunicorn
- **Monitoramento**: Logs estruturados

---

## CONVENÇÕES E BOAS PRÁTICAS

### 1. NOMENCLATURA

#### 1.1 Python
- **Classes**: PascalCase (`MeuModelo`)
- **Funções/Variáveis**: snake_case (`minha_funcao`)
- **Constantes**: UPPER_SNAKE_CASE (`MAX_TENTATIVAS`)
- **Módulos**: snake_case (`meu_modulo`)

#### 1.2 HTML/CSS
- **Classes CSS**: kebab-case (`minha-classe`)
- **IDs**: camelCase (`minhaDiv`)
- **Arquivos**: snake_case (`minha_pagina.html`)

#### 1.3 Banco de Dados
- **Tabelas**: snake_case (`meus_registros`)
- **Colunas**: snake_case (`data_criacao`)
- **Índices**: `idx_tabela_coluna`

### 2. DOCUMENTAÇÃO

#### 2.1 Docstrings
```python
def minha_funcao(parametro: str) -> bool:
    """
    Descrição da função.

    Args:
        parametro: Descrição do parâmetro

    Returns:
        Descrição do retorno

    Raises:
        ValueError: Quando o parâmetro é inválido
    """
    pass
```

#### 2.2 Comentários
```python
# Comentário de linha única

# Comentário de múltiplas linhas
# para explicar lógica complexa
# ou decisões importantes
```

### 3. PERFORMANCE

#### 3.1 Queries Otimizadas
```python
# ✅ Bom: Usar joinedload para evitar N+1
query = Processo.query.options(
    joinedload(Processo.cliente),
    joinedload(Processo.operadora)
)

# ❌ Ruim: Carregamento lazy
for processo in Processo.query.all():
    print(processo.cliente.nome)  # N+1 queries
```

#### 3.2 Paginação
```python
# Sempre paginar listagens grandes
page = request.args.get('page', 1, type=int)
per_page = 20
pagination = query.paginate(page=page, per_page=per_page)
```

### 4. SEGURANÇA

#### 4.1 Validação de Entrada
- Sempre validar dados de entrada
- Usar WTForms para validação de formulários
- Sanitizar dados antes de salvar

#### 4.2 Autenticação
- Todas as rotas protegidas com `@login_required`
- Verificar permissões quando necessário
- Usar CSRF tokens em formulários

#### 4.3 SQL Injection
- Usar SQLAlchemy ORM (proteção automática)
- Nunca concatenar strings em queries
- Usar parâmetros nomeados

### 5. TESTES

#### 5.1 Estrutura de Testes
```python
import pytest
from apps import create_app, db
from apps.models import MeuModelo

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_criar_modelo(app):
    """Testa criação de modelo"""
    with app.app_context():
        modelo = MeuModelo(nome='Teste')
        db.session.add(modelo)
        db.session.commit()

        assert modelo.id is not None
        assert modelo.nome == 'Teste'
```

### 6. DEPLOYMENT

#### 6.1 Variáveis de Ambiente
```bash
# .env
FLASK_ENV=production
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=your-secret-key
DEBUG=False
```

#### 6.2 Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
```

---

## CONCLUSÃO

Esta documentação estabelece os padrões fundamentais para desenvolvimento no sistema BRM Solutions. Todos os desenvolvedores devem seguir rigorosamente estas convenções para manter a consistência, qualidade e manutenibilidade do código.

**Lembre-se**: A consistência é mais importante que a perfeição individual. Sempre priorize seguir os padrões estabelecidos sobre implementações "mais elegantes" que quebrem a convenção.
