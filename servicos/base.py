"""
Serviço Base
============
Fornece comportamentos comuns a todos os serviços do sistema.

Como usar:
    class ServicoProdutos(ServicoBase):
        def __init__(self, banco):
            super().__init__(banco)
            self.repositorio = RepositorioProdutos(banco)

        def listar(self, busca=None):
            return self.repositorio.buscar_com_filtros(texto=busca)
"""

from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException


class ServicoBase:
    """
    Classe base com utilitários comuns a todos os serviços.

    Centraliza:
    - Lançamento de erros HTTP padronizados
    - Acesso à sessão do banco
    - Resolução da empresa (tenant) do usuário atual
    """

    def __init__(self, banco: Session, current_user=None, empresa_id: Optional[int] = None):
        """
        Inicializa o serviço com a sessão do banco e o contexto de empresa.

        Args:
            banco: Sessão SQLAlchemy (recebida via Depends(get_db))
            current_user: Usuário autenticado (fluxo normal, logado)
            empresa_id: ID da empresa a usar diretamente (fluxo público, sem
                usuário logado — ex.: catálogo público resolvido por slug)
        """
        self.banco = banco
        self.current_user = current_user
        self.empresa_id = empresa_id if empresa_id is not None else (
            current_user.company_id if current_user is not None else None
        )

    # ── Utilitários de erro ────────────────────────────────────────────────

    def erro_nao_encontrado(self, mensagem: str = "Registro não encontrado"):
        """
        Lança erro HTTP 404.

        Exemplo:
            produto = repo.buscar_por_id(id)
            if not produto:
                self.erro_nao_encontrado("Produto não encontrado")
        """
        raise HTTPException(status_code=404, detail=mensagem)

    def erro_requisicao(self, mensagem: str):
        """
        Lança erro HTTP 400 (dados inválidos).

        Exemplo:
            if quantidade < 0:
                self.erro_requisicao("Quantidade não pode ser negativa")
        """
        raise HTTPException(status_code=400, detail=mensagem)

    def erro_sem_permissao(self, mensagem: str = "Sem permissão para esta ação"):
        """Lança erro HTTP 403 (sem permissão)."""
        raise HTTPException(status_code=403, detail=mensagem)

    # ── Utilitário de validação ────────────────────────────────────────────

    def obter_ou_404(self, repositorio, id: int, mensagem: str = None):
        """
        Busca um registro pelo ID ou lança 404 automaticamente.

        Exemplo:
            produto = self.obter_ou_404(self.repositorio, produto_id, "Produto não encontrado")

        Args:
            repositorio: Instância do repositório
            id: ID a buscar
            mensagem: Mensagem de erro (opcional)

        Returns:
            Objeto encontrado
        """
        objeto = repositorio.buscar_por_id(id)
        if not objeto:
            raise HTTPException(
                status_code=404,
                detail=mensagem or f"Registro #{id} não encontrado"
            )
        return objeto

    def validar_pertence_a_empresa(self, modelo, id_valor, mensagem: str = "Registro inválido"):
        """
        Confirma que um ID de referência (categoria, marca, fornecedor, cliente,
        produto, usuário, etc.) informado num formulário realmente pertence à
        empresa do usuário atual — evita vincular um cadastro a um ID de outra
        empresa (ex.: colar um category_id de outra loja no POST).

        Não faz nada se id_valor for None/vazio (campo opcional não informado).

        Exemplo:
            self.validar_pertence_a_empresa(models.Category, category_id, "Categoria inválida")
        """
        if not id_valor:
            return
        existe = self.banco.query(modelo).filter(
            modelo.id == id_valor, modelo.company_id == self.empresa_id
        ).first()
        if not existe:
            self.erro_requisicao(mensagem)
