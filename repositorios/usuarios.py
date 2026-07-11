"""
Repositório de Usuários
=======================
Queries de usuários do sistema. Nenhuma lógica de negócio aqui.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
import models
from repositorios.base import RepositorioBase


class RepositorioUsuarios(RepositorioBase):
    """Queries de usuários do sistema."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.User, empresa_id)

    def buscar_por_username(self, username: str) -> Optional[models.User]:
        """
        Retorna usuário pelo nome de login. Não filtra por empresa: username
        é único no sistema inteiro (usado para checar duplicidade ao criar).
        """
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.username == username)
            .first()
        )

    def listar_todos(self) -> List[models.User]:
        """Todos os usuários da empresa, ordenados por nome completo."""
        return self._query().order_by(self.modelo.full_name).all()

    def listar_ativos(self) -> List[models.User]:
        """Somente usuários ativos da empresa."""
        return (
            self._query()
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.full_name)
            .all()
        )
