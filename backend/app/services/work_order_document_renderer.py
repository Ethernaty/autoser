from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from typing import Literal
from zipfile import ZIP_DEFLATED, ZipFile


DocumentLocale = Literal["ru", "en"]

_MISSING = "-"

_I18N: dict[DocumentLocale, dict[str, object]] = {
    "ru": {
        "lang": "ru",
        "title": "Заказ-наряд",
        "subtitle": "Документ автосервиса",
        "labels": {
            "number": "Номер",
            "name": "Имя",
            "phone": "Телефон",
            "email": "Email",
            "comment": "Комментарий",
            "plate": "Госномер",
            "model": "Марка / модель",
            "year": "Год",
            "vin": "VIN",
            "description": "Описание",
            "total": "Итого",
            "paid": "Оплачено",
            "remaining": "Остаток",
            "index": "#",
            "line_name": "Наименование",
            "line_type": "Тип",
            "qty": "Кол-во",
            "unit": "Цена",
            "line_total": "Сумма",
            "date": "Дата",
            "amount": "Сумма",
            "method": "Метод",
            "client_signature": "Подпись клиента",
            "executor_signature": "Подпись исполнителя",
        },
        "sections": {
            "client": "Данные клиента",
            "vehicle": "Данные автомобиля",
            "order": "Сводка заказа",
            "lines": "Позиции работ и запчастей",
            "payments": "Оплаты",
        },
        "empty_lines_title": "Позиции пока не добавлены",
        "empty_lines_note": "Добавьте работы и материалы, чтобы заполнить заказ-наряд.",
        "empty_payments_title": "Оплаты пока не зафиксированы",
        "empty_payments_note": "После фиксации оплаты записи появятся в таблице.",
        "statuses": {
            "new": "Новый",
            "in_progress": "В работе",
            "completed_unpaid": "Завершен, не оплачен",
            "completed_paid": "Завершен, оплачен",
            "cancelled": "Отменен",
        },
        "line_types": {"labor": "Работа", "part": "Запчасть", "misc": "Прочее"},
        "payment_methods": {"cash": "Наличные", "card": "Карта", "transfer": "Перевод", "other": "Прочее"},
    },
    "en": {
        "lang": "en",
        "title": "Work Order",
        "subtitle": "Auto-service document",
        "labels": {
            "number": "Number",
            "name": "Name",
            "phone": "Phone",
            "email": "Email",
            "comment": "Comment",
            "plate": "Plate",
            "model": "Make / model",
            "year": "Year",
            "vin": "VIN",
            "description": "Description",
            "total": "Total",
            "paid": "Paid",
            "remaining": "Remaining",
            "index": "#",
            "line_name": "Name",
            "line_type": "Type",
            "qty": "Qty",
            "unit": "Unit Price",
            "line_total": "Line Total",
            "date": "Date",
            "amount": "Amount",
            "method": "Method",
            "client_signature": "Client signature",
            "executor_signature": "Executor signature",
        },
        "sections": {
            "client": "Client Information",
            "vehicle": "Vehicle Information",
            "order": "Order Summary",
            "lines": "Work Lines",
            "payments": "Payments",
        },
        "empty_lines_title": "No line items added yet",
        "empty_lines_note": "Add labor and parts to complete this work order.",
        "empty_payments_title": "No payments recorded yet",
        "empty_payments_note": "Payments will appear here after they are recorded.",
        "statuses": {
            "new": "New",
            "in_progress": "In Progress",
            "completed_unpaid": "Completed Unpaid",
            "completed_paid": "Completed Paid",
            "cancelled": "Cancelled",
        },
        "line_types": {"labor": "Labor", "part": "Part", "misc": "Misc"},
        "payment_methods": {"cash": "Cash", "card": "Card", "transfer": "Transfer", "other": "Other"},
    },
}


@dataclass(frozen=True)
class WorkOrderDocumentLine:
    line_type: str
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    comment: str | None


@dataclass(frozen=True)
class WorkOrderDocumentPayment:
    amount: Decimal
    method: str
    paid_at: datetime
    comment: str | None


@dataclass(frozen=True)
class WorkOrderDocumentSnapshot:
    order_number: int
    description: str
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    client_name: str
    client_phone: str
    client_email: str | None
    vehicle_plate_number: str | None
    vehicle_make_model: str | None
    vehicle_year: int | None
    vehicle_vin: str | None
    lines: list[WorkOrderDocumentLine]
    payments: list[WorkOrderDocumentPayment]


