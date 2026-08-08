"""
Quarterly maintenance invoices, in the association's existing format.

The layout follows invoice no. 81 exactly - same blocks, same wording, same
declaration - with one addition he asked for: under MAINTENANCE CHARGES every
shop is listed with its own size, and the total area follows.
"""

import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

W, H = A4

SELLER = {
    "name": "AJANTA SERVICES ASSOCIATION",
    "addr": ["UGF-6, AJANTA TOWER, BARGAWAN, HIND NAGAR,", "KANPUR ROAD, LUCKNOW"],
}
BANK = [
    ("Bank Name", "Federal Bank"),
    ("A/c No.", "26100200001004"),
    ("Branch", "Alambagh, Lucknow"),
    ("IFS Code", "FDRL0002610"),
]
DECLARATION = [
    "- Payment shall be accepted only through banking channels.",
    "- The payment must be made within 7 (seven) days from the date of invoice.",
]

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
        "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_hundred(n):
    if n < 20:
        return ONES[n]
    return (TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else "")).strip()


def words(n):
    """Indian numbering, the way the existing invoice writes it."""
    n = int(n)
    if n == 0:
        return "Zero"
    parts = []
    for div, label in ((10000000, "Crore"), (100000, "Lakh"), (1000, "Thousand"), (100, "Hundred")):
        if n >= div:
            q, n = divmod(n, div)
            parts.append(_below_hundred(q) + " " + label)
    if n:
        parts.append(_below_hundred(n))
    return " ".join(parts)


def rupees(n):
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        g = []
        while len(head) > 2:
            g.insert(0, head[-2:]); head = head[:-2]
        if head:
            g.insert(0, head)
        s = ",".join(g + [tail])
    return s + ".00"


