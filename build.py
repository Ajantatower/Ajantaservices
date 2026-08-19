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
try:
    import qr as qrlib
    import invoice as inv
    import ownerpage
    from shoparea import AREA as SHOP_AREA, CARPET
except ModuleNotFoundError as e:
    raise SystemExit(
        "MISSING MODULE: %s\n"
        "build.py needs qr.py, invoice.py, ownerpage.py and shoparea.py beside it in the\n"
        "repo root, "
        "and the workflow must install pillow and reportlab." % e.name)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, "_site")
BASE = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
DATESTAMP = __import__("datetime").date.today().strftime("%y%m%d")

# Quarters that have been billed, newest last.
#   key, label printed on the invoice, invoice date, month and year for the number
QUARTERS = [
    ("2026Q1", "JANUARY TO MARCH 2026", "15-Feb-26", "0226"),
    ("2026Q2", "APRIL TO JUNE 2026",    "15-May-26", "0526"),
    ("2026Q3", "JULY TO SEPTEMBER 2026", "15-Aug-26", "0826"),
]
QMY = {q[0]: q[3] for q in QUARTERS}
SERIALS = {}          # filled in main(): quarter -> {party key: 1, 2, 3, ...}

PAY = dict(upi="ajanta1004@fbl", bank="Federal Bank", ac="26100200001004",
           ifsc="FDRL0002610", who="Chandan Dubey", phone="7007202574")

