"""
RPA Vivo - Implementação específica para Vivo
"""

from ..base import RPABase, ParametrosEntradaPadrao, ResultadoSaidaPadrao, StatusExecucaoRPA
from datetime import datetime


class VivoRPA(RPABase):
    """RPA específico para Vivo"""

    def __init__(self):
        super().__init__()
        self.nome_rpa = "VivoRPA"

    def executar_download(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa download de fatura Vivo"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="VivoRPA não implementado ainda",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )

    def executar_upload_sat(self, parametros: ParametrosEntradaPadrao) -> ResultadoSaidaPadrao:
        """Executa upload de fatura para SAT"""
        return ResultadoSaidaPadrao(
            sucesso=False,
            status=StatusExecucaoRPA.ERRO,
            mensagem="VivoRPA não suporta upload para SAT",
            timestamp_inicio=datetime.now(),
            timestamp_fim=datetime.now()
        )
