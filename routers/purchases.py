"""
Rotas de Compras
================
Responsabilidade: receber requisições HTTP e delegar ao ServicoCompras.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.compras import ServicoCompras
from servicos.catalogos import ServicoCatalogos
from servicos.produtos import ServicoProdutos

router = APIRouter(prefix="/compras", tags=["compras"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_compras(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Lista pedidos de compra com filtro de status."""
    compras, total = ServicoCompras(db).listar(status=status, pagina=page)
    return templates.TemplateResponse(
        request, "purchases/index.html",
        {
            "purchases": compras,
            "status": status,
            "page": page,
            "total": total,
            "per_page": 20,
            "current_user": current_user,
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def nova_compra(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Formulário para nova compra."""
    fornecedores = ServicoCatalogos(db).listar_fornecedores()
    produtos, _ = ServicoProdutos(db).listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "purchases/form.html",
        {
            "purchase": None,
            "suppliers": fornecedores,
            "products": produtos,
            "current_user": current_user,
        },
    )


@router.post("/novo")
async def criar_compra(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Cria novo pedido de compra."""
    form = await request.form()
    compra = ServicoCompras(db).criar(form, current_user)
    return RedirectResponse(f"/compras/{compra.id}", status_code=302)


@router.get("/{purchase_id}", response_class=HTMLResponse)
def detalhe_compra(
    purchase_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Detalhes de uma compra."""
    compra = ServicoCompras(db).obter_ou_erro(purchase_id)
    return templates.TemplateResponse(
        request, "purchases/detail.html",
        {"purchase": compra, "current_user": current_user},
    )


@router.post("/{purchase_id}/receber")
async def receber_compra(
    purchase_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Marca compra como recebida, atualiza estoque e gera conta a pagar."""
    ServicoCompras(db).receber(purchase_id, current_user)
    return RedirectResponse(f"/compras/{purchase_id}", status_code=302)


@router.post("/{purchase_id}/cancelar")
def cancelar_compra(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("compras")),
):
    """Cancela compra pendente."""
    ServicoCompras(db).cancelar(purchase_id)
    return RedirectResponse(f"/compras/{purchase_id}", status_code=302)
