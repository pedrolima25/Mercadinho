"""Rotas NFC-e"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
import models
import auth as auth_utils
from servicos.nfce import ServicoNfce

router = APIRouter(prefix="/nfce", tags=["nfce"])
templates = Jinja2Templates(directory="templates")


@router.post("/emitir/{sale_id}")
def emitir_nfce(
    sale_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    try:
        doc = ServicoNfce(db).emitir(sale_id)
        return JSONResponse({
            "success": True,
            "id":       doc.id,
            "chave":    doc.access_key,
            "numero":   doc.number,
            "status":   doc.status.value,
            "protocolo":doc.protocol,
            "motivo":   doc.rejection_reason,
            "qr_code":  doc.qr_code_url,
            "danfe_url": f"/nfce/{doc.id}/danfe",
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.get("/{doc_id}/danfe", response_class=HTMLResponse)
def danfe(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    doc = db.query(models.FiscalDocument).filter(
        models.FiscalDocument.id == doc_id
    ).first()
    if not doc:
        return HTMLResponse("<h3>Documento não encontrado</h3>", status_code=404)
    empresa = db.query(models.CompanyProfile).first()
    return templates.TemplateResponse(
        request, "nfce/danfe.html",
        {"doc": doc, "venda": doc.sale, "empresa": empresa}
    )


@router.post("/{doc_id}/cancelar")
def cancelar_nfce(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("vendas")),
):
    try:
        doc = ServicoNfce(db).cancelar(doc_id, "Cancelamento solicitado pelo operador")
        return JSONResponse({"success": True, "status": doc.status.value})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.get("/venda/{sale_id}")
def nfce_da_venda(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    doc = db.query(models.FiscalDocument).filter(
        models.FiscalDocument.sale_id == sale_id,
        models.FiscalDocument.model == "NFC-e",
    ).first()
    if not doc:
        return JSONResponse({"exists": False})
    return JSONResponse({
        "exists":    True,
        "id":        doc.id,
        "status":    doc.status.value,
        "chave":     doc.access_key,
        "protocolo": doc.protocol,
        "danfe_url": f"/nfce/{doc.id}/danfe",
    })