APP_LOGO = {
    "pt": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK4AAABgCAYAAACE7kkqAAAWHklEQVR42u19a5RcR3Xut/ep06e7p6dHGo00I1l+46ccbMcY+/qadwzYDiEYG8IrfgQn4TqXhFwCF9aNiROWsy4QuCEhgAMmsDAJcUJMzCsm4GAIdsDyCxnbsmVZQpJnRiONZrqnH+dU7X1/nJ6XZnq6ezQzGkN9a/XSo/vsOlX11a6vdu1TB/Dw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PB47oMo/fNFr92Ev/z2X+Kmf3g3ir006zsPj1XEWICD9K83/N9fww9VcXdN8ZAq3vD75wEAAvNz3QLsSfAcRBAA4oBrb3w5rnvPVzE+GqMyXsaEWHSv7f1FaAJP3OdcjxnAWeDCS/tx/U3fwfBoDWADCgwCNhBrPXE9VllvBYBYYN1AgP99y7+jWhEQGTDzXOHrieuxKuSBSeVBmAFuvO2jWL/pLMQ1C/45F7NNYKbE/pJBl24BsurK1OW3QzR9PVH6EZfKg1yBcNNtH8ALX/5OHDoYIwgz81xPU9dN2VJAm5TJ3PpWVea5T55RxuRvNb1ApM1mamJDdf4yZxOXlrDjD2v8yYp0TB5d/D0RgUDQjsrupMx22muRdpgbna5zzVzw6vV4x59/Cqeec0VT0gKAsxaqgE1m3wvx/GRoh2RE08TnYJqc2sYMcfiAoUZERFx6P7oAqZkA55oRV8EmS0SGmw/L9npfVVRcTWYRdmalO/CegcmxtnuhKlSdqtj07zNbo63yG2WGhaDpj4lIkopTbd3RLe3YmlOx85Mo303oKjKiHKNvUxfOvPAMXHT5tTj74ushAowtQFpVINfdg95+RhASxCo4IIwOu2kiHzZojj8tAgXzNxIxIak57NmRgBv0kAaRNmwOcOKWtTjm5GOQLRSQ1GoY3jOIp7ftx8+2x3B2hi53swfm5HebnxfixDP7MHDCJoRRhOrEBAZ37sPOn45icJeFQ9NBRz0bz79oTf8vf1pJuo9YJKhU1dWfSaqj36uM7b5jYvSp7WKr0onXM9k1Yf9Jr/40h13nk0IU2o4OF1U7Li4ZtPWx++PK8D2V8Z89Ek8MTSzsJRtlRkWz/uTLbgmjnl+BigXN0f4CEGtS3za8899+oz4xWJ47IAhBmOMNJ136kUy+7wpVkbl2SABlFXlmZOe3X18d330gjclS2qGveMNx+L0PfQUU9SGbXY+unjxCAhIFymMCgiyoaYmAeu0QbHwAYAMVQRAwSsOP4E+v/g088WBlioAmBN5/6x/gFVf+BWLH867pVIEM1fDlv3oDPvHeOwGkmx2vue63seXCt2PNhmPAjZWSpq2EcqmGnQ9/Cd+67WP4xue3oV6djjmLS8t91VtOwaVv+32cdt7VyPcUEDS6Qhqf0sgwHv3RZ/G1z/0N7v6nPXMGAAA64bwbHFHACjlirUuN0UEUgIgQ10uPjw89cO3Ys/ff15beUUHvsRf/Wu/mi79q4xKIOlg7NuTJZNkiFvWJwb899OzWP6mMPrVvXgI3ylyz6YIX9R3/snuSeBxEQZNR6RCE3RgbevAdIzvv+tQs4jbsFDc8/8wNJ1/2qI1L6f/Na0cQhHmUDzz5oaEn73hvaqfh9T/7o9ux5fwrMV5Ob9VZCxELJgabTNu6caZuTWJBfw/j9s/9Lm6+7tMwGcDGwCln53HrAxOoVQBxAppH7KqziAoG40Pb8b8uOwfXf/B9ePFr/hgOQGUCcLGF6PTUwWTAxiCbB6IAePInd+Jjf3ANtn73IADgrIuK+MOP34It570RsQDVCiDJtA0Cg4gRZAxyXekK7P67P46PvvO9eHpbbSZ5jajUGJpdCq2rUECtqJAoFIGJTu87/qX35gqbPzj89DdvFFfXluUQR+LqVtTF6X217+5TXpAoRIg5k+3aeP3Aqa+9vjT8yO+M7Lr7lnR6nls+ERlxdauqMUGy8/NNYnV1A+LocP05ZZHYqMRWxVliZJrakdiAKTdbqhDgXIxqbOESAbMBB6bjqIFYgZuleWuYkAyCMJwtEjOMesVCHM9L2sm5Pa4KYHrw0buexLr+YzA6Gjf6KSUpw8zph0pJUHIWx57+Gnz83/bj5t85C/VKFTd+/gnAZDByoIaAGRTMb0OsoDxqIQqc+7J34pPfvwp/8pZzce83hibJa0h1gRtfjM8lBgMEAtRJEpdrXb3P+z/9fHnX4PY7/lBby1YHYkMK26HL5ckAHyFozEx1q1Ztsf+cTwdh7oShJ7/+/iYaVdIydT6Z0KgZceM3srBYZpNKggXsgA0Bbt5pIwgMiOyi+4SYZ02cQoyADeD0MIIpKDCgBSMc6T3kCv0gAsZGYwQtPD8RgwIGBwbVskUQGvzRp34KFSBOgGQiRpjJtq4DZ8AAxg7UEOU34s//6Wm867LNePA/RsG83HFcYqYgnyTlcn7tye9as+mCVwLaKkbOS1i8IQ6ySVwqd/We9r41x1x4WZPy29ZI2tFgWnA9ucIx9CMoTgWwibQk7ZwijYFzglpFUK8JrO3chslkEddigPP4wBd/gN4Bhq7QBgRTkHdxJS4O/PLtYdQTptpw5TZ4JsvvGTj39kyuN1rp8n8uwIucAZh51mdxmy8ZTJRr2HTMmfitD1wNlRUb9azqxJhssdB35ksm4+Qr6m5UEARRvrvvrMumF3OLEkOe8UcDJsxgrGRxyZv/H044I1qx6YqIjIiVXPG462aspebXm8tDXRaxku057u3UiALQIiviWXQUQMRwiaCrWMSlV1+ycvvcxAwVDqKei4Mwzy6pyPwrfI6gGotqjcW1aTrItBZxzCqWTdTzUpNdGyXVA/XV5zxVIY2trKmRreh4oaYiM+omEF0aZ6AimNo5IV50noSIAGIngykdhPoYcSI452VvXQLiTt4At7LFqoIgyBwThIWcSyoT80XG4srIQxxkMmFGMy2nc51shwRQ10q3MiA2CLJ5E3YVUuKuMmQy3QhDRk1lOqLCnYcpOeAZmyOMiPiIZwpxaUJPrjsD5nT3q1pOB0gn2lWcRWAMcsW0f0WAahkQlZZ2KDBwMbDxhBd3RNzpBTXNiP6EBgqoxG0seFSIDRMHwbwrVwCl/Y8+BuDMKL/hBQpJmhlVgEnhEJhCV89J7w9MdKKqk+aRfwBCgoAQhPk1AA4s0u0srbxSTO8K3Xnrjbjh1P+OICyAYKHEDcdg2g4LKASkNnUkKogyjOGhx/G1z942a7R3AucE+S6DuBZj271fRq00guL6E3HKOb8OG6d5Ee2MC+cE+YJBtVzG1ru/gHrlEAprNuL0868FlBHXBBxwC28N5Asb2yOuiuUgMvuf+fctcWX/rnTaVwUUFETR2k3n35jt3vxOdbFtw/O2bPnS/m2PlYDH2r1iovuY2wdOe90egPINjcwtomTRohWPLoPGnZRE//yJh/CDO/vRvTaEc4ogICSx4LJrXoW3/tFXUTpkwcY0mfhiFNdk8M2/+x/4wof/DmGGUxtM2L+vjrERmVVW293hLHJ5g92PfwN/dvVV2P5gpeHVgYsuH8D7PnM/MrmNcG5hzyvOIp832LntDtz01jdh56O1qe/Oe/m78YEv3od88WRYK+14cNOBu0U8MbyrXhmeOOyb8v762Ls3b3nbb4K42A5x2ilr0tHSzPV8E9QnhsZsvfRYGPWcr5rY1rl6q3SBRQwM7bYY2j07A2f/3r1gWnBFC1GBIWBs/z7seqw+r+1FSV0CCBZ/8XtvwfYHK+BgOuvvB/86iM/f/Dq862M/wqHRGODMQmYAWHz0f16DnY/WEKQTAoiArd89iFv/9Cq895MP4dDBhe10TFwAxGE4lRSiCigBpOkOldQPkMmuSRcGR75GaSQ+oJ1sLA4iCky2L8234OWNlNAyrui0oXQmSwiCNK0vzIRtyw4ThiAGTDCdEthGfmvTRVQYGYwOPY4dD4+lCTrS6B+T8uDR+x5HIgCRaWnn0MgO7PzJeJol1kh55CDtssd//BQSh3ZnbNM5o7SRuqpT/0UgWrJt48nklRmpkUHYFQRhLkNzyiAARMX+s6/mMHei2voSSJWFXIZiQQ29VOTVGW0h0llaqKpCBRBqP6G7tVE7pS9pxvpGHMABtT8o1KVZZDJ70hNp2Gl/Y2h1PfYxI+MqVzyuN7/2eZdnCwNXBZnC8znIHD9nt1UxlTguLsHykdZjQV92FOyY1UbabGFTcc3mi27OF4+9gYghYlO5oII0ajC3wiqwYMqshlp4Jq8MzGoibbH/3Bf0Hffie0FsxNasqlpiMjN0K8/LlSYphMs3l0+GBmfm4ypUJP4FdLlHZcxyxww7/EE8Imij146EtD0D5124/sRf+bFIDElq8WRmV5omOJVnf/TAMCpOwlzfJcwhqTqoSvoRC0CRLW68RNUt/frt52aXmZrXpUPFYTrzNUkyvXBqlKZAYHIhTLS+U/JSI2qQKx67dt1xL7nXxuUaEQyYV3ba13YEFrGKlSjXe8nAaVfcVhl75pZG5IOgkkS5DS/J9578QXF1WSWyxUuFtG8FUWHgJHDwDBEHAJFCNQiibM/G829mCooqnW5AKIgCrD32xZ+BCkjBK7rAagQKRGypLS9JxCKJRIWBN+WKx75pdvs4iKvLskcdPDogLrFRsVh3/EsfOVzLEHFjuuxoVa+Tjq5rzQkbs4WBK1xciWnFPW36h43LI6oConbag1glttbW7ewxwPwL6WlVdalPN1gGqeDmPAivOpkfyO11ujpRmX5YPt97yhWN4KUchVYHAMSV4Wedq48TBW3u/LEhhg+9LfEI6CQk1um0xo2tnekPsWmPtBAQQ1y81yUTtdRbB4jyfZeqOE6jB22s6EViqNh0RSQWojFE48XTFkjqh5K4sv/vmUOZ9dSqx6oFr+CAskQstn7oey6ZkNRvRcwmf46qQztnAREFzGEuQyYyZCJDHBkOowyHUWZxTyjrVFSjtH/bh4kNH5V5z2N5pcKR8VaE2XD10O7PTevjgDgwUWuuqBAZtkn5odE9915lk9LBqSQcIu5ed9Y1hXWnfljcIrZ8G9uMEwee2FHd8PwvZQsDb5akHq94ZMNjVRJXiAPjkupIaeTRezq/GpZCkxndc++V5QOP7Tj86+r4no9EXRtea6LixY3sMNP5wHIYeeY7b990xhtficD0qbMrv1j0WF1SQcRVgjBvxgbvf72NS7bjJ7xZGRC4uDw6dVLLzI0QFYitPpnuYC1S7RIhruyvDj/19V8ipYNsooyKq6UH0nosPGPpEtlZNcQVK+oqYdRdKB944oNjz95/D6ZOUlwEiIOptLqZn1QzREfUgKoAMSpjOweffeL2E+LqwTtMppAlDg2Qnuan4moQief9qCd4Oz14tKRCi7MlVRqndUr6RIrJhCZrSiOPvWfk6W99OM2tpWUZlpqeHnOEoz5Nt6uVny3t++mXXlfsP/uC7nVb/jjMrb08MCarkymd82t4qMR+A2JValxiphY/AE+e6ERIaqM/HNt9zzvGhx9+ZHYQipacuEs79RFULMae3fpf44MP/WpU6C9G+f6TTLbn9MBkN0JnnIxHFCgRh5nCWVHXwJtV7JE/AeKxlMQliK3tFLETc5LGtfFUqrgJcbUnkuroD6vju75ZGd2xSyR5DsaXprO+VB1qpX3jtdK+hwA8tNBVfSe9+vvFvjM+6WzNks8NXgXEVbFssmb4qTsvqJUHR0A0V6hS6q3ExYcflLCEjrJZrHeps6cms5h0KlF91pPN80w0KhaVg9vvKK7f8sn0SdtfpNWZHrmTUO2IJx15BbFxLT0qtMWdTh2lL0tIWoLq5FHWNE/llZeOwLMbseWmRONZscK6U9+YnpDj88lXmcZtLDxaedGlCpFMjRgSBEBX3+mvr5X3fubwtIZc8djeTG7dK1USOaJn3xr1igqbit3rf+lKIuQVFJCqKBNz+ngdKZSJaDIZmaFwYbbnhZmu/qvaTWuk9AQTjxWKKizxJCMqqo5bOSimjLgYxb4tfxvl11/q4vJPFBySOkeBKURdG3+LiIstDwRpJQ9UwUFE/c+77HthtvccbX4eyTx1cW1GFdLFn7P13dMSq+WA8i58dRA37SlxsYit7AwyPf2qtiVJVBKJ8huuoK6BK2Y5ZJc0HmM/8lAUB1FAnNlo66Vag1esUKGmthvMY3A7O3YKFRCJjce2pVcTfH7Ec8rjElQSJPXx72WyvS/UxNrWz46lubAqh8Vs08yyJQpBqULVpo8NqSA9PaC1t25bjZCBCtfLg9va0s8e8zuYo8fbtLNr4z/7l8bLU9rcQGADpsysz5LXQ5epXdQSG7a18Udqpb1D0+uB53pQQZfKENp9fQIf1QoDmDi4fatLJg4Ss8FynY27WvpYnOUg4tLBx98jrq7w0nUlPK5iaUMFaYzU1sft+PBP3haEXUacq61AnY/8vViLKlVjNlE2qR7cOj74wLexxK3pibvSXpcIo/v+6xu1sT1fNlFXXtSVl7lQVkmqK0taicFsiFj27/rOq52tytQGh8fiiKvUxvScvkNOlmUhoYBKgqEdd76lNjH4lTAsFACxM1IKl0g+iAURxCVxfWLwZy083lKUKdC0HmyiDIjj4R3fPKU6tmtk8gCRDga4Lstvpc11RavMt3btSIt7a/t+nDVMQV5F4qa7PaSsKpYDztKyxBMbkiEuu8HHbr9y3fEvvaaw7sxbA2OMSAIVB0CkrWMbmy8EmciYIJPHgd33XJLUDsXNN1GImIIuEYkXXVlSBgWGg4iJjalVBr964Jm7r6mV9h6azB/uLPYThhCxEBc3Fi8yZ+ZUF0McN33P71xnRMhkGZXxuKlwEhWIM4hy65qqK2JCmGHUq3HT8a6anmCeyXQvFG5BJmLE1XgB7Z8qhHzRmFpl+NaunuOvm37r4nzEMiapHXwwqR0qLYs2a2RkiYt1/9N3fW586OF/LPSdcXmueOy1QVh4AQdhX+vMtIXMC2xc/fGBPf95w/jgAz+efrP74RqeILbm6vH4f+QKA78ukix6+1ZcfaRa3vfPEwce/+vSyKPbVNzi8zaGdu1Fjg3s2sLUe3HnFlhEPgAGd++amiYXkGfYvX0CT269HWe/8CrUdP6gnyiQJ+Cub92CSklnnbE7maK656kJ7N3xQ5x86kWoN3mHnQjQxcD37/vyXDuNa/Y8VcETD3wFZ7/giqb3owBCAPd99xMUhF1B97rTzwUH+eatSsnE6FMPJtWD9aV4dWpLXdKwTxTAZHsik+kuEofRIolLIkm1PjF0QGxN2yk7jNaEhfVnvoiI8h1VVqHi4rGkPr43qY48G898z8RiSUuUvrj5be97ObZc8ArE9bk7aQqHMMPY9dOt+OxN/4JqWRcMtU3eS28/44JXnQjiAIfnmyoUTIS4GuMHX9uFalnn1GHy35tPyeAlrz0HZMIpIs4cKMyMuFLGXX//MEaHpamd3gHGf7v0ZDAHc1tdU+8eV2r4z68/41W+h4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHx3Ma/x9f8a8BrYj6hgAAAABJRU5ErkJggg==",
    "gp": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK4AAABgCAYAAACE7kkqAAAX4klEQVR42u2deXAc133nP+9191y4CIIiCR7iAR4yJdEUJVGkZFqSFXtlxRUpih07lu0kPlJJnNjJ7tpb5dqqrfVukk1tKo5dOe3actZxxXKsjWz5SGxFEmOKEkmRBHGRBEmQ4AkCBEkMgMEc3e+9/ePNDDAESIIUQGAw/aqmWAQaPT3Tn/697/v9fu/3E5TRMMaY8rlWEAKGU4b/849p5tUKVixzWLbEYcliSSIuSo7X2h4vxMxcrxAz9c63NlzCMa3gHj4W0NIREI3Cm/t8PE9QVytY1uiwfo3DXWtcGhdJpBz9OwNIEX6HIbgzYsHsv/sO+ngeJGICrUEbGEga+vp99rX4JOKC5Usd7rvX5b67XRrmS0QBYEMR6HBc9f2GUmH6rO3lAcP//MowQVAqAcZKAq0hlzMECmqqBRvWubzrIY+71ri31QKXm1QIwZ2GobW1lK++nuM7L2aorrLW9nrWWQhQCjJZgyNhXZPLE9sjbNzg3hYNHGrccBTham4LcB1rNW9koQtWuiohMAY6uwI6uwLesdbl/e+Jsq7JKXkoQo0bjmmRCed6NN1nFJGI4GbmiYJljscs/YeOBnQeD3jwPo+nn4wyf54snk9U8AIufHanAVyAA20+6Yy5ZeuotX0l4oJIRPDGWz5/8rUUr+/xi5LhevIjBDccN/eFSqtVWzqCm7a21wLYGKiuEmQy8H//Kc3ffitNctA+FJUKbwjuFC/KALpOKc71KCIeTNVyUmtwHAvw/lafP/3LFJ1dQcXCG4I7DWN/i0+gpl6DGmMhrUkIkoOGr30jzY43ckg5usALwQ3HLcmETNbQfiQgOgUy4VpDafA8cF349v/L8MKPMsWHpFLgDcGdYplw+Kji4iWN500vRAXvRU2V4F9fyfH3z2cweU9DJcAbgjtFo2Dx9rf4t9WDoTXU1gpe35vjG99Oo1RlWN4Q3Cm0fslBw5EuRSwqbuuCSSmorRHsbfb55vPpkusKwQ3HdcEFaDsckBzUOM7tvwaloK5GsHu/z3dezMx5yRCCO5UyodXHmcFvVCmorRa8sjPHj/8tO6ddZSG4UyQTei9qTpxSRG+zTJjI41BbI/jBv2bZ3+LPWXhDcKdIJhxoC0iNmFmRAGMMxKKCf3ghQ0+vLvp5Q3DDMfoF5i3awXa7u2E2AGKMjbJlsoa//24aP5h7AYoQ3LcxClPwqbOKM+cV0cjsgaOQoNPVrfjxy9k5Z3VDcKdg7G8N8P3Zl2aolM1t+NmOLCdOKTs7mBDcUCZIyPnQesifkkyw6fJ4GCP4p5cyKFVmW15CcKdPJhztCui9qKc0E2yqrzMeg+MnFTt35+ZMHm8I7i2bsrxMaAkwsxwEbeyOin95NcdwysyJ4EQI7i2u2mW+2MehowHRqJjVIBgDnguXrmhefT0XglvJ4AJ0HAm4PKBx3dkPgtIQjwt27s4xOGQQZe5lCMG9xQUPwL7WoKx23LoOXEkafr47Vyw6EoJbQdZWCDvtHj8ZzHiI92avPRYVvLnPJ5MxZb3NPQT3FmXCwfaA4WEzo0k1t6R1Pejr1zS3ByXekRDcCpAJxtjchHLQtuPpteHg3fv9EtkTgjuHh87LhLM9ilNn1Kz3JlzrM0QjgpOnFT29umw9DCG4N2mtAA60BmSypnytlYR0xtDc5pfInxDcmRRxWtsg/djXFAk5KSEIoOXQ9O7ivR1fk+tAx1FlF5syBHeG5j8NOl/IQEor4sa+CstnpW7ZvBSLfXQHnL+gxu3i1WY0dXCiV+HSZoOVNgYiEcHZ84r+y7os8xfKu+jdVdWPzUgKdbILdeYUengIpETWz8dZsRp35WqKm8HeRsnDfS2BTVYZow2FgKg3KiVKV3P27bJZyPmGWFTgujO/mpcShlKGrm7FHQ0yBPe2Qpuv/hYcO0L6n5/Hf+tN1MVeyGRK7pBIJHCWrSD6xJPEnv4Qsm7e6N9PUtoWdGFH52iIt/Cz9WtcPvmReD5l0Iwz6lrBwJDhUGfAG2/5XElqEvGZ9/8KbPLN1vu9ENzbA60GITG5HKm/+yqZf34eM5JCxBOISBRicUYT+AwoRXDyOMFf/hnpF79L9ee+SPTx900a3vzbcehoQP9lTVVCFAstF/IA6mrFGBzGjwUNsGalw/atHv/wvQwdncGMwmuMrYRztkeVZY5u+c0R+dWEvnKZ5Oc/xci3vg6Oi5hXD5EIxVR/5YMKrLl0HEQsjqhvwAwmSf7BZ8j87MejZcBvZJnGZIKJ6ygWY+D8Bc2+gz4H2wOa2wOa2wJaDwUMDlk66uskv/ubCdY1ObYMqZhBcB3BpSuGgYHyi0K4ZQctBpNKkfzC7xK0HUQ2LIQgXz3Gz2FGRsDzEPEEGIMZGgSjEdU14DmY4SFiTz1DZMvDk+oOUjDKA0lDZ9e1Q7wFuPc2+7zwoww1hfL5+Z/XVAl+5QMxtj3g4Trw3LNx/virqRm1do6EkRHDhYshuNMPrpQMf+WPCVoOIBbcAb4P0sEMJpGLlxD/1Y/jPbAVZ1EjaEXQfYLc6zvI7ngZfaGH2Pt/iZov/2+E601KKhQOaclbzRv1c/A8Ww4/kSg9LpODbz6fZn69ZH2Tw+KFkg3rXZrbbOed613K1e9X0lrK3Hi2GNso5erfKWXo7QvBnfalcO71N0m/+H3kwvl5aCVmcIDYU89Q9fv/GVnfUGpVVjYRfey9xJ56muyrP6X6P34JpDMqXCcpEw60+dYpMYl+DoVq4mNBiXiQy8HO3TnWN8UxwKrlDvsO2toH2SxkcwZB/rLMaKQuFhM4wv5fa7t7twDw9fzJQthzFq4jEhGl0kTYjxNa3NthcZP/HXd5FnXJRVQHmCtJYs9+hJov/jd7jApKgcybMm/zFrzNW0p08mQdFz29+WIfEXHLU7vJF2ZODpriEi4Ws/ClRgwN9ZJ73+GxYplDdZUgCGBgUHO8W9FxxEbqIhFryTcsczHGkErD6bMKR078PCkFTStcEnEQQtB9RjGSNiUWW+bbWoXgTie3g2/h1L5Mze94jLwUIbsngXf33dT84ZdGzZvjlkpiMWa+LWpaMe5OTzRNF8BtbrNpgDeSCSXTc6lfA+nYCWLJ4tEHJjloSI0Ynn0qyn94PEp11fiLePwR2wjl+e9n6OwKiEUFz30wRm21IJszfPnPUiSHTEnCjxA2wldXK/jcp+NEIoLBIcOX/zw17nNKKRgaLj+LW1ZeBdP/Q0xKI6JQ/dwJ4o93kXjuN6ywNOODCgV9JwQIKRGOgxCi9OfX6R0mpd050NwR4E0yE8yYfKRZj76MgcEhw7xawRPbIyU7KD7xoTi/8oFYEdorA5rWQwEdnQHDKXvg0kbJ7386wZpVDj29ih27coCVCQ9s8shelTdRkAj3b/SIROwvXtuVYyA5viCfEDCSDi3uNFvcA/ZRUwIz4pN4RuE8uDlfusVCq/PT34UBzR/9IHtDy5gLoHGe4L8+EyvJrS0E17pPK86d15Pefu66dmNiLDZqnQWGVXe6fPADURYusG/S0Rlw4rRiw3qXdMYQjwl+9LMsr72RY2TEmvq6GsEz74+y9X6PiAe//FSM4ydT7G32ee+jEWJRwdYHPF7blSuZCbS2CeMPbfYwxmrivc0+sauy2QoTUCZLCO60jszp0TlYaZBrwGvMm8xSs5nxYf9JfUNwAwVdcRhMG+qrxq/u97f6+IGZVAqjMfDYwxEe2uwhhSiqESnGBijg4iXNt1/IEI0KXvpplsNHA5YtcXhtVy7virZaIzmo+eZ30tTXCdY1uay+02HlMoejJxQHWgMe2eLRuFBy11qXlg6/2JE9nTbcfZfL0kaZX1gG9PXra0odpUKLO71Dp0eXw4BxEhghsIiUgisF1MavcZpC4gug8pEvX42XCdmcoe3wzWWCxWOi2FxvotF2OOD572dIDlorPq/O5sZ2HA1YfIdDTbUgki/llM0aTp3VvPq6z/o1Lo4D8+slQipe35tj6/0ejgOPbPFoafdLPt+2fBhXa9i1J4frTvwZJhmDCcF9e1dbV1zuGAEyuIQwPohChssoMErD5WEzLgJrDCSiAi+/Etf5QyaSCZ3HFX0X9Tif7PXG+QuacxcUrjNqcZUyXLpst7IfOxkgpShqz1TKsHiRw3sf9biryaWuVuLlUwdyOUPXKUX/ZVOcCTwPohHoPqM4fDzgnvUuG9Y6LF3i0HtRIwUsWiC55y57a492WUkSi4o5VTusvMCNrYbkARSCqCPJjZwknTpFVVWTtbpCFDmtSwg+sT1SYlkKUvjnRwLOXTFEXWttqqKC6qgoGvPCOfa1+NzMvRYC9jT7vPDDDDXVpbAXKijGoqNPUjZrWNfk8lsfj5d4FDIZY4t4xAXvWFvahHr0hLDzTZ971rt4nmDLfS4v/sSK1c0bI8TyVn/nHr8kr2IieeM6IbjTOkT9dtSFF4iKHJd0NZ/rX8uWE2/x+Y1rCIzCRRZv7vxqwe+9LzLheXYdDYoWLFCGJfUOUa/UnTQ0bDhyzPpub6ZSTcSzheaqJrDSY3NzlYaqKsGnPjoKbWeX4mc7slzo08UducuXSn7h3VGWNcqSGaEqIeg4GnD2vGZpo2TLfR4v78iR8ykuyi70adqOBMRj154x7AbK8svILa8kmzt+iUg0QXO2no9dfox9ponvdf6AM0M9uMIl0KVibdQlZcj4CjD88IDP0R5NPM+0r+De5bJE+wK0Hwm4kswX+7gZz8dVkbOxr7EPRjZr2LjBo6620C1d8RdfT9F+JCA5ZBgcNvRdspVnfvJKdgL/qz3Hzj22Ms38eZK1q13uXCpZstg+wG+8lSOdvvY29IIVjkUJwZ3Wi42v5NW6z/OJi/fRY6pY4GiSuRR/sPNP6E9fwZUOBoMyCmUUCPtypCDmOXRdEPzNKxkSURsB08bKhMc3uCV+X6BYhn7a1pkaGuaNejF27c2h82VBXcdO37Go9dVuWDt+YjTahoL3t/oMJK0GfmSLx7u32SdyOGXY1xLcUNtqA4mEDMGdZk8uS5v+kGiklojJkDNQ5cXpvHKCT7z8X9hxbi8AjnBKXr5W/PDkq3z2e62kUjW4jkIKw1Da8Mg6h9ULZXGRJoR1Vx3vnt62T0LYxJvCgzKvTpLJGptCkf/Z5SuGDetcHtrsjpcdWLgHkoY9B2xH9bvXuzy4ySvq8/7LNy4PZbShtrr8pEJZaVxlDOtr7+ALmz/Jl978Cgvj8wm0otpLcC7Vy+/t+B9sXLCeBxfdy7LqRSit6B46z97eVg5fOU5sQRU1/BYy+T580tTGNb/9RKQoBQrW72C77ecw2RDvTT9+BjxXcPxEAETRGt77aISeXpuXoLVNiHlki8eHn4kRiYgJXVbGQDRfmeY92yPF6J5SsGuvj+de39qKfOLOgoYQ3GkdjpAoo/nw2qc4NXiev2v/Lgvi9Rgg6kQQDrT1d7K/r73k76JOhFqvFkNApvFr5CInMD0f4n89W8fyBlmMthkKxT78a/o9rwfj2H9vdGw0CidOK3bu9tm+1aOmSvDZ30zQfUaRHDQsXCBpXGQnxNZDARvWuePObYxdDJ7vVew76LPtAQ8h7E6N02fVjd14+Qd18R1OCO7tgFcbzRfv/zRVXoK/bvtHBIJqLwFAlZegWkwMFbgMZTLE6l/ij57YxuNrGlBG23PmfbenzipOn9MlXoYb6q0x2tid5DeqNcQigu/+IEOgDI9uiyAlrFzulCwuv/dShr6Lmo15HT6R7jYGTp5WbHvAyoSdu/1JlR7Xecu/eGH5adyymiOMGUVJG40Ukjd7DvLVlm/R0n8EgyHqRHCFgxQSg0EbQ6ADcsrHlQ5bF2/iP933Kd4xfxXKGJw8cQVwX/xJlp+8kp20TCi4ppY2SgTQf8XQf1lPqqaYyGvVdMaweoXDpns8Fi+UGGPrex1sDzh2IihaXwGc79UMDY/xFAibyfmFzyZYsczhzDnFn/7VyA3fvxDurqkSfOnzVdTWSBFa3Nuxqsxb3m2Nm9ja+E5ePbuHfzu9i47Lx7mcSZIOsjhSUuXGaIjPY2PDOp5c8W62Ln5nHvxRaAuWzA/stBy5ibZPhXza9iNB3uIKPGdyLrTCMVUJwamzmq7uTBFIra31rqkWDA0bLl0J8n5iUTxG5rfebLrX5vGC1bbZ7I31uQCCwLBwgQ0zh1JhBuCVQvLEsq08sWwrgQ64lEmSCkZwhUuVF6c+WovMJ46b/PZxOQbagrU9fjKgp+/mw6NSUkxwuZV+YlrbMO7YqNpYn3DJ+TWli0kJjz9iF5iDg4b9bUFJZtr1yA0CisCH4M4AvNbjYO+UK10WJRqAhqs8ErZiixTymvm3ExX7uBn43q6n4br+1gn2i2WyhrWrXdY3OQjsRs2BAU119eRkjpSwZlUI7owv2orTrzFFq2R3I4ji7ycCRkqbTH2oMyibCowir20f3WrDu74Pb+6bXNsqKxNgXq1k9YryBHfOVWu0QQSBzL8EN97FCzax+9JlPemdDjMNbSYL65pcHtjkISV0HPU526OKKZHX/Xtpy0GtutPubyvHrDGXCh8lxT7KaI1ijGF+vWB/i482dmuO60z+odMa3nm3e5W7MAS3TG6+BffygOHoifLp51DIHDvQGrDngF/0Nkx2e5FSMK9WFHN2y7HOr6x0cAFaOnyGhsy4jYSz/doLxUeqEmLSZf3tHjO7tae2RozP8w0tbvnIhHLt53ArrrdCMv3DD0bK+t5VrMUtyIRzFzTdp9WsbSI91Q9qNmtYvdJl7SpnMqXTQnBnq0w40OrbqokV8E0UwryPPRwp+7aoFQuulHaR0tIRVJC1hRXLHe67xy1ra1ux4Bb7OZxSnLugiHhUBLh+YHjy8Uh59mcLwR0dB1p9gqB8m9RN+iYLu3N4fZPL5nu9sre2FQtuwSXUfqS82z5NWs/n/336/dFiwfayv4eVKhOOHFP09etxbZ/m2nAcW3TkXQ9FWLvKeTsNh0JwZ1rrgd1MWAmfNZeDOxZInn4yejONhkJwZ9WUmb9xg0OGI8eDad3FO2vA9Q0feSZWTKYJwS1TcAFaDwckB8srxHsrEmFo2PAL2yNs3ODOGYlQkeAWQ7yt/qT2hJXz4jM1Yli72uGXfzE2pyxtxYFbuHm9FzVd3apsMsFu+oYKyPlQVyP59EfjeG7pQxuCW6YyoTlf7GMuhngLxfQE8JmPx2mYL8s2+ysEt3BTpXWFHWzz52SkrJB7kPPhkx+NzynXV8WCW6gLduqs4vRN9HMoN2gzWcOvfzjG5nvdOQ1t5VjcPKT7W3x838ypqVMKO5Pkcobf+HCcbfd7cx5aqJBEcpnfHNh6eG5lgklpd/ci4DMfS7B5o1sR0FYEuIUbeaxL0XtRk4jPDW+C49gt9dVVgs88F2f9msqBtjIsbjHEG8wJS1soPj04ZGha6fDJX4uz6A5ZUdDOeXALvWpTI7bjTblngklpC3lks4bHHo7wq0/HiHhUHLQVAa4QtpDdwGD5yoSClU2NGOpqJB/7YIyHNnujD2cFJqdWxOLs8LGAdNq2HZWSsoG3AGw2Z1AKHtzk8ewvRmmoLy39X4mjbOvjTtbigtWDL/97jp/vzpHJGhJx24h6tgJcADbnQy5rWLHc4QPvi7LpbrdkwTm171lej8CcBvfqcbZH89PXsjS3B+SyhlhM4Di3Vp9gujQsQDYHvm9YsljynndFePjBSElNs+lALAR3FoJbALMARvcZxY43crR0BAynDJ4niHijEajbCbHM98/W2ka+jIFljQ7bt3pse8Ar1syd7gVYCO4strjG2CBaoWh8X79mzwGf5vaAnl5FENgaXJ43atWmGuSxvdSUsoERpWwppXVNtjXUOzd4xV4St8tjEII7i8G9lgVWCo6fVDS3+xw+FtDXr/F9+3vPtXJCyjxwZkyZfDNxyfyxCIz9G6VsC9bAVsWnukqwfInDvRtcNm5wWbSgtO2pkLfvBoXglgG41wIYbAj1zHlFV7fi5GnF+V7FQNKQzYHWxlY1l7YGr5CFwtHjz2mM7TOh82mGjiNIxGF+veTOpQ5rVjk0rXRYMF9e93oIwQ3Bvd4oeBiuhiaXM/T1G3r7Nb19ir5LmoGkITViSGcMvm9zYI02SGmrJkYiEI/ZKorz50kWL5Q0LpQsWiiZP6+0lP/YxtQziU65gfv/AQ9uvCTI0nFUAAAAAElFTkSuQmCC",
    "pp": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK4AAABgCAYAAACE7kkqAAAY5klEQVR42u2de3Ac15Wff+f27Z6eGQADgHgDBJ8gRJF60aQkP0iJMfVMuax1ea31S/LGcWxZjl273rWTVCW7ydZu1rsl7SNZOUpWKnllW9JaVsWWJSuSZVGi1hRJkZQpvkCABAniRQDEYwDMo/vee/JHz4AERVAUOARmwDlVt2YKA2C6b399+pxzzzmXUJTzCoFAJMBswOBpn0VkhYg5DbEKp6k55tRfVWJXrQ5b5deErMhiS7h1Es4iS1gRADDGpBSSfb7xBzw92ZPQw/sm/eHDo17PwVGvp3vM6x1LqFFzsd9dlOwcFeWcCREAAIY5G1SrNtxaXxtu/XCVu+T2Ulm32ZWlKyySAAgMk4HMgJkzsPG0/0lEmVeR+Q6GZoWkGjsy7g++PpQ+9tKpRNuOwVRH/6Qa1hc6nqIUwT0zERkNl5WoXGQtLrmhdWnJhvsXhZbeH7EragkEzT40+2DWYBgvgIpEgBiLYEpJTP/vbAL0yAAMQvBFBOEIkhAkYZENZkZKjQ6cSh99rHti74+7JvccnvCH1EzHWAT3CtewZ7QZoSl6bVVL6abPN5Vc+8dhGWs0rKGMB8O+xwwDIWQAqBC5OQJjGFBs2JCAEJCOFCEIkkj4o329if0PtY+/8WT3xDsDWbNh+jEXwb1igbXIxoqyj7ZcFbvtv9SEl3+BIOCbJDT7XvCIJ5k7UN9P2DCMYmZYZDu2CINhMJTqfObw6Kt/2h7fdlizd8UDTFfiKVPGLiUSaCnbuGJNxd0PVbvLPqmMD59TipgNkZDvfeTPtbBhNoqJhEOutMjGcLrrpf0jv/yDtvhrh5nNlL18pTlxdGWd7BkN1RBZW7m++t6/rgu3/htlPPgm6YEsIUAyH4/dgBVYG1uEHUkOTiXbntxz+rlvn5zcO3glal+60qANyzKxoeqzX2qJ3fIYAHh6Mq+BnQlgx4o4BIH2+Btf3TX49GMJNaKDc5we0SiCW8CGQfYxuqz0poYbq7/4f2NOzYaUjhsGGQEhC/G8DIwCgLAoleP+0Ds7Bp/85LHx7V3nnnMR3EI8uUz4yCIbG6o//7vXVNz5z4p9KJ1OCWG5C+EcjdEpaTmupBAOjr78ubcG/ukpzf6CD51ZC/XEBFlgNii1q+WWhm8/0hL72PdSJu4ZMAsSzgK6OaWBNtqk/Ybo2s80RNcs60scfCGtJ4wga8FqXlqo0BrWqA23ln28/lvbInbFtWk1kRJC5kTLCkEgQWDOxFWJYAyDzfxCYoxOhWTUTaqR/a/2/f3H+hOHx7JzUQS3QKBdWnJj0y31X98ryKpSJuUJks6lzJIQBCKCVgbphILvaQiLQACMZtiuBTdqw+h5hpeVJ4XrMEx8a+8/rDk+sbN7IcJLCxHalrKNyzfVf/2oNh40lLoUByzQpgGsWhlEYyEsXbMI12xsxOLVlRCC0H1kBDtfPI6OdwYQjYXmX/PCKAuWlCKE1/u/v7J97I2jCw1eWmjQroptWnFL/YMdaZ1QDMalhLmICF5KIRSRaFlXg+tuXYzrNjehcWX5e2FRjGcf3o1nH96DkorQvGtehjGAMCERka/1/c/lHfFtnQsJ3gUBbtaDXlqyoWlL4x+e9ExKAUbQJSzTkiB4SYXm1ZX4xv/YjMaW6bCeDSYzB2YDEZ7+y134yUO7UV4dgVZm3uElkLJF2Hml5+GmExO7egQJmAUQbRCFf+cF0NaGW8s21//7Q75JKwaDLjG3gAjw0xqLWyvQ2FIO5RloZabMAGHR1LCkABDYv7/3Hzbg459fjbHBJCxbzPfcCAMI36TV5oYH99WGV5WaqWXiwharsKENAu2ldo19V9N/3GOJUIOGysmiAjPguBLH959GSXkIq9bXAswQlpgRdKIg0rBuSzM63hnEyUPDcKP2vNq8BBIGxkiyo80lH/pk58SO/+2ZSUMF/rC1ChtbgkUSdzR998mY07DZNwlPkGXnzgQBhCWw44VOhEsdXHVjHYxmENF5jSwiAAxYUmDdlma881o3TvdOIuTKqdDZfMGr2fPCsqyu2l3ZdDT+Lz8v9PhuwYJLFOQefLj2S59fXnrzn6RUPCWEDOX+e4BQ2MbOF49DWAJrPtoAwxzgQDNFIRihsMR1tzZh+/PHkBz3IG0L88guiISldCpV6TZvsMg+1J347QGiILOsCO5cO2OlNzZ9uOa+N5P++GVfwnWjNna/0gU/bXDdLU0ZDXoBeDWjtMJF64Y6bHuuA2wyZsb8wit9k0o1RNd+9nS689FRr3eiUOEtOHCztllYxsRtDX+0k0jEmFjQZc6dZQbCUQd7f92FybE01m1pzlzwGeAVBK0YVU0lWNxaiW3PtsN2xHl/d04jDQQABvXhNXd0xLc9qo2HQrR3Cw9cClL3PlLz+19rjK65z9OTKpd27YXhZURKHby7rQfDvZNYf+fSwNY1Gbv33JCNCCINTasqUFoZxvbnjwXOGs/rjS80+37UrmxwrGj3iYndewpR61oFBy0bNEbWLrq55r7X03r80pZyZwOvCeA9+FYf+o6O4cY7l0JIAb4QvJrRsq4GyjfY++pJREqd+Y00kLAUp7za8Krf6U0c+NsJfzCdraQogntZtEWwQnZrwzd+EJHlawyUJog5Pwc2jEiZg/bdA+g6NIwNdy2DtAXMTPBmHLZrb2nCUPcEDu/oR7jMmeelYdaCbKvCaVjSHt/206LGvcwmQkts06q1FXd/fz607bnwhksddP52CB17B3DjXcvghKzzw0uZ8AQzbtjSjI69AzjZNjKvMV6CsJRJexWhxdePeD0/GE53jRaSyVBQGtciG7fWPfCcLdzFBgya52LGLLxdh0ZwaEc/Nty5BG4kyBAjQefceJiK8X5oyxLs+VUXhvsT8xrjZSImMGJO49r2sa1PFtJScEGs/WU1wYqyj66qdJds8k1K5UuNmPYNyqpctO3qx5/f+yJGTiUgLDpvkg2J4OclFSH80eO3o7TSRTqlIATN08Un6ZuUqnaX3ras9OblAGfmuqhxc/low8a6rzwWskpWMbSZD9v2QprXLbEx0DWOva+exLotzSgpD51f82bgLVvkYtX6Gmz7aTvANG/wglgTiEpkVVP72NafFMqKmigEYAFGY3RtVZW77JO+SRuClXelN9o3KCkPoe/YGP7sd19Ab8doRvO+9/ErrCBM1rqhDg/+3WakEj6QyXUIch7eOy7f/FqOZ9KmOrzy0/XRqyuDFlH5r3Wt/Ac3MA7XV937zcrQki3aeB5RbsyEbFUDiDLQzH4IIjADoYiN+OkUdv7yOK7Z2Ijymsh5Q2XZGG/zVZUoiYXw1vPHYDuBc2c0B68cvGcOciaEoMsTA2b2pHAEYA0dn9i5PTvnRXAvAVoGIyorrZuqP/csw4RBsHKhg4iAdELBS2toZaC83Aw/pUEWIT6YwrafdmDluhrULCkDeAZ4tcGq9bVQvsHxA6cRLXfhhCRCYYmQG7xKx0Ii7kF5GnYo9zkPRBCGtYja1euOxt98yDdJzvfVtLw+umzG/uryLWs31n313aQ/lpOcBCEIqYSP6zcvxu1fuhrSzv39a1mEVEIhGnOwan0tmGe+3bKfjY+kpsOdAdRog67DI3jme7vQsXcQ4RI7aJWXQzFGp8J2zH2j/3+tOTz66sF8r5bI62YY2TBRU/SGLxhWhkRujC9G0PjzU9+6ASvX1cxRZOTCnzEDpRUz35NrPxbGiuvvxp/c83P0tI/CCcucxoBJQBjWaI6su//w6Kvfnc80zIJ3zhgGEVkh6sItX1EmLShXXWcYEDLoUms0Q/kmsCsvw7hYuLLwzjSUpxEusfGvv3oNvJSGyLHHRhBScRrV4ZX3h2VM5Hsfsrx3H2vcFXVhWV5pWHk57Z4YJHZNK8G5HIM+QJhrpogCEYJ8CAbql8Vgh0QmJzin6ApjfC9qV9TWhlsbiuGwS5S6yOqPAATOsQpg5rxo4vFBzY3L+QTPzLGpdVtvLoJ7iVLlLr/bsA+I3DWnE4LgpTU69g5k8mZNEH7KDs0XtwzLOBO6er/xAcwGoxlamfMOy6LL51ILITUrUR1efncR3EuQsBUTpXb1rZpVZn+FXHnQBuESG89/fx962kdhOxaEoDMjU2p+MTEZYdH0v51pfACzIVs5fPawHQuWFIgPp6B9viyLEgIQxvgotWu3hGV5XrOR11GF8lBjzLViywx7Jpet7JkBaVsYH0nhzz7zAu74/TVYeUM1bCcIiyllUL8shkUN0fOHsTL2cWrSR+e7Q0F17/s84rVvUFkXRf2K2IyhsezP33yuA93tI3DcsyIHRFBpjbde6AxiuZfFdyJhoIxrlS6ucBrLk2p0uAjubMB1GpssktCcVgTkdJmXDcNxJRJxDz/+8x2QtgUSQfbW6GAS/+6vNuITD1wLo02mb8JZGpsZggi9HaP40995HtIRF7Q9hUWIn07h7n97Db728KZgJc2i89rdRITXnj6C7c8fncp3OFvcqA3bEZcto4zByiLplDuNi3sTB4rgzkZiTsOay7lGwoZhSUJppTsFniUF3KiCvIhmHiQIoYh9UeC6KQ3bubiHRjTmoLw6gmjMeQ+4F21/X2JwrMypXw3gt0VwZyGlsurqyx1PZAb47HZKmUjDxbJxMb/PhA/0P892zua6BxmDBMOg1K5eU3TOZuucyYo1QVdtKsh294UoBAhmg7BVfnUR3FlKyIosZpjiLoJzCy4YBiERWVIEd7Z2jHCqso03ijJ36DIzLMupKoI7S7GF2xjYuCSKQM0ZuIJhYJNbWwR31ve+5RRBmicwKL93JSpqsqIU5o2VzwdnjE4VL9H8CLNJFcGdpSh4g5liSVNEac6QNQQBn5N9RXBnC65ODRDlf+HeAgMXRARlvKEiuLOUtEmcCDZWLsrcYRu0BEjrxMkiuLOUpB49GPQMm/s6kvP1Q8hKNqrsuBKWFOAFdWexIhJIqpEDRXBnKeP+4AGCAM2DjZuc8KdTeh5ySypCCEVlptHdwkGXIDCuhg4WwZ2lxL2+Q3Nt3waphcDoQCJzEd9LJBEBDJQtCqN6cSmUp7GgyAVjzOvZXwR3ljLq9ZzUrEBznGRjSYGhnokA0hlmSGe07E13L0Nywn/fNEiiD1Y4OX/alqRmhVGvt6cI7ixlxOsZTenxkwJSzFVIjA0gHQv9nXGkE35m77LzTFxm9/Tb7luN1TfX43Tv5LSSm2nvBcFPK6Qn/TzH1hhBtkjpsc5Rr2esCO5s7Uw1auLewK+FsGHmyEFjZtiOhaGeCXQdGgEY503czloGbtTGd564HTd/YjnSkwrxoSTiQ0mMD6cwNpRE/HQSibiH2qVlaL2pbma7OR+wBRmLJMbTg1uTaiyvY+d5n+d6OnX0xcbomvthEgrCmpPjFRYhnVTY++sutHyoJlP3dX5blxkor4ngO0/cjmP7hnBk1ymc7puAnzZwoxKV9VE0tpRjxXXVcKP2lLbOU4WrhGXLQe/Yi/nORd6D259q+821YNAc9r40muFGJLY/34l7vnE97JA1VSB5Ps2b1cjLr63C8murLmCGcF7bucEcM04lDv0m37nI+ySbU8m23oQ/MiDIdubMzmVGKGzjZNswtv20I+i9YMyFHa/MBiVaGWhtzpTfZN4zI8+dMzaCpJNUo8MDqaP9RXAvycMVSKoxM5A69qQUITCMmrunpkE4auPZh3cjPpSEZYn3beghRMYhs85yzjLv8z1axjBKipDpT7b/n4QaMfne3Dm/wc1c7a7Jtx8XZIHN3K2gMQN2yMJwfwKP/MHrU89SYxbmAjQbGEFSdE/u/eHZc18Ed1bwBJx2Texpm1SjQ5aQ7lxmihnNKImFsPvlE3jkW1vBzFOdxD9oiTjndZ8yNpawnKQ/MtA1sefQ2XNfBHdWj69gP4KEGtE9k/v+0hauYcPeXB6D1gZllWFsffoI/vvnfom+Y2OwpAgiCuaslqLZMvXMMGZ6q1ES+bsAwYY9W4TRk9j/N5NqWAeJTcX+uDmR9vjWJxgQTHMfCdHaoHSRi3e39eA/f+JneOZ7b+PUiThInNVSNANmdggxvdXoQNc4jr4zOGWG5BW4BMmAOBLf+o+FwkPeh8MyxZLomzxwejDZ8WyVu/RTPqe8ua5H08ogUubAT2s8+/BuvPyDg2hdX4vWG2vRvHoRymvCiJQ5QS6rbzA5msboQAIn20ZwbN8g9vyqCx+9ZyUe/PtbZ2zBND/zqz1buHIo1fGznsn9QwAh35s6FwS4WUfBsMGB0Ze++68avvlpTyXnxUs3miEsQtmiMJSvsftXXdj50nFYUsBxLchM0zw2DN/T8NMarBl2yEI6pRCO2vmnGJghLUccHH3lOwyT2eibi+DmzkkjdI7vODaUPP5yeah+i8/+vOwuyRxoXxKEaMzJrJ6dsWkzwYepnXOC5BpA+TrvIhIGrGzhyuHUiTeOxrcfCXoqFEaVVMHYuEQEzT72jfz8a1K4Aqznd4b5TI8voxng6ZvpcWaPsuzneanEWBspXLFv5Bdf0ezlfQisIMFlNiAQjo1v7+xPHHzKsaIOQ3soyqxtW8eKOP3Jwz/piL95hApI2xYUuBm9C8MaOwefeoCKbZku+YlBsLB78JkHDBdeIrworLkOnIf+5OGxtrHXvuJaZU6wG09RPpBty8pzZZlzZGzr13sS+08HDpkpgnu5vSMCYefgU4+Ne4P7pAhJA1YFcex5oNQMWFkiJMa9oSO7hp56lEAoxGrPggOXM15QWo/zbwYev0NSSBAXALhEUF4eaDXDyhGu3D74xMeTasyAKO9XyRaGxs06aiRwYmJ3/7vDv7g3LGOuMSqVv8cL2I6FrsPD03420+9eNmaNSoXtMnf/yEtfOD6+s7sQTYSCBje4wEEew66hp/+5N3Hg8ZAscfPV3mUTJKYf++0g3vpFJ4R1Tp7DWYMoUyGRY4ANKy8kS9xTybYf7xh48keEwlhomEksFLAQAAON3sT+F5eXfuTTIStSp6EU5Wk/XSEE3nntJOqWlmFxa8W03IZs3sPkWBrP/e1epFMKIkc7ZJkg19ZO6/jhl7q/d0dKjxvKhhYK+NqjsOEVYBjUhleV3rX4Px1nRpmBgcjDfSOIgpRIP63RuqEWzVdXIhSWU+aB0YyDv+nFycMjcCK52R3dgBVBwAKlXuz+i8ZTybZ4ds4KXWkVvAgSMGywpGRD422Nf9jtm6THYEk53NQvhz4aQITUpB80EjlHHFfCCecGWoYxgDCOcOUrPQ81nZh4u6eQ7doFB24ArwXDGi1lG5ff2vCNo2mdUIAR+QhvYDYEe/Keu5BimHOoaQkhEZGv9//DyiNjbxzNztFCkAW1/DQFb2zTilvqHuhQJg0NrQTEFbXdlIFRFqSUwsHWvkeWd8S3dS4kaBccuEGYxIKBxtKSG5tubXjwAEGUKZPyBMkrYj8Jw8qTwnUM66HX+x654fjEzu6FBu2CBPdszVsXuSr28fpvvhmWFWvTajIlRH5vyHHJ0BqVCskSN+GP7Hu17+82nkq2xRcitECBh8NmdkoYgiyM+4PpExNv/2N1eGVzRahpvTJJDwSihdVaEcGSt1ERWRHqSxx69OXev7pnON2VXKjQLliNe8aDDzxoi2zcXHPfZ68uv/3HitNQ2lsw2tcYnZJWyJVk492Rlz6za/BHP9HsY6FED65IcIMTPLMWv7z0w803VX/xZ6V21fVJM64Cm7gwHTcDowgsXKtMxL3BXTsG/+mezvEdveeecxHcgsc3KAKMyAprQ/XvfbmlbNOjDANPJzyQJUSBbHRtwAqsjWNFHQBoH3v9y7uGnn4iqcbMQlhYKIJ73pM9c2EXR2+oXrfoUw/Vhlu/qNiDb5J5DXAWWFuEHSkc9CfbHn978Jk/7k3sHz733IrgLlDdmy3BJhJoLdt81dqKu/6mMtR8p2YfHqcUMRsiIed/D2E2zEYxkbDJlVLYGEx1/uzAyIvfbo9vOxqUM2Wbd/AVdh2vUDlbQ1nkYGXZx1pXl2/5r1XusnsJAr5JQrPvEREIcwmxMQxWzAyLbMcWYTAMBpLHfnh47JX/djT+L+2afVyJWrYI7gwAEwhNJdfXtJRu+mJDZO23I3Z5vWEFZdIwUB4bGBIkCJDI2VKyMQZkYIwiASFgO1I4EGQhqcZ6uif2/XX7+Bs/6p7cN5TVqlcysEVwz52Ic8JHJXaVbI6uu6qp5IbP1YZWfNmV5TXZEnnDKhhgRZnOYBmcRDCl52pnNpmKOQPw1PZXBOEQWbDIhkU2wIxJNdo3mD72xMmJt3/YNbG3bVKd1jMdYxHcokzTwACmabSorLSq3ZV1tZHWm6pCy+8statvCcvYKovklL3MbDKvfI42DCIaGZMDRCLzHQzNCik1fnRc9b82lDr+/04lj7x1KtnWl1Aj+kLHU5QiuBd04rIa7tyYaESWi5jTUFbuNDSVO01rInZla9SqvM6xoo22sGtsCtcTCRcAtNEJhdSgNt5AWidOJvXou+Pe4MG439824nV3jXm9Ywk1Yi72u4sSyP8HWE0C9ciRoM0AAAAASUVORK5CYII=",
}

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ---------------------------------------------------------------- helpers
def fy_quarter(qkey):
    """Indian financial year runs April to March, so Jan-Mar 2026 is FY 25-26, Q4."""
    y, q = int(qkey[:4]), int(qkey[-1])
    fyq = {1: 4, 2: 1, 3: 2, 4: 3}[q]
    start = y - 1 if q == 1 else y
    return "%02d-%02d/Q%d" % (start % 100, (start + 1) % 100, fyq)


