
"""
Formulários para gerenciamento de operadoras
"""

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField, URLField, SelectField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from wtforms.widgets import TextArea

from apps.models import Operadoraa


class OperadoraForm(FlaskForm):
    """Formulário para cadastro/edição de operadoras"""
    
    nome = StringField(
        'Nome da Operadora',
        validators=[
            DataRequired(message='Nome é obrigatório'),
            Length(min=2, max=100, message='Nome deve ter entre 2 e 100 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: Embratel, Vivo, Oi, etc.'
        }
    )
    
    codigo = StringField(
        'Código Identificador',
        validators=[
            DataRequired(message='Código é obrigatório'),
            Length(min=2, max=20, message='Código deve ter entre 2 e 20 caracteres')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: EMB, VIV, OI',
            'style': 'text-transform: uppercase;'
        }
    )
    
    possui_rpa = BooleanField(
        'Possui RPA Homologado',
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    status_ativo = BooleanField(
        'Status Ativo',
        default=True,
        render_kw={
            'class': 'form-check-input'
        }
    )
    
    url_portal = URLField(
        'URL do Portal',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'https://portal.operadora.com.br'
        }
    )
    
    instrucoes_acesso = TextAreaField(
        'Instruções de Acesso',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Instruções detalhadas para acesso ao portal...'
        }
    )
    
    classe_rpa = StringField(
        'Classe do RPA',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: EmbratelRPA, VivoRPA'
        }
    )
    
    def validate_codigo(self, field):
        """Valida se o código não está duplicado"""
        # Converte para maiúsculo
        field.data = field.data.upper() if field.data else ''
        
        # Verifica duplicata apenas se não for a mesma operadora sendo editada
        operadora_existente = Operadora.query.filter_by(codigo=field.data).first()
        if operadora_existente:
            # Se estamos editando, pega o ID do objeto atual
            if hasattr(self, '_obj') and self._obj and self._obj.id != operadora_existente.id:
                raise ValidationError('Este código já está sendo usado por outra operadora.')
            elif not hasattr(self, '_obj') or not self._obj:
                raise ValidationError('Este código já está sendo usado por outra operadora.')
    
    def validate_nome(self, field):
        """Valida se o nome não está duplicado"""
        operadora_existente = Operadora.query.filter_by(nome=field.data).first()
        if operadora_existente:
            # Se estamos editando, pega o ID do objeto atual
            if hasattr(self, '_obj') and self._obj and self._obj.id != operadora_existente.id:
                raise ValidationError('Este nome já está sendo usado por outra operadora.')
            elif not hasattr(self, '_obj') or not self._obj:
                raise ValidationError('Este nome já está sendo usado por outra operadora.')d != operadora_existente.id:
                raise ValidationError('Este nome já está sendo usado por outra operadora.')
            elif not hasattr(self, '_obj') or not self._obj:
                raise ValidationError('Este nome já está sendo usado por outra operadora.')


class FiltroOperadoraForm(FlaskForm):
    """Formulário para filtros de busca de operadoras"""
    
    nome = StringField(
        'Nome',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por nome...'
        }
    )
    
    codigo = StringField(
        'Código',
        render_kw={
            'class': 'form-control',
            'placeholder': 'Filtrar por código...'
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
    
    rpa = SelectField(
        'RPA',
        choices=[
            ('', 'Todos'),
            ('com_rpa', 'Com RPA'),
            ('sem_rpa', 'Sem RPA')
        ],
        render_kw={
            'class': 'form-select'
        }
    )ass': 'form-select'
        }
    )
