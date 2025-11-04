"""
Formulários para gerenciamento de agendamentos
"""

from datetime import datetime
from typing import Optional as TypingOptional, Dict, Any

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional as WTOptional, Length, ValidationError

from apps.models import Agendamento, TipoAgendamento, Operadora


class CronHelper:
    """Helper para converter configurações amigáveis em expressão cron"""

    @staticmethod
    def frequencia_to_cron(frequencia: str, hora: int, minuto: int,
                           dia_semana: TypingOptional[str] = None,
                           dia_mes: TypingOptional[int] = None) -> str:
        """
        Converte configurações amigáveis em expressão cron

        Args:
            frequencia: 'diario', 'semanal', 'mensal'
            hora: Hora do dia (0-23)
            minuto: Minuto (0-59)
            dia_semana: Dia da semana para frequência semanal (0-6, onde 0=domingo)
            dia_mes: Dia do mês para frequência mensal (1-31)

        Returns:
            Expressão cron no formato padrão
        """
        if frequencia == 'diario':
            return f"{minuto} {hora} * * *"
        elif frequencia == 'semanal' and dia_semana is not None:
            return f"{minuto} {hora} * * {dia_semana}"
        elif frequencia == 'mensal' and dia_mes is not None:
            return f"{minuto} {hora} {dia_mes} * *"
        else:
            # Fallback para diário
            return f"{minuto} {hora} * * *"

    @staticmethod
    def cron_to_frequencia(cron: str) -> Dict[str, Any]:
        """
        Converte expressão cron em configurações amigáveis

        Args:
            cron: Expressão cron no formato padrão

        Returns:
            Dicionário com configurações amigáveis
        """
        try:
            partes = cron.strip().split()
            if len(partes) != 5:
                return {'frequencia': 'diario', 'hora': 0, 'minuto': 0}

            minuto, hora, dia, mes, dia_semana = partes

            # Converter para inteiros
            minuto = int(minuto) if minuto != '*' else 0
            hora = int(hora) if hora != '*' else 0

            # Determinar frequência
            if dia_semana != '*':
                return {
                    'frequencia': 'semanal',
                    'hora': hora,
                    'minuto': minuto,
                    'dia_semana': dia_semana
                }
            elif dia != '*':
                return {
                    'frequencia': 'mensal',
                    'hora': hora,
                    'minuto': minuto,
                    'dia_mes': int(dia)
                }
            else:
                return {
                    'frequencia': 'diario',
                    'hora': hora,
                    'minuto': minuto
                }
        except:
            return {'frequencia': 'diario', 'hora': 0, 'minuto': 0}


