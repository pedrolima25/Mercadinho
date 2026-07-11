"""
Serviço NFC-e — Nota Fiscal de Consumidor Eletrônica (Modelo 65)
================================================================
SEFAZ-AM (Amazonas) · Ambiente configurável (homologação / produção)

Sem certificado → gera XML e armazena como "pendente".
Com certificado  → assina, transmite para SEFAZ e armazena protocolo.

Configuração (.env):
  NFCE_AMBIENTE=2          # 1=produção 2=homologação
  NFCE_SERIE=001
  NFCE_CERT_PATH=          # caminho do .pfx
  NFCE_CERT_PASS=          # senha do .pfx
  NFCE_XML_DIR=fiscal/xml
"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.orm import Session

import models

# ── Constantes SEFAZ-AM ──────────────────────────────────────────────────────
_CUF       = "13"       # código UF Amazonas
_C_MUN     = "1302603"  # IBGE Manaus (ajuste se cidade diferente)
_VERSAO    = "4.00"
_NS        = "http://www.portalfiscal.inf.br/nfe"
_WSNS      = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"

_WS_HOMOLOG = "https://homnfe.sefaz.am.gov.br/nfeweb/services/NfeAutorizacao4"
_WS_PROD    = "https://nfe.sefaz.am.gov.br/nfeweb/services/NfeAutorizacao4"

# Mapa método pagamento → tPag NFC-e
_T_PAG = {
    "dinheiro": "01",
    "cheque":   "02",
    "credito":  "03",
    "debito":   "04",
    "fiado":    "05",
    "pix":      "17",
    "vale":     "10",
}


_CIDADES_SUPORTADAS = {"MANAUS", "PARINTINS", "ITACOATIARA", "MANACAPURU"}


def checklist_fiscal(db: Session, empresa_id: Optional[int] = None) -> dict:
    """Diagnostico do que falta para emitir NFC-e de verdade (nao simulado)."""
    empresa = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == empresa_id).first()

    cert_path = (empresa and empresa.nfce_cert_path) or os.getenv("NFCE_CERT_PATH", "")
    cert_pass = (empresa and empresa.nfce_cert_pass) or os.getenv("NFCE_CERT_PASS", "")
    csc       = (empresa and empresa.nfce_csc) or os.getenv("NFCE_CSC", "")
    csc_id    = (empresa and empresa.nfce_csc_id) or os.getenv("NFCE_CSC_ID", "")
    ambiente  = (empresa and empresa.nfce_ambiente) or os.getenv("NFCE_AMBIENTE", "")
    cert_existe = bool(cert_path) and Path(cert_path).exists()

    total_produtos = db.query(models.Product).filter(models.Product.company_id == empresa_id).count()
    sem_ncm = db.query(models.Product).filter(
        models.Product.company_id == empresa_id,
        (models.Product.ncm.is_(None)) | (models.Product.ncm == ""),
    ).count()
    sem_cfop = db.query(models.Product).filter(
        models.Product.company_id == empresa_id,
        (models.Product.cfop.is_(None)) | (models.Product.cfop == ""),
    ).count()

    cidade = (empresa.city or "").upper().strip() if empresa else ""

    itens = [
        {"grupo": "Cadastro", "item": "CNPJ preenchido",
         "ok": bool(empresa and empresa.cnpj)},
        {"grupo": "Cadastro", "item": "Inscricao Estadual preenchida",
         "ok": bool(empresa and empresa.state_registration)},
        {"grupo": "Cadastro", "item": "Endereco completo (rua, numero, bairro, cidade, UF, CEP)",
         "ok": bool(empresa and empresa.street and empresa.number and
                     empresa.neighborhood and empresa.city and empresa.state and empresa.zip_code)},
        {"grupo": "Cadastro", "item": "Regime tributario definido",
         "ok": bool(empresa and empresa.tax_regime)},
        {"grupo": "Cadastro", "item": f"Cidade suportada no mapeamento IBGE ({cidade or 'nao definida'})",
         "ok": cidade in _CIDADES_SUPORTADAS},
        {"grupo": "Tecnico", "item": "Certificado digital A1 configurado",
         "ok": cert_existe},
        {"grupo": "Tecnico", "item": "Senha do certificado configurada",
         "ok": bool(cert_pass)},
        {"grupo": "Tecnico", "item": "CSC (Codigo de Seguranca do Contribuinte) configurado",
         "ok": bool(csc and csc_id)},
        {"grupo": "Tecnico", "item": "Ambiente definido (homologacao/producao)",
         "ok": bool(ambiente)},
        {"grupo": "Produtos", "item": f"Produtos com NCM preenchido ({total_produtos - sem_ncm}/{total_produtos})",
         "ok": total_produtos > 0 and sem_ncm == 0},
        {"grupo": "Produtos", "item": f"Produtos com CFOP preenchido ({total_produtos - sem_cfop}/{total_produtos})",
         "ok": total_produtos > 0 and sem_cfop == 0},
    ]

    prontos = sum(1 for i in itens if i["ok"])
    return {"itens": itens, "prontos": prontos, "total": len(itens)}


class ServicoNfce:
    def __init__(self, db: Session, current_user=None, empresa_id: Optional[int] = None):
        self.db = db
        self.empresa_id = empresa_id if empresa_id is not None else (
            current_user.company_id if current_user is not None else None
        )
        empresa = db.query(models.CompanyProfile).filter(models.CompanyProfile.company_id == self.empresa_id).first()

        # Config prioriza o cadastro da empresa (tela /nfce/configuracao); cai para o .env se vazio
        self.ambiente  = (empresa and empresa.nfce_ambiente) or os.getenv("NFCE_AMBIENTE", "2")
        self.serie     = ((empresa and empresa.nfce_serie) or os.getenv("NFCE_SERIE", "001")).zfill(3)
        self.cert_path = (empresa and empresa.nfce_cert_path) or os.getenv("NFCE_CERT_PATH", "")
        self.cert_pass = (empresa and empresa.nfce_cert_pass) or os.getenv("NFCE_CERT_PASS", "")
        self.csc       = (empresa and empresa.nfce_csc) or os.getenv("NFCE_CSC", "")
        self.csc_id    = (empresa and empresa.nfce_csc_id) or os.getenv("NFCE_CSC_ID", "")
        self.xml_dir   = Path(os.getenv("NFCE_XML_DIR", "fiscal/xml"))
        self.xml_dir.mkdir(parents=True, exist_ok=True)

    # ── API pública ──────────────────────────────────────────────────────────

    def emitir(self, venda_id: int) -> models.FiscalDocument:
        """Emite NFC-e para uma venda. Retorna o FiscalDocument criado."""
        venda = self.db.query(models.Sale).filter(
            models.Sale.id == venda_id,
            models.Sale.company_id == self.empresa_id,
        ).first()
        if not venda:
            raise ValueError("Venda não encontrada")

        # Verifica se já existe documento para esta venda
        doc = self.db.query(models.FiscalDocument).filter(
            models.FiscalDocument.sale_id == venda_id,
            models.FiscalDocument.model == "NFC-e",
            models.FiscalDocument.company_id == self.empresa_id,
        ).first()
        if doc and doc.status == models.FiscalDocumentStatus.autorizada:
            raise ValueError("NFC-e já autorizada para esta venda")

        empresa = self._empresa()
        numero  = self._proximo_numero()
        cnf     = str(uuid.uuid4().int)[:8].zfill(8)
        chave   = self._chave(empresa.cnpj or "00000000000000", numero, cnf)
        dh_emi  = datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%dT%H:%M:%S") + "-04:00"

        xml_str = self._gerar_xml(venda, empresa, numero, chave, cnf, dh_emi)

        if doc is None:
            doc = models.FiscalDocument(
                sale_id=venda_id,
                model="NFC-e",
                series=self.serie,
                number=numero,
                access_key=chave,
                status=models.FiscalDocumentStatus.pendente,
                issued_at=datetime.now(timezone.utc),
                company_id=self.empresa_id,
            )
            self.db.add(doc)
            self.db.flush()

        # Salva XML localmente
        xml_file = self.xml_dir / f"nfce_{chave}.xml"
        xml_file.write_text(xml_str, encoding="utf-8")
        doc.xml_path = str(xml_file)

        if self.cert_path and Path(self.cert_path).exists():
            xml_assinado = self._assinar(xml_str, chave)
            resultado    = self._transmitir(xml_assinado)
            doc.protocol           = resultado.get("protocolo")
            doc.rejection_reason   = resultado.get("motivo")
            doc.qr_code_url        = self._qrcode_url(chave, venda, dh_emi)
            doc.status = (
                models.FiscalDocumentStatus.autorizada
                if resultado.get("cStat") in ("100", "150")
                else models.FiscalDocumentStatus.rejeitada
            )
            if doc.status == models.FiscalDocumentStatus.autorizada:
                doc.authorized_at = datetime.now(timezone.utc)
                xml_file.write_text(resultado.get("xml_proc", xml_assinado), encoding="utf-8")
        else:
            # Sem certificado: armazena pendente (homologação visual)
            doc.status = models.FiscalDocumentStatus.pendente
            doc.qr_code_url = self._qrcode_url(chave, venda, dh_emi)
            doc.rejection_reason = "Certificado não configurado — pendente de assinatura"

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def cancelar(self, doc_id: int, motivo: str) -> models.FiscalDocument:
        doc = self.db.query(models.FiscalDocument).filter(
            models.FiscalDocument.id == doc_id,
            models.FiscalDocument.company_id == self.empresa_id,
        ).first()
        if not doc:
            raise ValueError("Documento fiscal não encontrado")
        if doc.status != models.FiscalDocumentStatus.autorizada:
            raise ValueError("Somente NFC-e autorizada pode ser cancelada")
        doc.status = models.FiscalDocumentStatus.cancelada
        self.db.commit()
        return doc

    # ── Geração do XML ───────────────────────────────────────────────────────

    def _gerar_xml(self, venda, empresa, numero: int, chave: str, cnf: str, dh_emi: str) -> str:
        ns = _NS

        nfe = ET.Element(f"{{{ns}}}NFe")
        inf = ET.SubElement(nfe, f"{{{ns}}}infNFe",
                            Id=f"NFe{chave}", versao=_VERSAO)

        # ── ide ──
        ide = ET.SubElement(inf, f"{{{ns}}}ide")
        self._t(ide, "cUF",     _CUF)
        self._t(ide, "cNF",     cnf)
        self._t(ide, "natOp",   "VENDA DE MERCADORIAS")
        self._t(ide, "mod",     "65")
        self._t(ide, "serie",   self.serie)
        self._t(ide, "nNF",     str(numero))
        self._t(ide, "dhEmi",   dh_emi)
        self._t(ide, "tpNF",    "1")
        self._t(ide, "idDest",  "1")
        self._t(ide, "cMunFG",  self._ibge(empresa))
        self._t(ide, "tpImp",   "4")
        self._t(ide, "tpEmis",  "1")
        self._t(ide, "cDV",     chave[-1])
        self._t(ide, "tpAmb",   self.ambiente)
        self._t(ide, "finNFe",  "1")
        self._t(ide, "indFinal","1")
        self._t(ide, "indPres", "1")
        self._t(ide, "indIntermed", "0")
        self._t(ide, "verProc", "SuperMarket Pro 1.0")

        # ── emit ──
        cnpj_num = re.sub(r"\D", "", empresa.cnpj or "")
        emit = ET.SubElement(inf, f"{{{ns}}}emit")
        self._t(emit, "CNPJ",  cnpj_num)
        self._t(emit, "xNome", (empresa.legal_name or empresa.trade_name or "EMPRESA")[:60])
        self._t(emit, "xFant", (empresa.trade_name or "")[:60])
        end = ET.SubElement(emit, f"{{{ns}}}enderEmit")
        self._t(end, "xLgr",   (empresa.street or "Rua")[:60])
        self._t(end, "nro",    (empresa.number or "S/N")[:60])
        self._t(end, "xBairro",(empresa.neighborhood or "Centro")[:60])
        self._t(end, "cMun",   self._ibge(empresa))
        self._t(end, "xMun",   (empresa.city or "Manaus")[:60])
        self._t(end, "UF",     (empresa.state or "AM")[:2])
        self._t(end, "CEP",    re.sub(r"\D", "", empresa.zip_code or "69000000")[:8])
        self._t(end, "cPais",  "1058")
        self._t(end, "xPais",  "BRASIL")
        self._t(emit, "IE",    re.sub(r"\D", "", empresa.state_registration or ""))
        self._t(emit, "CRT",   "1")  # Simples Nacional

        # ── dest (consumidor não identificado) ──
        # NFC-e não obriga dest quando não identificado

        # ── det (itens) ──
        v_prod_total = 0.0
        v_desc_total = 0.0
        for idx, item in enumerate(venda.items, 1):
            p = item.product
            det = ET.SubElement(inf, f"{{{ns}}}det", nItem=str(idx))
            prod = ET.SubElement(det, f"{{{ns}}}prod")
            self._t(prod, "cProd",  str(p.id).zfill(6))
            ean = (p.barcode or "SEM GTIN")[:14]
            self._t(prod, "cEAN",   ean)
            self._t(prod, "xProd",  p.name[:120])
            self._t(prod, "NCM",    re.sub(r"\D", "", p.ncm or "22021000")[:8])
            self._t(prod, "CFOP",   p.cfop or "5102")
            self._t(prod, "uCom",   p.unit or "UN")
            qty  = float(item.quantity)
            prec = float(item.unit_price)
            disc = float(item.discount or 0)
            v_prod = round(qty * prec, 2)
            v_desc_total += disc
            v_prod_total += v_prod
            self._t(prod, "qCom",   f"{qty:.4f}")
            self._t(prod, "vUnCom", f"{prec:.10f}")
            self._t(prod, "vProd",  f"{v_prod:.2f}")
            self._t(prod, "cEANTrib", ean)
            self._t(prod, "uTrib", p.unit or "UN")
            self._t(prod, "qTrib",  f"{qty:.4f}")
            self._t(prod, "vUnTrib",f"{prec:.10f}")
            if disc > 0:
                self._t(prod, "vDesc", f"{disc:.2f}")
            self._t(prod, "indTot", "1")

            # imposto — Simples Nacional CSOSN
            imp = ET.SubElement(det, f"{{{ns}}}imposto")
            icms = ET.SubElement(imp, f"{{{ns}}}ICMS")
            csosn = p.cst_csosn or "400"
            icms_grp = ET.SubElement(icms, f"{{{ns}}}ICMSSN{csosn}")
            self._t(icms_grp, "orig",  p.origin or "0")
            self._t(icms_grp, "CSOSN", csosn)

            pis = ET.SubElement(imp, f"{{{ns}}}PIS")
            pis_nt = ET.SubElement(pis, f"{{{ns}}}PISNT")
            self._t(pis_nt, "CST", "07")

            cof = ET.SubElement(imp, f"{{{ns}}}COFINS")
            cof_nt = ET.SubElement(cof, f"{{{ns}}}COFINSNT")
            self._t(cof_nt, "CST", "07")

        # ── total ──
        v_nf = round(float(venda.total), 2)
        tot = ET.SubElement(inf, f"{{{ns}}}total")
        ict = ET.SubElement(tot, f"{{{ns}}}ICMSTot")
        for tag, val in [
            ("vBC","0.00"),("vICMS","0.00"),("vICMSDeson","0.00"),
            ("vFCP","0.00"),("vBCST","0.00"),("vST","0.00"),
            ("vFCPST","0.00"),("vFCPSTRet","0.00"),
            ("vProd", f"{v_prod_total:.2f}"),
            ("vFrete","0.00"),("vSeg","0.00"),
            ("vDesc", f"{v_desc_total:.2f}"),
            ("vII","0.00"),("vIPI","0.00"),("vIPIDevol","0.00"),
            ("vPIS","0.00"),("vCOFINS","0.00"),
            ("vOutro","0.00"),
            ("vNF", f"{v_nf:.2f}"),
        ]:
            self._t(ict, tag, val)

        # ── transp ──
        transp = ET.SubElement(inf, f"{{{ns}}}transp")
        self._t(transp, "modFrete", "9")

        # ── pag ──
        pag = ET.SubElement(inf, f"{{{ns}}}pag")
        for pgto in venda.payments:
            det_pag = ET.SubElement(pag, f"{{{ns}}}detPag")
            self._t(det_pag, "tPag", _T_PAG.get(pgto.method.value, "99"))
            self._t(det_pag, "vPag", f"{float(pgto.amount):.2f}")

        # ── infAdic ──
        inf_adic = ET.SubElement(inf, f"{{{ns}}}infAdic")
        msg = "EMITIDO EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL" \
            if self.ambiente == "2" else ""
        self._t(inf_adic, "infCpl", msg)

        ET.register_namespace("", ns)
        return '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(nfe, encoding="unicode")

    # ── Certificado ──────────────────────────────────────────────────────────

    def _carregar_pfx(self):
        """Le o .pfx e devolve (chave_privada, certificado, demais_certificados)."""
        from cryptography.hazmat.primitives.serialization import pkcs12
        cert_bytes = Path(self.cert_path).read_bytes()
        return pkcs12.load_key_and_certificates(cert_bytes, self.cert_pass.encode())

    def _cert_pem_files(self) -> Optional[tuple]:
        """Converte o .pfx em (cert.pem, key.pem) para TLS mutuo com a SEFAZ.

        httpx/ssl nao aceita PKCS12 diretamente — precisa de PEM. Os arquivos
        derivados ficam ao lado do .pfx e sao regenerados se o .pfx mudar.
        """
        if not self.cert_path or not Path(self.cert_path).exists():
            return None
        pfx_path = Path(self.cert_path)
        cert_pem = pfx_path.parent / f"{pfx_path.stem}.cert.pem"
        key_pem  = pfx_path.parent / f"{pfx_path.stem}.key.pem"
        if (not cert_pem.exists() or not key_pem.exists()
                or pfx_path.stat().st_mtime > cert_pem.stat().st_mtime):
            from cryptography.hazmat.primitives.serialization import (
                Encoding, PrivateFormat, NoEncryption,
            )
            priv_key, cert, _ = self._carregar_pfx()
            cert_pem.write_bytes(cert.public_bytes(Encoding.PEM))
            key_pem.write_bytes(priv_key.private_bytes(
                Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
            ))
        return (str(cert_pem), str(key_pem))

    # ── Assinatura ───────────────────────────────────────────────────────────

    def _assinar(self, xml_str: str, chave: str) -> str:
        """Assina o XML com o certificado A1 (.pfx)."""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            import base64
            from lxml import etree

            priv_key, cert, _ = self._carregar_pfx()

            tree  = etree.fromstring(xml_str.encode())
            ns    = {"nfe": _NS}
            inf   = tree.find(f"nfe:infNFe", ns)

            # Digest do infNFe
            canon = etree.tostring(inf, method="c14n", exclusive=True)
            digest = base64.b64encode(
                hashlib.sha1(canon).digest()
            ).decode()

            # Signature element
            sig_xml = f"""<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