def parse_units(u):
    """['LGF 28, 29 (1,020 sq ft)', ...] -> [(floor, [shop, ...], area), ...]"""
    out = []
    for seg in str(u or "").split("\u00b7"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.search(r"\(([\d,]+)\s*sq ft\)", seg)
        if not m:
            continue
        area = int(m.group(1).replace(",", ""))
        head = seg[:m.start()].strip()
        fm = re.match(r"(LGF|UGF|FF|SF)\s*(.*)", head)
        if fm:
            out.append((fm.group(1), fm.group(2).strip(" ,"), area))
        else:
            out.append(("", head, area))
    return out


def build(path, *, inv_no, inv_date, buyer, buyer_addr, units, rate, months, year,
          quarter_label):
    c = canvas.Canvas(path, pagesize=A4)
    x0, x1 = 18 * mm, W - 18 * mm
    y = H - 16 * mm

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, y, "INVOICE")
    y -= 9 * mm

    box_top = y
    c.rect(x0, 0, x1 - x0, y, stroke=0, fill=0)      # nothing, keeps coordinates honest

    # ---- seller and the invoice number panel
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0 + 3 * mm, y - 6 * mm, SELLER["name"])
    c.setFont("Helvetica", 8.5)
    for i, line in enumerate(SELLER["addr"]):
        c.drawString(x0 + 3 * mm, y - 11 * mm - i * 4 * mm, line)

    mid = x0 + (x1 - x0) * 0.62
    c.setFont("Helvetica", 8)
    c.drawString(mid + 3 * mm, y - 5 * mm, "Invoice No.")
    c.drawString(mid + 33 * mm, y - 5 * mm, "Dated")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(mid + 3 * mm, y - 10 * mm, str(inv_no))
    c.drawString(mid + 33 * mm, y - 10 * mm, inv_date)
    c.line(mid, y, mid, y - 22 * mm)
    c.line(mid, y - 12 * mm, x1, y - 12 * mm)
    c.rect(x0, y - 22 * mm, x1 - x0, 22 * mm)
    y -= 22 * mm

    # ---- buyer
    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 5 * mm, "Buyer (Bill to)")
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(x0 + 3 * mm, y - 10.5 * mm, buyer.upper())
    c.setFont("Helvetica", 8.5)
    c.drawString(x0 + 3 * mm, y - 15 * mm, buyer_addr)
    c.rect(x0, y - 19 * mm, x1 - x0, 19 * mm)
    y -= 19 * mm

    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 4.5 * mm, "Mode/Terms of Payment")
    c.drawString(mid + 3 * mm, y - 4.5 * mm, "Other References")
    c.line(mid, y, mid, y - 8 * mm)
    c.rect(x0, y - 8 * mm, x1 - x0, 8 * mm)
    y -= 8 * mm

    # ---- the charge table
    cols = [x0, x0 + 13 * mm, x1 - 74 * mm, x1 - 44 * mm, x1 - 24 * mm, x1]
    hdr = y
    c.setFont("Helvetica-Bold", 8.5)
    for i, label in enumerate(["Sl No.", "Particulars", "Quantity", "Rate", "Amount"]):
        if i == 0:
            c.drawCentredString((cols[0] + cols[1]) / 2, y - 5.5 * mm, label)
        elif i == 1:
            c.drawString(cols[1] + 2 * mm, y - 5.5 * mm, label)
        else:
            c.drawRightString(cols[i + 1] - 2 * mm, y - 5.5 * mm, label)
    y -= 8 * mm
    c.line(x0, y, x1, y)

    total_area = sum(a for _, _, a in units)
    amount = total_area * rate * 3

    body_top = y
    yy = y - 6 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString((cols[0] + cols[1]) / 2, yy, "1")
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(cols[1] + 2 * mm, yy, "MAINTENANCE CHARGES")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(cols[5] - 2 * mm, yy, rupees(amount))

    yy -= 5.5 * mm
    c.setFont("Helvetica", 8.5)
    for floor, shops, area in units:
        label = ("%s %s" % (floor, shops)).strip() or "Unit"
        c.drawString(cols[1] + 6 * mm, yy, label)
        c.drawRightString(cols[3] - 2 * mm, yy, "{:,} SQ FT".format(area))
        yy -= 4.6 * mm

    yy -= 1 * mm
    c.line(cols[1] + 6 * mm, yy + 3 * mm, cols[3] - 2 * mm, yy + 3 * mm)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(cols[1] + 6 * mm, yy, "TOTAL AREA")
    c.drawRightString(cols[3] - 2 * mm, yy, "{:,} SQ FT".format(total_area))
    yy -= 5.5 * mm
    c.setFont("Helvetica", 8.5)
    c.drawString(cols[1] + 6 * mm, yy, "@ %d PER SQ FT FOR THE QTR (%s)" % (rate, quarter_label))
    yy -= 8 * mm

    bottom = min(yy, body_top - 40 * mm)
    c.rect(x0, bottom, x1 - x0, hdr - bottom)
    for cx in cols[1:5]:
        c.line(cx, hdr, cx, bottom)
    c.line(x0, hdr - 8 * mm, x1, hdr - 8 * mm)

    y = bottom
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(cols[1] + 2 * mm, y - 5.5 * mm, "Total")
    c.drawRightString(cols[5] - 2 * mm, y - 5.5 * mm, rupees(amount))
    c.rect(x0, y - 8 * mm, x1 - x0, 8 * mm)
    for cx in cols[1:5]:
        c.line(cx, y, cx, y - 8 * mm)
    y -= 8 * mm

    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 5 * mm, "Amount Chargeable (in words)")
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x0 + 3 * mm, y - 10.5 * mm, "INR " + words(amount) + " Only")
    c.setFont("Helvetica", 7.5)
    c.drawRightString(x1 - 3 * mm, y - 10.5 * mm, "E. & O.E")
    c.rect(x0, y - 14 * mm, x1 - x0, 14 * mm)
    y -= 14 * mm

    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 5 * mm, "Declaration")
    c.setFont("Helvetica", 8)
    for i, line in enumerate(DECLARATION):
        c.drawString(x0 + 3 * mm, y - 10 * mm - i * 4.2 * mm, line)

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(mid + 3 * mm, y - 5 * mm, "Company's Bank Details")
    c.setFont("Helvetica", 8)
    # the branch and IFSC line is longer than the panel, so it wraps inside it
    # instead of running off the page edge
    avail = (x1 - 3 * mm) - (mid + 3 * mm)
    yy2 = y - 10 * mm
    for k, v in BANK:
        text = "%s : %s" % (k, v)
        if c.stringWidth(text, "Helvetica", 8) <= avail:
            c.drawString(mid + 3 * mm, yy2, text)
            yy2 -= 4.2 * mm
            continue
        head = k + " :"
        c.drawString(mid + 3 * mm, yy2, head)
        yy2 -= 4.2 * mm
        line = ""
        for word in v.split():
            trial = (line + " " + word).strip()
            if c.stringWidth(trial, "Helvetica", 8) <= avail - 3 * mm:
                line = trial
            else:
                c.drawString(mid + 6 * mm, yy2, line)
                yy2 -= 4.2 * mm
                line = word
        if line:
            c.drawString(mid + 6 * mm, yy2, line)
            yy2 -= 4.2 * mm
    c.line(mid, y, mid, y - 36 * mm)
    c.rect(x0, y - 36 * mm, x1 - x0, 36 * mm)
    y -= 36 * mm

    c.setFont("Helvetica", 8)
    c.drawString(x0 + 3 * mm, y - 6 * mm, "Customer's Seal and Signature")
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(x1 - 3 * mm, y - 6 * mm, "for " + SELLER["name"])
    c.setFont("Helvetica", 8)
    c.drawRightString(x1 - 3 * mm, y - 22 * mm, "Authorised Signatory")
    c.rect(x0, y - 26 * mm, x1 - x0, 26 * mm)
    y -= 26 * mm

    c.setFont("Helvetica-Oblique", 7.5)
    c.drawCentredString(W / 2, y - 6 * mm, "This is a computer generated invoice copy.")
    c.save()
    return amount, total_area
