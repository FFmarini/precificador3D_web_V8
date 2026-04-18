import math

def round_up(value: float, step: float) -> float:
    if not step or step <= 0:
        return float(value)
    return math.ceil(value / step) * step

def compute_pricing_farm(
    *,
    pieces: int,
    time_sec_per_piece: int,
    filament_g_per_piece: float,
    filament_price_per_kg: float,
    energy_price_per_kwh: float,
    printer_avg_watts: float,
    machine_cost_per_hour: float,
    labor_cost_fixed: float,
    margin_percent: float,
    round_to: float,
    failure_rate_percent: float,
    overhead_percent: float,
    packaging_cost: float,
    platform_fee_percent: float,
    payment_fee_percent: float,
    shipping_price: float,
    discount_value: float,
) -> dict:
    pieces = max(int(pieces or 1), 1)
    time_sec_per_piece = max(int(time_sec_per_piece or 0), 0)
    filament_g_per_piece = max(float(filament_g_per_piece or 0), 0.0)

    total_time_sec = time_sec_per_piece * pieces
    total_hours = total_time_sec / 3600.0

    total_filament_g = filament_g_per_piece * pieces
    filament_cost = (total_filament_g / 1000.0) * float(filament_price_per_kg or 0)

    energy_kwh = (float(printer_avg_watts or 0) / 1000.0) * total_hours
    energy_cost = energy_kwh * float(energy_price_per_kwh or 0)
    machine_cost = total_hours * float(machine_cost_per_hour or 0)

    base_cost = filament_cost + energy_cost + machine_cost + float(labor_cost_fixed or 0)
    base_cost *= (1.0 + (float(failure_rate_percent or 0) / 100.0))
    cost_with_overhead = base_cost * (1.0 + (float(overhead_percent or 0) / 100.0))

    product_price = cost_with_overhead * (1.0 + (float(margin_percent or 0) / 100.0))
    product_price = round_up(product_price, float(round_to or 1))

    fees_estimated = product_price * (float(platform_fee_percent or 0) / 100.0)
    fees_estimated += product_price * (float(payment_fee_percent or 0) / 100.0)

    packaging_cost = float(packaging_cost or 0)
    shipping_price = float(shipping_price or 0)
    discount_value = float(discount_value or 0)

    final_price = product_price + packaging_cost + shipping_price - discount_value
    final_price = max(0.0, final_price)

    profit = final_price - cost_with_overhead - fees_estimated - packaging_cost - shipping_price

    return {
        "total_time_sec": int(total_time_sec),
        "total_filament_g": float(total_filament_g),
        "total_cost": round(cost_with_overhead, 2),
        "product_price": round(product_price, 2),
        "fees_estimated": round(fees_estimated, 2),
        "final_price": round(final_price, 2),
        "profit": round(profit, 2),
    }
