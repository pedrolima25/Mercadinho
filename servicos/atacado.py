"""
Serviço de Venda no Atacado
=============================
Regras de negócio para faixas de preço por quantidade de produtos.
"""

from typing import List
from sqlalchemy.orm import Session
import models
from repositorios.atacado import RepositorioAtacado
from servicos.base import ServicoBase


class ServicoAtacado(ServicoBase):
    """Regras de negócio para faixas de preço por quantidade (atacado)."""

    def __init__(self, banco: Session, current_user=None):
        super().__init__(banco, current_user)
        self.repositorio = RepositorioAtacado(banco, self.empresa_id)

    def listar(self) -> List[models.WholesaleTier]:
        """Lista todas as faixas cadastradas."""
        return self.repositorio.listar_todas()

    def obter_ou_erro(self, tier_id: int) -> models.WholesaleTier:
        """Retorna a faixa ou lança 404."""
        return self.obter_ou_404(self.repositorio, tier_id, "Faixa de preço não encontrada")

    def _validar(self, dados_form) -> dict:
        product_id = dados_form.get("product_id")
        if not product_id:
            self.erro_requisicao("Selecione um produto")

        min_quantity = float(dados_form.get("min_quantity") or 0)
        if min_quantity <= 0:
            self.erro_requisicao("A quantidade mínima deve ser maior que zero")

        wholesale_price = float(dados_form.get("wholesale_price") or 0)
        if wholesale_price <= 0:
            self.erro_requisicao("O preço no atacado deve ser maior que zero")

        produto = self.banco.query(models.Product).filter(
            models.Product.id == int(product_id),
            models.Product.company_id == self.empresa_id,
        ).first()
        if not produto:
            self.erro_requisicao("Produto não encontrado")
        if wholesale_price >= float(produto.sale_price):
            self.erro_requisicao("O preço no atacado deve ser menor que o preço normal do produto")

        return {
            "product_id": int(product_id),
            "min_quantity": min_quantity,
            "wholesale_price": wholesale_price,
            "is_active": dados_form.get("is_active") == "on",
        }

    def criar(self, dados_form) -> models.WholesaleTier:
        """Cria uma nova faixa de preço por quantidade."""
        return self.repositorio.criar(self._validar(dados_form))

    def atualizar(self, tier_id: int, dados_form) -> models.WholesaleTier:
        """Atualiza uma faixa existente."""
        tier = self.obter_ou_erro(tier_id)
        for campo, valor in self._validar(dados_form).items():
            setattr(tier, campo, valor)
        self.banco.commit()
        return tier

    def excluir(self, tier_id: int):
        """Remove a faixa de preço."""
        self.obter_ou_erro(tier_id)
        self.repositorio.excluir_fisico(tier_id)