def invoice_no(qkey, party_key):
    """Month and year, then a serial that starts at 1 for every quarter.

    The month in front is what keeps it unique: a serial on its own would repeat
    each quarter, but 05/26 no. 1 and 08/26 no. 1 are different invoices and always
    will be. The serial follows the register's own order, so rebuilding the same
    quarter produces the same number for the same party rather than a new one.
    """
    n = SERIALS.get(qkey, {}).get(str(party_key))
    if n is None:
        return "AJ/%s/%s" % (QMY.get(qkey, qkey), str(party_key).zfill(2))
    return "AJ/%s/%02d" % (QMY.get(qkey, qkey), n)


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
    W, HGT = 1200, 1200
    im = Image.new("RGB", (W, HGT), "#FCFBF8")
    d  = ImageDraw.Draw(im)
    # a drawn skyline behind everything - our own artwork, very faint
    sky = Image.new("RGBA", (W, HGT), (0, 0, 0, 0))
    sd  = ImageDraw.Draw(sky)
    for bx, bw, bh in [(-40, 230, 96), (210, 260, 138), (500, 200, 84),
                       (730, 250, 124), (1010, 230, 100)]:
        sd.rectangle([bx, HGT - 24 - bh, bx + bw, HGT - 24], fill=(11, 18, 32, 5))
    im.paste(Image.alpha_composite(im.convert("RGBA"), sky).convert("RGB"), (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 18], fill=ink)
    d.rectangle([0, 18, W, 190], fill=wash)
    d.text((70, 74), "AJANTA TOWER", font=ImageFont.truetype(FONT_B, 30), fill=ink)
    d.text((70, 122), label, font=ImageFont.truetype(FONT_B, 25), fill=ink)

    size = 76
    while size > 34:
        f_name = ImageFont.truetype(FONT_B, size)
        if len(wrap(d, o["n"], f_name, 1060)) <= 2:
            break
        size -= 4
    y = 268
    for line in wrap(d, o["n"], f_name, 1060)[:2]:
        d.text((70, y), line, font=f_name, fill="#14171C")
        y += int(size * 1.18)

    f_u = ImageFont.truetype(FONT_R, 30)
    uy = y + 14
    for line in wrap(d, (o["u"] or ""), f_u, 1060)[:2]:
        d.text((70, uy), line, font=f_u, fill="#5B7488"); uy += 40

    f_lab = ImageFont.truetype(FONT_B, 24)
    f_num = ImageFont.truetype(FONT_B, 58)
    f_big = ImageFont.truetype(FONT_B, 132)

    # the headline figure gets a panel of its own
    d.rounded_rectangle([60, 560, 1140, 812], 26, fill=wash)
    if o["b"] > 0:
        d.text((96, 596), "STILL TO PAY", font=f_lab, fill=ink)
        d.text((92, 636), rupees(o["b"]), font=f_big, fill=ink)
    else:
        d.text((96, 596), "PENDING", font=f_lab, fill="#0B6B52")
        d.text((92, 636), "NIL", font=f_big, fill="#0B6B52")

    # a bar showing how far the payment got
    pct = 0 if o["dm"] <= 0 else max(0.0, min(1.0, o["p"] / o["dm"]))
    d.rounded_rectangle([60, 856, 1140, 880], 12, fill="#F0D6CE" if o["b"] > 0 else "#D6EFE7")
    if pct > 0:
        d.rounded_rectangle([60, 856, 60 + int(1080 * pct), 880], 12, fill="#12A08A")

    yb = 928
    d.text((70,  yb), "BILL", font=f_lab, fill="#8A9099")
    d.text((70,  yb + 36), rupees(o["dm"]), font=f_num, fill="#14171C")
    d.text((520, yb), "PAID SO FAR", font=f_lab, fill="#8A9099")
    d.text((520, yb + 36), rupees(o["p"]), font=f_num, fill="#0B6B52")

    d.rectangle([0, 1056, W, HGT], fill="#FCFBF8")
    d.line([70, 1076, 1130, 1076], fill="#E3E8EF", width=2)
    d.text((70, 1104), "AJANTA SERVICES ASSOCIATION",
           font=ImageFont.truetype(FONT_B, 25), fill="#5B7488")
    d.text((70, 1144), (BASE or "").replace("https://", ""),
           font=ImageFont.truetype(FONT_B, 23), fill="#9AA3B0")
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
import ownerpage


