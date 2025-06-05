
"""
Formulários para gerenciamento de clientes
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, BooleanField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, ValidationError, Email
from wtforms.widgets import TextArea

from apps.models import Cliente, Operadora


class ClienteForm(FlaskForm):
    """Formulário para cadastro/edição de clientes"""
    
    razao_social = StringField(
        'Razão Social',
        validators=[
            DataRequired(message='Razão social é obrigatória'),
            Length(min=2, max=255, message='Razão social deve ter entre 2 e 255 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: Empresa LTDA'
        }
    )
    
    nome_sat = StringField(
        'Nome no SAT',
        validators=[
            DataRequired(message='Nome no SAT é obrigatório'),
            Length(min=2, max=255, message='Nome no SAT deve ter entre 2 e 255 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Como aparece no sistema SAT'
        }
    )
    
    cnpj = StringField(
        'CNPJ',
        validators=[
            DataRequired(message='CNPJ é obrigatório'),
            Length(min=14, max=20, message='CNPJ deve ter entre 14 e 20 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '00.000.000/0000-00'
        }
    )
    
    operadora_id = SelectField(
        'Operadora',
        validators=[DataRequired(message='Operadora é obrigatória')],
        render_kw={'class': 'form-select'},
        coerce=str
    )
    
    servico = StringField(
        'Serviço',
        validators=[
            DataRequired(message='Serviço é obrigatório'),
            Length(min=1, max=255, message='Serviço deve ter no máximo 255 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: Fixo, Internet, Link Dedicado'
        }
    )
    
    unidade = StringField(
        'Unidade/Filial',
        validators=[
            DataRequired(message='Unidade é obrigatória'),
            Length(min=1, max=100, message='Unidade deve ter no máximo 100 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: Campo Grande-MS, Matriz'
        }
    )
    
    filtro = StringField(
        'Filtro',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtro específico para busca de faturas'
        }
    )
    
    dados_sat = TextAreaField(
        'Dados SAT',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Dados específicos para integração com SAT'
        }
    )
    
    site_emissao = StringField(
        'Site de Emissão',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'URL ou local de emissão da fatura'
        }
    )
    
    login_portal = StringField(
        'Login do Portal',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Login para acesso ao portal da operadora'
        }
    )
    
    senha_portal = StringField(
        'Senha do Portal',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'type': 'password',
            'placeholder': 'Senha para acesso ao portal'
        }
    )
    
    cpf = StringField(
        'CPF',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': '000.000.000-00'
        }
    )
    
    status_ativo = BooleanField(
        'Status Ativo',
        default=True,
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carrega operadoras ativas para o select
        self.operadora_id.choices = [('', 'Selecione uma operadora')] + [
            (str(op.id), f"{op.nome} ({op.codigo})")
            for op in Operadora.query.filter_by(status_ativo=True).order_by(Operadora.nome).all()
        ]
    
    def validate_cnpj(self, field):
        """Valida se o CNPJ não está duplicado para a mesma operadora/unidade/serviço"""
        if not field.data:
            return
        
        # Remove formatação do CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, field.data))
        field.data = cnpj_limpo
        
        # Verifica duplicata apenas se não for o mesmo cliente sendo editado
        cliente_existente = Cliente.query.filter_by(
            cnpj=cnpj_limpo,
            operadora_id=self.operadora_id.data,
            unidade=self.unidade.data,
            servico=self.servico.data
        ).first()
        
        if cliente_existente:
            # Se estamos editando, pega o ID do objeto atual
            if hasattr(self, '_obj') and self._obj and str(self._obj.id) != str(cliente_existente.id):
                raise ValidationError('Já existe um cliente com este CNPJ, operadora, unidade e serviço.')
            elif not hasattr(self, '_obj') or not self._obj:
                raise ValidationError('Já existe um cliente com este CNPJ, operadora, unidade e serviço.')


class FiltroClienteForm(FlaskForm):
    """Formulário para filtros de busca de clientes"""
    
    razao_social = StringField(
        'Razão Social',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por razão social...'
        }
    )
    
    cnpj = StringField(
        'CNPJ',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por CNPJ...'
        }
    )
    
    operadora = SelectField(
        'Operadora',
        render_kw={'class': 'form-select'},
        coerce=str
    )
    
    servico = StringField(
        'Serviço',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por serviço...'
        }
    )
    
    unidade = StringField(
        'Unidade',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por unidade...'
        }
    )
    
    status = SelectField(
        'Status',
        choices=[
            ('', 'Todos'),
            ('ativo', 'Ativo'),
            ('inativo', 'Inativo')
        ],
        render_kw={
            'class': 'form-select'
        }
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carrega todas as operadoras para o filtro
        self.operadora.choices = [('', 'Todas')] + [
            (str(op.id), f"{op.nome} ({op.codigo})")
            for op in Operadora.query.order_by(Operadora.nome).all()
        ]


class ImportarClientesForm(FlaskForm):
    """Formulário para importação de clientes via CSV"""
    
    arquivo_csv = FileField(
        'Arquivo CSV',
        validators=[
            DataRequired(message='Arquivo CSV é obrigatório'),
            FileAllowed(['csv'], 'Apenas arquivos CSV são permitidos')
        ],
        render_kw={
            'class': 'form-control',
            'accept': '.csv'
        }
    )
    
    sobrescrever_existentes = BooleanField(
        'Sobrescrever clientes existentes',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )
