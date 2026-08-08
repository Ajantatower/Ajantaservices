"""The owner's own payment page.

Built around one job: get this person to pay. The amount and the QR are the page.
Everything else - the bank details, the quarterly bills - is folded away until it
is asked for, so the QR is reachable on a phone without scrolling.

Kept out of build.py so the CSS and JavaScript can be written normally; the page
is assembled with .format(), and every brace would otherwise need doubling.
"""

CSS = """
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0}
body{background:#EDF1F7;min-height:100vh;color:#0B1220;
  font-family:"Noto Sans Devanagari",-apple-system,system-ui,sans-serif;
  padding:12px 12px 20px;display:flex;justify-content:center}
.wrap{width:100%;max-width:420px}
.card{background:#fff;border-radius:16px;overflow:hidden;
  box-shadow:0 1px 2px rgba(11,18,32,.06),0 18px 36px -26px rgba(11,18,32,.5)}

.strip{padding:9px 16px;font-size:10px;letter-spacing:.13em;font-weight:800;text-transform:uppercase}
.pad{padding:15px 16px 16px}

h1{font-family:"Plus Jakarta Sans",sans-serif;font-size:19px;margin:0;line-height:1.2;
  letter-spacing:-.02em;word-break:break-word}
.u{color:#7C8AA0;font-size:11.5px;margin:4px 0 0;line-height:1.45}

.hero{margin-top:13px;padding:13px 15px;border-radius:13px}
.hero .k{font-size:10px;letter-spacing:.11em;font-weight:800;text-transform:uppercase;opacity:.85}
.hero .v{font-family:"Space Grotesk",monospace;font-weight:700;line-height:1;
  font-size:clamp(32px,10vw,42px);letter-spacing:-.025em;margin-top:5px}
.hero .s{margin-top:8px;font-size:11.5px;font-weight:600;opacity:.8}
.hero .bar{height:4px;border-radius:99px;background:rgba(11,18,32,.10);margin-top:9px;overflow:hidden}
.hero .bar i{display:block;height:100%;border-radius:99px;background:#0B6B52}

.qr{margin-top:13px;text-align:center}
.qr img{width:190px;max-width:64vw;height:auto;display:block;margin:0 auto;
  image-rendering:pixelated;border-radius:9px}
.qr p{margin:8px 0 0;font-size:11.5px;line-height:1.45;color:#7C8AA0}
.acts{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:11px}

.btn{display:flex;align-items:center;justify-content:center;gap:6px;text-decoration:none;
  font:inherit;font-size:12.5px;font-weight:700;padding:10px;border-radius:10px;
  border:1px solid #DCE2EB;background:#fff;color:#0B1220;cursor:pointer;white-space:nowrap}
.btn:active{transform:scale(.97);background:#F6F8FB}
.btn svg{width:14px;height:14px;flex:none;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round}

/* the folded sections have to LOOK pressable, or nobody finds what is inside */
details{margin-top:8px}
summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:9px;
  font-size:13px;font-weight:700;color:#26324A;padding:12px 13px;
  border:1px solid #DCE2EB;border-radius:11px;background:#F8FAFC}
summary::-webkit-details-marker{display:none}
summary:active{transform:scale(.99);background:#F1F5F9}
summary b{flex:1;font-weight:700}
summary em{font-style:normal;font-size:10.5px;font-weight:700;color:#9AA3B0;letter-spacing:.04em}
summary i{font-style:normal;font-size:15px;color:#8A93A2;font-weight:700;line-height:1;
  display:inline-block;transition:transform .18s}
details[open] summary{border-bottom-left-radius:0;border-bottom-right-radius:0;background:#fff}
details[open] summary i{transform:rotate(90deg)}
details[open] .fold{border:1px solid #DCE2EB;border-top:0;border-radius:0 0 11px 11px;
  padding:2px 13px 8px;background:#fff}

.row{display:flex;align-items:center;gap:9px;padding:8px 0;border-bottom:1px solid #F3F5F9}
.row:last-child{border-bottom:0}
.row .rk{font-size:10.5px;color:#9AA3B0;font-weight:700;min-width:62px}
.row .rv{flex:1;font-family:"Space Grotesk",monospace;font-size:12.5px;font-weight:700;word-break:break-all}
.mini{border:1px solid #DCE2EB;background:#fff;border-radius:8px;padding:5px 9px;
  font:inherit;font-size:10px;font-weight:800;letter-spacing:.06em;color:#7C8AA0;cursor:pointer}
.mini:active{transform:scale(.94)}
.mini.done{background:#E7F7F1;border-color:#9FDCC7;color:#0B6B52}

.bill{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #F3F5F9}
.bill:last-child{border-bottom:0}
.bill b{flex:1;font-size:12.5px;font-weight:700}
.ic{border:1px solid #DCE2EB;background:#fff;border-radius:8px;padding:6px 8px;cursor:pointer;
  display:grid;place-items:center;color:#5B6478;text-decoration:none}
.ic:active{transform:scale(.94)}
.ic svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round;display:block}

.full{display:block;text-align:center;margin-top:11px;font-size:12.5px;font-weight:700;
  color:#2E8BC0;text-decoration:none;padding:10px;border-radius:10px;background:#F4F9FD}
.legal{margin-top:11px;font-size:9.5px;line-height:1.55;color:#A6AEBB;text-align:center}
.legal b{color:#8A93A2}
.toast{position:fixed;left:50%;bottom:22px;transform:translate(-50%,12px);opacity:0;
  background:#0B1220;color:#fff;font-size:12px;font-weight:700;padding:9px 15px;border-radius:99px;
  pointer-events:none;transition:opacity .2s,transform .2s;z-index:9}
.toast.on{opacity:1;transform:translate(-50%,0)}
@media(prefers-reduced-motion:reduce){
  .btn:active,.mini:active,.ic:active{transform:none}
  summary i{transition:none}
}
"""

