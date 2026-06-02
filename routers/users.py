"""
Rotas de Usuários
=================
Responsabilidade: receber requisições HTTP e delegar ao ServicoUsuarios.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth as auth_utils
from servicos.usuarios import ServicoUsuarios

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def listar_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Lista todos os usuários (somente admin)."""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    servico = ServicoUsuarios(db)
    return templates.TemplateResponse(
        request, "users/index.html",
        {"users": servico.listar_todos(), "current_user": current_user},
    )


@router.get("/novo", response_class=HTMLResponse)
def novo_usuario(
    request: Request,
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Exibe formulário de cadastro de usuário."""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403)
    return templates.TemplateResponse(
        request, "users/form.html",
        {"user": None, "current_user": current_user, "roles": models.UserRole},
    )


@router.post("/novo")
async def criar_usuario(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Cria novo usuário. Validações ficam no ServicoUsuarios."""
    form = await request.form()
    servico = ServicoUsuarios(db)
    servico.criar(form, current_user)
    return RedirectResponse("/usuarios", status_code=302)


@router.get("/{user_id}/editar", response_class=HTMLResponse)
def editar_usuario(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Exibe formulário de edição de usuário."""
    servico = ServicoUsuarios(db)
    usuario = servico.obter_ou_erro(user_id)
    return templates.TemplateResponse(
        request, "users/form.html",
        {"user": usuario, "current_user": current_user, "roles": models.UserRole},
    )


@router.post("/{user_id}/editar")
async def atualizar_usuario(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Salva alterações do usuário."""
    form = await request.form()
    ServicoUsuarios(db).atualizar(user_id, form, current_user)
    return RedirectResponse("/usuarios", status_code=302)


@router.post("/{user_id}/excluir")
def excluir_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    """Desativa usuário."""
    ServicoUsuarios(db).desativar(user_id, current_user)
    return RedirectResponse("/usuarios", status_code=302)
