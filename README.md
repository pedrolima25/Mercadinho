# SuperMarket Pro

Sistema de gestão comercial para mercados, mercearias, padarias e lojas de pequeno e médio porte.  
Roda localmente na rede interna — sem mensalidade, sem internet obrigatória.

---

## Índice

1. [O que o sistema faz](#funcionalidades)
2. [Requisitos](#requisitos)
3. [Instalação — Servidor (Docker)](#instalação-servidor)
4. [Instalação — Outras Máquinas (Caixas / Gerentes)](#instalação-clientes)
5. [Primeiro acesso](#primeiro-acesso)
6. [Perfis de usuário](#perfis-de-usuário)
7. [Módulos do sistema](#módulos-do-sistema)
8. [Configuração da empresa](#configuração-da-empresa)
9. [Backup dos dados](#backup)
10. [Solução de problemas](#solução-de-problemas)
11. [Referência técnica](#referência-técnica)

---

## Funcionalidades

| Módulo | O que faz |
|---|---|
| **PDV — Frente de Caixa** | Venda por código de barras ou catálogo, múltiplos pagamentos, QR Code PIX, cupom imprimível |
| **Caixa** | Abertura e fechamento de caixa, sangria, suprimento, histórico |
| **Estoque** | Entradas, saídas, ajustes, lotes com validade, alertas de estoque baixo |
| **Produtos** | Cadastro completo com código de barras, preço de custo/venda, dados fiscais |
| **Compras** | Pedidos a fornecedores, recebimento de mercadorias com atualização automática do estoque |
| **Financeiro** | Contas a pagar, contas a receber, despesas, visão geral financeira |
| **Clientes** | Cadastro com limite de fiado, controle de saldo devedor |
| **Devoluções** | Devolução parcial ou total de itens com reposição automática no estoque |
| **Relatórios** | Vendas por período, produtos mais vendidos, estoque baixo, análise financeira |
| **Dashboard** | Gráficos de vendas diárias, métodos de pagamento e top produtos |
| **Alertas** | Notificações de estoque baixo e contas vencidas em tempo real |
| **Empresa** | Logo, dados fiscais, chave PIX, rodapé do cupom |
| **Usuários** | Múltiplos usuários com diferentes níveis de acesso |

---

## Requisitos

### Máquina Servidor
- Windows 10 / 11 (64 bits)
- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- 4 GB de RAM (recomendado: 8 GB)
- 10 GB de espaço em disco
- Conexão com a internet (somente na primeira instalação)

### Máquinas Clientes (Caixas / Gerentes)
- Qualquer computador ou tablet com browser (Chrome, Edge, Firefox)
- Conectado na mesma rede Wi-Fi ou cabo que o servidor
- **Não precisa instalar nada**

---

## Instalação — Servidor

> Execute este processo apenas **uma vez**, na máquina que será o servidor.

### 1. Instalar o Docker Desktop

Baixe em: https://www.docker.com/products/docker-desktop/

Durante a instalação aceite as opções padrão.  
Após instalar, **reinicie o computador**.  
Abra o Docker Desktop e aguarde o ícone ficar verde na barra de tarefas.

### 2. Executar o instalador

Na pasta do sistema, clique duas vezes em:

```
INSTALAR.bat
```

O instalador vai:
- Verificar se o Docker está rodando
- Criar o arquivo de configurações (`.env`)
- Fazer o build e subir os containers (PostgreSQL + App)
- Liberar a porta 8000 no firewall do Windows
- Criar atalhos na área de trabalho
- Abrir o sistema no browser automaticamente

> **Tempo estimado:** 5 a 10 minutos na primeira vez (baixa as imagens Docker).  
> Nas próximas vezes leva menos de 30 segundos.

### 3. Anotar o IP do servidor

Ao final da instalação, o IP da máquina é exibido na tela.  
Exemplo: `192.168.1.10`

Anote esse número — será necessário para configurar as outras máquinas.

---

## Instalação — Clientes

As máquinas clientes (caixas, gerentes) **não precisam de instalação**.

### Opção 1 — Abrir direto no browser

1. Abra o Chrome ou Edge
2. Digite na barra de endereço:
   ```
   http://192.168.1.10:8000
   ```
   (substitua pelo IP do servidor)
3. Salve como favorito

### Opção 2 — Atalho na área de trabalho (Caixa em tela cheia)

Crie um atalho com o destino:

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk http://192.168.1.10:8000/pdv --no-first-run
```

Isso abre o PDV em **tela cheia** ao clicar — ideal para terminais de caixa.  
Para sair da tela cheia: `ALT + F4`.

---

## Uso diário

| Ação | Como fazer |
|---|---|
| **Ligar o sistema** | Clique em `SuperMarket Pro - Iniciar` na área de trabalho |
| **Acessar pelo browser** | http://localhost:8000 (servidor) ou http://IP:8000 (clientes) |
| **Desligar o sistema** | Clique em `SuperMarket Pro - Parar` na área de trabalho |

> O `INICIAR.bat` inicia o Docker automaticamente se ele não estiver rodando.

---

## Primeiro acesso

Acesse http://localhost:8000 e faça login com:

| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `admin123` |

**Troque a senha imediatamente** em: Usuários → admin → Editar.

### Configuração inicial recomendada

1. **Empresa** (`/empresa`) — Preencha nome, CNPJ, endereço, logo e chave PIX
2. **Categorias** (`/categorias`) — Crie as categorias de produtos
3. **Fornecedores** (`/fornecedores`) — Cadastre os fornecedores
4. **Produtos** (`/produtos`) — Cadastre o estoque inicial
5. **Usuários** (`/usuarios`) — Crie usuários para cada operador

---

## Perfis de usuário

| Perfil | O que pode fazer |
|---|---|
| **admin** | Acesso total — configurações, usuários, todos os módulos |
| **gerente** | Todos os módulos exceto configurações do sistema |
| **caixa** | PDV, abertura/fechamento de caixa, visualização de vendas |
| **estoquista** | Produtos, estoque, compras |
| **financeiro** | Financeiro, relatórios |

---

## Módulos do sistema

### PDV — Frente de Caixa (`/pdv`)

- Acesse em uma aba separada ou máquina dedicada
- Busca de produtos por código de barras (leitor ou teclado) ou pelo catálogo
- Suporte a produtos vendidos por peso (KG)
- Pagamentos: Dinheiro, PIX, Débito, Crédito, Fiado, Vale
- PIX gera QR Code automaticamente com base na chave configurada
- Cupom impresso direto do browser (compatível com impressoras térmicas 80mm)
- Atalhos de teclado: F2 (foco leitor), F4 (finalizar), F5–F9 (pagamentos), ESC (limpar)

### Caixa (`/caixa`)

- Abrir o caixa com saldo inicial antes de começar as vendas
- Sangria (retirada) e suprimento (entrada) de dinheiro
- Fechar o caixa com conferência de valores
- Histórico de operações por caixa e operador

### Estoque (`/estoque`)

- Entrada, saída e ajuste de estoque com registro de motivo
- Controle de lotes com data de validade
- Histórico completo de movimentações
- Alerta automático de produtos abaixo do estoque mínimo

### Compras (`/compras`)

- Registro de pedidos a fornecedores com produtos e valores
- Ao marcar como "Recebida" o estoque é atualizado automaticamente
- Geração automática de conta a pagar

### Financeiro (`/financeiro`)

- **Contas a pagar:** lançamento manual ou automático (via compras)
- **Contas a receber:** controle de valores a receber, incluindo vendas fiado
- **Despesas:** registro de despesas operacionais por categoria
- Alertas de contas vencidas no sino de notificações

### Devoluções (`/vendas/{id}/devolver`)

- Acessível pela tela de detalhes da venda
- Devolução parcial ou total de itens
- Tipo: reembolso ou troca
- Estoque reposto automaticamente

### Relatórios (`/relatorios`)

| Relatório | O que mostra |
|---|---|
| Vendas | Total por período, por dia, por método de pagamento |
| Produtos | Top 20 produtos por receita, produtos com estoque baixo |
| Financeiro | Receitas, despesas, compras e lucro estimado por mês |
| Estoque baixo | Lista de produtos abaixo do mínimo |

---

## Configuração da empresa

Acesse `/empresa` para configurar:

- **Logo** — upload de imagem (PNG, JPG, WebP)
- **Dados fiscais** — CNPJ, IE, IM, regime tributário
- **Endereço** — aparece no cupom de venda
- **Contato** — e-mail, telefone, WhatsApp
- **PIX** — chave PIX e cidade (gera o QR Code nas vendas)
- **Cupom** — slogan e mensagem do rodapé

---

## Backup

### Backup manual

Abra o terminal (CMD) e execute:

```bat
docker exec supermarket_db pg_dump -U postgres supermercado > backup_%date:~6,4%%date:~3,2%%date:~0,2%.sql
```

Isso cria um arquivo `.sql` com todos os dados do sistema.

### Restaurar backup

```bat
docker exec -i supermarket_db psql -U postgres supermercado < backup_AAAAMMDD.sql
```

### Onde ficam os dados

Os dados ficam em um volume Docker chamado `postgres_data`.  
Ao parar e reiniciar os containers, os dados são preservados automaticamente.

---

## Solução de problemas

### Sistema não abre / porta 8000 inacessível

1. Verifique se o Docker Desktop está rodando (ícone verde na barra de tarefas)
2. Execute `INICIAR.bat` e aguarde a mensagem "SISTEMA RODANDO"
3. Tente acessar http://localhost:8000

### "Cannot connect to the Docker daemon"

O Docker Desktop não está iniciado.  
Abra o Docker Desktop manualmente e aguarde ficar verde, depois execute `INICIAR.bat`.

### Erro no build do Dockerfile

Verifique a conexão com a internet e execute `INSTALAR.bat` novamente.

### Outro computador não acessa o sistema

1. Confirme que estão na mesma rede Wi-Fi ou cabo
2. Verifique o IP correto do servidor (salvo em `ip_servidor.txt`)
3. Confirme que o firewall foi liberado — execute `INSTALAR.bat` novamente como administrador

### Esqueci a senha do admin

Execute no terminal (com o sistema rodando):

```bat
docker exec -it supermarket_app python -c "from database import SessionLocal; from models import User; import auth; db=SessionLocal(); u=db.query(User).filter(User.username=='admin').first(); u.hashed_password=auth.get_password_hash('nova_senha'); db.commit(); print('Senha alterada')"
```

---

## Referência técnica

### Stack

| Componente | Tecnologia |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Banco de dados | PostgreSQL 16 |
| ORM | SQLAlchemy 2 |
| Templates | Jinja2 + Bootstrap 5 |
| Autenticação | JWT (python-jose) |
| QR Code PIX | segno (geração server-side) |
| Gráficos | Chart.js 4 |
| Deploy | Docker + docker-compose |

### Estrutura de arquivos

```
supermarket/
├── main.py                 # App principal, dashboard, middlewares
├── models.py               # Modelos do banco de dados
├── schemas.py              # Schemas Pydantic
├── auth.py                 # Autenticação JWT
├── config.py               # Configurações (.env)
├── database.py             # Conexão com banco
├── routers/
│   ├── auth_router.py      # Login/logout
│   ├── products.py         # Produtos
│   ├── sales.py            # Vendas + PDV
│   ├── stock.py            # Estoque
│   ├── purchases.py        # Compras
│   ├── financial.py        # Financeiro
│   ├── cash_register.py    # Caixa
│   ├── reports.py          # Relatórios
│   ├── users.py            # Usuários
│   ├── company.py          # Empresa
│   └── catalogs.py         # Categorias, marcas, fornecedores, clientes
├── templates/              # HTML Jinja2
├── static/                 # CSS, JS, imagens
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── INSTALAR.bat
├── INICIAR.bat
└── PARAR.bat
```

### Variáveis de ambiente (.env)

| Variável | Descrição | Padrão |
|---|---|---|
| `DATABASE_URL` | URL de conexão com o banco | PostgreSQL via Docker |
| `SECRET_KEY` | Chave de assinatura JWT | Trocar em produção |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duração da sessão em minutos | 480 (8 horas) |
| `APP_NAME` | Nome do sistema | SuperMarket Pro |
| `MARKET_NAME` | Nome do mercado | Mercadinho |
| `PIX_KEY` | Chave PIX (opcional — pode configurar pelo painel) | vazio |
| `PIX_CITY` | Cidade para o payload PIX | MANAUS |

### Endpoints da API

| Endpoint | Descrição |
|---|---|
| `GET /api/docs` | Documentação interativa (Swagger UI) |
| `GET /api/qrcode?text=...` | Gera QR Code PNG |
| `GET /api/alerts` | Alertas de estoque baixo e contas vencidas |
| `GET /produtos/api/buscar?q=...` | Busca de produtos para o PDV |
| `GET /produtos/api/barcode/{code}` | Produto por código de barras |
| `POST /pdv/finalizar` | Finaliza uma venda |
| `POST /auth/token` | Gera token JWT (integração API) |

### Portas utilizadas

| Porta | Serviço |
|---|---|
| `8000` | Aplicação web (acesso do browser) |
| `5432` | PostgreSQL (interno ao Docker) |
