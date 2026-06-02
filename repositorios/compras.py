"""
Repositório de Compras
======================
Queries para pedidos de compra e seus itens.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
import models
from repositorios.base import RepositorioBase


class RepositorioCompras(RepositorioBase):
    """Queries de pedidos de compra a fornecedores."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Purchase)

    def listar_com_filtros(
        self, status: str = None, pagina: int = 1, por_pagina: int = 20
    ) -> Tuple[List[models.Purchase], int]:
        """Lista compras com filtro de status e paginação."""
        consulta = self.banco.query(self.modelo).options(
            joinedload(self.modelo.supplier)
        )
        if status:
            consulta = consulta.filter(self.modelo.status == status)

        total = consulta.count()
        deslocamento = (pagina - 1) * por_pagina
        compras = (
            consulta.order_by(self.modelo.created_at.desc())
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )
        return compras, total

    def buscar_com_itens(self, compra_id: int) -> Optional[models.Purchase]:
        """Retorna compra com fornecedor e itens carregados."""
        return (
            self.banco.query(self.modelo)
            .options(
                joinedload(self.modelo.supplier),
                joinedload(self.modelo.items).joinedload(models.PurchaseItem.product),
            )
            .filter(self.modelo.id == compra_id)
            .first()
        )
