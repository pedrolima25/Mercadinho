"""
Serviço Financeiro
==================
Regras de negócio para contas a pagar, contas a receber e despesas.
"""

from datetime import date
from typing import List, Tuple
from sqlalchemy.orm import Session
import models
from repositorios.financeiro import (
    RepositorioContasPagar,
    RepositorioContasReceber,
    RepositorioDespesas,
)
from servicos.base import ServicoBase


class ServicoFinanceiro(ServicoBase):
    """Regras de negócio para o módulo financeiro."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.contas_pagar = RepositorioContasPagar(banco)
        self.contas_receber = RepositorioContasReceber(banco)
        self.despesas = RepositorioDespesas(banco)

    # ── Visão geral ────────────────────────────────────────────────────────

    def visao_geral(self) -> dict:
        """
        Dados para o dashboard financeiro.

        Returns:
            Resumo de valores pendentes, vencidos e despesas do mês.
        """
        hoje = date.today()
        return {
            "overdue_pay": self.contas_pagar.total_vencido(hoje),
            "pending_pay": self.contas_pagar.total_pendente(hoje),
            "pending_rec": self.contas_receber.total_pendente(),
            "month_expense": self.despesas.total_no_mes(hoje.month, hoje.year),
            "recent_payable": self.contas_pagar.listar_pendentes_proximas(10),
            "recent_receivable": self.contas_receber.listar_pendentes_proximas(10),
            "today": hoje.isoformat(),
        }

    # ── Contas a Pagar ─────────────────────────────────────────────────────

    def listar_contas_pagar(self, status: str = None, pagina: int = 1):
        """Lista contas a pagar com filtros."""
        return self.contas_pagar.listar_com_filtros(status=status, pagina=pagina)

    def criar_conta_pagar(self, dados_form) -> models.AccountPayable:
        """Cria nova conta a pagar."""
        return self.contas_pagar.criar({
            "supplier_id": int(dados_form.get("supplier_id")) if dados_form.get("supplier_id") else None,
            "description": dados_form.get("description"),
            "amount": float(dados_form.get("amount")),
            "due_date": dados_form.get("due_date"),
            "notes": dados_form.get("notes") or None,
        })

    def pagar_conta(self, conta_id: int, dados_form) -> models.AccountPayable:
        """Registra pagamento de uma conta."""
        conta = self.obter_ou_404(self.contas_pagar, conta_id, "Conta não encontrada")
        conta.paid_date = dados_form.get("paid_date") or date.today()
        conta.paid_amount = float(dados_form.get("paid_amount") or conta.amount)
        conta.status = models.AccountStatus.pago
        self.banco.commit()
        return conta

    def cancelar_conta_pagar(self, conta_id: int) -> models.AccountPayable:
        """Cancela uma conta a pagar."""
        conta = self.obter_ou_404(self.contas_pagar, conta_id, "Conta não encontrada")
        conta.status = models.AccountStatus.cancelado
        self.banco.commit()
        return conta

    # ── Contas a Receber ───────────────────────────────────────────────────

    def listar_contas_receber(self, status: str = None, pagina: int = 1):
        """Lista contas a receber com filtros."""
        return self.contas_receber.listar_com_filtros(status=status, pagina=pagina)

    def criar_conta_receber(self, dados_form) -> models.AccountReceivable:
        """Cria nova conta a receber."""
        return self.contas_receber.criar({
            "customer_id": int(dados_form.get("customer_id")) if dados_form.get("customer_id") else None,
            "description": dados_form.get("description"),
            "amount": float(dados_form.get("amount")),
            "due_date": dados_form.get("due_date"),
            "notes": dados_form.get("notes") or None,
        })

    def receber_conta(self, conta_id: int, dados_form) -> models.AccountReceivable:
        """Registra recebimento de uma conta. Atualiza saldo do cliente se fiado."""
        conta = self.obter_ou_404(self.contas_receber, conta_id, "Conta não encontrada")
        conta.paid_date = dados_form.get("paid_date") or date.today()
        conta.paid_amount = float(dados_form.get("paid_amount") or conta.amount)
        conta.status = models.AccountStatus.pago

        # Reduz o saldo devedor do cliente (para vendas fiado)
        if conta.customer_id:
            cliente = self.banco.query(models.Customer).filter(
                models.Customer.id == conta.customer_id
            ).first()
            if cliente:
                cliente.balance = max(0, float(cliente.balance) - float(conta.paid_amount))

        self.banco.commit()
        return conta

    # ── Despesas ───────────────────────────────────────────────────────────

    def listar_despesas(self, pagina: int = 1):
        """Lista despesas paginadas."""
        return self.despesas.listar_paginado(pagina=pagina)

    def criar_despesa(self, dados_form, usuario: models.User) -> models.Expense:
        """Cria nova despesa operacional."""
        return self.despesas.criar({
            "description": dados_form.get("description"),
            "category": dados_form.get("category") or None,
            "amount": float(dados_form.get("amount")),
            "date": dados_form.get("date"),
            "notes": dados_form.get("notes") or None,
            "user_id": usuario.id,
        })

    def excluir_despesa(self, despesa_id: int):
        """Remove uma despesa definitivamente."""
        self.despesas.excluir_fisico(despesa_id)
