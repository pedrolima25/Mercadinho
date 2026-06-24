from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum, Numeric, BigInteger, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum
from database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    gerente = "gerente"
    caixa = "caixa"
    estoquista = "estoquista"
    financeiro = "financeiro"


class SaleStatus(str, enum.Enum):
    aberta = "aberta"
    finalizada = "finalizada"
    cancelada = "cancelada"


class ReturnType(str, enum.Enum):
    reembolso = "reembolso"
    troca = "troca"


class ReturnStatus(str, enum.Enum):
    processada = "processada"
    cancelada = "cancelada"


class PurchaseStatus(str, enum.Enum):
    pendente = "pendente"
    recebida = "recebida"
    cancelada = "cancelada"


class MovementType(str, enum.Enum):
    entrada = "entrada"
    saida = "saida"
    ajuste = "ajuste"


class PaymentMethod(str, enum.Enum):
    dinheiro = "dinheiro"
    pix = "pix"
    debito = "debito"
    credito = "credito"
    fiado = "fiado"
    vale = "vale"


class AccountStatus(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    vencido = "vencido"
    cancelado = "cancelado"


class CashRegisterStatus(str, enum.Enum):
    aberto = "aberto"
    fechado = "fechado"


class CashMovementType(str, enum.Enum):
    sangria = "sangria"
    suprimento = "suprimento"


class FiscalDocumentStatus(str, enum.Enum):
    pendente = "pendente"
    emitida = "emitida"
    autorizada = "autorizada"
    rejeitada = "rejeitada"
    cancelada = "cancelada"
    contingencia = "contingencia"


# ─── Usuários e Funcionários ─────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(150), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.caixa, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sales = relationship("Sale", back_populates="user")
    cash_registers = relationship("CashRegister", back_populates="user")
    stock_movements = relationship("StockMovement", back_populates="user")
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")

    def has_permission(self, key: str) -> bool:
        """Admin e Gerente têm acesso total; demais perfis dependem de permissão explícita."""
        if self.role in (UserRole.admin, UserRole.gerente):
            return True
        return any(p.permission_key == key for p in self.permissions)


class UserPermission(Base):
    """Permissão extra de tela/módulo concedida a um usuário sem perfil gerente/admin."""
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "permission_key", name="uq_user_permission"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission_key = Column(String(50), nullable=False)

    user = relationship("User", back_populates="permissions")


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    position = Column(String(100), nullable=True)
    salary = Column(Numeric(10, 2), nullable=True)
    hire_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


# ─── Cadastros ────────────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    products = relationship("Product", back_populates="category")


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="brand")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    cnpj = Column(String(18), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    contact_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="supplier")
    purchases = relationship("Purchase", back_populates="supplier")
    accounts_payable = relationship("AccountPayable", back_populates="supplier")


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    credit_limit = Column(Numeric(10, 2), default=0)
    balance = Column(Numeric(10, 2), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sales = relationship("Sale", back_populates="customer")
    accounts_receivable = relationship("AccountReceivable", back_populates="customer")


# ─── Produtos e Estoque ───────────────────────────────────────────────────────

class CompanyProfile(Base):
    __tablename__ = "company_profile"
    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String(200), nullable=True)
    trade_name = Column(String(200), nullable=False, default="Mercadinho")
    cnpj = Column(String(18), nullable=True)
    state_registration = Column(String(30), nullable=True)
    municipal_registration = Column(String(30), nullable=True)
    tax_regime = Column(String(80), nullable=True)
    cnae = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    whatsapp = Column(String(30), nullable=True)
    website = Column(String(150), nullable=True)
    zip_code = Column(String(12), nullable=True)
    street = Column(String(180), nullable=True)
    number = Column(String(20), nullable=True)
    complement = Column(String(120), nullable=True)
    neighborhood = Column(String(120), nullable=True)
    city = Column(String(120), nullable=True)
    state = Column(String(2), nullable=True)
    country = Column(String(80), default="Brasil")
    responsible_name = Column(String(150), nullable=True)
    responsible_cpf = Column(String(14), nullable=True)
    responsible_phone = Column(String(30), nullable=True)
    responsible_email = Column(String(120), nullable=True)
    slogan = Column(String(180), nullable=True)
    receipt_footer = Column(String(255), nullable=True)
    pix_key = Column(String(150), nullable=True)
    pix_city = Column(String(80), nullable=True)
    logo_url = Column(String(255), default="/static/img/logo.svg")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String(50), unique=True, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    image_url = Column(String(500), nullable=True)
    cost_price = Column(Numeric(10, 2), default=0)
    sale_price = Column(Numeric(10, 2), nullable=False, default=0)
    stock_quantity = Column(Numeric(10, 3), default=0)
    min_stock = Column(Numeric(10, 3), default=0)
    unit = Column(String(10), default="UN")
    ncm = Column(String(8), nullable=True)
    cest = Column(String(10), nullable=True)
    cfop = Column(String(4), nullable=True)
    origin = Column(String(1), nullable=True, default="0")
    cst_csosn = Column(String(4), nullable=True)
    icms_rate = Column(Numeric(5, 2), default=0)
    pis_rate = Column(Numeric(5, 2), default=0)
    cofins_rate = Column(Numeric(5, 2), default=0)
    tax_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    stock_movements = relationship("StockMovement", back_populates="product")
    batches = relationship("ProductBatch", back_populates="product")
    promotions = relationship("Promotion", back_populates="product", cascade="all, delete-orphan")
    wholesale_tiers = relationship("WholesaleTier", back_populates="product", cascade="all, delete-orphan")
    campaign_items = relationship("CampaignItem", back_populates="product")

    def campanha_preco_ativo(self):
        """Retorna o menor preço de divulgação vigente em campanhas ativas para este produto, ou None."""
        precos = [
            float(item.custom_price)
            for item in self.campaign_items
            if item.custom_price is not None and item.campaign and item.campaign.is_active
        ]
        return min(precos) if precos else None

    def promocao_ativa(self):
        """Retorna a promoção vigente agora (dentro do período e ativa), ou None."""
        agora = datetime.now(timezone.utc)
        for promo in self.promotions:
            if promo.is_active and promo.start_at <= agora <= promo.end_at:
                return promo
        return None

    def tiers_atacado_ativos(self):
        """Faixas de preço por quantidade ativas, ordenadas pela quantidade mínima."""
        return sorted(
            [t for t in self.wholesale_tiers if t.is_active],
            key=lambda t: float(t.min_quantity),
        )


