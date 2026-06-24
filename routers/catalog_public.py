"""
Rotas de Catálogo Público
==========================
Páginas sem login, feitas para divulgação (link de WhatsApp, redes sociais).
Não expõem dados sensíveis: nada de estoque, custo ou código de barras.
"""

import re
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from servicos.produtos import ServicoProdutos

router = APIRouter(tags=["catalogo-publico"])
templates = Jinja2Templates(directory="templates")


def _whatsapp_digits(request: Request) -> str:
    numero = getattr(request.app.state, "company_phone", "") or ""
    return re.sub(r"\D", "", numero)


@router.get("/catalogo", response_class=HTMLResponse, name="catalogo_publico")
def catalogo_publico(request: Request, categoria: str = None, db: Session = Depends(get_db)):
    """Catálogo público com todos os produtos ativos."""
    produtos = ServicoProdutos(db).listar_publico()
    categorias = sorted({p["category"] for p in produtos})
    if categoria:
        produtos = [p for p in produtos if p["category"] == categoria]
    return templates.TemplateResponse(
        request, "public/catalogo.html",
        {
            "products": produtos,
            "categories": categorias,
            "categoria_atual": categoria,
            "whatsapp_digits": _whatsapp_digits(request),
        },
    )


@router.get("/catalogo/ofertas", response_class=HTMLResponse, name="catalogo_ofertas")
def catalogo_ofertas(request: Request, db: Session = Depends(get_db)):
    """Catálogo público só com produtos em promoção ou com preço de atacado."""
    produtos = ServicoProdutos(db).listar_publico(somente_ofertas=True)
    return templates.TemplateResponse(
        request, "public/ofertas.html",
        {"products": produtos, "whatsapp_digits": _whatsapp_digits(request)},
    )