def _locale(locale: str | None) -> DocumentLocale:
    if locale and locale.lower().startswith("en"):
        return "en"
    return "ru"


def _copy(locale: str | None) -> dict[str, object]:
    return _I18N[_locale(locale)]


def _map(copy_map: dict[str, object], key: str) -> dict[str, str]:
    value = copy_map.get(key)
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    return {}


def _text(copy_map: dict[str, object], key: str) -> str:
    value = copy_map.get(key)
    return str(value) if isinstance(value, str) else key


def _label(copy_map: dict[str, object], key: str) -> str:
    return _map(copy_map, "labels").get(key, key)


def _section(copy_map: dict[str, object], key: str) -> str:
    return _map(copy_map, "sections").get(key, key)


def _display(value: str | None) -> str:
    if value is None:
        return _MISSING
    clean = value.strip()
    return clean if clean else _MISSING


def _fmt_dt(value: datetime, locale: DocumentLocale) -> str:
    if locale == "ru":
        return value.strftime("%d.%m.%Y %H:%M")
    return value.strftime("%Y-%m-%d %H:%M")


def _fmt_money(value: Decimal, locale: DocumentLocale) -> str:
    formatted = f"{Decimal(value):,.2f}"
    if locale == "ru":
        return formatted.replace(",", " ").replace(".", ",")
    return formatted


def _fmt_qty(value: Decimal, locale: DocumentLocale) -> str:
    raw = f"{Decimal(value):f}".rstrip("0").rstrip(".")
    if not raw:
        raw = "0"
    return raw.replace(".", ",") if locale == "ru" else raw


def _enum_label(value: str, mapping: dict[str, str]) -> str:
    return mapping.get(value, value.replace("_", " ").title())


def _escape_multiline(value: str | None) -> str:
    return escape(_display(value)).replace("\n", "<br/>")


def _html_rows(fields: list[tuple[str, str]]) -> str:
    return "".join(
        f"<div class='row'><span class='k'>{escape(label)}</span><span class='v'>{escape(val)}</span></div>"
        for label, val in fields
    )


