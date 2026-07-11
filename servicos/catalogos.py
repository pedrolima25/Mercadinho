"""
Serviço de Catálogos
====================
Regras de negócio para: Categorias, Marcas, Fornecedores, Clientes e Funcionários.

Exemplo de uso:
    servico = ServicoCatalogos(banco)
    categorias = servico.listar_categorias()
    fornecedor = servico.obter_fornecedor_ou_erro(5)
"""

from typing import List
from sqlalchemy.orm import Session
import models
from repositorios.catalogos import (
    RepositorioCategorias,
    RepositorioMarcas,
    RepositorioFornecedores,
    RepositorioClientes,
    RepositorioFuncionarios,
)
from servicos.base import ServicoBase


class ServicoCatalogos(ServicoBase):
    """
    Serviço unificado para todos os catálogos auxiliares.
    Agrupa categorias, marcas, fornecedores, clientes e funcionários
    em um único serviço para facilitar o uso nos routers.
    """

    def __init__(self, banco: Session, current_user=None):
        super().__init__(banco, current_user)
        self.categorias = RepositorioCategorias(banco, self.empresa_id)
        self.marcas = RepositorioMarcas(banco, self.empresa_id)
        self.fornecedores = RepositorioFornecedores(banco, self.empresa_id)
        self.clientes = RepositorioClientes(banco, self.empresa_id)
        self.funcionarios = RepositorioFuncionarios(banco, self.empresa_id)

    # ── Categorias ─────────────────────────────────────────────────────────

    def listar_categorias(self) -> List[models.Category]:
        """Retorna todas as categorias ativas."""
        return self.categorias.listar_todas()

    def obter_categoria_ou_erro(self, categoria_id: int) -> models.Category:
        """Retorna categoria ou lança 404."""
        return self.obter_ou_404(self.categorias, categoria_id, "Categoria não encontrada")

    def criar_categoria(self, dados_form) -> models.Category:
        """Cria nova categoria."""
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("Nome da categoria é obrigatório")
        return self.categorias.criar({
            "name": nome,
            "description": dados_form.get("description") or None,
        })

    def atualizar_categoria(self, categoria_id: int, dados_form) -> models.Category:
        """Atualiza categoria existente."""
        categoria = self.obter_categoria_ou_erro(categoria_id)
        categoria.name = dados_form.get("name")
        categoria.description = dados_form.get("description") or None
        categoria.is_active = dados_form.get("is_active") == "on"
        self.banco.commit()
        return categoria

    def desativar_categoria(self, categoria_id: int):
        """Desativa categoria (soft delete)."""
        self.categorias.desativar(categoria_id)

    # ── Marcas ─────────────────────────────────────────────────────────────

    def listar_marcas(self) -> List[models.Brand]:
        """Retorna todas as marcas ativas."""
        return self.marcas.listar_todas()

    def obter_marca_ou_erro(self, marca_id: int) -> models.Brand:
        """Retorna marca ou lança 404."""
        return self.obter_ou_404(self.marcas, marca_id, "Marca não encontrada")

    def criar_marca(self, dados_form) -> models.Brand:
        """Cria nova marca."""
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("Nome da marca é obrigatório")
        return self.marcas.criar({
            "name": nome,
            "description": dados_form.get("description") or None,
        })

    def atualizar_marca(self, marca_id: int, dados_form) -> models.Brand:
        """Atualiza marca existente."""
        marca = self.obter_marca_ou_erro(marca_id)
        marca.name = dados_form.get("name")
        marca.description = dados_form.get("description") or None
        marca.is_active = dados_form.get("is_active") == "on"
        self.banco.commit()
        return marca

    def desativar_marca(self, marca_id: int):
        """Desativa marca."""
        self.marcas.desativar(marca_id)

    # ── Fornecedores ───────────────────────────────────────────────────────

    def listar_fornecedores(self) -> List[models.Supplier]:
        """Retorna todos os fornecedores ativos."""
        return self.fornecedores.listar_todos()

    def obter_fornecedor_ou_erro(self, fornecedor_id: int) -> models.Supplier:
        """Retorna fornecedor ou lança 404."""
        return self.obter_ou_404(self.fornecedores, fornecedor_id, "Fornecedor não encontrado")

    def criar_fornecedor(self, dados_form) -> models.Supplier:
        """Cria novo fornecedor."""
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("Nome do fornecedor é obrigatório")
        return self.fornecedores.criar({
            "name": nome,
            "cnpj": dados_form.get("cnpj") or None,
            "email": dados_form.get("email") or None,
            "phone": dados_form.get("phone") or None,
            "address": dados_form.get("address") or None,
            "contact_name": dados_form.get("contact_name") or None,
        })

    def atualizar_fornecedor(self, fornecedor_id: int, dados_form) -> models.Supplier:
        """Atualiza fornecedor existente."""
        fornecedor = self.obter_fornecedor_ou_erro(fornecedor_id)
        fornecedor.name = dados_form.get("name")
        fornecedor.cnpj = dados_form.get("cnpj") or None
        fornecedor.email = dados_form.get("email") or None
        fornecedor.phone = dados_form.get("phone") or None
        fornecedor.address = dados_form.get("address") or None
        fornecedor.contact_name = dados_form.get("contact_name") or None
        fornecedor.is_active = dados_form.get("is_active") == "on"
        self.banco.commit()
        return fornecedor

    def desativar_fornecedor(self, fornecedor_id: int):
        """Desativa fornecedor."""
        self.fornecedores.desativar(fornecedor_id)

    # ── Clientes ───────────────────────────────────────────────────────────

    def listar_clientes(self) -> List[models.Customer]:
        """Retorna todos os clientes ativos."""
        return self.clientes.listar_todos()

    def listar_clientes_ativos(self) -> List[models.Customer]:
        """Clientes ativos — usado no PDV para seleção de cliente."""
        return self.clientes.listar_ativos()

    def obter_cliente_ou_erro(self, cliente_id: int) -> models.Customer:
        """Retorna cliente ou lança 404."""
        return self.obter_ou_404(self.clientes, cliente_id, "Cliente não encontrado")

    def criar_cliente(self, dados_form) -> models.Customer:
        """Cria novo cliente."""
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("Nome do cliente é obrigatório")
        return self.clientes.criar({
            "name": nome,
            "cpf": dados_form.get("cpf") or None,
            "email": dados_form.get("email") or None,
            "phone": dados_form.get("phone") or None,
            "address": dados_form.get("address") or None,
            "credit_limit": float(dados_form.get("credit_limit") or 0),
            "person_type": dados_form.get("person_type") or None,
            "trade_name": dados_form.get("trade_name") or None,
            "contact_name": dados_form.get("contact_name") or None,
            "birth_date": dados_form.get("birth_date") or None,
            "gender": dados_form.get("gender") or None,
            "sales_channel": dados_form.get("sales_channel") or None,
        })

    def atualizar_cliente(self, cliente_id: int, dados_form) -> models.Customer:
        """Atualiza cliente existente."""
        cliente = self.obter_cliente_ou_erro(cliente_id)
        cliente.name = dados_form.get("name")
        cliente.cpf = dados_form.get("cpf") or None
        cliente.email = dados_form.get("email") or None
        cliente.phone = dados_form.get("phone") or None
        cliente.address = dados_form.get("address") or None
        cliente.credit_limit = float(dados_form.get("credit_limit") or 0)
        cliente.is_active = dados_form.get("is_active") == "on"
        cliente.person_type = dados_form.get("person_type") or None
        cliente.trade_name = dados_form.get("trade_name") or None
        cliente.contact_name = dados_form.get("contact_name") or None
        cliente.birth_date = dados_form.get("birth_date") or None
        cliente.gender = dados_form.get("gender") or None
        cliente.sales_channel = dados_form.get("sales_channel") or None
        self.banco.commit()
        return cliente

    def desativar_cliente(self, cliente_id: int):
        """Desativa cliente."""
        self.clientes.desativar(cliente_id)

    # ── Funcionários ───────────────────────────────────────────────────────

    def listar_funcionarios(self) -> List[models.Employee]:
        """Retorna todos os funcionários."""
        return self.funcionarios.listar_todos()

    def obter_funcionario_ou_erro(self, funcionario_id: int) -> models.Employee:
        """Retorna funcionário ou lança 404."""
        return self.obter_ou_404(self.funcionarios, funcionario_id, "Funcionário não encontrado")

    def criar_funcionario(self, dados_form) -> models.Employee:
        """Cria novo funcionário."""
        nome = (dados_form.get("name") or "").strip()
        if not nome:
            self.erro_requisicao("Nome do funcionário é obrigatório")
        user_id = int(dados_form.get("user_id")) if dados_form.get("user_id") else None
        self.validar_pertence_a_empresa(models.User, user_id, "Usuário inválido")
        return self.funcionarios.criar({
            "name": nome,
            "cpf": dados_form.get("cpf") or None,
            "email": dados_form.get("email") or None,
            "phone": dados_form.get("phone") or None,
            "position": dados_form.get("position") or None,
            "salary": float(dados_form.get("salary") or 0) or None,
            "hire_date": dados_form.get("hire_date") or None,
            "user_id": user_id,
        })

    def atualizar_funcionario(self, funcionario_id: int, dados_form) -> models.Employee:
        """Atualiza funcionário existente."""
        funcionario = self.obter_funcionario_ou_erro(funcionario_id)
        funcionario.name = dados_form.get("name")
        funcionario.cpf = dados_form.get("cpf") or None
        funcionario.email = dados_form.get("email") or None
        funcionario.phone = dados_form.get("phone") or None
        funcionario.position = dados_form.get("position") or None
        funcionario.salary = float(dados_form.get("salary") or 0) or None
        funcionario.hire_date = dados_form.get("hire_date") or None
        user_id = int(dados_form.get("user_id")) if dados_form.get("user_id") else None
        self.validar_pertence_a_empresa(models.User, user_id, "Usuário inválido")
        funcionario.user_id = user_id
        funcionario.is_active = dados_form.get("is_active") == "on"
        self.banco.commit()
        return funcionario

    def desativar_funcionario(self, funcionario_id: int):
        """Desativa funcionário."""
        self.funcionarios.desativar(funcionario_id)
