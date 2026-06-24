"""
Serviço de Promoções
=====================
Regras de negócio para preços promocionais temporários de produtos.
"""

from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
import models
from repositorios.promocoes import RepositorioPromocoes
from servicos.base import ServicoBase


class ServicoPromocoes(ServicoBase):
    """Regras de negócio para promoções."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.repositorio = RepositorioPromocoes(banco)

    def listar(self) -> List[models.Promotion]:
        """Lista todas as promoções, mais recentes primeiro."""
        return self.repositorio.listar_todas()

    def obter_ou_erro(self, promocao_id: int) -> models.Promotion:
        """Retorna a promoção ou lança 404."""
        return self.obter_ou_404(self.repositorio, promocao_id, "Promoção não encontrada")

    def _validar(self, dados_form) -> dict:
        product_id = dados_form.get("product_id")
        if not product_id:
            self.erro_requisicao("Selecione um produto")

        promo_price = float(dados_form.get("promo_price") or 0)
        if promo_price <= 0:
            self.erro_requisicao("O preço promocional deve ser maior que zero")

        start_at = dados_form.get("start_at")
        end_at = dados_form.get("end_at")
        if not start_at or not end_at:
            self.erro_requisicao("Informe o período de início e fim da promoção")

        inicio = datetime.fromisoformat(start_at)
        fim = datetime.fromisoformat(end_at)
        if fim <= inicio:
            self.erro_requisicao("A data de término deve ser depois da data de início")

        return {
            "product_id": int(product_id),
            "promo_price": promo_price,
            "start_at": inicio,
            "end_at": fim,
            "is_active": dados_form.get("is_active") == "on",
        }

    def criar(self, dados_form) -> models.Promotion:
        """Cria uma nova promoção para um produto."""
        dados = self._validar(dados_form)
        produto = self.banco.query(models.Product).filter(models.Product.id == dados["product_id"]).first()
        if not produto:
            self.erro_requisicao("Produto não encontrado")
        return self.repositorio.criar(dados)

    def atualizar(self, promocao_id: int, dados_form) -> models.Promotion:
        """Atualiza uma promoção existente."""
        promocao = self.obter_ou_erro(promocao_id)
        dados = self._validar(dados_form)
        for campo, valor in dados.items():
            setattr(promocao, campo, valor)
        self.banco.commit()
        return promocao

    def excluir(self, promocao_id: int):
        """Remove a promoção."""
        self.obter_ou_erro(promocao_id)
        self.repositorio.excluir_fisico(promocao_id)
