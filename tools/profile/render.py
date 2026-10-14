"""Renders the profile README's SVG slices into assets/.

Every slice is part of one continuous console frame. Run fetch.py first to refresh
data/*.json; this script only reads those files and draws.
"""
import base64, datetime, hashlib, html, io, json, math, pathlib, re, textwrap

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
OUT = ROOT / "assets"
FONT_DIR = HERE / "fonts"
PURPLE, PINK, GREEN = "#a855f7", "#ec4899", "#3fb950"
CYAN, MAGENTA = PURPLE, PINK   # keep internal aliases so shared helpers work unchanged
W, M = 880, 16
FL, FR = M, W - M
X = 52
e = html.escape


def visible(markup):
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def faces(text, weights=(400, 700)):
    text += "0123456789"
    out = []
    for w in weights:
        f = TTFont(FONT_DIR / f"jetbrains-mono-latin-{w}-normal.woff2", recalcTimestamp=False)
        o = subset.Options(); o.flavor = "woff2"; o.layout_features = []
        s = subset.Subsetter(o); s.populate(text=text); s.subset(f)
        b = io.BytesIO(); f.flavor = "woff2"; f.save(b)
        out.append(f"@font-face{{font-family:'JBM';font-weight:{w};src:url(data:font/woff2;base64,"
                   f"{base64.b64encode(b.getvalue()).decode()}) format('woff2')}}")
    return "".join(out)


BASE_CSS = f"""text{{font-family:'JBM',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px}}
.dim{{fill:#8b949e}}.cy{{fill:{PURPLE}}}.fg{{fill:#c9d1d9}}.gr{{fill:{GREEN}}}.wh{{fill:#f0fbff}}.pk{{fill:{PINK}}}
@keyframes fadein{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.ln{{animation:fadein .35s ease-out both}}
.cursor{{animation:blink 1.05s step-end infinite}}
.dot{{animation:pulse 2s ease-in-out infinite}}"""

DEFS = f"""<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{PURPLE}" stroke-opacity=".06"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="g" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>"""


def slice_svg(h, body, *, title, desc, text, top=False, bottom=False, css="", defs="", weights=(400, 700)):
    assert h % 40 == 0, h
    y0 = M if top else 0
    y1 = h - M if bottom else h
    rails = f"M{FL} {y0}V{y1}M{FR} {y0}V{y1}"
    if top:
        rails += f"M{FL} {y0}H{FR}"
    if bottom:
        rails += f"M{FL} {y1}H{FR}"
    gy0 = y0 if top else -40
    gy1 = y1 if bottom else h + 40
    glow = f"M{FL} {gy0}V{gy1}M{FR} {gy0}V{gy1}" + (f"M{FL} {y0}H{FR}" if top else "") + (f"M{FL} {y1}H{FR}" if bottom else "")
    corners = ""
    if top:
        corners += f'<path d="M{FL-7} {y0+18}V{y0-7}H{FL+18}"/><path d="M{FR-18} {y0-7}H{FR+7}V{y0+18}"/>'
    if bottom:
        corners += f'<path d="M{FL-7} {y1-18}V{y1+7}H{FL+18}"/><path d="M{FR-18} {y1+7}H{FR+7}V{y1-18}"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(title)}</title>
