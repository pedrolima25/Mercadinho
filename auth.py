from datetime import datetime, timedelta, date
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_from_token(token: str, db: Session) -> Optional[models.User]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    return db.query(models.User).filter(models.User.username == username).first()


def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    return get_user_from_token(token, db)


def _check_licenca(user: models.User):
    """Bloqueia acesso se a empresa estiver bloqueada ou com plano vencido."""
    if user.role == models.UserRole.super_administrador:
        return
    if not user.empresa:
        return
    empresa = user.empresa
    if empresa.bloqueado:
        motivo = empresa.motivo_bloqueio or "Conta bloqueada"
        raise HTTPException(status_code=302, headers={"Location": f"/bloqueado?motivo={motivo}"})
    if empresa.data_vencimento and empresa.data_vencimento < date.today():
        raise HTTPException(status_code=302, headers={"Location": "/vencido"})


def require_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    user = get_current_user_from_cookie(request, db)
    if not user or not user.is_active:
        from fastapi.responses import RedirectResponse
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    _check_licenca(user)
    return user


def require_super_admin(request: Request, db: Session = Depends(get_db)) -> models.User:
    user = get_current_user_from_cookie(request, db)
    if not user or not user.is_active:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if user.role != models.UserRole.super_administrador:
        raise HTTPException(status_code=403, detail="Acesso restrito ao super administrador")
    return user


def require_roles(*roles: models.UserRole):
    def checker(request: Request, db: Session = Depends(get_db)) -> models.User:
        user = get_current_user_from_cookie(request, db)
        if not user or not user.is_active:
            raise HTTPException(status_code=302, headers={"Location": "/login"})
        if user.role not in roles and user.role != models.UserRole.admin:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return user
    return checker


def require_gerente(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Exige nível gerente ou admin."""
    user = get_current_user_from_cookie(request, db)
    if not user or not user.is_active:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if user.role not in (models.UserRole.admin, models.UserRole.gerente):
        raise HTTPException(status_code=403, detail="Acesso restrito a gerentes e administradores")
    return user


def require_permission(key: str):
    """
    Exige acesso à tela/módulo `key`.
    Admin e Gerente sempre passam; demais perfis precisam da permissão
    explícita concedida em /usuarios/{id}/permissoes.
    """
    def checker(request: Request, db: Session = Depends(get_db)) -> models.User:
        user = get_current_user_from_cookie(request, db)
        if not user or not user.is_active:
            raise HTTPException(status_code=302, headers={"Location": "/login"})
        if not user.has_permission(key):
            raise HTTPException(status_code=403, detail="Sem permissão para acessar esta tela")
        return user
    return checker
