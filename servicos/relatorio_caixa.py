"""
Relatório de Fechamento de Caixa
=================================
Monta os dados consolidados e por caixa (lançamentos, vendas por forma de
pagamento e conferência sistema x informado) e gera as versões em PDF
(A4 e cupom) e o texto de resumo para envio por WhatsApp.

Acesso restrito a admin e gerente (ver auth.require_gerente nas rotas).
"""
from io import BytesIO
from typing import Optional
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session, joinedload

import models

ROTULOS_METODO = {
    "dinheiro": "Dinheiro",
    "debito": "Débito",
    "credito": "Crédito",
    "pix": "PIX",
    "fiado": "Fiado",
    "vale": "Vale",
}

ROTULOS_MOVIMENTO = {
    "suprimento": "Suprimento",
    "sangria": "Sangria",
    "despesa": "Despesa",
    "vale_funcionario": "Vale Funcionário",
}


def formatar_valor(valor: float, sinal: bool = False) -> str:
    """Formata um número no padrão brasileiro (ex: 1.234,56), opcionalmente com sinal +/-."""
    texto = f"{valor:+,.2f}" if sinal else f"{valor:,.2f}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


def formatar_moeda(valor: float) -> str:
    """Formata um valor em reais no padrão brasileiro (ex: R$ 1.234,56)."""
    return f"R$ {formatar_valor(valor)}"


def caixas_no_periodo(banco: Session, date_from: str, date_to: str, caixa_id: Optional[int] = None):
    """
    Caixas fechados dentro do período (independente de quando foram abertos) +
    caixas ainda abertos que foram abertos dentro do período.
    """
    query = (
        banco.query(models.CashRegister)
        .options(
            joinedload(models.CashRegister.user),
            joinedload(models.CashRegister.sales).joinedload(models.Sale.payments),
            joinedload(models.CashRegister.cash_movements),
            joinedload(models.CashRegister.closing_counts),
        )
        .filter(
            or_(
                # Caixa fechado dentro do período (independente de quando foi aberto)
                and_(
                    models.CashRegister.closed_at.isnot(None),
                    func.date(models.CashRegister.closed_at) >= date_from,
                    func.date(models.CashRegister.closed_at) <= date_to,
                ),
                # Caixa ainda aberto, aberto dentro do período
                and_(
                    models.CashRegister.closed_at.is_(None),
                    func.date(models.CashRegister.opened_at) >= date_from,
                    func.date(models.CashRegister.opened_at) <= date_to,
                ),
            )
        )
    )
    if caixa_id:
        query = query.filter(models.CashRegister.id == caixa_id)
    return query.order_by(models.CashRegister.opened_at.asc()).all()


def _resumo_caixa(caixa: models.CashRegister) -> dict:
    movimentos = []
    entrada_total = 0.0
    saida_total = 0.0
    for mv in caixa.cash_movements:
        valor = float(mv.amount)
        is_entrada = mv.type == models.CashMovementType.suprimento
        entrada = valor if is_entrada else 0.0
        saida = valor if not is_entrada else 0.0
        entrada_total += entrada
        saida_total += saida
        movimentos.append({
            "tipo": ROTULOS_MOVIMENTO.get(mv.type.value, mv.type.value),
            "motivo": mv.reason or "—",
            "entrada": entrada,
            "saida": saida,
        })

    # Fiado não é dinheiro recebido no caixa (gera conta a receber do cliente),
    # por isso fica de fora das Vendas/Conferência e some num bloco próprio.
    vendas_por_metodo = {}
    fiado_total = 0.0
    for venda in caixa.sales:
        if venda.status == models.SaleStatus.finalizada:
            for pagamento in venda.payments:
                metodo = pagamento.method.value
                if metodo == "fiado":
                    fiado_total += float(pagamento.amount)
                else:
                    vendas_por_metodo[metodo] = vendas_por_metodo.get(metodo, 0) + float(pagamento.amount)

    resumo = []
    for contagem in sorted(caixa.closing_counts, key=lambda c: c.method.value):
        if contagem.method == models.PaymentMethod.fiado:
            continue
        sistema_v = float(contagem.system_amount)
        informado_v = float(contagem.informed_amount)
        resumo.append({
            "method": contagem.method.value,
            "system": sistema_v,
            "informed": informado_v,
            "diff": informado_v - sistema_v,
        })

    return {
        "id": caixa.id,
        "user_name": caixa.user.full_name if caixa.user else "—",
        "opened_at": caixa.opened_at,
        "closed_at": caixa.closed_at,
        "status": caixa.status.value,
        "opening_balance": float(caixa.opening_balance or 0),
        "movements": movimentos,
        "movements_total": {"entrada": entrada_total, "saida": saida_total},
        "sales_by_method": vendas_por_metodo,
        "sales_total": sum(vendas_por_metodo.values()),
        "fiado_total": fiado_total,
        "summary": resumo,
        "summary_total": {
            "system": sum(r["system"] for r in resumo),
            "informed": sum(r["informed"] for r in resumo),
            "diff": sum(r["diff"] for r in resumo),
        },
    }


