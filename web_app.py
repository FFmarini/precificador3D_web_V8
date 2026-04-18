import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for

from app.db import (
    add_filament_stock,
    adjust_filament_stock,
    db_connect,
    db_init,
    delete_client,
    delete_filament,
    delete_order,
    delete_project,
    format_order_code,
    get_client,
    get_filament,
    get_low_stock_filaments,
    get_order,
    get_project,
    get_setting,
    list_client_receipt_orders,
    list_clients,
    list_filaments,
    list_orders,
    list_projects,
    list_stock_movements,
    process_order_stock,
    save_client,
    save_filament,
    save_order,
    save_project,
    set_setting,
)
from app.pdfs import generate_client_pdf, generate_client_receipt_pdf
from app.pricing import compute_pricing_farm

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = BASE_DIR / "pdf_out"
UPLOAD_DIR = BASE_DIR / "uploads"
for directory in [DATA_DIR, PDF_DIR, UPLOAD_DIR]:
    directory.mkdir(exist_ok=True)
if not os.environ.get("PREC_DB_PATH"):
    if os.name == "nt":
        local_data_dir = Path(os.environ.get("TEMP", BASE_DIR)) / "PrecificadorWeb"
        local_data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["PREC_DB_PATH"] = str(local_data_dir / "precificador.db")
    else:
        os.environ["PREC_DB_PATH"] = str(DATA_DIR / "precificador.db")

app = Flask(__name__)
app.secret_key = "precificador-web-v8-1"
_DB_READY = False


@app.before_request
def ensure_db():
    global _DB_READY
    if not _DB_READY:
        db_init()
        _DB_READY = True


def to_float(value, default=0.0):
    try:
        return float(str(value or default).replace(",", "."))
    except Exception:
        return float(default)


def to_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return int(default)


def hhmmss_to_seconds(text: str):
    parts = (text or "00:00:00").strip().split(":")
    if len(parts) != 3:
        return 0
    h, m, s = [int(x) for x in parts]
    return h * 3600 + m * 60 + s


def flash_stock_feedback(result):
    if result.get("action") == "discounted":
        flash(f"Estoque baixado automaticamente: {result['grams']:.0f} g.", "success")


def list_args(default_sort="id", default_direction="desc"):
    return {
        "search": (request.args.get("q") or "").strip(),
        "sort": request.args.get("sort") or default_sort,
        "direction": request.args.get("direction") or default_direction,
    }


@app.route("/")
def dashboard():
    orders = list_orders()
    fatur_mes = sum(float(item.get("final_price") or 0) for item in orders)
    lucro_mes = sum(float(item.get("profit") or 0) for item in orders)
    low_stock_filaments = get_low_stock_filaments()
    return render_template(
        "dashboard.html",
        total_orders=len(orders),
        fatur_mes=fatur_mes,
        lucro_mes=lucro_mes,
        low_stock_filaments=low_stock_filaments,
    )


@app.route("/clients")
def clients_page():
    args = list_args(default_sort="nome", default_direction="asc")
    return render_template("clients.html", clients=list_clients(**args), **args)


@app.post("/clients/new")
def clients_new():
    save_client(
        {
            "name": request.form.get("name"),
            "phone": request.form.get("phone"),
            "instagram": request.form.get("instagram"),
            "city": request.form.get("city"),
            "notes": request.form.get("notes"),
        }
    )
    flash("Cliente salvo.", "success")
    return redirect(url_for("clients_page"))


@app.get("/clients/edit/<int:client_id>")
def clients_edit(client_id):
    return render_template("client_edit.html", client=get_client(client_id))


@app.post("/clients/edit/<int:client_id>")
def clients_edit_post(client_id):
    save_client(
        {
            "name": request.form.get("name"),
            "phone": request.form.get("phone"),
            "instagram": request.form.get("instagram"),
            "city": request.form.get("city"),
            "notes": request.form.get("notes"),
        },
        client_id=client_id,
    )
    flash("Cliente atualizado.", "success")
    return redirect(url_for("clients_page"))


