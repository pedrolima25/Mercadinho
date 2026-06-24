"""
Serviço de Vendas
=================
Regras de negócio para listagem, cancelamento e devoluções de vendas.
A lógica de FINALIZAR a venda (PDV) fica no ServiçoPDV.
"""

from datetime import date
from typing import List, Tuple
from sqlalchemy.orm import Session
import models
from repositorios.vendas import RepositorioVendas
from servicos.base import ServicoBase
from servicos.produtos import ServicoProdutos


class ServicoVendas(ServicoBase):
    """Regras de negócio para gestão de vendas."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.repositorio = RepositorioVendas(banco)

    def listar(
        self,
        data_inicio: str = None,
        data_fim: str = None,
        status: str = None,
        pagina: int = 1,
    ) -> Tuple[List[models.Sale], int]:
        """Lista vendas com filtros."""
        return self.repositorio.listar_com_filtros(
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status,
            pagina=pagina,
        )

    def obter_ou_erro(self, venda_id: int) -> models.Sale:
        """Retorna venda com todos os detalhes ou lança 404."""
        venda = self.repositorio.buscar_com_detalhes(venda_id)
        if not venda:
            self.erro_nao_encontrado("Venda não encontrada")
        return venda

    def cancelar(self, venda_id: int, usuario: models.User) -> models.Sale:
        """
        Cancela uma venda finalizada.

        Efeitos:
        - Devolve estoque de cada item
        - Cancela contas a receber de fiado
        - Reduz saldo devedor do cliente (se fiado)
        """
        venda = self.obter_ou_erro(venda_id)
        if venda.status != models.SaleStatus.finalizada:
            self.erro_requisicao("Somente vendas finalizadas podem ser canceladas")

        venda.status = models.SaleStatus.cancelada

        # Devolve o estoque de cada item vendido
        for item in venda.items:
            produto = self.banco.query(models.Product).filter(
                models.Product.id == item.product_id
            ).first()
            if produto:
                produto.stock_quantity = float(produto.stock_quantity) + float(item.quantity)
                # Registra movimentação de entrada no estoque
                movimentacao = models.StockMovement(
                    product_id=item.product_id,
                    type=models.MovementType.entrada,
                    quantity=float(item.quantity),
                    reason=f"Cancelamento venda #{venda_id}",
                    user_id=usuario.id,
                )
                self.banco.add(movimentacao)

        # Cancela registros de fiado
        for pagamento in venda.payments:
            if pagamento.method == models.PaymentMethod.fiado and venda.customer_id:
                cliente = self.banco.query(models.Customer).filter(
                    models.Customer.id == venda.customer_id
                ).first()
                if cliente:
                    cliente.balance = max(0, float(cliente.balance) - float(pagamento.amount))

                # Cancela a conta a receber gerada pelo fiado
                conta = self.banco.query(models.AccountReceivable).filter(
                    models.AccountReceivable.customer_id == venda.customer_id,
                    models.AccountReceivable.description == f"Fiado - Venda #{venda.id}",
                    models.AccountReceivable.status == models.AccountStatus.pendente,
                ).first()
                if conta:
                    conta.status = models.AccountStatus.cancelado

        self.banco.commit()
        return venda

    def devolver(self, venda_id: int, dados_form, usuario: models.User) -> models.SaleReturn:
        """
        Registra devolução de itens de uma venda.

        Permite devolução parcial (só alguns itens ou quantidade menor).
        Valida que não devolve mais do que foi vendido.
        """
        venda = self.obter_ou_erro(venda_id)
        if venda.status != models.SaleStatus.finalizada:
            self.erro_requisicao("Somente vendas finalizadas podem ter devoluções")

        # Calcula quantidade já devolvida por item
        ja_devolvido: dict[int, float] = {}
        for devolucao in venda.returns:
            if devolucao.status == models.ReturnStatus.processada:
                for item_dev in devolucao.items:
                    ja_devolvido[item_dev.sale_item_id] = (
                        ja_devolvido.get(item_dev.sale_item_id, 0.0) + float(item_dev.quantity)
                    )

        # Cria o cabeçalho da devolução
        devolucao = models.SaleReturn(
            sale_id=venda_id,
            user_id=usuario.id,
            type=models.ReturnType(dados_form.get("type", "reembolso")),
            reason=dados_form.get("reason", "").strip(),
            notes=dados_form.get("notes") or None,
            total=0,
        )
        if not devolucao.reason:
            self.erro_requisicao("Informe o motivo da devolução")

        self.banco.add(devolucao)
        self.banco.flush()  # Obtém o ID antes de criar os itens

        total_devolvido = 0.0
        for item in venda.items:
            # Lê a quantidade informada no formulário para este item
            qty_str = dados_form.get(f"qty_{item.id}", "0")
            try:
                quantidade = float(qty_str)
            except (ValueError, TypeError):
                quantidade = 0.0

            if quantidade <= 0:
                continue  # Item não selecionado para devolução

            # Limita à quantidade disponível para devolução
            disponivel = float(item.quantity) - ja_devolvido.get(item.id, 0.0)
            quantidade = min(quantidade, disponivel)
            if quantidade <= 0:
                continue

            total_linha = round(quantidade * float(item.unit_price), 2)

            # Cria o item de devolução
            item_dev = models.SaleReturnItem(
                return_id=devolucao.id,
                sale_item_id=item.id,
                product_id=item.product_id,
                quantity=quantidade,
                unit_price=float(item.unit_price),
                total=total_linha,
            )
            self.banco.add(item_dev)
            total_devolvido += total_linha

            # Repõe o estoque do produto devolvido
            produto = self.banco.query(models.Product).filter(
                models.Product.id == item.product_id
            ).first()
            if produto:
                produto.stock_quantity = float(produto.stock_quantity) + quantidade
                # Registra a movimentação de entrada
                movimentacao = models.StockMovement(
                    product_id=item.product_id,
                    type=models.MovementType.entrada,
                    quantity=quantidade,
                    reason=f"Devolução #{devolucao.id} - Venda #{venda_id}",
                    reference_id=devolucao.id,
                    reference_type="return",
                    user_id=usuario.id,
                )
                self.banco.add(movimentacao)

        # Valida que pelo menos um item foi devolvido
        if total_devolvido == 0:
            self.banco.rollback()
            self.erro_requisicao("Nenhum item válido selecionado para devolução")

        devolucao.total = total_devolvido
        self.banco.commit()
        return devolucao

    def quantidade_devolvida_por_item(self, venda: models.Sale) -> dict:
        """
        Calcula a quantidade já devolvida por item da venda.
        Usado no formulário de devolução para mostrar o disponível.

        Returns:
            {sale_item_id: quantidade_ja_devolvida}
        """
        ja_devolvido = {}
        for devolucao in venda.returns:
            if devolucao.status == models.ReturnStatus.processada:
                for item_dev in devolucao.items:
                    ja_devolvido[item_dev.sale_item_id] = (
                        ja_devolvido.get(item_dev.sale_item_id, 0.0) + float(item_dev.quantity)
                    )
        return ja_devolvido


class ServicoPDV(ServicoBase):
    """
    Regras de negócio do PDV (Ponto de Venda).

    Responsável pela lógica de finalização de vendas:
    - Validar itens e estoque
    - Processar pagamentos (incluindo fiado)
    - Atualizar estoque
    - Gerar contas a receber para fiado
    """

    def __init__(self, banco: Session):
        super().__init__(banco)

    def pagina_pdv(self, usuario: models.User) -> dict:
        """Dados para renderizar o PDV."""
        # Caixa aberto do operador
        caixa_aberto = self.banco.query(models.CashRegister).filter(
            models.CashRegister.user_id == usuario.id,
            models.CashRegister.status == models.CashRegisterStatus.aberto,
        ).first()

        # Clientes ativos (para seleção no PDV)
        clientes = (
            self.banco.query(models.Customer)
            .filter(models.Customer.is_active == True)
            .order_by(models.Customer.name)
            .all()
        )

        # Número do caixa = posição entre os caixas abertos no momento (001, 002, ...)
        caixa_numero = 1
        if caixa_aberto:
            ids_abertos = [
                id_
                for id_, in self.banco.query(models.CashRegister.id)
                .filter(models.CashRegister.status == models.CashRegisterStatus.aberto)
                .order_by(models.CashRegister.opened_at.asc(), models.CashRegister.id.asc())
                .all()
            ]
            if caixa_aberto.id in ids_abertos:
                caixa_numero = ids_abertos.index(caixa_aberto.id) + 1

        return {"open_register": caixa_aberto, "customers": clientes, "caixa_numero": caixa_numero}

    def finalizar_venda(self, dados: dict, usuario: models.User) -> dict:
        """
        Finaliza uma venda no PDV.

        Fluxo:
        1. Valida dados recebidos do frontend
        2. Valida estoque de cada produto
        3. Calcula totais
        4. Valida pagamentos
        5. Cria venda, itens e pagamentos
        6. Atualiza estoque
        7. Processa fiado (se houver)

        Args:
            dados: JSON enviado pelo frontend do PDV
            usuario: Operador logado

        Returns:
            {"success": True, "sale_id": ..., "troco": ..., "customer_name": ...}
        """
        from datetime import datetime

        itens_dados = dados.get("items", []) or []
        pagamentos_dados = dados.get("payments", []) or []
        cliente_id = dados.get("customer_id")
        desconto = float(dados.get("discount", 0))

        # ── Validações básicas ─────────────────────────────────────────────
        if not itens_dados:
            self.erro_requisicao("Carrinho vazio")
        if not pagamentos_dados:
            self.erro_requisicao("Informe ao menos uma forma de pagamento")
        if desconto < 0:
            self.erro_requisicao("Desconto inválido")

        # Verifica se tem caixa aberto
        caixa_aberto = self.banco.query(models.CashRegister).filter(
            models.CashRegister.user_id == usuario.id,
            models.CashRegister.status == models.CashRegisterStatus.aberto,
        ).first()
        if not caixa_aberto:
            self.erro_requisicao("Abra o caixa antes de finalizar a venda")

        # ── Valida cliente (se informado) ──────────────────────────────────
        cliente = None
        if cliente_id:
            cliente = self.banco.query(models.Customer).filter(
                models.Customer.id == int(cliente_id),
                models.Customer.is_active == True,
            ).first()
            if not cliente:
                self.erro_requisicao("Cliente inválido ou inativo")

        # ── Valida e calcula itens ─────────────────────────────────────────
        servico_produtos = ServicoProdutos(self.banco)
        produtos_por_id = {}
        qtd_por_produto = {}
        itens_validados = []
        subtotal = 0.0
        desconto_itens = 0.0

        for item_dado in itens_dados:
            try:
                produto_id = int(item_dado["product_id"])
                quantidade = float(item_dado["quantity"])
                desconto_item = float(item_dado.get("discount", 0) or 0)
            except (KeyError, TypeError, ValueError):
                self.erro_requisicao("Item inválido no carrinho")

            if quantidade <= 0 or desconto_item < 0:
                self.erro_requisicao("Quantidade ou desconto inválido")

            # Busca produto (com cache para não consultar duas vezes)
            produto = produtos_por_id.get(produto_id)
            if not produto:
                produto = self.banco.query(models.Product).filter(
                    models.Product.id == produto_id,
                    models.Product.is_active == True,
                ).first()
                if not produto:
                    self.erro_requisicao("Produto inválido ou inativo")
                produtos_por_id[produto_id] = produto

            preco_unitario = servico_produtos.preco_efetivo(produto, quantidade)
            linha_subtotal = quantidade * preco_unitario

            if desconto_item > linha_subtotal:
                self.erro_requisicao(f"Desconto maior que o valor do item: {produto.name}")

            subtotal += linha_subtotal
            desconto_itens += desconto_item
            qtd_por_produto[produto_id] = qtd_por_produto.get(produto_id, 0.0) + quantidade
            itens_validados.append((produto, quantidade, preco_unitario, desconto_item, linha_subtotal - desconto_item))

        # Verifica estoque de cada produto
        for produto_id, quantidade_solicitada in qtd_por_produto.items():
            produto = produtos_por_id[produto_id]
            if float(produto.stock_quantity) < quantidade_solicitada:
                self.erro_requisicao(
                    f"Estoque insuficiente para {produto.name}. "
                    f"Disponível: {float(produto.stock_quantity):.3f} {produto.unit}"
                )

        # Calcula total final
        total = max(0, subtotal - desconto_itens - desconto)

        # ── Valida pagamentos ──────────────────────────────────────────────
        pagamentos_validados = []
        valor_fiado = 0.0

        for pag_dado in pagamentos_dados:
            try:
                metodo = models.PaymentMethod(pag_dado["method"])
                valor = float(pag_dado["amount"])
            except (KeyError, TypeError, ValueError):
                self.erro_requisicao("Pagamento inválido")

            if valor <= 0:
                self.erro_requisicao("Valor de pagamento inválido")

            if metodo == models.PaymentMethod.fiado:
                if not cliente:
                    self.erro_requisicao("Venda fiado exige cliente selecionado")
                valor_fiado += valor

            pagamentos_validados.append((metodo, valor))

        # Verifica limite de fiado do cliente
        if cliente and valor_fiado:
            saldo_projetado = float(cliente.balance) + valor_fiado
            if saldo_projetado > float(cliente.credit_limit):
                self.erro_requisicao("Limite de fiado do cliente excedido")

        # Verifica se total pago cobre o valor da venda
        total_pago = sum(valor for _, valor in pagamentos_validados)
        if total_pago < total:
            self.erro_requisicao("Pagamento insuficiente")

        # ── Cria a venda ───────────────────────────────────────────────────
        venda = models.Sale(
            cash_register_id=caixa_aberto.id,
            customer_id=cliente.id if cliente else None,
            user_id=usuario.id,
            subtotal=subtotal,
            discount=desconto,
            total=total,
            status=models.SaleStatus.finalizada,
            finalized_at=datetime.utcnow(),
        )
        self.banco.add(venda)
        self.banco.flush()  # Obtém o ID da venda antes de criar os itens

        # Cria itens e atualiza estoque
        for produto, quantidade, preco_unitario, desconto_item, total_item in itens_validados:
            item_venda = models.SaleItem(
                sale_id=venda.id,
                product_id=produto.id,
                quantity=quantidade,
                unit_price=preco_unitario,
                discount=desconto_item,
                total=total_item,
            )
            self.banco.add(item_venda)

            # Baixa do estoque
            produto.stock_quantity = float(produto.stock_quantity) - quantidade

            # Registra movimentação de saída no estoque
            movimentacao = models.StockMovement(
                product_id=produto.id,
                type=models.MovementType.saida,
                quantity=quantidade,
                reason=f"Venda #{venda.id}",
                reference_id=venda.id,
                reference_type="sale",
                user_id=usuario.id,
            )
            self.banco.add(movimentacao)

        # Cria os pagamentos
        for metodo, valor in pagamentos_validados:
            pagamento = models.Payment(sale_id=venda.id, method=metodo, amount=valor)
            self.banco.add(pagamento)

            # Para fiado: atualiza saldo e gera conta a receber
            if metodo == models.PaymentMethod.fiado and cliente:
                cliente.balance = float(cliente.balance) + valor
                conta_receber = models.AccountReceivable(
                    customer_id=cliente.id,
                    description=f"Fiado - Venda #{venda.id}",
                    amount=valor,
                    due_date=date.today(),
                )
                self.banco.add(conta_receber)

        self.banco.commit()

        # Retorna dados para o frontend
        troco = total_pago - total
        return {
            "success": True,
            "sale_id": venda.id,
            "troco": troco,
            "customer_name": cliente.name if cliente else "",
        }

    def verificar_supervisor(self, dados: dict) -> dict:
        """
        Verifica se as credenciais pertencem a um supervisor (admin ou gerente).
        Usado para autorizar descontos acima do limite no PDV.
        """
        import auth as auth_utils

        username = (dados.get("username") or "").strip()
        senha = dados.get("password") or ""

        if not username or not senha:
            return {"ok": False, "error": "Informe usuário e senha"}

        usuario = self.banco.query(models.User).filter(
            models.User.username == username,
            models.User.is_active == True,
        ).first()

        if not usuario or not auth_utils.verify_password(senha, usuario.hashed_password):
            return {"ok": False, "error": "Credenciais inválidas"}

        if usuario.role not in (models.UserRole.admin, models.UserRole.gerente):
            return {"ok": False, "error": "Usuário não tem permissão de supervisor"}

        return {"ok": True, "supervisor": usuario.full_name}