def montar_relatorio(banco: Session, date_from: str, date_to: str, caixa_id: Optional[int] = None) -> dict:
    """Monta os dados do relatório de fechamento: cada caixa do período + o consolidado."""
    caixas = caixas_no_periodo(banco, date_from, date_to, caixa_id)
    por_caixa = [_resumo_caixa(c) for c in caixas]

    movs_consolidado = []
    entrada_consolidado = saida_consolidado = 0.0
    vendas_consolidado = {}
    fiado_consolidado = 0.0
    fundo_consolidado = 0.0
    resumo_acumulado = {}
    for c in por_caixa:
        movs_consolidado.extend(c["movements"])
        entrada_consolidado += c["movements_total"]["entrada"]
        saida_consolidado += c["movements_total"]["saida"]
        fiado_consolidado += c["fiado_total"]
        fundo_consolidado += c["opening_balance"]
        for metodo, valor in c["sales_by_method"].items():
            vendas_consolidado[metodo] = vendas_consolidado.get(metodo, 0) + valor
        for r in c["summary"]:
            acumulado = resumo_acumulado.setdefault(r["method"], {"system": 0.0, "informed": 0.0})
            acumulado["system"] += r["system"]
            acumulado["informed"] += r["informed"]

    resumo_consolidado = []
    for metodo in sorted(resumo_acumulado.keys()):
        dados = resumo_acumulado[metodo]
        resumo_consolidado.append({
            "method": metodo,
            "system": dados["system"],
            "informed": dados["informed"],
            "diff": dados["informed"] - dados["system"],
        })

    consolidado = {
        "movements": movs_consolidado,
        "movements_total": {"entrada": entrada_consolidado, "saida": saida_consolidado},
        "sales_by_method": vendas_consolidado,
        "sales_total": sum(vendas_consolidado.values()),
        "fiado_total": fiado_consolidado,
        "opening_balance": fundo_consolidado,
        "summary": resumo_consolidado,
        "summary_total": {
            "system": sum(r["system"] for r in resumo_consolidado),
            "informed": sum(r["informed"] for r in resumo_consolidado),
            "diff": sum(r["diff"] for r in resumo_consolidado),
        },
    }

    return {
        "date_from": date_from,
        "date_to": date_to,
        "caixa_id": caixa_id,
        "caixas": por_caixa,
        "consolidado": consolidado,
    }


def texto_resumo_whatsapp(dados: dict, nome_empresa: str) -> str:
    """Texto plano (compatível com formatação do WhatsApp) para o link wa.me."""
    consolidado = dados["consolidado"]
    linhas = [
        f"*Relatório de Caixa — {nome_empresa}*",
        f"Período: {dados['date_from']} a {dados['date_to']}",
    ]
    if len(dados["caixas"]) == 1:
        caixa = dados["caixas"][0]
        linhas.append(f"Caixa #{caixa['id']} — {caixa['user_name']}")
        linhas.append(f"Fundo de Abertura: {formatar_moeda(caixa['opening_balance'])}")
    elif dados["caixas"]:
        linhas.append(f"{len(dados['caixas'])} caixa(s) no período")
        linhas.append(f"Fundo total: {formatar_moeda(consolidado['opening_balance'])}")

    if consolidado["movements"]:
        linhas.append("")
        linhas.append("*Lançamentos de Caixa:*")
        for m in consolidado["movements"]:
            valor = m["entrada"] or m["saida"]
            sinal = "+" if m["entrada"] else "-"
            linhas.append(f"{m['tipo']} ({m['motivo']}): {sinal}{formatar_moeda(valor)}")
        linhas.append(
            f"Total Entradas: {formatar_moeda(consolidado['movements_total']['entrada'])} "
            f"/ Total Saídas: {formatar_moeda(consolidado['movements_total']['saida'])}"
        )

    linhas.append("")
    linhas.append("*Vendas por forma de pagamento:*")
    for metodo, valor in consolidado["sales_by_method"].items():
        linhas.append(f"{ROTULOS_METODO.get(metodo, metodo)}: {formatar_moeda(valor)}")
    linhas.append(f"Total recebido: {formatar_moeda(consolidado['sales_total'])}")

    if consolidado["fiado_total"]:
        linhas.append(f"Fiado (a receber, não entra no caixa): {formatar_moeda(consolidado['fiado_total'])}")

    if consolidado["summary"]:
        linhas.append("")
        linhas.append("*Conferência (Sistema x Informado):*")
        for r in consolidado["summary"]:
            linhas.append(
                f"{ROTULOS_METODO.get(r['method'], r['method'])}: "
                f"Sist. {formatar_moeda(r['system'])} / Inf. {formatar_moeda(r['informed'])} "
                f"(Dif. {formatar_valor(r['diff'], sinal=True)})"
            )
        linhas.append(f"Diferença total: {formatar_valor(consolidado['summary_total']['diff'], sinal=True)}")

    return "\n".join(linhas)