def per_shop_units(o):
    """Every shop on its own line, with its own super area.

    The register groups shops - "LGF 28, 29, 33, 34 (1,020 sq ft)" - because that
    is how the holding is described. An invoice should show each shop, so the areas
    come from the master sheet. Every group was checked to add up to the register's
    own figure before this was switched on; if one ever stops adding up the build
    says so rather than printing a number nobody can reconcile.
    """
    out, total = [], 0
    for seg in str(o.get("u") or "").split("\u00b7"):
        m = re.search(r"\(([\d,]+)\s*sq ft\)", seg)
        if not m:
            continue
        want = int(m.group(1).replace(",", ""))
        head = re.sub(r"\s*\([^)]*\)", "", seg).strip()
        fm = re.match(r"(LGF|UGF|FF|SF)\s*(.*)", head)
        if not fm:
            continue
        floor, rest = fm.group(1), fm.group(2).strip()
        codes = [rest] if floor == "SF" else [s.strip() for s in rest.split(",") if s.strip()]

        rows, got, i = [], 0, 0
        while i < len(codes):
            code = codes[i]
            if floor == "LGF" and code == "12A" and i + 1 < len(codes) and codes[i + 1] == "13":
                code, i = "12A/13", i + 1
            key = "%s-%s" % (floor, code)
            if key not in SHOP_AREA:
                return None                      # fall back to the grouped form
            rows.append((floor, code, SHOP_AREA[key]))
            got += SHOP_AREA[key]
            i += 1
        if got != want:
            return None
        out += rows
        total += got
    return out or None



