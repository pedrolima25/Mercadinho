from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, timedelta

from database import engine, Base, get_db
import models
import auth as auth_utils
from config import settings

# Routers
from routers.auth_router import router as auth_router
from routers.products import router as products_router
from routers.stock import router as stock_router
from routers.sales import router as sales_router, pdv_router
from routers.purchases import router as purchases_router
from routers.financial import router as financial_router
from routers.cash_register import router as cash_register_router
from routers.reports import router as reports_router
from routers.users import router as users_router
from routers.company import router as company_router, load_company_brand
from routers.catalogs import (
    categories_router, brands_router, suppliers_router,
    customers_router, employees_router
)

# Criar tabelas
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, docs_url="/api/docs")
app.state.market_name = settings.market_name
app.state.market_logo_url = settings.market_logo_url
app.state.company_receipt_footer = "Obrigado pela preferencia"
app.state.company_cnpj = ""
app.state.company_phone = ""
app.state.company_email = ""
app.state.company_address = ""
load_company_brand(app)

# Static files e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Registrar routers
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(stock_router)
app.include_router(sales_router)
app.include_router(pdv_router)
app.include_router(purchases_router)
app.include_router(financial_router)
app.include_router(cash_register_router)
app.include_router(reports_router)
app.include_router(users_router)
app.include_router(company_router)
app.include_router(categories_router)
app.include_router(brands_router)
app.include_router(suppliers_router)
app.include_router(customers_router)
app.include_router(employees_router)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    current_user = auth_utils.get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    today = date.today()

    # Estatísticas
    total_today = db.query(func.sum(models.Sale.total)).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        func.date(models.Sale.created_at) == today
    ).scalar() or 0

    total_month = db.query(func.sum(models.Sale.total)).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        extract('month', models.Sale.created_at) == today.month,
        extract('year', models.Sale.created_at) == today.year
    ).scalar() or 0

    orders_today = db.query(func.count(models.Sale.id)).filter(
        models.Sale.status == models.SaleStatus.finalizada,
        func.date(models.Sale.created_at) == today
    ).scalar() or 0

    low_stock_count = db.query(func.count(models.Product.id)).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).scalar() or 0

    open_payable = db.query(func.sum(models.AccountPayable.amount)).filter(
        models.AccountPayable.status == models.AccountStatus.pendente
    ).scalar() or 0

    open_receivable = db.query(func.sum(models.AccountReceivable.amount)).filter(
        models.AccountReceivable.status == models.AccountStatus.pendente
    ).scalar() or 0

    open_register = db.query(models.CashRegister).filter(
        models.CashRegister.user_id == current_user.id,
        models.CashRegister.status == models.CashRegisterStatus.aberto
    ).first()

    stats = {
        "total_sales_today": total_today,
        "total_sales_month": total_month,
        "total_orders_today": orders_today,
        "low_stock_count": low_stock_count,
        "open_accounts_payable": open_payable,
        "open_accounts_receivable": open_receivable,
        "cash_balance": open_register.opening_balance if open_register else None
    }

    recent_sales = db.query(models.Sale).filter(
        func.date(models.Sale.created_at) == today
    ).order_by(models.Sale.created_at.desc()).limit(8).all()

    low_stock = db.query(models.Product).filter(
        models.Product.is_active == True,
        models.Product.stock_quantity <= models.Product.min_stock
    ).order_by(models.Product.stock_quantity).limit(8).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats,
        "recent_sales": recent_sales,
        "low_stock": low_stock,
        "today": today.isoformat()
    })


# ─── Contexto global para templates ──────────────────────────────────────────
@app.middleware("http")
async def add_template_globals(request: Request, call_next):
    response = await call_next(request)
    return response


