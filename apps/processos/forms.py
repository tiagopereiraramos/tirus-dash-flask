from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, DecimalField, TextAreaField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from wtforms.widgets import TextInput

from apps.models import Cliente, Operadora
from apps.models.processo import StatusProcesso
from apps import db


class ProcessoFiltroForm(FlaskForm):
    """Formulário para filtros na listagem de processos"""

    busca = StringField(
        'Buscar',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': 'Cliente, CNPJ, operadora...'}
    )

    status = SelectField(
        'Status',
        choices=[('', 'Todos')] + [(s.value, s.value.replace('_', ' ').title()) for s in StatusProcesso],
        validators=[Optional()]
    )

    mes_ano = StringField(
        'Mês/Ano',
        validators=[Optional(), Length(max=7)],
        render_kw={'placeholder': 'MM/AAAA'}
    )

    operadora = SelectField(
        'Operadora',
        choices=[('', 'Todas')],
        validators=[Optional()],
        coerce=str
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carregar operadoras dinamicamente
        operadoras = db.session.query(Operadora).filter(Operadora.status_ativo == True).all()
        self.operadora.choices = [('', 'Todas')] + [(str(op.id), op.nome) for op in operadoras]


class ProcessoForm(FlaskForm):
    """Formulário para criação/edição de processos"""

    cliente_id = SelectField(
        'Cliente',
        validators=[DataRequired(message='Cliente é obrigatório')],
        coerce=str
    )

    mes_ano = StringField(
        'Mês/Ano',
        validators=[DataRequired(message='Mês/Ano é obrigatório'), Length(max=7)],
        render_kw={'placeholder': 'MM/AAAA'}
    )

    status_processo = SelectField(
        'Status do Processo',
        choices=[
            ('AGUARDANDO_DOWNLOAD', 'Aguardando Download'),
            ('DOWNLOAD_COMPLETO', 'Download Completo'),
            ('UPLOAD_SAT_REALIZADO', 'Upload SAT Realizado'),
            ('DOWNLOAD_EM_ANDAMENTO', 'Download em Andamento'),
            ('DOWNLOAD_FALHOU', 'Download Falhou'),
            ('AGUARDANDO_APROVACAO', 'Aguardando Aprovação'),
            ('APROVADO', 'Aprovado'),
            ('REJEITADO', 'Rejeitado'),
            ('ENVIANDO_SAT', 'Enviando para SAT'),
            ('ENVIADO_SAT', 'Enviado para SAT'),
            ('FALHA_ENVIO_SAT', 'Falha no Envio SAT'),
            ('CONCLUIDO', 'Concluído'),
            ('CANCELADO', 'Cancelado')
        ],
        default='AGUARDANDO_DOWNLOAD',
        validators=[DataRequired()]
    )

    url_fatura = StringField(
        'URL da Fatura',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': 'URL da fatura no portal da operadora'}
    )

    data_vencimento = DateField(
        'Data de Vencimento',
        validators=[Optional()]
    )

    valor_fatura = DecimalField(
        'Valor da Fatura',
        validators=[Optional(), NumberRange(min=0, message='Valor deve ser positivo')],
        places=2
    )

    upload_manual = BooleanField(
        'Upload Manual',
        default=False
    )

    criado_automaticamente = BooleanField(
        'Criado Automaticamente',
        default=True
    )

    observacoes = TextAreaField(
        'Observações',
        validators=[Optional()],
        render_kw={'rows': 4, 'placeholder': 'Observações sobre o processo...'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carregar clientes ativos dinamicamente
        clientes = db.session.query(Cliente)\
            .join(Operadora)\
            .filter(Cliente.status_ativo == True, Operadora.status_ativo == True)\
            .order_by(Cliente.razao_social)\
            .all()

        self.cliente_id.choices = [
            (str(cliente.id), f"{cliente.razao_social} ({cliente.operadora.nome})")
            for cliente in clientes
        ]


class AprovacaoForm(FlaskForm):
    """Formulário para aprovação/rejeição de processos"""

    observacoes = TextAreaField(
        'Observações',
        validators=[Optional()],
        render_kw={'rows': 3, 'placeholder': 'Observações sobre a aprovação/rejeição...'}
    )

    acao = HiddenField(
        validators=[DataRequired()]
    )


class CriarProcessosMensaisForm(FlaskForm):
    """Formulário para criação em massa de processos mensais"""

    mes_ano = StringField(
        'Mês/Ano',
        validators=[DataRequired(message='Mês/Ano é obrigatório'), Length(max=7)],
        render_kw={'placeholder': 'MM/AAAA'}
    )

    operadora_id = SelectField(
        'Operadora (opcional)',
        choices=[('', 'Todas as operadoras')],
        validators=[Optional()],
        coerce=str
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Carregar operadoras ativas
        operadoras = db.session.query(Operadora).filter(Operadora.status_ativo == True).all()
        self.operadora_id.choices = [('', 'Todas as operadoras')] + [
            (str(op.id), op.nome) for op in operadoras
        ]