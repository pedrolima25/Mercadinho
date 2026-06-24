"""
Repositório de Venda no Atacado
=================================
Queries de faixas de preço por quantidade (wholesale tiers) por produto.
"""

from typing import List
from sqlalchemy.orm import Session, joinedload
import models
from repositorios.base import RepositorioBase


class RepositorioAtacado(RepositorioBase):
    """Queries de faixas de preço por quantidade."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.WholesaleTier)

    def listar_todas(self) -> List[models.WholesaleTier]:
        """Todas as faixas, agrupadas por produto, com o produto carregado."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.product))
            .order_by(self.modelo.product_id, self.modelo.min_quantity)
            .all()
        )
