from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import date, timedelta
from database import get_db
import models, auth as auth_utils
from servicos import relatorio_caixa
from routers.company import get_or_create_company

router = APIRouter(prefix="/relatorios", tags=["relatorios"])
templates = Jinja2Templates(directory="templates")
templates.env.filters["brl"] = relatorio_caixa.formatar_moeda
templates.env.filters["brl_sinal"] = lambda v: relatorio_caixa.formatar_valor(v, sinal=True)


@router.get("", response_class=HTMLResponse)
def reports_home(request: Request, current_user: models.User = Depends(auth_utils.require_permission("relatorios"))):
    return templates.TemplateResponse(request, "reports/index.html", {"current_user": current_user})


@router.get("/vendas", response_class=HTMLResponse)
def sales_report(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("relatorios"))
):
    today = date.today()
    if not date_from:
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = today.isoformat()

    sales = db.query(models.Sale).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        func.date(models.Sale.created_at) >= date_from,
        func.date(models.Sale.created_at) <= date_to
    ).all()

    total_sales = sum(float(s.total) for s in sales)
    total_discount = sum(float(s.discount) for s in sales)
    count = len(sales)
    avg_ticket = total_sales / count if count > 0 else 0

    by_day = {}
    for sale in sales:
        day = sale.created_at.date().isoformat()
        by_day[day] = by_day.get(day, 0) + float(sale.total)

    by_payment = {}
    for sale in sales:
        for pay in sale.payments:
            method = pay.method.value
            by_payment[method] = by_payment.get(method, 0) + float(pay.amount)

    return templates.TemplateResponse(request, "reports/sales.html", {
        "current_user": current_user,
        "date_from": date_from, "date_to": date_to,
        "total_sales": total_sales, "total_discount": total_discount,
        "count": count, "avg_ticket": avg_ticket,
        "by_day": sorted(by_day.items()), "by_payment": by_payment
    })


@router.get("/produtos", response_class=HTMLResponse)
def products_report(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("relatorios"))
):
    today = date.today()
    if not date_from:
        date_from = today.replace(day=1).isoformat()
    if not date_to:
        date_to = today.isoformat()

    top_products = db.query(
        models.Product.name,
        func.sum(models.SaleItem.quantity).label("qty_sold"),
        func.sum(models.SaleItem.total).label("revenue")
    ).join(models.SaleItem).join(models.Sale).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        func.date(models.Sale.created_at) >= date_from,
        func.date(models.Sale.created_at) <= date_to
    ).group_by(models.Product.id, models.Product.name).order_by(
        func.sum(models.SaleItem.total).desc()
    ).limit(20).all()

    low_stock = db.query(models.Product).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).order_by(models.Product.stock_quantity).all()

    return templates.TemplateResponse(request, "reports/products.html", {
        "current_user": current_user,
        "date_from": date_from, "date_to": date_to,
        "top_products": top_products, "low_stock": low_stock
    })


@router.get("/financeiro", response_class=HTMLResponse)
def financial_report(
    request: Request,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("relatorios"))
):
    today = date.today()
    month = month or today.month
    year = year or today.year

    sales_total = db.query(func.sum(models.Sale.total)).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        extract('month', models.Sale.created_at) == month,
        extract('year', models.Sale.created_at) == year
    ).scalar() or 0

    expenses_total = db.query(func.sum(models.Expense.amount)).filter(
        extract('month', models.Expense.date) == month,
        extract('year', models.Expense.date) == year
    ).scalar() or 0

    purchases_total = db.query(func.sum(models.Purchase.total)).filter(
        models.Purchase.status == models.PurchaseStatus.recebida,
        extract('month', models.Purchase.created_at) == month,
        extract('year', models.Purchase.created_at) == year
    ).scalar() or 0

    expenses = db.query(models.Expense).filter(
        extract('month', models.Expense.date) == month,
        extract('year', models.Expense.date) == year
    ).order_by(models.Expense.date).all()

    profit = float(sales_total) - float(expenses_total) - float(purchases_total)

    return templates.TemplateResponse(request, "reports/financial.html", {
        "current_user": current_user,
        "month": month, "year": year,
        "sales_total": sales_total, "expenses_total": expenses_total,
        "purchases_total": purchases_total, "profit": profit,
        "expenses": expenses
    })


@router.get("/estoque-baixo", response_class=HTMLResponse)
def low_stock_report(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_permission("relatorios"))):
    products = db.query(models.Product).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).order_by(models.Product.stock_quantity).all()
    return templates.TemplateResponse(request, "reports/low_stock.html", {"products": products, "current_user": current_user})


@router.get("/fechamento-caixa", response_class=HTMLResponse)
def cash_closing_report(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    caixa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente),
):
    """Relatório de fechamento de caixa (consolidado + por caixa). Restrito a admin e gerente."""
    today = date.today().isoformat()
    date_from = date_from or today
    date_to = date_to or today
    caixa_id = int(caixa_id) if caixa_id else None

    dados = relatorio_caixa.montar_relatorio(db, date_from, date_to, caixa_id)
    empresa = get_or_create_company(db)

    caixas_disponiveis = relatorio_caixa.caixas_no_periodo(db, date_from, date_to)

    whatsapp_texto = relatorio_caixa.texto_resumo_whatsapp(dados, empresa.trade_name or "Mercadinho")

    return templates.TemplateResponse(request, "reports/cash_closing.html", {
        "current_user": current_user,
        "date_from": date_from, "date_to": date_to, "caixa_id": caixa_id,
        "caixas_disponiveis": caixas_disponiveis,
        "dados": dados,
        "whatsapp_texto": whatsapp_texto,
    })


@router.get("/fechamento-caixa/pdf")
def cash_closing_report_pdf(
    formato: str = "a4",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    caixa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente),
):
    """Gera o PDF do relatório de fechamento de caixa, em A4 ou em formato de cupom. Restrito a admin e gerente."""
    today = date.today().isoformat()
    date_from = date_from or today
    date_to = date_to or today
    caixa_id = int(caixa_id) if caixa_id else None

    dados = relatorio_caixa.montar_relatorio(db, date_from, date_to, caixa_id)
    empresa = get_or_create_company(db)
    nome_empresa = empresa.trade_name or "Mercadinho"

    if formato == "cupom":
        pdf_bytes = relatorio_caixa.gerar_pdf_cupom(dados, nome_empresa)
    else:
        pdf_bytes = relatorio_caixa.gerar_pdf_a4(dados, nome_empresa)

    nome_arquivo = f"fechamento-caixa-{date_from}-a-{date_to}-{formato}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nome_arquivo}"'},
    )
