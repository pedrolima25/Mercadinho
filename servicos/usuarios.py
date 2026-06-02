"""
Serviço de Usuários
===================
Regras de negócio para criação e gestão de usuários do sistema.
"""

from typing import List
from sqlalchemy.orm import Session
import models
import auth as auth_utils
from repositorios.usuarios import RepositorioUsuarios
from servicos.base import ServicoBase


class ServicoUsuarios(ServicoBase):
    """Regras de negócio para usuários do sistema."""

    def __init__(self, banco: Session):
        super().__init__(banco)
        self.repositorio = RepositorioUsuarios(banco)

    def listar_todos(self) -> List[models.User]:
        """Retorna todos os usuários ordenados por nome."""
        return self.repositorio.listar_todos()

    def listar_ativos(self) -> List[models.User]:
        """Retorna somente usuários ativos."""
        return self.repositorio.listar_ativos()

    def obter_ou_erro(self, usuario_id: int) -> models.User:
        """Retorna usuário ou lança 404."""
        return self.obter_ou_404(self.repositorio, usuario_id, "Usuário não encontrado")

    def criar(self, dados_form, usuario_atual: models.User) -> models.User:
        """
        Cria novo usuário.

        Validações:
        ✓ Somente admin pode criar usuários
        ✓ Username único
        ✓ Senha obrigatória
        """
        if usuario_atual.role != models.UserRole.admin:
            self.erro_sem_permissao("Somente administradores podem criar usuários")

        username = (dados_form.get("username") or "").strip()
        if not username:
            self.erro_requisicao("Nome de usuário é obrigatório")

        # Verifica se username já existe
        if self.repositorio.buscar_por_username(username):
            self.erro_requisicao("Nome de usuário já está em uso")

        senha = dados_form.get("password") or ""
        if not senha:
            self.erro_requisicao("Senha é obrigatória")

        return self.repositorio.criar({
            "username": username,
            "email": dados_form.get("email") or None,
            "full_name": dados_form.get("full_name"),
            "hashed_password": auth_utils.get_password_hash(senha),
            "role": models.UserRole(dados_form.get("role")),
            "is_active": dados_form.get("is_active") == "on",
        })

    def atualizar(self, usuario_id: int, dados_form, usuario_atual: models.User) -> models.User:
        """
        Atualiza dados do usuário.
        Admin pode alterar role e status; o próprio usuário só pode alterar nome e senha.
        """
        usuario = self.obter_ou_erro(usuario_id)

        # Verifica permissão
        eh_admin = usuario_atual.role == models.UserRole.admin
        eh_o_proprio = usuario_atual.id == usuario_id
        if not eh_admin and not eh_o_proprio:
            self.erro_sem_permissao("Sem permissão para editar este usuário")

        # Atualiza campos básicos
        usuario.full_name = dados_form.get("full_name")
        usuario.email = dados_form.get("email") or None

        # Somente admin pode mudar role e status
        if eh_admin:
            usuario.role = models.UserRole(dados_form.get("role"))
            usuario.is_active = dados_form.get("is_active") == "on"

        # Atualiza senha se informada
        nova_senha = dados_form.get("password") or ""
        if nova_senha:
            usuario.hashed_password = auth_utils.get_password_hash(nova_senha)

        self.banco.commit()
        return usuario

    def desativar(self, usuario_id: int, usuario_atual: models.User):
        """Desativa usuário. Não permite desativar a si mesmo."""
        if usuario_atual.role != models.UserRole.admin:
            self.erro_sem_permissao("Somente administradores podem desativar usuários")
        if usuario_id == usuario_atual.id:
            self.erro_requisicao("Você não pode desativar sua própria conta")
        usuario = self.obter_ou_erro(usuario_id)
        usuario.is_active = False
        self.banco.commit()
