"""Motor: filtros ffmpeg, codificacao e analisador de video (sem interface)."""
import subprocess, sys, os, re, threading, tempfile
from pathlib import Path
import numpy as np

EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".mxf", ".wmv"}
HERE = Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent
FFMPEG = str(HERE / "ffmpeg.exe") if (HERE / "ffmpeg.exe").exists() else "ffmpeg"
APP_VERSION = "1.0.0"
# Instalado (o instalador cria installed.flag): saida em Videos\Instagram Quality. Portatil: pasta output ao lado do exe.
OUT = (Path.home() / "Videos" / "Instagram Quality") if (HERE / "installed.flag").exists() else HERE / "output"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DEFAULTS = dict(sharp=0.6, cas=0.0, hp=0.0, hp_r=4.0, contrast=1.0, sat=1.0, bright=0.0, gamma=1.0,
                vib=0.0, hdr=0, denoise=0.0, deband=0, grain=0.0, quality="Equilibrado (~12 Mbps)", fps="30")
PRESETS = {
    "Equilibrado (recomendado)": {},
    "Só converter (sem efeitos)": dict(sharp=0.0),
    "Nítido + cor": dict(sharp=0.7, hp=35, hp_r=3, contrast=1.06, sat=1.08),
    "Máximo detalhe": dict(sharp=0.5, cas=0.4, hp=45, hp_r=3, contrast=1.05, deband=1, grain=2, quality="Alta (~20 Mbps)"),
    "Limpar vídeo ruidoso": dict(denoise=3, sharp=0.6, deband=1),
}
QUALITY = {"Leve (~8 Mbps)": (20, "10M"), "Equilibrado (~12 Mbps)": (18, "16M"), "Alta (~20 Mbps)": (16, "24M")}
HDR = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
       "zscale=t=bt709:m=bt709:r=tv")

SCALE = ("scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease:"
         "force_divisible_by=2:flags=lanczos")


def build_vf(o):
    """Monta a cadeia de filtros do ffmpeg a partir das opcoes (so entra o que foi ligado)."""
    f = [SCALE]
    if o["hdr"]: f.append(HDR)
    if o["denoise"] > 0:
        d = o["denoise"]; f.append(f"hqdn3d={d:.1f}:{d:.1f}:{d*1.5:.1f}:{d*1.5:.1f}")
    if o["deband"]: f.append("deband")
    if (o["contrast"], o["sat"], o["bright"], o["gamma"]) != (1, 1, 0, 1):
        f.append(f"eq=contrast={o['contrast']:.2f}:saturation={o['sat']:.2f}:"
                 f"brightness={o['bright']:.2f}:gamma={o['gamma']:.2f}")
    if o["vib"]: f.append(f"vibrance=intensity={o['vib']:.2f}")
    if o["sharp"] > 0: f.append(f"unsharp=5:5:{o['sharp']:.2f}:5:5:0")
    if o["cas"] > 0: f.append(f"cas=strength={o['cas']:.2f}")
    vf = ",".join(f)
    if o["hp"] > 0:  # high-pass: original - desfoque + 50% cinza, misturado em overlay so na luminancia
        vf += (f",split=3[o1][o2][o3];[o2]gblur=sigma={o['hp_r']:.1f}[bl];"
               f"[o3][bl]blend=all_expr='clip(A-B+128,0,255)'[hp];"
               f"[o1][hp]blend=all_mode=overlay:all_opacity={o['hp']/100:.2f}:c1_opacity=0:c2_opacity=0")
    if o["grain"] > 0: vf += f",noise=alls={o['grain']:.0f}:allf=t"
    return vf + ",format=yuv420p"


def encode_args(o):
    crf, maxr = QUALITY[o["quality"]]
    a = ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "4.2",
         "-crf", str(crf), "-maxrate", maxr, "-bufsize", str(int(maxr[:-1]) * 2) + "M", "-g", "60", "-bf", "2",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart"]
    if o["fps"] != "original": a += ["-fpsmax", o["fps"]]
    return a


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, creationflags=NOWIN, **kw)


def duration(p):
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", run([FFMPEG, "-hide_banner", "-i", str(p)]).stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0