<desc id="d">{e(desc)}</desc>
<style>
{faces(text + visible(body), weights)}
{BASE_CSS}
{css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
{DEFS}
{defs}
</defs>
<path d="{glow}" fill="none" stroke="{PURPLE}" stroke-width="3" opacity=".55" filter="url(#glow)"/>
<rect x="{FL}" y="{y0}" width="{FR-FL}" height="{y1-y0}" fill="#03040a"/>
<rect x="{FL}" y="{y0}" width="{FR-FL}" height="{y1-y0}" fill="url(#grid)"/>
{body}
<path d="{rails}" fill="none" stroke="{PURPLE}" stroke-width="1.2"/>
<g fill="none" stroke="{PURPLE}" stroke-width="2">{corners}</g>
</svg>
'''


def heading(y, name, counter):
    return f'''<text x="{X}" y="{y}" font-weight="700" fill="{PURPLE}" filter="url(#g)" opacity=".8" style="font-size:20px">~/</text>
<text x="{X}" y="{y}" font-weight="700" style="font-size:20px"><tspan class="cy">~/</tspan><tspan class="wh">{e(name)}</tspan></text>
<text x="{FR-36}" y="{y}" text-anchor="end" letter-spacing="2" fill="#6e7681" style="font-size:12px">{e(counter)}</text>
<line x1="{X}" y1="{y+14}" x2="{FR-36}" y2="{y+14}" stroke="{PURPLE}" stroke-opacity=".4"/>
<line x1="{X}" y1="{y+14}" x2="{X+120}" y2="{y+14}" stroke="{PURPLE}" stroke-width="2"/>
<line x1="{X}" y1="{y+14}" x2="{X+120}" y2="{y+14}" stroke="{PURPLE}" stroke-width="3" filter="url(#g)"/>'''


def stagger(rows, y0, lh, delay0=0.15, step=0.12):
    out, y, i = [], y0, 0
    for r in rows:
        if r is None:
            y += 14; continue
        i += 1
        out.append(f'<g class="ln" style="animation-delay:{delay0 + i*step:.2f}s">' + r.replace("{y}", str(y)) + "</g>")
        y += lh
    return "\n".join(out), y


def up40(v):
    return int(math.ceil(v / 40) * 40)


# ─────────────────────────────── header ───────────────────────────────
def build_header():
    bar_left = "● ● ●"
    bar_right = "CONNECTED"
    name = "AUDREY KITIO"
    h = 480
    css = f"""@keyframes type{{from{{width:0}}}}
@keyframes flicker{{0%{{opacity:0}}10%{{opacity:1}}14%{{opacity:.2}}22%{{opacity:1}}30%{{opacity:.4}}40%,100%{{opacity:1}}}}
@keyframes gm{{0%,92%,100%{{transform:translate(0,0)}}93%{{transform:translate(5px,-1px)}}95%{{transform:translate(-3px,1px)}}97%{{transform:translate(2px,0)}}}}
@keyframes gc{{0%,92%,100%{{transform:translate(0,0)}}93%{{transform:translate(-5px,1px)}}95%{{transform:translate(4px,-1px)}}97%{{transform:translate(-2px,0)}}}}
.typing{{animation:type .7s steps(8) .3s both}}
.name{{animation:flicker .9s linear 1.3s both}}
.gm{{animation:gm 6s linear 2.2s infinite}}.gc{{animation:gc 6s linear 2.2s infinite}}"""
    defs = f"""<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity=".2"/></pattern>
<filter id="tglow" x="-5%" y="-40%" width="110%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="sglow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>
<clipPath id="typeclip"><rect class="typing" x="{X}" y="246" width="140" height="26"/></clipPath>"""
    # dot before CONNECTED label
    conn_x = FR - 20 - len(bar_right) * 8.2 - 24
    # meterpreter lines — staggered fadein
    meta_rows = [
        f'<text x="{X}" y="{{y}}" class="dim"><tspan class="gr">[*]</tspan> Sending stage (175174 bytes) to 192.168.1.105</text>',
        f'<text x="{X}" y="{{y}}" class="dim"><tspan class="gr">[*]</tspan> Meterpreter session 1 opened (10.10.14.5:4444 -&gt;</text>',
        f'<text x="{X+28}" y="{{y}}" class="dim">192.168.1.105:53422) at 2049-03-17 03:17:42 +0000</text>',
        None,
        f'<text x="{X}" y="{{y}}" class="fg"><tspan class="cy">meterpreter</tspan> &gt; sysinfo</text>',
        f'<text x="{X}" y="{{y}}" class="dim">Computer    : <tspan class="fg">AUDREY-KITIO</tspan></text>',
        f'<text x="{X}" y="{{y}}" class="dim">OS          : Linux 6.5.0-generic (x86_64)</text>',
        None,
        f'<text x="{X}" y="{{y}}" class="gr" font-weight="700">[+] ACCESS GRANTED :: Target compromised successfully.</text>',
    ]
    meta_svg, y_after_meta = stagger(meta_rows, 80, 22, delay0=0.2, step=0.15)
    # description lines after whoami + name
    desc_rows = [
        f'<text x="{X}" y="{{y}}" class="fg"><tspan class="cy">&gt;&gt;</tspan> &#201;tudiante Ing&#233;nieure Cloud &amp; Cybers&#233;curit&#233;</text>',
        f'<text x="{X}" y="{{y}}" class="fg"><tspan class="cy">&gt;&gt;</tspan> &#171;&#160;Je construis les architectures, je les attaque et j&#39;apprends &#224; les d&#233;fendre.&#160;&#187;</text>',
        f'<text x="{X}" y="{{y}}" class="fg"><tspan class="cy">&gt;&gt;</tspan> Double-dipl&#244;me&#160;: EFREI Paris &#215; Institut Universitaire Saint Jean</text>',
    ]
    desc_svg, _ = stagger(desc_rows, 350, 24, delay0=2.0, step=0.25)
    body = f'''<rect x="{FL}" y="{M}" width="{FR-FL}" height="34" fill="{PURPLE}" fill-opacity=".08"/>
<line x1="{FL}" y1="{M+34}" x2="{FR}" y2="{M+34}" stroke="{PURPLE}" stroke-opacity=".5"/>
<text x="{FL+16}" y="{M+22}" letter-spacing="2" class="cy" style="font-size:13px">{e(bar_left)}</text>
<text x="{FR-20}" y="{M+22}" letter-spacing="1" class="dim" text-anchor="end" style="font-size:12px">{e(bar_right)}</text>
<circle class="dot" cx="{conn_x}" cy="{M+18}" r="4" fill="{GREEN}"/>
<circle class="dot" cx="{conn_x}" cy="{M+18}" r="4" fill="{GREEN}" filter="url(#sglow)"/>
{meta_svg}
<g clip-path="url(#typeclip)"><text x="{X}" y="268" class="dim"><tspan class="gr">$</tspan> whoami</text></g>
<g class="name" font-weight="800" letter-spacing="2" style="font-size:44px">
<text x="{X}" y="322" fill="{PURPLE}" opacity=".55" filter="url(#tglow)" style="font-size:44px">{name}</text>
<g class="gm"><text x="{X+3}" y="322" fill="{PINK}" opacity=".75" style="font-size:44px">{name}</text></g>
<g class="gc"><text x="{X-3}" y="322" fill="{PURPLE}" opacity=".85" style="font-size:44px">{name}</text></g>
<text x="{X}" y="322" fill="#f0fbff" style="font-size:44px">{name}</text>
</g>
{desc_svg}
<g class="ln" style="animation-delay:3.2s">
<text x="{X}" y="430" class="gr">$</text>
<rect class="cursor" x="{X+18}" y="417" width="10" height="17" fill="{PURPLE}"/>
<rect class="cursor" x="{X+18}" y="417" width="10" height="17" fill="{PURPLE}" filter="url(#sglow)"/>
</g>
<rect x="{FL}" y="{M+35}" width="{FR-FL}" height="{h-M-35}" fill="url(#scan)"/>'''
    text = (bar_left + bar_right + name
            + "[*] Sending stage bytes to Meterpreter session opened at"
            + "Computer AUDREY-KITIO OS Linux 6.5.0-generic x86_64"
            + "[+] ACCESS GRANTED Target compromised successfully"
            + "$ whoami >> Etudiante Ingenieure Cloud Cybersecurite"
            + "Je construis les architectures je les attaque et j apprends a les defendre"
            + "Double-diplome EFREI Paris Institut Universitaire Saint Jean"
            + "192.168.1.105:53422 2049-03-17 03:17:42 +0000 10.10.14.5:4444")
    return slice_svg(h, body, title="Audrey Kitio",
                     desc="Etudiante Ingenieure Cloud et Cybersecurite. "
                          "Double-diplome EFREI Paris et Institut Universitaire Saint Jean.",
                     text=text, top=True, css=css, defs=defs, weights=(400, 700, 800))


# ─────────────────────────────── footer ───────────────────────────────
def build_footer():
    h = 200
    bar_right = "DISCONNECTED"
    disc_x = FR - 20 - len(bar_right) * 8.2 - 24
    # exit sequence
    exit_rows = [
        f'<text x="{X}" y="{{y}}" class="dim"><tspan class="gr">you@kali:~$</tspan> exit</text>',
        f'<text x="{X}" y="{{y}}" class="dim">logout</text>',
        f'<text x="{X}" y="{{y}}" class="dim">Connection to <tspan class="cy">192.168.1.105</tspan> closed.</text>',
        f'<text x="{X}" y="{{y}}" class="dim"><tspan class="gr">[*]</tspan> Session terminated by user.</text>',
        f'<text x="{X}" y="{{y}}" class="dim"><tspan class="gr">[*]</tspan> Cleanup complete. Logs wiped.</text>',
    ]
    exit_svg, y_end = stagger(exit_rows, 36, 22, delay0=0.1, step=0.12)
    # divider and tagline
    cx = (FL + FR) // 2
    tagline = "BUILD . EXPLOIT . DEFEND . STAY VIGILANT"
    tw = len(tagline) * 8.1
    lx1, lx2 = X, cx - tw // 2 - 16
    rx1, rx2 = cx + tw // 2 + 16, FR - 36
    body = f'''{exit_svg}
<g class="ln" style="animation-delay:.9s">
<line x1="{lx1}" y1="{y_end+10}" x2="{lx2:.0f}" y2="{y_end+10}" stroke="{PURPLE}" stroke-opacity=".4"/>
<text x="{cx}" y="{y_end+14}" text-anchor="middle" letter-spacing="2" fill="{PURPLE}" style="font-size:11px">{e(tagline)}</text>
<line x1="{rx1:.0f}" y1="{y_end+10}" x2="{rx2}" y2="{y_end+10}" stroke="{PURPLE}" stroke-opacity=".4"/>
</g>
<rect x="{FL}" y="{h-M-34}" width="{FR-FL}" height="34" fill="{PURPLE}" fill-opacity=".08"/>
<line x1="{FL}" y1="{h-M-34}" x2="{FR}" y2="{h-M-34}" stroke="{PURPLE}" stroke-opacity=".5"/>
<text x="{FL+16}" y="{h-M-12}" letter-spacing="2" class="cy" style="font-size:13px">&#9679; &#9679; &#9679;</text>
<text x="{FR-20}" y="{h-M-12}" letter-spacing="1" class="dim" text-anchor="end" style="font-size:12px">{e(bar_right)}</text>
<circle cx="{disc_x}" cy="{h-M-18}" r="4" fill="#484f58"/>'''
    text = ("you@kali:~$ exit logout Connection to 192.168.1.105 closed."
            + "[*] Session terminated by user Cleanup complete Logs wiped"
            + tagline + bar_right + "● ● ●")
    return slice_svg(h, body, title="End of profile", desc="Connection closed. Session terminated.",
                     text=text, bottom=True)


# ────────────────────────────── projects ──────────────────────────────
HW = W // 2


def half_slice(h, side, body, *, title, desc, text, weights=(400, 700)):
    assert h % 40 == 0
    rx = FL if side == "L" else HW - M
    bx0, bx1 = (FL, HW) if side == "L" else (0, HW - M)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{HW}" height="{h}" viewBox="0 0 {HW} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(title)}</title>
<desc id="d">{e(desc)}</desc>
<style>
{faces(text + visible(body), weights)}
{BASE_CSS}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
{DEFS}
</defs>
<path d="M{rx} -40V{h+40}" fill="none" stroke="{PURPLE}" stroke-width="3" opacity=".55" filter="url(#glow)"/>
<rect x="{bx0}" y="0" width="{bx1-bx0}" height="{h}" fill="#03040a"/>
<rect x="{bx0}" y="0" width="{bx1-bx0}" height="{h}" fill="url(#grid)"/>
{body}
<path d="M{rx} 0V{h}" fill="none" stroke="{PURPLE}" stroke-width="1.2"/>
</svg>
'''


PROJECTS = [
    dict(slug="bgp-peering", name="BGP Dual-Upstream Peering",
         url="https://github.com/NekoKits1/Optimisation-Routage-BGP-pour-peering-FAI-CDN",
         tag="NETWORK ENGINEERING", tagc=PURPLE,
         desc="BGP dual-upstream pour operateur telecom. BFD failover <30s, HQoS, local-pref, AS-path prepending. Simulation EVE-NG."),
    dict(slug="localstack", name="Cloud-simul-avec-localstack",
         url="https://github.com/NekoKits1/Cloud-simul-avec-localstack",
         tag="CLOUD ARCHITECTURE", tagc=PURPLE,
         desc="Pipeline serverless S3 > Lambda > DynamoDB conteneurise sous Docker. Architecture AWS locale sans compte reel."),
    dict(slug="reverse-shell", name="Reverse-Shell-Python-TCP",
         url="https://github.com/NekoKits1/reverse-shell-python-tcp",
         tag="OFFENSIVE SECURITY", tagc=PINK,
         desc="Reverse shell TCP en Python. Persistance Registry Run Key. Detection cote defense : Sysmon + MITRE ATT&CK."),
]
CARD_H = 200


def build_projects_head():
    h = 120
    body = heading(44, "projets", "// ls") + f'''
<g class="ln" style="animation-delay:.2s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> ls -l ~/projets</text></g>'''
    return slice_svg(h, body, title="Projets", desc="Projets techniques", text="~/projets// ls$ ls -l")


def build_card(p, side, delay):
    x0 = 52 if side == "L" else 10
    cw, y0, ch = 378, 12, 176
    pad = 18
    tx = x0 + pad
    cut = 16
    box = f"M{x0} {y0}H{x0+cw-cut}L{x0+cw} {y0+cut}V{y0+ch}H{x0+cut}L{x0} {y0+ch-cut}Z"
    # wrap desc at 43 chars
    raw_desc = p["desc"]
    lines = textwrap.wrap(raw_desc, 43)
    lines = lines[:3]
    tag_w = len(p["tag"]) * 7.6 + 16
    title_w = len(p["name"]) * 10.2
    desc_svg = "\n".join(f'<text x="{tx}" y="{100 + i*20}" class="fg" style="font-size:13px">{e(l)}</text>'
                         for i, l in enumerate(lines))
    body = f'''<g class="ln" style="animation-delay:{delay:.2f}s">
<path d="{box}" fill="{PURPLE}" fill-opacity=".035"/>
<path d="{box}" fill="none" stroke="{PURPLE}" stroke-opacity=".4"/>
<path d="M{x0+cw-cut} {y0}L{x0+cw} {y0+cut}" stroke="{PURPLE}" stroke-width="2"/>
<text x="{tx}" y="{y0+34}" font-weight="700" fill="{PURPLE}" filter="url(#g)" opacity=".6" style="font-size:17px">{e(p["name"])}</text>
<text x="{tx}" y="{y0+34}" font-weight="700" class="cy" style="font-size:17px">{e(p["name"])}</text>
<path d="M{tx+title_w+11} {y0+31}l8-8M{tx+title_w+13} {y0+23}h6v6" fill="none" stroke="{PURPLE}" stroke-width="1.6"/>
<rect x="{tx}" y="{y0+46}" width="{tag_w}" height="18" fill="none" stroke="{p["tagc"]}" stroke-opacity=".8"/>
<text x="{tx+8}" y="{y0+59}" letter-spacing="1" fill="{p["tagc"]}" style="font-size:11px">{e(p["tag"])}</text>
{desc_svg}
<text x="{tx}" y="{y0+158}" class="dim" style="font-size:12px">github.com/NekoKits1</text>
</g>'''
    text = p["name"] + p["tag"] + raw_desc + "github.com/NekoKits1"
    return half_slice(CARD_H, side, body, title=p["name"],
                      desc=f'{p["name"]}: {raw_desc}', text=text)


def build_card_full(p, delay):
    """Full-width card for the third project (alone on its row)."""
    x0, y0 = 52, 12
    cw, ch = 776, 176
    pad, cut = 18, 16
    tx = x0 + pad
    box = f"M{x0} {y0}H{x0+cw-cut}L{x0+cw} {y0+cut}V{y0+ch}H{x0+cut}L{x0} {y0+ch-cut}Z"
    raw_desc = p["desc"]
    lines = textwrap.wrap(raw_desc, 90)
    lines = lines[:2]
    tag_w = len(p["tag"]) * 7.6 + 16
    title_w = len(p["name"]) * 10.2
    desc_svg = "\n".join(f'<text x="{tx}" y="{100 + i*20}" class="fg" style="font-size:13px">{e(l)}</text>'
                         for i, l in enumerate(lines))
    body = f'''<g class="ln" style="animation-delay:{delay:.2f}s">
<path d="{box}" fill="{PINK}" fill-opacity=".025"/>
<path d="{box}" fill="none" stroke="{PINK}" stroke-opacity=".5"/>
<path d="M{x0+cw-cut} {y0}L{x0+cw} {y0+cut}" stroke="{PINK}" stroke-width="2"/>
<text x="{tx}" y="{y0+34}" font-weight="700" fill="{PINK}" filter="url(#g)" opacity=".6" style="font-size:17px">{e(p["name"])}</text>
<text x="{tx}" y="{y0+34}" font-weight="700" class="pk" style="font-size:17px">{e(p["name"])}</text>
<path d="M{tx+title_w+11} {y0+31}l8-8M{tx+title_w+13} {y0+23}h6v6" fill="none" stroke="{PINK}" stroke-width="1.6"/>
<rect x="{tx}" y="{y0+46}" width="{tag_w}" height="18" fill="none" stroke="{p["tagc"]}" stroke-opacity=".8"/>
<text x="{tx+8}" y="{y0+59}" letter-spacing="1" fill="{p["tagc"]}" style="font-size:11px">{e(p["tag"])}</text>
{desc_svg}
<text x="{tx}" y="{y0+158}" class="dim" style="font-size:12px">github.com/NekoKits1</text>
<text x="{x0+cw-pad}" y="{y0+158}" text-anchor="end" class="dim" style="font-size:12px">(Le projet qui a permis cette connexion !)</text>
</g>'''
    text = p["name"] + p["tag"] + raw_desc + "github.com/NekoKits1 Le projet qui a permis cette connexion"
    return slice_svg(CARD_H, body, title=p["name"], desc=f'{p["name"]}: {raw_desc}', text=text)


# ─────────────────────────────── stack ────────────────────────────────
STACK = [
    ("cloud & devops", ["AWS", "Docker", "Terraform", "LocalStack", "Ansible"]),
    ("networking & security", ["Cisco IOS", "BGP (i/eBGP)", "OSPF", "EVE-NG", "Wireshark"]),
    ("systems & virtualization", ["Linux (Ubuntu/Kali)", "Windows Server", "VMware"]),
    ("programming & scripting", ["Python", "Bash", "Java"]),
]


def build_stack():
    parts = [heading(44, "stack", "// scan"),
             f'<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> scan --loadout --top-level</text></g>']
    y, rowh = 126, 44
    cw = 0.6 * 13
    for r, (cat, items) in enumerate(STACK):
        parts.append(f'<g class="ln" style="animation-delay:{.25 + r*.1:.2f}s">')
        parts.append(f'<text x="{X}" y="{y+20}" class="dim" style="font-size:13px">{e(cat)}</text>')
        parts.append(f'<text x="{X+180}" y="{y+20}" class="cy" style="font-size:13px">&#8250;</text>')
        x = X + 200
        for it in items:
            w = len(it) * cw + 26
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" fill="{PURPLE}" fill-opacity=".06" stroke="{PURPLE}" stroke-opacity=".55"/>')
            parts.append(f'<path d="M{x:.1f} {y+8}V{y}H{x+8:.1f}" fill="none" stroke="{PURPLE}" stroke-width="2"/>')
            parts.append(f'<text x="{x+13:.1f}" y="{y+20}" font-weight="700" class="cy" style="font-size:13px">{e(it)}</text>')
            x += w + 10
        parts.append("</g>")
        y += rowh
    h = up40(y + 10)
    text = "~/stack// scan$ scan --loadout --top-level>" + "".join(c + "".join(i) for c, i in STACK)
    desc = "Tech stack. " + " ".join(f"{c}: {', '.join(i)}." for c, i in STACK)
    return slice_svg(h, "\n".join(parts), title="Tech stack", desc=desc, text=text)


# ──────────────────────────────── links ───────────────────────────────
LINKS = [
    ("linkedin", "LinkedIn", "linkedin.com/in/audreykarellekitio", "https://www.linkedin.com/in/audreykarellekitio/"),
    ("email", "Email", "audreykarellekits@gmail.com", "mailto:audreykarellekits@gmail.com"),
]
ICONS = json.load(open(HERE / "icons.json"))
SEG = W // len(LINKS)   # 440 px per button
BTN_W, BTN_GAP = 190, 60


def icon_markup(key, x, y, size=18):
    if key == "linkedin":
        return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{PURPLE}"/>'
                f'<text x="{x + size/2}" y="{y + size - 4.5}" text-anchor="middle" font-weight="700" fill="#03040a" style="font-size:12px">in</text>')
    if key == "email":
        # simple envelope
        s = size
        return (f'<rect x="{x}" y="{y+2}" width="{s}" height="{s-4}" rx="2" fill="none" stroke="{PURPLE}" stroke-width="1.5"/>'
                f'<path d="M{x} {y+2}l{s/2} {(s-4)*0.5}l{s/2} {-(s-4)*0.5}" fill="none" stroke="{PURPLE}" stroke-width="1.5"/>')
    d = ICONS.get(key, "")
    return f'<path transform="translate({x} {y}) scale({size/24})" d="{d}" fill="{PURPLE}"/>'


