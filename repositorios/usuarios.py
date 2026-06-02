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

    def __init__(self, banco: Session):
        super().__init__(banco, models.User)

    def buscar_por_username(self, username: str) -> Optional[models.User]:
        """Retorna usuário pelo nome de login."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.username == username)
            .first()
        )

    def listar_todos(self) -> List[models.User]:
        """Todos os usuários ordenados por nome completo."""
        return self.banco.query(self.modelo).order_by(self.modelo.full_name).all()

    def listar_ativos(self) -> List[models.User]:
        """Somente usuários ativos."""
        return (
            self.banco.query(self.modelo)
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.full_name)
            .all()
        )
