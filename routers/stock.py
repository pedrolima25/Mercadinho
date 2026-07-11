"""
Rotas de Estoque
================
Responsabilidade: receber requisições HTTP e delegar ao ServicoEstoque.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.estoque import ServicoEstoque
from servicos.produtos import ServicoProdutos

router = APIRouter(prefix="/estoque", tags=["estoque"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def visao_geral(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Tela principal de estoque: produtos críticos, lotes e últimas movimentações."""
    servico = ServicoEstoque(db, current_user)
    dados = servico.visao_geral()
    return templates.TemplateResponse(request, "stock/index.html", {**dados, "current_user": current_user})


@router.get("/movimentacao", response_class=HTMLResponse)
def nova_movimentacao(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Formulário para registrar movimentação de estoque."""
    servico_produtos = ServicoProdutos(db, current_user)
    produtos, _ = servico_produtos.listar(por_pagina=1000)
    return templates.TemplateResponse(
        request, "stock/movement.html",
        {"products": produtos, "current_user": current_user},
    )


@router.post("/movimentacao")
async def registrar_movimentacao(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Salva movimentação de estoque (entrada, saída ou ajuste)."""
    form = await request.form()
    ServicoEstoque(db, current_user).registrar_movimentacao(form, current_user)
    return RedirectResponse("/estoque", status_code=302)


@router.get("/lotes", response_class=HTMLResponse)
def lotes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Tela de lotes e validades."""
    servico = ServicoEstoque(db, current_user)
    dados = servico.listar_lotes()
    return templates.TemplateResponse(request, "stock/batches.html", {**dados, "current_user": current_user})


@router.post("/lotes/novo")
async def criar_lote(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Cria novo lote de produto."""
    form = await request.form()
    ServicoEstoque(db, current_user).criar_lote(form)
    return RedirectResponse("/estoque/lotes", status_code=302)


@router.post("/lotes/{lote_id}/perda")
async def registrar_perda_lote(
    lote_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Dá baixa (perda) de um lote — vencido ou avaria."""
    form = await request.form()
    ServicoEstoque(db, current_user).registrar_perda_lote(lote_id, form, current_user)
    return RedirectResponse("/estoque/lotes", status_code=302)


@router.get("/historico", response_class=HTMLResponse)
def historico(
    request: Request,
    product_id: Optional[int] = None,
    type: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("estoque")),
):
    """Histórico completo de movimentações com filtros."""
    servico = ServicoEstoque(db, current_user)
    servico_produtos = ServicoProdutos(db, current_user)

    movimentacoes, total = servico.historico(produto_id=product_id, tipo=type, pagina=page)
    produtos, _ = servico_produtos.listar(por_pagina=1000)

    return templates.TemplateResponse(
        request, "stock/history.html",
        {
            "movements": movimentacoes,
            "products": produtos,
            "product_id": product_id,
            "type": type,
            "page": page,
            "total": total,
            "per_page": 30,
            "current_user": current_user,
        },
    )
