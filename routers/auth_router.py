from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
from database import get_db
import auth as auth_utils
from config import settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = auth_utils.get_current_user_from_cookie(request, next(get_db()))
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = auth_utils.authenticate_user(db, username, password)
    if not user or not user.is_active:
        return templates.TemplateResponse(request, "login.html", {"error": "Usuário ou senha inválidos"})
    token = auth_utils.create_access_token(
        {"sub": user.username},
        timedelta(minutes=settings.access_token_expire_minutes)
    )
    destino = "/pdv" if user.role.value == "caixa" else "/"
    response = RedirectResponse(destino, status_code=302)
    response.set_cookie(
        "access_token",
        f"Bearer {token}",
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.post("/auth/token")
async def api_token(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = auth_utils.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = auth_utils.create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
