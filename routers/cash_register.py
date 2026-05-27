from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/caixa", tags=["caixa"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def cash_register_page(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    open_register = db.query(models.CashRegister).options(joinedload(models.CashRegister.user)).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()

    history = db.query(models.CashRegister).options(joinedload(models.CashRegister.user)).filter(
        models.CashRegister.user_id == current_user.id
    ).order_by(models.CashRegister.opened_at.desc()).limit(10).all()

    return templates.TemplateResponse("cash_register/index.html", {
        "request": request, "open_register": open_register,
        "history": history, "current_user": current_user
    })


@router.post("/abrir")
async def open_cash_register(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    existing = db.query(models.CashRegister).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()
    if existing:
        return RedirectResponse("/caixa", status_code=302)

    form = await request.form()
    register = models.CashRegister(
        user_id=current_user.id,
        opening_balance=float(form.get("opening_balance") or 0),
        notes=form.get("notes") or None
    )
    db.add(register); db.commit()
    return RedirectResponse("/caixa", status_code=302)


@router.post("/fechar")
async def close_cash_register(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    register = db.query(models.CashRegister).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()
    if not register:
        return RedirectResponse("/caixa", status_code=302)

    form = await request.form()
    register.status = models.CashRegisterStatus.fechado
    register.closing_balance = float(form.get("closing_balance") or 0)
    register.closed_at = datetime.utcnow()
    register.notes = form.get("notes") or register.notes
    db.commit()
    return RedirectResponse(f"/caixa/{register.id}", status_code=302)


@router.get("/{register_id}", response_class=HTMLResponse)
def cash_register_detail(register_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    register = db.query(models.CashRegister).options(
        joinedload(models.CashRegister.user),
        joinedload(models.CashRegister.sales).joinedload(models.Sale.payments),
        joinedload(models.CashRegister.cash_movements)
    ).filter(models.CashRegister.id == register_id).first()

    if not register:
        return RedirectResponse("/caixa", status_code=302)

    sales_total = sum(float(s.total) for s in register.sales if s.status == models.SaleStatus.finalizada)
    cash_in = sum(float(m.amount) for m in register.cash_movements if m.type == models.CashMovementType.suprimento)
    cash_out = sum(float(m.amount) for m in register.cash_movements if m.type == models.CashMovementType.sangria)

    by_method = {}
    for sale in register.sales:
        if sale.status == models.SaleStatus.finalizada:
            for pay in sale.payments:
                method = pay.method.value
                by_method[method] = by_method.get(method, 0) + float(pay.amount)

    return templates.TemplateResponse("cash_register/detail.html", {
        "request": request, "register": register, "current_user": current_user,
        "sales_total": sales_total, "cash_in": cash_in, "cash_out": cash_out,
        "by_method": by_method
    })


@router.post("/{register_id}/movimentacao")
async def cash_movement(register_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    form = await request.form()
    mv = models.CashMovement(
        cash_register_id=register_id,
        type=models.CashMovementType(form.get("type")),
        amount=float(form.get("amount")),
        reason=form.get("reason") or None,
        user_id=current_user.id
    )
    db.add(mv); db.commit()
    return RedirectResponse(f"/caixa/{register_id}", status_code=302)
