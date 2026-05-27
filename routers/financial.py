from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from datetime import date
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/financeiro", tags=["financeiro"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def financial_overview(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    today = date.today()
    overdue_pay = db.query(func.sum(models.AccountPayable.amount)).filter(
        models.AccountPayable.status == models.AccountStatus.pendente,
        models.AccountPayable.due_date < today
    ).scalar() or 0
    pending_pay = db.query(func.sum(models.AccountPayable.amount)).filter(
        models.AccountPayable.status == models.AccountStatus.pendente,
        models.AccountPayable.due_date >= today
    ).scalar() or 0
    pending_rec = db.query(func.sum(models.AccountReceivable.amount)).filter(
        models.AccountReceivable.status == models.AccountStatus.pendente
    ).scalar() or 0
    month_expense = db.query(func.sum(models.Expense.amount)).filter(
        func.extract('month', models.Expense.date) == today.month,
        func.extract('year', models.Expense.date) == today.year
    ).scalar() or 0

    recent_payable = db.query(models.AccountPayable).options(joinedload(models.AccountPayable.supplier)).filter(
        models.AccountPayable.status == models.AccountStatus.pendente
    ).order_by(models.AccountPayable.due_date).limit(10).all()
    recent_receivable = db.query(models.AccountReceivable).options(joinedload(models.AccountReceivable.customer)).filter(
        models.AccountReceivable.status == models.AccountStatus.pendente
    ).order_by(models.AccountReceivable.due_date).limit(10).all()

    return templates.TemplateResponse("financial/index.html", {
        "request": request, "current_user": current_user,
        "overdue_pay": overdue_pay, "pending_pay": pending_pay,
        "pending_rec": pending_rec, "month_expense": month_expense,
        "recent_payable": recent_payable, "recent_receivable": recent_receivable,
        "today": today.isoformat()
    })


# ─── Contas a Pagar ───────────────────────────────────────────────────────────
@router.get("/contas-pagar", response_class=HTMLResponse)
def accounts_payable(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    q = db.query(models.AccountPayable).options(joinedload(models.AccountPayable.supplier))
    if status:
        q = q.filter(models.AccountPayable.status == status)
    total = q.count()
    per_page = 20
    items = q.order_by(models.AccountPayable.due_date).offset((page - 1) * per_page).limit(per_page).all()
    suppliers = db.query(models.Supplier).filter(models.Supplier.is_active == True).all()
    return templates.TemplateResponse("financial/accounts_payable.html", {
        "request": request, "items": items, "suppliers": suppliers, "status": status,
        "page": page, "total": total, "per_page": per_page, "current_user": current_user,
        "today": date.today().isoformat()
    })


@router.post("/contas-pagar/novo")
async def create_payable(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.AccountPayable(
        supplier_id=int(form.get("supplier_id")) if form.get("supplier_id") else None,
        description=form.get("description"),
        amount=float(form.get("amount")),
        due_date=form.get("due_date"),
        notes=form.get("notes") or None
    )
    db.add(item); db.commit()
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


@router.post("/contas-pagar/{item_id}/pagar")
async def pay_payable(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.AccountPayable).filter(models.AccountPayable.id == item_id).first()
    form = await request.form()
    if item:
        item.paid_date = form.get("paid_date") or date.today()
        item.paid_amount = float(form.get("paid_amount") or item.amount)
        item.status = models.AccountStatus.pago
        db.commit()
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


@router.post("/contas-pagar/{item_id}/excluir")
def delete_payable(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.AccountPayable).filter(models.AccountPayable.id == item_id).first()
    if item:
        item.status = models.AccountStatus.cancelado; db.commit()
    return RedirectResponse("/financeiro/contas-pagar", status_code=302)


# ─── Contas a Receber ─────────────────────────────────────────────────────────
@router.get("/contas-receber", response_class=HTMLResponse)
def accounts_receivable(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    q = db.query(models.AccountReceivable).options(joinedload(models.AccountReceivable.customer))
    if status:
        q = q.filter(models.AccountReceivable.status == status)
    total = q.count()
    per_page = 20
    items = q.order_by(models.AccountReceivable.due_date).offset((page - 1) * per_page).limit(per_page).all()
    customers = db.query(models.Customer).filter(models.Customer.is_active == True).all()
    return templates.TemplateResponse("financial/accounts_receivable.html", {
        "request": request, "items": items, "customers": customers, "status": status,
        "page": page, "total": total, "per_page": per_page, "current_user": current_user,
        "today": date.today().isoformat()
    })


@router.post("/contas-receber/novo")
async def create_receivable(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.AccountReceivable(
        customer_id=int(form.get("customer_id")) if form.get("customer_id") else None,
        description=form.get("description"),
        amount=float(form.get("amount")),
        due_date=form.get("due_date"),
        notes=form.get("notes") or None
    )
    db.add(item); db.commit()
    return RedirectResponse("/financeiro/contas-receber", status_code=302)


@router.post("/contas-receber/{item_id}/receber")
async def receive_receivable(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.AccountReceivable).filter(models.AccountReceivable.id == item_id).first()
    form = await request.form()
    if item:
        item.paid_date = form.get("paid_date") or date.today()
        item.paid_amount = float(form.get("paid_amount") or item.amount)
        item.status = models.AccountStatus.pago
        if item.customer_id:
            customer = db.query(models.Customer).filter(models.Customer.id == item.customer_id).first()
            if customer:
                customer.balance = max(0, float(customer.balance) - float(item.paid_amount))
        db.commit()
    return RedirectResponse("/financeiro/contas-receber", status_code=302)


# ─── Despesas ─────────────────────────────────────────────────────────────────
@router.get("/despesas", response_class=HTMLResponse)
def expenses(request: Request, page: int = 1, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    total = db.query(models.Expense).count()
    per_page = 20
    items = db.query(models.Expense).order_by(models.Expense.date.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse("financial/expenses.html", {
        "request": request, "items": items, "page": page, "total": total,
        "per_page": per_page, "current_user": current_user,
        "today": date.today().isoformat()
    })


@router.post("/despesas/novo")
async def create_expense(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Expense(
        description=form.get("description"),
        category=form.get("category") or None,
        amount=float(form.get("amount")),
        date=form.get("date"),
        notes=form.get("notes") or None,
        user_id=current_user.id
    )
    db.add(item); db.commit()
    return RedirectResponse("/financeiro/despesas", status_code=302)


@router.post("/despesas/{item_id}/excluir")
def delete_expense(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Expense).filter(models.Expense.id == item_id).first()
    if item:
        db.delete(item); db.commit()
    return RedirectResponse("/financeiro/despesas", status_code=302)
