"""
Serviço de Campanhas
=====================
Regras de negócio para campanhas (encartes temáticos) e seus produtos.
"""

import re
from typing import List, Optional
from sqlalchemy.orm import Session
import models
from repositorios.campanhas import RepositorioCampanhas
from servicos.base import ServicoBase
from servicos.produtos import ServicoProdutos
from utils.slug import slugify as _slugify_base


def _slugify(texto: str) -> str:
    return _slugify_base(texto, fallback="campanha")


class ServicoCampanhas(ServicoBase):
    """Regras de negócio para campanhas."""

    def __init__(self, banco: Session, current_user=None, empresa_id: Optional[int] = None):
        super().__init__(banco, current_user, empresa_id)
        self.repositorio = RepositorioCampanhas(banco, self.empresa_id)

    def listar(self) -> List[models.Campaign]:
        """Lista todas as campanhas, mais recentes primeiro."""
        return self.repositorio.listar_todas()

    def obter_ou_erro(self, campanha_id: int) -> models.Campaign:
        """Retorna a campanha (com itens) ou lança 404."""
        campanha = self.repositorio.buscar_por_id_com_itens(campanha_id)
        if not campanha:
            self.erro_nao_encontrado("Campanha não encontrada")
        return campanha

    def obter_por_slug_ou_erro(self, slug: str) -> models.Campaign:
        """Retorna a campanha ativa pelo slug ou lança 404 — usado na página pública."""
        campanha = self.repositorio.buscar_por_slug(slug)
        if not campanha:
            self.erro_nao_encontrado("Campanha não encontrada")
        return campanha

    def _gerar_slug_unico(self, nome: str, slug_informado: str, exceto_id: int = None) -> str:
        base = _slugify(slug_informado or nome)
        slug = base
        contador = 2
        while self.repositorio.slug_ja_existe(slug, exceto_id):
            slug = f"{base}-{contador}"
            contador += 1
        return slug

    def _validar(self, dados_form, campanha_id: int = None) -> dict:
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("O nome da campanha é obrigatório")

        cor = (dados_form.get("color_primary") or "#17a8e8").strip()
        if not re.match(r"^#[0-9a-fA-F]{6}$", cor):
            cor = "#17a8e8"

        slug = self._gerar_slug_unico(nome, dados_form.get("slug"), exceto_id=campanha_id)

        return {
            "name": nome,
            "slug": slug,
            "subtitle": (dados_form.get("subtitle") or "").strip() or None,
            "color_primary": cor,
            "is_active": dados_form.get("is_active") == "on",
        }

    def criar(self, dados_form) -> models.Campaign:
        """Cria uma nova campanha."""
        return self.repositorio.criar(self._validar(dados_form))

    def atualizar(self, campanha_id: int, dados_form) -> models.Campaign:
        """Atualiza os dados de uma campanha."""
        campanha = self.obter_ou_erro(campanha_id)
        for campo, valor in self._validar(dados_form, campanha_id=campanha_id).items():
            setattr(campanha, campo, valor)
        self.banco.commit()
        return campanha

    def excluir(self, campanha_id: int):
        """Remove a campanha e seus itens."""
        self.obter_ou_erro(campanha_id)
        self.repositorio.excluir_fisico(campanha_id)

    # ── Produtos da campanha ───────────────────────────────────────────────

    def adicionar_produto(self, campanha_id: int, dados_form) -> models.CampaignItem:
        """Adiciona um produto à campanha, com preço de divulgação opcional."""
        self.obter_ou_erro(campanha_id)
        product_id = dados_form.get("product_id")
        if not product_id:
            self.erro_requisicao("Selecione um produto")
        product_id = int(product_id)
        self.validar_pertence_a_empresa(models.Product, product_id, "Produto inválido")

        ja_existe = self.banco.query(models.CampaignItem).filter(
            models.CampaignItem.campaign_id == campanha_id,
            models.CampaignItem.product_id == product_id,
        ).first()
        if ja_existe:
            self.erro_requisicao("Esse produto já está nessa campanha")

        custom_price_raw = (dados_form.get("custom_price") or "").strip()
        custom_price = float(custom_price_raw) if custom_price_raw else None
        if custom_price is not None and custom_price <= 0:
            self.erro_requisicao("O preço de divulgação deve ser maior que zero")

        item = models.CampaignItem(
            campaign_id=campanha_id, product_id=product_id, custom_price=custom_price,
        )
        self.banco.add(item)
        self.banco.commit()
        return item

    def remover_produto(self, campanha_id: int, item_id: int):
        """Remove um produto de uma campanha."""
        item = self.banco.query(models.CampaignItem).filter(
            models.CampaignItem.id == item_id,
            models.CampaignItem.campaign_id == campanha_id,
        ).first()
        if not item:
            self.erro_nao_encontrado("Item da campanha não encontrado")
        self.banco.delete(item)
        self.banco.commit()

    def produtos_publicos(self, campanha: models.Campaign) -> List[dict]:
        """Produtos da campanha formatados para a página pública, com preço final já calculado."""
        servico_produtos = ServicoProdutos(self.banco, empresa_id=self.empresa_id)
        resultado = []
        for item in campanha.items:
            produto = item.product
            if not produto or not produto.is_active:
                continue
            preco = servico_produtos.preco_pdv(produto)
            if item.custom_price is not None:
                preco = {
                    "sale_price": float(item.custom_price),
                    "is_promo": True,
                    "original_price": float(produto.sale_price),
                }
            resultado.append({
                "id": produto.id,
                "name": produto.name,
                "image_url": produto.image_url or "",
                "category": produto.category.name if produto.category else "Outros",
                "unit": produto.unit,
                **preco,
            })
        return resultado