JS = """
(function(){
  var toast = document.getElementById("toast"), timer = null;
  function say(m){
    if (!toast) return;
    toast.textContent = m; toast.classList.add("on");
    clearTimeout(timer); timer = setTimeout(function(){ toast.classList.remove("on"); }, 1500);
  }
  function mark(btn){
    if (!btn) return;
    var was = btn.textContent;
    btn.textContent = "OK"; btn.classList.add("done");
    setTimeout(function(){ btn.textContent = was; btn.classList.remove("done"); }, 1300);
  }
  function legacy(text, ok){
    /* Safari blocks the clipboard API inside some in-app browsers, and that is
       exactly where these links get opened - from WhatsApp. */
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", "");
    ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, text.length);
    try { document.execCommand("copy"); ok(); } catch(e){ say("कॉपी नहीं हो सका"); }
    document.body.removeChild(ta);
  }
  function copy(text, btn){
    var ok = function(){ say("कॉपी हो गया"); mark(btn); };
    if (navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(ok, function(){ legacy(text, ok); });
    } else { legacy(text, ok); }
  }
  function shareLink(url, title, text){
    if (navigator.share) navigator.share({title:title, text:text, url:url}).catch(function(){});
    else copy((text ? text + "\\n" : "") + url);
  }
  function shareFile(url, name, title){
    /* Send the PDF itself where the phone allows it; fall back to the link, which
       always works. */
    if (!navigator.canShare){ shareLink(url, title, ""); return; }
    fetch(url).then(function(r){ return r.blob(); }).then(function(b){
      var f = new File([b], name, {type: b.type || "application/pdf"});
      if (navigator.canShare({files:[f]})) return navigator.share({files:[f], title:title});
      shareLink(url, title, "");
    }).catch(function(){ shareLink(url, title, ""); });
  }
  function saveImage(url, name, title){
    /* iPhone ignores the download attribute - Safari just opens the picture. The
       only route into the camera roll is the share sheet, which carries a Save
       Image item. Android takes the plain download, so try that second. */
    if (navigator.canShare){
      fetch(url).then(function(r){ return r.blob(); }).then(function(b){
        var f = new File([b], name, {type: b.type || "image/png"});
        if (navigator.canShare({files:[f]})) return navigator.share({files:[f], title:title});
        plainDownload(url, name);
      }).catch(function(){ plainDownload(url, name); });
    } else {
      plainDownload(url, name);
    }
  }
  function plainDownload(url, name){
    var a = document.createElement("a");
    a.href = url; a.download = name; a.rel = "noopener";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){ say("तस्वीर पर देर तक दबाकर सेव कीजिए"); }, 900);
  }
  document.addEventListener("click", function(ev){
    var t = ev.target && ev.target.closest ? ev.target : null;
    if (!t) return;
    var sv = t.closest("[data-savefile]");
    if (sv){
      ev.preventDefault();
      saveImage(sv.getAttribute("data-savefile"), sv.getAttribute("data-name") || "qr.png",
                sv.getAttribute("data-title") || document.title);
      return;
    }
    var c = t.closest("[data-copy]");
    if (c){ copy(c.getAttribute("data-copy"), c); return; }
    var f = t.closest("[data-sharefile]");
    if (f){
      ev.preventDefault();
      shareFile(f.getAttribute("data-sharefile"), f.getAttribute("data-name") || "bill.pdf",
                f.getAttribute("data-title") || document.title);
      return;
    }
    var s = t.closest("[data-share]");
    if (s){
      ev.preventDefault();
      shareLink(s.getAttribute("data-share"), s.getAttribute("data-title") || document.title,
                s.getAttribute("data-text") || "");
    }
  });
})();
"""

