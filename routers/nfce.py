"""Rotas NFC-e"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
import models
import auth as auth_utils
from routers.company import get_or_create_company
from servicos.nfce import ServicoNfce, checklist_fiscal

router = APIRouter(prefix="/nfce", tags=["nfce"])
templates = Jinja2Templates(directory="templates")

CERT_DIR = Path("fiscal") / "certs"


@router.get("/checklist", response_class=HTMLResponse)
def checklist(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("empresa")),
):
    dados = checklist_fiscal(db, current_user.company_id)
    return templates.TemplateResponse(request, "nfce/checklist.html", dados)


@router.get("/configuracao", response_class=HTMLResponse)
def configuracao_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("empresa")),
):
    empresa = get_or_create_company(db, current_user.company_id)
    return templates.TemplateResponse(request, "nfce/configuracao.html", {
        "empresa": empresa,
        "success": request.query_params.get("success") == "1",
    })


@router.post("/configuracao")
async def configuracao_save(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_permission("empresa")),
):
    empresa = get_or_create_company(db, current_user.company_id)
    form = await request.form()

    empresa.nfce_ambiente = form.get("nfce_ambiente") or "2"
    empresa.nfce_serie = (form.get("nfce_serie") or "001").strip().zfill(3)
    empresa.nfce_csc = (form.get("nfce_csc") or "").strip() or None
    empresa.nfce_csc_id = (form.get("nfce_csc_id") or "").strip() or None

    cert_pass = (form.get("nfce_cert_pass") or "").strip()
    if cert_pass:
        empresa.nfce_cert_pass = cert_pass

    cert_file = form.get("nfce_cert_file")
    filename = getattr(cert_file, "filename", "") or ""
    if filename:
        CERT_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix.lower()
        if ext == ".pfx":
            target = CERT_DIR / f"empresa-{empresa.id}.pfx"
            with target.open("wb") as out_file:
                out_file.write(await cert_file.read())
            empresa.nfce_cert_path = str(target)

    db.commit()
    return RedirectResponse("/nfce/configuracao?success=1", status_code=302)


@router.post("/emitir/{sale_id}")
def emitir_nfce(
    sale_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.require_user),
):
    try:
        doc = ServicoNfce(db, current_user).emitir(sale_id)
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
        models.FiscalDocument.id == doc_id,
        models.FiscalDocument.company_id == current_user.company_id,
    ).first()
    if not doc:
        return HTMLResponse("<h3>Documento não encontrado</h3>", status_code=404)
    empresa = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.company_id == current_user.company_id
    ).first()
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
        doc = ServicoNfce(db, current_user).cancelar(doc_id, "Cancelamento solicitado pelo operador")
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
        models.FiscalDocument.company_id == current_user.company_id,
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
