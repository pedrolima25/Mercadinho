"""
Serviço de Produtos
===================
Contém todas as regras de negócio relacionadas a produtos.

Responsabilidades:
- Validar dados antes de salvar
- Orquestrar criação de movimentação de estoque inicial
- Retornar dados no formato esperado pelos routers

Exemplo de uso:
    servico = ServicoProdutos(banco)
    produtos, total = servico.listar(busca="arroz", pagina=1)
    produto = servico.obter_ou_erro(produto_id=5)
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
import models
from repositorios.produtos import RepositorioProdutos
from servicos.base import ServicoBase


class ServicoProdutos(ServicoBase):
    """Regras de negócio para produtos."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        # Repositório que faz as queries no banco
        self.repositorio = RepositorioProdutos(banco)

    # ── Consultas ──────────────────────────────────────────────────────────

    def listar(
        self,
        busca: str = None,
        categoria_id: int = None,
        estoque_baixo: bool = False,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> Tuple[List[models.Product], int]:
        """
        Lista produtos com filtros e paginação.

        Returns:
            (lista_de_produtos, total_encontrado)
        """
        return self.repositorio.buscar_com_filtros(
            texto=busca,
            categoria_id=categoria_id,
            estoque_baixo=estoque_baixo,
            pagina=pagina,
            por_pagina=por_pagina,
        )

    def obter_ou_erro(self, produto_id: int) -> models.Product:
        """
        Retorna o produto ou lança HTTPException 404.

        Usado nos routers quando o produto precisa existir.
        """
        return self.obter_ou_404(
            self.repositorio, produto_id, "Produto não encontrado"
        )

    def buscar_por_codigo_barras(self, codigo: str) -> models.Product:
        """Retorna produto pelo código de barras ou lança 404."""
        produto = self.repositorio.buscar_por_codigo_barras(codigo)
        if not produto:
            self.erro_nao_encontrado(f"Produto com código '{codigo}' não encontrado")
        return produto

    def preco_pdv(self, produto: models.Product) -> dict:
        """Preço atual do produto, considerando o menor entre promoção e preço de campanha vigentes."""
        preco_normal = float(produto.sale_price)
        candidatos = []

        promo = produto.promocao_ativa()
        if promo:
            candidatos.append(float(promo.promo_price))

        preco_campanha = produto.campanha_preco_ativo()
        if preco_campanha is not None:
            candidatos.append(preco_campanha)

        if candidatos:
            return {
                "sale_price": min(candidatos),
                "is_promo": True,
                "original_price": preco_normal,
            }
        return {"sale_price": preco_normal, "is_promo": False, "original_price": preco_normal}

    def preco_efetivo(self, produto: models.Product, quantidade: float = 0) -> float:
        """
        Preço unitário final automático, usado para COBRAR a venda no PDV.
        Considera promoção, preço de campanha e a faixa de atacado vigente
        para a quantidade informada — sempre o menor valor entre os ativos.
        """
        candidatos = [float(produto.sale_price)]

        promo = produto.promocao_ativa()
        if promo:
            candidatos.append(float(promo.promo_price))

        preco_campanha = produto.campanha_preco_ativo()
        if preco_campanha is not None:
            candidatos.append(preco_campanha)

        for tier in produto.tiers_atacado_ativos():
            if quantidade >= float(tier.min_quantity):
                candidatos.append(float(tier.wholesale_price))

        return min(candidatos)

    def tiers_pdv(self, produto: models.Product) -> dict:
        """Faixas de preço por quantidade (atacado) ativas, para o PDV recalcular o preço conforme a quantidade."""
        tiers = [
            {"min_quantity": float(t.min_quantity), "price": float(t.wholesale_price)}
            for t in produto.tiers_atacado_ativos()
        ]
        return {"wholesale_tiers": tiers}

    def listar_publico(self, somente_ofertas: bool = False) -> List[dict]:
        """
        Catálogo público (sem login) para divulgação — ex: link de WhatsApp.
        Não inclui dados sensíveis como estoque ou código de barras.
        """
        produtos = self.repositorio.buscar_ativos_ordenados()
        resultado = []
        for p in produtos:
            preco = self.preco_pdv(p)
            tiers = self.tiers_pdv(p)["wholesale_tiers"]
            tem_oferta = preco["is_promo"] or bool(tiers)
            if somente_ofertas and not tem_oferta:
                continue
            resultado.append({
                "id": p.id,
                "name": p.name,
                "image_url": p.image_url or "",
                "category": p.category.name if p.category else "Outros",
                "unit": p.unit,
                "wholesale_tiers": tiers,
                "tem_oferta": tem_oferta,
                **preco,
            })
        return resultado

    def listar_para_pdv(self) -> List[dict]:
        """
        Retorna todos os produtos ativos formatados para o catálogo do PDV.
        Inclui: id, nome, preço, estoque, categoria, código de barras.
        """
        produtos = self.repositorio.buscar_ativos_ordenados()
        return [
            {
                "id": p.id,
                "barcode": p.barcode or "",
                "name": p.name,
                **self.preco_pdv(p),
                **self.tiers_pdv(p),
                "stock_quantity": float(p.stock_quantity),
                "unit": p.unit,
                "category": p.category.name if p.category else "Sem categoria",
                "image_url": p.image_url or "",
            }
            for p in produtos
        ]

    def buscar_rapido(self, texto: str) -> List[dict]:
        """Busca rápida para autocomplete do PDV."""
        produtos = self.repositorio.buscar_por_texto_rapido(texto)
        return [
            {
                "id": p.id,
                "barcode": p.barcode,
                "name": p.name,
                **self.preco_pdv(p),
                **self.tiers_pdv(p),
                "stock_quantity": float(p.stock_quantity),
                "unit": p.unit,
                "image_url": p.image_url or "",
            }
            for p in produtos
        ]

    # ── Criação e edição ───────────────────────────────────────────────────

    def cadastrar(self, dados_form, usuario: models.User) -> models.Product:
        """
        Cadastra um novo produto com validações.

        Validações:
        ✓ Nome obrigatório
        ✓ Preço de venda não pode ser negativo
        ✓ Código de barras único (se informado)

        Args:
            dados_form: Objeto do formulário (request.form())
            usuario: Usuário que está cadastrando

        Returns:
            Produto criado

        Raises:
            HTTPException 400: Se alguma validação falhar
        """
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("O nome do produto é obrigatório")

        preco_venda = float(dados_form.get("sale_price") or 0)
        if preco_venda < 0:
            self.erro_requisicao("O preço de venda não pode ser negativo")

        codigo_barras = dados_form.get("barcode") or None
        if codigo_barras and self.repositorio.codigo_barras_ja_existe(codigo_barras):
            self.erro_requisicao(f"Código de barras '{codigo_barras}' já está em uso")

        # Cria o produto
        produto = models.Product(
            barcode=codigo_barras,
            name=nome,
            description=dados_form.get("description") or None,
            category_id=int(dados_form.get("category_id")) if dados_form.get("category_id") else None,
            brand_id=int(dados_form.get("brand_id")) if dados_form.get("brand_id") else None,
            supplier_id=int(dados_form.get("supplier_id")) if dados_form.get("supplier_id") else None,
            cost_price=float(dados_form.get("cost_price") or 0),
            sale_price=preco_venda,
            stock_quantity=float(dados_form.get("stock_quantity") or 0),
            min_stock=float(dados_form.get("min_stock") or 0),
            unit=dados_form.get("unit", "UN"),
            ncm=dados_form.get("ncm") or None,
            cest=dados_form.get("cest") or None,
            cfop=dados_form.get("cfop") or None,
            origin=dados_form.get("origin") or "0",
            cst_csosn=dados_form.get("cst_csosn") or None,
            icms_rate=float(dados_form.get("icms_rate") or 0),
            pis_rate=float(dados_form.get("pis_rate") or 0),
            cofins_rate=float(dados_form.get("cofins_rate") or 0),
            tax_notes=dados_form.get("tax_notes") or None,
            is_active=dados_form.get("is_active") == "on",
        )
        self.banco.add(produto)
        self.banco.commit()

        # Registra movimentação de estoque inicial se houver quantidade
        estoque_inicial = float(dados_form.get("stock_quantity") or 0)
        if estoque_inicial > 0:
            movimentacao = models.StockMovement(
                product_id=produto.id,
                type=models.MovementType.entrada,
                quantity=estoque_inicial,
                reason="Estoque inicial",
                user_id=usuario.id,
            )
            self.banco.add(movimentacao)
            self.banco.commit()

        return produto

    def atualizar(self, produto_id: int, dados_form, usuario: models.User) -> models.Product:
        """
        Atualiza os dados de um produto existente.

        Validações:
        ✓ Produto deve existir
        ✓ Código de barras único (exceto o próprio produto)
        """
        produto = self.obter_ou_erro(produto_id)

        # Valida código de barras duplicado
        codigo_barras = dados_form.get("barcode") or None
        if codigo_barras and self.repositorio.codigo_barras_ja_existe(codigo_barras, exceto_id=produto_id):
            self.erro_requisicao(f"Código de barras '{codigo_barras}' já está em uso por outro produto")

        # Atualiza os campos
        produto.barcode = codigo_barras
        produto.name = dados_form.get("name")
        produto.description = dados_form.get("description") or None
        produto.category_id = int(dados_form.get("category_id")) if dados_form.get("category_id") else None
        produto.brand_id = int(dados_form.get("brand_id")) if dados_form.get("brand_id") else None
        produto.supplier_id = int(dados_form.get("supplier_id")) if dados_form.get("supplier_id") else None
        produto.cost_price = float(dados_form.get("cost_price") or 0)
        produto.sale_price = float(dados_form.get("sale_price") or 0)
        produto.min_stock = float(dados_form.get("min_stock") or 0)
        produto.unit = dados_form.get("unit", "UN")
        produto.ncm = dados_form.get("ncm") or None
        produto.cest = dados_form.get("cest") or None
        produto.cfop = dados_form.get("cfop") or None
        produto.origin = dados_form.get("origin") or "0"
        produto.cst_csosn = dados_form.get("cst_csosn") or None
        produto.icms_rate = float(dados_form.get("icms_rate") or 0)
        produto.pis_rate = float(dados_form.get("pis_rate") or 0)
        produto.cofins_rate = float(dados_form.get("cofins_rate") or 0)
        produto.tax_notes = dados_form.get("tax_notes") or None
        produto.is_active = dados_form.get("is_active") == "on"

        self.banco.commit()
        return produto

    def excluir(self, produto_id: int, usuario: models.User):
        """Desativa o produto (soft delete — mantém histórico de vendas)."""
        produto = self.obter_ou_erro(produto_id)
        produto.is_active = False
        self.banco.commit()