@app.get("/clients/delete/<int:client_id>")
def clients_delete(client_id):
    delete_client(client_id)
    flash("Cliente excluído.", "success")
    return redirect(url_for("clients_page"))


@app.get("/clients/<int:client_id>/receipt")
def clients_receipt(client_id):
    client = get_client(client_id)
    if not client:
        flash("Cliente não encontrado.", "warning")
        return redirect(url_for("clients_page"))

    orders = list_client_receipt_orders(client_id)
    if not orders:
        flash("Esse cliente ainda não tem pedidos para recibo.", "warning")
        return redirect(url_for("clients_page"))

    logo_path = get_setting("pdf_logo_path")
    logo_path = Path(logo_path) if logo_path else None
    pdf_path = PDF_DIR / f"recibo_cliente_{client_id}.pdf"
    generate_client_receipt_pdf(client, orders, pdf_path, logo_path=logo_path)
    return send_from_directory(pdf_path.parent.resolve(), pdf_path.name, as_attachment=True)


@app.route("/filaments")
def filaments_page():
    args = list_args(default_sort="nome", default_direction="asc")
    return render_template("filaments.html", filaments=list_filaments(**args), **args)


@app.post("/filaments/new")
def filaments_new():
    save_filament(
        {
            "name": request.form.get("name"),
            "brand": request.form.get("brand"),
            "ftype": request.form.get("ftype"),
            "color": request.form.get("color"),
            "code": request.form.get("code"),
            "price_per_kg": to_float(request.form.get("price_per_kg")),
            "notes": request.form.get("notes"),
            "stock_grams": to_float(request.form.get("stock_grams")),
            "min_stock_alert_grams": to_float(request.form.get("min_stock_alert_grams"), 200.0),
            "spool_weight_grams": to_float(request.form.get("spool_weight_grams"), 1000.0),
        }
    )
    flash("Filamento salvo.", "success")
    return redirect(url_for("filaments_page"))


@app.get("/filaments/edit/<int:fid>")
def filaments_edit(fid):
    return render_template("filament_edit.html", filament=get_filament(fid))


@app.post("/filaments/edit/<int:fid>")
def filaments_edit_post(fid):
    save_filament(
        {
            "name": request.form.get("name"),
            "brand": request.form.get("brand"),
            "ftype": request.form.get("ftype"),
            "color": request.form.get("color"),
            "code": request.form.get("code"),
            "price_per_kg": to_float(request.form.get("price_per_kg")),
            "notes": request.form.get("notes"),
            "stock_grams": to_float(request.form.get("stock_grams")),
            "min_stock_alert_grams": to_float(request.form.get("min_stock_alert_grams"), 200.0),
            "spool_weight_grams": to_float(request.form.get("spool_weight_grams"), 1000.0),
        },
        filament_id=fid,
    )
    flash("Filamento atualizado.", "success")
    return redirect(url_for("filaments_page"))


@app.post("/filaments/<int:fid>/stock/add")
def filaments_stock_add(fid):
    filament = get_filament(fid)
    if not filament:
        flash("Filamento não encontrado.", "warning")
        return redirect(url_for("filaments_page"))

    direct_grams = to_float(request.form.get("grams"), 0.0)
    spool_count = to_float(request.form.get("spool_count"), 0.0)
    spool_weight = to_float(
        request.form.get("spool_weight_grams"), filament.get("spool_weight_grams", 1000.0)
    )
    grams = direct_grams if direct_grams > 0 else spool_count * spool_weight
    if grams <= 0:
        flash("Informe gramas diretas ou rolos x peso do rolo.", "warning")
        return redirect(request.referrer or url_for("filaments_page"))

    notes = request.form.get("notes") or "Entrada manual de estoque"
    add_filament_stock(fid, grams, notes=notes)
    flash(f"Entrada registrada: +{grams:.0f} g.", "success")
    return redirect(request.referrer or url_for("filaments_page"))


