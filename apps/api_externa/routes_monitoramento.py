"""
Rotas para monitoramento em tempo real da API externa
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from flask import request, jsonify, current_app, Blueprint
from flask_login import login_required
from flask_wtf.csrf import generate_csrf
from apps import csrf

from apps import db
from apps.models import Processo, Execucao
from .auth import get_auth
from .services_externos import APIExternaFuncionalService

bp_monitoramento = Blueprint('api_monitoramento', __name__,
                             url_prefix='/api/v2/monitoramento')

logger = logging.getLogger(__name__)


@bp_monitoramento.route('/status/<job_id>', methods=['GET'])
@login_required
def consultar_status_job(job_id):
    """
    Consulta o status de um job específico na API externa

    Args:
        job_id: ID do job a ser consultado

    Returns:
        Status detalhado do job com logs em tempo real
    """
    try:
        logger.info(f"Consultando status do job: {job_id}")

        # Obter serviço da API externa
        service = APIExternaFuncionalService()

        # Consultar status na API externa
        try:
            status = service.consultar_status_job(job_id)

            # Buscar execução relacionada no banco local
            execucao = Execucao.query.filter(
                Execucao.resultado_saida.contains(f'"job_id": "{job_id}"')
            ).first()

            # Preparar resposta com informações completas
            resposta = {
                'success': True,
                'job_id': job_id,
                'status': {
                    'status': status.status,
                    'progress': status.progress,
                    'result': status.result,
                    'error': status.error,
                    'created_at': status.created_at,
                    'started_at': status.started_at,
                    'completed_at': status.completed_at,
                    'logs': status.logs
                },
                'execucao_local': {
                    'id': str(execucao.id) if execucao else None,
                    'processo_id': str(execucao.processo_id) if execucao else None,
                    'tipo_execucao': execucao.tipo_execucao if execucao else None,
                    'status_execucao': execucao.status_execucao if execucao else None,
                    'data_inicio': execucao.data_inicio.isoformat() if execucao and execucao.data_inicio else None,
                    'data_fim': execucao.data_fim.isoformat() if execucao and execucao.data_fim else None,
                    'duracao_segundos': execucao.duracao_segundos if execucao else None
                },
                'timestamp': datetime.now().isoformat()
            }

            # Se o job foi concluído, atualizar execução local automaticamente
            if status.status in ['COMPLETED', 'FAILED'] and execucao:
                logger.info(
                    f"Job {job_id} concluído com status {status.status}, atualizando execução local")
                service.atualizar_status_processo_automatico(
                    job_id, str(execucao.processo_id))

            return jsonify(resposta)

        except Exception as api_error:
            logger.error(
                f"Erro ao consultar job {job_id} na API externa: {str(api_error)}")
            return jsonify({
                'success': False,
                'error': 'ERRO_CONSULTA_API',
                'message': f'Erro ao consultar job na API externa: {str(api_error)}',
                'job_id': job_id
            }), 500

    except Exception as e:
        logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_CONSULTAR_JOB',
            'message': f'Erro ao consultar job: {str(e)}',
            'job_id': job_id
        }), 500


@bp_monitoramento.route('/jobs/ativos', methods=['GET'])
@login_required
def listar_jobs_ativos():
    """
    Lista todos os jobs ativos na API externa

    Returns:
        Lista de jobs ativos com status e informações básicas
    """
    try:
        logger.info("Listando jobs ativos da API externa")

        # Obter autenticação
        auth = get_auth()

        # Consultar jobs ativos na API externa
        try:
            resultado = auth.list_jobs()

            if resultado['success']:
                jobs = resultado.get('jobs', [])

                # Enriquecer com informações locais
                jobs_enriquecidos = []
                for job in jobs:
                    job_id = job.get('job_id', '')

                    # Buscar execução relacionada
                    execucao = Execucao.query.filter(
                        Execucao.resultado_saida.contains(
                            f'"job_id": "{job_id}"')
                    ).first()

                    job_enriquecido = {
                        'job_id': job_id,
                        'status': job.get('status', 'UNKNOWN'),
                        'progress': job.get('progress', 0),
                        'operadora': job.get('operadora', ''),
                        'created_at': job.get('created_at'),
                        'started_at': job.get('started_at'),
                        'execucao_local': {
                            'id': str(execucao.id) if execucao else None,
                            'processo_id': str(execucao.processo_id) if execucao else None,
                            'tipo_execucao': execucao.tipo_execucao if execucao else None,
                            'status_execucao': execucao.status_execucao if execucao else None
                        }
                    }
                    jobs_enriquecidos.append(job_enriquecido)

                return jsonify({
                    'success': True,
                    'jobs': jobs_enriquecidos,
                    'total': len(jobs_enriquecidos),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'ERRO_LISTAR_JOBS',
                    'message': resultado.get('message', 'Erro ao listar jobs'),
                    'details': resultado.get('error')
                }), 500

        except Exception as api_error:
            logger.error(
                f"Erro ao listar jobs na API externa: {str(api_error)}")
            return jsonify({
                'success': False,
                'error': 'ERRO_CONSULTA_API',
                'message': f'Erro ao consultar API externa: {str(api_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Erro ao listar jobs ativos: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_LISTAR_JOBS',
            'message': f'Erro ao listar jobs: {str(e)}'
        }), 500


@bp_monitoramento.route('/processo/<processo_id>/jobs', methods=['GET'])
@login_required
def listar_jobs_processo(processo_id):
    """
    Lista todos os jobs relacionados a um processo específico

    Args:
        processo_id: ID do processo

    Returns:
        Lista de jobs do processo com status detalhado
    """
    try:
        logger.info(f"Listando jobs do processo: {processo_id}")

        # Verificar se processo existe
        processo = Processo.query.get_or_404(processo_id)

        # Buscar execuções do processo que têm jobs associados
        execucoes = Execucao.query.filter_by(processo_id=processo_id).order_by(
            Execucao.data_inicio.desc()).all()

        jobs_data = []
        for execucao in execucoes:
            if execucao.tem_job_associado():
                job_id = execucao.get_job_id()

                # Consultar status atual na API externa
                try:
                    service = APIExternaFuncionalService()
                    status = service.consultar_status_job(job_id)

                    job_info = {
                        'job_id': job_id,
                        'execucao_id': str(execucao.id),
                        'tipo_execucao': execucao.tipo_execucao,
                        'status_execucao': execucao.status_execucao,
                        'status_api': status.status,
                        'progress': status.progress,
                        'result': status.result,
                        'error': status.error,
                        'created_at': status.created_at,
                        'started_at': status.started_at,
                        'completed_at': status.completed_at,
                        'logs': status.logs,
                        'data_inicio': execucao.data_inicio.isoformat() if execucao.data_inicio else None,
                        'data_fim': execucao.data_fim.isoformat() if execucao.data_fim else None,
                        'duracao_segundos': execucao.duracao_segundos
                    }
                    jobs_data.append(job_info)

                except Exception as e:
                    logger.error(f"Erro ao consultar job {job_id}: {str(e)}")
                    # Adicionar job com informações limitadas
                    job_info = {
                        'job_id': job_id,
                        'execucao_id': str(execucao.id),
                        'tipo_execucao': execucao.tipo_execucao,
                        'status_execucao': execucao.status_execucao,
                        'status_api': 'ERRO_CONSULTA',
                        'error': f'Erro ao consultar status: {str(e)}',
                        'data_inicio': execucao.data_inicio.isoformat() if execucao.data_inicio else None,
                        'data_fim': execucao.data_fim.isoformat() if execucao.data_fim else None,
                        'duracao_segundos': execucao.duracao_segundos
                    }
                    jobs_data.append(job_info)

        return jsonify({
            'success': True,
            'processo_id': str(processo.id),
            'processo_info': {
                'cliente': processo.cliente.razao_social,
                'operadora': processo.cliente.operadora.nome if processo.cliente.operadora else None,
                'mes_ano': processo.mes_ano,
                'status_processo': processo.status_processo
            },
            'jobs': jobs_data,
            'total': len(jobs_data),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(
            f"Erro ao listar jobs do processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_LISTAR_JOBS_PROCESSO',
            'message': f'Erro ao listar jobs do processo: {str(e)}'
        }), 500


@bp_monitoramento.route('/conexao/teste', methods=['GET'])
@login_required
def testar_conexao_api():
    """
    Testa a conexão com a API externa

    Returns:
        Status da conexão e informações da API
    """
    try:
        logger.info("Testando conexão com API externa")

        # Obter autenticação
        auth = get_auth()

        # Testar conexão
        resultado = auth.test_connection()

        if resultado['success']:
            return jsonify({
                'success': True,
                'message': 'Conexão com API externa estabelecida com sucesso',
                'status': resultado.get('status', {}),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'ERRO_CONEXAO',
                'message': resultado.get('message', 'Erro ao conectar com API externa'),
                'details': resultado.get('error')
            }), 500

    except Exception as e:
        logger.error(f"Erro ao testar conexão com API externa: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_TESTE_CONEXAO',
            'message': f'Erro ao testar conexão: {str(e)}'
        }), 500


@bp_monitoramento.route('/logs/<job_id>', methods=['GET'])
@login_required
def obter_logs_job(job_id):
    """
    Obtém logs detalhados de um job específico

    Args:
        job_id: ID do job

    Returns:
        Logs detalhados do job
    """
    try:
        logger.info(f"Obtendo logs do job: {job_id}")

        # Obter serviço da API externa
        service = APIExternaFuncionalService()

        # Consultar status completo (inclui logs)
        try:
            status = service.consultar_status_job(job_id)

            return jsonify({
                'success': True,
                'job_id': job_id,
                'logs': status.logs or [],
                'total_logs': len(status.logs) if status.logs else 0,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as api_error:
            logger.error(
                f"Erro ao obter logs do job {job_id}: {str(api_error)}")
            return jsonify({
                'success': False,
                'error': 'ERRO_OBTER_LOGS',
                'message': f'Erro ao obter logs: {str(api_error)}',
                'job_id': job_id
            }), 500

    except Exception as e:
        logger.error(f"Erro ao obter logs do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_OBTER_LOGS',
            'message': f'Erro ao obter logs: {str(e)}',
            'job_id': job_id
        }), 500


@bp_monitoramento.route('/cancelar/<job_id>', methods=['DELETE'])
@login_required
def cancelar_job(job_id):
    """
    Cancela um job em execução

    Args:
        job_id: ID do job a ser cancelado

    Returns:
        Confirmação do cancelamento
    """
    try:
        logger.info(f"Cancelando job: {job_id}")

        # Obter autenticação
        auth = get_auth()

        # Fazer requisição de cancelamento
        try:
            headers = auth.get_headers()
            response = auth._session.delete(
                f"{auth.base_url}/jobs/{job_id}",
                headers=headers
            )

            if response.status_code == 200:
                resultado = response.json()
                return jsonify({
                    'success': True,
                    'message': f'Job {job_id} cancelado com sucesso',
                    'resultado': resultado,
                    'timestamp': datetime.now().isoformat()
                })
            elif response.status_code == 404:
                return jsonify({
                    'success': False,
                    'error': 'JOB_NAO_ENCONTRADO',
                    'message': f'Job {job_id} não encontrado'
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'error': 'ERRO_CANCELAR_JOB',
                    'message': f'Erro ao cancelar job: HTTP {response.status_code}',
                    'details': response.text
                }), 500

        except Exception as api_error:
            logger.error(f"Erro ao cancelar job {job_id}: {str(api_error)}")
            return jsonify({
                'success': False,
                'error': 'ERRO_CANCELAR_JOB',
                'message': f'Erro ao cancelar job: {str(api_error)}',
                'job_id': job_id
            }), 500

    except Exception as e:
        logger.error(f"Erro ao cancelar job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_CANCELAR_JOB',
            'message': f'Erro ao cancelar job: {str(e)}',
            'job_id': job_id
        }), 500
