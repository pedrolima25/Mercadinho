"""
Rotas de Catálogo Público
==========================
Páginas sem login, feitas para divulgação (link de WhatsApp, redes sociais).
Cada empresa tem seu próprio link, identificado pelo slug (/loja/{slug}/...).
Não expõem dados sensíveis: nada de estoque, custo ou código de barras.
"""

import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
from routers.company import get_or_create_company, branding_from_profile
from servicos.produtos import ServicoProdutos
from servicos.campanhas import ServicoCampanhas

router = APIRouter(prefix="/loja/{empresa_slug}", tags=["catalogo-publico"])
templates = Jinja2Templates(directory="templates")


def _resolver_empresa(empresa_slug: str, db: Session) -> models.Empresa:
    """Resolve a empresa pelo slug da URL, ou 404. Bloqueia se a licença estiver suspensa."""
    empresa = db.query(models.Empresa).filter(models.Empresa.slug == empresa_slug).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    if empresa.bloqueado:
        raise HTTPException(status_code=404, detail="Loja indisponível no momento")
    return empresa


def _whatsapp_digits(request: Request) -> str:
    numero = request.state.company.get("company_phone", "") if hasattr(request.state, "company") else ""
    return re.sub(r"\D", "", numero or "")


@router.get("/catalogo", response_class=HTMLResponse, name="catalogo_publico")
def catalogo_publico(empresa_slug: str, request: Request, categoria: str = None, db: Session = Depends(get_db)):
    """Catálogo público com todos os produtos ativos da empresa."""
    empresa = _resolver_empresa(empresa_slug, db)
    request.state.company = branding_from_profile(get_or_create_company(db, empresa.id))

    produtos = ServicoProdutos(db, empresa_id=empresa.id).listar_publico()
    categorias = sorted({p["category"] for p in produtos})
    if categoria:
        produtos = [p for p in produtos if p["category"] == categoria]
    return templates.TemplateResponse(
        request, "public/catalogo.html",
        {
            "empresa_slug": empresa_slug,
            "products": produtos,
            "categories": categorias,
            "categoria_atual": categoria,
            "whatsapp_digits": _whatsapp_digits(request),
        },
    )


@router.get("/catalogo/ofertas", response_class=HTMLResponse, name="catalogo_ofertas")
def catalogo_ofertas(empresa_slug: str, request: Request, db: Session = Depends(get_db)):
    """Catálogo público só com produtos em promoção ou com preço de atacado."""
    empresa = _resolver_empresa(empresa_slug, db)
    request.state.company = branding_from_profile(get_or_create_company(db, empresa.id))

    servico_produtos = ServicoProdutos(db, empresa_id=empresa.id)
    produtos = servico_produtos.listar_publico(somente_ofertas=True)

    agora = datetime.now(timezone.utc)
    promos_ativas = db.query(models.Promotion).filter(
        models.Promotion.is_active == True,
        models.Promotion.start_at <= agora,
        models.Promotion.end_at >= agora,
        models.Promotion.company_id == empresa.id,
    ).all()
    validade_fim = min((p.end_at for p in promos_ativas), default=None)

    return templates.TemplateResponse(
        request, "public/ofertas.html",
        {
            "empresa_slug": empresa_slug,
            "products": produtos,
            "whatsapp_digits": _whatsapp_digits(request),
            "validade_fim": validade_fim,
        },
    )


@router.get("/campanhas/{slug}", response_class=HTMLResponse, name="campanha_publica")
def campanha_publica(empresa_slug: str, slug: str, request: Request, db: Session = Depends(get_db)):
    """Página pública de uma campanha (encarte temático) — sem login."""
    empresa = _resolver_empresa(empresa_slug, db)
    request.state.company = branding_from_profile(get_or_create_company(db, empresa.id))

    servico = ServicoCampanhas(db, empresa_id=empresa.id)
    campanha = servico.obter_por_slug_ou_erro(slug)
    produtos = servico.produtos_publicos(campanha)
    return templates.TemplateResponse(
        request, "public/campanha.html",
        {
            "empresa_slug": empresa_slug,
            "campaign": campanha,
            "products": produtos,
            "whatsapp_digits": _whatsapp_digits(request),
        },
    )