ICON_DOWN = ('<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4'
             'M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>')
ICON_SHARE = ('<svg viewBox="0 0 24 24"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7'
              'M12 15V3m0 0L8 7m4-4 4 4"/></svg>')

PAGE = """<!DOCTYPE html>
<html lang="hi"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="{wash}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ajanta Services Association">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{base}/o/{key}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="1200">
<meta property="og:url" content="{base}/o/{key}.html">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@700;800&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<div class="wrap"><div class="card">
  <div class="strip" style="background:{wash};color:{ink}">अजंता टावर · {label}</div>
  <div class="pad">
    <h1>{name}</h1>
    <p class="u">{units}</p>

    <div class="hero" style="background:{wash};color:{ink}">
      <div class="k">{duelabel}</div>
      <div class="v">{due}</div>
      <div class="s">बिल {billed} · जमा {paid}</div>
      <div class="bar"><i style="width:{pct}%"></i></div>
    </div>

{qr}
    <details>
      <summary><b>एसोसिएशन का खाता</b><em>UPI · खाता · IFSC</em><i>&#8250;</i></summary>
      <div class="fold">
      <div class="row"><span class="rk">UPI</span><span class="rv">{upi}</span>
        <button class="mini" type="button" data-copy="{upi}">COPY</button></div>
      <div class="row"><span class="rk">खाता सं.</span><span class="rv">{ac}</span>
        <button class="mini" type="button" data-copy="{ac}">COPY</button></div>
      <div class="row"><span class="rk">IFSC</span><span class="rv">{ifsc}</span>
        <button class="mini" type="button" data-copy="{ifsc}">COPY</button></div>
      <div class="row"><span class="rk">बैंक</span>
        <span class="rv" style="font-family:inherit;font-weight:600">{bank}</span></div>
      </div>
    </details>

{bills}
    <a class="full" href="{base}/">पूरा हिसाब देखिए &#8594;</a>
    <p class="legal">&#169; 2026 <b>Shucart Enterprises</b>. All rights reserved.
    Design and code proprietary.</p>
  </div>
</div></div>
<div class="toast" id="toast"></div>
<script>{js}</script>
</body></html>
"""

QR_BLOCK = """    <div class="qr">
      <img src="{base}/o/qr-{key}.png" alt="UPI QR" width="190" height="190">
      <p>किसी भी UPI ऐप से स्कैन कीजिए — <b>{due}</b> पहले से भरी हुई आएगी।</p>
      <div class="acts">
        <button class="btn" type="button" data-savefile="{base}/o/qrcard-{key}.png"
                data-name="ajanta-{key}-qr.png" data-title="{sharetitle}">{down}QR सेव</button>
        <button class="btn" type="button" data-share="{base}/o/{key}.html"
                data-title="{sharetitle}" data-text="{sharetext}">{share}भेजिए</button>
      </div>
    </div>
"""

BILLS_BLOCK = """    <details>
      <summary><b>तिमाही बिल</b><em>{count} PDF</em><i>&#8250;</i></summary>
      <div class="fold">
{rows}      </div>
    </details>
"""

BILL_ROW = """      <div class="bill"><b>{label}</b>
        <a class="ic" href="{url}" download target="_blank" rel="noopener" title="खोलिए">{down}</a>
        <button class="ic" type="button" data-sharefile="{url}" data-name="{fname}"
                data-title="{title}" title="भेजिए">{share}</button></div>
"""
