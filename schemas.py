from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from models import UserRole, SaleStatus, PurchaseStatus, PaymentMethod, AccountStatus, MovementType, CashRegisterStatus, CashMovementType, FiscalDocumentStatus


# ─── Auth ─────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# ─── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: str
    role: UserRole = UserRole.caixa
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Employee ─────────────────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    name: str
    cpf: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    salary: Optional[Decimal] = None
    hire_date: Optional[date] = None
    is_active: bool = True
    user_id: Optional[int] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    name: Optional[str] = None

class EmployeeOut(EmployeeBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Category ─────────────────────────────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: Optional[str] = None

class CategoryOut(CategoryBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Brand ────────────────────────────────────────────────────────────────────

class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BrandBase):
    name: Optional[str] = None

class BrandOut(BrandBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Supplier ─────────────────────────────────────────────────────────────────

class SupplierBase(BaseModel):
    name: str
    cnpj: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    is_active: bool = True

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(SupplierBase):
    name: Optional[str] = None

class SupplierOut(SupplierBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Customer ─────────────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str
    cpf: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Decimal = Decimal("0")
    is_active: bool = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    name: Optional[str] = None

class CustomerOut(CustomerBase):
    id: int
    balance: Decimal
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Product ──────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    supplier_id: Optional[int] = None
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    stock_quantity: Decimal = Decimal("0")
    min_stock: Decimal = Decimal("0")
    unit: str = "UN"
    ncm: Optional[str] = None
    cest: Optional[str] = None
    cfop: Optional[str] = None
    origin: Optional[str] = "0"
    cst_csosn: Optional[str] = None
    icms_rate: Decimal = Decimal("0")
    pis_rate: Decimal = Decimal("0")
    cofins_rate: Decimal = Decimal("0")
    tax_notes: Optional[str] = None
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    category: Optional[CategoryOut] = None
    brand: Optional[BrandOut] = None
    supplier: Optional[SupplierOut] = None
    class Config:
        from_attributes = True

class ProductSimple(BaseModel):
    id: int
    barcode: Optional[str]
    name: str
    sale_price: Decimal
    stock_quantity: Decimal
    unit: str
    class Config:
        from_attributes = True


# ─── Stock Movement ───────────────────────────────────────────────────────────

class StockMovementBase(BaseModel):
    product_id: int
    type: MovementType
    quantity: Decimal
    reason: Optional[str] = None

class StockMovementCreate(StockMovementBase):
    pass

class StockMovementOut(StockMovementBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    product: Optional[ProductSimple] = None
    class Config:
        from_attributes = True


# ─── Product Batch ────────────────────────────────────────────────────────────

class ProductBatchBase(BaseModel):
    product_id: int
    batch_number: Optional[str] = None
    quantity: Decimal
    expiry_date: Optional[date] = None

class ProductBatchCreate(ProductBatchBase):
    pass

class ProductBatchOut(ProductBatchBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Cash Register ────────────────────────────────────────────────────────────

class CashRegisterOpen(BaseModel):
    opening_balance: Decimal = Decimal("0")
    notes: Optional[str] = None

class CashRegisterClose(BaseModel):
    closing_balance: Decimal
    notes: Optional[str] = None

class CashRegisterOut(BaseModel):
    id: int
    user_id: int
    opening_balance: Decimal
    closing_balance: Optional[Decimal]
    status: CashRegisterStatus
    opened_at: datetime
    closed_at: Optional[datetime]
    notes: Optional[str]
    user: Optional[UserOut] = None
    class Config:
        from_attributes = True

class CashMovementCreate(BaseModel):
    type: CashMovementType
    amount: Decimal
    reason: Optional[str] = None

class CashMovementOut(CashMovementCreate):
    id: int
    cash_register_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Sale ─────────────────────────────────────────────────────────────────────

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal = Decimal("0")

class SaleItemOut(SaleItemCreate):
    id: int
    total: Decimal
    product: Optional[ProductSimple] = None
    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: Decimal

class PaymentOut(PaymentCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class FiscalDocumentOut(BaseModel):
    id: int
    sale_id: Optional[int]
    model: str
    series: Optional[str]
    number: Optional[int]
    access_key: Optional[str]
    status: FiscalDocumentStatus
    protocol: Optional[str]
    qr_code_url: Optional[str]
    xml_path: Optional[str]
    rejection_reason: Optional[str]
    contingency: bool
    issued_at: Optional[datetime]
    authorized_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    cash_register_id: Optional[int] = None
    discount: Decimal = Decimal("0")
    notes: Optional[str] = None
    items: List[SaleItemCreate]
    payments: List[PaymentCreate]

class SaleOut(BaseModel):
    id: int
    cash_register_id: Optional[int]
    customer_id: Optional[int]
    user_id: int
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    status: SaleStatus
    notes: Optional[str]
    created_at: datetime
    finalized_at: Optional[datetime]
    customer: Optional[CustomerOut] = None
    user: Optional[UserOut] = None
    items: List[SaleItemOut] = []
    payments: List[PaymentOut] = []
    class Config:
        from_attributes = True


# ─── Purchase ─────────────────────────────────────────────────────────────────

class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: Decimal
    unit_cost: Decimal

class PurchaseItemOut(PurchaseItemCreate):
    id: int
    total: Decimal
    product: Optional[ProductSimple] = None
    class Config:
        from_attributes = True

class PurchaseCreate(BaseModel):
    supplier_id: Optional[int] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    expected_date: Optional[date] = None
    items: List[PurchaseItemCreate]

class PurchaseUpdate(BaseModel):
    status: Optional[PurchaseStatus] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None

class PurchaseOut(BaseModel):
    id: int
    supplier_id: Optional[int]
    user_id: int
    invoice_number: Optional[str]
    status: PurchaseStatus
    total: Decimal
    notes: Optional[str]
    expected_date: Optional[date]
    received_date: Optional[date]
    created_at: datetime
    supplier: Optional[SupplierOut] = None
    items: List[PurchaseItemOut] = []
    class Config:
        from_attributes = True


# ─── Financial ────────────────────────────────────────────────────────────────

class AccountPayableCreate(BaseModel):
    supplier_id: Optional[int] = None
    description: str
    amount: Decimal
    due_date: date
    notes: Optional[str] = None

class AccountPayableUpdate(BaseModel):
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    status: Optional[AccountStatus] = None
    notes: Optional[str] = None

class AccountPayableOut(AccountPayableCreate):
    id: int
    paid_date: Optional[date]
    paid_amount: Optional[Decimal]
    status: AccountStatus
    created_at: datetime
    supplier: Optional[SupplierOut] = None
    class Config:
        from_attributes = True

class AccountReceivableCreate(BaseModel):
    customer_id: Optional[int] = None
    description: str
    amount: Decimal
    due_date: date
    notes: Optional[str] = None

class AccountReceivableUpdate(BaseModel):
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None
    status: Optional[AccountStatus] = None
    notes: Optional[str] = None

class AccountReceivableOut(AccountReceivableCreate):
    id: int
    paid_date: Optional[date]
    paid_amount: Optional[Decimal]
    status: AccountStatus
    created_at: datetime
    customer: Optional[CustomerOut] = None
    class Config:
        from_attributes = True

class ExpenseCreate(BaseModel):
    description: str
    category: Optional[str] = None
    amount: Decimal
    date: date
    notes: Optional[str] = None

class ExpenseOut(ExpenseCreate):
    id: int
    user_id: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_sales_today: Decimal
    total_sales_month: Decimal
    total_orders_today: int
    low_stock_count: int
    open_accounts_payable: Decimal
    open_accounts_receivable: Decimal
    cash_balance: Optional[Decimal]
