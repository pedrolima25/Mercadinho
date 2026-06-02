"""
Serviço de Caixa
================
Regras de negócio para abertura, fechamento e movimentações de caixa.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import models
from repositorios.caixa import RepositorioCaixa
from servicos.base import ServicoBase


class ServicoCaixa(ServicoBase):
    """Regras de negócio para o caixa do PDV."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.repositorio = RepositorioCaixa(banco)

    def visao_geral(self, usuario: models.User) -> dict:
        """Dados para a tela principal do caixa."""
        caixa_aberto = self.repositorio.buscar_aberto_do_usuario(usuario.id)
        historico = self.repositorio.historico_do_usuario(usuario.id)
        return {
            "open_register": caixa_aberto,
            "history": historico,
        }

    def caixa_aberto_do_usuario(self, usuario_id: int) -> Optional[models.CashRegister]:
        """Retorna o caixa aberto do usuário, ou None se não tiver."""
        return self.repositorio.buscar_aberto_do_usuario(usuario_id)

    def abrir(self, dados_form, usuario: models.User) -> models.CashRegister:
        """
        Abre o caixa para o usuário.
        Valida que não existe outro caixa aberto para o mesmo usuário.
        """
        # Verifica se já tem caixa aberto
        caixa_existente = self.repositorio.buscar_aberto_do_usuario(usuario.id)
        if caixa_existente:
            self.erro_requisicao("Você já possui um caixa aberto")

        caixa = models.CashRegister(
            user_id=usuario.id,
            opening_balance=float(dados_form.get("opening_balance") or 0),
            notes=dados_form.get("notes") or None,
        )
        self.banco.add(caixa)
        self.banco.commit()
        return caixa

    def fechar(self, dados_form, usuario: models.User) -> models.CashRegister:
        """
        Fecha o caixa do usuário.
        Registra o saldo final e o horário de fechamento.
        """
        caixa = self.repositorio.buscar_aberto_do_usuario(usuario.id)
        if not caixa:
            self.erro_requisicao("Nenhum caixa aberto para fechar")

        # Verifica permissão (admin/gerente pode fechar qualquer caixa)
        pode_fechar = (
            usuario.role in (models.UserRole.admin, models.UserRole.gerente)
            or caixa.user_id == usuario.id
        )
        if not pode_fechar:
            self.erro_sem_permissao("Sem permissão para fechar este caixa")

        caixa.status = models.CashRegisterStatus.fechado
        caixa.closing_balance = float(dados_form.get("closing_balance") or 0)
        caixa.closed_at = datetime.utcnow()
        caixa.notes = dados_form.get("notes") or caixa.notes

        self.banco.commit()
        return caixa

    def detalhe(self, caixa_id: int) -> dict:
        """Dados para a tela de detalhes de um caixa."""
        caixa = self.repositorio.buscar_com_detalhes(caixa_id)
        if not caixa:
            self.erro_nao_encontrado("Caixa não encontrado")

        # Calcula totais
        total_vendas = sum(
            float(v.total)
            for v in caixa.sales
            if v.status == models.SaleStatus.finalizada
        )
        entradas = sum(
            float(m.amount)
            for m in caixa.cash_movements
            if m.type == models.CashMovementType.suprimento
        )
        saidas = sum(
            float(m.amount)
            for m in caixa.cash_movements
            if m.type == models.CashMovementType.sangria
        )

        # Agrupa por método de pagamento
        por_metodo = {}
        for venda in caixa.sales:
            if venda.status == models.SaleStatus.finalizada:
                for pagamento in venda.payments:
                    metodo = pagamento.method.value
                    por_metodo[metodo] = por_metodo.get(metodo, 0) + float(pagamento.amount)

        return {
            "register": caixa,
            "sales_total": total_vendas,
            "cash_in": entradas,
            "cash_out": saidas,
            "by_method": por_metodo,
        }

    def movimentacao(self, caixa_id: int, dados_form, usuario: models.User) -> models.CashMovement:
        """
        Registra sangria ou suprimento de caixa.

        Sangria: retirada de dinheiro do caixa
        Suprimento: entrada de dinheiro no caixa
        """
        caixa = self.repositorio.buscar_por_id(caixa_id)
        if not caixa:
            self.erro_nao_encontrado("Caixa não encontrado")
        if caixa.status != models.CashRegisterStatus.aberto:
            self.erro_requisicao("Caixa fechado não aceita movimentações")

        # Verifica permissão
        pode_movimentar = (
            usuario.role in (models.UserRole.admin, models.UserRole.gerente)
            or caixa.user_id == usuario.id
        )
        if not pode_movimentar:
            self.erro_sem_permissao("Sem permissão para movimentar este caixa")

        valor = float(dados_form.get("amount") or 0)
        if valor <= 0:
            self.erro_requisicao("Valor inválido para movimentação")

        movimentacao = models.CashMovement(
            cash_register_id=caixa_id,
            type=models.CashMovementType(dados_form.get("type")),
            amount=valor,
            reason=dados_form.get("reason") or None,
            user_id=usuario.id,
        )
        self.banco.add(movimentacao)
        self.banco.commit()
        return movimentacao