class ProductBatch(Base):
    __tablename__ = "product_batches"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(50), nullable=True)
    quantity = Column(Numeric(10, 3), default=0)
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="batches")


class Promotion(Base):
    """Preço promocional temporário de um produto, aplicado automaticamente no PDV."""
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    promo_price = Column(Numeric(10, 2), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="promotions")


class WholesaleTier(Base):
    """Faixa de preço por quantidade (venda no atacado), aplicada automaticamente no PDV."""
    __tablename__ = "wholesale_tiers"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    min_quantity = Column(Numeric(10, 3), nullable=False)
    wholesale_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="wholesale_tiers")


class Campaign(Base):
    """Encarte temático com produtos selecionados manualmente, para divulgação (WhatsApp, redes sociais)."""
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(160), unique=True, nullable=False, index=True)
    subtitle = Column(String(200), nullable=True)
    color_primary = Column(String(7), default="#17a8e8")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("CampaignItem", back_populates="campaign", cascade="all, delete-orphan")


class CampaignItem(Base):
    """Produto selecionado dentro de uma campanha, com preço de divulgação opcional."""
    __tablename__ = "campaign_items"
    __table_args__ = (UniqueConstraint("campaign_id", "product_id", name="uq_campaign_product"),)

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    custom_price = Column(Numeric(10, 2), nullable=True)

    campaign = relationship("Campaign", back_populates="items")
    product = relationship("Product", back_populates="campaign_items")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    reason = Column(String(255), nullable=True)
    reference_id = Column(Integer, nullable=True)
    reference_type = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="stock_movements")
    user = relationship("User", back_populates="stock_movements")


