"""
Rotas para APIs Externas - Sistema BEG Telecomunicações
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any

from flask import request, jsonify, current_app, Blueprint
from flask_login import login_required
from flask_wtf.csrf import generate_csrf
from apps import csrf

from apps import db
from apps.models import Processo
from .services import APIExternaService

bp = Blueprint('api_externa', __name__, url_prefix='/api/v1/external')

logger = logging.getLogger(__name__)


@bp.route('/enviar-rpa/<processo_id>', methods=['POST'])
@login_required
def enviar_para_rpa(processo_id):
    """Envia processo para RPA externo"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório'
            }), 400

        # Obter URL do endpoint
        data = request.get_json()
        url_endpoint = data.get('url_endpoint')

        if not url_endpoint:
            return jsonify({
                'success': False,
                'error': 'URL_ENDPOINT_REQUIRED',
                'message': 'URL do endpoint RPA é obrigatória'
            }), 400

        # Verificar se o processo pode ser enviado
        if processo.status_processo != "AGUARDANDO_DOWNLOAD":
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': 'Processo não está no status adequado para envio RPA'
            }), 400

        # Enviar para RPA externo
        service = APIExternaService()
        resposta = service.enviar_para_rpa_externo(processo, url_endpoint)

        if resposta.success:
            logger.info(
                f"Processo {processo_id} enviado para RPA externo com sucesso")
            return jsonify({
                'success': True,
                'message': 'Processo enviado para RPA externo com sucesso',
                'execucao_id': resposta.execucao_id,
                'resultado': resposta.resultado
            })
        else:
            logger.error(
                f"Erro ao enviar processo {processo_id} para RPA externo: {resposta.erro}")
            return jsonify({
                'success': False,
                'error': 'RPA_EXECUTION_FAILED',
                'message': f'Erro no RPA externo: {resposta.erro}'
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao enviar processo {processo_id} para RPA externo: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/enviar-sat/<processo_id>', methods=['POST'])
@login_required
def enviar_para_sat(processo_id):
    """Envia processo para SAT externo"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório'
            }), 400

        # Obter URL do endpoint
        data = request.get_json()
        url_endpoint = data.get('url_endpoint')

        if not url_endpoint:
            return jsonify({
                'success': False,
                'error': 'URL_ENDPOINT_REQUIRED',
                'message': 'URL do endpoint SAT é obrigatória'
            }), 400

        # Verificar se o processo pode ser enviado
        if processo.status_processo != "AGUARDANDO_ENVIO_SAT":
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': 'Processo não está no status adequado para envio SAT'
            }), 400

        # Enviar para SAT externo
        service = APIExternaService()
        resposta = service.enviar_para_sat_externo(processo, url_endpoint)

        if resposta.success:
            logger.info(
                f"Processo {processo_id} enviado para SAT externo com sucesso")
            return jsonify({
                'success': True,
                'message': 'Processo enviado para SAT externo com sucesso',
                'protocolo_sat': resposta.protocolo_sat
            })
        else:
            logger.error(
                f"Erro ao enviar processo {processo_id} para SAT externo: {resposta.erro}")
            return jsonify({
                'success': False,
                'error': 'SAT_EXECUTION_FAILED',
                'message': f'Erro no SAT externo: {resposta.erro}'
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao enviar processo {processo_id} para SAT externo: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/payload-rpa/<processo_id>', methods=['GET'])
@login_required
def visualizar_payload_rpa(processo_id):
    """Visualiza o payload que seria enviado para RPA"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        service = APIExternaService()
        payload = service.criar_payload_rpa(processo)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'payload': payload.to_dict(),
            'csrf_token': generate_csrf()
        })

    except Exception as e:
        logger.error(
            f"Erro ao criar payload RPA para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/payload-sat/<processo_id>', methods=['GET'])
@login_required
def visualizar_payload_sat(processo_id):
    """Visualiza o payload que seria enviado para SAT"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Usar o serviço correto da API externa
        from apps.api_externa.routes_externos import get_service
        service = get_service()
        payload = service.criar_payload_sat(processo)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'payload': payload.to_dict(),
            'csrf_token': generate_csrf()
        })

    except Exception as e:
        logger.error(
            f"Erro ao criar payload SAT para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/enviar-rpa-producao/<processo_id>', methods=['POST'])
@login_required
def enviar_para_rpa_producao(processo_id):
    """Envia processo para RPA em produção"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório'
            }), 400

        # Obter URL base da API em produção
        data = request.get_json()
        url_base = data.get('url_base', 'http://191.252.218.230:8000')

        # Verificar se o processo pode ser enviado
        if processo.status_processo != "AGUARDANDO_DOWNLOAD":
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': 'Processo não está no status adequado para envio RPA'
            }), 400

        # Enviar para RPA em produção
        service = APIExternaService()
        resposta = service.enviar_para_rpa_producao(processo, url_base)

        if resposta.success:
            logger.info(
                f"Processo {processo_id} enviado para RPA produção com sucesso")
            return jsonify({
                'success': True,
                'message': 'Processo enviado para RPA produção com sucesso',
                'resultado': resposta.data,
                'timestamp': resposta.timestamp
            })
        else:
            logger.error(
                f"Erro ao enviar processo {processo_id} para RPA produção: {resposta.error}")
            return jsonify({
                'success': False,
                'error': 'RPA_PRODUCAO_FAILED',
                'message': f'Erro no RPA produção: {resposta.message}'
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao enviar processo {processo_id} para RPA produção: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/enviar-sat-producao/<processo_id>', methods=['POST'])
@login_required
def enviar_para_sat_producao(processo_id):
    """Envia processo para SAT em produção"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        # Verificar CSRF token
        csrf_token = request.headers.get(
            'X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({
                'success': False,
                'error': 'CSRF_TOKEN_MISSING',
                'message': 'Token CSRF é obrigatório'
            }), 400

        # Obter URL base da API em produção
        data = request.get_json()
        url_base = data.get('url_base', 'http://191.252.218.230:8000')

        # Verificar se o processo pode ser enviado
        if processo.status_processo != "AGUARDANDO_ENVIO_SAT":
            return jsonify({
                'success': False,
                'error': 'INVALID_PROCESS_STATUS',
                'message': 'Processo não está no status adequado para envio SAT'
            }), 400

        # Enviar para SAT em produção
        service = APIExternaService()
        resposta = service.enviar_para_sat_producao(processo, url_base)

        if resposta.success:
            logger.info(
                f"Processo {processo_id} enviado para SAT produção com sucesso")
            return jsonify({
                'success': True,
                'message': 'Processo enviado para SAT produção com sucesso',
                'resultado': resposta.data,
                'timestamp': resposta.timestamp
            })
        else:
            logger.error(
                f"Erro ao enviar processo {processo_id} para SAT produção: {resposta.error}")
            return jsonify({
                'success': False,
                'error': 'SAT_PRODUCAO_FAILED',
                'message': f'Erro no SAT produção: {resposta.message}'
            }), 500

    except Exception as e:
        logger.error(
            f"Erro ao enviar processo {processo_id} para SAT produção: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/payload-rpa-producao/<processo_id>', methods=['GET'])
@login_required
def visualizar_payload_rpa_producao(processo_id):
    """Visualiza o payload que seria enviado para RPA em produção"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        service = APIExternaService()
        payload = service.criar_payload_rpa_producao(processo)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'payload': payload.to_dict(),
            'endpoint': f"/executar/{processo.cliente.operadora.codigo.lower() if processo.cliente.operadora else 'unknown'}",
            'csrf_token': generate_csrf()
        })

    except Exception as e:
        logger.error(
            f"Erro ao criar payload RPA produção para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/payload-sat-producao/<processo_id>', methods=['GET'])
@login_required
def visualizar_payload_sat_producao(processo_id):
    """Visualiza o payload que seria enviado para SAT em produção"""
    try:
        processo = Processo.query.get_or_404(processo_id)

        service = APIExternaService()
        payload = service.criar_payload_sat_producao(processo)

        return jsonify({
            'success': True,
            'processo_id': processo_id,
            'payload': payload.to_dict(),
            'endpoint': "/executar/sat",
            'csrf_token': generate_csrf()
        })

    except Exception as e:
        logger.error(
            f"Erro ao criar payload SAT produção para processo {processo_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/teste-conexao-producao', methods=['POST'])
@login_required
def teste_conexao_producao():
    """Testa conexão com a API em produção"""
    try:
        data = request.get_json()
        url_base = data.get('url_base', 'http://191.252.218.230:8000')

        # Testar health check
        try:
            response = requests.get(f"{url_base}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                return jsonify({
                    'success': True,
                    'message': 'Conexão com API em produção OK',
                    'health_status': health_data,
                    'url_base': url_base
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'HEALTH_CHECK_FAILED',
                    'message': f'Health check falhou: {response.status_code}',
                    'url_base': url_base
                }), 500

        except requests.exceptions.RequestException as e:
            return jsonify({
                'success': False,
                'error': 'CONNECTION_FAILED',
                'message': f'Erro de conexão: {str(e)}',
                'url_base': url_base
            }), 500

    except Exception as e:
        logger.error(f"Erro no teste de conexão produção: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': f'Erro interno: {str(e)}'
        }), 500