def collect(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from sorted(f for f in p.iterdir() if f.suffix.lower() in EXTS)
        elif p.suffix.lower() in EXTS:
            yield p


# ---------- analisador ----------
def probe(p):
    s = run([FFMPEG, "-hide_banner", "-i", str(p)]).stderr
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", s)
    vl = next((l for l in s.splitlines() if "Video:" in l), "")
    wh = re.search(r"\b(\d{2,5})x(\d{2,5})\b", vl)
    if not wh: raise RuntimeError("Não consegui ler as informações do vídeo.")
    w, h = int(wh[1]), int(wh[2])
    rot = re.search(r"rotation of (-?[\d.]+)", s)
    if rot and abs(float(rot[1])) % 180 == 90: w, h = h, w
    fps = re.search(r"([\d.]+) fps", vl); br = re.search(r"bitrate: (\d+) kb/s", s)
    return dict(dur=int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]) if d else 0, w=w, h=h,
                fps=float(fps[1]) if fps else 30.0, kbps=int(br[1]) if br else 0,
                codec=(re.search(r"Video: (\w+)", vl) or [0, "?"])[1],
                hdr=bool(re.search(r"arib-std-b67|smpte2084", vl)))


def final_size(w, h):
    k = min(1, 1080 / w, 1920 / h)
    return max(2, int(w * k) // 2 * 2), max(2, int(h * k) // 2 * 2)


def frames_at(p, t, W, H, hdr):
    vf = f"scale={W}:{H}:flags=lanczos" + ("," + HDR if hdr else "")
    r = subprocess.run([FFMPEG, "-v", "error", "-ss", str(t), "-i", str(p), "-frames:v", "2", "-vf", vf,
                        "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True, creationflags=NOWIN)
    n = len(r.stdout) // (W * H * 3)
    return np.frombuffer(r.stdout[:n * W * H * 3], np.uint8).reshape(n, H, W, 3)


def metrics(fr):
    f = fr[0].astype(np.float32)
    Y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    mx, mn = f.max(-1), f.min(-1); lit = mx > 40
    L = (Y[:-2, :-2] - 2 * Y[:-2, 1:-1] + Y[:-2, 2:] - 2 * Y[1:-1, :-2] + 4 * Y[1:-1, 1:-1]
         - 2 * Y[1:-1, 2:] + Y[2:, :-2] - 2 * Y[2:, 1:-1] + Y[2:, 2:])
    g = np.maximum(np.abs(Y[:-1, :-1] - Y[:-1, 1:]), np.abs(Y[:-1, :-1] - Y[1:, :-1]))
    p1, p99 = np.percentile(Y, [1, 99])
    m = dict(mean=Y.mean(), spread=p99 - p1, sat=((mx - mn)[lit] / mx[lit]).mean() if lit.any() else 0,
             noise=np.sqrt(np.pi / 2) / 6 * np.abs(L).mean(), g95=np.percentile(g, 95),
             busy=(g > 20).mean(), flat=(g < 1.0).mean(), clip=(Y > 250).mean())
    if len(fr) > 1:
        m["motion"] = np.abs(fr[1].astype(np.float32).mean(-1) - f.mean(-1)).mean()
    r = {k: float(v) for k, v in m.items()}
    r["hist"] = np.histogram(Y, bins=18, range=(0, 256))[0] / Y.size
    return r


def analyze(p):
    """Amostra 6 pontos do video e devolve (ajustes recomendados, relatorio em texto, dados medidos). Heuristicas, nao ciencia exata."""
    inf = probe(p); W, H = final_size(inf["w"], inf["h"])
    ms = []
    for t in (.1, .25, .4, .55, .7, .85):
        fr = frames_at(p, inf["dur"] * t, W, H, inf["hdr"])
        if len(fr): ms.append(metrics(fr))
    if not ms: raise RuntimeError("Não consegui ler frames do vídeo.")
    m = {k: float(np.median([x.get(k, 0) for x in ms])) for k in ms[0] if k != "hist"}
    hist = np.mean([x["hist"] for x in ms], axis=0)
    o, why = dict(DEFAULTS), []
    if inf["hdr"]: o["hdr"] = 1; why.append("Vídeo HDR detectado → converter pra SDR (senão as cores ficam lavadas).")
    if m["g95"] < 18: o.update(sharp=0.9, hp=40, hp_r=3); why.append(f"Imagem macia (nitidez {m['g95']:.0f}) → sharpen forte + high-pass.")
    elif m["g95"] < 35: o.update(sharp=0.6, hp=20, hp_r=3); why.append(f"Nitidez normal ({m['g95']:.0f}) → sharpen moderado + high-pass leve.")
    else: o.update(sharp=0.3); why.append(f"Já bem nítido ({m['g95']:.0f}) → sharpen mínimo, pra não criar halos.")
    if m["noise"] > 3.5: o["denoise"] = 3; o["sharp"] = max(0.3, o["sharp"] - 0.2); why.append(f"Muito ruído ({m['noise']:.1f}) → redução de ruído 3 (sharpen reduzido).")
    elif m["noise"] > 2: o["denoise"] = 1.5; why.append(f"Ruído moderado ({m['noise']:.1f}) → redução de ruído leve.")
    else: why.append(f"Imagem limpa (ruído {m['noise']:.1f}) → sem redução de ruído.")
    if m["mean"] < 80: o["gamma"] = 1.08; why.append(f"Cena escura (brilho {m['mean']:.0f}/255) → gamma 1.08; o Instagram esmaga sombras.")
    elif m["mean"] > 175: o["gamma"] = 0.96; why.append(f"Cena muito clara (brilho {m['mean']:.0f}/255) → gamma 0.96.")
    if m["spread"] < 170: o["contrast"] = 1.10; why.append(f"Contraste baixo (faixa {m['spread']:.0f}) → contraste 1.10.")
    elif m["spread"] < 205: o["contrast"] = 1.05; why.append(f"Contraste médio (faixa {m['spread']:.0f}) → contraste 1.05.")
    if m["sat"] < 0.28: o["sat"] = 1.12; why.append(f"Cores apagadas (sat. {m['sat']:.2f}) → saturação 1.12.")
    elif m["sat"] < 0.40: o["sat"] = 1.06; why.append(f"Cores discretas (sat. {m['sat']:.2f}) → saturação 1.06.")
    if m["flat"] > 0.5:
        o["deband"] = 1; o["grain"] = 2 if m["flat"] > 0.65 else 0
        why.append(f"Muitas áreas lisas ({m['flat']:.0%}) → deband{' + grão leve' if o['grain'] else ''} contra faixas de degradê.")
    if inf["kbps"] and inf["kbps"] < 3000 and inf["w"] * inf["h"] >= 921600:
        o["deband"] = 1; why.append(f"Fonte já muito comprimida ({inf['kbps']/1000:.1f} Mbps) → deband pra suavizar blocos.")
    if m["busy"] > 0.22 or m.get("motion", 0) > 6: o["quality"] = "Alta (~20 Mbps)"; why.append(f"Muito detalhe/movimento (detalhe {m['busy']:.0%}) → bitrate alto.")
    elif m["busy"] < 0.08 and m.get("motion", 0) < 1.5: o["quality"] = "Leve (~8 Mbps)"; why.append("Cena simples e parada → bitrate leve basta.")
    else: why.append("Detalhe médio → bitrate equilibrado.")
    if m["clip"] > 0.02: why.append(f"Aviso: {m['clip']:.0%} da imagem está estourada (branco) — se der, reduza a exposição na edição.")
    head = (f"Original: {inf['w']}x{inf['h']} @ {inf['fps']:.0f} fps, {inf['codec']}, "
            f"{inf['kbps']/1000:.1f} Mbps, {inf['dur']:.0f}s\nSaída: {W}x{H}"
            + (" (não amplia vídeo menor que 1080)" if inf["w"] < 1080 and inf["h"] < 1920 else "")
            + f", máx. 30 fps\nAmostras analisadas: {len(ms)}\n")
    return o, head + "\nRecomendações:\n" + "\n".join("• " + w for w in why), dict(m=m, hist=hist, info=inf, size=(W, H))




NOMINAL = {"Leve (~8 Mbps)": 8, "Equilibrado (~12 Mbps)": 12, "Alta (~20 Mbps)": 20}


def estimate_mb(dur, quality):
    """Tamanho aproximado (nominal, maximo) em MB: video no bitrate-alvo + audio 256k."""
    cap = int(QUALITY[quality][1][:-1])
    return (NOMINAL[quality] + 0.256) * dur / 8, (cap + 0.256) * dur / 8


def apply_intensity(o, k):
    """k=1 deixa como esta; <1 aproxima cada efeito do neutro; >1 exagera (com tetos que o ffmpeg aceita)."""
    if abs(k - 1) < 1e-6: return o
    o = dict(o)
    for key in ("sharp", "cas", "hp", "vib", "denoise", "grain"): o[key] = o[key] * k
    for key, neutro in (("contrast", 1), ("sat", 1), ("gamma", 1), ("bright", 0)): o[key] = neutro + (o[key] - neutro) * k
    o["hp"], o["cas"] = min(100, o["hp"]), min(1, o["cas"])
    return o