@app.post("/filaments/<int:fid>/stock/adjust")
def filaments_stock_adjust(fid):
    grams = to_float(request.form.get("adjust_grams"), 0.0)
    if grams == 0:
        flash("Informe um ajuste diferente de zero.", "warning")
        return redirect(request.referrer or url_for("filaments_page"))

    notes = request.form.get("notes") or "Ajuste manual de estoque"
    adjust_filament_stock(fid, grams, notes=notes)
    flash(f"Ajuste registrado: {grams:+.0f} g.", "success")
    return redirect(request.referrer or url_for("filaments_page"))


@app.get("/filaments/delete/<int:fid>")
def filaments_delete(fid):
    delete_filament(fid)
    flash("Filamento excluído.", "success")
    return redirect(url_for("filaments_page"))


@app.route("/projects")
def projects_page():
    args = list_args(default_sort="nome", default_direction="asc")
    return render_template("projects.html", projects=list_projects(**args), **args)


@app.post("/projects/new")
def projects_new():
    save_project(
        {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "thumbnail_url": request.form.get("thumbnail_url"),
            "notes": request.form.get("notes"),
        }
    )
    flash("Projeto salvo.", "success")
    return redirect(url_for("projects_page"))


@app.get("/projects/edit/<int:project_id>")
def projects_edit(project_id):
    return render_template("project_edit.html", project=get_project(project_id))


@app.post("/projects/edit/<int:project_id>")
def projects_edit_post(project_id):
    save_project(
        {
            "name": request.form.get("name"),
            "url": request.form.get("url"),
            "thumbnail_url": request.form.get("thumbnail_url"),
            "notes": request.form.get("notes"),
        },
        project_id=project_id,
    )
    flash("Projeto atualizado.", "success")
    return redirect(url_for("projects_page"))


@app.get("/projects/delete/<int:project_id>")
def projects_delete(project_id):
    delete_project(project_id)
    flash("Projeto excluído.", "success")
    return redirect(url_for("projects_page"))


@app.route("/orders")
def orders_page():
    args = list_args()
    return render_template(
        "orders.html",
        page_title="Pedidos",
        page_description="Pedidos ativos: tudo que ainda exige atenção.",
        show_new_form=True,
        orders=list_orders(view="active", **args),
        clients=list_clients(),
        projects=list_projects(),
        filaments=list_filaments(),
        logo=get_setting("pdf_logo_path") or "",
        **args,
    )


@app.route("/stock")
def stock_page():
    args = list_args()
    return render_template(
        "orders.html",
        page_title="Estoque",
        page_description="Itens cadastrados como estoque.",
        show_new_form=False,
        orders=list_orders(view="stock", **args),
        clients=[],
        projects=[],
        filaments=[],
        logo="",
        **args,
    )


@app.route("/history")
def history_page():
    args = list_args()
    return render_template(
        "orders.html",
        page_title="Histórico",
        page_description="Pedidos entregues ou cancelados.",
        show_new_form=False,
        orders=list_orders(view="history", **args),
        clients=[],
        projects=[],
        filaments=[],
        logo="",
        **args,
    )


