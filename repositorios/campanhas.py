"""
Repositório de Campanhas
=========================
Queries de campanhas (encartes temáticos) e seus produtos.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
import models
from repositorios.base import RepositorioBase


class RepositorioCampanhas(RepositorioBase):
    """Queries de campanhas."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.Campaign, empresa_id)

    def listar_todas(self) -> List[models.Campaign]:
        """Todas as campanhas, mais recentes primeiro, com os itens carregados."""
        return (
            self._query()
            .options(joinedload(self.modelo.items).joinedload(models.CampaignItem.product))
            .order_by(self.modelo.created_at.desc())
            .all()
        )

    def buscar_por_id_com_itens(self, campanha_id: int) -> Optional[models.Campaign]:
        """Campanha pelo ID, com os itens e produtos carregados."""
        return (
            self._query()
            .options(joinedload(self.modelo.items).joinedload(models.CampaignItem.product))
            .filter(self.modelo.id == campanha_id)
            .first()
        )

    def buscar_por_slug(self, slug: str) -> Optional[models.Campaign]:
        """
        Campanha ativa pelo slug, com os itens e produtos carregados — usada na
        página pública. O repositório precisa ter sido instanciado com o
        empresa_id da empresa resolvida pela URL, para garantir que a
        campanha encontrada pertence a ela.
        """
        return (
            self._query()
            .options(joinedload(self.modelo.items).joinedload(models.CampaignItem.product))
            .filter(self.modelo.slug == slug, self.modelo.is_active == True)
            .first()
        )

    def slug_ja_existe(self, slug: str, exceto_id: int = None) -> bool:
        """Verifica se um slug já está em uso por outra campanha."""
        consulta = self.banco.query(self.modelo).filter(self.modelo.slug == slug)
        if exceto_id:
            consulta = consulta.filter(self.modelo.id != exceto_id)
        return consulta.first() is not None
