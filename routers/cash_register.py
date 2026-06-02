"""
Rotas de Caixa
==============
Responsabilidade: receber requisições HTTP e delegar ao ServicoCaixa.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.caixa import ServicoCaixa

router = APIRouter(prefix="/caixa", tags=["caixa"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def pagina_caixa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Tela principal do caixa: caixa aberto e histórico."""
    dados = ServicoCaixa(db).visao_geral(current_user)
    return templates.TemplateResponse(
        request, "cash_register/index.html",
        {**dados, "current_user": current_user},
    )


@router.post("/abrir")
async def abrir_caixa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Abre o caixa com saldo inicial."""
    form = await request.form()
    ServicoCaixa(db).abrir(form, current_user)
    return RedirectResponse("/caixa", status_code=302)


@router.post("/fechar")
async def fechar_caixa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Fecha o caixa com saldo final."""
    form = await request.form()
    caixa = ServicoCaixa(db).fechar(form, current_user)
    return RedirectResponse(f"/caixa/{caixa.id}", status_code=302)


@router.get("/{register_id}", response_class=HTMLResponse)
def detalhe_caixa(
    register_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Detalhes de um caixa: vendas, movimentações e totais."""
    dados = ServicoCaixa(db).detalhe(register_id)
    return templates.TemplateResponse(
        request, "cash_register/detail.html",
        {**dados, "current_user": current_user},
    )


@router.post("/{register_id}/movimentacao")
async def movimentacao_caixa(
    register_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Registra sangria ou suprimento no caixa."""
    form = await request.form()
    ServicoCaixa(db).movimentacao(register_id, form, current_user)
    return RedirectResponse(f"/caixa/{register_id}", status_code=302)
