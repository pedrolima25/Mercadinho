"""
Catálogo de permissões granulares por tela/módulo.

Admin e Gerente sempre têm acesso total (ver models.User.has_permission).
Para os demais perfis (Caixa, Estoquista, Financeiro), o admin pode liberar
telas específicas usuário por usuário em /usuarios/{id}/permissoes.
"""

PERMISSIONS = [
    ("dashboard", "Dashboard"),
    ("vendas", "Vendas — Histórico e Detalhes"),
    ("produtos", "Produtos"),
    ("estoque", "Estoque"),
    ("compras", "Compras"),
    ("empresa", "Empresa"),
    ("categorias", "Categorias"),
    ("marcas", "Marcas"),
    ("fornecedores", "Fornecedores"),
    ("clientes", "Clientes"),
    ("funcionarios", "Funcionários"),
    ("financeiro", "Financeiro"),
    ("relatorios", "Relatórios"),
]

PERMISSION_LABELS = dict(PERMISSIONS)
PERMISSION_KEYS = [key for key, _ in PERMISSIONS]
