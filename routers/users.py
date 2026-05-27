from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models, auth as auth_utils

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def list_users(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    users = db.query(models.User).order_by(models.User.full_name).all()
    return templates.TemplateResponse("users/index.html", {"request": request, "users": users, "current_user": current_user})


@router.get("/novo", response_class=HTMLResponse)
def new_user(request: Request, current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403)
    return templates.TemplateResponse("users/form.html", {"request": request, "user": None, "current_user": current_user, "roles": models.UserRole})


@router.post("/novo")
async def create_user(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403)
    form = await request.form()
    existing = db.query(models.User).filter(models.User.username == form.get("username")).first()
    if existing:
        return templates.TemplateResponse("users/form.html", {
            "request": request, "user": None, "current_user": current_user,
            "roles": models.UserRole, "error": "Nome de usuário já existe"
        })
    user = models.User(
        username=form.get("username"),
        email=form.get("email") or None,
        full_name=form.get("full_name"),
        hashed_password=auth_utils.get_password_hash(form.get("password")),
        role=models.UserRole(form.get("role")),
        is_active=form.get("is_active") == "on"
    )
    db.add(user); db.commit()
    return RedirectResponse("/usuarios", status_code=302)


@router.get("/{user_id}/editar", response_class=HTMLResponse)
def edit_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin and current_user.id != user_id:
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return templates.TemplateResponse("users/form.html", {"request": request, "user": user, "current_user": current_user, "roles": models.UserRole})


@router.post("/{user_id}/editar")
async def update_user(user_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin and current_user.id != user_id:
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    form = await request.form()
    if user:
        user.full_name = form.get("full_name")
        user.email = form.get("email") or None
        if current_user.role == models.UserRole.admin:
            user.role = models.UserRole(form.get("role"))
            user.is_active = form.get("is_active") == "on"
        if form.get("password"):
            user.hashed_password = auth_utils.get_password_hash(form.get("password"))
        db.commit()
    return RedirectResponse("/usuarios", status_code=302)


@router.post("/{user_id}/excluir")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth_utils.require_user)):
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user and user.id != current_user.id:
        user.is_active = False; db.commit()
    return RedirectResponse("/usuarios", status_code=302)
