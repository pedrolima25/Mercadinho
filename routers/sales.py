from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, cast, Date
from typing import Optional
from datetime import datetime, date
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/vendas", tags=["vendas"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_sales(
    request: Request,
    page: int = 1,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user)
):
    q = db.query(models.Sale).options(
        joinedload(models.Sale.customer),
        joinedload(models.Sale.user),
        joinedload(models.Sale.items)
    )
    if date_from:
        q = q.filter(func.date(models.Sale.created_at) >= date_from)
    if date_to:
        q = q.filter(func.date(models.Sale.created_at) <= date_to)
    if status:
        q = q.filter(models.Sale.status == status)
    total = q.count()
    per_page = 20
    sales = q.order_by(models.Sale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse("sales/index.html", {
        "request": request, "sales": sales, "page": page, "total": total,
        "per_page": per_page, "date_from": date_from, "date_to": date_to,
        "status": status, "current_user": current_user
    })


@router.get("/{sale_id}", response_class=HTMLResponse)
def sale_detail(sale_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    sale = db.query(models.Sale).options(
        joinedload(models.Sale.customer), joinedload(models.Sale.user),
        joinedload(models.Sale.items).joinedload(models.SaleItem.product),
        joinedload(models.Sale.payments)
    ).filter(models.Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("sales/detail.html", {"request": request, "sale": sale, "current_user": current_user})


@router.post("/{sale_id}/cancelar")
def cancel_sale(sale_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    sale = db.query(models.Sale).filter(models.Sale.id == sale_id).first()
    if sale and sale.status == models.SaleStatus.finalizada:
        sale.status = models.SaleStatus.cancelada
        for item in sale.items:
            product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
            if product:
                product.stock_quantity = float(product.stock_quantity) + float(item.quantity)
                mv = models.StockMovement(
                    product_id=item.product_id, type=models.MovementType.entrada,
                    quantity=float(item.quantity), reason=f"Cancelamento venda #{sale_id}",
                    user_id=current_user.id
                )
                db.add(mv)
        db.commit()
    return RedirectResponse(f"/vendas/{sale_id}", status_code=302)


# ─── PDV ──────────────────────────────────────────────────────────────────────
pdv_router = APIRouter(prefix="/pdv", tags=["pdv"])


@pdv_router.get("", response_class=HTMLResponse)
def pdv_page(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    open_register = db.query(models.CashRegister).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()
    customers = db.query(models.Customer).filter(models.Customer.is_active == True).order_by(models.Customer.name).all()
    return templates.TemplateResponse("sales/pdv.html", {
        "request": request, "current_user": current_user,
        "open_register": open_register, "customers": customers
    })


@pdv_router.post("/finalizar")
async def finalize_sale(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    import json
    data = await request.json()
    items_data = data.get("items", [])
    payments_data = data.get("payments", [])
    customer_id = data.get("customer_id")
    discount = float(data.get("discount", 0))

    if not items_data:
        return JSONResponse({"error": "Carrinho vazio"}, status_code=400)

    open_register = db.query(models.CashRegister).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()

    subtotal = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items_data)
    total = max(0, subtotal - discount)

    total_paid = sum(float(p["amount"]) for p in payments_data)
    if total_paid < total:
        return JSONResponse({"error": "Pagamento insuficiente"}, status_code=400)

    sale = models.Sale(
        cash_register_id=open_register.id if open_register else None,
        customer_id=customer_id or None,
        user_id=current_user.id,
        subtotal=subtotal,
        discount=discount,
        total=total,
        status=models.SaleStatus.finalizada,
        finalized_at=datetime.utcnow()
    )
    db.add(sale)
    db.flush()

    for item_data in items_data:
        product = db.query(models.Product).filter(models.Product.id == item_data["product_id"]).first()
        if not product:
            continue
        qty = float(item_data["quantity"])
        unit_price = float(item_data["unit_price"])
        item_discount = float(item_data.get("discount", 0))
        item_total = qty * unit_price - item_discount

        sale_item = models.SaleItem(
            sale_id=sale.id, product_id=product.id,
            quantity=qty, unit_price=unit_price,
            discount=item_discount, total=item_total
        )
        db.add(sale_item)
        product.stock_quantity = max(0, float(product.stock_quantity) - qty)
        mv = models.StockMovement(
            product_id=product.id, type=models.MovementType.saida,
            quantity=qty, reason=f"Venda #{sale.id}",
            reference_id=sale.id, reference_type="sale", user_id=current_user.id
        )
        db.add(mv)

    for pay_data in payments_data:
        payment = models.Payment(
            sale_id=sale.id,
            method=models.PaymentMethod(pay_data["method"]),
            amount=float(pay_data["amount"])
        )
        db.add(payment)

        if pay_data["method"] == "fiado" and customer_id:
            customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
            if customer:
                customer.balance = float(customer.balance) + float(pay_data["amount"])
                ar = models.AccountReceivable(
                    customer_id=customer_id,
                    description=f"Fiado - Venda #{sale.id}",
                    amount=float(pay_data["amount"]),
                    due_date=date.today()
                )
                db.add(ar)

    db.commit()
    troco = total_paid - total
    return JSONResponse({"success": True, "sale_id": sale.id, "troco": troco})


@pdv_router.post("/verificar-supervisor")
async def verificar_supervisor(request: Request, db: Session = Depends(get_db)):
    """Verifica se as credenciais pertencem a um supervisor (admin ou gerente)."""
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return JSONResponse({"ok": False, "error": "Informe usuário e senha"})

    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.is_active == True
    ).first()

    if not user:
        return JSONResponse({"ok": False, "error": "Usuário não encontrado"})

    if not auth_utils.verify_password(password, user.hashed_password):
        return JSONResponse({"ok": False, "error": "Senha incorreta"})

    if user.role not in (models.UserRole.admin, models.UserRole.gerente):
        return JSONResponse({"ok": False, "error": "Usuário sem permissão de supervisor"})

    return JSONResponse({"ok": True, "supervisor": user.full_name})
