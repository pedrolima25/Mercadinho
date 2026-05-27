from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date, timedelta
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/estoque", tags=["estoque"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def stock_overview(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    low_stock = db.query(models.Product).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).order_by(models.Product.name).all()

    expiring = db.query(models.ProductBatch).options(joinedload(models.ProductBatch.product)).filter(
        models.ProductBatch.expiry_date != None
    ).order_by(models.ProductBatch.expiry_date).limit(20).all()

    movements = db.query(models.StockMovement).options(
        joinedload(models.StockMovement.product),
        joinedload(models.StockMovement.user)
    ).order_by(models.StockMovement.created_at.desc()).limit(30).all()

    return templates.TemplateResponse("stock/index.html", {
        "request": request, "low_stock": low_stock, "expiring": expiring,
        "movements": movements, "current_user": current_user
    })


@router.get("/movimentacao", response_class=HTMLResponse)
def new_movement(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    products = db.query(models.Product).filter(models.Product.is_active == True).order_by(models.Product.name).all()
    return templates.TemplateResponse("stock/movement.html", {"request": request, "products": products, "current_user": current_user})


@router.post("/movimentacao")
async def create_movement(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    product_id = int(form.get("product_id"))
    quantity = float(form.get("quantity", 0))
    mov_type = form.get("type")
    reason = form.get("reason") or None

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product:
        if mov_type == "entrada":
            product.stock_quantity = float(product.stock_quantity) + quantity
        elif mov_type == "saida":
            product.stock_quantity = max(0, float(product.stock_quantity) - quantity)
        elif mov_type == "ajuste":
            product.stock_quantity = quantity

        mv = models.StockMovement(
            product_id=product_id, type=models.MovementType(mov_type),
            quantity=quantity, reason=reason, user_id=current_user.id
        )
        db.add(mv)
        db.commit()

    return RedirectResponse("/estoque", status_code=302)


@router.get("/lotes", response_class=HTMLResponse)
def batches(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    batches = db.query(models.ProductBatch).options(joinedload(models.ProductBatch.product)).order_by(models.ProductBatch.expiry_date).all()
    products = db.query(models.Product).filter(models.Product.is_active == True).all()
    today = date.today()
    near_date = (today + timedelta(days=30)).isoformat()
    return templates.TemplateResponse("stock/batches.html", {
        "request": request, "batches": batches, "products": products,
        "current_user": current_user,
        "now_date": today.isoformat(), "near_date": near_date
    })


@router.post("/lotes/novo")
async def create_batch(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    batch = models.ProductBatch(
        product_id=int(form.get("product_id")),
        batch_number=form.get("batch_number") or None,
        quantity=float(form.get("quantity") or 0),
        expiry_date=form.get("expiry_date") or None
    )
    db.add(batch)
    db.commit()
    return RedirectResponse("/estoque/lotes", status_code=302)


@router.get("/historico", response_class=HTMLResponse)
def movement_history(
    request: Request,
    product_id: Optional[int] = None,
    type: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    q = db.query(models.StockMovement).options(joinedload(models.StockMovement.product), joinedload(models.StockMovement.user))
    if product_id:
        q = q.filter(models.StockMovement.product_id == product_id)
    if type:
        q = q.filter(models.StockMovement.type == type)
    total = q.count()
    per_page = 30
    movements = q.order_by(models.StockMovement.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    products = db.query(models.Product).filter(models.Product.is_active == True).all()
    return templates.TemplateResponse("stock/history.html", {
        "request": request, "movements": movements, "products": products,
        "product_id": product_id, "type": type, "page": page,
        "total": total, "per_page": per_page, "current_user": current_user
    })
