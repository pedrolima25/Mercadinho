import uuid
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models
import auth as auth_utils
from auth import require_super_admin
from utils.slug import slugify

router = APIRouter(prefix="/saas", tags=["saas"])
templates = Jinja2Templates(directory="templates")


def _stats_empresa(db: Session, empresa: models.Empresa) -> dict:
    users = db.query(func.count(models.User.id)).filter(models.User.company_id == empresa.id).scalar() or 0
    vendas = db.query(func.count(models.Sale.id)).join(models.User).filter(models.User.company_id == empresa.id).scalar() or 0
    return {"users": users, "vendas": vendas}


def _gerar_slug_unico_empresa(db: Session, nome: str, exceto_id: int = None) -> str:
    base = slugify(nome, fallback="loja")
    slug = base
    contador = 2
    while True:
        consulta = db.query(models.Empresa).filter(models.Empresa.slug == slug)
        if exceto_id:
            consulta = consulta.filter(models.Empresa.id != exceto_id)
        if not consulta.first():
            return slug
        slug = f"{base}-{contador}"
        contador += 1


def _status_empresa(empresa: models.Empresa) -> str:
    if empresa.bloqueado:
        return "bloqueada"
    if empresa.data_vencimento and empresa.data_vencimento < date.today():
        return "vencida"
    if empresa.data_vencimento and empresa.data_vencimento <= date.today() + timedelta(days=7):
        return "vencendo"
    return "ativa"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def saas_index(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_super_admin)):
    empresas = db.query(models.Empresa).order_by(models.Empresa.created_at.desc()).all()
    lista = []
    for e in empresas:
        stats = _stats_empresa(db, e)
        lista.append({"empresa": e, "status": _status_empresa(e), **stats})

    total = len(empresas)
    ativas = sum(1 for x in lista if x["status"] == "ativa")
    bloqueadas = sum(1 for x in lista if x["status"] == "bloqueada")
    vencidas = sum(1 for x in lista if x["status"] == "vencida")
    vencendo = sum(1 for x in lista if x["status"] == "vencendo")

    return templates.TemplateResponse(request, "saas/index.html", {
        "current_user": current_user,
        "lista": lista,
        "total": total, "ativas": ativas, "bloqueadas": bloqueadas,
        "vencidas": vencidas, "vencendo": vencendo,
    })


# ── Criar empresa ─────────────────────────────────────────────────────────────

@router.get("/nova", response_class=HTMLResponse)
def saas_nova_form(request: Request, current_user: models.User = Depends(require_super_admin)):
    return templates.TemplateResponse(request, "saas/form_empresa.html", {
        "current_user": current_user, "empresa": None, "erro": None,
    })


