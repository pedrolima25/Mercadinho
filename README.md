# Mercadinho

Sistema web de gestao para mercadinho, mercado, padaria, loja pequena e operacoes similares. O projeto roda localmente com FastAPI, Jinja2, SQLAlchemy e PostgreSQL.

## O que o sistema faz

- PDV / frente de caixa com busca por codigo de barras ou nome.
- Venda por unidade e por KG, com janela para peso ou conversao de valor em quilo.
- Pagamentos em dinheiro, PIX, debito, credito e fiado.
- Cupom ao finalizar venda, com dados da empresa, logo, itens, pagamentos e troco.
- Cadastro completo da empresa, incluindo logo.
- Cadastro de produtos, categorias, marcas, fornecedores, clientes e funcionarios.
- Controle de estoque, movimentacoes, lotes e validade.
- Caixa com abertura, fechamento, sangria e suprimento.
- Compras, contas a pagar, contas a receber e despesas.
- Relatorios de vendas, produtos, financeiro e estoque baixo.
- Usuarios e permissoes.

## Tecnologias

- Python 3.10+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Jinja2
- Bootstrap

## Requisitos

Instale antes:

- Python 3.10 ou superior
- PostgreSQL local, ou Docker Desktop para rodar o banco via `docker-compose.yml`
- Git, se for clonar pelo GitHub

## Instalacao rapida no Windows

1. Clone o projeto:

```bash
git clone https://github.com/pedrolima25/Mercadinho.git
cd Mercadinho
```

2. Suba o PostgreSQL.

Se for usar Docker:

```bash
docker compose up -d
```

O `docker-compose.yml` cria um banco com:

```text
usuario: postgres
senha: postgres
banco: supermercado
porta: 5432
```

3. Execute o instalador:

```bat
instalar.bat
```

O script cria o ambiente virtual, instala as dependencias, copia `.env.example` para `.env` se ainda nao existir, cria as tabelas e gera dados iniciais.

4. Confira o arquivo `.env`.

Se estiver usando o banco do Docker, deixe assim:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supermercado
SECRET_KEY=troque-esta-chave-em-producao
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
APP_NAME=SuperMarket Pro
MARKET_NAME=Mercadinho
MARKET_LOGO_URL=/static/img/logo.svg
```

5. Inicie o sistema:

```bat
iniciar.bat
```

6. Acesse no navegador:

```text
http://localhost:8000
```

Login inicial:

```text
usuario: admin
senha: admin123
```

## Instalacao manual

Use estes passos caso prefira nao usar o `.bat`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -c "from main import create_initial_data; create_initial_data()"
python main.py
```

Depois acesse:

```text
http://localhost:8000
```

## Configuracao da empresa

Depois de entrar no sistema, acesse:

```text
Cadastros > Empresa
```

Nessa tela voce pode cadastrar:

- nome fantasia e razao social
- CNPJ e inscricoes
- endereco completo
- telefone, WhatsApp, e-mail e site
- responsavel
- slogan e mensagem do cupom
- logo da empresa

Esses dados aparecem no sistema, no PDV e no cupom final.

## Como usar o PDV

1. Abra ou confirme que existe um caixa aberto.
2. Acesse `PDV - Frente de Caixa`.
3. Leia o codigo de barras ou digite o nome do produto.
4. Para produtos em KG, informe o peso ou o valor em reais para converter em quilos.
5. Clique em finalizar ou use os atalhos de pagamento.
6. Confirme o pagamento.
7. O sistema mostra o cupom da venda, com opcao de imprimir.

## Atalhos do PDV

- `F2`: focar busca de produto
- `F4`: finalizar venda
- `F5`: dinheiro
- `F6`: PIX
- `F7`: debito
- `F8`: credito
- `F9`: fiado
- `ESC`: cancelar venda

## Funcionamento offline

O sistema pode funcionar sem internet se estiver rodando no computador local ou em um servidor dentro da rede da loja.

Para uso offline completo, evite depender de arquivos externos da internet. O banco deve estar no mesmo computador ou em outro computador da rede local.

Exemplo em rede interna:

```text
http://IP_DO_SERVIDOR:8000
```

## Estrutura do projeto

```text
.
├── main.py                 # Inicializacao da aplicacao FastAPI
├── models.py               # Modelos do banco
├── schemas.py              # Schemas Pydantic
├── database.py             # Conexao com o banco
├── auth.py                 # Login, senha e token
├── routers/                # Rotas do sistema
├── templates/              # Telas HTML/Jinja
├── static/                 # CSS, JS, imagens e logo
├── requirements.txt        # Dependencias Python
├── docker-compose.yml      # PostgreSQL via Docker
├── instalar.bat            # Instalacao no Windows
└── iniciar.bat             # Inicia o sistema
```

## Cuidados importantes

- Nao envie o arquivo `.env` para o GitHub.
- Troque `SECRET_KEY` antes de usar em producao.
- Troque a senha padrao do usuario `admin`.
- Faca backup do PostgreSQL regularmente.
- A pasta `static/uploads/` guarda arquivos enviados, como logos de empresa.

## Backup basico do banco

Exemplo usando PostgreSQL local:

```bash
pg_dump -U postgres -h localhost supermercado > backup_supermercado.sql
```

Para restaurar:

```bash
psql -U postgres -h localhost supermercado < backup_supermercado.sql
```

## Atualizar no GitHub

Depois de alterar arquivos:

```bash
git status
git add .
git commit -m "Descricao da alteracao"
git push
```