# ─── Geração de PDF ───────────────────────────────────────────────────────────

def _linhas_movimentos(c: dict) -> list:
    cabecalho = [["Tipo", "Motivo", "Entrada", "Saída"]]
    if not c["movements"]:
        return cabecalho + [["—", "Sem lançamentos", "—", "—"]]
    linhas = [[m["tipo"], m["motivo"], formatar_moeda(m["entrada"]) if m["entrada"] else "—",
               formatar_moeda(m["saida"]) if m["saida"] else "—"] for m in c["movements"]]
    linhas.append(["Total", "", formatar_moeda(c["movements_total"]["entrada"]), formatar_moeda(c["movements_total"]["saida"])])
    return cabecalho + linhas


def _linhas_vendas(c: dict) -> list:
    cabecalho = [["Forma de Pagamento", "Valor"]]
    if not c["sales_by_method"]:
        return cabecalho + [["Sem vendas", "—"]]
    linhas = [[ROTULOS_METODO.get(m, m), formatar_moeda(v)] for m, v in c["sales_by_method"].items()]
    linhas.append(["Total Recebido", formatar_moeda(c["sales_total"])])
    return cabecalho + linhas


def _linhas_resumo(c: dict) -> list:
    cabecalho = [["Forma", "Sistema", "Informado", "Diferença"]]
    if not c["summary"]:
        return cabecalho + [["Sem conferência", "—", "—", "—"]]
    linhas = [[
        ROTULOS_METODO.get(r["method"], r["method"]),
        formatar_moeda(r["system"]), formatar_moeda(r["informed"]), formatar_valor(r["diff"], sinal=True),
    ] for r in c["summary"]]
    total = c["summary_total"]
    linhas.append(["Total", formatar_moeda(total["system"]), formatar_moeda(total["informed"]), formatar_valor(total["diff"], sinal=True)])
    return cabecalho + linhas


