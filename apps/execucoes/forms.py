"""
Formulários do módulo de Execuções
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, DateField
from wtforms.validators import Optional


class ExecucaoFiltroForm(FlaskForm):
    """Formulário para filtrar execuções"""
    
    busca = StringField(
        'Busca',
        validators=[Optional()],
        render_kw={'placeholder': 'Buscar por processo, cliente, job ID...'}
    )
    
    status = SelectField(
        'Status',
        choices=[
            ('', 'Todos os status'),
            ('EXECUTANDO', 'Executando'),
            ('CONCLUIDO', 'Concluído'),
            ('FALHOU', 'Falhou'),
            ('TENTANDO_NOVAMENTE', 'Tentando Novamente'),
            ('CANCELADO', 'Cancelado'),
            ('TIMEOUT', 'Timeout')
        ],
        validators=[Optional()],
        default=''
    )
    
    tipo = SelectField(
        'Tipo',
        choices=[
            ('', 'Todos os tipos'),
            ('DOWNLOAD_FATURA', 'Download de Fatura'),
            ('UPLOAD_SAT', 'Upload SAT'),
            ('UPLOAD_MANUAL', 'Upload Manual')
        ],
        validators=[Optional()],
        default=''
    )
    
    operadora = SelectField(
        'Operadora',
        choices=[('', 'Todas as operadoras')],
        validators=[Optional()],
        coerce=str,
        default=''
    )
    
    data_inicio = DateField(
        'Data Início',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    
    data_fim = DateField(
        'Data Fim',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
