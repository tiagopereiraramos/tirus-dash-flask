"""
Rotas para logs em tempo real via Server-Sent Events
Integração cirúrgica com a API externa de logs
"""

from flask import Blueprint, Response, request, current_app
from flask_login import login_required
import requests
import json
import logging
from typing import Generator, Dict, Any

# Configurar logging
logger = logging.getLogger(__name__)

# Criar blueprint
api_logs_tempo_real_bp = Blueprint(
    'api_logs_tempo_real', __name__, url_prefix='/api/v2/logs-tempo-real')

def get_api_token() -> str:
    """Obtém token JWT global do sistema"""
    try:
        from apps.api_externa.auth import get_auth
        auth = get_auth()
        token = auth.token
        if not token:
            logger.error("Token JWT não encontrado no sistema")
            raise ValueError("Token JWT não configurado")
        return token
    except Exception as e:
        logger.error(f"Erro ao obter token JWT: {e}")
        raise


def stream_logs_filtrados(job_id: str, api_url: str, token: str) -> Generator[str, None, None]:
    """
    Stream de logs filtrados por job_id da API externa

    Args:
        job_id: ID do job para filtrar logs
        api_url: URL base da API externa
        token: Token JWT para autenticação

    Yields:
        str: Dados de log formatados para SSE
    """
    try:
        # URL do endpoint de logs da API externa
        url = f"{api_url}/events/logs"

        # Headers com autenticação
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }

        logger.info(f"Iniciando stream de logs para job_id: {job_id}")

        # Fazer requisição para a API externa
        # IMPORTANTE: Sem read timeout, apenas connect timeout
        # SSE streams podem ficar silenciosos por longos períodos
        response = requests.get(url, headers=headers, stream=True, timeout=(10, None))
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
                                'job_id': job_id,
                                'timestamp': data.get('timestamp', ''),
                                'service': data.get('service', 'rpa-api'),
                                'logger': data.get('logger', 'app.main')
                            }

                            # Detectar conclusão do job
                            message = data.get('message', '').lower()
                            level = data.get('level', 'INFO')
                            
                            if level == 'WARN' and 'concluído' in message and 'deve ser atualizado' in message:
                                # Job terminou - extrair status
                                if 'completed' in message.lower():
                                    formatted_data['job_status'] = 'COMPLETED'
                                    formatted_data['type'] = 'job_completed'
                                elif 'failed' in message.lower() or 'erro' in message:
                                    formatted_data['job_status'] = 'FAILED'
                                    formatted_data['type'] = 'job_failed'
                                else:
                                    formatted_data['job_status'] = 'COMPLETED'
                                    formatted_data['type'] = 'job_completed'

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
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Erro inesperado no stream de logs: {e}")
        logger.error(f"Traceback completo:\n{tb}")
        # Enviar mensagem de erro
        error_data = {
            'type': 'error',
            'message': f'Erro interno: {str(e)}',
            'timestamp': ''
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@api_logs_tempo_real_bp.route('/stream/<job_id>')
@login_required
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

        # IMPORTANTE: Obter configurações ANTES do generator para evitar erro de contexto
        api_url = current_app.config.get('API_EXTERNA_URL', 'http://191.252.218.230:8000')
        
        # Obter token JWT diretamente para evitar erro de contexto
        # Prioridade: 1) Admin user token, 2) Config token
        from apps.authentication.models import Users
        token = None
        admin_user = Users.query.filter_by(is_admin=True).first()
        if admin_user and admin_user.api_externa_token:
            token = admin_user.api_externa_token
        else:
            token = current_app.config.get('API_EXTERNA_TOKEN')
        
        if not token:
            raise ValueError("Token JWT não configurado no sistema")

        def generate():
            # Enviar evento de conexão
            connection_data = {
                'type': 'connection',
                'message': f'Conectado ao stream de logs para job {job_id}',
                'timestamp': ''
            }
            yield f"data: {json.dumps(connection_data)}\n\n"

            # Stream de logs filtrados (passar api_url e token como parâmetros)
            for log_data in stream_logs_filtrados(job_id, api_url, token):
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


@api_logs_tempo_real_bp.route('/atualizar-status/<job_id>', methods=['POST'])
@login_required
def atualizar_status_job(job_id: str):
    """
    Atualiza o status de uma execução quando o job termina
    
    Args:
        job_id: ID do job que terminou
        
    Expected JSON body:
        {
            "status": "COMPLETED" ou "FAILED",
            "mensagem": "Mensagem opcional"
        }
    
    Returns:
        JSON: Resultado da atualização
    """
    from flask import request, jsonify
    from apps.models.execucao import Execucao, StatusExecucao
    from apps import db
    from datetime import datetime
    
    try:
        # Obter dados do request
        data = request.get_json() or {}
        novo_status = data.get('status', 'COMPLETED')
        mensagem = data.get('mensagem', '')
        
        # Buscar execução pelo job_id
        execucao = Execucao.query.filter_by(job_id=job_id).first()
        
        if not execucao:
            logger.warning(f"Execução não encontrada para job_id: {job_id}")
            return jsonify({
                'success': False,
                'message': f'Execução não encontrada para job_id: {job_id}'
            }), 404
        
        # Atualizar status
        if novo_status == 'COMPLETED':
            execucao.status_execucao = StatusExecucao.CONCLUIDO.value
            if not mensagem:
                mensagem = 'Job concluído com sucesso'
        elif novo_status == 'FAILED':
            execucao.status_execucao = StatusExecucao.FALHOU.value
            if not mensagem:
                mensagem = 'Job falhou'
        else:
            execucao.status_execucao = novo_status
        
        # Persistir data_fim para métricas de duração
        if not execucao.data_fim:
            execucao.data_fim = datetime.now()
        
        # Adicionar mensagem aos logs
        if mensagem:
            logs_atuais = execucao.mensagem_log or ''
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execucao.mensagem_log = f"{logs_atuais}\n[{timestamp}] {mensagem}"
        
        # Salvar no banco
        db.session.commit()
        
        logger.info(f"Status da execução {execucao.id} atualizado para {novo_status} (job_id: {job_id})")
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso',
            'execucao_id': str(execucao.id),
            'novo_status': execucao.status_execucao
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status do job {job_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500


@api_logs_tempo_real_bp.route('/status-job/<job_id>')
@login_required
def consultar_status_job(job_id: str):
    """
    Consulta o status de um job específico na API externa
    
    Args:
        job_id: ID do job para consultar
        
    Returns:
        JSON: Status do job
    """
    from flask import jsonify
    
    try:
        # Obter configurações
        api_url = current_app.config.get('API_EXTERNA_URL', 'http://191.252.218.230:8000')
        
        # Obter token JWT diretamente
        from apps.authentication.models import Users
        token = None
        admin_user = Users.query.filter_by(is_admin=True).first()
        if admin_user and admin_user.api_externa_token:
            token = admin_user.api_externa_token
        else:
            token = current_app.config.get('API_EXTERNA_TOKEN')
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Token JWT não configurado no sistema'
            }), 401
        
        # Consultar status na API externa
        url = f"{api_url}/jobs/{job_id}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Retornar dados do job
        job_data = response.json()
        
        return jsonify({
            'success': True,
            'job': job_data
        }), 200
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return jsonify({
                'success': False,
                'message': f'Job {job_id} não encontrado na API externa'
            }), 404
        else:
            logger.error(f"Erro HTTP ao consultar job {job_id}: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro ao consultar API externa: {e.response.status_code}'
            }), 500
    except Exception as e:
        logger.error(f"Erro ao consultar status do job {job_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao consultar status: {str(e)}'
        }), 500


