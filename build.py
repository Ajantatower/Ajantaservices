#!/usr/bin/env python3
"""
Builds the whole Ajanta Tower site from data/slim.json.

    python3 build.py                     -> builds into _site/
    python3 build.py https://example.com -> same, with that base URL

The base URL only matters for the WhatsApp / social preview cards, which have
to carry an absolute address because a crawler cannot run JavaScript. On GitHub
the workflow passes it in automatically, so nothing here needs editing by hand.
"""

import json, os, re, shutil, sys, html as H
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, "_site")
BASE = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")

PAY = dict(upi="ajanta1004@fbl", bank="Federal Bank", ac="26100200001004",
           ifsc="FDRL0002610", who="Chandan Dubey", phone="7007202574")

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ---------------------------------------------------------------- helpers
def rupees(n):
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "\u20B9" + s


def band_of(o):
    if o["s"] in ("full", "near"):
        return "full"
    if o["s"] == "part":
        return "part"
    if o["p"] <= 0 or (o["dm"] > 0 and o["b"] / o["dm"] > 0.7):
        return "zero"
    return "arrear"


IMG_TONE = {
    "full":   ("#0B6B52", "#E7F7F1", "CLEARED IN FULL"),
    "part":   ("#8A5A06", "#FFF4E0", "PART PAID"),
    "arrear": ("#8A4212", "#FDEDE0", "A QUARTER OR MORE BEHIND"),
    "zero":   ("#9E3F22", "#FCE9E3", "NOTHING PAID YET"),
}
PAGE_TONE = {
    "full":   ("#0B6B52", "#E7F7F1", "\u092a\u0942\u0930\u093e \u092d\u0941\u0917\u0924\u093e\u0928 \u0939\u094b \u091a\u0941\u0915\u093e", "#12A08A"),
    "part":   ("#8A5A06", "#FFF4E0", "\u0906\u0902\u0936\u093f\u0915 \u092d\u0941\u0917\u0924\u093e\u0928", "#F5A524"),
    "arrear": ("#8A4212", "#FDEDE0", "\u090f\u0915 \u0924\u093f\u092e\u093e\u0939\u0940 \u092f\u093e \u0909\u0938\u0938\u0947 \u0905\u0927\u093f\u0915 \u092c\u0915\u093e\u092f\u093e", "#E0662B"),
    "zero":   ("#9E3F22", "#FCE9E3", "\u0905\u092c \u0924\u0915 \u0915\u094b\u0908 \u092d\u0941\u0917\u0924\u093e\u0928 \u0928\u0939\u0940\u0902", "#D24A2C"),
}


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- preview images
def owner_image(key, o, path):
    ink, wash, label = IMG_TONE[band_of(o)]
    im = Image.new("RGB", (1200, 630), "#FCFBF8")
    d  = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 12], fill=ink)
    d.rectangle([0, 12, 1200, 150], fill=wash)
    d.text((70, 58), "AJANTA TOWER  \u00B7  " + label,
           font=ImageFont.truetype(FONT_B, 21), fill=ink)

    size = 50
    while size > 26:
        f_name = ImageFont.truetype(FONT_B, size)
        if len(wrap(d, o["n"], f_name, 1060)) <= 2:
            break
        size -= 3
    y = 186
    for line in wrap(d, o["n"], f_name, 1060)[:2]:
        d.text((70, y), line, font=f_name, fill="#14171C")
        y += int(size * 1.16)

    d.text((70, y + 8), (o["u"] or "")[:74],
           font=ImageFont.truetype(FONT_R, 24), fill="#5B7488")

    f_lab = ImageFont.truetype(FONT_B, 19)
    f_num = ImageFont.truetype(FONT_B, 50)
    f_big = ImageFont.truetype(FONT_B, 74)
    yb = 392
    d.line([70, yb - 26, 1130, yb - 26], fill="#DDE7EF", width=2)
    d.text((70,  yb), "BILL", font=f_lab, fill="#8A9099")
    d.text((70,  yb + 30), rupees(o["dm"]), font=f_num, fill="#14171C")
    d.text((360, yb), "PAID", font=f_lab, fill="#8A9099")
    d.text((360, yb + 30), rupees(o["p"]), font=f_num, fill="#0B6B52")
    if o["b"] > 0:
        d.text((700, yb), "STILL TO PAY", font=f_lab, fill=ink)
        d.text((700, yb + 22), rupees(o["b"]), font=f_big, fill=ink)
    else:
        d.text((700, yb), "PENDING", font=f_lab, fill="#0B6B52")
        d.text((700, yb + 22), "NIL", font=f_big, fill="#0B6B52")

    d.line([70, 556, 1130, 556], fill="#EDF2F7", width=1)
    d.text((70, 574), (BASE or "Ajanta Services Association").replace("https://", ""),
           font=ImageFont.truetype(FONT_B, 23), fill="#8A9099")
    im.save(path, optimize=True)


