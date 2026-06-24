"""
Repositório de Promoções
=========================
Queries de preços promocionais temporários por produto.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
import models
from repositorios.base import RepositorioBase


class RepositorioPromocoes(RepositorioBase):
    """Queries de promoções."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Promotion)

    def listar_todas(self) -> List[models.Promotion]:
        """Todas as promoções, mais recentes primeiro, com o produto carregado."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.product))
            .order_by(self.modelo.start_at.desc())
            .all()
        )