def render_work_order_html(snapshot: WorkOrderDocumentSnapshot, *, locale: str | None = None) -> bytes:
    doc_locale = _locale(locale)
    copy_map = _copy(locale)
    line_types = _map(copy_map, "line_types")
    payment_methods = _map(copy_map, "payment_methods")
    vehicle_year = str(snapshot.vehicle_year) if snapshot.vehicle_year is not None else _MISSING
    info_rows = f"""
      <tr>
        <th>{escape(_label(copy_map, "name"))}</th>
        <td>{escape(_display(snapshot.client_name))}</td>
        <th>{escape(_label(copy_map, "phone"))}</th>
        <td>{escape(_display(snapshot.client_phone))}</td>
      </tr>
      <tr>
        <th>{escape(_label(copy_map, "email"))}</th>
        <td>{escape(_display(snapshot.client_email))}</td>
        <th>{escape(_label(copy_map, "plate"))}</th>
        <td>{escape(_display(snapshot.vehicle_plate_number))}</td>
      </tr>
      <tr>
        <th>{escape(_label(copy_map, "model"))}</th>
        <td>{escape(_display(snapshot.vehicle_make_model))}</td>
        <th>{escape(_label(copy_map, "year"))}</th>
        <td>{escape(vehicle_year)}</td>
      </tr>
      <tr>
        <th>{escape(_label(copy_map, "vin"))}</th>
        <td colspan="3">{escape(_display(snapshot.vehicle_vin))}</td>
      </tr>
      <tr>
        <th>{escape(_label(copy_map, "description"))}</th>
        <td colspan="3">{_escape_multiline(snapshot.description)}</td>
      </tr>
    """

    line_rows = "".join(
        f"""
        <tr>
          <td>{idx}</td>
          <td>{escape(item.name)}</td>
          <td>{escape(_enum_label(item.line_type, line_types))}</td>
          <td>{escape(_fmt_qty(item.quantity, doc_locale))}</td>
          <td>{escape(_fmt_money(item.unit_price, doc_locale))}</td>
          <td>{escape(_fmt_money(item.line_total, doc_locale))}</td>
        </tr>
        """
        for idx, item in enumerate(snapshot.lines, start=1)
    )
    if not line_rows:
        line_rows = (
            "<tr><td colspan='6' class='empty'>"
            f"<div class='et'>{escape(_text(copy_map, 'empty_lines_title'))}</div>"
            f"<div class='en'>{escape(_text(copy_map, 'empty_lines_note'))}</div>"
            "</td></tr>"
        )

    payment_rows = "".join(
        f"""
        <tr>
          <td>{escape(_fmt_dt(item.paid_at, doc_locale))}</td>
          <td>{escape(_fmt_money(item.amount, doc_locale))}</td>
          <td>{escape(_enum_label(item.method, payment_methods))}</td>
        </tr>
        """
        for item in snapshot.payments
    )
    if not payment_rows:
        payment_rows = (
            "<tr><td colspan='3' class='empty'>"
            f"<div class='et'>{escape(_text(copy_map, 'empty_payments_title'))}</div>"
            f"<div class='en'>{escape(_text(copy_map, 'empty_payments_note'))}</div>"
            "</td></tr>"
        )

    html = f"""<!doctype html>
<html lang="{_text(copy_map, "lang")}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(_text(copy_map, "title"))} #{snapshot.order_number}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 12px; background: #f8fafc; color: #0f172a; font: 400 13px/1.42 Arial, sans-serif; }}
    .doc {{ max-width: 980px; margin: 0 auto; background: #fff; border: 1px solid #cbd5e1; padding: 12px; }}
    .head {{ border: 1px solid #cbd5e1; padding: 10px 12px; display: grid; gap: 8px; }}
    .brand {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #475569; }}
    h1 {{ margin: 0; text-align: center; font-size: 21px; line-height: 1.22; }}
    .sub {{ margin: 0; text-align: center; color: #64748b; font-size: 12px; }}
    .meta {{ margin-top: 4px; display: flex; justify-content: flex-end; }}
    .meta-chip {{ border: 1px solid #cbd5e1; background: #f8fafc; padding: 5px 9px; font-size: 12px; font-weight: 700; }}
    .sec {{ margin-top: 10px; border: 1px solid #cbd5e1; padding: 9px; break-inside: avoid; }}
    .st {{ margin: 0 0 7px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #334155; }}
    table {{ width: 100%; border-collapse: collapse; border: 1px solid #cbd5e1; }}
    th, td {{ border: 1px solid #dbe5f0; padding: 6px 7px; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; color: #334155; font-weight: 700; }}
    td {{ font-size: 12px; word-break: break-word; }}
    .form-table th {{ width: 20%; }}
    .form-table td {{ width: 30%; }}
    .totals {{ margin-top: 9px; display: grid; gap: 8px; grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .t {{ border: 1px solid #dbe5f0; padding: 8px; }}
    .t .k {{ display: block; font-size: 10px; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: .04em; }}
    .t .v {{ display: block; margin-top: 2px; font-size: 17px; line-height: 1.15; font-weight: 700; color: #0f172a; }}
    .t.total {{ background: #f8fafc; }}
    .t.paid {{ background: #f0fdf4; }}
    .t.rem {{ background: #fff7ed; }}
    .empty {{ background: #f8fafc; padding: 10px 8px; }} .et {{ font-size: 12px; font-weight: 700; color: #334155; }}
    .en {{ margin-top: 2px; font-size: 11px; color: #64748b; }}
    .sign {{ margin-top: 10px; display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }}
    .sign-item {{ border-top: 1px solid #94a3b8; padding-top: 4px; font-size: 11px; color: #475569; text-align: center; }}
    @media (max-width: 860px) {{ body {{ padding: 8px; }} .totals, .sign {{ grid-template-columns: 1fr; }} .form-table th, .form-table td {{ width: auto; }} }}
    @page {{ size: A4; margin: 12mm; }}
    @media print {{ body {{ background: #fff; padding: 0; }} .doc {{ border: 0; padding: 0; max-width: none; }} .head, .sec, table {{ break-inside: avoid; }} .t {{ background: #fff !important; }} }}
  </style>
</head>
<body>
  <div class="doc">
    <header class="head">
      <div class="brand">AutoService CRM</div>
      <h1>{escape(_text(copy_map, "title"))}</h1>
      <p class="sub">{escape(_text(copy_map, "subtitle"))}</p>
      <div class="meta"><span class="meta-chip">{escape(_label(copy_map, "number"))}: #{snapshot.order_number}</span></div>
    </header>

    <section class="sec">
      <h2 class="st">{escape(_section(copy_map, "client"))} / {escape(_section(copy_map, "vehicle"))}</h2>
      <table class="form-table"><tbody>{info_rows}</tbody></table>
    </section>

    <section class="sec" style="margin-top:10px;">
      <h2 class="st">{escape(_section(copy_map, "order"))}</h2>
      <div class="totals">
        <div class="t total"><span class="k">{escape(_label(copy_map, "total"))}</span><span class="v">{escape(_fmt_money(snapshot.total_amount, doc_locale))}</span></div>
        <div class="t paid"><span class="k">{escape(_label(copy_map, "paid"))}</span><span class="v">{escape(_fmt_money(snapshot.paid_amount, doc_locale))}</span></div>
        <div class="t rem"><span class="k">{escape(_label(copy_map, "remaining"))}</span><span class="v">{escape(_fmt_money(snapshot.remaining_amount, doc_locale))}</span></div>
      </div>
    </section>

    <section class="sec" style="margin-top:10px;">
      <h2 class="st">{escape(_section(copy_map, "lines"))}</h2>
      <table>
        <thead><tr>
          <th>{escape(_label(copy_map, "index"))}</th><th>{escape(_label(copy_map, "line_name"))}</th><th>{escape(_label(copy_map, "line_type"))}</th>
          <th>{escape(_label(copy_map, "qty"))}</th><th>{escape(_label(copy_map, "unit"))}</th><th>{escape(_label(copy_map, "line_total"))}</th>
        </tr></thead>
        <tbody>{line_rows}</tbody>
        <tfoot><tr><th colspan="5" style="text-align:right;">{escape(_label(copy_map, "total"))}</th><th>{escape(_fmt_money(snapshot.total_amount, doc_locale))}</th></tr></tfoot>
      </table>
    </section>

    <section class="sec" style="margin-top:10px;">
      <h2 class="st">{escape(_section(copy_map, "payments"))}</h2>
      <table>
        <thead><tr>
          <th>{escape(_label(copy_map, "date"))}</th><th>{escape(_label(copy_map, "amount"))}</th><th>{escape(_label(copy_map, "method"))}</th>
        </tr></thead>
        <tbody>{payment_rows}</tbody>
      </table>
    </section>

    <div class="sign">
      <div class="sign-item">{escape(_label(copy_map, "client_signature"))}</div>
      <div class="sign-item">{escape(_label(copy_map, "executor_signature"))}</div>
    </div>
  </div>
</body>
</html>
"""
    return html.encode("utf-8")


