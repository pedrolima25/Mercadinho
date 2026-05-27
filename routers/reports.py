from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import date, timedelta
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/relatorios", tags=["relatorios"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def reports_home(request: Request, current_user: models.User = Depends(auth_utils.require_gerente)):
    return templates.TemplateResponse("reports/index.html", {"request": request, "current_user": current_user})


@router.get("/vendas", response_class=HTMLResponse)
def sales_report(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
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

    return templates.TemplateResponse("reports/sales.html", {
        "request": request, "current_user": current_user,
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
    current_user: models.User = Depends(auth_utils.require_gerente)
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

    return templates.TemplateResponse("reports/products.html", {
        "request": request, "current_user": current_user,
        "date_from": date_from, "date_to": date_to,
        "top_products": top_products, "low_stock": low_stock
    })


@router.get("/financeiro", response_class=HTMLResponse)
def financial_report(
    request: Request,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
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

    return templates.TemplateResponse("reports/financial.html", {
        "request": request, "current_user": current_user,
        "month": month, "year": year,
        "sales_total": sales_total, "expenses_total": expenses_total,
        "purchases_total": purchases_total, "profit": profit,
        "expenses": expenses
    })


@router.get("/estoque-baixo", response_class=HTMLResponse)
def low_stock_report(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    products = db.query(models.Product).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).order_by(models.Product.stock_quantity).all()
    return templates.TemplateResponse("reports/low_stock.html", {"request": request, "products": products, "current_user": current_user})