def qr_card(key, o, qr_matrix, path):
    """The image people actually save and forward.

    A bare QR square tells whoever receives it nothing - not who it is for, not how
    much, not who is asking. This is the QR with all of that around it, so it stands
    on its own in a WhatsApp thread. The canvas is measured to the content first,
    because a card with a hand's width of blank at the bottom looks unfinished.
    """
    W = 1000
    ink, wash, label = IMG_TONE[band_of(o)]
    scratch = ImageDraw.Draw(Image.new("RGB", (W, 10)))

    size = 46
    while size > 26:
        f_name = ImageFont.truetype(FONT_B, size)
        if len(wrap(scratch, o["n"], f_name, 890)) <= 2:
            break
        size -= 3
    name_lines = wrap(scratch, o["n"], f_name, 890)[:2]
    f_u = ImageFont.truetype(FONT_R, 25)
    unit_lines = wrap(scratch, (o["u"] or ""), f_u, 890)[:2]

    y_name = 196
    y = y_name + len(name_lines) * int(size * 1.18)
    y_units = y + 6
    y = y_units + len(unit_lines) * 34

    top = y + 22
    mods = len(qr_matrix)
    scale = 560 // (mods + 6)
    side = (mods + 6) * scale
    qy = top + 214
    cy = qy + side + 44
    HT = cy + 78 + 34 + 96

    im = Image.new("RGB", (W, HT), "#FFFFFF")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=ink)
    d.rectangle([0, 10, W, 150], fill=wash)
    d.text((56, 44), "AJANTA TOWER", font=ImageFont.truetype(FONT_B, 30), fill=ink)
    d.text((56, 92), "MAINTENANCE PAYMENT", font=ImageFont.truetype(FONT_B, 22), fill=ink)

    yy = y_name
    for line in name_lines:
        d.text((56, yy), line, font=f_name, fill="#14171C")
        yy += int(size * 1.18)
    yy = y_units
    for line in unit_lines:
        d.text((56, yy), line, font=f_u, fill="#5B7488")
        yy += 34

    d.rounded_rectangle([46, top, W - 46, top + 168], 22, fill=wash)
    d.text((78, top + 26), "AMOUNT TO PAY", font=ImageFont.truetype(FONT_B, 23), fill=ink)
    d.text((74, top + 62), rupees(o["b"]), font=ImageFont.truetype(FONT_B, 88), fill=ink)

    qx = (W - side) // 2
    d.rounded_rectangle([qx - 16, qy - 16, qx + side + 16, qy + side + 16], 20,
                        fill="#FFFFFF", outline="#E6EBF2", width=2)
    for r in range(mods):
        for c in range(mods):
            if qr_matrix[r][c]:
                x = qx + (c + 3) * scale
                ty = qy + (r + 3) * scale
                d.rectangle([x, ty, x + scale - 1, ty + scale - 1], fill="#000000")

    f_s = ImageFont.truetype(FONT_B, 27)
    d.text(((W - d.textlength("SCAN WITH ANY UPI APP", font=f_s)) / 2, cy),
           "SCAN WITH ANY UPI APP", font=f_s, fill="#14171C")
    f_v = ImageFont.truetype(FONT_R, 25)
    d.text(((W - d.textlength(PAY["upi"], font=f_v)) / 2, cy + 40), PAY["upi"],
           font=f_v, fill="#5B7488")
    f_t = ImageFont.truetype(FONT_R, 21)
    note = "The amount is already filled in"
    d.text(((W - d.textlength(note, font=f_t)) / 2, cy + 78), note, font=f_t, fill="#8A9099")

    d.line([56, HT - 84, W - 56, HT - 84], fill="#EDF2F7", width=2)
    d.text((56, HT - 64), "AJANTA SERVICES ASSOCIATION",
           font=ImageFont.truetype(FONT_B, 22), fill="#5B7488")
    d.text((56, HT - 34), (BASE or "").replace("https://", ""),
           font=ImageFont.truetype(FONT_B, 20), fill="#9AA3B0")
    im.save(path, optimize=True)
    return (qx - 16, qy - 16, qx + side + 16, qy + side + 16)


