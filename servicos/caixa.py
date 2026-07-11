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
from servicos.relatorio_caixa import ROTULOS_MOVIMENTO


METODOS_FECHAMENTO = [
    models.PaymentMethod.dinheiro,
    models.PaymentMethod.debito,
    models.PaymentMethod.credito,
    models.PaymentMethod.pix,
    models.PaymentMethod.fiado,
    models.PaymentMethod.vale,
]

# Tipos de movimentação que retiram dinheiro do caixa (saída).
# Despesa e Vale Funcionário são variações de sangria, categorizadas
# separadamente só para identificar o motivo no relatório.
TIPOS_SAIDA = {
    models.CashMovementType.sangria,
    models.CashMovementType.despesa,
    models.CashMovementType.vale_funcionario,
}


class ServicoCaixa(ServicoBase):
    """Regras de negócio para o caixa do PDV."""

    def __init__(self, banco: Session, current_user=None):
        super().__init__(banco, current_user)
        self.repositorio = RepositorioCaixa(banco, self.empresa_id)

    def visao_geral(self, usuario: models.User) -> dict:
        """Dados para a tela principal do caixa."""
        caixa_aberto = self.repositorio.buscar_aberto_do_usuario(usuario.id)
        historico = self.repositorio.historico_do_usuario(usuario.id)
        return {
            "open_register": caixa_aberto,
            "history": historico,
            "open_register_totals": self.totais_sistema(caixa_aberto) if caixa_aberto else {},
            "open_register_movements": self._movimentos_para_exibir(caixa_aberto) if caixa_aberto else [],
        }

    def _movimentos_para_exibir(self, caixa: models.CashRegister) -> list:
        """Lançamentos (sangria/suprimento/despesa/vale funcionário) do caixa, para exibir antes de fechar."""
        return [
            {
                "tipo": ROTULOS_MOVIMENTO.get(mv.type.value, mv.type.value),
                "motivo": mv.reason or "—",
                "valor": float(mv.amount),
                "entrada": mv.type == models.CashMovementType.suprimento,
            }
            for mv in caixa.cash_movements
        ]

    def totais_sistema(self, caixa: models.CashRegister) -> dict:
        """
        Valor que o sistema espera encontrar de cada forma de pagamento no fechamento.

        Dinheiro inclui o fundo de abertura e as sangrias/suprimentos, pois é o
        único método contado fisicamente na gaveta. As demais formas (débito,
        crédito, pix, fiado, vale) são apenas o total vendido, conferido contra
        o extrato/comprovante de cada um.
        """
        por_metodo = {metodo.value: 0.0 for metodo in METODOS_FECHAMENTO}
        for venda in caixa.sales:
            if venda.status == models.SaleStatus.finalizada:
                for pagamento in venda.payments:
                    metodo = pagamento.method.value
                    por_metodo[metodo] = por_metodo.get(metodo, 0) + float(pagamento.amount)

        suprimento = sum(
            float(m.amount) for m in caixa.cash_movements
            if m.type == models.CashMovementType.suprimento
        )
        saidas = sum(
            float(m.amount) for m in caixa.cash_movements
            if m.type in TIPOS_SAIDA
        )
        por_metodo["dinheiro"] += float(caixa.opening_balance or 0) + suprimento - saidas
        return por_metodo

    def caixas_abertos(self, usuario: models.User) -> dict:
        """Lista todos os caixas abertos no momento, numerados (001, 002, ...)."""
        if usuario.role not in (models.UserRole.admin, models.UserRole.gerente):
            self.erro_sem_permissao("Sem permissão para ver os caixas de outros operadores")

        abertos = self.repositorio.listar_abertos()
        linhas = [
            {"numero": i + 1, "register": caixa}
            for i, caixa in enumerate(abertos)
        ]
        return {"rows": linhas}

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
            company_id=self.empresa_id,
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

        sistema = self.totais_sistema(caixa)
        total_informado = 0.0
        for metodo in METODOS_FECHAMENTO:
            informado = float(dados_form.get(f"informado_{metodo.value}") or 0)
            total_informado += informado
            self.banco.add(models.CashClosingCount(
                cash_register_id=caixa.id,
                method=metodo,
                system_amount=sistema.get(metodo.value, 0),
                informed_amount=informado,
            ))

        caixa.status = models.CashRegisterStatus.fechado
        caixa.closing_balance = total_informado
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
            if m.type in TIPOS_SAIDA
        )

        # Agrupa por método de pagamento
        por_metodo = {}
        for venda in caixa.sales:
            if venda.status == models.SaleStatus.finalizada:
                for pagamento in venda.payments:
                    metodo = pagamento.method.value
                    por_metodo[metodo] = por_metodo.get(metodo, 0) + float(pagamento.amount)

        # Conferência de fechamento (sistema x informado), se o caixa já foi fechado
        conferencia = []
        for contagem in sorted(caixa.closing_counts, key=lambda c: c.method.value):
            sistema_v = float(contagem.system_amount)
            informado_v = float(contagem.informed_amount)
            conferencia.append({
                "method": contagem.method.value,
                "system": sistema_v,
                "informed": informado_v,
                "diff": informado_v - sistema_v,
            })
        conferencia_total = {
            "system": sum(c["system"] for c in conferencia),
            "informed": sum(c["informed"] for c in conferencia),
            "diff": sum(c["diff"] for c in conferencia),
        }

        return {
            "register": caixa,
            "sales_total": total_vendas,
            "cash_in": entradas,
            "cash_out": saidas,
            "by_method": por_metodo,
            "closing_counts": conferencia,
            "closing_total": conferencia_total,
        }

    def movimentacao(self, caixa_id: int, dados_form, usuario: models.User) -> models.CashMovement:
        """
        Registra uma movimentação de caixa.

        Suprimento: entrada de dinheiro no caixa
        Sangria: retirada de dinheiro do caixa (genérica)
        Despesa: retirada para pagar uma conta/compra da loja
        Vale Funcionário: retirada referente a vale de funcionário
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