@app.post("/orders/new")
def orders_new():
    pieces = to_int(request.form.get("pieces"), 1)
    time_sec_per_piece = hhmmss_to_seconds(request.form.get("time_text"))
    filament_g_per_piece = to_float(request.form.get("filament_g_per_piece"))
    calc = compute_pricing_farm(
        pieces=pieces,
        time_sec_per_piece=time_sec_per_piece,
        filament_g_per_piece=filament_g_per_piece,
        filament_price_per_kg=to_float(request.form.get("filament_price_per_kg")),
        energy_price_per_kwh=to_float(request.form.get("energy_price_per_kwh")),
        printer_avg_watts=to_float(request.form.get("printer_avg_watts")),
        machine_cost_per_hour=to_float(request.form.get("machine_cost_per_hour")),
        labor_cost_fixed=to_float(request.form.get("labor_cost_fixed")),
        margin_percent=to_float(request.form.get("margin_percent")),
        round_to=to_float(request.form.get("round_to"), 1),
        failure_rate_percent=to_float(request.form.get("failure_rate_percent")),
        overhead_percent=to_float(request.form.get("overhead_percent")),
        packaging_cost=to_float(request.form.get("packaging_cost")),
        platform_fee_percent=to_float(request.form.get("platform_fee_percent")),
        payment_fee_percent=to_float(request.form.get("payment_fee_percent")),
        shipping_price=to_float(request.form.get("shipping_price")),
        discount_value=to_float(request.form.get("discount_value")),
    )
    order_id = save_order(
        {
            "client_id": to_int(request.form.get("client_id")),
            "project_id": to_int(request.form.get("project_id")),
            "filament_id": to_int(request.form.get("filament_id")) or None,
            "pieces": pieces,
            "time_seconds_per_piece": time_sec_per_piece,
            "filament_g_per_piece": filament_g_per_piece,
            "chosen_color": request.form.get("chosen_color"),
            "status": request.form.get("status") or "Orçado",
            "payment_method": request.form.get("payment_method") or "Pix",
            "is_paid": 1 if request.form.get("is_paid") == "on" else 0,
            "notes": request.form.get("notes"),
            "filament_price_per_kg": to_float(request.form.get("filament_price_per_kg")),
            "energy_price_per_kwh": to_float(request.form.get("energy_price_per_kwh")),
            "printer_avg_watts": to_float(request.form.get("printer_avg_watts")),
            "machine_cost_per_hour": to_float(request.form.get("machine_cost_per_hour")),
            "labor_cost_fixed": to_float(request.form.get("labor_cost_fixed")),
            "margin_percent": to_float(request.form.get("margin_percent")),
            "round_to": to_float(request.form.get("round_to"), 1),
            "failure_rate_percent": to_float(request.form.get("failure_rate_percent")),
            "overhead_percent": to_float(request.form.get("overhead_percent")),
            "packaging_cost": to_float(request.form.get("packaging_cost")),
            "platform_fee_percent": to_float(request.form.get("platform_fee_percent")),
            "payment_fee_percent": to_float(request.form.get("payment_fee_percent")),
            "shipping_price": to_float(request.form.get("shipping_price")),
            "discount_value": to_float(request.form.get("discount_value")),
            "total_cost": calc["total_cost"],
            "product_price": calc["product_price"],
            "fees_estimated": calc["fees_estimated"],
            "profit": calc["profit"],
            "final_price": calc["final_price"],
        }
    )
    flash("Pedido salvo.", "success")
    flash_stock_feedback(process_order_stock(order_id))
    return redirect(url_for("orders_page"))


@app.get("/orders/edit/<int:order_id>")
def orders_edit(order_id):
    return render_template(
        "order_edit.html",
        order=get_order(order_id),
        clients=list_clients(),
        projects=list_projects(),
        filaments=list_filaments(),
    )


