"""
Rotas Financeiras
=================
Responsabilidade: receber requisições HTTP e delegar ao ServicoFinanceiro.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.financeiro import ServicoFinanceiro
from servicos.catalogos import ServicoCatalogos

router = APIRouter(prefix="/financeiro", tags=["financeiro"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def visao_geral(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    """Dashboard financeiro: resumo de contas e despesas."""
    dados = ServicoFinanceiro(db).visao_geral()
    return templates.TemplateResponse(request, "financial/index.html", {**dados, "current_user": current_user})


# ── Contas a Pagar ─────────────────────────────────────────────────────────

@router.get("/contas-pagar", response_class=HTMLResponse)
def contas_pagar(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    servico = ServicoFinanceiro(db)
    fornecedores = ServicoCatalogos(db).listar_fornecedores()
    itens, total = servico.listar_contas_pagar(status=status, pagina=page)
    return templates.TemplateResponse(
        request, "financial/accounts_payable.html",
        {
            "items": itens, "suppliers": fornecedores, "status": status,
            "page": page, "total": total, "per_page": 20,
            "today": __import__("datetime").date.today().isoformat(),
            "current_user": current_user,
        },
    )


@router.post("/contas-pagar/novo")
async def criar_conta_pagar(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    form = await request.form()
    ServicoFinanceiro(db).criar_conta_pagar(form)
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


@router.post("/contas-pagar/{item_id}/pagar")
async def pagar_conta(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    form = await request.form()
    ServicoFinanceiro(db).pagar_conta(item_id, form)
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


@router.post("/contas-pagar/{item_id}/excluir")
def excluir_conta_pagar(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    ServicoFinanceiro(db).cancelar_conta_pagar(item_id)
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


# ── Contas a Receber ───────────────────────────────────────────────────────

@router.get("/contas-receber", response_class=HTMLResponse)
def contas_receber(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    servico = ServicoFinanceiro(db)
    clientes = ServicoCatalogos(db).listar_clientes()
    itens, total = servico.listar_contas_receber(status=status, pagina=page)
    return templates.TemplateResponse(
        request, "financial/accounts_receivable.html",
        {
            "items": itens, "customers": clientes, "status": status,
            "page": page, "total": total, "per_page": 20,
            "today": __import__("datetime").date.today().isoformat(),
            "current_user": current_user,
        },
    )


@router.post("/contas-receber/novo")
async def criar_conta_receber(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    form = await request.form()
    ServicoFinanceiro(db).criar_conta_receber(form)
    return RedirectResponse("/financeiro/contas-receber", status_code=302)


@router.post("/contas-receber/{item_id}/receber")
async def receber_conta(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    form = await request.form()
    ServicoFinanceiro(db).receber_conta(item_id, form)
    return RedirectResponse("/financeiro/contas-receber", status_code=302)


# ── Despesas ───────────────────────────────────────────────────────────────

@router.get("/despesas", response_class=HTMLResponse)
def despesas(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    itens, total = ServicoFinanceiro(db).listar_despesas(pagina=page)
    return templates.TemplateResponse(
        request, "financial/expenses.html",
        {
            "items": itens, "page": page, "total": total, "per_page": 20,
            "today": __import__("datetime").date.today().isoformat(),
            "current_user": current_user,
        },
    )


@router.post("/despesas/novo")
async def criar_despesa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    form = await request.form()
    ServicoFinanceiro(db).criar_despesa(form, current_user)
    return RedirectResponse("/financeiro/despesas", status_code=302)


@router.post("/despesas/{item_id}/excluir")
def excluir_despesa(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("financeiro")),
):
    ServicoFinanceiro(db).excluir_despesa(item_id)
    return RedirectResponse("/financeiro/despesas", status_code=302)
