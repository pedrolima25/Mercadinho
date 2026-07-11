"""
Rotas de Campanhas
===================
Responsabilidade: receber requisições HTTP e delegar ao ServicoCampanhas.
Tela administrativa — a página pública fica em routers/catalog_public.py.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.campanhas import ServicoCampanhas
from servicos.produtos import ServicoProdutos

router = APIRouter(prefix="/campanhas", tags=["campanhas"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_campanhas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Lista todas as campanhas cadastradas."""
    campanhas = ServicoCampanhas(db, current_user).listar()
    return templates.TemplateResponse(
        request, "campaigns/index.html",
        {"campaigns": campanhas, "current_user": current_user},
    )


@router.get("/novo", response_class=HTMLResponse)
def nova_campanha(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Formulário de nova campanha."""
    return templates.TemplateResponse(
        request, "campaigns/form.html",
        {"campaign": None, "current_user": current_user},
    )


@router.post("/novo")
async def criar_campanha(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Cria uma nova campanha."""
    form = await request.form()
    campanha = ServicoCampanhas(db, current_user).criar(form)
    return RedirectResponse(f"/campanhas/{campanha.id}/editar", status_code=302)


@router.get("/{campanha_id}/editar", response_class=HTMLResponse)
def editar_campanha(
    campanha_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Formulário de edição de campanha, com gestão dos produtos incluídos."""
    servico = ServicoCampanhas(db, current_user)
    campanha = servico.obter_ou_erro(campanha_id)
    produtos, _ = ServicoProdutos(db, current_user).listar(por_pagina=1000)
    ja_incluidos = {item.product_id for item in campanha.items}
    produtos_disponiveis = [p for p in produtos if p.id not in ja_incluidos]
    return templates.TemplateResponse(
        request, "campaigns/form.html",
        {
            "campaign": campanha,
            "products_available": produtos_disponiveis,
            "current_user": current_user,
        },
    )


@router.post("/{campanha_id}/editar")
async def atualizar_campanha(
    campanha_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Salva alterações de uma campanha."""
    form = await request.form()
    ServicoCampanhas(db, current_user).atualizar(campanha_id, form)
    return RedirectResponse(f"/campanhas/{campanha_id}/editar", status_code=302)


@router.post("/{campanha_id}/excluir")
def excluir_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Remove uma campanha."""
    ServicoCampanhas(db, current_user).excluir(campanha_id)
    return RedirectResponse("/campanhas", status_code=302)


@router.post("/{campanha_id}/produtos")
async def adicionar_produto_campanha(
    campanha_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Adiciona um produto à campanha."""
    form = await request.form()
    ServicoCampanhas(db, current_user).adicionar_produto(campanha_id, form)
    return RedirectResponse(f"/campanhas/{campanha_id}/editar", status_code=302)


@router.post("/{campanha_id}/produtos/{item_id}/excluir")
def remover_produto_campanha(
    campanha_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("campanhas")),
):
    """Remove um produto da campanha."""
    ServicoCampanhas(db, current_user).remover_produto(campanha_id, item_id)
    return RedirectResponse(f"/campanhas/{campanha_id}/editar", status_code=302)