def front_image(totals, own, path):
    demand = sum(o["dm"] for o in own.values())
    open_b = sum(o["b"] for o in own.values() if o["b"] > 0)
    behind = sum(1 for o in own.values() if o["b"] > 0)
    payers = len({o["n"] for o in own.values() if o["p"] > 0})

    im = Image.new("RGB", (1200, 630), "#FFFFFF")
    d  = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1200, 10], fill="#12293F")
    d.text((70, 62), "AJANTA TOWER  \u00B7  OPEN ACCOUNTS",
           font=ImageFont.truetype(FONT_B, 22), fill="#8A9099")
    f_head = ImageFont.truetype(FONT_B, 62)
    d.text((70, 108), "%d owners are keeping" % payers, font=f_head, fill="#14171C")
    d.text((70, 182), "this building open.",           font=f_head, fill="#14171C")
    d.text((70, 272), "Every rupee collected and every rupee spent, itemised and dated.",
           font=ImageFont.truetype(FONT_R, 27), fill="#4A5058")

    y, x = 356, 70
    f_lab = ImageFont.truetype(FONT_B, 20)
    f_num = ImageFont.truetype(FONT_B, 54)
    d.line([70, y - 22, 1130, y - 22], fill="#14171C", width=2)
    for label, value, colour in [
        ("BILLED",                       rupees(demand),         "#14171C"),
        ("COME IN",                      rupees(totals["paid"]), "#0B6B52"),
        ("STILL OUT \u00B7 %d OWNERS" % behind, rupees(open_b),  "#B92718")]:
        d.text((x, y + 6),  label, font=f_lab, fill="#8A9099")
        d.text((x, y + 40), value, font=f_num, fill=colour)
        x += 372
    d.line([70, y + 128, 1130, y + 128], fill="#E3E5E8", width=1)
    d.text((70, y + 152), (BASE or "Ajanta Services Association").replace("https://", ""),
           font=ImageFont.truetype(FONT_B, 26), fill="#8A9099")
    im.save(path, optimize=True)


