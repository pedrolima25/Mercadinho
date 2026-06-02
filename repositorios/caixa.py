"""
Repositório de Caixa
====================
Queries para registros de caixa e movimentações (sangria/suprimento).
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
import models
from repositorios.base import RepositorioBase


class RepositorioCaixa(RepositorioBase):
    """Queries de registros de abertura/fechamento de caixa."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.CashRegister)

    def buscar_aberto_do_usuario(self, usuario_id: int) -> Optional[models.CashRegister]:
        """Retorna o caixa aberto do usuário, se existir."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.user))
            .filter(
                self.modelo.user_id == usuario_id,
                self.modelo.status == models.CashRegisterStatus.aberto,
            )
            .first()
        )

    def historico_do_usuario(self, usuario_id: int, limite: int = 10) -> List[models.CashRegister]:
        """Últimos caixas do usuário ordenados do mais recente."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.user))
            .filter(self.modelo.user_id == usuario_id)
            .order_by(self.modelo.opened_at.desc())
            .limit(limite)
            .all()
        )

    def buscar_com_detalhes(self, caixa_id: int) -> Optional[models.CashRegister]:
        """Retorna caixa com vendas, pagamentos e movimentações carregados."""
        return (
            self.banco.query(self.modelo)
            .options(
                joinedload(self.modelo.user),
                joinedload(self.modelo.sales).joinedload(models.Sale.payments),
                joinedload(self.modelo.cash_movements),
            )
            .filter(self.modelo.id == caixa_id)
            .first()
        )
