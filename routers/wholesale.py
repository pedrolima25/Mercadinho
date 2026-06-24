"""
Rotas de Venda no Atacado
==========================
Responsabilidade: receber requisições HTTP e delegar ao ServicoAtacado.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.atacado import ServicoAtacado
from servicos.produtos import ServicoProdutos

router = APIRouter(prefix="/atacado", tags=["atacado"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_atacado(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Lista todas as faixas de preço por quantidade."""
    tiers = ServicoAtacado(db).listar()
    return templates.TemplateResponse(
        request, "wholesale/index.html",
        {"tiers": tiers, "current_user": current_user},
    )


@router.get("/novo", response_class=HTMLResponse)
def novo_tier(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Formulário de nova faixa de preço."""
    produtos, _ = ServicoProdutos(db).listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "wholesale/form.html",
        {"tier": None, "products": produtos, "current_user": current_user},
    )


@router.post("/novo")
async def criar_tier(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Cria uma nova faixa de preço por quantidade."""
    form = await request.form()
    ServicoAtacado(db).criar(form)
    return RedirectResponse("/atacado", status_code=302)


@router.get("/{tier_id}/editar", response_class=HTMLResponse)
def editar_tier(
    tier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Formulário de edição de uma faixa de preço."""
    servico = ServicoAtacado(db)
    tier = servico.obter_ou_erro(tier_id)
    produtos, _ = ServicoProdutos(db).listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "wholesale/form.html",
        {"tier": tier, "products": produtos, "current_user": current_user},
    )


@router.post("/{tier_id}/editar")
async def atualizar_tier(
    tier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Salva alterações de uma faixa de preço."""
    form = await request.form()
    ServicoAtacado(db).atualizar(tier_id, form)
    return RedirectResponse("/atacado", status_code=302)


@router.post("/{tier_id}/excluir")
def excluir_tier(
    tier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("atacado")),
):
    """Remove uma faixa de preço."""
    ServicoAtacado(db).excluir(tier_id)
    return RedirectResponse("/atacado", status_code=302)