<SignedInfo>
<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
<Reference URI="#NFe{chave}">
<Transforms><Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/></Transforms>
<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
<DigestValue>{digest}</DigestValue>
</Reference>
</SignedInfo>
<SignatureValue/>
<KeyInfo>
<X509Data><X509Certificate>{base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()}</X509Certificate></X509Data>
</KeyInfo>
</Signature>"""

            sig_el = etree.fromstring(sig_xml.encode())
            si     = sig_el.find("{http://www.w3.org/2000/09/xmldsig#}SignedInfo")
            si_can = etree.tostring(si, method="c14n", exclusive=True)
            sig_val = base64.b64encode(
                priv_key.sign(si_can, padding.PKCS1v15(), hashes.SHA1())
            ).decode()
            sig_el.find("{http://www.w3.org/2000/09/xmldsig#}SignatureValue").text = sig_val

            inf.append(sig_el)
            return etree.tostring(tree, encoding="unicode", xml_declaration=False)
        except Exception as e:
            raise RuntimeError(f"Erro ao assinar XML: {e}")

    # ── Transmissão SEFAZ ────────────────────────────────────────────────────

    def _transmitir(self, xml_assinado: str) -> dict:
        """Envia lote para SEFAZ e retorna resultado."""
        lote = f"""<?xml version="1.0" encoding="UTF-8"?>