class AgendamentoForm(FlaskForm):
    """Formulário para cadastro/edição de agendamentos"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Popular opções de operadora
        operadoras = Operadora.query.filter_by(
            status_ativo=True).order_by(Operadora.nome).all()
        self.operadora.choices = [('', '-- Selecione uma operadora (opcional) --')] + [
            (str(op.id), f"{op.nome} ({op.codigo})") for op in operadoras
        ]

    nome_agendamento = StringField(
        'Nome do Agendamento',
        validators=[DataRequired(), Length(min=3, max=255)],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Ex: Downloads Embratel'
        }
    )

    descricao = TextAreaField(
        'Descrição',
        validators=[WTOptional(), Length(max=1000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descreva o propósito deste agendamento...'
        }
    )

    # Campos amigáveis para cron
    frequencia = SelectField(
        'Frequência',
        choices=[
            ('diario', 'Diário'),
            ('semanal', 'Semanal'),
            ('mensal', 'Mensal')
        ],
        validators=[DataRequired()],
        render_kw={
            'class': 'form-select'
        }
    )

    hora = SelectField(
        'Hora',
        choices=[(str(i), f"{i:02d}:00") for i in range(24)],
        validators=[DataRequired()],
        render_kw={
            'class': 'form-select'
        }
    )

    minuto = SelectField(
        'Minuto',
        choices=[(str(i), f"{i:02d}")
                 for i in range(0, 60, 5)],  # A cada 5 minutos
        validators=[DataRequired()],
        render_kw={
            'class': 'form-select'
        }
    )

    dia_semana = SelectField(
        'Dia da Semana',
        choices=[
            ('1', 'Segunda-feira'),
            ('2', 'Terça-feira'),
            ('3', 'Quarta-feira'),
            ('4', 'Quinta-feira'),
            ('5', 'Sexta-feira'),
            ('6', 'Sábado'),
            ('0', 'Domingo')
        ],
        validators=[WTOptional()],
        render_kw={
            'class': 'form-select'
        }
    )

    dia_mes = SelectField(
        'Dia do Mês',
        # 1-28 para evitar problemas com fevereiro
        choices=[(str(i), str(i)) for i in range(1, 29)],
        validators=[WTOptional()],
        render_kw={
            'class': 'form-select'
        }
    )

    # Campo oculto para a expressão cron gerada
    cron_expressao = StringField(
        'Expressão Cron',
        validators=[DataRequired()],
        render_kw={
            'type': 'hidden'
        }
    )

    tipo_agendamento = SelectField(
        'Tipo de Agendamento',
        choices=[
            ('CRIAR_PROCESSOS_MENSAIS', 'Criar Processos Mensais'),
            ('EXECUTAR_DOWNLOADS', 'Executar Downloads'),
            ('ENVIAR_RELATORIOS', 'Enviar Relatórios'),
            ('LIMPEZA_LOGS', 'Limpeza de Logs'),
            ('BACKUP_DADOS', 'Backup de Dados')
        ],
        validators=[DataRequired()],
        render_kw={
            'class': 'form-select'
        }
    )

    operadora = SelectField(
        'Operadora (Opcional)',
        coerce=str,
        validators=[WTOptional()],
        render_kw={
            'class': 'form-select'
        }
    )

    status_ativo = BooleanField(
        'Status Ativo',
        default=True,
        render_kw={
            'class': 'form-check-input'
        }
    )

    def validate(self, extra_validators=None):
        """Validação customizada do formulário"""
        if not super().validate(extra_validators=extra_validators):
            return False

        # Validar campos específicos por frequência
        if self.frequencia.data == 'semanal' and not self.dia_semana.data:
            self.dia_semana.errors.append(
                'Dia da semana é obrigatório para frequência semanal')
            return False

        if self.frequencia.data == 'mensal' and not self.dia_mes.data:
            self.dia_mes.errors.append(
                'Dia do mês é obrigatório para frequência mensal')
            return False

        # Gerar expressão cron
        cron = CronHelper.frequencia_to_cron(
            frequencia=self.frequencia.data,
            hora=int(self.hora.data),
            minuto=int(self.minuto.data),
            dia_semana=self.dia_semana.data if self.frequencia.data == 'semanal' else None,
            dia_mes=int(
                self.dia_mes.data) if self.frequencia.data == 'mensal' else None
        )

        self.cron_expressao.data = cron
        return True


class FiltroAgendamentoForm(FlaskForm):
    """Formulário para filtros de busca de agendamentos"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Popular opções de operadora
        operadoras = Operadora.query.filter_by(
            status_ativo=True).order_by(Operadora.nome).all()
        self.operadora.choices = [('', 'Todas')] + [
            (str(op.id), f"{op.nome} ({op.codigo})") for op in operadoras
        ]

    nome = StringField(
        'Nome',
        validators=[WTOptional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Buscar por nome...'
        }
    )

    tipo = SelectField(
        'Tipo',
        choices=[
            ('', 'Todos'),
            ('CRIAR_PROCESSOS_MENSAIS', 'Criar Processos Mensais'),
            ('EXECUTAR_DOWNLOADS', 'Executar Downloads'),
            ('ENVIAR_RELATORIOS', 'Enviar Relatórios'),
            ('LIMPEZA_LOGS', 'Limpeza de Logs'),
            ('BACKUP_DADOS', 'Backup de Dados')
        ],
        render_kw={
            'class': 'form-select'
        }
    )

    operadora = SelectField(
        'Operadora',
        render_kw={
            'class': 'form-select'
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
