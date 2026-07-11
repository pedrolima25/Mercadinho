"""
Rotas de Promoções
==================
Responsabilidade: receber requisições HTTP e delegar ao ServicoPromocoes.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.promocoes import ServicoPromocoes
from servicos.produtos import ServicoProdutos

router = APIRouter(prefix="/promocoes", tags=["promocoes"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_promocoes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Lista todas as promoções cadastradas."""
    promocoes = ServicoPromocoes(db, current_user).listar()
    return templates.TemplateResponse(
        request, "promotions/index.html",
        {"promotions": promocoes, "current_user": current_user},
    )


@router.get("/novo", response_class=HTMLResponse)
def nova_promocao(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Formulário de nova promoção."""
    produtos, _ = ServicoProdutos(db, current_user).listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "promotions/form.html",
        {"promotion": None, "products": produtos, "current_user": current_user},
    )


@router.post("/novo")
async def criar_promocao(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Cria uma nova promoção."""
    form = await request.form()
    ServicoPromocoes(db, current_user).criar(form)
    return RedirectResponse("/promocoes", status_code=302)


@router.get("/{promotion_id}/editar", response_class=HTMLResponse)
def editar_promocao(
    promotion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Formulário de edição de promoção."""
    servico = ServicoPromocoes(db, current_user)
    promocao = servico.obter_ou_erro(promotion_id)
    produtos, _ = ServicoProdutos(db, current_user).listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "promotions/form.html",
        {"promotion": promocao, "products": produtos, "current_user": current_user},
    )


@router.post("/{promotion_id}/editar")
async def atualizar_promocao(
    promotion_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Salva alterações de uma promoção."""
    form = await request.form()
    ServicoPromocoes(db, current_user).atualizar(promotion_id, form)
    return RedirectResponse("/promocoes", status_code=302)


@router.post("/{promotion_id}/excluir")
def excluir_promocao(
    promotion_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("promocoes")),
):
    """Remove uma promoção."""
    ServicoPromocoes(db, current_user).excluir(promotion_id)
    return RedirectResponse("/promocoes", status_code=302)