# ─── Caixa ────────────────────────────────────────────────────────────────────

class CashRegister(Base):
    __tablename__ = "cash_registers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opening_balance = Column(Numeric(10, 2), default=0)
    closing_balance = Column(Numeric(10, 2), nullable=True)
    status = Column(Enum(CashRegisterStatus), default=CashRegisterStatus.aberto)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="cash_registers")
    sales = relationship("Sale", back_populates="cash_register")
    cash_movements = relationship("CashMovement", back_populates="cash_register")


class CashMovement(Base):
    __tablename__ = "cash_movements"
    id = Column(Integer, primary_key=True, index=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    type = Column(Enum(CashMovementType), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cash_register = relationship("CashRegister", back_populates="cash_movements")
    user = relationship("User")


# ─── Vendas ───────────────────────────────────────────────────────────────────

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subtotal = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    status = Column(Enum(SaleStatus), default=SaleStatus.aberta)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finalized_at = Column(DateTime(timezone=True), nullable=True)

    cash_register = relationship("CashRegister", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    user = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale", cascade="all, delete-orphan")
    fiscal_documents = relationship("FiscalDocument", back_populates="sale")
    returns = relationship("SaleReturn", back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sale = relationship("Sale", back_populates="payments")


class SaleReturn(Base):
    __tablename__ = "sale_returns"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(ReturnType), default=ReturnType.reembolso)
    reason = Column(String(255), nullable=False)
    total = Column(Numeric(10, 2), default=0)
    status = Column(Enum(ReturnStatus), default=ReturnStatus.processada)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sale = relationship("Sale", back_populates="returns")
    user = relationship("User")
    items = relationship("SaleReturnItem", back_populates="sale_return", cascade="all, delete-orphan")


class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"
    id = Column(Integer, primary_key=True, index=True)
    return_id = Column(Integer, ForeignKey("sale_returns.id"), nullable=False)
    sale_item_id = Column(Integer, ForeignKey("sale_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    sale_return = relationship("SaleReturn", back_populates="items")
    sale_item = relationship("SaleItem")
    product = relationship("Product")


class FiscalDocument(Base):
    __tablename__ = "fiscal_documents"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    model = Column(String(10), nullable=False, default="NFC-e")
    series = Column(String(10), nullable=True)
    number = Column(BigInteger, nullable=True)
    access_key = Column(String(44), nullable=True, index=True)
    status = Column(Enum(FiscalDocumentStatus), default=FiscalDocumentStatus.pendente)
    protocol = Column(String(80), nullable=True)
    qr_code_url = Column(Text, nullable=True)
    xml_path = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    contingency = Column(Boolean, default=False)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sale = relationship("Sale", back_populates="fiscal_documents")


# ─── Compras ──────────────────────────────────────────────────────────────────

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_number = Column(String(50), nullable=True)
    status = Column(Enum(PurchaseStatus), default=PurchaseStatus.pendente)
    total = Column(Numeric(10, 2), default=0)
    notes = Column(Text, nullable=True)
    expected_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier", back_populates="purchases")
    user = relationship("User")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")


# ─── Financeiro ───────────────────────────────────────────────────────────────

class AccountPayable(Base):
    __tablename__ = "accounts_payable"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    status = Column(Enum(AccountStatus), default=AccountStatus.pendente)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier", back_populates="accounts_payable")


class AccountReceivable(Base):
    __tablename__ = "accounts_receivable"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    status = Column(Enum(AccountStatus), default=AccountStatus.pendente)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="accounts_receivable")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(Date, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
