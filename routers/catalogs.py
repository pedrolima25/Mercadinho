"""Routers para categorias, marcas, fornecedores, clientes e funcionários."""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models, auth as auth_utils

templates = Jinja2Templates(directory="templates")


# ─── Categorias ───────────────────────────────────────────────────────────────
categories_router = APIRouter(prefix="/categorias", tags=["categorias"])

@categories_router.get("", response_class=HTMLResponse)
def list_categories(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    items = db.query(models.Category).order_by(models.Category.name).all()
    return templates.TemplateResponse("catalogs/categories.html", {"request": request, "items": items, "current_user": current_user})

@categories_router.post("/novo")
async def create_category(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Category(name=form.get("name"), description=form.get("description") or None)
    db.add(item); db.commit()
    return RedirectResponse("/categorias", status_code=302)

@categories_router.post("/{item_id}/editar")
async def update_category(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Category).filter(models.Category.id == item_id).first()
    form = await request.form()
    if item:
        item.name = form.get("name")
        item.description = form.get("description") or None
        item.is_active = form.get("is_active") == "on"
        db.commit()
    return RedirectResponse("/categorias", status_code=302)

@categories_router.post("/{item_id}/excluir")
def delete_category(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Category).filter(models.Category.id == item_id).first()
    if item:
        item.is_active = False; db.commit()
    return RedirectResponse("/categorias", status_code=302)


# ─── Marcas ───────────────────────────────────────────────────────────────────
brands_router = APIRouter(prefix="/marcas", tags=["marcas"])

@brands_router.get("", response_class=HTMLResponse)
def list_brands(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    items = db.query(models.Brand).order_by(models.Brand.name).all()
    return templates.TemplateResponse("catalogs/brands.html", {"request": request, "items": items, "current_user": current_user})

@brands_router.post("/novo")
async def create_brand(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Brand(name=form.get("name"), description=form.get("description") or None)
    db.add(item); db.commit()
    return RedirectResponse("/marcas", status_code=302)

@brands_router.post("/{item_id}/editar")
async def update_brand(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Brand).filter(models.Brand.id == item_id).first()
    form = await request.form()
    if item:
        item.name = form.get("name")
        item.description = form.get("description") or None
        item.is_active = form.get("is_active") == "on"
        db.commit()
    return RedirectResponse("/marcas", status_code=302)

@brands_router.post("/{item_id}/excluir")
def delete_brand(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Brand).filter(models.Brand.id == item_id).first()
    if item:
        item.is_active = False; db.commit()
    return RedirectResponse("/marcas", status_code=302)


# ─── Fornecedores ─────────────────────────────────────────────────────────────
suppliers_router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])

@suppliers_router.get("", response_class=HTMLResponse)
def list_suppliers(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    items = db.query(models.Supplier).order_by(models.Supplier.name).all()
    return templates.TemplateResponse("catalogs/suppliers.html", {"request": request, "items": items, "current_user": current_user})

@suppliers_router.get("/novo", response_class=HTMLResponse)
def new_supplier(request: Request, current_user: models.User = Depends(auth_utils.require_gerente)):
    return templates.TemplateResponse("catalogs/supplier_form.html", {"request": request, "item": None, "current_user": current_user})

@suppliers_router.post("/novo")
async def create_supplier(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Supplier(
        name=form.get("name"), cnpj=form.get("cnpj") or None,
        email=form.get("email") or None, phone=form.get("phone") or None,
        address=form.get("address") or None, contact_name=form.get("contact_name") or None
    )
    db.add(item); db.commit()
    return RedirectResponse("/fornecedores", status_code=302)

@suppliers_router.get("/{item_id}/editar", response_class=HTMLResponse)
def edit_supplier(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Supplier).filter(models.Supplier.id == item_id).first()
    return templates.TemplateResponse("catalogs/supplier_form.html", {"request": request, "item": item, "current_user": current_user})

@suppliers_router.post("/{item_id}/editar")
async def update_supplier(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Supplier).filter(models.Supplier.id == item_id).first()
    form = await request.form()
    if item:
        item.name = form.get("name"); item.cnpj = form.get("cnpj") or None
        item.email = form.get("email") or None; item.phone = form.get("phone") or None
        item.address = form.get("address") or None; item.contact_name = form.get("contact_name") or None
        item.is_active = form.get("is_active") == "on"
        db.commit()
    return RedirectResponse("/fornecedores", status_code=302)

@suppliers_router.post("/{item_id}/excluir")
def delete_supplier(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Supplier).filter(models.Supplier.id == item_id).first()
    if item:
        item.is_active = False; db.commit()
    return RedirectResponse("/fornecedores", status_code=302)


# ─── Clientes ─────────────────────────────────────────────────────────────────
customers_router = APIRouter(prefix="/clientes", tags=["clientes"])

@customers_router.get("", response_class=HTMLResponse)
def list_customers(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    items = db.query(models.Customer).order_by(models.Customer.name).all()
    return templates.TemplateResponse("catalogs/customers.html", {"request": request, "items": items, "current_user": current_user})

@customers_router.get("/novo", response_class=HTMLResponse)
def new_customer(request: Request, current_user: models.User = Depends(auth_utils.require_gerente)):
    return templates.TemplateResponse("catalogs/customer_form.html", {"request": request, "item": None, "current_user": current_user})

@customers_router.post("/novo")
async def create_customer(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Customer(
        name=form.get("name"), cpf=form.get("cpf") or None,
        email=form.get("email") or None, phone=form.get("phone") or None,
        address=form.get("address") or None,
        credit_limit=float(form.get("credit_limit") or 0)
    )
    db.add(item); db.commit()
    return RedirectResponse("/clientes", status_code=302)

@customers_router.get("/{item_id}/editar", response_class=HTMLResponse)
def edit_customer(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Customer).filter(models.Customer.id == item_id).first()
    return templates.TemplateResponse("catalogs/customer_form.html", {"request": request, "item": item, "current_user": current_user})

@customers_router.post("/{item_id}/editar")
async def update_customer(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Customer).filter(models.Customer.id == item_id).first()
    form = await request.form()
    if item:
        item.name = form.get("name"); item.cpf = form.get("cpf") or None
        item.email = form.get("email") or None; item.phone = form.get("phone") or None
        item.address = form.get("address") or None
        item.credit_limit = float(form.get("credit_limit") or 0)
        item.is_active = form.get("is_active") == "on"
        db.commit()
    return RedirectResponse("/clientes", status_code=302)

@customers_router.post("/{item_id}/excluir")
def delete_customer(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Customer).filter(models.Customer.id == item_id).first()
    if item:
        item.is_active = False; db.commit()
    return RedirectResponse("/clientes", status_code=302)


# ─── Funcionários ─────────────────────────────────────────────────────────────
employees_router = APIRouter(prefix="/funcionarios", tags=["funcionarios"])

@employees_router.get("", response_class=HTMLResponse)
def list_employees(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    items = db.query(models.Employee).order_by(models.Employee.name).all()
    return templates.TemplateResponse("catalogs/employees.html", {"request": request, "items": items, "current_user": current_user})

@employees_router.get("/novo", response_class=HTMLResponse)
def new_employee(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    users = db.query(models.User).filter(models.User.is_active == True).all()
    return templates.TemplateResponse("catalogs/employee_form.html", {"request": request, "item": None, "users": users, "current_user": current_user})

@employees_router.post("/novo")
async def create_employee(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    form = await request.form()
    item = models.Employee(
        name=form.get("name"), cpf=form.get("cpf") or None,
        email=form.get("email") or None, phone=form.get("phone") or None,
        position=form.get("position") or None,
        salary=float(form.get("salary") or 0) or None,
        hire_date=form.get("hire_date") or None,
        user_id=int(form.get("user_id")) if form.get("user_id") else None
    )
    db.add(item); db.commit()
    return RedirectResponse("/funcionarios", status_code=302)

@employees_router.get("/{item_id}/editar", response_class=HTMLResponse)
def edit_employee(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Employee).filter(models.Employee.id == item_id).first()
    users = db.query(models.User).filter(models.User.is_active == True).all()
    return templates.TemplateResponse("catalogs/employee_form.html", {"request": request, "item": item, "users": users, "current_user": current_user})

@employees_router.post("/{item_id}/editar")
async def update_employee(item_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_gerente)):
    item = db.query(models.Employee).filter(models.Employee.id == item_id).first()
    form = await request.form()
    if item:
        item.name = form.get("name"); item.cpf = form.get("cpf") or None
        item.email = form.get("email") or None; item.phone = form.get("phone") or None
        item.position = form.get("position") or None
        item.salary = float(form.get("salary") or 0) or None
        item.hire_date = form.get("hire_date") or None
        item.user_id = int(form.get("user_id")) if form.get("user_id") else None
        item.is_active = form.get("is_active") == "on"
        db.commit()
    return RedirectResponse("/funcionarios", status_code=302)