# =============================================================================
# ENDPOINTS DUMMY PARA SIMULAÇÃO
# =============================================================================

@bp.route('/dummy/rpa/executar-download', methods=['POST'])
@csrf.exempt
def dummy_rpa_download():
    """Endpoint dummy para simular RPA de download"""
    try:
        data = request.get_json()
        processo_id = data.get('processo_id')
        operadora = data.get('operadora', {})

        # Simular processamento
        logger.info(
            f"[DUMMY RPA] Iniciando download para processo {processo_id}")
        time.sleep(2)  # Simular tempo de processamento

        # Gerar dados simulados baseados na operadora
        codigo_operadora = operadora.get('codigo', 'UNK')
        valores_simulados = {
            'EMB': 1250.50,
            'VIV': 890.75,
            'OII': 1560.25,
            'DIG': 720.30
        }

        valor_fatura = valores_simulados.get(codigo_operadora, 1000.00)
        execucao_id = str(uuid.uuid4())

        resposta = {
            "success": True,
            "processo_id": processo_id,
            "execucao_id": execucao_id,
            "status": "CONCLUIDO",
            "mensagem": f"Download {codigo_operadora} realizado com sucesso",
            "resultado": {
                "arquivo_baixado": f"fatura_{codigo_operadora.lower()}_{data.get('processo', {}).get('mes_ano', '').replace('/', '_')}.pdf",
                "url_arquivo": f"https://minio.local/tirus-faturas/fatura_{codigo_operadora.lower()}.pdf",
                "dados_extraidos": {
                    "valor_fatura": valor_fatura,
                    "data_vencimento": f"2025-{int(data.get('processo', {}).get('mes_ano', '07/2025').split('/')[0]) + 1:02d}-15",
                    "numero_fatura": f"FAT-2025-{codigo_operadora}-001",
                    "mes_referencia": data.get('processo', {}).get('mes_ano', '07/2025')
                },
                "tempo_execucao_segundos": 120.5,
                "logs_execucao": [
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando login no portal {operadora.get('nome', 'Operadora')}",
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Login realizado com sucesso",
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Navegando para área de faturas",
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Fatura localizada",
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Download concluído"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"[DUMMY RPA] Download concluído para processo {processo_id}")
        return jsonify(resposta)

    except Exception as e:
        logger.error(f"[DUMMY RPA] Erro no download: {str(e)}")
        return jsonify({
            "success": False,
            "processo_id": data.get('processo_id', ''),
            "erro": f"Erro no RPA dummy: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@bp.route('/dummy/sat/upload-fatura', methods=['POST'])
@csrf.exempt
def dummy_sat_upload():
    """Endpoint dummy para simular upload no SAT"""
    try:
        data = request.get_json()
        processo_id = data.get('processo_id')

        # Simular processamento
        logger.info(
            f"[DUMMY SAT] Iniciando upload para processo {processo_id}")
        time.sleep(1.5)  # Simular tempo de processamento

        protocolo_sat = f"SAT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        resposta = {
            "success": True,
            "processo_id": processo_id,
            "protocolo_sat": protocolo_sat,
            "mensagem": "Upload realizado com sucesso no sistema SAT",
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"[DUMMY SAT] Upload concluído para processo {processo_id} - Protocolo: {protocolo_sat}")
        return jsonify(resposta)

    except Exception as e:
        logger.error(f"[DUMMY SAT] Erro no upload: {str(e)}")
        return jsonify({
            "success": False,
            "processo_id": data.get('processo_id', ''),
            "erro": f"Erro no SAT dummy: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@bp.route('/dummy/rpa/teste-conexao', methods=['POST'])
@csrf.exempt
def dummy_rpa_teste_conexao():
    """Endpoint dummy para testar conexão RPA"""
    try:
        data = request.get_json()
        operadora = data.get('operadora', {})

        # Simular teste de conexão
        time.sleep(1)

        resposta = {
            "success": True,
            "operadora": operadora.get('codigo', 'UNK'),
            "status_conexao": "OK",
            "mensagem": f"Conexão com portal {operadora.get('nome', 'Operadora')} OK",
            "tempo_resposta_ms": 1200,
            "timestamp": datetime.now().isoformat()
        }

        return jsonify(resposta)

    except Exception as e:
        return jsonify({
            "success": False,
            "erro": f"Erro no teste de conexão: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@bp.route('/dummy/sat/teste-conexao', methods=['POST'])
@csrf.exempt
def dummy_sat_teste_conexao():
    """Endpoint dummy para testar conexão SAT"""
    try:
        # Simular teste de conexão
        time.sleep(0.5)

        resposta = {
            "success": True,
            "status_conexao": "OK",
            "mensagem": "Conexão com sistema SAT OK",
            "versao_api": "1.0.0",
            "tempo_resposta_ms": 800,
            "timestamp": datetime.now().isoformat()
        }

        return jsonify(resposta)

    except Exception as e:
        return jsonify({
            "success": False,
            "erro": f"Erro no teste de conexão SAT: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@bp.route('/dummy/status', methods=['GET'])
def dummy_status():
    """Status dos serviços dummy"""
    return jsonify({
        "success": True,
        "servicos": {
            "rpa_download": "ONLINE",
            "sat_upload": "ONLINE",
            "teste_conexao": "ONLINE"
        },
        "endpoints_disponiveis": [
            "POST /api/v1/external/dummy/rpa/executar-download",
            "POST /api/v1/external/dummy/sat/upload-fatura",
            "POST /api/v1/external/dummy/rpa/teste-conexao",
            "POST /api/v1/external/dummy/sat/teste-conexao"
        ],
        "timestamp": datetime.now().isoformat()
    })
