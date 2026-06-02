"""
Repositório de Catálogos
========================
Queries para: Categorias, Marcas, Fornecedores, Clientes e Funcionários.
Nenhuma lógica de negócio — só acesso ao banco.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
import models
from repositorios.base import RepositorioBase


# ── Categorias ─────────────────────────────────────────────────────────────

class RepositorioCategorias(RepositorioBase):
    """Queries de categorias de produtos."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Category)

    def listar_ativas(self) -> List[models.Category]:
        """Todas as categorias ativas ordenadas por nome."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def listar_todas(self) -> List[models.Category]:
        """Todas as categorias (ativas e inativas) ordenadas por nome."""
        return self.banco.query(self.modelo).order_by(self.modelo.name).all()


# ── Marcas ──────────────────────────────────────────────────────────────────

class RepositorioMarcas(RepositorioBase):
    """Queries de marcas de produtos."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Brand)

    def listar_ativas(self) -> List[models.Brand]:
        """Todas as marcas ativas ordenadas por nome."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def listar_todas(self) -> List[models.Brand]:
        """Todas as marcas ordenadas por nome."""
        return self.banco.query(self.modelo).order_by(self.modelo.name).all()


# ── Fornecedores ─────────────────────────────────────────────────────────────

class RepositorioFornecedores(RepositorioBase):
    """Queries de fornecedores."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Supplier)

    def listar_ativos(self) -> List[models.Supplier]:
        """Fornecedores ativos ordenados por nome."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def listar_todos(self) -> List[models.Supplier]:
        """Todos os fornecedores ordenados por nome."""
        return self.banco.query(self.modelo).order_by(self.modelo.name).all()


# ── Clientes ──────────────────────────────────────────────────────────────────

class RepositorioClientes(RepositorioBase):
    """Queries de clientes."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Customer)

    def listar_ativos(self) -> List[models.Customer]:
        """Clientes ativos ordenados por nome."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def listar_todos(self) -> List[models.Customer]:
        """Todos os clientes ordenados por nome."""
        return self.banco.query(self.modelo).order_by(self.modelo.name).all()


# ── Funcionários ──────────────────────────────────────────────────────────────

class RepositorioFuncionarios(RepositorioBase):
    """Queries de funcionários."""

    def __init__(self, banco: Session):
        super().__init__(banco, models.Employee)

    def listar_ativos(self) -> List[models.Employee]:
        """Funcionários ativos ordenados por nome."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def listar_todos(self) -> List[models.Employee]:
        """Todos os funcionários ordenados por nome."""
        return self.banco.query(self.modelo).order_by(self.modelo.name).all()