@app.post("/orders/edit/<int:order_id>")
def orders_edit_post(order_id):
    pieces = to_int(request.form.get("pieces"), 1)
    time_sec_per_piece = hhmmss_to_seconds(request.form.get("time_text"))
    filament_g_per_piece = to_float(request.form.get("filament_g_per_piece"))
    calc = compute_pricing_farm(
        pieces=pieces,
        time_sec_per_piece=time_sec_per_piece,
        filament_g_per_piece=filament_g_per_piece,
        filament_price_per_kg=to_float(request.form.get("filament_price_per_kg")),
        energy_price_per_kwh=to_float(request.form.get("energy_price_per_kwh")),
        printer_avg_watts=to_float(request.form.get("printer_avg_watts")),
        machine_cost_per_hour=to_float(request.form.get("machine_cost_per_hour")),
        labor_cost_fixed=to_float(request.form.get("labor_cost_fixed")),
        margin_percent=to_float(request.form.get("margin_percent")),
        round_to=to_float(request.form.get("round_to"), 1),
        failure_rate_percent=to_float(request.form.get("failure_rate_percent")),
        overhead_percent=to_float(request.form.get("overhead_percent")),
        packaging_cost=to_float(request.form.get("packaging_cost")),
        platform_fee_percent=to_float(request.form.get("platform_fee_percent")),
        payment_fee_percent=to_float(request.form.get("payment_fee_percent")),
        shipping_price=to_float(request.form.get("shipping_price")),
        discount_value=to_float(request.form.get("discount_value")),
    )
    save_order(
        {
            "client_id": to_int(request.form.get("client_id")),
            "project_id": to_int(request.form.get("project_id")),
            "filament_id": to_int(request.form.get("filament_id")) or None,
            "pieces": pieces,
            "time_seconds_per_piece": time_sec_per_piece,
            "filament_g_per_piece": filament_g_per_piece,
            "chosen_color": request.form.get("chosen_color"),
            "status": request.form.get("status") or "Orçado",
            "payment_method": request.form.get("payment_method") or "Pix",
            "is_paid": 1 if request.form.get("is_paid") == "on" else 0,
            "notes": request.form.get("notes"),
            "filament_price_per_kg": to_float(request.form.get("filament_price_per_kg")),
            "energy_price_per_kwh": to_float(request.form.get("energy_price_per_kwh")),
            "printer_avg_watts": to_float(request.form.get("printer_avg_watts")),
            "machine_cost_per_hour": to_float(request.form.get("machine_cost_per_hour")),
            "labor_cost_fixed": to_float(request.form.get("labor_cost_fixed")),
            "margin_percent": to_float(request.form.get("margin_percent")),
            "round_to": to_float(request.form.get("round_to"), 1),
            "failure_rate_percent": to_float(request.form.get("failure_rate_percent")),
            "overhead_percent": to_float(request.form.get("overhead_percent")),
            "packaging_cost": to_float(request.form.get("packaging_cost")),
            "platform_fee_percent": to_float(request.form.get("platform_fee_percent")),
            "payment_fee_percent": to_float(request.form.get("payment_fee_percent")),
            "shipping_price": to_float(request.form.get("shipping_price")),
            "discount_value": to_float(request.form.get("discount_value")),
            "total_cost": calc["total_cost"],
            "product_price": calc["product_price"],
            "fees_estimated": calc["fees_estimated"],
            "profit": calc["profit"],
            "final_price": calc["final_price"],
        },
        order_id=order_id,
    )
    flash("Pedido atualizado.", "success")
    flash_stock_feedback(process_order_stock(order_id))
    return redirect(url_for("orders_page"))


@app.get("/orders/delete/<int:order_id>")
def orders_delete(order_id):
    delete_order(order_id)
    flash("Pedido excluído.", "success")
    return redirect(url_for("orders_page"))


@app.get("/orders/pdf/<int:order_id>")
def orders_pdf(order_id):
    con = db_connect()
    row = con.execute(
        """
        SELECT o.*, c.name AS client_name, p.name AS project_name, COALESCE(f.name,'') AS filament_name
        FROM orders o
        JOIN clients c ON c.id=o.client_id
        JOIN projects p ON p.id=o.project_id
        LEFT JOIN filaments f ON f.id=o.filament_id
        WHERE o.id=?
        """,
        (order_id,),
    ).fetchone()
    con.close()
    if not row:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("orders_page"))
    logo_path = get_setting("pdf_logo_path")
    logo_path = Path(logo_path) if logo_path else None
    pdf_path = Path("pdf_out") / f"{format_order_code(row['order_no'])}.pdf"
    generate_client_pdf(dict(row), pdf_path, logo_path=logo_path)
    return send_from_directory(pdf_path.parent.resolve(), pdf_path.name, as_attachment=True)


@app.post("/settings/logo")
def settings_logo():
    uploaded = request.files.get("logo")
    if not uploaded or not uploaded.filename:
        flash("Selecione um arquivo.", "warning")
        return redirect(url_for("orders_page"))
    ext = Path(uploaded.filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        flash("Arquivo inválido.", "warning")
        return redirect(url_for("orders_page"))
    output = UPLOAD_DIR / f"logo{ext}"
    uploaded.save(output)
    set_setting("pdf_logo_path", str(output.resolve()))
    flash("Logo salva.", "success")
    return redirect(url_for("orders_page"))


@app.get("/stock/movements")
def stock_movements_page():
    filament_id = to_int(request.args.get("filament_id"), 0) or None
    return render_template(
        "stock_movements.html",
        movements=list_stock_movements(fid=filament_id, limit=200),
        filaments=list_filaments(),
        selected_filament_id=filament_id,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
