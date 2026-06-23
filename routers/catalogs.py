"""
Rotas de Catálogos
==================
Responsabilidade: receber requisições HTTP e delegar ao ServicoCatalogos.
Cobre: Categorias, Marcas, Fornecedores, Clientes e Funcionários.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.catalogos import ServicoCatalogos
from servicos.usuarios import ServicoUsuarios

templates = Jinja2Templates(directory="templates")


# ── Categorias ─────────────────────────────────────────────────────────────

categories_router = APIRouter(prefix="/categorias", tags=["categorias"])


@categories_router.get("", response_class=HTMLResponse)
def listar_categorias(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("categorias")),
):
    servico = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request, "catalogs/categories.html",
        {"items": servico.listar_categorias(), "current_user": current_user},
    )


@categories_router.post("/novo")
async def criar_categoria(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("categorias")),
):
    form = await request.form()
    ServicoCatalogos(db).criar_categoria(form)
    return RedirectResponse("/categorias", status_code=302)


@categories_router.post("/{item_id}/editar")
async def atualizar_categoria(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("categorias")),
):
    form = await request.form()
    ServicoCatalogos(db).atualizar_categoria(item_id, form)
    return RedirectResponse("/categorias", status_code=302)


@categories_router.post("/{item_id}/excluir")
def excluir_categoria(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("categorias")),
):
    ServicoCatalogos(db).desativar_categoria(item_id)
    return RedirectResponse("/categorias", status_code=302)


# ── Marcas ─────────────────────────────────────────────────────────────────

brands_router = APIRouter(prefix="/marcas", tags=["marcas"])


@brands_router.get("", response_class=HTMLResponse)
def listar_marcas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("marcas")),
):
    servico = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request, "catalogs/brands.html",
        {"items": servico.listar_marcas(), "current_user": current_user},
    )


@brands_router.post("/novo")
async def criar_marca(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("marcas")),
):
    form = await request.form()
    ServicoCatalogos(db).criar_marca(form)
    return RedirectResponse("/marcas", status_code=302)


@brands_router.post("/{item_id}/editar")
async def atualizar_marca(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("marcas")),
):
    form = await request.form()
    ServicoCatalogos(db).atualizar_marca(item_id, form)
    return RedirectResponse("/marcas", status_code=302)


@brands_router.post("/{item_id}/excluir")
def excluir_marca(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("marcas")),
):
    ServicoCatalogos(db).desativar_marca(item_id)
    return RedirectResponse("/marcas", status_code=302)


# ── Fornecedores ───────────────────────────────────────────────────────────

suppliers_router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])


@suppliers_router.get("", response_class=HTMLResponse)
def listar_fornecedores(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    servico = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request, "catalogs/suppliers.html",
        {"items": servico.listar_fornecedores(), "current_user": current_user},
    )


@suppliers_router.get("/novo", response_class=HTMLResponse)
def novo_fornecedor(
    request: Request,
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    return templates.TemplateResponse(
        request, "catalogs/supplier_form.html",
        {"item": None, "current_user": current_user},
    )


@suppliers_router.post("/novo")
async def criar_fornecedor(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    form = await request.form()
    ServicoCatalogos(db).criar_fornecedor(form)
    return RedirectResponse("/fornecedores", status_code=302)


@suppliers_router.get("/{item_id}/editar", response_class=HTMLResponse)
def editar_fornecedor(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    servico = ServicoCatalogos(db)
    item = servico.obter_fornecedor_ou_erro(item_id)
    return templates.TemplateResponse(
        request, "catalogs/supplier_form.html",
        {"item": item, "current_user": current_user},
    )


@suppliers_router.post("/{item_id}/editar")
async def atualizar_fornecedor(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    form = await request.form()
    ServicoCatalogos(db).atualizar_fornecedor(item_id, form)
    return RedirectResponse("/fornecedores", status_code=302)


@suppliers_router.post("/{item_id}/excluir")
def excluir_fornecedor(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("fornecedores")),
):
    ServicoCatalogos(db).desativar_fornecedor(item_id)
    return RedirectResponse("/fornecedores", status_code=302)


# ── Clientes ───────────────────────────────────────────────────────────────

customers_router = APIRouter(prefix="/clientes", tags=["clientes"])


@customers_router.get("", response_class=HTMLResponse)
def listar_clientes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    servico = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request, "catalogs/customers.html",
        {"items": servico.listar_clientes(), "current_user": current_user},
    )


@customers_router.get("/novo", response_class=HTMLResponse)
def novo_cliente(
    request: Request,
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    return templates.TemplateResponse(
        request, "catalogs/customer_form.html",
        {"item": None, "current_user": current_user},
    )


@customers_router.post("/novo")
async def criar_cliente(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    form = await request.form()
    ServicoCatalogos(db).criar_cliente(form)
    return RedirectResponse("/clientes", status_code=302)


@customers_router.get("/{item_id}/editar", response_class=HTMLResponse)
def editar_cliente(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    servico = ServicoCatalogos(db)
    item = servico.obter_cliente_ou_erro(item_id)
    return templates.TemplateResponse(
        request, "catalogs/customer_form.html",
        {"item": item, "current_user": current_user},
    )


@customers_router.post("/{item_id}/editar")
async def atualizar_cliente(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    form = await request.form()
    ServicoCatalogos(db).atualizar_cliente(item_id, form)
    return RedirectResponse("/clientes", status_code=302)


@customers_router.post("/{item_id}/excluir")
def excluir_cliente(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("clientes")),
):
    ServicoCatalogos(db).desativar_cliente(item_id)
    return RedirectResponse("/clientes", status_code=302)


# ── Funcionários ───────────────────────────────────────────────────────────

employees_router = APIRouter(prefix="/funcionarios", tags=["funcionarios"])


@employees_router.get("", response_class=HTMLResponse)
def listar_funcionarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("funcionarios")),
):
    servico = ServicoCatalogos(db)
    return templates.TemplateResponse(
        request, "catalogs/employees.html",
        {"items": servico.listar_funcionarios(), "current_user": current_user},
    )


@employees_router.get("/novo", response_class=HTMLResponse)
def novo_funcionario(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("funcionarios")),
):
    servico_usuarios = ServicoUsuarios(db)
    return templates.TemplateResponse(
        request, "catalogs/employee_form.html",
        {"item": None, "users": servico_usuarios.listar_todos(), "current_user": current_user},
    )


@employees_router.post("/novo")
async def criar_funcionario(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("funcionarios")),
):
    form = await request.form()
    ServicoCatalogos(db).criar_funcionario(form)
    return RedirectResponse("/funcionarios", status_code=302)


@employees_router.get("/{item_id}/editar", response_class=HTMLResponse)
def editar_funcionario(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("funcionarios")),
):
    servico = ServicoCatalogos(db)
    servico_usuarios = ServicoUsuarios(db)
    item = servico.obter_funcionario_ou_erro(item_id)
    return templates.TemplateResponse(
        request, "catalogs/employee_form.html",
        {"item": item, "users": servico_usuarios.listar_todos(), "current_user": current_user},
    )


@employees_router.post("/{item_id}/editar")
async def atualizar_funcionario(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("funcionarios")),
):
    form = await request.form()
    ServicoCatalogos(db).atualizar_funcionario(item_id, form)
    return RedirectResponse("/funcionarios", status_code=302)
