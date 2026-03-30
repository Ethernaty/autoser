from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from zipfile import ZIP_DEFLATED, ZipFile


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
    work_order_id: str
    status: str
    description: str
    created_at: datetime
    updated_at: datetime
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    client_name: str
    client_phone: str
    client_email: str | None
    client_source: str | None
    client_comment: str | None
    vehicle_plate_number: str | None
    vehicle_make_model: str | None
    vehicle_year: int | None
    vehicle_vin: str | None
    vehicle_comment: str | None
    lines: list[WorkOrderDocumentLine]
    payments: list[WorkOrderDocumentPayment]


def _fmt_money(value: Decimal) -> str:
    return f"{Decimal(value):.2f}"


def _fmt_dt(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def render_work_order_html(snapshot: WorkOrderDocumentSnapshot) -> bytes:
    lines_rows = "".join(
        f"""
        <tr>
          <td>{index}</td>
          <td>{escape(item.name)}</td>
          <td>{escape(item.line_type)}</td>
          <td>{escape(str(item.quantity))}</td>
          <td>{_fmt_money(item.unit_price)}</td>
          <td>{_fmt_money(item.line_total)}</td>
          <td>{escape(item.comment or "-")}</td>
        </tr>
        """
        for index, item in enumerate(snapshot.lines, start=1)
    )
    if not lines_rows:
        lines_rows = "<tr><td colspan='7'>No lines added</td></tr>"

    payment_rows = "".join(
        f"""
        <tr>
          <td>{_fmt_dt(item.paid_at)}</td>
          <td>{_fmt_money(item.amount)}</td>
          <td>{escape(item.method)}</td>
          <td>{escape(item.comment or "-")}</td>
        </tr>
        """
        for item in snapshot.payments
    )
    if not payment_rows:
        payment_rows = "<tr><td colspan='4'>No payments</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Work order {escape(snapshot.work_order_id)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 24px; font-size: 13px; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    h2 {{ margin: 20px 0 8px; font-size: 16px; }}
    .muted {{ color: #6b7280; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .box {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Work Order</h1>
  <p class="muted">#{escape(snapshot.work_order_id)} | Status: {escape(snapshot.status)}</p>

  <div class="grid">
    <div class="box">
      <h2>Client</h2>
      <p><strong>Name:</strong> {escape(snapshot.client_name)}</p>
      <p><strong>Phone:</strong> {escape(snapshot.client_phone)}</p>
      <p><strong>Email:</strong> {escape(snapshot.client_email or "-")}</p>
      <p><strong>Source:</strong> {escape(snapshot.client_source or "-")}</p>
      <p><strong>Comment:</strong> {escape(snapshot.client_comment or "-")}</p>
    </div>
    <div class="box">
      <h2>Vehicle</h2>
      <p><strong>Plate:</strong> {escape(snapshot.vehicle_plate_number or "-")}</p>
      <p><strong>Model:</strong> {escape(snapshot.vehicle_make_model or "-")}</p>
      <p><strong>Year:</strong> {escape(str(snapshot.vehicle_year) if snapshot.vehicle_year is not None else "-")}</p>
      <p><strong>VIN:</strong> {escape(snapshot.vehicle_vin or "-")}</p>
      <p><strong>Comment:</strong> {escape(snapshot.vehicle_comment or "-")}</p>
    </div>
  </div>

  <div class="box" style="margin-top: 12px;">
    <h2>Order</h2>
    <p><strong>Description:</strong> {escape(snapshot.description)}</p>
    <p><strong>Created:</strong> {_fmt_dt(snapshot.created_at)}</p>
    <p><strong>Updated:</strong> {_fmt_dt(snapshot.updated_at)}</p>
    <p><strong>Total:</strong> {_fmt_money(snapshot.total_amount)} | <strong>Paid:</strong> {_fmt_money(snapshot.paid_amount)} | <strong>Remaining:</strong> {_fmt_money(snapshot.remaining_amount)}</p>
  </div>

  <h2>Work lines</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Type</th>
        <th>Qty</th>
        <th>Unit</th>
        <th>Total</th>
        <th>Comment</th>
      </tr>
    </thead>
    <tbody>
      {lines_rows}
    </tbody>
  </table>

  <h2>Payments</h2>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Amount</th>
        <th>Method</th>
        <th>Comment</th>
      </tr>
    </thead>
    <tbody>
      {payment_rows}
    </tbody>
  </table>
</body>
</html>
"""
    return html.encode("utf-8")


def _fit_text(text: str, *, limit: int = 110) -> list[str]:
    source = text.strip()
    if not source:
        return [""]
    lines: list[str] = []
    for raw in source.splitlines() or [""]:
        lines.extend(wrap(raw, width=limit) or [""])
    return lines


def render_work_order_pdf(snapshot: WorkOrderDocumentSnapshot) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("reportlab_required_for_pdf_generation") from exc

    font_name = "Helvetica"
    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for candidate in font_candidates:
        if candidate.exists():
            try:
                pdfmetrics.registerFont(TTFont("AutoServiceDocFont", str(candidate)))
                font_name = "AutoServiceDocFont"
                break
            except Exception:
                continue

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 14 * mm
    right = width - 14 * mm
    y = height - 16 * mm

    def ensure_space(lines: int = 1) -> None:
        nonlocal y
        if y - (lines * 6 * mm) > 18 * mm:
            return
        pdf.showPage()
        pdf.setFont(font_name, 10)
        y = height - 16 * mm

    def draw_text(text: str, size: int = 10, leading_mm: float = 5.2) -> None:
        nonlocal y
        ensure_space()
        pdf.setFont(font_name, size)
        for line in _fit_text(text, limit=120):
            ensure_space()
            pdf.drawString(left, y, line)
            y -= leading_mm * mm

    def draw_title(text: str) -> None:
        nonlocal y
        ensure_space()
        pdf.setFont(font_name, 16)
        pdf.drawString(left, y, text)
        y -= 7 * mm

    def draw_section(title: str) -> None:
        nonlocal y
        ensure_space()
        y -= 2 * mm
        pdf.setFont(font_name, 12)
        pdf.drawString(left, y, title)
        y -= 5 * mm
        pdf.setLineWidth(0.4)
        pdf.line(left, y, right, y)
        y -= 4 * mm

    draw_title("Work Order")
    draw_text(f"ID: {snapshot.work_order_id} | Status: {snapshot.status}", size=10)
    draw_text(f"Created: {_fmt_dt(snapshot.created_at)} | Updated: {_fmt_dt(snapshot.updated_at)}", size=9)

    draw_section("Client")
    draw_text(f"Name: {snapshot.client_name}")
    draw_text(f"Phone: {snapshot.client_phone}")
    draw_text(f"Email: {snapshot.client_email or '-'}")
    draw_text(f"Source: {snapshot.client_source or '-'}")
    draw_text(f"Comment: {snapshot.client_comment or '-'}")

    draw_section("Vehicle")
    draw_text(f"Plate: {snapshot.vehicle_plate_number or '-'}")
    draw_text(f"Model: {snapshot.vehicle_make_model or '-'}")
    draw_text(f"Year: {snapshot.vehicle_year if snapshot.vehicle_year is not None else '-'}")
    draw_text(f"VIN: {snapshot.vehicle_vin or '-'}")
    draw_text(f"Comment: {snapshot.vehicle_comment or '-'}")

    draw_section("Order")
    draw_text(f"Description: {snapshot.description}")
    draw_text(
        f"Total: {_fmt_money(snapshot.total_amount)} | Paid: {_fmt_money(snapshot.paid_amount)} | Remaining: {_fmt_money(snapshot.remaining_amount)}"
    )

    draw_section("Work lines")
    if snapshot.lines:
        for index, item in enumerate(snapshot.lines, start=1):
            draw_text(
                f"{index}. {item.name} ({item.line_type}) | qty {item.quantity} | unit {_fmt_money(item.unit_price)} | total {_fmt_money(item.line_total)}"
            )
            if item.comment:
                draw_text(f"   comment: {item.comment}", size=9)
    else:
        draw_text("No lines added.")

    draw_section("Payments")
    if snapshot.payments:
        for index, item in enumerate(snapshot.payments, start=1):
            draw_text(f"{index}. {_fmt_dt(item.paid_at)} | {_fmt_money(item.amount)} | {item.method}")
            if item.comment:
                draw_text(f"   comment: {item.comment}", size=9)
    else:
        draw_text("No payments.")

    pdf.save()
    return buffer.getvalue()


def _docx_p(text: str, *, bold: bool = False) -> str:
    safe = escape(text)
    run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (
        "<w:p><w:r>"
        f"{run_props}"
        f"<w:t xml:space='preserve'>{safe}</w:t>"
        "</w:r></w:p>"
    )


def render_work_order_docx(snapshot: WorkOrderDocumentSnapshot) -> bytes:
    body: list[str] = []
    body.append(_docx_p("Work Order", bold=True))
    body.append(_docx_p(f"ID: {snapshot.work_order_id}"))
    body.append(_docx_p(f"Status: {snapshot.status}"))
    body.append(_docx_p(f"Created: {_fmt_dt(snapshot.created_at)}"))
    body.append(_docx_p(f"Updated: {_fmt_dt(snapshot.updated_at)}"))

    body.append(_docx_p("Client", bold=True))
    body.append(_docx_p(f"Name: {snapshot.client_name}"))
    body.append(_docx_p(f"Phone: {snapshot.client_phone}"))
    body.append(_docx_p(f"Email: {snapshot.client_email or '-'}"))
    body.append(_docx_p(f"Source: {snapshot.client_source or '-'}"))
    body.append(_docx_p(f"Comment: {snapshot.client_comment or '-'}"))

    body.append(_docx_p("Vehicle", bold=True))
    body.append(_docx_p(f"Plate: {snapshot.vehicle_plate_number or '-'}"))
    body.append(_docx_p(f"Model: {snapshot.vehicle_make_model or '-'}"))
    body.append(_docx_p(f"Year: {snapshot.vehicle_year if snapshot.vehicle_year is not None else '-'}"))
    body.append(_docx_p(f"VIN: {snapshot.vehicle_vin or '-'}"))
    body.append(_docx_p(f"Comment: {snapshot.vehicle_comment or '-'}"))

    body.append(_docx_p("Order details", bold=True))
    body.append(_docx_p(f"Description: {snapshot.description}"))
    body.append(_docx_p(f"Total: {_fmt_money(snapshot.total_amount)}"))
    body.append(_docx_p(f"Paid: {_fmt_money(snapshot.paid_amount)}"))
    body.append(_docx_p(f"Remaining: {_fmt_money(snapshot.remaining_amount)}"))

    body.append(_docx_p("Work lines", bold=True))
    if snapshot.lines:
        for index, item in enumerate(snapshot.lines, start=1):
            body.append(
                _docx_p(
                    f"{index}. {item.name} ({item.line_type}) | qty {item.quantity} | unit {_fmt_money(item.unit_price)} | total {_fmt_money(item.line_total)}"
                )
            )
            if item.comment:
                body.append(_docx_p(f"   comment: {item.comment}"))
    else:
        body.append(_docx_p("No lines added."))

    body.append(_docx_p("Payments", bold=True))
    if snapshot.payments:
        for index, item in enumerate(snapshot.payments, start=1):
            body.append(_docx_p(f"{index}. {_fmt_dt(item.paid_at)} | {_fmt_money(item.amount)} | {item.method}"))
            if item.comment:
                body.append(_docx_p(f"   comment: {item.comment}"))
    else:
        body.append(_docx_p("No payments."))

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