# ─── Seed de dados iniciais ───────────────────────────────────────────────────
def create_initial_data():
    db = next(get_db())
    try:
        # Admin user
        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin = models.User(
                username="admin",
                email="admin@supermercado.com",
                full_name="Administrador",
                hashed_password=auth_utils.get_password_hash("admin123"),
                role=models.UserRole.admin,
                is_active=True
            )
            db.add(admin)

            # Criar usuário caixa de exemplo
            caixa = models.User(
                username="caixa1",
                email="caixa@supermercado.com",
                full_name="Operador Caixa 1",
                hashed_password=auth_utils.get_password_hash("caixa123"),
                role=models.UserRole.caixa,
                is_active=True
            )
            db.add(caixa)
            db.flush()

            # Categorias
            cats = ["Bebidas", "Laticínios", "Carnes e Aves", "Hortifruti", "Padaria",
                    "Mercearia", "Limpeza", "Higiene e Beleza", "Frios e Embutidos", "Congelados"]
            cat_objs = {}
            for c in cats:
                obj = models.Category(name=c)
                db.add(obj)
                db.flush()
                cat_objs[c] = obj

            # Marcas
            brands = ["Nestlé", "Unilever", "P&G", "Ambev", "Sadia", "Perdigão", "Coca-Cola", "Sem Marca"]
            brand_objs = {}
            for b in brands:
                obj = models.Brand(name=b)
                db.add(obj)
                db.flush()
                brand_objs[b] = obj

            # Fornecedor
            supplier = models.Supplier(
                name="Distribuidora Central Ltda",
                cnpj="12.345.678/0001-90",
                email="contato@distribuidora.com",
                phone="(11) 3333-4444",
                contact_name="João Silva"
            )
            db.add(supplier)
            db.flush()

            # Produtos de exemplo
            products_data = [
                ("7891000055120", "Leite Integral 1L", "Laticínios", "Nestlé", 2.80, 4.99, 50, 10, "UN"),
                ("7891000315873", "Iogurte Natural 170g", "Laticínios", "Nestlé", 1.50, 2.99, 30, 5, "UN"),
                ("7891149101265", "Coca-Cola 2L", "Bebidas", "Coca-Cola", 5.50, 8.99, 40, 10, "UN"),
                ("7896085843939", "Água Mineral 500ml", "Bebidas", "Sem Marca", 0.80, 1.99, 100, 20, "UN"),
                ("7896085826956", "Pão de Forma 500g", "Padaria", "Sem Marca", 3.20, 5.49, 20, 5, "UN"),
                ("7893000985607", "Frango Inteiro Kg", "Carnes e Aves", "Sadia", 8.00, 12.99, 30, 5, "KG"),
                ("7896035908436", "Feijão Carioca 1Kg", "Mercearia", "Sem Marca", 4.00, 7.49, 60, 10, "UN"),
                ("7896085891817", "Arroz Agulhinha 5Kg", "Mercearia", "Sem Marca", 18.00, 28.99, 40, 8, "UN"),
                ("7891150058312", "Sabão em Pó 1Kg", "Limpeza", "Unilever", 6.00, 10.99, 25, 5, "UN"),
                ("7891024125419", "Detergente Líquido 500ml", "Limpeza", "Sem Marca", 1.20, 2.49, 50, 10, "UN"),
                ("7891000244616", "Café Torrado 500g", "Mercearia", "Nestlé", 7.50, 12.99, 30, 5, "UN"),
                ("7891000100103", "Açúcar Cristal 1Kg", "Mercearia", "Sem Marca", 2.80, 4.99, 50, 10, "UN"),
                ("7896085020039", "Tomate 1Kg", "Hortifruti", "Sem Marca", 3.00, 6.99, 20, 5, "KG"),
                ("7896085043991", "Banana Prata 1Kg", "Hortifruti", "Sem Marca", 2.50, 5.49, 15, 5, "KG"),
                ("7891000100219", "Macarrão Espaguete 500g", "Mercearia", "Sem Marca", 2.00, 3.99, 40, 8, "UN"),
            ]

            for barcode, name, cat_name, brand_name, cost, sale, stock, min_s, unit in products_data:
                p = models.Product(
                    barcode=barcode, name=name,
                    category_id=cat_objs.get(cat_name, cat_objs["Mercearia"]).id,
                    brand_id=brand_objs.get(brand_name, brand_objs["Sem Marca"]).id,
                    supplier_id=supplier.id,
                    cost_price=cost, sale_price=sale,
                    stock_quantity=stock, min_stock=min_s, unit=unit
                )
                db.add(p)
                db.flush()

                mv = models.StockMovement(
                    product_id=p.id, type=models.MovementType.entrada,
                    quantity=stock, reason="Estoque inicial", user_id=admin.id
                )
                db.add(mv)

            # Cliente de exemplo
            cliente = models.Customer(name="Maria da Silva", cpf="123.456.789-00", phone="(11) 99999-8888", credit_limit=500)
            db.add(cliente)

            db.commit()
            print("Dados iniciais criados! Login: admin / admin123")
    except Exception as e:
        db.rollback()
        print(f"Seed já existe ou erro: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_data()
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
