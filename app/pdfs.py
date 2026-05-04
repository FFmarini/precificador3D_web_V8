from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
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


def generate_orders_budget_pdf(
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

    def new_page():
        _draw_logo(pdf, logo_path, page_height)
        y_pos = top
        _line(pdf, 50 * mm, y_pos, "Orcamento consolidado - Tres De Impressoes", font="Helvetica-Bold", size=16)
        y_pos -= 9 * mm
        _line(pdf, left, y_pos, f"Itens no orcamento: {len(orders)}", size=11)
        y_pos -= 5 * mm
        _line(pdf, left, y_pos, f"Total consolidado: {_money(total_value)}", font="Helvetica-Bold", size=11)
        y_pos -= 8 * mm
        pdf.line(left, y_pos, right, y_pos)
        y_pos -= 6 * mm
        return y_pos

    y = new_page()
    for item in orders:
        if y < bottom + 30 * mm:
            pdf.showPage()
            y = new_page()

        _line(
            pdf,
            left,
            y,
            f"{item['code']} | {_safe_text(item.get('client_name'))} | {_safe_text(item.get('project_name'))}",
            font="Helvetica-Bold",
            size=10,
        )
        y -= 5 * mm
        _line(
            pdf,
            left,
            y,
            f"Status: {_safe_text(item.get('status'))}   Qtd: {int(item.get('pieces') or 0)}   Filamento: {_safe_text(item.get('filament_name'))}",
            size=9,
        )
        y -= 5 * mm
        _line(
            pdf,
            left,
            y,
            f"Cor: {_safe_text(item.get('chosen_color'))}   Total: {_money(item.get('final_price'))}",
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

    _line(pdf, left, y, f"Valor total dos orcamentos: {_money(total_value)}", font="Helvetica-Bold", size=12)
    y -= 12 * mm
    _line(pdf, left, y, "Assinatura: _________________________________________________", size=10)

    pdf.showPage()
    pdf.save()


def _fit_text_lines(text: str, font_name: str, font_size: float, width: float, max_lines: int):
    lines = simpleSplit(_safe_text(text, ""), font_name, font_size, width)
    if not lines:
        return [_safe_text(text)]
    return lines[:max_lines]


def _draw_label_text(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    font_name: str,
    font_size: float,
    max_width: float,
    max_lines: int,
    line_gap: float,
):
    lines = _fit_text_lines(text, font_name, font_size, max_width, max_lines)
    for line in lines:
        pdf.setFont(font_name, font_size)
        pdf.drawString(x, y, line)
        y -= line_gap
    return y


def generate_filament_labels_pdf(
    filaments: list[dict],
    out_path: Path,
    logo_path: Path | None = None,
):
    pdf = canvas.Canvas(str(out_path), pagesize=A4)
    page_width, page_height = A4

    label_width = 40 * mm
    label_height = 25 * mm
    columns = 5
    rows = 11
    margin_x = (page_width - (columns * label_width)) / 2
    margin_y = (page_height - (rows * label_height)) / 2

    def draw_label(item: dict, index: int):
        page_slot = index % (columns * rows)
        col = page_slot % columns
        row = page_slot // columns
        x = margin_x + (col * label_width)
        y = page_height - margin_y - ((row + 1) * label_height)

        pdf.roundRect(x, y, label_width, label_height, 2.5 * mm, stroke=1, fill=0)

        inner_x = x + (2.2 * mm)
        text_y = y + label_height - (4 * mm)
        usable_width = label_width - (4.4 * mm)

        if item.get("code"):
            pdf.setFont("Helvetica", 6.5)
            pdf.drawRightString(x + label_width - (2.2 * mm), text_y, _safe_text(item.get("code")))

        header = " | ".join(part for part in [_safe_text(item.get("brand"), ""), _safe_text(item.get("ftype"), "")] if part)
        if header:
            text_y = _draw_label_text(
                pdf,
                inner_x,
                text_y,
                header,
                "Helvetica",
                6.8,
                usable_width - (12 * mm),
                1,
                3.2 * mm,
            )
        else:
            text_y -= 3.2 * mm

        text_y = _draw_label_text(
            pdf,
            inner_x,
            text_y,
            _safe_text(item.get("name")),
            "Helvetica-Bold",
            8.2,
            usable_width,
            2,
            3.6 * mm,
        )
        text_y -= 0.4 * mm

        color_text = _safe_text(item.get("color"), "")
        if color_text:
            text_y = _draw_label_text(
                pdf,
                inner_x,
                text_y,
                color_text,
                "Helvetica",
                7.2,
                usable_width,
                2,
                3.3 * mm,
            )

    for index, item in enumerate(filaments):
        if index and index % (columns * rows) == 0:
            pdf.showPage()
        draw_label(item, index)

    pdf.showPage()
    pdf.save()
