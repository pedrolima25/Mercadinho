from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional
from database import get_db
import models, schemas, auth as auth_utils

router = APIRouter(prefix="/produtos", tags=["produtos"])
templates = Jinja2Templates(directory="templates")


def get_product_or_404(product_id: int, db: Session) -> models.Product:
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return p


@router.get("", response_class=HTMLResponse)
def list_products(
    request: Request,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    low_stock: Optional[bool] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    q = db.query(models.Product).options(joinedload(models.Product.category), joinedload(models.Product.brand))
    if search:
        q = q.filter(or_(models.Product.name.ilike(f"%{search}%"), models.Product.barcode.ilike(f"%{search}%")))
    if category_id:
        q = q.filter(models.Product.category_id == category_id)
    if low_stock:
        q = q.filter(models.Product.stock_quantity <= models.Product.min_stock)
    total = q.count()
    per_page = 20
    products = q.order_by(models.Product.name).offset((page - 1) * per_page).limit(per_page).all()
    categories = db.query(models.Category).filter(models.Category.is_active == True).all()
    return templates.TemplateResponse("products/index.html", {
        "request": request, "products": products, "categories": categories,
        "search": search, "category_id": category_id, "low_stock": low_stock,
        "page": page, "total": total, "per_page": per_page,
        "current_user": current_user
    })


@router.get("/novo", response_class=HTMLResponse)
def new_product(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    categories = db.query(models.Category).filter(models.Category.is_active == True).all()
    brands = db.query(models.Brand).filter(models.Brand.is_active == True).all()
    suppliers = db.query(models.Supplier).filter(models.Supplier.is_active == True).all()
    return templates.TemplateResponse("products/form.html", {
        "request": request, "product": None, "categories": categories,
        "brands": brands, "suppliers": suppliers, "current_user": current_user
    })


@router.post("/novo")
async def create_product(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_gerente)
):
    form = await request.form()
    product = models.Product(
        barcode=form.get("barcode") or None,
        name=form.get("name"),
        description=form.get("description") or None,
        category_id=int(form.get("category_id")) if form.get("category_id") else None,
        brand_id=int(form.get("brand_id")) if form.get("brand_id") else None,
        supplier_id=int(form.get("supplier_id")) if form.get("supplier_id") else None,
        cost_price=float(form.get("cost_price") or 0),
        sale_price=float(form.get("sale_price") or 0),
        stock_quantity=float(form.get("stock_quantity") or 0),
        min_stock=float(form.get("min_stock") or 0),
        unit=form.get("unit", "UN"),
        is_active=form.get("is_active") == "on"
    )
    db.add(product)
    db.commit()
    if float(form.get("stock_quantity") or 0) > 0:
        mv = models.StockMovement(
            product_id=product.id, type=models.MovementType.entrada,
            quantity=float(form.get("stock_quantity")),
            reason="Estoque inicial", user_id=current_user.id
        )
        db.add(mv)
        db.commit()
    return RedirectResponse("/produtos", status_code=302)


@router.get("/{product_id}/editar", response_class=HTMLResponse)
def edit_product(request: Request, product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    product = get_product_or_404(product_id, db)
    categories = db.query(models.Category).filter(models.Category.is_active == True).all()
    brands = db.query(models.Brand).filter(models.Brand.is_active == True).all()
    suppliers = db.query(models.Supplier).filter(models.Supplier.is_active == True).all()
    return templates.TemplateResponse("products/form.html", {
        "request": request, "product": product, "categories": categories,
        "brands": brands, "suppliers": suppliers, "current_user": current_user
    })


@router.post("/{product_id}/editar")
async def update_product(request: Request, product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    product = get_product_or_404(product_id, db)
    form = await request.form()
    product.barcode = form.get("barcode") or None
    product.name = form.get("name")
    product.description = form.get("description") or None
    product.category_id = int(form.get("category_id")) if form.get("category_id") else None
    product.brand_id = int(form.get("brand_id")) if form.get("brand_id") else None
    product.supplier_id = int(form.get("supplier_id")) if form.get("supplier_id") else None
    product.cost_price = float(form.get("cost_price") or 0)
    product.sale_price = float(form.get("sale_price") or 0)
    product.min_stock = float(form.get("min_stock") or 0)
    product.unit = form.get("unit", "UN")
    product.is_active = form.get("is_active") == "on"
    db.commit()
    return RedirectResponse("/produtos", status_code=302)


@router.post("/{product_id}/excluir")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    product = get_product_or_404(product_id, db)
    product.is_active = False
    db.commit()
    return RedirectResponse("/produtos", status_code=302)


# API JSON endpoints for PDV
@router.get("/api/buscar")
def search_products_api(q: str = "", db: Session = Depends(get_db)):
    products = db.query(models.Product).filter(
        models.Product.is_active == True,
        or_(models.Product.name.ilike(f"%{q}%"), models.Product.barcode.ilike(f"%{q}%"))
    ).limit(10).all()
    return [{"id": p.id, "barcode": p.barcode, "name": p.name, "sale_price": float(p.sale_price), "stock_quantity": float(p.stock_quantity), "unit": p.unit} for p in products]


@router.get("/api/todos")
def all_products_api(db: Session = Depends(get_db)):
    """Retorna todos os produtos ativos para o catálogo do PDV."""
    products = db.query(models.Product).options(
        joinedload(models.Product.category)
    ).filter(models.Product.is_active == True).order_by(models.Product.name).all()
    return [{
        "id": p.id, "barcode": p.barcode or "", "name": p.name,
        "sale_price": float(p.sale_price), "stock_quantity": float(p.stock_quantity),
        "unit": p.unit, "category": p.category.name if p.category else "Sem categoria"
    } for p in products]


@router.get("/api/barcode/{barcode}")
def get_by_barcode(barcode: str, db: Session = Depends(get_db)):
    p = db.query(models.Product).filter(models.Product.barcode == barcode, models.Product.is_active == True).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return {"id": p.id, "barcode": p.barcode, "name": p.name, "sale_price": float(p.sale_price), "stock_quantity": float(p.stock_quantity), "unit": p.unit}