@router.post("/nova")
async def saas_nova_criar(
    request: Request,
    nome: str = Form(...),
    cnpj: str = Form(""),
    email_responsavel: str = Form(""),
    telefone_responsavel: str = Form(""),
    plano: str = Form("basico"),
    valor_mensal: str = Form(""),
    data_vencimento: str = Form(""),
    admin_username: str = Form(...),
    admin_senha: str = Form(...),
    admin_nome: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    # Valida username único
    if db.query(models.User).filter(models.User.username == admin_username).first():
        return templates.TemplateResponse(request, "saas/form_empresa.html", {
            "current_user": current_user, "empresa": None,
            "erro": f"Usuário '{admin_username}' já existe no sistema.",
        })

    empresa = models.Empresa(
        nome=nome,
        slug=_gerar_slug_unico_empresa(db, nome),
        cnpj=cnpj or None,
        email_responsavel=email_responsavel or None,
        telefone_responsavel=telefone_responsavel or None,
        plano=plano,
        valor_mensal=float(valor_mensal) if valor_mensal else None,
        data_vencimento=date.fromisoformat(data_vencimento) if data_vencimento else None,
        chave_licenca=str(uuid.uuid4())[:13].upper(),
    )
    db.add(empresa)
    db.flush()

    admin = models.User(
        username=admin_username,
        full_name=admin_nome,
        hashed_password=auth_utils.get_password_hash(admin_senha),
        role=models.UserRole.admin,
        company_id=empresa.id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa.id}", status_code=302)


# ── Detalhe / edição ──────────────────────────────────────────────────────────

@router.get("/empresa/{empresa_id}", response_class=HTMLResponse)
def saas_empresa_detalhe(empresa_id: int, request: Request, db: Session = Depends(get_db),
                          current_user: models.User = Depends(require_super_admin)):
    empresa = db.get(models.Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404, "Empresa não encontrada")
    stats = _stats_empresa(db, empresa)
    usuarios = db.query(models.User).filter(models.User.company_id == empresa_id).all()
    return templates.TemplateResponse(request, "saas/detalhe_empresa.html", {
        "current_user": current_user, "empresa": empresa,
        "status": _status_empresa(empresa), **stats, "usuarios": usuarios,
        "today": date.today(),
    })


@router.post("/empresa/{empresa_id}/editar")
async def saas_empresa_editar(
    empresa_id: int,
    nome: str = Form(...),
    cnpj: str = Form(""),
    email_responsavel: str = Form(""),
    telefone_responsavel: str = Form(""),
    plano: str = Form("basico"),
    valor_mensal: str = Form(""),
    data_vencimento: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    empresa = db.get(models.Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404)
    empresa.nome = nome
    empresa.cnpj = cnpj or None
    empresa.email_responsavel = email_responsavel or None
    empresa.telefone_responsavel = telefone_responsavel or None
    empresa.plano = plano
    empresa.valor_mensal = float(valor_mensal) if valor_mensal else None
    empresa.data_vencimento = date.fromisoformat(data_vencimento) if data_vencimento else None
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa_id}", status_code=302)


# ── Ações de licença ──────────────────────────────────────────────────────────

@router.post("/empresa/{empresa_id}/bloquear")
async def saas_bloquear(
    empresa_id: int,
    motivo: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    empresa = db.get(models.Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404)
    empresa.bloqueado = True
    empresa.motivo_bloqueio = motivo or "Bloqueado pelo administrador"
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa_id}", status_code=302)


@router.post("/empresa/{empresa_id}/desbloquear")
async def saas_desbloquear(empresa_id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(require_super_admin)):
    empresa = db.get(models.Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404)
    empresa.bloqueado = False
    empresa.motivo_bloqueio = None
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa_id}", status_code=302)


@router.post("/empresa/{empresa_id}/renovar")
async def saas_renovar(
    empresa_id: int,
    dias: int = Form(30),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    empresa = db.get(models.Empresa, empresa_id)
    if not empresa:
        raise HTTPException(404)
    base = empresa.data_vencimento if (empresa.data_vencimento and empresa.data_vencimento >= date.today()) else date.today()
    empresa.data_vencimento = base + timedelta(days=dias)
    empresa.bloqueado = False
    empresa.motivo_bloqueio = None
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa_id}", status_code=302)


@router.post("/empresa/{empresa_id}/acessar")
async def saas_impersonar(
    empresa_id: int, request: Request, db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    """Entra no sistema como se fosse o admin da empresa (impersonação)."""
    admin_empresa = db.query(models.User).filter(
        models.User.company_id == empresa_id,
        models.User.role == models.UserRole.admin,
        models.User.is_active == True,
    ).first()
    if not admin_empresa:
        raise HTTPException(404, "Nenhum usuário admin encontrado nesta empresa")

    from datetime import timedelta
    from config import settings
    token = auth_utils.create_access_token(
        {"sub": admin_empresa.username, "impersonando": True, "saas_return": True},
        timedelta(hours=2),
    )
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("access_token", f"Bearer {token}", httponly=True, samesite="lax", max_age=7200)
    response.set_cookie("saas_origem", str(empresa_id), httponly=False, samesite="lax", max_age=7200)
    return response


@router.get("/sair-impersonacao")
def saas_sair_impersonacao(request: Request, db: Session = Depends(get_db)):
    """Volta para o painel SaaS após impersonação."""
    response = RedirectResponse("/saas/", status_code=302)
    response.delete_cookie("saas_origem")
    # Restaura sessão do super admin — precisa relogar
    response.delete_cookie("access_token")
    return response


# ── Reset de senha ────────────────────────────────────────────────────────────

@router.post("/empresa/{empresa_id}/reset-senha")
async def saas_reset_senha(
    empresa_id: int,
    user_id: int = Form(...),
    nova_senha: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_super_admin),
):
    user = db.get(models.User, user_id)
    if not user or user.company_id != empresa_id:
        raise HTTPException(404)
    user.hashed_password = auth_utils.get_password_hash(nova_senha)
    db.commit()
    return RedirectResponse(f"/saas/empresa/{empresa_id}", status_code=302)