@api_logs_tempo_real_bp.route('/teste-conexao')
@login_required
def teste_conexao():
    """
    Endpoint para testar conexão com a API externa de logs

    Returns:
        dict: Status da conexão
    """
    try:
        # Verificar se o token JWT está configurado
        try:
            token = get_api_token()
        except Exception as e:
            return {
                'success': False,
                'message': 'Token JWT não configurado no sistema',
                'error': str(e),
                'status_code': 401
            }
        
        # Verificar se a API externa está acessível (apenas ping, não esperar stream)
        api_url = current_app.config.get('API_EXTERNA_URL', 'http://191.252.218.230:8000')
        ping_url = f"{api_url}/docs"  # Endpoint que responde rápido
        
        try:
            ping_response = requests.get(ping_url, timeout=3)
            api_online = ping_response.status_code == 200
        except:
            api_online = False

        return {
            'success': True,
            'message': 'Sistema de logs em tempo real configurado corretamente',
            'token_status': 'Token JWT global válido',
            'api_externa_status': 'ONLINE' if api_online else 'OFFLINE',
            'sse_endpoint': f"{api_url}/events/logs",
            'status_code': 200
        }

    except Exception as e:
        logger.error(f"Erro inesperado no teste de conexão: {e}")
        return {
            'success': False,
            'message': f'Erro interno: {str(e)}',
            'status_code': 500
        }