def build_links_head():
    body = heading(44, "connexions", "// ping") + f'''
<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> ping audrey --all-channels</text></g>'''
    return slice_svg(120, body, title="Connexions", desc="Comment me contacter",
                     text="~/connexions// ping$ ping audrey --all-channels")


def build_link_button(k):
    key, label, handle, url = LINKS[k]
    h = 80
    x0 = SEG * k
    lx = X + k * (BTN_W + BTN_GAP) - x0
    first, last = k == 0, k == len(LINKS) - 1
    bg0 = FL - x0 if first else 0
    bg1 = FR - x0 if last else SEG
    rails = (f"M{FL - x0} 0V{h}" if first else "") + (f"M{FR - x0} 0V{h}" if last else "")
    glow = (f"M{FL - x0} -40V{h+40}" if first else "") + (f"M{FR - x0} -40V{h+40}" if last else "")
    by, bh, cut = 12, 56, 12
    box = f"M{lx} {by}H{lx+BTN_W-cut}L{lx+BTN_W} {by+cut}V{by+bh}H{lx}Z"
    text = label + "in"
    # vertically center the label+icon in the box since there's no subtitle line
    icy = by + (bh - 18) // 2  # icon top
    ty  = icy + 14              # text baseline ≈ icon mid
    body = f'''<g class="ln" style="animation-delay:{.25 + k*.12:.2f}s">
<path d="{box}" fill="{PURPLE}" fill-opacity=".05"/>
<path d="{box}" fill="none" stroke="{PURPLE}" stroke-opacity=".55"/>
<path d="M{lx+BTN_W-cut} {by}L{lx+BTN_W} {by+cut}" stroke="{PURPLE}" stroke-width="2"/>
<g filter="url(#g)" opacity=".5">{icon_markup(key, lx+12, icy)}</g>
{icon_markup(key, lx+12, icy)}
<text x="{lx+38}" y="{ty}" font-weight="700" class="cy" style="font-size:14px">{e(label)}</text>
</g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SEG}" height="{h}" viewBox="0 0 {SEG} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(label)}</title>
<desc id="d">{e(label)}: {e(url)}</desc>
<style>
{faces(text + visible(body))}
{BASE_CSS}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
<pattern id="grid" x="{(-x0) % 40}" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{PURPLE}" stroke-opacity=".06"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="g" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
{f'<path d="{glow}" fill="none" stroke="{PURPLE}" stroke-width="3" opacity=".55" filter="url(#glow)"/>' if glow else ""}
<rect x="{bg0}" y="0" width="{bg1-bg0}" height="{h}" fill="#03040a"/>
<rect x="{bg0}" y="0" width="{bg1-bg0}" height="{h}" fill="url(#grid)"/>
{body}
{f'<path d="{rails}" fill="none" stroke="{PURPLE}" stroke-width="1.2"/>' if rails else ""}
</svg>
'''


def write(rel, svg):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)


def main():
    global OUT
    import argparse
    ap = argparse.ArgumentParser(description="Render the profile SVGs from data/stats.json.")
    ap.add_argument("--data", type=pathlib.Path, default=DATA)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    args = ap.parse_args()
    OUT = args.out
    write("header.svg", build_header())
    write("links.svg", build_links_head())
    for k in range(len(LINKS)):
        key = LINKS[k][0]
        write(f"links/{key}.svg", build_link_button(k))
    write("projects.svg", build_projects_head())
    # row 1: BGP (L) + LocalStack (R)
    write(f"card-{PROJECTS[0]['slug']}.svg", build_card(PROJECTS[0], "L", 0.30))
    write(f"card-{PROJECTS[1]['slug']}.svg", build_card(PROJECTS[1], "R", 0.42))
    # row 2: RevShell full-width
    write(f"card-{PROJECTS[2]['slug']}.svg", build_card_full(PROJECTS[2], 0.54))
    write("stack.svg", build_stack())
    write("footer.svg", build_footer())
    print("rendered", len(list(OUT.rglob("*.svg"))), "SVGs into", OUT)


if __name__ == "__main__":
    main()
