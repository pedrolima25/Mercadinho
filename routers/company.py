import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import auth as auth_utils
import models
from config import settings
from database import get_db

router = APIRouter(prefix="/empresa", tags=["empresa"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = Path("static") / "uploads" / "company"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

COMPANY_FIELDS = [
    "legal_name", "trade_name", "cnpj", "state_registration",
    "municipal_registration", "tax_regime", "cnae", "email", "phone",
    "whatsapp", "website", "zip_code", "street", "number", "complement",
    "neighborhood", "city", "state", "country", "responsible_name",
    "responsible_cpf", "responsible_phone", "responsible_email", "slogan",
    "receipt_footer", "pix_key", "pix_city", "notes",
]


def get_or_create_company(db: Session, empresa_id: Optional[int] = None) -> models.CompanyProfile:
    """Retorna o perfil (dados da loja, PIX, NFC-e) da empresa, criando um se ainda não existir."""
    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == empresa_id).first()
    if company:
        return company

    company = models.CompanyProfile(
        company_id=empresa_id,
        trade_name=settings.market_name or "Mercadinho",
        logo_url=settings.market_logo_url or "/static/img/logo.svg",
        country="Brasil",
        receipt_footer="Obrigado pela preferencia",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def branding_from_profile(company: models.CompanyProfile) -> dict:
    """Dados de marca (nome, logo, PIX, etc) de UMA empresa — usado por requisição, nunca global."""
    address_parts = [
        company.street,
        company.number,
        company.neighborhood,
        company.city,
        company.state,
    ]
    return {
        "market_name": company.trade_name or settings.market_name,
        "market_logo_url": company.logo_url or settings.market_logo_url,
        "company_receipt_footer": company.receipt_footer or "Obrigado pela preferencia",
        "company_cnpj": company.cnpj or "",
        "company_phone": company.phone or company.whatsapp or "",
        "company_email": company.email or "",
        "company_slogan": company.slogan or "",
        "pix_key": company.pix_key or settings.pix_key or "",
        "pix_city": (company.pix_city or settings.pix_city or "MANAUS").upper(),
        "company_address": " - ".join([part for part in address_parts if part]),
    }


def default_branding() -> dict:
    """Marca padrão exibida antes do login, quando ainda não se sabe de qual empresa é a requisição."""
    return {
        "market_name": settings.market_name or "Mercadinho",
        "market_logo_url": settings.market_logo_url or "/static/img/logo.svg",
        "company_receipt_footer": "Obrigado pela preferencia",
        "company_cnpj": "",
        "company_phone": "",
        "company_email": "",
        "company_slogan": "",
        "pix_key": settings.pix_key or "",
        "pix_city": (settings.pix_city or "MANAUS").upper(),
        "company_address": "",
    }


def save_logo(file_obj) -> str | None:
    filename = getattr(file_obj, "filename", "") or ""
    if not filename:
        return None

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / f"logo-{int(time.time())}{ext}"
    with target.open("wb") as out_file:
        shutil.copyfileobj(file_obj.file, out_file)
    return "/" + target.as_posix()


@router.get("", response_class=HTMLResponse)
def company_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("empresa")),
):
    company = get_or_create_company(db, current_user.company_id)
    return templates.TemplateResponse(request, "company/form.html", {
        "company": company,
        "current_user": current_user,
        "success": request.query_params.get("success") == "1",
    })


@router.post("")
async def save_company(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("empresa")),
):
    company = get_or_create_company(db, current_user.company_id)
    form = await request.form()

    for field in COMPANY_FIELDS:
        value = form.get(field)
        setattr(company, field, value.strip() if isinstance(value, str) and value.strip() else None)

    if not company.trade_name:
        company.trade_name = "Mercadinho"
    if not company.country:
        company.country = "Brasil"

    logo_url = save_logo(form.get("logo"))
    if logo_url:
        company.logo_url = logo_url

    db.commit()
    db.refresh(company)
    return RedirectResponse("/empresa?success=1", status_code=302)
