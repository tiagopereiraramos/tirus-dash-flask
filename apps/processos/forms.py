
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, DateField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from wtforms.widgets import TextArea

from apps.models import Cliente, StatusProcesso


class ProcessoForm(FlaskForm):
    """Formulário para criação/edição de processos"""
    
    cliente_id = SelectField(
        'Cliente',
        validators=[DataRequired(message="Selecione um cliente")],
        coerce=str,
        choices=[]
    )
    
    mes_ano = StringField(
        'Mês/Ano (MM/AAAA)',
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=7, max=7, message="Formato deve ser MM/AAAA")
        ],
        render_kw={"placeholder": "06/2025"}
    )
    
    status_processo = SelectField(
        'Status do Processo',
        validators=[DataRequired(message="Selecione um status")],
        choices=[
            (StatusProcesso.AGUARDANDO_DOWNLOAD.value, 'Aguardando Download'),
            (StatusProcesso.DOWNLOAD_EM_ANDAMENTO.value, 'Download em Andamento'),
            (StatusProcesso.DOWNLOAD_CONCLUIDO.value, 'Download Concluído'),
            (StatusProcesso.DOWNLOAD_FALHOU.value, 'Download Falhou'),
            (StatusProcesso.AGUARDANDO_APROVACAO.value, 'Aguardando Aprovação'),
            (StatusProcesso.APROVADO.value, 'Aprovado'),
            (StatusProcesso.REJEITADO.value, 'Rejeitado'),
            (StatusProcesso.ENVIANDO_SAT.value, 'Enviando SAT'),
            (StatusProcesso.ENVIADO_SAT.value, 'Enviado SAT'),
            (StatusProcesso.FALHA_ENVIO_SAT.value, 'Falha Envio SAT'),
            (StatusProcesso.CONCLUIDO.value, 'Concluído'),
            (StatusProcesso.CANCELADO.value, 'Cancelado')
        ]
    )
    
    url_fatura = StringField(
        'URL da Fatura',
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "https://portal.operadora.com/fatura/123456"}
    )
    
    data_vencimento = DateField(
        'Data de Vencimento',
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    
    valor_fatura = DecimalField(
        'Valor da Fatura (R$)',
        validators=[Optional(), NumberRange(min=0, message="Valor deve ser positivo")],
        places=2,
        render_kw={"step": "0.01", "placeholder": "0.00"}
    )
    
    upload_manual = BooleanField(
        'Upload Manual'
    )
    
    criado_automaticamente = BooleanField(
        'Criado Automaticamente',
        default=True
    )
    
    observacoes = TextAreaField(
        'Observações',
        validators=[Optional(), Length(max=1000)],
        widget=TextArea(),
        render_kw={"rows": 4, "placeholder": "Observações sobre o processo..."}
    )

    def __init__(self, *args, **kwargs):
        super(ProcessoForm, self).__init__(*args, **kwargs)
        self.populate_cliente_choices()

    def populate_cliente_choices(self):
        """Popula as opções de clientes ativos"""
        from apps import db
        clientes = db.session.query(Cliente)\
            .filter(Cliente.status_ativo == True)\
            .order_by(Cliente.razao_social)\
            .all()
        
        self.cliente_id.choices = [('', 'Selecione um cliente')] + [
            (str(cliente.id), f"{cliente.razao_social} - {cliente.operadora.nome}")
            for cliente in clientes
        ]


class ProcessoFiltroForm(FlaskForm):
    """Formulário para filtros de busca de processos"""
    
    busca = StringField(
        'Buscar',
        validators=[Optional()],
        render_kw={"placeholder": "Buscar por cliente, operadora..."}
    )
    
    status = SelectField(
        'Status',
        validators=[Optional()],
        choices=[('', 'Todos os Status')] + [
            (StatusProcesso.AGUARDANDO_DOWNLOAD.value, 'Aguardando Download'),
            (StatusProcesso.DOWNLOAD_EM_ANDAMENTO.value, 'Download em Andamento'),
            (StatusProcesso.DOWNLOAD_CONCLUIDO.value, 'Download Concluído'),
            (StatusProcesso.DOWNLOAD_FALHOU.value, 'Download Falhou'),
            (StatusProcesso.AGUARDANDO_APROVACAO.value, 'Aguardando Aprovação'),
            (StatusProcesso.APROVADO.value, 'Aprovado'),
            (StatusProcesso.REJEITADO.value, 'Rejeitado'),
            (StatusProcesso.ENVIANDO_SAT.value, 'Enviando SAT'),
            (StatusProcesso.ENVIADO_SAT.value, 'Enviado SAT'),
            (StatusProcesso.FALHA_ENVIO_SAT.value, 'Falha Envio SAT'),
            (StatusProcesso.CONCLUIDO.value, 'Concluído'),
            (StatusProcesso.CANCELADO.value, 'Cancelado')
        ]
    )
    
    mes_ano = StringField(
        'Mês/Ano',
        validators=[Optional()],
        render_kw={"placeholder": "MM/AAAA"}
    )
    
    operadora = SelectField(
        'Operadora',
        validators=[Optional()],
        coerce=str,
        choices=[]
    )

    def __init__(self, *args, **kwargs):
        super(ProcessoFiltroForm, self).__init__(*args, **kwargs)
        self.populate_operadora_choices()

    def populate_operadora_choices(self):
        """Popula as opções de operadoras"""
        from apps.models import Operadora
        from apps import db
        
        operadoras = db.session.query(Operadora)\
            .filter(Operadora.status_ativo == True)\
            .order_by(Operadora.nome)\
            .all()
        
        self.operadora.choices = [('', 'Todas as Operadoras')] + [
            (str(op.id), op.nome) for op in operadoras
        ]


class AprovacaoForm(FlaskForm):
    """Formulário para aprovação/rejeição de processos"""
    
    acao = HiddenField(
        validators=[DataRequired()]
    )
    
    observacoes = TextAreaField(
        'Observações',
        validators=[Optional(), Length(max=1000)],
        widget=TextArea(),
        render_kw={"rows": 4, "placeholder": "Observações sobre a aprovação/rejeição..."}
    )


class CriarProcessosMensaisForm(FlaskForm):
    """Formulário para criação automática de processos mensais"""
    
    mes_ano = StringField(
        'Mês/Ano (MM/AAAA)',
        validators=[
            DataRequired(message="Campo obrigatório"),
            Length(min=7, max=7, message="Formato deve ser MM/AAAA")
        ],
        render_kw={"placeholder": "06/2025"}
    )
    
    operadora_id = SelectField(
        'Operadora (opcional)',
        validators=[Optional()],
        coerce=str,
        choices=[]
    )

    def __init__(self, *args, **kwargs):
        super(CriarProcessosMensaisForm, self).__init__(*args, **kwargs)
        self.populate_operadora_choices()

    def populate_operadora_choices(self):
        """Popula as opções de operadoras"""
        from apps.models import Operadora
        from apps import db
        
        operadoras = db.session.query(Operadora)\
            .filter(Operadora.status_ativo == True)\
            .order_by(Operadora.nome)\
            .all()
        
        self.operadora_id.choices = [('', 'Todas as Operadoras')] + [
            (str(op.id), op.nome) for op in operadoras
        ]
