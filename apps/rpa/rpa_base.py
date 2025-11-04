"""
Base RPA Concentrator - Padrão Imutável Input/Output
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class StatusExecucao(Enum):
    """Status de execução do RPA"""
    PENDENTE = "PENDENTE"
    EM_EXECUCAO = "EM_EXECUCAO"
    CONCLUIDO = "CONCLUIDO"
    ERRO = "ERRO"
    TIMEOUT = "TIMEOUT"


@dataclass
class InputRPA:
    """Input imutável para RPA"""
    cliente_id: str
    operadora_id: str
    mes_ano: str
    credenciais: Dict[str, Any]
    parametros_especiais: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutputRPA:
    """Output imutável do RPA"""
    sucesso: bool
    status: StatusExecucao
    mensagem: str
    dados_fatura: Optional[Dict[str, Any]] = None
    erro_tecnico: Optional[str] = None
    tempo_execucao: Optional[float] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.timestamp:
            result['timestamp'] = self.timestamp.isoformat()
        return result


class RPABase(ABC):
    """
    Classe base para todos os RPAs

    Implementa o padrão imutável Input/Output e fornece
    métodos comuns para todos os RPAs.
    """

    def __init__(self, timeout_padrao: int = 300, tentativas_maximas: int = 3):
        self.timeout_padrao = timeout_padrao
        self.tentativas_maximas = tentativas_maximas
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def executar_download(self, input_data: InputRPA) -> OutputRPA:
        """
        Executa o download da fatura

        Args:
            input_data: Dados de entrada imutáveis

        Returns:
            OutputRPA: Resultado da execução
        """
        pass

    @abstractmethod
    def executar_upload_sat(self, input_data: InputRPA) -> OutputRPA:
        """
        Executa o upload para o SAT

        Args:
            input_data: Dados de entrada imutáveis

        Returns:
            OutputRPA: Resultado da execução
        """
        pass

    def validar_input(self, input_data: InputRPA) -> List[str]:
        """
        Valida os dados de entrada

        Args:
            input_data: Dados a serem validados

        Returns:
            Lista de erros encontrados
        """
        erros = []

        if not input_data.cliente_id:
            erros.append("cliente_id é obrigatório")

        if not input_data.operadora_id:
            erros.append("operadora_id é obrigatório")

        if not input_data.mes_ano:
            erros.append("mes_ano é obrigatório")

        if not input_data.credenciais:
            erros.append("credenciais são obrigatórias")

        return erros

    def simular_download_dummy(self, input_data: InputRPA) -> OutputRPA:
        """
        Simula download dummy para testes

        Args:
            input_data: Dados de entrada

        Returns:
            OutputRPA com dados simulados
        """
        self.logger.info(
            f"Simulando download dummy para cliente {input_data.cliente_id}")

        # Simula tempo de processamento
        time.sleep(2)

        # Gera dados dummy da fatura
        dados_fatura = {
            "url_fatura": f"https://portal.{input_data.operadora_id}.com/fatura/{input_data.mes_ano}",
            "caminho_s3_fatura": f"s3://faturas/{input_data.cliente_id}/{input_data.mes_ano}/fatura.pdf",
            "data_vencimento": "2024-12-15",
            "valor_fatura": 1250.50,
            "numero_fatura": f"FAT-{input_data.mes_ano}-001",
            "status_download": "CONCLUIDO"
        }

        return OutputRPA(
            sucesso=True,
            status=StatusExecucao.CONCLUIDO,
            mensagem="Download simulado com sucesso",
            dados_fatura=dados_fatura,
            tempo_execucao=2.0,
            timestamp=datetime.now()
        )

    def simular_upload_sat_dummy(self, input_data: InputRPA) -> OutputRPA:
        """
        Simula upload para SAT dummy para testes

        Args:
            input_data: Dados de entrada

        Returns:
            OutputRPA com resultado simulado
        """
        self.logger.info(
            f"Simulando upload SAT dummy para cliente {input_data.cliente_id}")

        # Simula tempo de processamento
        time.sleep(1.5)

        return OutputRPA(
            sucesso=True,
            status=StatusExecucao.CONCLUIDO,
            mensagem="Upload para SAT simulado com sucesso",
            dados_fatura={
                "protocolo_sat": f"SAT-{input_data.cliente_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "status_envio": "ENVIADO",
                "data_envio": datetime.now().isoformat()
            },
            tempo_execucao=1.5,
            timestamp=datetime.now()
        )

    def simular_erro_dummy(self, input_data: InputRPA, tipo_erro: str = "timeout") -> OutputRPA:
        """
        Simula erro dummy para testes

        Args:
            input_data: Dados de entrada
            tipo_erro: Tipo de erro a simular

        Returns:
            OutputRPA com erro simulado
        """
        self.logger.warning(f"Simulando erro dummy: {tipo_erro}")

        erros = {
            "timeout": ("Timeout na conexão com portal", StatusExecucao.TIMEOUT),
            "credenciais": ("Credenciais inválidas", StatusExecucao.ERRO),
            "fatura_nao_encontrada": ("Fatura não encontrada", StatusExecucao.ERRO),
            "portal_indisponivel": ("Portal temporariamente indisponível", StatusExecucao.ERRO)
        }

        mensagem, status = erros.get(
            tipo_erro, ("Erro desconhecido", StatusExecucao.ERRO))

        return OutputRPA(
            sucesso=False,
            status=status,
            mensagem=mensagem,
            erro_tecnico=f"Erro simulado: {tipo_erro}",
            tempo_execucao=1.0,
            timestamp=datetime.now()
        )
