"""
Repositório Financeiro
======================
Queries para contas a pagar, contas a receber e despesas.
"""

from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import models
from repositorios.base import RepositorioBase


class RepositorioContasPagar(RepositorioBase):
    """Queries de contas a pagar."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.AccountPayable, empresa_id)

    def listar_com_filtros(
        self, status: str = None, pagina: int = 1, por_pagina: int = 20
    ) -> Tuple[List[models.AccountPayable], int]:
        """Lista contas com filtro de status e paginação."""
        consulta = self._query().options(
            joinedload(self.modelo.supplier)
        )
        if status:
            consulta = consulta.filter(self.modelo.status == status)
        total = consulta.count()
        deslocamento = (pagina - 1) * por_pagina
        itens = consulta.order_by(self.modelo.due_date).offset(deslocamento).limit(por_pagina).all()
        return itens, total

    def total_pendente(self, hoje: date = None) -> float:
        """Soma das contas pendentes ainda não vencidas."""
        hoje = hoje or date.today()
        return float(
            self._query().with_entities(func.sum(self.modelo.amount))
            .filter(self.modelo.status == models.AccountStatus.pendente, self.modelo.due_date >= hoje)
            .scalar() or 0
        )

    def total_vencido(self, hoje: date = None) -> float:
        """Soma das contas pendentes já vencidas."""
        hoje = hoje or date.today()
        return float(
            self._query().with_entities(func.sum(self.modelo.amount))
            .filter(self.modelo.status == models.AccountStatus.pendente, self.modelo.due_date < hoje)
            .scalar() or 0
        )

    def listar_pendentes_proximas(self, limite: int = 10) -> List[models.AccountPayable]:
        """Próximas contas a vencer, ordenadas por data."""
        return (
            self._query()
            .options(joinedload(self.modelo.supplier))
            .filter(self.modelo.status == models.AccountStatus.pendente)
            .order_by(self.modelo.due_date)
            .limit(limite)
            .all()
        )


class RepositorioContasReceber(RepositorioBase):
    """Queries de contas a receber."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.AccountReceivable, empresa_id)

    def listar_com_filtros(
        self, status: str = None, pagina: int = 1, por_pagina: int = 20
    ) -> Tuple[List[models.AccountReceivable], int]:
        """Lista contas com filtro de status e paginação."""
        consulta = self._query().options(
            joinedload(self.modelo.customer)
        )
        if status:
            consulta = consulta.filter(self.modelo.status == status)
        total = consulta.count()
        deslocamento = (pagina - 1) * por_pagina
        itens = consulta.order_by(self.modelo.due_date).offset(deslocamento).limit(por_pagina).all()
        return itens, total

    def total_pendente(self) -> float:
        """Soma de todas as contas a receber pendentes."""
        return float(
            self._query().with_entities(func.sum(self.modelo.amount))
            .filter(self.modelo.status == models.AccountStatus.pendente)
            .scalar() or 0
        )

    def listar_pendentes_proximas(self, limite: int = 10) -> List[models.AccountReceivable]:
        """Próximas contas a receber, ordenadas por data."""
        return (
            self._query()
            .options(joinedload(self.modelo.customer))
            .filter(self.modelo.status == models.AccountStatus.pendente)
            .order_by(self.modelo.due_date)
            .limit(limite)
            .all()
        )


class RepositorioDespesas(RepositorioBase):
    """Queries de despesas operacionais."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.Expense, empresa_id)

    def listar_paginado(self, pagina: int = 1, por_pagina: int = 20) -> Tuple[List[models.Expense], int]:
        """Lista despesas mais recentes com paginação."""
        total = self._query().count()
        deslocamento = (pagina - 1) * por_pagina
        itens = (
            self._query()
            .order_by(self.modelo.date.desc())
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )
        return itens, total

    def total_no_mes(self, mes: int, ano: int) -> float:
        """Soma das despesas de um mês/ano específico."""
        from sqlalchemy import extract
        return float(
            self._query().with_entities(func.sum(self.modelo.amount))
            .filter(
                extract("month", self.modelo.date) == mes,
                extract("year", self.modelo.date) == ano,
            )
            .scalar() or 0
        )
