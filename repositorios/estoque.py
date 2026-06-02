"""
Repositório de Estoque
======================
Queries para movimentações de estoque e lotes de produtos.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import models
from repositorios.base import RepositorioBase


class RepositorioMovimentacoes(RepositorioBase):
    """Queries de movimentações de estoque."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.StockMovement)

    def listar_recentes(self, limite: int = 30) -> List[models.StockMovement]:
        """Últimas movimentações com dados do produto e usuário."""
        return (
            self.banco.query(self.modelo)
            .options(
                joinedload(self.modelo.product),
                joinedload(self.modelo.user),
            )
            .order_by(self.modelo.created_at.desc())
            .limit(limite)
            .all()
        )

    def listar_com_filtros(
        self,
        produto_id: int = None,
        tipo: str = None,
        pagina: int = 1,
        por_pagina: int = 30,
    ) -> tuple:
        """
        Histórico de movimentações com filtros.

        Returns:
            (lista_movimentacoes, total)
        """
        consulta = self.banco.query(self.modelo).options(
            joinedload(self.modelo.product),
            joinedload(self.modelo.user),
        )
        if produto_id:
            consulta = consulta.filter(self.modelo.product_id == produto_id)
        if tipo:
            consulta = consulta.filter(self.modelo.type == tipo)

        total = consulta.count()
        deslocamento = (pagina - 1) * por_pagina
        movimentacoes = (
            consulta.order_by(self.modelo.created_at.desc())
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )
        return movimentacoes, total


class RepositorioLotes(RepositorioBase):
    """Queries de lotes de produtos com validade."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.ProductBatch)

    def listar_todos(self) -> List[models.ProductBatch]:
        """Todos os lotes ordenados por validade."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.product))
            .order_by(self.modelo.expiry_date)
            .all()
        )

    def proximos_a_vencer(self, limite: int = 20) -> List[models.ProductBatch]:
        """Lotes com data de validade próxima."""
        return (
            self.banco.query(self.modelo)
            .options(joinedload(self.modelo.product))
            .filter(self.modelo.expiry_date != None)
            .order_by(self.modelo.expiry_date)
            .limit(limite)
            .all()
        )