# ---------------------------------------------------------------- owner pages
OWNER_PAGE = """<!DOCTYPE html>
<html lang="hi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ajanta Services Association">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{base}/o/{key}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{base}/o/{key}.html">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700&family=Plus+Jakarta+Sans:wght@600;700&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:linear-gradient(180deg,#FCFBF8,#EFF3FA);min-height:100vh;
  font-family:"Noto Sans Devanagari",system-ui,sans-serif;color:#0B1220;
  padding:26px 18px 40px;display:flex;justify-content:center}}
.card{{width:100%;max-width:520px;background:#fff;border:1px solid rgba(11,18,32,.09);border-radius:18px;
  overflow:hidden;box-shadow:0 1px 2px rgba(11,18,32,.05),0 20px 40px -28px rgba(11,18,32,.55)}}
.top{{background:{wash};padding:15px 20px;border-bottom:1px solid rgba(0,0,0,.05)}}
.top b{{font-size:11px;letter-spacing:.13em;color:{ink};font-weight:700}}
.pad{{padding:20px}}
h1{{font-family:"Plus Jakarta Sans",sans-serif;font-size:clamp(23px,6.2vw,30px);margin:0;line-height:1.16;letter-spacing:-.02em}}
.u{{color:#5B7488;font-size:13px;margin:8px 0 0;line-height:1.5}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px;
  border-top:1px solid #EDF2F7;padding-top:16px}}
.k{{font-size:10.5px;letter-spacing:.1em;color:#8A9099;font-weight:700;text-transform:uppercase}}
.v{{font-family:"Space Grotesk",monospace;font-weight:700;font-size:20px;margin-top:4px}}
.due{{grid-column:1/-1;background:{wash};border-radius:14px;padding:14px 16px;margin-top:2px}}
.due .v{{font-size:clamp(30px,9vw,40px);color:{ink}}}
.btn{{display:block;text-align:center;text-decoration:none;font-weight:700;font-size:16px;
  padding:15px;border-radius:13px;background:{accent};color:#fff;margin-top:16px}}
.apps{{display:grid;gap:8px;margin-top:10px}}
.apps a{{display:block;text-align:center;text-decoration:none;font-weight:700;font-size:14px;
  padding:12px;border-radius:11px;border:1px solid #D5DAE3;color:#0B1220}}
.det{{margin-top:16px;border-top:1px solid #EDF2F7;padding-top:14px;font-size:13px;line-height:1.75;color:#3A4560}}
.det b{{color:#0B1220;font-family:"Space Grotesk",monospace}}
.full{{display:block;text-align:center;margin-top:18px;font-size:13.5px;font-weight:700;color:#2E8BC0;text-decoration:none}}
</style></head>
<body><div class="card">
<div class="top"><b>\u0905\u091c\u0902\u0924\u093e \u091f\u093e\u0935\u0930 \u00B7 {label}</b></div>
<div class="pad">
<h1>{name}</h1>
<p class="u">{units}</p>
<div class="grid">
  <div><div class="k">\u092c\u093f\u0932 \u0930\u093e\u0936\u093f</div><div class="v">{billed}</div></div>
  <div><div class="k">\u091c\u092e\u093e</div><div class="v" style="color:#0B6B52">{paid}</div></div>
  <div class="due"><div class="k" style="color:{ink}">{duelabel}</div><div class="v">{due}</div></div>
</div>
{action}
<p class="det">\u092f\u0939 \u092a\u0948\u0938\u093e \u0906\u092a\u0915\u0940 \u0905\u092a\u0928\u0940 \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0947 \u0930\u0916\u0930\u0916\u093e\u0935 \u0915\u093e \u0916\u0930\u094d\u091a \u0939\u0948 \u2014 \u0938\u092b\u093e\u0908, \u092c\u093f\u091c\u0932\u0940, \u092a\u093e\u0928\u0940 \u0914\u0930 \u092e\u0930\u092e\u094d\u092e\u0924\u0964<br>
UPI: <b>{upi}</b><br>{bank}, A/c <b>{ac}</b>, IFSC <b>{ifsc}</b><br>
<em>\u0930\u093f\u092e\u093e\u0930\u094d\u0915 \u092e\u0947\u0902 \u0905\u092a\u0928\u093e \u0926\u0941\u0915\u093e\u0928 \u0928\u0902\u092c\u0930 \u0905\u0935\u0936\u094d\u092f \u0932\u093f\u0916\u093f\u090f</em></p>
<a class="full" href="{base}/">\u092a\u0942\u0930\u093e \u0939\u093f\u0938\u093e\u092c \u0926\u0947\u0916\u093f\u090f \u2014 \u0939\u0930 \u0930\u0941\u092a\u092f\u093e, \u0928\u093e\u092e \u0914\u0930 \u0924\u093e\u0930\u0940\u0916 \u0915\u0947 \u0938\u093e\u0925 \u2192</a>
</div></div></body></html>
"""


