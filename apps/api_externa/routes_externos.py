"""
Rotas para API externa funcional
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from flask import request, jsonify, current_app, Blueprint
from flask_login import login_required
from flask_wtf.csrf import generate_csrf
from apps import csrf

from apps import db
from apps.models import Processo
from .services_externos import APIExternaFuncionalService

bp_externos = Blueprint('api_externos', __name__,
                        url_prefix='/api/v2/externos')

logger = logging.getLogger(__name__)

# Instância global do serviço
_service_instance: Optional[APIExternaFuncionalService] = None


def get_service() -> APIExternaFuncionalService:
    """Obtém instância global do serviço"""
    global _service_instance

    if _service_instance is None:
        _service_instance = APIExternaFuncionalService()

    return _service_instance


@bp_externos.route('/executar/<processo_id>', methods=['POST'])
@login_required
def executar_processo(processo_id):
    """Executa processo usando API externa funcional"""
    try:
        processo = Processo.query.get_or_404(processo_id)
        service = get_service()

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório. Use o endpoint /executar-sem-csrf/{processo_id} para testes sem CSRF.',
                'csrf_required': True
            }), 400

        # Obter parâmetros
        data = request.get_json() or {}
        tipo_execucao = data.get('tipo', 'rpa')  # 'rpa' ou 'sat'
        sincrono = data.get('sincrono', False)

        # Verificar se o processo pode ser executado
        if processo.status_processo not in ["AGUARDANDO_DOWNLOAD", "DOWNLOAD_CONCLUIDO"]:
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': f'Processo não está no status adequado: {processo.status_processo}',
                'status_atual': processo.status_processo,
                'status_aceitos': ["AGUARDANDO_DOWNLOAD", "DOWNLOAD_CONCLUIDO"]
            }), 400

        # Executar baseado no tipo
        if tipo_execucao == 'sat':
            if processo.status_processo != "DOWNLOAD_CONCLUIDO":
                return jsonify({
                    'success': False,
                    'error': 'DOWNLOAD_REQUIRED',
                    'message': 'Download deve ser concluído antes do SAT',
                    'status_atual': processo.status_processo,
                    'status_requerido': "DOWNLOAD_CONCLUIDO"
                }), 400

            resultado = service.executar_sat_externo(processo, sincrono)
        else:
            resultado = service.executar_rpa_externo(processo, sincrono)

        # Preparar resposta
        if sincrono:
            # Execução síncrona - resultado direto
            return jsonify({
                'success': True,
                'message': f'Execução {tipo_execucao} concluída com sucesso',
                'tipo': tipo_execucao,
                'sincrono': True,
                'resultado': resultado
            })
        else:
            # Execução assíncrona - job criado
            return jsonify({
                'success': True,
                'message': f'Job {tipo_execucao} criado com sucesso',
                'tipo': tipo_execucao,
                'sincrono': False,
                'job_id': resultado.job_id,
                'status': resultado.status,
                'status_url': f'/api/v2/externos/status/{resultado.job_id}'
            })

    except ValueError as e:
        logger.error(
            f"Erro de validação para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Erro ao executar processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'EXECUTION_ERROR',
            'message': f'Erro na execução: {str(e)}'
        }), 500


@bp_externos.route('/executar-sem-csrf/<processo_id>', methods=['POST'])
@login_required
def executar_processo_sem_csrf(processo_id):
    """Executa processo usando API externa funcional SEM validação CSRF (para testes)"""
    try:
        processo = Processo.query.get_or_404(processo_id)
        service = get_service()

        # Obter parâmetros
        data = request.get_json() or {}
        tipo_execucao = data.get('tipo', 'rpa')  # 'rpa' ou 'sat'
        sincrono = data.get('sincrono', False)

        # Verificar se o processo pode ser executado
        if processo.status_processo not in ["AGUARDANDO_DOWNLOAD", "DOWNLOAD_CONCLUIDO"]:
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': f'Processo não está no status adequado: {processo.status_processo}',
                'status_atual': processo.status_processo,
                'status_aceitos': ["AGUARDANDO_DOWNLOAD", "DOWNLOAD_CONCLUIDO"]
            }), 400

        # Executar baseado no tipo
        if tipo_execucao == 'sat':
            if processo.status_processo != "DOWNLOAD_CONCLUIDO":
                return jsonify({
                    'success': False,
                    'error': 'DOWNLOAD_REQUIRED',
                    'message': 'Download deve ser concluído antes do SAT',
                    'status_atual': processo.status_processo,
                    'status_requerido': "DOWNLOAD_CONCLUIDO"
                }), 400

            resultado = service.executar_sat_externo(processo, sincrono)
        else:
            resultado = service.executar_rpa_externo(processo, sincrono)

        # Preparar resposta
        if sincrono:
            # Execução síncrona - resultado direto
            return jsonify({
                'success': True,
                'message': f'Execução {tipo_execucao} concluída com sucesso (sem CSRF)',
                'tipo': tipo_execucao,
                'sincrono': True,
                'resultado': resultado,
                'csrf_disabled': True
            })
        else:
            # Execução assíncrona - job criado
            return jsonify({
                'success': True,
                'message': f'Job {tipo_execucao} criado com sucesso (sem CSRF)',
                'tipo': tipo_execucao,
                'sincrono': False,
                'job_id': resultado.job_id,
                'status': resultado.status,
                'status_url': f'/api/v2/externos/status/{resultado.job_id}',
                'csrf_disabled': True
            })

    except ValueError as e:
        logger.error(
            f"Erro de validação para processo {processo_id} (sem CSRF): {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(
            f"Erro ao executar processo {processo_id} (sem CSRF): {str(e)}")
        return jsonify({
            'success': False,
            'error': 'EXECUTION_ERROR',
            'message': f'Erro na execução: {str(e)}'
        }), 500


@bp_externos.route('/status/<job_id>', methods=['GET'])
@login_required
def consultar_status_job(job_id):
    """Consulta status de um job"""
    try:
        service = get_service()
        processo_id = request.args.get('processo_id', '')

        status = service.consultar_status_job(job_id, processo_id)

        if not status:
            return jsonify({
                'success': False,
                'error': 'JOB_NOT_FOUND',
                'message': f'Job {job_id} não encontrado'
            }), 404

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': status.to_dict()
        })

    except Exception as e:
        logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'STATUS_ERROR',
            'message': f'Erro ao consultar status: {str(e)}'
        }), 500


@bp_externos.route('/monitorar/<job_id>', methods=['POST'])
@login_required
def monitorar_job(job_id):
    """Monitora um job até conclusão"""
    try:
        service = get_service()
        data = request.get_json() or {}

        processo_id = data.get('processo_id', '')
        max_wait = data.get('max_wait', 300)
        poll_interval = data.get('poll_interval', 5)

        status = service.monitorar_job(
            job_id=job_id,
            processo_id=processo_id,
            max_wait=max_wait,
            poll_interval=poll_interval
        )

        if not status:
            return jsonify({
                'success': False,
                'error': 'MONITORING_ERROR',
                'message': f'Erro ao monitorar job {job_id}'
            }), 500

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': status.to_dict(),
            'concluido': status.status in ['COMPLETED', 'FAILED']
        })

    except Exception as e:
        logger.error(f"Erro ao monitorar job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'MONITORING_ERROR',
            'message': f'Erro ao monitorar: {str(e)}'
        }), 500


@bp_externos.route('/cancelar/<job_id>', methods=['DELETE'])
@login_required
def cancelar_job(job_id):
    """Cancela um job em execução"""
    try:
        service = get_service()
        processo_id = request.args.get('processo_id', '')

        sucesso = service.cancelar_job(job_id, processo_id)

        if sucesso:
            return jsonify({
                'success': True,
                'message': f'Job {job_id} cancelado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'CANCEL_ERROR',
                'message': f'Erro ao cancelar job {job_id}'
            }), 500

    except Exception as e:
        logger.error(f"Erro ao cancelar job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'CANCEL_ERROR',
            'message': f'Erro ao cancelar: {str(e)}'
        }), 500


@bp_externos.route('/logs/<job_id>', methods=['GET'])
@login_required
def obter_logs_job(job_id):
    """Obtém logs detalhados de um job"""
    try:
        service = get_service()
        logs = service.obter_logs_job(job_id)

        return jsonify({
            'success': True,
            'job_id': job_id,
            'logs': logs,
            'total': len(logs)
        })

    except Exception as e:
        logger.error(f"Erro ao obter logs do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'LOGS_ERROR',
            'message': f'Erro ao obter logs: {str(e)}'
        }), 500


@bp_externos.route('/processo/<processo_id>/jobs', methods=['GET'])
@login_required
def listar_jobs_processo(processo_id):
    """Lista todos os jobs de um processo"""
    try:
        service = get_service()
        jobs = service.listar_jobs_processo(processo_id)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'jobs': [job.to_dict() for job in jobs],
            'total': len(jobs)
        })

    except Exception as e:
        logger.error(
            f"Erro ao listar jobs do processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'JOBS_ERROR',
            'message': f'Erro ao listar jobs: {str(e)}'
        }), 500


@bp_externos.route('/payload/<processo_id>', methods=['GET'])
@login_required
def visualizar_payload(processo_id):
    """Visualiza payload que seria enviado para um processo"""
    try:
        processo = Processo.query.get_or_404(processo_id)
        service = get_service()

        tipo = request.args.get('tipo', 'rpa')

        if tipo == 'sat':
            payload = service.criar_payload_sat(processo)
        else:
            payload = service.criar_payload_operadora(processo)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'tipo': tipo,
            'payload': payload.to_dict(),
            'operadora': processo.cliente.operadora.codigo if processo.cliente.operadora else None
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'PAYLOAD_ERROR',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(
            f"Erro ao gerar payload para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'PAYLOAD_ERROR',
            'message': f'Erro ao gerar payload: {str(e)}'
        }), 500


@bp_externos.route('/estatisticas', methods=['GET'])
@login_required
def obter_estatisticas():
    """Obtém estatísticas do serviço"""
    try:
        service = get_service()
        stats = service.obter_estatisticas()

        return jsonify({
            'success': True,
            'estatisticas': stats
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'STATS_ERROR',
            'message': f'Erro ao obter estatísticas: {str(e)}'
        }), 500


@bp_externos.route('/cache/limpar', methods=['POST'])
@login_required
def limpar_cache():
    """Limpa itens expirados do cache"""
    try:
        service = get_service()
        removidos = service.limpar_cache()

        return jsonify({
            'success': True,
            'message': f'Cache limpo: {removidos} itens removidos',
            'itens_removidos': removidos
        })

    except Exception as e:
        logger.error(f"Erro ao limpar cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'CACHE_ERROR',
            'message': f'Erro ao limpar cache: {str(e)}'
        }), 500


@bp_externos.route('/health', methods=['GET'])
def health_check():
    """Verifica saúde do serviço"""
    try:
        from .auth import test_api_externa_connection
        resultado = test_api_externa_connection()

        return jsonify({
            'success': resultado.get('success', False),
            'api_externa': resultado,
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy' if resultado.get('success') else 'unhealthy'
        })

    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'HEALTH_ERROR',
            'message': str(e),
            'status': 'unhealthy'
        }), 500


@bp_externos.route('/teste/<processo_id>', methods=['POST'])
@login_required
def teste_execucao(processo_id):
    """Testa execução sem alterar status do processo"""
    try:
        processo = Processo.query.get_or_404(processo_id)
        service = get_service()

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório'
            }), 400

        # Obter parâmetros
        data = request.get_json() or {}
        tipo_execucao = data.get('tipo', 'rpa')

        # Criar payload apenas (sem executar)
        if tipo_execucao == 'sat':
            payload = service.criar_payload_sat(processo)
        else:
            payload = service.criar_payload_operadora(processo)

        return jsonify({
            'success': True,
            'message': 'Teste de payload realizado com sucesso',
            'processo_id': processo_id,
            'tipo': tipo_execucao,
            'payload': payload.to_dict(),
            'operadora': processo.cliente.operadora.codigo if processo.cliente.operadora else None
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'TEST_ERROR',
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Erro no teste para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'TEST_ERROR',
            'message': f'Erro no teste: {str(e)}'
        }), 500


@bp_externos.route('/jobs/ativos', methods=['GET'])
@login_required
def listar_jobs_ativos():
    """Lista jobs ativos para o dashboard"""
    try:
        service = get_service()

        # Obter jobs ativos do monitor
        jobs_ativos = service.monitor.get_active_jobs()

        # Formatar dados para o frontend
        jobs_formatados = []
        for job_id, job_info in jobs_ativos.items():
            status = service.consultar_status_job(
                job_id, job_info.get('processo_id', ''))

            if status:
                jobs_formatados.append({
                    'job_id': job_id,
                    'processo_id': job_info.get('processo_id', ''),
                    'operadora': status.operadora,
                    'tipo': 'RPA' if status.operadora != 'SAT' else 'SAT',
                    'status': status.status,
                    'progress': status.progress,
                    'created_at': status.created_at,
                    'started_at': status.started_at,
                    'duration': _calcular_duracao(status.created_at, status.started_at)
                })

        return jsonify({
            'success': True,
            'jobs': jobs_formatados,
            'total': len(jobs_formatados)
        })

    except Exception as e:
        logger.error(f"Erro ao listar jobs ativos: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'JOBS_ATIVOS_ERROR',
            'message': f'Erro ao listar jobs ativos: {str(e)}'
        }), 500


@bp_externos.route('/jobs/historico', methods=['GET'])
@login_required
def listar_historico_jobs():
    """Lista histórico de jobs para o dashboard"""
    try:
        service = get_service()

        # Obter jobs recentes do cache
        jobs_recentes = service.cache.get_recent_jobs(limit=50)

        # Formatar dados para o frontend
        jobs_formatados = []
        for job_status in jobs_recentes:
            jobs_formatados.append({
                'job_id': job_status.job_id,
                'operadora': job_status.operadora,
                'tipo': 'RPA' if job_status.operadora != 'SAT' else 'SAT',
                'status': job_status.status,
                'progress': job_status.progress,
                'created_at': job_status.created_at,
                'started_at': job_status.started_at,
                'completed_at': job_status.completed_at,
                'error': job_status.error,
                'result': job_status.result
            })

        return jsonify({
            'success': True,
            'jobs': jobs_formatados,
            'total': len(jobs_formatados)
        })

    except Exception as e:
        logger.error(f"Erro ao listar histórico de jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'HISTORICO_ERROR',
            'message': f'Erro ao listar histórico: {str(e)}'
        }), 500


@bp_externos.route('/atualizar-status/<job_id>', methods=['POST'])
@login_required
def atualizar_status_processo_automatico(job_id):
    """
    Atualiza automaticamente o status do processo baseado no resultado do job
    """
    try:
        data = request.get_json() or {}
        processo_id = data.get('processo_id')

        if not processo_id:
            return jsonify({
                'success': False,
                'error': 'PROCESSO_ID_REQUERIDO',
                'message': 'ID do processo é obrigatório'
            }), 400

        service = get_service()
        sucesso = service.atualizar_status_processo_automatico(
            job_id, processo_id)

        if sucesso:
            return jsonify({
                'success': True,
                'message': 'Status do processo atualizado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'FALHA_ATUALIZACAO',
                'message': 'Falha ao atualizar status do processo'
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao atualizar status do processo automaticamente: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ERRO_ATUALIZAR_STATUS',
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500


@bp_externos.route('/estatisticas/operadoras', methods=['GET'])
@login_required
def estatisticas_operadoras():
    """Obtém estatísticas por operadora"""
    try:
        service = get_service()

        # Obter jobs recentes
        jobs_recentes = service.cache.get_recent_jobs(limit=100)

        # Contar por operadora
        contadores = {
            'oi': 0,
            'vivo': 0,
            'embratel': 0,
            'digitalnet': 0,
            'sat': 0
        }

        for job in jobs_recentes:
            operadora = job.operadora.lower()
            if operadora in contadores:
                contadores[operadora] += 1

        return jsonify({
            'success': True,
            'estatisticas': contadores
        })

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas por operadora: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'STATS_OPERADORAS_ERROR',
            'message': f'Erro ao obter estatísticas: {str(e)}'
        }), 500


def _calcular_duracao(created_at, started_at):
    """Calcula duração em segundos"""
    try:
        if not created_at or not started_at:
            return 0

        from datetime import datetime
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))

        return int((started - created).total_seconds())
    except:
        return 0


@bp_externos.route('/jobs', methods=['GET'])
@login_required
def list_jobs():
    """Lista todos os jobs da API externa"""
    try:
        from .auth import list_api_externa_jobs
        resultado = list_api_externa_jobs()
        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao listar jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao listar jobs'
        }), 500


@bp_externos.route('/status/<job_id>', methods=['GET'])
@login_required
def get_job_status(job_id):
    """Obtém o status de um job específico"""
    try:
        from .auth import get_api_externa_job_status
        resultado = get_api_externa_job_status(job_id)
        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao obter status do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao obter status do job'
        }), 500


@bp_externos.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Dashboard da API externa"""
    from flask import render_template
    return render_template('processos/dashboard_api_externa.html')