def owner_page(key, o):
    ink, wash, label = PAGE_TONE[band_of(o)][0], PAGE_TONE[band_of(o)][1], PAGE_TONE[band_of(o)][2]
    pct = 0 if o["dm"] <= 0 else max(0, min(100, round(o["p"] / o["dm"] * 100)))
    TOWER = "\u0905\u091c\u0902\u0924\u093e \u091f\u093e\u0935\u0930"

    if o["b"] > 0:
        title = "%s \u2014 %s \u092c\u093e\u0915\u0940 \u00b7 %s" % (o["n"], rupees(o["b"]), TOWER)
        desc = ("\u092c\u093f\u0932 %s \u00b7 \u091c\u092e\u093e %s \u00b7 \u092c\u0915\u093e\u092f\u093e %s\u0964 "
                "\u092f\u0939 \u092a\u0948\u0938\u093e \u0906\u092a\u0915\u0940 \u0905\u092a\u0928\u0940 \u0938\u0902\u092a\u0924\u094d\u0924\u093f \u0915\u0947 \u0930\u0916\u0930\u0916\u093e\u0935 \u0915\u093e \u0916\u0930\u094d\u091a \u0939\u0948\u0964"
                % (rupees(o["dm"]), rupees(o["p"]), rupees(o["b"])))
        duelabel, due = "\u0905\u092d\u0940 \u0926\u0947\u0928\u093e \u0939\u0948", rupees(o["b"])
        qr = ownerpage.QR_BLOCK.format(
            base=BASE, key=key, due=rupees(o["b"]),
            down=ownerpage.ICON_DOWN, share=ownerpage.ICON_SHARE,
            sharetitle=H.escape("%s \u00b7 %s" % (TOWER, o["n"])),
            sharetext=H.escape("%s \u0915\u093e \u0930\u0916\u0930\u0916\u093e\u0935 \u2014 \u092c\u0915\u093e\u092f\u093e %s" % (TOWER, rupees(o["b"]))))
    else:
        title = "%s \u2014 \u092a\u0942\u0930\u093e \u092d\u0941\u0917\u0924\u093e\u0928 \u00b7 %s" % (o["n"], TOWER)
        desc = ("\u092c\u093f\u0932 %s \u00b7 \u091c\u092e\u093e %s \u00b7 \u0915\u094b\u0908 \u092c\u0915\u093e\u092f\u093e \u0928\u0939\u0940\u0902\u0964"
                % (rupees(o["dm"]), rupees(o["p"])))
        duelabel, due, qr = "\u092c\u0915\u093e\u092f\u093e", "\u0936\u0942\u0928\u094d\u092f", ""

    rows = []
    for qkey, qlabel, qdate, _my in QUARTERS:
        nice = qlabel.title().replace(" To ", " \u0938\u0947 ")
        rows.append(ownerpage.BILL_ROW.format(
            label=H.escape(nice),
            url=BASE + "/o/bill-" + str(key) + "-" + qkey + ".pdf",
            fname="ajanta-bill-%s-%s.pdf" % (key, qkey),
            title=H.escape("%s \u00b7 %s \u00b7 %s" % (TOWER, o["n"], nice)),
            down=ownerpage.ICON_DOWN, share=ownerpage.ICON_SHARE))
    bills = ownerpage.BILLS_BLOCK.format(rows="".join(rows), count=len(rows)) if rows else ""

    return ownerpage.PAGE.format(
        css=ownerpage.CSS, js=ownerpage.JS,
        title=H.escape(title), desc=H.escape(desc), base=BASE, key=key,
        wash=wash, ink=ink, label=H.escape(label),
        name=H.escape(o["n"]), units=H.escape(o["u"] or ""),
        billed=rupees(o["dm"]), paid=rupees(o["p"]), pct=pct,
        duelabel=duelabel, due=due, qr=qr, bills=bills,
        upi=PAY["upi"], bank=PAY["bank"] + " \u00b7 Alambagh, Lucknow",
        ac=PAY["ac"], ifsc=PAY["ifsc"])


