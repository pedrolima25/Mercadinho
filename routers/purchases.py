from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/compras", tags=["compras"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_purchases(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    q = db.query(models.Purchase).options(joinedload(models.Purchase.supplier))
    if status:
        q = q.filter(models.Purchase.status == status)
    total = q.count()
    per_page = 20
    purchases = q.order_by(models.Purchase.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return templates.TemplateResponse("purchases/index.html", {
        "request": request, "purchases": purchases, "status": status,
        "page": page, "total": total, "per_page": per_page, "current_user": current_user
    })


@router.get("/novo", response_class=HTMLResponse)
def new_purchase(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    suppliers = db.query(models.Supplier).filter(models.Supplier.is_active == True).all()
    products = db.query(models.Product).filter(models.Product.is_active == True).order_by(models.Product.name).all()
    return templates.TemplateResponse("purchases/form.html", {
        "request": request, "purchase": None, "suppliers": suppliers,
        "products": products, "current_user": current_user
    })


@router.post("/novo")
async def create_purchase(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    supplier_id = int(form.get("supplier_id")) if form.get("supplier_id") else None
    invoice = form.get("invoice_number") or None
    expected_date = form.get("expected_date") or None
    notes = form.get("notes") or None

    product_ids = form.getlist("product_id[]")
    quantities = form.getlist("quantity[]")
    unit_costs = form.getlist("unit_cost[]")

    if not product_ids:
        return RedirectResponse("/compras/novo", status_code=302)

    total = sum(float(q) * float(c) for q, c in zip(quantities, unit_costs))

    purchase = models.Purchase(
        supplier_id=supplier_id, user_id=current_user.id,
        invoice_number=invoice, notes=notes,
        expected_date=expected_date, total=total
    )
    db.add(purchase)
    db.flush()

    for pid, qty, cost in zip(product_ids, quantities, unit_costs):
        item = models.PurchaseItem(
            purchase_id=purchase.id, product_id=int(pid),
            quantity=float(qty), unit_cost=float(cost),
            total=float(qty) * float(cost)
        )
        db.add(item)

    db.commit()
    return RedirectResponse(f"/compras/{purchase.id}", status_code=302)


@router.get("/{purchase_id}", response_class=HTMLResponse)
def purchase_detail(purchase_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    purchase = db.query(models.Purchase).options(
        joinedload(models.Purchase.supplier),
        joinedload(models.Purchase.items).joinedload(models.PurchaseItem.product)
    ).filter(models.Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("purchases/detail.html", {"request": request, "purchase": purchase, "current_user": current_user})


@router.post("/{purchase_id}/receber")
async def receive_purchase(purchase_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    purchase = db.query(models.Purchase).options(joinedload(models.Purchase.items)).filter(models.Purchase.id == purchase_id).first()
    if not purchase or purchase.status != models.PurchaseStatus.pendente:
        return RedirectResponse(f"/compras/{purchase_id}", status_code=302)

    purchase.status = models.PurchaseStatus.recebida
    purchase.received_date = date.today()

    for item in purchase.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if product:
            product.stock_quantity = float(product.stock_quantity) + float(item.quantity)
            if float(item.unit_cost) > 0:
                product.cost_price = float(item.unit_cost)
            mv = models.StockMovement(
                product_id=item.product_id, type=models.MovementType.entrada,
                quantity=float(item.quantity),
                reason=f"Compra #{purchase_id}",
                reference_id=purchase_id, reference_type="purchase",
                user_id=current_user.id
            )
            db.add(mv)

    db.commit()
    return RedirectResponse(f"/compras/{purchase_id}", status_code=302)


@router.post("/{purchase_id}/cancelar")
def cancel_purchase(purchase_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    purchase = db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()
    if purchase and purchase.status == models.PurchaseStatus.pendente:
        purchase.status = models.PurchaseStatus.cancelada
        db.commit()
    return RedirectResponse(f"/compras/{purchase_id}", status_code=302)
