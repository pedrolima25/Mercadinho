"""
Rotas de Vendas e PDV
=====================
Responsabilidade: receber requisições HTTP e delegar a ServicoVendas / ServicoPDV.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.vendas import ServicoVendas, ServicoPDV

router = APIRouter(prefix="/vendas", tags=["vendas"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_vendas(
    request: Request,
    page: int = 1,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Lista todas as vendas com filtros de data e status."""
    vendas, total = ServicoVendas(db).listar(
        data_inicio=date_from,
        data_fim=date_to,
        status=status,
        pagina=page,
    )
    return templates.TemplateResponse(
        request, "sales/index.html",
        {
            "sales": vendas, "page": page, "total": total, "per_page": 20,
            "date_from": date_from, "date_to": date_to, "status": status,
            "current_user": current_user,
        },
    )


@router.get("/{sale_id}", response_class=HTMLResponse)
def detalhe_venda(
    sale_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Detalhes de uma venda: itens, pagamentos e devoluções."""
    venda = ServicoVendas(db).obter_ou_erro(sale_id)
    return templates.TemplateResponse(
        request, "sales/detail.html",
        {"sale": venda, "current_user": current_user},
    )


@router.post("/{sale_id}/cancelar")
def cancelar_venda(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("vendas")),
):
    """Cancela uma venda e devolve o estoque."""
    ServicoVendas(db).cancelar(sale_id, current_user)
    return RedirectResponse(f"/vendas/{sale_id}", status_code=302)


@router.get("/{sale_id}/devolver", response_class=HTMLResponse)
def formulario_devolucao(
    sale_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("vendas")),
):
    """Formulário para registrar devolução de itens."""
    servico = ServicoVendas(db)
    venda = servico.obter_ou_erro(sale_id)

    if venda.status != models.SaleStatus.finalizada:
        return RedirectResponse(f"/vendas/{sale_id}", status_code=302)

    ja_devolvido = servico.quantidade_devolvida_por_item(venda)
    return templates.TemplateResponse(
        request, "sales/return_form.html",
        {
            "sale": venda,
            "returned_qty": ja_devolvido,
            "current_user": current_user,
        },
    )


@router.post("/{sale_id}/devolver")
async def registrar_devolucao(
    sale_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("vendas")),
):
    """Registra devolução de itens e repõe estoque."""
    form = await request.form()
    devolucao = ServicoVendas(db).devolver(sale_id, form, current_user)
    return RedirectResponse(f"/vendas/{sale_id}?devolucao={devolucao.id}", status_code=302)


# ── PDV ─────────────────────────────────────────────────────────────────────

pdv_router = APIRouter(prefix="/pdv", tags=["pdv"])


@pdv_router.get("", response_class=HTMLResponse)
def pagina_pdv(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Tela do PDV: frente de caixa."""
    dados = ServicoPDV(db).pagina_pdv(current_user)
    return templates.TemplateResponse(
        request, "sales/pdv.html",
        {**dados, "current_user": current_user},
    )


@pdv_router.post("/finalizar")
async def finalizar_venda(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Finaliza uma venda: valida, salva, atualiza estoque e processa pagamentos."""
    dados = await request.json()
    resultado = ServicoPDV(db).finalizar_venda(dados, current_user)
    return JSONResponse(resultado)


@pdv_router.get("/cliente/{cliente_id}/credito")
def credito_cliente(
    cliente_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Retorna saldo devedor e limite de crédito do cliente para o PDV."""
    cliente = db.query(models.Customer).filter(models.Customer.id == cliente_id).first()
    if not cliente:
        return JSONResponse({"error": "Cliente não encontrado"}, status_code=404)
    limite   = float(cliente.credit_limit or 0)
    saldo    = float(cliente.balance or 0)
    disponivel = max(0.0, limite - saldo)
    return JSONResponse({
        "id": cliente.id,
        "name": cliente.name,
        "credit_limit": limite,
        "balance": saldo,
        "disponivel": disponivel,
    })


@pdv_router.post("/verificar-supervisor")
async def verificar_supervisor(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Verifica se as credenciais são de um supervisor (para autorizar descontos)."""
    dados = await request.json()
    resultado = ServicoPDV(db).verificar_supervisor(dados)
    return JSONResponse(resultado)
