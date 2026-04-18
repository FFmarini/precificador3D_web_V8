from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _draw_logo(pdf: canvas.Canvas, logo_path: Path | None, page_height: float):
    if not logo_path or not logo_path.exists():
        return
    try:
        pdf.drawImage(
            str(logo_path),
            15 * mm,
            page_height - 35 * mm,
            width=30 * mm,
            height=30 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        return


def _line(pdf: canvas.Canvas, x: float, y: float, text: str, font="Helvetica", size=10):
    pdf.setFont(font, size)
    pdf.drawString(x, y, text)


def _money(value) -> str:
    return f"R$ {float(value or 0):.2f}"


def _safe_text(value, fallback="-"):
    text = str(value or "").strip()
    return text if text else fallback


def generate_client_pdf(order_row, out_path: Path, logo_path: Path | None = None):
    pdf = canvas.Canvas(str(out_path), pagesize=A4)
    _, page_height = A4
    y = page_height - 20 * mm
    _draw_logo(pdf, logo_path, page_height)

    _line(pdf, 50 * mm, y, "Orcamento - Tres De Impressoes", font="Helvetica-Bold", size=16)
    y -= 12 * mm
    _line(pdf, 15 * mm, y, f"Cliente: {_safe_text(order_row['client_name'])}", size=11)
    y -= 6 * mm
    _line(pdf, 15 * mm, y, f"Projeto: {_safe_text(order_row['project_name'])}", size=11)
    y -= 6 * mm
    _line(pdf, 15 * mm, y, f"Filamento: {_safe_text(order_row.get('filament_name'))}", size=11)
    y -= 6 * mm
    _line(pdf, 15 * mm, y, f"Cor escolhida: {_safe_text(order_row.get('chosen_color'))}", size=11)
    y -= 6 * mm
    _line(pdf, 15 * mm, y, f"Quantidade: {int(order_row['pieces'])}", size=11)
    y -= 10 * mm
    _line(
        pdf,
        15 * mm,
        y,
        f"TOTAL (cliente): {_money(order_row['final_price'])}",
        font="Helvetica-Bold",
        size=14,
    )
    y -= 10 * mm
    _line(pdf, 15 * mm, y, "Observacoes:", size=10)
    y -= 5 * mm
    _line(pdf, 15 * mm, y, _safe_text(order_row.get("notes"), "")[:120], size=10)
    pdf.showPage()
    pdf.save()


def generate_client_receipt_pdf(
    client: dict,
    orders: list[dict],
    out_path: Path,
    logo_path: Path | None = None,
):
    pdf = canvas.Canvas(str(out_path), pagesize=A4)
    page_width, page_height = A4
    left = 15 * mm
    right = page_width - 15 * mm
    top = page_height - 20 * mm
    bottom = 20 * mm

    total_value = sum(float(item.get("final_price") or 0) for item in orders)
    paid_value = sum(float(item.get("final_price") or 0) for item in orders if int(item.get("is_paid") or 0))
    pending_value = total_value - paid_value

    def new_page():
        _draw_logo(pdf, logo_path, page_height)
        y_pos = top
        _line(pdf, 50 * mm, y_pos, "Recibo consolidado - Tres De Impressoes", font="Helvetica-Bold", size=16)
        y_pos -= 9 * mm
        _line(pdf, left, y_pos, f"Cliente: {_safe_text(client.get('name'))}", size=11)
        y_pos -= 5 * mm
        _line(
            pdf,
            left,
            y_pos,
            f"Telefone: {_safe_text(client.get('phone'))}   Cidade: {_safe_text(client.get('city'))}",
            size=10,
        )
        y_pos -= 5 * mm
        _line(
            pdf,
            left,
            y_pos,
            f"Pedidos no recibo: {len(orders)}   Total: {_money(total_value)}   Pago: {_money(paid_value)}   Em aberto: {_money(pending_value)}",
            font="Helvetica-Bold",
            size=10,
        )
        y_pos -= 8 * mm
        pdf.line(left, y_pos, right, y_pos)
        y_pos -= 6 * mm
        return y_pos

    y = new_page()
    for item in orders:
        if y < bottom + 28 * mm:
            pdf.showPage()
            y = new_page()

        _line(
            pdf,
            left,
            y,
            f"{item['code']} | {_safe_text(item.get('project_name'))} | Status: {_safe_text(item.get('status'))}",
            font="Helvetica-Bold",
            size=10,
        )
        y -= 5 * mm
        _line(
            pdf,
            left,
            y,
            f"Qtd: {int(item.get('pieces') or 0)}   Filamento: {_safe_text(item.get('filament_name'))}   Cor: {_safe_text(item.get('chosen_color'))}",
            size=9,
        )
        y -= 5 * mm
        _line(
            pdf,
            left,
            y,
            f"Pagamento: {_safe_text(item.get('payment_method'))}   Pago: {'Sim' if int(item.get('is_paid') or 0) else 'Nao'}   Valor: {_money(item.get('final_price'))}",
            size=9,
        )
        notes = _safe_text(item.get("notes"), "")
        if notes:
            y -= 5 * mm
            _line(pdf, left, y, f"Obs.: {notes[:100]}", size=9)
        y -= 6 * mm
        pdf.line(left, y, right, y)
        y -= 6 * mm

    if y < bottom + 18 * mm:
        pdf.showPage()
        y = new_page()

    _line(pdf, left, y, "Resumo final", font="Helvetica-Bold", size=12)
    y -= 6 * mm
    _line(pdf, left, y, f"Total consolidado: {_money(total_value)}", size=10)
    y -= 5 * mm
    _line(pdf, left, y, f"Total pago: {_money(paid_value)}", size=10)
    y -= 5 * mm
    _line(pdf, left, y, f"Saldo em aberto: {_money(pending_value)}", size=10)
    y -= 12 * mm
    _line(pdf, left, y, "Assinatura: _________________________________________________", size=10)

    pdf.showPage()
    pdf.save()