def main():
    data = json.load(open(os.path.join(ROOT, "data", "slim.json"), encoding="utf-8"))
    own  = data["own"]

    # Per-shop super areas for the 3D payment tower. Areas only, from the master
    # sheet via shoparea.py; ownership always comes from the register (slim.json).
    sa = {}
    for k, a in SHOP_AREA.items():
        fl, unit = k.split("-", 1)
        sa.setdefault(fl, {})[unit] = a
    data["sa"] = sa
    # and the carpet areas beside them - the tower is drawn to carpet, the bill
    # is still worked out on super area, and a shop panel can show both
    data["ca"] = CARPET

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

    for name in ("story.html", "tower.html", "film.html", "howto.html", "upi-test.html", "upi-test2.html"):
        src = os.path.join(ROOT, "src", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, name))

    front_image(data["totals"], own, os.path.join(OUT, "preview.png"))

    billable = sorted((k for k, o in own.items() if inv.parse_units(o["u"])), key=lambda k: int(k))
    for q in QUARTERS:
        SERIALS[q[0]] = {k: i + 1 for i, k in enumerate(billable)}

    made_qr = 0
    made_inv = 0
    CFG_RATE = int(data.get("cfg", {}).get("rate", 4))
    for key, o in own.items():
        open(os.path.join(OUT, "o", "%s.html" % key), "w", encoding="utf-8").write(owner_page(key, o))
        owner_image(key, o, os.path.join(OUT, "o", "%s.png" % key))
        # each owner who still owes gets a QR with their own amount already in it.
        # Every one is decoded again before it ships - a QR nobody can read is worse
        # than no QR at all.
        if o["b"] > 0:
            unit = re.sub(r"\s*\([^)]*\)", "", (o["u"] or "").split("\u00b7")[0]).strip()
            note = re.sub(r"[^A-Za-z0-9 ]+", " ", "Maintenance " + unit)
            note = re.sub(r"\s+", " ", note).strip()[:30]
            s = ("upi://pay?pa=" + quote(PAY["upi"]) +
                 "&pn=" + quote("Ajanta Services Association") +
                 "&cu=INR&am=" + str(int(o["b"])) + "&tn=" + quote(note))
            mat, ver, mask = qrlib.encode(s, "M")
            path = os.path.join(OUT, "o", "qr-%s.png" % key)
            qrlib.to_png(mat, path, scale=6, quiet=3)
            if qrlib.decode(qrlib.matrix_from_png(path)) != s:
                raise SystemExit("QR for owner %s does not read back correctly" % key)
            cardpath = os.path.join(OUT, "o", "qrcard-%s.png" % key)
            box = qr_card(key, o, mat, cardpath)
            # the card carries other dark shapes, so crop to the QR before reading it
            crop = os.path.join(OUT, "o", "_check.png")
            Image.open(cardpath).crop(box).save(crop)
            if qrlib.decode(qrlib.matrix_from_png(crop)) != s:
                raise SystemExit("QR card for owner %s does not read back correctly" % key)
            os.remove(crop)
            made_qr += 1

        # a quarterly invoice per owner, in the association's own format.
        # The invoice number comes from the register when it is known there;
        # otherwise it falls back to a quarter-and-shop reference.
        units = per_shop_units(o) or inv.parse_units(o["u"])
        if units:
            for qkey, qlabel, qdate, _my in QUARTERS:
                num = (o.get("inv") or {}).get(qkey) or invoice_no(qkey, key)
                inv.build(os.path.join(OUT, "o", "bill-%s-%s.pdf" % (key, qkey)),
                          inv_no=num, inv_date=qdate,
                          buyer=o["n"], buyer_addr="AJANTA TOWER, LUCKNOW",
                          units=units, rate=CFG_RATE, months=3, year=2026,
                          quarter_label=qlabel)
            made_inv += len(QUARTERS)
    print("  %d payment QRs written and each one decoded again" % made_qr)
    print("  %d quarterly invoices written" % made_inv)

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
