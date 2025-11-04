"""
Rotas para monitoramento em tempo real da API externa
"""
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context
from typing import Dict, Any, Optional
import json
import threading
import time

from .client import APIExternaClient
from .monitor_tempo_real import get_monitor_tempo_real
from .models import JobStatus

logger = logging.getLogger(__name__)

# Blueprint para rotas de tempo real
api_tempo_real_bp = Blueprint(
    'api_tempo_real', __name__, url_prefix='/api/tempo-real')


@api_tempo_real_bp.route('/status/<job_id>', methods=['GET'])
def obter_status_tempo_real(job_id: str):
    """
    Obtém status em tempo real de um job via Server-Sent Events

    Args:
        job_id: ID do job

    Returns:
        Stream de eventos SSE com status do job
    """
    try:
        client = APIExternaClient()

        def gerar_eventos():
            """Gerador de eventos SSE"""
            try:
                # Conectar ao stream da API externa
                response = client.obter_status_tempo_real(job_id)

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    # Repassar evento da API externa
                    yield f"{line}\n\n"

            except Exception as e:
                logger.error(
                    f"Erro no stream de status para job {job_id}: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(gerar_eventos()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )

    except Exception as e:
        logger.error(
            f"Erro ao obter status em tempo real para job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@api_tempo_real_bp.route('/logs/<job_id>', methods=['GET'])
def obter_logs_tempo_real(job_id: str):
    """
    Obtém logs em tempo real de um job via Server-Sent Events

    Args:
        job_id: ID do job

    Returns:
        Stream de eventos SSE com logs do job
    """
    try:
        client = APIExternaClient()

        def gerar_logs():
            """Gerador de logs SSE"""
            try:
                # Conectar ao stream da API externa
                response = client.obter_logs_tempo_real(job_id)

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    # Repassar evento da API externa
                    yield f"{line}\n\n"

            except Exception as e:
                logger.error(f"Erro no stream de logs para job {job_id}: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(gerar_logs()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )

    except Exception as e:
        logger.error(
            f"Erro ao obter logs em tempo real para job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@api_tempo_real_bp.route('/monitor/<job_id>', methods=['POST'])
def iniciar_monitoramento(job_id: str):
    """
    Inicia monitoramento em tempo real para um job

    Args:
        job_id: ID do job

    Returns:
        Confirmação de início do monitoramento
    """
    try:
        client = APIExternaClient()
        monitor = get_monitor_tempo_real(client)

        # Iniciar monitoramento
        monitor.iniciar_monitoramento(job_id)

        logger.info(f"Monitoramento iniciado para job {job_id}")

        return jsonify({
            'success': True,
            'message': f'Monitoramento iniciado para job {job_id}',
            'job_id': job_id
        })

    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento para job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@api_tempo_real_bp.route('/monitor/<job_id>', methods=['DELETE'])
def parar_monitoramento(job_id: str):
    """
    Para monitoramento de um job

    Args:
        job_id: ID do job

    Returns:
        Confirmação de parada do monitoramento
    """
    try:
        client = APIExternaClient()
        monitor = get_monitor_tempo_real(client)

        # Parar monitoramento
        monitor.parar_monitoramento(job_id)

        logger.info(f"Monitoramento parado para job {job_id}")

        return jsonify({
            'success': True,
            'message': f'Monitoramento parado para job {job_id}',
            'job_id': job_id
        })

    except Exception as e:
        logger.error(f"Erro ao parar monitoramento para job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500


@api_tempo_real_bp.route('/monitor/status', methods=['GET'])
def obter_status_monitoramento():
    """
    Obtém status dos monitoramentos ativos

    Returns:
        Lista de jobs sendo monitorados
    """
    try:
        client = APIExternaClient()
        monitor = get_monitor_tempo_real(client)

        jobs_monitorados = monitor.obter_jobs_monitorados()

        return jsonify({
            'success': True,
            'jobs_monitorados': jobs_monitorados,
            'total': len(jobs_monitorados)
        })

    except Exception as e:
        logger.error(f"Erro ao obter status do monitoramento: {e}")
        return jsonify({'error': str(e)}), 500


@api_tempo_real_bp.route('/teste-conexao', methods=['GET'])
def teste_conexao_tempo_real():
    """
    Testa conexão com os endpoints de tempo real

    Returns:
        Status da conexão
    """
    try:
        client = APIExternaClient()

        # Testar health check
        health_ok = client.health_check()

        if not health_ok:
            return jsonify({
                'success': False,
                'message': 'API externa não está respondendo',
                'health_check': False
            }), 503

        # Testar autenticação
        try:
            # Tentar listar jobs para testar autenticação
            jobs = client.listar_jobs(limit=1)

            return jsonify({
                'success': True,
                'message': 'Conexão com API externa funcionando',
                'health_check': True,
                'autenticacao': True,
                'endpoints_tempo_real': {
                    'status': f'/api/tempo-real/status/{{job_id}}',
                    'logs': f'/api/tempo-real/logs/{{job_id}}',
                    'monitor': f'/api/tempo-real/monitor/{{job_id}}'
                }
            })

        except Exception as auth_error:
            return jsonify({
                'success': False,
                'message': 'Erro de autenticação com API externa',
                'health_check': True,
                'autenticacao': False,
                'error': str(auth_error)
            }), 401

    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro ao testar conexão',
            'error': str(e)
        }), 500

