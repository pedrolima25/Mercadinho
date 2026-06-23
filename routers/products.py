"""
Rotas de Produtos
=================
Responsabilidade: receber requisições HTTP e delegar ao ServicoProdutos.
Não contém lógica de negócio — apenas parse do request e render da resposta.
"""

from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
import os, uuid, shutil
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
import models
import auth as auth_utils
from servicos.produtos import ServicoProdutos
from servicos.catalogos import ServicoCatalogos

router = APIRouter(prefix="/produtos", tags=["produtos"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_produtos(
    request: Request,
    search: Optional[str] = None,
    category_id: Optional[str] = None,   # str para aceitar "" sem erro 422
    low_stock: Optional[str] = None,      # str para aceitar "true"/"" sem erro 422
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Lista produtos com filtros e paginação."""
    servico = ServicoProdutos(db)
    servico_catalogos = ServicoCatalogos(db)

    # Converte category_id para int somente se for um número válido
    cat_id = int(category_id) if category_id and category_id.isdigit() else None

    # Converte low_stock para bool somente se for "true"
    estoque_baixo = low_stock == "true"

    # Limpa search vazio (form envia "" quando campo está em branco)
    busca = search.strip() if search and search.strip() else None

    produtos, total = servico.listar(
        busca=busca,
        categoria_id=cat_id,
        estoque_baixo=estoque_baixo,
        pagina=page,
    )
    categorias = servico_catalogos.listar_categorias()

    return templates.TemplateResponse(
        request,
        "products/index.html",
        {
            "products": produtos,
            "categories": categorias,
            "search": busca,
            "category_id": cat_id,          # int para o {% if category_id == c.id %} funcionar
            "low_stock": estoque_baixo,     # bool para o {% if low_stock %}checked{% endif %}
            "page": page,
            "total": total,
            "per_page": 20,
            "current_user": current_user,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def novo_produto(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Exibe formulário de cadastro de novo produto."""
    servico_catalogos = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request,
        "products/form.html",
        {
            "product": None,
            "categories": servico_catalogos.listar_categorias(),
            "brands": servico_catalogos.listar_marcas(),
            "suppliers": servico_catalogos.listar_fornecedores(),
            "current_user": current_user,
        },
    )


@router.post("/novo")
async def criar_produto(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Cria um novo produto. Validações ficam no ServiçoProdutos."""
    form = await request.form()
    servico = ServicoProdutos(db)
    servico.cadastrar(form, current_user)
    return RedirectResponse("/produtos", status_code=302)


@router.get("/{product_id}/editar", response_class=HTMLResponse)
def editar_produto(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Exibe formulário de edição de produto."""
    servico = ServicoProdutos(db)
    servico_catalogos = ServicoCatalogos(db)
    produto = servico.obter_ou_erro(product_id)

    return templates.TemplateResponse(
        request,
        "products/form.html",
        {
            "product": produto,
            "categories": servico_catalogos.listar_categorias(),
            "brands": servico_catalogos.listar_marcas(),
            "suppliers": servico_catalogos.listar_fornecedores(),
            "current_user": current_user,
        },
    )


@router.post("/{product_id}/editar")
async def atualizar_produto(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Salva alterações de um produto existente."""
    form = await request.form()
    servico = ServicoProdutos(db)
    servico.atualizar(product_id, form, current_user)
    return RedirectResponse("/produtos", status_code=302)


@router.post("/{product_id}/excluir")
def excluir_produto(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("produtos")),
):
    """Desativa um produto (mantém histórico)."""
    servico = ServicoProdutos(db)
    servico.excluir(product_id, current_user)
    return RedirectResponse("/produtos", status_code=302)


# ── API JSON para o PDV ────────────────────────────────────────────────────

@router.get("/api/buscar")
def api_buscar_produtos(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Busca rápida de produtos para o autocomplete do PDV."""
    servico = ServicoProdutos(db)
    return servico.buscar_rapido(q)


@router.get("/api/todos")
def api_todos_produtos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Retorna todos os produtos ativos para o catálogo do PDV."""
    servico = ServicoProdutos(db)
    return servico.listar_para_pdv()


@router.get("/api/barcode/{barcode}")
def api_produto_por_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Retorna produto pelo código de barras — usado pelo leitor no PDV."""
    servico = ServicoProdutos(db)
    produto = servico.buscar_por_codigo_barras(barcode)
    return {
        "id": produto.id,
        "barcode": produto.barcode,
        "name": produto.name,
        "sale_price": float(produto.sale_price),
        "stock_quantity": float(produto.stock_quantity),
        "unit": produto.unit,
        "image_url": produto.image_url or "",
    }


_UPLOAD_DIR = "static/uploads/products"
_ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}

@router.post("/{product_id}/imagem")
async def upload_imagem(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Faz upload da foto de um produto e salva o caminho no banco."""
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in _ALLOWED:
        return JSONResponse({"error": "Formato inválido. Use JPG, PNG ou WEBP."}, status_code=400)

    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    filename = f"prod-{product_id}-{uuid.uuid4().hex[:8]}{ext}"
    dest = os.path.join(_UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    produto = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not produto:
        return JSONResponse({"error": "Produto não encontrado"}, status_code=404)

    # Remove imagem antiga se existir
    if produto.image_url:
        old = produto.image_url.lstrip("/")
        if os.path.exists(old):
            os.remove(old)

    produto.image_url = f"/static/uploads/products/{filename}"
    db.commit()
    return JSONResponse({"image_url": produto.image_url})
