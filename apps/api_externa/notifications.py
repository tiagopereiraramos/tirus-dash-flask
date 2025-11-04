"""
Sistema de Notificações para API Externa Funcional
Gerencia notificações em tempo real, emails e alertas
"""
import logging
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from threading import Thread, Lock
import queue

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuração de notificação"""
    email_enabled: bool = False
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: List[str] = None

    push_enabled: bool = False
    webhook_url: str = ""

    # Configurações de alerta
    notify_on_success: bool = True
    notify_on_failure: bool = True
    notify_on_timeout: bool = True
    notify_on_cancel: bool = False

    # Thresholds
    failure_threshold: int = 3  # Notificar após N falhas consecutivas
    timeout_threshold: int = 300  # Segundos

    def __post_init__(self):
        if self.email_to is None:
            self.email_to = []


@dataclass
class NotificationEvent:
    """Evento de notificação"""
    id: str
    tipo: str  # 'success', 'failure', 'timeout', 'cancel', 'info'
    job_id: str
    processo_id: str
    operadora: str
    mensagem: str
    detalhes: Dict[str, Any] = None
    timestamp: datetime = None
    enviado: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.detalhes is None:
            self.detalhes = {}


class NotificationManager:
    """Gerenciador de notificações"""

    def __init__(self, config: NotificationConfig = None):
        """
        Inicializa o gerenciador de notificações

        Args:
            config: Configuração de notificações
        """
        self.config = config or NotificationConfig()
        self.notifications: List[NotificationEvent] = []
        self.lock = Lock()
        self.email_queue = queue.Queue()
        self.failure_count: Dict[str, int] = {}  # job_id -> count

        # Iniciar thread de processamento de emails
        if self.config.email_enabled:
            self.email_thread = Thread(target=self._email_worker, daemon=True)
            self.email_thread.start()

        logger.info("NotificationManager inicializado")

    def notify_job_success(self, job_id: str, processo_id: str, operadora: str,
                           resultado: str = None):
        """Notifica sucesso de job"""
        if not self.config.notify_on_success:
            return

        mensagem = f"Job {job_id} concluído com sucesso"
        if resultado:
            mensagem += f" - {resultado}"

        self._create_notification(
            tipo='success',
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes={'resultado': resultado}
        )

    def notify_job_failure(self, job_id: str, processo_id: str, operadora: str,
                           erro: str = None):
        """Notifica falha de job"""
        if not self.config.notify_on_failure:
            return

        # Contar falhas consecutivas
        with self.lock:
            self.failure_count[job_id] = self.failure_count.get(job_id, 0) + 1
            failure_count = self.failure_count[job_id]

        # Só notificar após threshold
        if failure_count < self.config.failure_threshold:
            return

        mensagem = f"Job {job_id} falhou (tentativa #{failure_count})"
        if erro:
            mensagem += f" - {erro}"

        self._create_notification(
            tipo='failure',
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes={'erro': erro, 'tentativa': failure_count}
        )

    def notify_job_timeout(self, job_id: str, processo_id: str, operadora: str,
                           duracao: int = None):
        """Notifica timeout de job"""
        if not self.config.notify_on_timeout:
            return

        mensagem = f"Job {job_id} atingiu timeout"
        if duracao:
            mensagem += f" após {duracao} segundos"

        self._create_notification(
            tipo='timeout',
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes={'duracao': duracao}
        )

    def notify_job_cancel(self, job_id: str, processo_id: str, operadora: str,
                          motivo: str = None):
        """Notifica cancelamento de job"""
        if not self.config.notify_on_cancel:
            return

        mensagem = f"Job {job_id} foi cancelado"
        if motivo:
            mensagem += f" - {motivo}"

        self._create_notification(
            tipo='cancel',
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes={'motivo': motivo}
        )

    def notify_info(self, job_id: str, processo_id: str, operadora: str,
                    mensagem: str, detalhes: Dict[str, Any] = None):
        """Notifica informação geral"""
        self._create_notification(
            tipo='info',
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes=detalhes or {}
        )

    def _create_notification(self, tipo: str, job_id: str, processo_id: str,
                             operadora: str, mensagem: str, detalhes: Dict[str, Any] = None):
        """Cria e envia notificação"""
        notification = NotificationEvent(
            id=f"{job_id}_{tipo}_{datetime.now().timestamp()}",
            tipo=tipo,
            job_id=job_id,
            processo_id=processo_id,
            operadora=operadora,
            mensagem=mensagem,
            detalhes=detalhes or {}
        )

        # Adicionar à lista
        with self.lock:
            self.notifications.append(notification)
            # Manter apenas últimas 1000 notificações
            if len(self.notifications) > 1000:
                self.notifications = self.notifications[-1000:]

        # Enviar notificações
        self._send_notifications(notification)

        logger.info(f"Notificação criada: {notification.id} - {mensagem}")

    def _send_notifications(self, notification: NotificationEvent):
        """Envia notificações por diferentes canais"""
        try:
            # Email
            if self.config.email_enabled and self.config.email_to:
                self.email_queue.put(notification)

            # Webhook
            if self.config.push_enabled and self.config.webhook_url:
                self._send_webhook(notification)

            notification.enviado = True

        except Exception as e:
            logger.error(
                f"Erro ao enviar notificação {notification.id}: {str(e)}")

    def _email_worker(self):
        """Worker thread para envio de emails"""
        while True:
            try:
                notification = self.email_queue.get(timeout=60)
                self._send_email(notification)
                self.email_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no email worker: {str(e)}")

    def _send_email(self, notification: NotificationEvent):
        """Envia email de notificação"""
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from
            msg['To'] = ', '.join(self.config.email_to)
            msg['Subject'] = f"[RPA] {notification.tipo.upper()} - {notification.operadora}"

            # Corpo do email
            body = self._create_email_body(notification)
            msg.attach(MIMEText(body, 'html'))

            # Enviar email
            with smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_username,
                             self.config.email_password)
                server.send_message(msg)

            logger.info(f"Email enviado para notificação {notification.id}")

        except Exception as e:
            logger.error(f"Erro ao enviar email: {str(e)}")

    def _create_email_body(self, notification: NotificationEvent) -> str:
        """Cria corpo do email HTML"""
        tipo_cores = {
            'success': '#28a745',
            'failure': '#dc3545',
            'timeout': '#ffc107',
            'cancel': '#6c757d',
            'info': '#17a2b8'
        }

        cor = tipo_cores.get(notification.tipo, '#6c757d')

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {cor}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px; }}
                .detail {{ margin: 5px 0; }}
                .label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Notificação RPA - {notification.tipo.upper()}</h2>
            </div>
            <div class="content">
                <div class="detail">
                    <span class="label">Mensagem:</span> {notification.mensagem}
                </div>
                <div class="detail">
                    <span class="label">Job ID:</span> {notification.job_id}
                </div>
                <div class="detail">
                    <span class="label">Processo ID:</span> {notification.processo_id}
                </div>
                <div class="detail">
                    <span class="label">Operadora:</span> {notification.operadora}
                </div>
                <div class="detail">
                    <span class="label">Data/Hora:</span> {notification.timestamp.strftime('%d/%m/%Y %H:%M:%S')}
                </div>
        """

        if notification.detalhes:
            html += "<div class='detail'><span class='label'>Detalhes:</span></div>"
            for key, value in notification.detalhes.items():
                html += f"<div class='detail' style='margin-left: 20px;'>• {key}: {value}</div>"

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def _send_webhook(self, notification: NotificationEvent):
        """Envia notificação via webhook"""
        try:
            import requests

            payload = {
                'notification_id': notification.id,
                'tipo': notification.tipo,
                'job_id': notification.job_id,
                'processo_id': notification.processo_id,
                'operadora': notification.operadora,
                'mensagem': notification.mensagem,
                'timestamp': notification.timestamp.isoformat(),
                'detalhes': notification.detalhes
            }

            response = requests.post(
                self.config.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                logger.info(
                    f"Webhook enviado para notificação {notification.id}")
            else:
                logger.warning(
                    f"Webhook retornou status {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao enviar webhook: {str(e)}")

    def get_notifications(self, limit: int = 100, tipo: str = None,
                          operadora: str = None) -> List[NotificationEvent]:
        """Obtém notificações com filtros"""
        with self.lock:
            notifications = self.notifications.copy()

        # Aplicar filtros
        if tipo:
            notifications = [n for n in notifications if n.tipo == tipo]

        if operadora:
            notifications = [
                n for n in notifications if n.operadora == operadora]

        # Ordenar por timestamp (mais recentes primeiro)
        notifications.sort(key=lambda x: x.timestamp, reverse=True)

        return notifications[:limit]

    def get_notification_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas de notificações"""
        with self.lock:
            notifications = self.notifications.copy()

        stats = {
            'total': len(notifications),
            'por_tipo': {},
            'por_operadora': {},
            'ultimas_24h': 0,
            'enviadas': 0,
            'falhas': 0
        }

        # Contar por tipo e operadora
        for notification in notifications:
            # Por tipo
            stats['por_tipo'][notification.tipo] = stats['por_tipo'].get(
                notification.tipo, 0) + 1

            # Por operadora
            stats['por_operadora'][notification.operadora] = stats['por_operadora'].get(
                notification.operadora, 0) + 1

            # Últimas 24h
            if notification.timestamp > datetime.now() - timedelta(days=1):
                stats['ultimas_24h'] += 1

            # Enviadas vs falhas
            if notification.enviado:
                stats['enviadas'] += 1
            else:
                stats['falhas'] += 1

        return stats

    def clear_notifications(self, older_than_days: int = 30):
        """Limpa notificações antigas"""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        with self.lock:
            original_count = len(self.notifications)
            self.notifications = [
                n for n in self.notifications
                if n.timestamp > cutoff_date
            ]
            removed_count = original_count - len(self.notifications)

        logger.info(f"Removidas {removed_count} notificações antigas")
        return removed_count

    def reset_failure_count(self, job_id: str):
        """Reseta contador de falhas para um job"""
        with self.lock:
            if job_id in self.failure_count:
                del self.failure_count[job_id]


# Instância global
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Obtém instância global do gerenciador de notificações"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def set_notification_config(config: NotificationConfig):
    """Define configuração de notificações"""
    global _notification_manager
    _notification_manager = NotificationManager(config)
