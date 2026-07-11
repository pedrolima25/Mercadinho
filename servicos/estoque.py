"""
Serviço de Estoque
==================
Regras de negócio para movimentações de estoque e lotes.
"""

from datetime import date, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
import models
from repositorios.estoque import RepositorioMovimentacoes, RepositorioLotes
from repositorios.produtos import RepositorioProdutos
from servicos.base import ServicoBase


class ServicoEstoque(ServicoBase):
    """Regras de negócio para controle de estoque."""

    def __init__(self, banco: Session, current_user=None):
        super().__init__(banco, current_user)
        self.movimentacoes = RepositorioMovimentacoes(banco, self.empresa_id)
        self.lotes = RepositorioLotes(banco, self.empresa_id)
        self.produtos = RepositorioProdutos(banco, self.empresa_id)

    def visao_geral(self) -> dict:
        """
        Dados para a tela principal de estoque.

        Returns:
            {
                "estoque_baixo": [...produtos abaixo do mínimo],
                "proximos_a_vencer": [...lotes com validade próxima],
                "movimentacoes_recentes": [...últimas 30 movimentações]
            }
        """
        hoje = date.today()
        data_alerta = (hoje + timedelta(days=30)).isoformat()

        return {
            "low_stock": self.produtos.com_estoque_baixo(),
            "expiring": self.lotes.proximos_a_vencer(),
            "movements": self.movimentacoes.listar_recentes(30),
            # Data limite para alertas de validade (usada no template)
            "now_date": hoje.isoformat(),
            "near_date": data_alerta,
        }

    def registrar_movimentacao(self, dados_form, usuario: models.User) -> models.StockMovement:
        """
        Registra entrada, saída ou ajuste de estoque.

        Validações:
        ✓ Produto deve existir
        ✓ Quantidade válida (não negativa para entrada/saída)
        ✓ Estoque suficiente para saída
        """
        produto_id = int(dados_form.get("product_id"))
        quantidade = float(dados_form.get("quantity", 0))
        tipo = dados_form.get("type")
        motivo = dados_form.get("reason") or None

        # Valida quantidade
        if quantidade < 0 or (tipo != "ajuste" and quantidade <= 0):
            self.erro_requisicao("Quantidade inválida")

        # Busca produto
        produto = self.produtos.buscar_por_id(produto_id)
        if not produto:
            self.erro_nao_encontrado("Produto não encontrado")

        # Aplica a movimentação no estoque
        if tipo == "entrada":
            produto.stock_quantity = float(produto.stock_quantity) + quantidade
        elif tipo in ("saida", "perda"):
            if float(produto.stock_quantity) < quantidade:
                self.erro_requisicao(
                    f"Estoque insuficiente. Disponível: {float(produto.stock_quantity):.3f} {produto.unit}"
                )
            produto.stock_quantity = float(produto.stock_quantity) - quantidade
        elif tipo == "ajuste":
            # No ajuste, a quantidade informada é o novo saldo
            produto.stock_quantity = quantidade
        else:
            self.erro_requisicao("Tipo de movimentação inválido")

        # Registra a movimentação no histórico
        movimentacao = models.StockMovement(
            product_id=produto_id,
            type=models.MovementType(tipo),
            quantity=quantidade,
            reason=motivo,
            user_id=usuario.id,
            company_id=self.empresa_id,
        )
        self.banco.add(movimentacao)
        self.banco.commit()
        return movimentacao

    def historico(
        self,
        produto_id: int = None,
        tipo: str = None,
        pagina: int = 1,
    ) -> Tuple[List[models.StockMovement], int]:
        """Histórico de movimentações com filtros."""
        return self.movimentacoes.listar_com_filtros(
            produto_id=produto_id,
            tipo=tipo,
            pagina=pagina,
        )

    def listar_lotes(self) -> dict:
        """Dados para a tela de lotes."""
        hoje = date.today()
        return {
            "batches": self.lotes.listar_todos(),
            "products": self.produtos.buscar_ativos_ordenados(),
            "now_date": hoje.isoformat(),
            "near_date": (hoje + timedelta(days=30)).isoformat(),
        }

    def criar_lote(self, dados_form) -> models.ProductBatch:
        """Cria novo lote de produto."""
        produto_id = int(dados_form.get("product_id"))
        self.validar_pertence_a_empresa(models.Product, produto_id, "Produto inválido")
        lote = models.ProductBatch(
            product_id=produto_id,
            batch_number=dados_form.get("batch_number") or None,
            quantity=float(dados_form.get("quantity") or 0),
            expiry_date=dados_form.get("expiry_date") or None,
            company_id=self.empresa_id,
        )
        self.banco.add(lote)
        self.banco.commit()
        return lote

    def registrar_perda_lote(self, lote_id: int, dados_form, usuario: models.User) -> models.StockMovement:
        """
        Dá baixa (perda) de um lote — usado pra vencido ou avaria vinculados a um lote.
        Desconta a quantidade do estoque do produto e do próprio lote.
        """
        lote = self.lotes.buscar_por_id(lote_id)
        if not lote:
            self.erro_nao_encontrado("Lote não encontrado")

        motivo = dados_form.get("reason") or "Vencido"
        quantidade = float(dados_form.get("quantity") or lote.quantity or 0)

        if quantidade <= 0:
            self.erro_requisicao("Quantidade inválida")
        if quantidade > float(lote.quantity):
            self.erro_requisicao(
                f"Quantidade maior que o saldo do lote. Disponível: {float(lote.quantity):.3f}"
            )

        produto = self.produtos.buscar_por_id(lote.product_id)
        if not produto:
            self.erro_nao_encontrado("Produto do lote não encontrado")
        if float(produto.stock_quantity) < quantidade:
            self.erro_requisicao(
                f"Estoque insuficiente. Disponível: {float(produto.stock_quantity):.3f} {produto.unit}"
            )

        produto.stock_quantity = float(produto.stock_quantity) - quantidade
        lote.quantity = float(lote.quantity) - quantidade

        movimentacao = models.StockMovement(
            product_id=produto.id,
            type=models.MovementType.perda,
            quantity=quantidade,
            reason=f"{motivo} (Lote {lote.batch_number or lote.id})",
            reference_id=lote.id,
            reference_type="lote",
            user_id=usuario.id,
            company_id=self.empresa_id,
        )
        self.banco.add(movimentacao)
        self.banco.commit()
        return movimentacao