<enviNFe xmlns="{_NS}" versao="{_VERSAO}">
  <idLote>1</idLote>
  <indSinc>1</indSinc>
  {xml_assinado}
</enviNFe>"""

        soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="{_WSNS}">
      <cUF>{_CUF}</cUF>
      <versaoDados>{_VERSAO}</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="{_WSNS}">{lote}</nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""

        ws_url = _WS_HOMOLOG if self.ambiente == "2" else _WS_PROD
        try:
            # SEFAZ exige TLS mutuo: certificado do contribuinte convertido para PEM
            resp = httpx.post(
                ws_url,
                content=soap.encode("utf-8"),
                headers={"Content-Type": "application/soap+xml; charset=utf-8",
                         "SOAPAction": ""},
                timeout=30.0,
                cert=self._cert_pem_files(),
            )
            return self._parsear_retorno(resp.text)
        except Exception as e:
            return {"cStat": "999", "motivo": str(e)}

    def _parsear_retorno(self, resp_xml: str) -> dict:
        try:
            root = ET.fromstring(resp_xml)
            ns = {"nfe": _NS}
            prot = root.find(f".//{{{_NS}}}protNFe")
            if prot is not None:
                info = prot.find(f"{{{_NS}}}infProt")
                return {
                    "cStat":    self._find(info, "cStat"),
                    "motivo":   self._find(info, "xMotivo"),
                    "protocolo":self._find(info, "nProt"),
                    "xml_proc": resp_xml,
                }
            ret = root.find(f".//{{{_NS}}}retEnviNFe")
            return {
                "cStat":  self._find(ret, "cStat") if ret else "999",
                "motivo": self._find(ret, "xMotivo") if ret else "Resposta inválida",
            }
        except Exception as e:
            return {"cStat": "999", "motivo": str(e)}

    # ── Utilitários ──────────────────────────────────────────────────────────

    def _empresa(self) -> models.CompanyProfile:
        emp = self.db.query(models.CompanyProfile).filter(
            models.CompanyProfile.company_id == self.empresa_id
        ).first()
        if not emp:
            raise ValueError("Perfil da empresa não configurado")
        return emp

    def _proximo_numero(self) -> int:
        ultimo = self.db.query(models.FiscalDocument).filter(
            models.FiscalDocument.model == "NFC-e",
            models.FiscalDocument.series == self.serie,
            models.FiscalDocument.company_id == self.empresa_id,
        ).order_by(models.FiscalDocument.number.desc()).first()
        return (ultimo.number or 0) + 1 if ultimo else 1

    def _ibge(self, empresa) -> str:
        # Mapeamento simplificado AM; em produção use tabela completa
        cidades = {"MANAUS": "1302603", "PARINTINS": "1303403",
                   "ITACOATIARA": "1301902", "MANACAPURU": "1302504"}
        cidade = (empresa.city or "MANAUS").upper().strip()
        return cidades.get(cidade, "1302603")

    def _chave(self, cnpj: str, numero: int, cnf: str) -> str:
        cnpj_num = re.sub(r"\D", "", cnpj).zfill(14)
        aamm     = datetime.now().strftime("%y%m")
        mod      = "65"
        serie    = self.serie.zfill(3)
        nnf      = str(numero).zfill(9)
        tp_emis  = "1"
        base     = (_CUF + aamm + cnpj_num + mod + serie +
                    nnf + tp_emis + cnf.zfill(8))
        dv       = self._mod11(base)
        return base + str(dv)

    @staticmethod
    def _mod11(chave: str) -> int:
        mult, soma = 2, 0
        for d in reversed(chave):
            soma += int(d) * mult
            mult = 2 if mult == 9 else mult + 1
        resto = soma % 11
        return 0 if resto in (0, 1) else 11 - resto

    def _qrcode_url(self, chave: str, venda, dh_emi: str) -> str:
        """Monta a URL do QR Code com cHashQRCode calculado a partir do CSC (NT 2015.002)."""
        from urllib.parse import quote

        base = ("https://homnfe.sefaz.am.gov.br/nfceweb/consultarNFCe.aspx"
                if self.ambiente == "2"
                else "https://nfe.sefaz.am.gov.br/nfceweb/consultarNFCe.aspx")
        v_nf      = f"{float(venda.total):.2f}"
        cid_token = (self.csc_id or "000001").zfill(6)
        raw_query = (
            f"chNFe={chave}&nVersao=100&tpAmb={self.ambiente}&cDest="
            f"&dhEmi={dh_emi}&vNF={v_nf}&vICMS=0.00&digVal="
            f"&cIdToken={cid_token}"
        )
        hash_hex = (
            hashlib.sha1((raw_query + self.csc).encode()).hexdigest().upper()
            if self.csc else ""
        )
        encoded_query = raw_query.replace(dh_emi, quote(dh_emi, safe=""))
        return f"{base}?{encoded_query}&cHashQRCode={hash_hex}"

    @staticmethod
    def _t(parent, tag: str, text: str):
        el = ET.SubElement(parent, f"{{{_NS}}}{tag}")
        el.text = text

    @staticmethod
    def _find(el, tag: str) -> str:
        if el is None:
            return ""
        found = el.find(f"{{{_NS}}}{tag}")
        return found.text if found is not None and found.text else ""