def gerar_pdf_a4(dados: dict, nome_empresa: str) -> bytes:
    """Relatório completo em página A4."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    estilos = getSampleStyleSheet()
    historia = [
        Paragraph(f"<b>Relatório de Fechamento de Caixa</b>", estilos["Title"]),
        Paragraph(nome_empresa, estilos["Normal"]),
        Paragraph(f"Período: {dados['date_from']} a {dados['date_to']}", estilos["Normal"]),
        Spacer(1, 10 * mm),
    ]

    def tabela(linhas, larguras):
        t = Table(linhas, colWidths=larguras)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f3f5")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        return t

    secoes = list(dados["caixas"])
    mostrar_consolidado = dados["caixa_id"] is None and len(secoes) != 1
    if mostrar_consolidado:
        secoes = [{"id": None, "user_name": None, **dados["consolidado"]}] + secoes

    for c in secoes:
        if c["id"] is None:
            titulo = f"Consolidado — {len(dados['caixas'])} caixa(s)"
            periodo = f"Fundo total: {formatar_moeda(c['opening_balance'])}"
        else:
            titulo = f"Caixa #{c['id']} — Operador(a): {c['user_name']}"
            periodo = f"Abertura: {c['opened_at'].strftime('%d/%m/%Y %H:%M')}"
            if c["closed_at"]:
                periodo += f" | Encerramento: {c['closed_at'].strftime('%d/%m/%Y %H:%M')}"
            else:
                periodo += " | Caixa ainda aberto"
            periodo += f" | Fundo de Abertura: {formatar_moeda(c['opening_balance'])}"

        historia.append(Paragraph(titulo, estilos["Heading3"]))
        historia.append(Paragraph(periodo, estilos["Normal"]))
        historia.append(Spacer(1, 3 * mm))

        historia.append(Paragraph("Lançamentos de Caixa", estilos["Heading4"]))
        historia.append(tabela(_linhas_movimentos(c), [35 * mm, 65 * mm, 30 * mm, 30 * mm]))
        historia.append(Spacer(1, 4 * mm))

        historia.append(Paragraph("Vendas por Forma de Pagamento (recebido no caixa)", estilos["Heading4"]))
        historia.append(tabela(_linhas_vendas(c), [120 * mm, 40 * mm]))
        historia.append(Spacer(1, 4 * mm))

        historia.append(Paragraph("Conferência — Sistema x Informado", estilos["Heading4"]))
        historia.append(tabela(_linhas_resumo(c), [60 * mm, 40 * mm, 40 * mm, 40 * mm]))
        historia.append(Spacer(1, 4 * mm))

        historia.append(Paragraph(
            f"<b>Fiado (a receber, não entra no caixa):</b> {formatar_moeda(c['fiado_total'])}",
            estilos["Normal"],
        ))
        historia.append(Spacer(1, 8 * mm))

    doc.build(historia)
    return buffer.getvalue()


def gerar_pdf_cupom(dados: dict, nome_empresa: str) -> bytes:
    """Relatório no formato de cupom (papel térmico estreito, 80mm)."""
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(80 * mm, 250 * mm),
        topMargin=4 * mm, bottomMargin=4 * mm, leftMargin=3 * mm, rightMargin=3 * mm,
    )
    base = getSampleStyleSheet()
    titulo_st = ParagraphStyle("cupomTitulo", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10, alignment=1)
    centro_st = ParagraphStyle("cupomCentro", parent=base["Normal"], fontSize=7.5, alignment=1)
    secao_st = ParagraphStyle("cupomSecao", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, spaceBefore=4, spaceAfter=2)
    fonte = 7.5

    historia = [
        Paragraph(nome_empresa, titulo_st),
        Paragraph("Relatório de Fechamento de Caixa", centro_st),
        Paragraph(f"Período: {dados['date_from']} a {dados['date_to']}", centro_st),
    ]

    def tabela(linhas, larguras):
        t = Table(linhas, colWidths=larguras)
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), fonte),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        return t

    secoes = list(dados["caixas"])
    mostrar_consolidado = dados["caixa_id"] is None and len(secoes) != 1
    if mostrar_consolidado:
        secoes = [{"id": None, "user_name": None, **dados["consolidado"]}] + secoes

    largura_total = 74 * mm
    for c in secoes:
        historia.append(HRFlowable(width="100%", thickness=0.5, spaceBefore=3, spaceAfter=3))
        if c["id"] is None:
            historia.append(Paragraph(f"CONSOLIDADO ({len(dados['caixas'])} caixas)", secao_st))
            historia.append(Paragraph(f"Fundo total: {formatar_moeda(c['opening_balance'])}", centro_st))
        else:
            historia.append(Paragraph(f"CAIXA #{c['id']} — {c['user_name']}", secao_st))
            sub = c["opened_at"].strftime("%d/%m %H:%M")
            sub += " a " + c["closed_at"].strftime("%d/%m %H:%M") if c["closed_at"] else " (aberto)"
            historia.append(Paragraph(sub, centro_st))
            historia.append(Paragraph(f"Fundo de Abertura: {formatar_moeda(c['opening_balance'])}", centro_st))

        historia.append(Paragraph("Lançamentos", secao_st))
        historia.append(tabela(_linhas_movimentos(c), [largura_total * 0.22, largura_total * 0.38, largura_total * 0.2, largura_total * 0.2]))

        historia.append(Paragraph("Vendas (recebido no caixa)", secao_st))
        historia.append(tabela(_linhas_vendas(c), [largura_total * 0.6, largura_total * 0.4]))

        historia.append(Paragraph("Conferência", secao_st))
        historia.append(tabela(_linhas_resumo(c), [largura_total * 0.3, largura_total * 0.23, largura_total * 0.23, largura_total * 0.24]))

        historia.append(Paragraph(
            f"Fiado (a receber, não entra no caixa): {formatar_moeda(c['fiado_total'])}",
            ParagraphStyle("cupomFiado", parent=base["Normal"], fontSize=fonte, spaceBefore=3),
        ))

    doc.build(historia)
    return buffer.getvalue()
