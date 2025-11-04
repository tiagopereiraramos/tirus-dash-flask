"""
RPA Base Concentrador - Sistema de Orquestração RPA BEG Telecomunicações

Implementação do padrão imutável de entrada/saída para todos os RPAs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
from datetime import datetime
import uuid

from apps.models import Processo, Execucao, Cliente, Operadora
from apps.models.execucao import TipoExecucao, StatusExecucao
from apps import db


class TipoOperacao(Enum):
    """Tipos de operação suportados pelo sistema"""
    DOWNLOAD_FATURA = "DOWNLOAD_FATURA"
    UPLOAD_SAT = "UPLOAD_SAT"


class StatusExecucaoRPA(Enum):
    """Status de execução específicos do RPA"""
    INICIADO = "iniciado"
    EM_PROGRESSO = "em_progresso"
    SUCESSO = "sucesso"
    ERRO = "erro"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ParametrosEntradaPadrao:
    """
    Parâmetros de entrada padronizados para todos os RPAs

    Classe imutável que garante consistência na entrada de dados
    """
    id_processo: str
    id_cliente: str
    operadora_codigo: str
    url_portal: str
    usuario: str
    senha: str
    cpf: Optional[str] = None
    filtro: Optional[str] = None
    nome_sat: str = ""
    dados_sat: str = ""
    unidade: str = ""
    servico: str = ""


@dataclass
class ResultadoSaidaPadrao:
    """
    Resultado de saída padronizado para todos os RPAs

    Contém todos os dados necessários para rastreabilidade
    """
    sucesso: bool
    status: StatusExecucaoRPA
    mensagem: str
    arquivo_baixado: Optional[str] = None
    url_s3: Optional[str] = None
    dados_extraidos: Dict[str, Any] = None
    tempo_execucao_segundos: float = 0.0
    tentativa_numero: int = 1
    timestamp_inicio: Optional[datetime] = None
    timestamp_fim: Optional[datetime] = None
    logs_execucao: List[str] = None
    screenshots_debug: List[str] = None
    dados_especificos: Dict[str, Any] = None

    def __post_init__(self):
        """Inicializa listas vazias se não fornecidas"""
        if self.dados_extraidos is None:
            self.dados_extraidos = {}
        if self.logs_execucao is None:
            self.logs_execucao = []
        if self.screenshots_debug is None:
            self.screenshots_debug = []
        if self.dados_especificos is None:
            self.dados_especificos = {}


class RPABase(ABC):
    """
    Classe base abstrata para todos os RPAs

    Define a interface padrão que todos os RPAs devem implementar
    """

    def __init__(self):
        self.logger = logging.getLogger(f"RPA.{self.__class__.__name__}")

    @abstractmethod
    def executar_download(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """
        Executa download de fatura

        Args:
            parametros: Parâmetros padronizados de entrada

        Returns:
            Resultado padronizado da execução
        """
        pass

    @abstractmethod
    def executar_upload_sat(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """
        Executa upload de fatura para SAT

        Args:
            parametros: Parâmetros padronizados de entrada

        Returns:
            Resultado padronizado da execução
        """
        pass

    def adicionar_log(self, mensagem: str) -> None:
        """Adiciona mensagem ao log do RPA"""
        self.logger.info(mensagem)

    def adicionar_erro(self, mensagem: str) -> None:
        """Adiciona erro ao log do RPA"""
        self.logger.error(mensagem)


class ConcentradorRPA:
    """
    Concentrador que gerencia todos os RPAs registrados

    Direciona operações para o RPA correto baseado no código da operadora
    """

    def __init__(self):
        self.logger = logging.getLogger("ConcentradorRPA")
        self.rpas_registrados: Dict[str, RPABase] = {}
        self._registrar_rpas_disponiveis()

    def _registrar_rpas_disponiveis(self) -> None:
        """Registra todos os RPAs disponíveis no sistema"""
        try:
            # Importações dinâmicas para evitar dependências circulares
            from .rpas.embratel_rpa import EmbratelRPA
            from .rpas.digitalnet_rpa import DigitalnetRPA
            from .rpas.vivo_rpa import VivoRPA
            from .rpas.oi_rpa import OiRPA
            from .rpas.sat_rpa import SatRPA

            self.rpas_registrados = {
                "EMB": EmbratelRPA(),
                "DIG": DigitalnetRPA(),
                "VIV": VivoRPA(),
                "OII": OiRPA(),
                "SAT": SatRPA(),  # RPA para upload no SAT
            }

            self.logger.info("RPAs registrados: %s",
                             list(self.rpas_registrados.keys()))

        except ImportError as e:
            self.logger.warning(
                "Alguns RPAs não puderam ser registrados: %s", str(e))
            # Registra apenas os RPAs disponíveis
            self.rpas_registrados = {}

    def executar_operacao(self, operacao: TipoOperacao, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """
        Executa operação no RPA apropriado

        Args:
            operacao: Tipo de operação a ser executada
            parametros: Parâmetros padronizados de entrada

        Returns:
            Resultado padronizado da execução
        """
        try:
            # Determina qual RPA usar baseado na operação
            codigo_rpa = "SAT" if operacao == TipoOperacao.UPLOAD_SAT else parametros.operadora_codigo

            if codigo_rpa not in self.rpas_registrados:
                self.logger.error("RPA não encontrado: %s", codigo_rpa)
                return ResultadoSaidaPadrao(
                    sucesso=False,
                    status=StatusExecucaoRPA.ERRO,
                    mensagem=f"RPA não encontrado: {codigo_rpa}"
                )

            rpa = self.rpas_registrados[codigo_rpa]
            self.logger.info("Executando %s com RPA %s",
                             operacao.value, codigo_rpa)

            # Executa a operação apropriada
            if operacao == TipoOperacao.DOWNLOAD_FATURA:
                return rpa.executar_download(parametros)
            elif operacao == TipoOperacao.UPLOAD_SAT:
                return rpa.executar_upload_sat(parametros)
            else:
                return ResultadoSaidaPadrao(
                    sucesso=False,
                    status=StatusExecucaoRPA.ERRO,
                    mensagem=f"Operação não suportada: {operacao}"
                )

        except Exception as e:
            self.logger.error("Erro na execução da operação: %s", str(e))
            return ResultadoSaidaPadrao(
                sucesso=False,
                status=StatusExecucaoRPA.ERRO,
                mensagem=f"Erro interno: {str(e)}"
            )

    def listar_rpas_disponiveis(self) -> List[str]:
        """Retorna lista de códigos dos RPAs disponíveis"""
        return list(self.rpas_registrados.keys())

    def obter_rpa(self, codigo: str) -> Optional[RPABase]:
        """Retorna RPA específico pelo código"""
        return self.rpas_registrados.get(codigo)


class ServicoRPA:
    """
    Serviço que integra o ConcentradorRPA com o sistema de processos
    """

    def __init__(self):
        self.concentrador = ConcentradorRPA()
        self.logger = logging.getLogger("ServicoRPA")

    def executar_download_processo(self, processo_id: str, usuario_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executa download de fatura para um processo específico

        Args:
            processo_id: ID do processo
            usuario_id: ID do usuário que iniciou a execução

        Returns:
            Dicionário com resultado da execução
        """
        try:
            # Busca o processo
            processo = Processo.query.get_or_404(processo_id)

            # Verifica se pode executar
            if processo.status_processo != "AGUARDANDO_DOWNLOAD":
                return {
                    'success': False,
                    'message': 'Processo não está no status adequado para download'
                }

            # Verifica se processo pode executar download
            if not processo.pode_tentar_download_novamente:
                return {
                    'success': False,
                    'message': 'Processo não está no status adequado para download'
                }

            # Cria execução com número da tentativa correto
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                numero_tentativa=processo.numero_tentativas_download + 1,
                executado_por_usuario_id=usuario_id
            )

            db.session.add(execucao)
            db.session.commit()

            # Prepara parâmetros
            parametros = self._criar_parametros_entrada(processo)

            # Executa RPA
            resultado = self.concentrador.executar_operacao(
                TipoOperacao.DOWNLOAD_FATURA,
                parametros
            )

            # Atualiza execução
            self._atualizar_execucao_com_resultado(execucao, resultado)

            # Atualiza processo se sucesso
            if resultado.sucesso:
                processo.marcar_download_completo()
                if resultado.url_s3:
                    processo.caminho_s3_fatura = resultado.url_s3
                if resultado.dados_extraidos:
                    if 'valor_fatura' in resultado.dados_extraidos:
                        processo.valor_fatura = resultado.dados_extraidos['valor_fatura']
                    if 'data_vencimento' in resultado.dados_extraidos:
                        processo.data_vencimento = resultado.dados_extraidos['data_vencimento']

            db.session.commit()

            return {
                'success': resultado.sucesso,
                'execucao_id': str(execucao.id),
                'message': resultado.mensagem,
                'resultado': {
                    'arquivo_baixado': resultado.arquivo_baixado,
                    'url_s3': resultado.url_s3,
                    'dados_extraidos': resultado.dados_extraidos,
                    'tempo_execucao': resultado.tempo_execucao_segundos
                }
            }

        except Exception as e:
            db.session.rollback()
            self.logger.error("Erro ao executar download: %s", str(e))
            return {
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }

    def executar_upload_sat_processo(self, processo_id: str, usuario_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executa upload de fatura para SAT

        Args:
            processo_id: ID do processo
            usuario_id: ID do usuário que iniciou a execução

        Returns:
            Dicionário com resultado da execução
        """
        try:
            processo = Processo.query.get_or_404(processo_id)

            if not processo.pode_enviar_sat:
                return {
                    'success': False,
                    'message': 'Processo não pode ser enviado para SAT'
                }

            # Verifica se processo pode executar SAT
            if not processo.pode_tentar_sat_novamente:
                return {
                    'success': False,
                    'message': 'Processo não está no status adequado para envio SAT'
                }

            # Cria execução com número da tentativa correto
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.UPLOAD_SAT.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                numero_tentativa=processo.numero_tentativas_sat + 1,
                executado_por_usuario_id=usuario_id
            )

            db.session.add(execucao)
            db.session.commit()

            # Prepara parâmetros
            parametros = self._criar_parametros_entrada(processo)

            # Executa RPA
            resultado = self.concentrador.executar_operacao(
                TipoOperacao.UPLOAD_SAT,
                parametros
            )

            # Atualiza execução
            self._atualizar_execucao_com_resultado(execucao, resultado)

            # Atualiza processo se sucesso
            if resultado.sucesso:
                processo.enviar_para_sat()

            db.session.commit()

            return {
                'success': resultado.sucesso,
                'execucao_id': str(execucao.id),
                'message': resultado.mensagem
            }

        except Exception as e:
            db.session.rollback()
            self.logger.error("Erro ao executar upload SAT: %s", str(e))
            return {
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }

    def _criar_parametros_entrada(self, processo: Processo) -> ParametrosEntradaPadrao:
        """Cria parâmetros de entrada padronizados a partir do processo"""
        cliente = processo.cliente
        operadora = cliente.operadora

        return ParametrosEntradaPadrao(
            id_processo=str(processo.id),
            id_cliente=str(cliente.id),
            operadora_codigo=operadora.codigo,
            url_portal=operadora.url_portal or "",
            usuario=cliente.login_portal or "",
            senha=cliente.senha_portal or "",
            cpf=cliente.cpf,
            filtro=cliente.filtro,
            nome_sat=cliente.nome_sat,
            dados_sat=cliente.dados_sat or "",
            unidade=cliente.unidade,
            servico=cliente.servico or ""
        )

    def _atualizar_execucao_com_resultado(self, execucao: Execucao, resultado: ResultadoSaidaPadrao) -> None:
        """Atualiza execução com resultado do RPA"""
        execucao.data_fim = datetime.now()

        if resultado.sucesso:
            execucao.status_execucao = StatusExecucao.CONCLUIDO.value
        else:
            execucao.status_execucao = StatusExecucao.FALHOU.value

        execucao.resultado_saida = {
            'sucesso': resultado.sucesso,
            'status': resultado.status.value,
            'mensagem': resultado.mensagem,
            'arquivo_baixado': resultado.arquivo_baixado,
            'url_s3': resultado.url_s3,
            'dados_extraidos': resultado.dados_extraidos,
            'tempo_execucao_segundos': resultado.tempo_execucao_segundos,
            'logs_execucao': resultado.logs_execucao,
            'screenshots_debug': resultado.screenshots_debug,
            'dados_especificos': resultado.dados_especificos
        }

        if resultado.logs_execucao:
            execucao.mensagem_log = "\n".join(resultado.logs_execucao)

        if resultado.url_s3:
            execucao.url_arquivo_s3 = resultado.url_s3
