"""
Serviço TEF — Transferência Eletrônica de Fundos
=================================================
Suporta dois modos:
  mock=True   → simula aprovação em ~4s (desenvolvimento / sem maquininha)
  mock=False  → integração PayGo Web (serviço local HTTP na porta configurada)

Para usar PayGo real, defina no .env:
  TEF_MOCK=false
  TEF_PAYGO_URL=http://localhost:8080
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class TEFStatus(str, Enum):
    processando = "processando"
    aprovado    = "aprovado"
    negado      = "negado"
    cancelado   = "cancelado"
    erro        = "erro"


@dataclass
class TEFTransacao:
    id: str
    valor: float
    metodo: str          # "debito" ou "credito"
    parcelas: int = 1
    status: TEFStatus = TEFStatus.processando
    nsu: Optional[str] = None
    autorizacao: Optional[str] = None
    mensagem: str = "Apresente o cartão na maquininha"
    criado_em: float = field(default_factory=time.time)


# Armazena transações em memória (suficiente para PDV single-worker)
_store: Dict[str, TEFTransacao] = {}


class ServicoTEF:
    def __init__(self, mock: bool = True, paygo_url: str = "http://localhost:8080"):
        self.mock = mock
        self.paygo_url = paygo_url

    # ── API pública ──────────────────────────────────────────────────────────

    def iniciar(self, valor: float, metodo: str, parcelas: int = 1) -> TEFTransacao:
        tx = TEFTransacao(id=str(uuid.uuid4()), valor=valor, metodo=metodo, parcelas=parcelas)
        _store[tx.id] = tx
        target = self._mock_processar if self.mock else self._paygo_processar
        threading.Thread(target=target, args=(tx,), daemon=True).start()
        return tx

    def obter(self, tx_id: str) -> Optional[TEFTransacao]:
        return _store.get(tx_id)

    def cancelar(self, tx_id: str) -> bool:
        tx = _store.get(tx_id)
        if tx and tx.status == TEFStatus.processando:
            tx.status = TEFStatus.cancelado
            tx.mensagem = "Transação cancelada pelo operador"
            return True
        return False

    # ── Backends ─────────────────────────────────────────────────────────────

    def _mock_processar(self, tx: TEFTransacao):
        """Simula aprovação após 4 s — para testes sem maquininha física."""
        time.sleep(4)
        if tx.status == TEFStatus.cancelado:
            return
        tx.nsu = f"{int(time.time()) % 1_000_000:06d}"
        tx.autorizacao = uuid.uuid4().hex[:6].upper()
        tx.status = TEFStatus.aprovado
        tx.mensagem = "Transação aprovada"

    def _paygo_processar(self, tx: TEFTransacao):
        """Integração PayGo Web TEF — serviço HTTP local."""
        try:
            import httpx
            resp = httpx.post(
                f"{self.paygo_url}/payments",
                json={
                    "amount": int(round(tx.valor * 100)),
                    "paymentType": "DEBIT" if tx.metodo == "debito" else "CREDIT",
                    "installments": tx.parcelas,
                    "externalId": tx.id,
                },
                timeout=120.0,
            )
            data = resp.json()
            if data.get("status") == "APPROVED":
                tx.nsu = str(data.get("nsu", ""))
                tx.autorizacao = str(data.get("authorizationCode", ""))
                tx.status = TEFStatus.aprovado
                tx.mensagem = "Transação aprovada"
            else:
                tx.status = TEFStatus.negado
                tx.mensagem = data.get("message", "Transação negada pela operadora")
        except Exception as exc:
            tx.status = TEFStatus.erro
            tx.mensagem = f"Falha de comunicação com o TEF: {exc}"


# Instância única — lida com configuração ao primeiro uso
_instancia: Optional[ServicoTEF] = None


def get_tef() -> ServicoTEF:
    global _instancia
    if _instancia is None:
        import os
        mock = os.getenv("TEF_MOCK", "true").lower() != "false"
        url  = os.getenv("TEF_PAYGO_URL", "http://localhost:8080")
        _instancia = ServicoTEF(mock=mock, paygo_url=url)
    return _instancia
