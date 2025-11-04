"""
Rotas do módulo RPA - Sistema de Orquestração RPA BEG Telecomunicações
"""

from apps import db
from apps.authentication.util import verify_user_jwt
from apps.models.execucao import TipoExecucao, StatusExecucao
from apps.models import Processo, Execucao, Operadora
from .base import ServicoRPA, TipoOperacao, StatusExecucaoRPA
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint
bp = Blueprint('rpa', __name__, url_prefix='/api/v1/rpa')


logger = logging.getLogger(__name__)


@bp.route('/executar-download', methods=['POST'])
@verify_user_jwt
def executar_download():
    """
    Endpoint para executar download de fatura via RPA

    Payload esperado:
    {
        "processo_id": "uuid-do-processo",
        "usuario_id": "uuid-do-usuario" (opcional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Dados JSON são obrigatórios'
            }), 400

        processo_id = data.get('processo_id')
        usuario_id = data.get('usuario_id')

        if not processo_id:
            return jsonify({
                'success': False,
                'message': 'processo_id é obrigatório'
            }), 400

        # Executa download
        servico_rpa = ServicoRPA()
        resultado = servico_rpa.executar_download_processo(
            processo_id, usuario_id)

        if resultado['success']:
            logger.info(
                "Download executado com sucesso para processo %s", processo_id)
            return jsonify(resultado)
        else:
            logger.error("Erro no download do processo %s: %s",
                         processo_id, resultado['message'])
            return jsonify(resultado), 400

    except Exception as e:
        logger.error("Erro interno ao executar download: %s", str(e))
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/executar-upload-sat', methods=['POST'])
@verify_user_jwt
def executar_upload_sat():
    """
    Endpoint para executar upload de fatura para SAT via RPA

    Payload esperado:
    {
        "processo_id": "uuid-do-processo",
        "usuario_id": "uuid-do-usuario" (opcional)
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Dados JSON são obrigatórios'
            }), 400

        processo_id = data.get('processo_id')
        usuario_id = data.get('usuario_id')

        if not processo_id:
            return jsonify({
                'success': False,
                'message': 'processo_id é obrigatório'
            }), 400

        # Executa upload SAT
        servico_rpa = ServicoRPA()
        resultado = servico_rpa.executar_upload_sat_processo(
            processo_id, usuario_id)

        if resultado['success']:
            logger.info(
                "Upload SAT executado com sucesso para processo %s", processo_id)
            return jsonify(resultado)
        else:
            logger.error("Erro no upload SAT do processo %s: %s",
                         processo_id, resultado['message'])
            return jsonify(resultado), 400

    except Exception as e:
        logger.error("Erro interno ao executar upload SAT: %s", str(e))
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500


@bp.route('/status-execucao/<execucao_id>', methods=['GET'])
@verify_user_jwt
def status_execucao(execucao_id):
    """
    Consulta status de uma execução específica

    Args:
        execucao_id: ID da execução
    """
    try:
        execucao = Execucao.query.get_or_404(execucao_id)

        # Calcula duração se finalizada
        duracao = None
        if execucao.data_fim:
            duracao = (execucao.data_fim -
                       execucao.data_inicio).total_seconds()

        return jsonify({
            'success': True,
            'execucao': {
                'id': str(execucao.id),
                'processo_id': str(execucao.processo_id),
                'tipo_execucao': execucao.tipo_execucao,
                'status_execucao': execucao.status_execucao,
                'classe_rpa_utilizada': execucao.classe_rpa_utilizada,
                'data_inicio': execucao.data_inicio.isoformat() if execucao.data_inicio else None,
                'data_fim': execucao.data_fim.isoformat() if execucao.data_fim else None,
                'duracao_segundos': duracao,
                'numero_tentativa': execucao.numero_tentativa,
                'mensagem_log': execucao.mensagem_log,
                'url_arquivo_s3': execucao.url_arquivo_s3,
                'resultado_saida': execucao.resultado_saida,
                'parametros_entrada': execucao.parametros_entrada
            }
        })

    except Exception as e:
        logger.error("Erro ao consultar status da execução %s: %s",
                     execucao_id, str(e))
        return jsonify({
            'success': False,
            'message': f'Erro ao consultar execução: {str(e)}'
        }), 500