@bp_externos.route('/processar-resultado/<job_id>', methods=['POST'])
@login_required
def processar_resultado_job(job_id):
    """Processa o resultado de um job concluído"""
    try:
        from flask import request
        service = get_service()

        data = request.get_json() or {}
        processo_id = data.get('processo_id')
        resultado = data.get('resultado', {})

        if not processo_id:
            return jsonify({
                'success': False,
                'error': 'MISSING_PROCESSO_ID',
                'message': 'ID do processo é obrigatório'
            }), 400

        # Processar resultado
        sucesso = service.processar_resultado_job(
            job_id, processo_id, resultado)

        if sucesso:
            return jsonify({
                'success': True,
                'message': f'Resultado do job {job_id} processado com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'PROCESSING_ERROR',
                'message': f'Erro ao processar resultado do job {job_id}'
            }), 500

    except Exception as e:
        logger.error(f"Erro ao processar resultado do job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'PROCESSING_ERROR',
            'message': f'Erro ao processar resultado: {str(e)}'
        }), 500


@bp_externos.route('/processo/<processo_id>/executar-download', methods=['POST'])
@login_required
def executar_download_rpa(processo_id):
    """Executa download RPA para um processo específico"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar se o processo pode fazer download
        if not processo.pode_fazer_download:
            return jsonify({
                'success': False,
                'error': 'INVALID_STATUS',
                'message': 'Processo não pode fazer download no status atual'
            }), 400

        service = get_service()

        # Executar download via API externa
        resultado = service.executar_download_processo(processo_id)

        if resultado.get('success'):
            return jsonify({
                'success': True,
                'message': 'Download RPA iniciado com sucesso',
                'job_id': resultado.get('job_id'),
                'processo_id': processo_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'DOWNLOAD_ERROR',
                'message': resultado.get('message', 'Erro ao iniciar download RPA')
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao executar download RPA para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'EXECUTION_ERROR',
            'message': f'Erro ao executar download: {str(e)}'
        }), 500


@bp_externos.route('/processo/<processo_id>/executar-rpa-terceirizado', methods=['POST'])
@login_required
def executar_rpa_terceirizado(processo_id):
    """Executa RPA terceirizado para um processo específico"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar se o processo pode fazer download
        if not processo.pode_fazer_download:
            return jsonify({
                'success': False,
                'error': 'INVALID_STATUS',
                'message': 'Processo não pode fazer download no status atual'
            }), 400

        service = get_service()

        # Executar RPA terceirizado via API externa
        resultado = service.executar_rpa_terceirizado_processo(processo_id)

        if resultado.get('success'):
            return jsonify({
                'success': True,
                'message': 'RPA terceirizado iniciado com sucesso',
                'job_id': resultado.get('job_id'),
                'processo_id': processo_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'RPA_ERROR',
                'message': resultado.get('message', 'Erro ao iniciar RPA terceirizado')
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao executar RPA terceirizado para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'EXECUTION_ERROR',
            'message': f'Erro ao executar RPA terceirizado: {str(e)}'
        }), 500


@bp_externos.route('/processo/<processo_id>/executar-sat-terceirizado', methods=['POST'])
@login_required
def executar_sat_terceirizado(processo_id):
    """Executa SAT terceirizado para um processo específico"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar se o processo pode ser enviado para SAT
        if not processo.pode_enviar_sat:
            return jsonify({
                'success': False,
                'error': 'INVALID_STATUS',
                'message': 'Processo não pode ser enviado para SAT no status atual'
            }), 400

        service = get_service()

        # Executar SAT terceirizado via API externa
        resultado = service.executar_sat_terceirizado_processo(processo_id)

        if resultado.get('success'):
            return jsonify({
                'success': True,
                'message': 'SAT terceirizado iniciado com sucesso',
                'job_id': resultado.get('job_id'),
                'processo_id': processo_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'SAT_ERROR',
                'message': resultado.get('message', 'Erro ao iniciar SAT terceirizado')
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao executar SAT terceirizado para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'EXECUTION_ERROR',
            'message': f'Erro ao executar SAT terceirizado: {str(e)}'
        }), 500
