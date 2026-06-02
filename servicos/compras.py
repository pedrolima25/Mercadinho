"""
Serviço de Compras
==================
Regras de negócio para pedidos de compra a fornecedores.

Fluxo principal:
1. Criar pedido (status: pendente)
2. Receber mercadoria → atualiza estoque + gera conta a pagar
3. Cancelar pedido (se ainda pendente)
"""

from datetime import date
from typing import List, Tuple
from sqlalchemy.orm import Session
import models
from repositorios.compras import RepositorioCompras
from servicos.base import ServicoBase


class ServicoCompras(ServicoBase):
    """Regras de negócio para compras de fornecedores."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.repositorio = RepositorioCompras(banco)

    def listar(
        self, status: str = None, pagina: int = 1
    ) -> Tuple[List[models.Purchase], int]:
        """Lista compras com filtro e paginação."""
        return self.repositorio.listar_com_filtros(status=status, pagina=pagina)

    def obter_ou_erro(self, compra_id: int) -> models.Purchase:
        """Retorna compra com dados completos ou lança 404."""
        compra = self.repositorio.buscar_com_itens(compra_id)
        if not compra:
            self.erro_nao_encontrado("Compra não encontrada")
        return compra

    def criar(self, dados_form, usuario: models.User) -> models.Purchase:
        """
        Cria novo pedido de compra.

        Valida que há pelo menos um item antes de salvar.
        """
        produto_ids = dados_form.getlist("product_id[]")
        quantidades = dados_form.getlist("quantity[]")
        custos_unitarios = dados_form.getlist("unit_cost[]")

        if not produto_ids:
            self.erro_requisicao("Adicione pelo menos um produto à compra")

        # Calcula total da compra
        total = sum(
            float(q) * float(c)
            for q, c in zip(quantidades, custos_unitarios)
        )

        # Cria o cabeçalho da compra
        compra = models.Purchase(
            supplier_id=int(dados_form.get("supplier_id")) if dados_form.get("supplier_id") else None,
            user_id=usuario.id,
            invoice_number=dados_form.get("invoice_number") or None,
            notes=dados_form.get("notes") or None,
            expected_date=dados_form.get("expected_date") or None,
            total=total,
        )
        self.banco.add(compra)
        self.banco.flush()  # Obtém o ID gerado antes de criar os itens

        # Cria os itens da compra
        for pid, qty, custo in zip(produto_ids, quantidades, custos_unitarios):
            item = models.PurchaseItem(
                purchase_id=compra.id,
                product_id=int(pid),
                quantity=float(qty),
                unit_cost=float(custo),
                total=float(qty) * float(custo),
            )
            self.banco.add(item)

        self.banco.commit()
        return compra

    def receber(self, compra_id: int, usuario: models.User) -> models.Purchase:
        """
        Marca a compra como recebida.

        Efeitos:
        - Atualiza o estoque de cada produto
        - Registra movimentação de entrada no estoque
        - Gera conta a pagar automaticamente
        """
        compra = self.obter_ou_erro(compra_id)

        if compra.status != models.PurchaseStatus.pendente:
            self.erro_requisicao("Somente compras pendentes podem ser recebidas")

        # Atualiza status e data de recebimento
        compra.status = models.PurchaseStatus.recebida
        compra.received_date = date.today()

        # Atualiza estoque de cada item
        for item in compra.items:
            produto = self.banco.query(models.Product).filter(
                models.Product.id == item.product_id
            ).first()

            if produto:
                # Adiciona quantidade ao estoque
                produto.stock_quantity = float(produto.stock_quantity) + float(item.quantity)

                # Atualiza preço de custo se informado
                if float(item.unit_cost) > 0:
                    produto.cost_price = float(item.unit_cost)

                # Registra movimentação de entrada
                movimentacao = models.StockMovement(
                    product_id=item.product_id,
                    type=models.MovementType.entrada,
                    quantity=float(item.quantity),
                    reason=f"Compra #{compra_id}",
                    reference_id=compra_id,
                    reference_type="purchase",
                    user_id=usuario.id,
                )
                self.banco.add(movimentacao)

        # Gera conta a pagar se houver valor
        if float(compra.total or 0) > 0:
            conta_pagar = models.AccountPayable(
                supplier_id=compra.supplier_id,
                description=f"Compra #{compra.id}",
                amount=float(compra.total),
                due_date=compra.expected_date or date.today(),
                notes=compra.invoice_number and f"NF/Documento: {compra.invoice_number}",
            )
            self.banco.add(conta_pagar)

        self.banco.commit()
        return compra

    def cancelar(self, compra_id: int) -> models.Purchase:
        """Cancela uma compra (somente se ainda pendente)."""
        compra = self.obter_ou_erro(compra_id)
        if compra.status != models.PurchaseStatus.pendente:
            self.erro_requisicao("Somente compras pendentes podem ser canceladas")
        compra.status = models.PurchaseStatus.cancelada
        self.banco.commit()
        return compra