@bp.route('/processos-pendentes', methods=['GET'])
@verify_user_jwt
def processos_pendentes():
    """
    Lista processos que podem ser executados

    Query params:
        - operadora_id: Filtrar por operadora
        - status: Filtrar por status
        - limit: Limite de resultados
    """
    try:
        operadora_id = request.args.get('operadora_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)

        # Query base
        query = Processo.query.filter(
            Processo.status_processo == 'AGUARDANDO_DOWNLOAD'
        ).join(Processo.cliente).join(Operadora)

        # Aplicar filtros
        if operadora_id:
            query = query.filter(Operadora.id == operadora_id)

        if status:
            query = query.filter(Processo.status_processo == status)

        # Ordenar e limitar
        processos = query.order_by(
            Processo.data_criacao.desc()).limit(limit).all()

        # Formatar resultado
        processos_data = []
        for processo in processos:
            processos_data.append({
                'id': str(processo.id),
                'mes_ano': processo.mes_ano,
                'status_processo': processo.status_processo,
                'cliente': {
                    'id': str(processo.cliente.id),
                    'razao_social': processo.cliente.razao_social,
                    'cnpj': processo.cliente.cnpj
                },
                'operadora': {
                    'id': str(processo.cliente.operadora.id),
                    'nome': processo.cliente.operadora.nome,
                    'codigo': processo.cliente.operadora.codigo
                },
                'data_criacao': processo.data_criacao.isoformat() if processo.data_criacao else None
            })

        return jsonify({
            'success': True,
            'processos': processos_data,
            'total': len(processos_data)
        })

    except Exception as e:
        logger.error("Erro ao listar processos pendentes: %s", str(e))
        return jsonify({
            'success': False,
            'message': f'Erro ao listar processos: {str(e)}'
        }), 500


@bp.route('/relatorio-execucoes', methods=['GET'])
@verify_user_jwt
def relatorio_execucoes():
    """
    Relatório de execuções com estatísticas

    Query params:
        - data_inicio: Data de início (YYYY-MM-DD)
        - data_fim: Data de fim (YYYY-MM-DD)
        - operadora_id: Filtrar por operadora
        - tipo_execucao: Filtrar por tipo
    """
    try:
        from datetime import datetime, timedelta

        # Parâmetros de filtro
        data_inicio_str = request.args.get('data_inicio')
        data_fim_str = request.args.get('data_fim')
        operadora_id = request.args.get('operadora_id')
        tipo_execucao = request.args.get('tipo_execucao')

        # Query base
        query = Execucao.query.join(Execucao.processo).join(
            Processo.cliente).join(Operadora)

        # Aplicar filtros de data
        if data_inicio_str:
            try:
                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
                query = query.filter(Execucao.data_inicio >= data_inicio)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de data_inicio inválido. Use YYYY-MM-DD'
                }), 400

        if data_fim_str:
            try:
                data_fim = datetime.strptime(
                    data_fim_str, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Execucao.data_inicio < data_fim)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de data_fim inválido. Use YYYY-MM-DD'
                }), 400

        # Aplicar outros filtros
        if operadora_id:
            query = query.filter(Operadora.id == operadora_id)

        if tipo_execucao:
            query = query.filter(Execucao.tipo_execucao == tipo_execucao)

        # Executar query
        execucoes = query.all()

        # Calcular estatísticas
        total_execucoes = len(execucoes)
        sucessos = sum(1 for e in execucoes if e.status_execucao ==
                       StatusExecucao.CONCLUIDO.value)
        falhas = sum(1 for e in execucoes if e.status_execucao ==
                     StatusExecucao.FALHOU.value)
        em_andamento = sum(1 for e in execucoes if e.esta_em_andamento)

        # Estatísticas por operadora
        stats_por_operadora = {}
        for execucao in execucoes:
            operadora_nome = execucao.processo.cliente.operadora.nome
            if operadora_nome not in stats_por_operadora:
                stats_por_operadora[operadora_nome] = {
                    'total': 0,
                    'sucessos': 0,
                    'falhas': 0
                }

            stats_por_operadora[operadora_nome]['total'] += 1
            if execucao.status_execucao == StatusExecucao.CONCLUIDO.value:
                stats_por_operadora[operadora_nome]['sucessos'] += 1
            elif execucao.status_execucao == StatusExecucao.FALHOU.value:
                stats_por_operadora[operadora_nome]['falhas'] += 1

        return jsonify({
            'success': True,
            'relatorio': {
                'periodo': {
                    'data_inicio': data_inicio_str,
                    'data_fim': data_fim_str
                },
                'estatisticas_gerais': {
                    'total_execucoes': total_execucoes,
                    'sucessos': sucessos,
                    'falhas': falhas,
                    'em_andamento': em_andamento,
                    'taxa_sucesso': (sucessos / total_execucoes * 100) if total_execucoes > 0 else 0
                },
                'estatisticas_por_operadora': stats_por_operadora
            }
        })

    except Exception as e:
        logger.error("Erro ao gerar relatório de execuções: %s", str(e))
        return jsonify({
            'success': False,
            'message': f'Erro ao gerar relatório: {str(e)}'
        }), 500


