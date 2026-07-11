"""
Repositório de Produtos
=======================
Responsável por todas as queries relacionadas a produtos no banco de dados.
Nenhuma lógica de negócio aqui — só acesso ao banco.
"""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import models
from repositorios.base import RepositorioBase


class RepositorioProdutos(RepositorioBase):
    """Queries de produtos, categorias e marcas."""

    def __init__(self, banco: Session, empresa_id: Optional[int] = None):
        super().__init__(banco, models.Product, empresa_id)

    def buscar_com_filtros(
        self,
        texto: str = None,
        categoria_id: int = None,
        estoque_baixo: bool = False,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> tuple:
        """
        Busca produtos com filtros opcionais e paginação.

        Returns:
            (lista_de_produtos, total_encontrado)
        """
        # Monta a query base com carregamento antecipado das relações
        consulta = self._query().options(
            joinedload(self.modelo.category),
            joinedload(self.modelo.brand),
        )

        # Filtro de texto (nome ou código de barras)
        if texto:
            termo = f"%{texto}%"
            consulta = consulta.filter(
                or_(
                    self.modelo.name.ilike(termo),
                    self.modelo.barcode.ilike(termo),
                )
            )

        # Filtro de categoria
        if categoria_id:
            consulta = consulta.filter(self.modelo.category_id == categoria_id)

        # Filtro de estoque baixo
        if estoque_baixo:
            consulta = consulta.filter(
                self.modelo.stock_quantity <= self.modelo.min_stock
            )

        # Conta total antes de paginar
        total = consulta.count()

        # Aplica paginação e ordena por nome
        deslocamento = (pagina - 1) * por_pagina
        produtos = (
            consulta.order_by(self.modelo.name)
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )

        return produtos, total

    def buscar_por_codigo_barras(self, codigo: str) -> Optional[models.Product]:
        """Retorna produto pelo código de barras (EAN, QR Code, etc.)."""
        return (
            self._query()
            .options(
                joinedload(self.modelo.promotions),
                joinedload(self.modelo.wholesale_tiers),
                joinedload(self.modelo.campaign_items).joinedload(models.CampaignItem.campaign),
            )
            .filter(
                self.modelo.barcode == codigo,
                self.modelo.is_active == True,
            )
            .first()
        )

    def buscar_por_codigo_balanca(self, codigo_5: str) -> Optional[models.Product]:
        """Busca produto pelo código de 5 dígitos da balança (últimos 5 do EAN)."""
        opts = [
            joinedload(self.modelo.promotions),
            joinedload(self.modelo.wholesale_tiers),
            joinedload(self.modelo.campaign_items).joinedload(models.CampaignItem.campaign),
        ]
        # Tenta match exato do código de 5 dígitos no final do barcode
        produto = (
            self._query()
            .options(*opts)
            .filter(
                self.modelo.barcode.like(f"%{codigo_5}"),
                self.modelo.is_active == True,
            )
            .first()
        )
        if not produto:
            # Tenta match pelo próprio código como barcode direto
            produto = (
                self._query()
                .options(*opts)
                .filter(
                    self.modelo.barcode == codigo_5,
                    self.modelo.is_active == True,
                )
                .first()
            )
        return produto

    def com_estoque_baixo(self, limite: int = None) -> List[models.Product]:
        """Produtos com quantidade atual abaixo do mínimo configurado."""
        consulta = (
            self._query()
            .filter(
                self.modelo.is_active == True,
                self.modelo.stock_quantity <= self.modelo.min_stock,
            )
            .order_by(self.modelo.stock_quantity)
        )
        if limite:
            consulta = consulta.limit(limite)
        return consulta.all()

    def buscar_ativos_ordenados(self) -> List[models.Product]:
        """Todos os produtos ativos ordenados por nome — usado no PDV."""
        return (
            self._query()
            .options(
                joinedload(self.modelo.category),
                joinedload(self.modelo.promotions),
                joinedload(self.modelo.wholesale_tiers),
                joinedload(self.modelo.campaign_items).joinedload(models.CampaignItem.campaign),
            )
            .filter(self.modelo.is_active == True)
            .order_by(self.modelo.name)
            .all()
        )

    def buscar_por_texto_rapido(self, texto: str, limite: int = 10) -> List[models.Product]:
        """Busca rápida por nome ou código de barras — usada no autocomplete do PDV."""
        termo = f"%{texto}%"
        return (
            self._query()
            .options(
                joinedload(self.modelo.promotions),
                joinedload(self.modelo.wholesale_tiers),
                joinedload(self.modelo.campaign_items).joinedload(models.CampaignItem.campaign),
            )
            .filter(
                self.modelo.is_active == True,
                or_(
                    self.modelo.name.ilike(termo),
                    self.modelo.barcode.ilike(termo),
                ),
            )
            .limit(limite)
            .all()
        )

    def codigo_barras_ja_existe(self, codigo: str, exceto_id: int = None) -> bool:
        """
        Verifica se um código de barras já está em uso.

        Args:
            codigo: Código a verificar
            exceto_id: Ignora este produto (útil na edição)
        """
        consulta = self.banco.query(self.modelo).filter(
            self.modelo.barcode == codigo
        )
        if exceto_id:
            consulta = consulta.filter(self.modelo.id != exceto_id)
        return consulta.first() is not None