def _fit_text(text: str, *, limit: int = 108) -> list[str]:
    source = text.strip()
    if not source:
        return [""]
    lines: list[str] = []
    for raw in source.splitlines() or [""]:
        lines.extend(wrap(raw, width=limit) or [""])
    return lines


def _pdf_font() -> str:
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        return "Helvetica"

    for candidate in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ):
        if not candidate.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("AutoServiceDocFont", str(candidate)))
            return "AutoServiceDocFont"
        except Exception:
            continue
    return "Helvetica"


def render_work_order_pdf(snapshot: WorkOrderDocumentSnapshot, *, locale: str | None = None) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("reportlab_required_for_pdf_generation") from exc

    doc_locale = _locale(locale)
    copy_map = _copy(locale)
    line_types = _map(copy_map, "line_types")
    payment_methods = _map(copy_map, "payment_methods")

    font = _pdf_font()
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{_text(copy_map, 'title')} #{snapshot.order_number}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "wo_title",
        parent=styles["Heading1"],
        fontName=font,
        fontSize=18,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=2,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "wo_subtitle",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
    )
    brand_style = ParagraphStyle(
        "wo_brand",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#475569"),
    )
    meta_style = ParagraphStyle(
        "wo_meta",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.2,
        leading=11,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#0f172a"),
    )
    section_style = ParagraphStyle(
        "wo_section",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10.2,
        leading=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "wo_body",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.6,
        leading=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0f172a"),
    )
    label_style = ParagraphStyle(
        "wo_label",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8.2,
        leading=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#334155"),
    )

    def p(value: str, style: ParagraphStyle) -> Paragraph:
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    def section_title(value: str) -> Paragraph:
        return p(value.upper(), section_style)

    story: list[object] = []
    border_color = colors.HexColor("#cbd5e1")
    grid_color = colors.HexColor("#dbe5f0")

    header_data = [
        [p("AUTOSERVICE CRM", brand_style), p(f"{_label(copy_map, 'number')}: #{snapshot.order_number}", meta_style)],
        [p(_text(copy_map, "title"), title_style), ""],
        [p(_text(copy_map, "subtitle"), subtitle_style), ""],
    ]
    header = Table(header_data, colWidths=[doc.width * 0.72, doc.width * 0.28])
    header.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 2), (1, 2)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 5 * mm))

    vehicle_year = str(snapshot.vehicle_year) if snapshot.vehicle_year is not None else _MISSING
    info_table_data = [
        [p(_label(copy_map, "name").upper(), label_style), p(_display(snapshot.client_name), body_style), p(_label(copy_map, "phone").upper(), label_style), p(_display(snapshot.client_phone), body_style)],
        [p(_label(copy_map, "email").upper(), label_style), p(_display(snapshot.client_email), body_style), p(_label(copy_map, "plate").upper(), label_style), p(_display(snapshot.vehicle_plate_number), body_style)],
        [p(_label(copy_map, "model").upper(), label_style), p(_display(snapshot.vehicle_make_model), body_style), p(_label(copy_map, "year").upper(), label_style), p(vehicle_year, body_style)],
        [p(_label(copy_map, "vin").upper(), label_style), p(_display(snapshot.vehicle_vin), body_style), "", ""],
        [p(_label(copy_map, "description").upper(), label_style), p(_display(snapshot.description), body_style), "", ""],
    ]
    info_table = Table(info_table_data, colWidths=[doc.width * 0.16, doc.width * 0.34, doc.width * 0.16, doc.width * 0.34])
    info_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                ("SPAN", (1, 3), (3, 3)),
                ("SPAN", (1, 4), (3, 4)),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (2, 0), (2, 2), colors.HexColor("#f8fafc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    info_block = Table([[section_title(f"{_section(copy_map, 'client')} / {_section(copy_map, 'vehicle')}")], [info_table]], colWidths=[doc.width])
    info_block.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_block)
    story.append(Spacer(1, 4 * mm))

    total_cells = []
    for key, value, bg in [
        (_label(copy_map, "total"), _fmt_money(snapshot.total_amount, doc_locale), colors.HexColor("#f8fafc")),
        (_label(copy_map, "paid"), _fmt_money(snapshot.paid_amount, doc_locale), colors.HexColor("#f0fdf4")),
        (_label(copy_map, "remaining"), _fmt_money(snapshot.remaining_amount, doc_locale), colors.HexColor("#fff7ed")),
    ]:
        total_cells.append(
            Paragraph(
                f"<font size='7' color='#64748b'><b>{escape(key.upper())}</b></font><br/><font size='14' color='#0f172a'><b>{escape(value)}</b></font>",
                ParagraphStyle("tot_cell", parent=styles["Normal"], fontName=font, leading=14, alignment=TA_LEFT),
            )
        )
    totals_table = Table([total_cells], colWidths=[doc.width / 3] * 3)
    totals_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f0fdf4")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#fff7ed")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    summary_block = Table([[section_title(_section(copy_map, "order"))], [totals_table]], colWidths=[doc.width])
    summary_block.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_block)
    story.append(Spacer(1, 4 * mm))

    line_header = [
        p(_label(copy_map, "index").upper(), label_style),
        p(_label(copy_map, "line_name").upper(), label_style),
        p(_label(copy_map, "line_type").upper(), label_style),
        p(_label(copy_map, "qty").upper(), label_style),
        p(_label(copy_map, "unit").upper(), label_style),
        p(_label(copy_map, "line_total").upper(), label_style),
    ]
    line_rows: list[list[object]] = [line_header]
    if snapshot.lines:
        for idx, item in enumerate(snapshot.lines, start=1):
            line_rows.append(
                [
                    p(str(idx), body_style),
                    p(item.name, body_style),
                    p(_enum_label(item.line_type, line_types), body_style),
                    p(_fmt_qty(item.quantity, doc_locale), body_style),
                    p(_fmt_money(item.unit_price, doc_locale), body_style),
                    p(_fmt_money(item.line_total, doc_locale), body_style),
                ]
            )
        line_rows.append(
            [
                p("", body_style),
                p("", body_style),
                p("", body_style),
                p("", body_style),
                p(_label(copy_map, "total").upper(), ParagraphStyle("tot_label", parent=label_style, alignment=TA_RIGHT)),
                p(_fmt_money(snapshot.total_amount, doc_locale), ParagraphStyle("tot_value", parent=body_style, alignment=TA_LEFT)),
            ]
        )
    else:
        line_rows.append([p(_text(copy_map, "empty_lines_title"), body_style), "", "", "", "", ""])

    lines_table = Table(
        line_rows,
        colWidths=[doc.width * 0.07, doc.width * 0.33, doc.width * 0.16, doc.width * 0.12, doc.width * 0.16, doc.width * 0.16],
        repeatRows=1,
    )
    line_style: list[tuple] = [
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if snapshot.lines:
        total_row_idx = len(line_rows) - 1
        line_style.extend([("SPAN", (0, total_row_idx), (4, total_row_idx)), ("ALIGN", (0, total_row_idx), (4, total_row_idx), "RIGHT")])
    else:
        line_style.extend(
            [
                ("SPAN", (0, 1), (5, 1)),
                ("BACKGROUND", (0, 1), (5, 1), colors.HexColor("#f8fafc")),
            ]
        )
    lines_table.setStyle(TableStyle(line_style))
    lines_block = Table([[section_title(_section(copy_map, "lines"))], [lines_table]], colWidths=[doc.width])
    lines_block.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(lines_block)
    story.append(Spacer(1, 4 * mm))

    payment_header = [p(_label(copy_map, "date").upper(), label_style), p(_label(copy_map, "amount").upper(), label_style), p(_label(copy_map, "method").upper(), label_style)]
    payment_table_rows: list[list[object]] = [payment_header]
    if snapshot.payments:
        for item in snapshot.payments:
            payment_table_rows.append(
                [
                    p(_fmt_dt(item.paid_at, doc_locale), body_style),
                    p(_fmt_money(item.amount, doc_locale), body_style),
                    p(_enum_label(item.method, payment_methods), body_style),
                ]
            )
    else:
        payment_table_rows.append([p(_text(copy_map, "empty_payments_title"), body_style), "", ""])

    payments_table = Table(payment_table_rows, colWidths=[doc.width * 0.4, doc.width * 0.3, doc.width * 0.3], repeatRows=1)
    payment_style: list[tuple] = [
        ("BOX", (0, 0), (-1, -1), 0.75, border_color),
        ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if not snapshot.payments:
        payment_style.extend([("SPAN", (0, 1), (2, 1)), ("BACKGROUND", (0, 1), (2, 1), colors.HexColor("#f8fafc"))])
    payments_table.setStyle(TableStyle(payment_style))
    payments_block = Table([[section_title(_section(copy_map, "payments"))], [payments_table]], colWidths=[doc.width])
    payments_block.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.75, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(payments_block)
    story.append(Spacer(1, 4 * mm))

    signatures = Table(
        [[p(_label(copy_map, "client_signature"), ParagraphStyle("sig", parent=body_style, alignment=TA_CENTER, textColor=colors.HexColor("#475569"))), p(_label(copy_map, "executor_signature"), ParagraphStyle("sig2", parent=body_style, alignment=TA_CENTER, textColor=colors.HexColor("#475569")))]],
        colWidths=[doc.width / 2, doc.width / 2],
    )
    signatures.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (0, 0), 0.75, colors.HexColor("#94a3b8")),
                ("LINEABOVE", (1, 0), (1, 0), 0.75, colors.HexColor("#94a3b8")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(signatures)

    doc.build(story)
    return pdf_buffer.getvalue()


def _docx_p(text: str, *, bold: bool = False) -> str:
    safe = escape(text)
    run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (
        "<w:p><w:r>"
        f"{run_props}"
        f"<w:t xml:space='preserve'>{safe}</w:t>"
        "</w:r></w:p>"
    )


def render_work_order_docx(snapshot: WorkOrderDocumentSnapshot, *, locale: str | None = None) -> bytes:
    doc_locale = _locale(locale)
    copy_map = _copy(locale)
    line_types = _map(copy_map, "line_types")
    payment_methods = _map(copy_map, "payment_methods")

    body: list[str] = []
    body.append(_docx_p(_text(copy_map, "title"), bold=True))
    body.append(_docx_p(f"{_label(copy_map, 'number')}: #{snapshot.order_number}"))
    body.append(_docx_p(""))

    body.append(_docx_p(_section(copy_map, "client"), bold=True))
    body.append(_docx_p(f"{_label(copy_map, 'name')}: {_display(snapshot.client_name)}"))
    body.append(_docx_p(f"{_label(copy_map, 'phone')}: {_display(snapshot.client_phone)}"))
    body.append(_docx_p(f"{_label(copy_map, 'email')}: {_display(snapshot.client_email)}"))
    body.append(_docx_p(""))

    body.append(_docx_p(_section(copy_map, "vehicle"), bold=True))
    body.append(_docx_p(f"{_label(copy_map, 'plate')}: {_display(snapshot.vehicle_plate_number)}"))
    body.append(_docx_p(f"{_label(copy_map, 'model')}: {_display(snapshot.vehicle_make_model)}"))
    body.append(_docx_p(f"{_label(copy_map, 'year')}: {snapshot.vehicle_year if snapshot.vehicle_year is not None else _MISSING}"))
    body.append(_docx_p(f"{_label(copy_map, 'vin')}: {_display(snapshot.vehicle_vin)}"))
    body.append(_docx_p(""))

    body.append(_docx_p(_section(copy_map, "order"), bold=True))
    body.append(_docx_p(f"{_label(copy_map, 'description')}: {_display(snapshot.description)}"))
    body.append(_docx_p(f"{_label(copy_map, 'total')}: {_fmt_money(snapshot.total_amount, doc_locale)}"))
    body.append(_docx_p(f"{_label(copy_map, 'paid')}: {_fmt_money(snapshot.paid_amount, doc_locale)}"))
    body.append(_docx_p(f"{_label(copy_map, 'remaining')}: {_fmt_money(snapshot.remaining_amount, doc_locale)}"))
    body.append(_docx_p(""))

    body.append(_docx_p(_section(copy_map, "lines"), bold=True))
    if snapshot.lines:
        for idx, item in enumerate(snapshot.lines, start=1):
            body.append(
                _docx_p(
                    f"{idx}. {item.name} | {_label(copy_map, 'line_type')}: {_enum_label(item.line_type, line_types)}"
                    f" | {_label(copy_map, 'qty')}: {_fmt_qty(item.quantity, doc_locale)}"
                    f" | {_label(copy_map, 'unit')}: {_fmt_money(item.unit_price, doc_locale)}"
                    f" | {_label(copy_map, 'line_total')}: {_fmt_money(item.line_total, doc_locale)}"
                )
            )
            if item.comment:
                body.append(_docx_p(f"{_label(copy_map, 'comment')}: {item.comment}"))
    else:
        body.append(_docx_p(_text(copy_map, "empty_lines_title")))
    body.append(_docx_p(""))

    body.append(_docx_p(_section(copy_map, "payments"), bold=True))
    if snapshot.payments:
        for idx, item in enumerate(snapshot.payments, start=1):
            body.append(
                _docx_p(
                    f"{idx}. {_label(copy_map, 'date')}: {_fmt_dt(item.paid_at, doc_locale)}"
                    f" | {_label(copy_map, 'amount')}: {_fmt_money(item.amount, doc_locale)}"
                    f" | {_label(copy_map, 'method')}: {_enum_label(item.method, payment_methods)}"
                )
            )
            if item.comment:
                body.append(_docx_p(f"{_label(copy_map, 'comment')}: {item.comment}"))
    else:
        body.append(_docx_p(_text(copy_map, "empty_payments_title")))

    document_xml = (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
        "<w:body>"
        + "".join(body)
        + "<w:sectPr><w:pgSz w:w='11906' w:h='16838'/><w:pgMar w:top='1440' w:right='1440' w:bottom='1440' w:left='1440'/></w:sectPr>"
        + "</w:body></w:document>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return output.getvalue()