@bp.route('/rpas-disponiveis', methods=['GET'])
@verify_user_jwt
def rpas_disponiveis():
    """Lista RPAs disponíveis no sistema"""
    try:
        from .base import ConcentradorRPA

        concentrador = ConcentradorRPA()
        rpas = concentrador.listar_rpas_disponiveis()

        return jsonify({
            'success': True,
            'rpas_disponiveis': rpas
        })

    except Exception as e:
        logger.error("Erro ao listar RPAs disponíveis: %s", str(e))
        return jsonify({
            'success': False,
            'message': f'Erro ao listar RPAs: {str(e)}'
        }), 500


@bp.route('/teste-rpa/<codigo_operadora>', methods=['POST'])
@verify_user_jwt
def teste_rpa(codigo_operadora):
    """
    Testa RPA específico com dados de exemplo

    Args:
        codigo_operadora: Código da operadora (EMB, VIV, etc.)
    """
    try:
        from .base import ConcentradorRPA, ParametrosEntradaPadrao, TipoOperacao

        concentrador = ConcentradorRPA()
        rpa = concentrador.obter_rpa(codigo_operadora)

        if not rpa:
            return jsonify({
                'success': False,
                'message': f'RPA não encontrado para operadora: {codigo_operadora}'
            }), 404

        # Dados de teste
        parametros_teste = ParametrosEntradaPadrao(
            id_processo="teste-123",
            id_cliente="cliente-teste",
            operadora_codigo=codigo_operadora,
            url_portal="https://portal.teste.com",
            usuario="usuario_teste",
            senha="senha_teste",
            cpf="12345678901",
            filtro="fatura_mensal",
            nome_sat="TESTE_SAT",
            dados_sat="TESTE|DADOS|SAT",
            unidade="MATRIZ",
            servico="INTERNET_DEDICADA"
        )

        # Executa teste
        resultado = concentrador.executar_operacao(
            TipoOperacao.DOWNLOAD_FATURA,
            parametros_teste
        )

        return jsonify({
            'success': resultado.sucesso,
            'message': resultado.mensagem,
            'resultado': {
                'status': resultado.status.value,
                'arquivo_baixado': resultado.arquivo_baixado,
                'url_s3': resultado.url_s3,
                'tempo_execucao': resultado.tempo_execucao_segundos,
                'logs_execucao': resultado.logs_execucao
            }
        })

    except Exception as e:
        logger.error("Erro ao testar RPA %s: %s", codigo_operadora, str(e))
        return jsonify({
            'success': False,
            'message': f'Erro ao testar RPA: {str(e)}'
        }), 500