def owner_page(key, o):
    ink, wash, label, accent = PAGE_TONE[band_of(o)]

    def upi(scheme):
        return scheme + ("pa=" + quote(PAY["upi"]) +
                         "&pn=" + quote("Ajanta Services Association") +
                         "&cu=INR&am=" + str(int(o["b"])) +
                         "&tn=" + quote("Maintenance " + o["n"]))

    if o["b"] > 0:
        title = "%s \u2014 %s \u092c\u093e\u0915\u0940 \u00B7 \u0905\u091c\u0902\u0924\u093e \u091f\u093e\u0935\u0930" % (o["n"], rupees(o["b"]))
        desc  = ("\u092c\u093f\u0932 %s \u00B7 \u091c\u092e\u093e %s \u00B7 \u092c\u0915\u093e\u092f\u093e %s\u0964 "
                 "\u092f\u0939 \u092a\u0948\u0938\u093e \u0906\u092a\u0915\u0940 \u0905\u092a\u0928\u0940 \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0947 \u0930\u0916\u0930\u0916\u093e\u0935 \u0915\u093e \u0916\u0930\u094d\u091a \u0939\u0948\u0964"
                 % (rupees(o["dm"]), rupees(o["p"]), rupees(o["b"])))
        duelabel, due = "\u0905\u092d\u0940 \u0926\u0947\u0928\u093e \u0939\u0948", rupees(o["b"])
        action = ('<a class="btn" href="%s">%s \u0915\u093e \u092d\u0941\u0917\u0924\u093e\u0928 \u0915\u0930\u0947\u0902</a>'
                  '<div class="apps">'
                  '<a href="%s">Google Pay</a>'
                  '<a href="%s">PhonePe</a>'
                  '<a href="%s">Paytm</a></div>'
                  % (upi("upi://pay?"), rupees(o["b"]),
                     upi("tez://upi/pay?"), upi("phonepe://pay?"), upi("paytmmp://pay?")))
    else:
        title = "%s \u2014 \u092a\u0942\u0930\u093e \u092d\u0941\u0917\u0924\u093e\u0928 \u00B7 \u0905\u091c\u0902\u0924\u093e \u091f\u093e\u0935\u0930" % o["n"]
        desc  = ("\u092c\u093f\u0932 %s \u00B7 \u091c\u092e\u093e %s \u00B7 \u0915\u094b\u0908 \u092c\u0915\u093e\u092f\u093e \u0928\u0939\u0940\u0902\u0964"
                 % (rupees(o["dm"]), rupees(o["p"])))
        duelabel, due, action = "\u092c\u0915\u093e\u092f\u093e", "\u0936\u0942\u0928\u094d\u092f", ""

    return OWNER_PAGE.format(
        title=H.escape(title), desc=H.escape(desc), base=BASE, key=key,
        wash=wash, ink=ink, accent=accent, label=H.escape(label),
        name=H.escape(o["n"]), units=H.escape(o["u"] or ""),
        billed=rupees(o["dm"]), paid=rupees(o["p"]),
        duelabel=duelabel, due=due, action=action,
        upi=PAY["upi"], bank=PAY["bank"], ac=PAY["ac"], ifsc=PAY["ifsc"])


# ---------------------------------------------------------------- main
def main():
    data = json.load(open(os.path.join(ROOT, "data", "slim.json"), encoding="utf-8"))
    own  = data["own"]

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "o"))

    # the front page: one template, the register poured into it
    tpl = open(os.path.join(ROOT, "src", "template.html"), encoding="utf-8").read()
    page = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    if BASE:
        page = re.sub(r'(property="og:image" content=")[^"]*"',
                      lambda m: m.group(1) + BASE + '/preview.png"', page)
        page = re.sub(r'(property="og:url" content=")[^"]*"',
                      lambda m: m.group(1) + BASE + '/"', page)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)

    css = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    assert css.count("{") == css.count("}"), "stylesheet braces do not balance"

    for name in ("story.html", "tower.html", "film.html"):
        src = os.path.join(ROOT, "src", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, name))

    front_image(data["totals"], own, os.path.join(OUT, "preview.png"))

    for key, o in own.items():
        open(os.path.join(OUT, "o", "%s.html" % key), "w", encoding="utf-8").write(owner_page(key, o))
        owner_image(key, o, os.path.join(OUT, "o", "%s.png" % key))

    # a ready message per owner, so nothing has to be typed
    lines = ["READY-TO-SEND WHATSAPP MESSAGES", "Har owner ka apna link.", "", "=" * 60, ""]
    for key, o in sorted(own.items(), key=lambda kv: -kv[1]["b"]):
        if o["b"] <= 0:
            continue
        lines += ["\u0928\u092e\u0938\u094d\u0924\u0947 %s \u091c\u0940," % o["n"],
                  "\u0905\u091c\u0902\u0924\u093e \u091f\u093e\u0935\u0930 \u0915\u093e \u0906\u092a\u0915\u093e \u0930\u0916\u0930\u0916\u093e\u0935 \u0936\u0941\u0932\u094d\u0915 \u2014 \u092a\u0942\u0930\u093e \u0935\u093f\u0935\u0930\u0923 \u0914\u0930 \u092d\u0941\u0917\u0924\u093e\u0928 \u0915\u093e \u092c\u091f\u0928 \u092f\u0939\u093e\u0901 \u0939\u0948:",
                  "%s/o/%s.html" % (BASE, key), "", "=" * 60, ""]
    open(os.path.join(OUT, "whatsapp-messages.txt"), "w", encoding="utf-8").write("\n".join(lines))

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(OUT) for f in fs)
    print("built %d owner pages into _site/  (%.1f MB)  base=%s"
          % (len(own), total / 1048576, BASE or "(none)"))


if __name__ == "__main__":
    main()
