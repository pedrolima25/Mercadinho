"""
Repositório Base
================
Fornece operações CRUD comuns para todos os repositórios do sistema.

Como usar:
    class RepositorioProdutos(RepositorioBase):
        def __init__(self, banco):
            super().__init__(banco, models.Product)

        def buscar_por_codigo_barras(self, codigo):
            return self.banco.query(self.modelo).filter(...).first()
"""

from typing import List, Optional, Type, Any
from sqlalchemy.orm import Session


class RepositorioBase:
    """
    Classe base com operações CRUD reutilizáveis.

    Todos os repositórios herdam desta classe para não repetir
    as operações básicas de banco de dados.
    """

    def __init__(self, banco: Session, modelo: Type, empresa_id: Optional[int] = None):
        """
        Inicializa o repositório.

        Args:
            banco: Sessão do SQLAlchemy (recebida via Depends(get_db))
            modelo: Classe do modelo SQLAlchemy (ex: models.Product)
            empresa_id: ID da empresa (tenant) do usuário atual. Obrigatório
                para modelos com coluna `company_id` — todas as consultas
                deste repositório ficam restritas a essa empresa.
        """
        self.banco = banco
        self.modelo = modelo
        self.empresa_id = empresa_id

    # ── Isolamento multi-tenant ──────────────────────────────────────────────

    def _query(self):
        """
        Ponto único de acesso ao banco: toda leitura do repositório passa por
        aqui, para nunca esquecer o filtro por empresa.
        """
        consulta = self.banco.query(self.modelo)
        if hasattr(self.modelo, "company_id"):
            if self.empresa_id is None:
                raise RuntimeError(
                    f"{type(self).__name__}: empresa_id não informado para "
                    f"consultar {self.modelo.__name__} (tabela com dados por empresa)."
                )
            consulta = consulta.filter(self.modelo.company_id == self.empresa_id)
        return consulta

    # ── Leitura ────────────────────────────────────────────────────────────

    def buscar_por_id(self, id: int) -> Optional[Any]:
        """Retorna um registro pelo ID, ou None se não encontrar."""
        return self._query().filter(self.modelo.id == id).first()

    def buscar_todos(self, pagina: int = 1, por_pagina: int = 20) -> List[Any]:
        """
        Retorna registros com paginação.

        Args:
            pagina: Número da página (começa em 1)
            por_pagina: Quantidade de registros por página

        Returns:
            Lista de objetos do modelo
        """
        deslocamento = (pagina - 1) * por_pagina
        return (
            self._query()
            .offset(deslocamento)
            .limit(por_pagina)
            .all()
        )

    def buscar_ativos(self) -> List[Any]:
        """Retorna todos os registros onde is_active = True."""
        if not hasattr(self.modelo, "is_active"):
            return self.buscar_todos(por_pagina=1000)
        return (
            self._query()
            .filter(self.modelo.is_active == True)
            .all()
        )

    def contar(self) -> int:
        """Retorna o total de registros na tabela."""
        return self._query().count()

    # ── Escrita ────────────────────────────────────────────────────────────

    def criar(self, dados: dict) -> Any:
        """
        Cria um novo registro no banco.

        Args:
            dados: Dicionário com os campos do modelo

        Returns:
            Objeto criado e salvo
        """
        if hasattr(self.modelo, "company_id") and "company_id" not in dados:
            dados = {**dados, "company_id": self.empresa_id}
        objeto = self.modelo(**dados)
        self.banco.add(objeto)
        self.banco.commit()
        self.banco.refresh(objeto)
        return objeto

    def salvar(self):
        """
        Persiste mudanças pendentes no banco.
        Use após alterar atributos de um objeto diretamente.

        Exemplo:
            produto.nome = "Novo Nome"
            repositorio.salvar()
        """
        self.banco.commit()

    def adicionar(self, objeto: Any):
        """
        Adiciona um objeto à sessão sem commitar.
        Use quando precisar adicionar vários antes de salvar.

        Exemplo:
            repo.adicionar(item1)
            repo.adicionar(item2)
            repo.salvar()
        """
        self.banco.add(objeto)

    def flush(self):
        """
        Envia as mudanças para o banco sem commitar a transação.
        Útil para obter o ID gerado antes de criar objetos relacionados.
        """
        self.banco.flush()

    def excluir_fisico(self, id: int) -> bool:
        """
        Remove o registro do banco definitivamente.
        Prefira usar desativar() para manter histórico.

        Returns:
            True se encontrou e excluiu, False se não encontrou
        """
        objeto = self.buscar_por_id(id)
        if objeto:
            self.banco.delete(objeto)
            self.banco.commit()
            return True
        return False

    def desativar(self, id: int) -> bool:
        """
        Desativa um registro (soft delete — is_active = False).
        O registro continua no banco mas não aparece nas listagens normais.

        Returns:
            True se encontrou e desativou, False se não encontrou
        """
        objeto = self.buscar_por_id(id)
        if objeto and hasattr(objeto, "is_active"):
            objeto.is_active = False
            self.banco.commit()
            return True
        return False

    def rollback(self):
        """Desfaz todas as mudanças não commitadas da sessão atual."""
        self.banco.rollback()
