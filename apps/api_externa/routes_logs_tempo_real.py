"""
Rotas para logs em tempo real via Server-Sent Events
Integração cirúrgica com a API externa de logs
"""

from flask import Blueprint, Response, request, current_app
import requests
import json
import logging
from typing import Generator, Dict, Any

# Configurar logging
logger = logging.getLogger(__name__)

# Criar blueprint
api_logs_tempo_real_bp = Blueprint(
    'api_logs_tempo_real', __name__, url_prefix='/api/v2/logs-tempo-real')

# URL base da API externa
API_EXTERNA_BASE_URL = "http://191.252.218.230:8000"

# Token da API externa
API_EXTERNA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AYnJtc29sdXRpb25zLmNvbS5iciIsInJvbGUiOiJhZG1pbiIsImNyZWF0ZWRfYXQiOiIyMDI1LTA5LTA5VDE1OjEyOjAxLjAxNjQxMCIsImV4cCI6MTc2MDAyMjcyMX0.fF9z68JYx-EhVcP7F9Vk-Yz8G5O4c5dddG8dNy69CRQ"


def stream_logs_filtrados(job_id: str) -> Generator[str, None, None]:
    """
    Stream de logs filtrados por job_id da API externa

    Args:
        job_id: ID do job para filtrar logs

    Yields:
        str: Dados de log formatados para SSE
    """
    try:
        # URL do endpoint de logs da API externa
        url = f"{API_EXTERNA_BASE_URL}/events/logs"

        # Headers com autenticação
        headers = {
            'Authorization': f'Bearer {API_EXTERNA_TOKEN}',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }

        logger.info(f"Iniciando stream de logs para job_id: {job_id}")

        # Fazer requisição para a API externa
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # Processar stream de dados
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # Verificar se é uma linha de dados SSE
                if line.startswith('data: '):
                    try:
                        # Extrair dados JSON
                        json_data = line[6:]  # Remove 'data: '
                        data = json.loads(json_data)

                        # Filtrar logs por job_id
                        if (data.get('type') == 'log' and
                            (data.get('job_id') == job_id or
                             data.get('job_id') == 'UNKNOWN' or
                             not data.get('job_id'))):

                            # Formatar para SSE
                            formatted_data = {
                                'type': data.get('type', 'log'),
                                'level': data.get('level', 'INFO'),
                                'message': data.get('message', ''),
                                'operadora': data.get('operadora', 'UNKNOWN'),
                                'job_id': data.get('job_id', job_id),
                                'timestamp': data.get('timestamp', ''),
                                'service': data.get('service', 'rpa-api'),
                                'logger': data.get('logger', 'app.main')
                            }

                            # Enviar dados formatados
                            yield f"data: {json.dumps(formatted_data)}\n\n"

                    except json.JSONDecodeError as e:
                        logger.warning(f"Erro ao decodificar JSON: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Erro ao processar linha de log: {e}")
                        continue

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para API externa: {e}")
        # Enviar mensagem de erro
        error_data = {
            'type': 'error',
            'message': f'Erro de conexão: {str(e)}',
            'timestamp': ''
        }
        yield f"data: {json.dumps(error_data)}\n\n"

    except Exception as e:
        logger.error(f"Erro inesperado no stream de logs: {e}")
        # Enviar mensagem de erro
        error_data = {
            'type': 'error',
            'message': f'Erro interno: {str(e)}',
            'timestamp': ''
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@api_logs_tempo_real_bp.route('/stream/<job_id>')
def stream_logs(job_id: str):
    """
    Endpoint SSE para logs em tempo real filtrados por job_id

    Args:
        job_id: ID do job para filtrar logs

    Returns:
        Response: Stream de dados SSE
    """
    try:
        logger.info(f"Iniciando stream de logs para job_id: {job_id}")

        def generate():
            # Enviar evento de conexão
            connection_data = {
                'type': 'connection',
                'message': f'Conectado ao stream de logs para job {job_id}',
                'timestamp': ''
            }
            yield f"data: {json.dumps(connection_data)}\n\n"

            # Stream de logs filtrados
            for log_data in stream_logs_filtrados(job_id):
                yield log_data

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )

    except Exception as e:
        logger.error(f"Erro no endpoint de stream de logs: {e}")
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n",
            mimetype='text/event-stream',
            status=500
        )


@api_logs_tempo_real_bp.route('/teste-conexao')
def teste_conexao():
    """
    Endpoint para testar conexão com a API externa de logs

    Returns:
        dict: Status da conexão
    """
    try:
        url = f"{API_EXTERNA_BASE_URL}/events/logs"
        headers = {
            'Authorization': f'Bearer {API_EXTERNA_TOKEN}',
            'Accept': 'text/event-stream'
        }

        # Fazer requisição de teste
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return {
            'success': True,
            'message': 'Conexão com API externa de logs estabelecida com sucesso',
            'status_code': response.status_code
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao testar conexão: {e}")
        return {
            'success': False,
            'message': f'Erro de conexão: {str(e)}',
            'status_code': 500
        }

    except Exception as e:
        logger.error(f"Erro inesperado no teste de conexão: {e}")
        return {
            'success': False,
            'message': f'Erro interno: {str(e)}',
            'status_code': 500
        }
