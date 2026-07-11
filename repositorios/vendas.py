"""
Repositório de Vendas
=====================
Queries para vendas, itens, pagamentos e devoluções.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import models
from repositorios.base import RepositorioBase


class RepositorioVendas(RepositorioBase):
    """Queries de vendas."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.Sale, empresa_id)

    def listar_com_filtros(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        status: str = None,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> Tuple[List[models.Sale], int]:
        """Lista vendas com filtros de data, status e paginação."""
        consulta = self._query().options(
            joinedload(self.modelo.customer),
            joinedload(self.modelo.user),
            joinedload(self.modelo.items),
        )
        if data_inicio:
            consulta = consulta.filter(func.date(self.modelo.created_at) >= data_inicio)
        if data_fim:
            consulta = consulta.filter(func.date(self.modelo.created_at) <= data_fim)
        if status:
            consulta = consulta.filter(self.modelo.status == status)

        total = consulta.count()
        deslocamento = (pagina - 1) * por_pagina
        vendas = (
            consulta.order_by(self.modelo.created_at.desc())
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )
        return vendas, total

    def buscar_com_detalhes(self, venda_id: int) -> Optional[models.Sale]:
        """Retorna venda com cliente, operador, itens, pagamentos e devoluções."""
        return (
            self._query()
            .options(
                joinedload(self.modelo.customer),
                joinedload(self.modelo.user),
                joinedload(self.modelo.items).joinedload(models.SaleItem.product),
                joinedload(self.modelo.payments),
                joinedload(self.modelo.returns).joinedload(models.SaleReturn.items)
                    .joinedload(models.SaleReturnItem.product),
                joinedload(self.modelo.returns).joinedload(models.SaleReturn.user),
            )
            .filter(self.modelo.id == venda_id)
            .first()
        )
