"""Instagram Quality: interface (modo normal compacto + modo avancado detalhado). O motor esta em engine.py."""
import ctypes, json, os, subprocess, sys, tempfile, threading
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import engine as E

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)  # texto nitido em telas com escala
except Exception: pass
try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IQ.InstagramQuality")  # icone proprio na barra de tarefas
except Exception: pass

C = SimpleNamespace(bg="#0f0f0f", panel="#151515", stage="#0a0a0a", line="#262626", sel="#1e1e1e", mute="#8c8c8c",
                    fg="#ececec", acc="#c6f432", on="#10150a", warn="#ffb84d")
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
CFG = Path(os.environ.get("APPDATA", str(Path.home()))) / "InstagramQuality" / "config.json"
S = 1.0  # fator de escala da tela, definido ao criar a janela
FAM = {"": "Segoe UI", "m": "Segoe UI Semibold", "b": "Segoe UI Semibold"}


def px(n): return max(1, int(round(n * S)))
def fnt(size, w=""): return (FAM[w], size)


def load_fonts():
    for f in (BASE / "fonts").glob("*.ttf"):
        try: ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)  # 0x10 = so deste processo
        except Exception: pass
    have = set(tkfont.families())
    if "Poppins" in have:
        FAM.update({"": "Poppins", "m": "Poppins Medium" if "Poppins Medium" in have else "Poppins",
                    "b": "Poppins SemiBold" if "Poppins SemiBold" in have else "Poppins"})


# ---------------- widgets proprios ----------------
class Slider(tk.Canvas):
    def __init__(s, parent, var, lo, hi, step, bg=C.panel):
        super().__init__(parent, height=px(18), bg=bg, highlightthickness=0, cursor="hand2")
        s.var, s.lo, s.hi, s.step = var, lo, hi, step
        s.bind("<Configure>", lambda e: s.draw()); s.bind("<Button-1>", s.move); s.bind("<B1-Motion>", s.move)
        var.trace_add("write", lambda *a: s.draw())

    def draw(s):
        s.delete("all"); w, h, pad = s.winfo_width(), s.winfo_height(), px(7)
        f = min(1, max(0, (s.var.get() - s.lo) / (s.hi - s.lo))); x = pad + (w - 2 * pad) * f; y = h // 2
        s.create_line(pad, y, w - pad, y, fill=C.line, width=px(4), capstyle="round")
        s.create_line(pad, y, x, y, fill=C.acc, width=px(4), capstyle="round")
        r = px(6); s.create_oval(x - r, y - r, x + r, y + r, fill=C.fg, outline="")

    def move(s, e):
        pad = px(7); f = min(1, max(0, (e.x - pad) / max(1, s.winfo_width() - 2 * pad)))
        s.var.set(round(round((s.lo + f * (s.hi - s.lo)) / s.step) * s.step, 4))


class Switch(tk.Canvas):
    def __init__(s, parent, var, bg=C.panel):
        super().__init__(parent, width=px(30), height=px(16), bg=bg, highlightthickness=0, cursor="hand2")
        s.var = var; s.bind("<Button-1>", lambda e: var.set(0 if var.get() else 1)); var.trace_add("write", lambda *a: s.draw()); s.draw()

    def draw(s):
        s.delete("all"); on = s.var.get(); w, h = px(30), px(16)
        col = C.acc if on else C.line
        s.create_oval(0, 0, h, h, fill=col, outline=""); s.create_oval(w - h, 0, w, h, fill=col, outline="")
        s.create_rectangle(h // 2, 0, w - h // 2, h, fill=col, outline="")
        r = px(6); cx = w - h // 2 if on else h // 2
        s.create_oval(cx - r, h // 2 - r, cx + r, h // 2 + r, fill=C.on if on else C.mute, outline="")


class Btn(tk.Label):
    def __init__(s, parent, text, cmd, primary=False, bg=C.panel):
        s.primary, s.cmd, s.base = primary, cmd, (C.acc if primary else bg)
        super().__init__(parent, text=text, bg=s.base, fg=C.on if primary else C.fg, font=fnt(9, "b" if primary else "m"),
                         padx=px(12), pady=px(5), cursor="hand2", highlightthickness=1,
                         highlightbackground=C.acc if primary else C.line)
        s.bind("<Button-1>", lambda e: s.cmd()); s.bind("<Enter>", lambda e: s.config(bg="#d7ff5a" if primary else C.sel))
        s.bind("<Leave>", lambda e: s.config(bg=s.base))


class Section(tk.Frame):
    def __init__(s, parent, title, opened=True):
        super().__init__(parent, bg=C.panel)
        s.title, s.opened = title, opened
        s.head = tk.Label(s, bg=C.panel, fg=C.mute, font=fnt(8, "m"), anchor="w", cursor="hand2")
        s.head.pack(fill="x", pady=(px(8), px(5))); s.head.bind("<Button-1>", lambda e: s.toggle())
        s.body = tk.Frame(s, bg=C.panel); s.body.pack(fill="x"); s.body.grid_columnconfigure(0, weight=1); s.body._r = 0
        s.show()

    def show(s):
        s.head.config(text=f"{s.title.upper()}   {'▾' if s.opened else '▸'}")
        if s.opened: s.body.pack(fill="x")
        else: s.body.pack_forget()

    def toggle(s): s.opened = not s.opened; s.show()


def gadd(body, w, **kw):
    r = body._r; w.grid(row=r, column=0, sticky="ew", **kw); body._r = r + 1


def cfg_load():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception: return {}


def cfg_save(d):
    try: CFG.parent.mkdir(parents=True, exist_ok=True); CFG.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception: pass


HINTS = {"inten": "Escala todos os efeitos. 100% = como está; abaixo disso, mais suave.", "sharp": "Nitidez geral. 0.4–0.8 é seguro.", "cas": "Só onde falta detalhe.", "hp": "Realça textura e microcontraste.",
         "hp_r": "Pequeno = detalhe fino.", "contrast": "1.00 = original.", "sat": "O Instagram desbota cores.",
         "gamma": ">1 clareia tons médios.", "bright": "0 = original.", "vib": "Satura só cores apagadas.",
         "denoise": "Limpa chiado em cena escura.", "grain": "Esconde blocos e degradês."}


class App(tk.Tk):
    def __init__(s, paths):
        super().__init__()
        global S
        S = s.winfo_fpixels("1i") / 96
        load_fonts()
        s.title("Instagram Quality"); s.configure(bg=C.bg)
        try: s.iconbitmap(default=str(BASE / "icon.ico"))
        except Exception: pass
        s.geometry(f"{px(1000)}x{px(660)}"); s.minsize(px(860), px(560))
        s.cfg = cfg_load(); saved = s.cfg.get("opts", {})
        s.v = {}
        for k, d in E.DEFAULTS.items():
            val = saved.get(k, d)
            s.v[k] = (tk.StringVar(value=str(val)) if isinstance(d, str) else tk.IntVar(value=int(val)) if isinstance(d, int)
                      else tk.DoubleVar(value=float(val)))
        if s.v["quality"].get() not in E.QUALITY: s.v["quality"].set(E.DEFAULTS["quality"])
        s.adv, s.each = tk.IntVar(value=int(s.cfg.get("advanced", 0))), tk.IntVar(value=int(s.cfg.get("each", 0)))
        s.inten = tk.DoubleVar(value=float(s.cfg.get("intensity", 100)))
        s.vs, s.glob, s.loading, s.an_hidden = {}, None, False, set()  # vs = ajustes por video (modo "Cada video")
        s.zoom, s.pos, s.status = tk.IntVar(value=0), tk.DoubleVar(value=0.5), tk.StringVar(value="Adicione vídeos para começar.")
        s.files, s.info, s.thumbs, s.analysis, s.done = [], {}, {}, {}, set()
        s.sel = None; s.proc = None; s.cancel = False; s.busy = False
        s.pv_tok, s.pv_key, s.pv_b, s.pv_a, s.disp, s.photo, s.split, s.geom = 0, None, None, None, None, None, 0.5, None
        s.pv_after = None; s.pv_busy = False; s.pv_err = ""
        s.adv_widgets = []; s.hint_labels = []
        s.presets = {**E.PRESETS, **s.cfg.get("presets", {})}
        s.style()
        s.build()
        for k, v in s.v.items():
            v.trace_add("write", lambda *a, k=k: s.touch(k))
        s.inten.trace_add("write", lambda *a: s.touch("inten")); s.each.trace_add("write", s.on_each)
        s.adv.trace_add("write", s.apply_mode); s.pos.trace_add("write", lambda *a: s.update_time())
        s.zoom.trace_add("write", lambda *a: (s.rebuild_disp(), s.draw_stage()))
        if s.each.get(): s.glob = s.snapshot()
        s.apply_mode(); s.add(paths)
        s.protocol("WM_DELETE_WINDOW", s.close)

    # ---------- estilo / construcao ----------
    def style(s):
        st = ttk.Style(s); st.theme_use("clam")
        st.configure("D.TCombobox", fieldbackground=C.sel, background=C.sel, foreground=C.fg, arrowcolor=C.mute,
                     bordercolor=C.line, lightcolor=C.sel, darkcolor=C.sel, padding=px(3))
        st.map("D.TCombobox", fieldbackground=[("readonly", C.sel)], foreground=[("readonly", C.fg)],
               selectbackground=[("readonly", C.sel)], selectforeground=[("readonly", C.fg)])
        s.option_add("*TCombobox*Listbox.background", C.sel); s.option_add("*TCombobox*Listbox.foreground", C.fg)
        s.option_add("*TCombobox*Listbox.selectBackground", C.acc); s.option_add("*TCombobox*Listbox.selectForeground", C.on)
        s.option_add("*TCombobox*Listbox.font", fnt(9))

    def lbl(s, parent, text="", fg=C.fg, font=None, bg=C.panel, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=font or fnt(9), **kw)

    def build(s):
        s.grid_rowconfigure(1, weight=1); s.grid_columnconfigure(0, weight=1)
        # --- barra de cima ---
        top = tk.Frame(s, bg=C.panel); top.grid(row=0, column=0, sticky="ew")
        tk.Label(top, text="IQ", bg=C.acc, fg=C.on, font=fnt(8, "b"), width=3).pack(side="left", padx=(px(12), px(8)), pady=px(8))
        s.lbl(top, "Instagram Quality", font=fnt(10, "b")).pack(side="left")
        Btn(top, "Pasta de saída", s.open_out).pack(side="right", padx=(px(6), px(12)))
        Btn(top, "Analisar todos", s.analyze_all).pack(side="right", padx=px(6))
        Btn(top, "Analisar", s.analyze_ui).pack(side="right", padx=px(6))
        Switch(top, s.adv).pack(side="right", padx=(px(6), 0)); s.lbl(top, "Avançado", fg=C.mute).pack(side="right")
        tk.Label(top, textvariable=s.status, bg=C.panel, fg=C.mute, font=fnt(8), anchor="w").pack(
            side="left", fill="x", expand=True, padx=px(16))  # por ultimo, pra nao empurrar os botoes
        tk.Frame(s, bg=C.line, height=1).grid(row=0, column=0, sticky="sew")
        body = tk.Frame(s, bg=C.bg); body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(0, weight=1)

        # --- lateral (rolavel) ---
        s.side = tk.Frame(body, bg=C.panel, width=px(232)); s.side.grid(row=0, column=0, sticky="ns"); s.side.grid_propagate(False)
        s.side.pack_propagate(False)
        tk.Frame(body, bg=C.line, width=1).grid(row=0, column=0, sticky="nse")
        cv = tk.Canvas(s.side, bg=C.panel, highlightthickness=0); cv.pack(fill="both", expand=True)
        s.inner = tk.Frame(cv, bg=C.panel); s.inner.grid_columnconfigure(0, weight=1)
        win = cv.create_window(0, 0, window=s.inner, anchor="nw")
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        s.inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        s.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units")
                   if cv.winfo_containing(e.x_root, e.y_root) is not None and str(cv.winfo_containing(e.x_root, e.y_root)).startswith(str(s.side))
                   and s.inner.winfo_height() > cv.winfo_height() else None)
        s.side_cv = cv
        pad = px(12); r = 0
        # vídeos
        s.files_hdr = s.lbl(s.inner, "VÍDEOS", fg=C.mute, font=fnt(8, "m"), anchor="w")
        s.files_hdr.grid(row=r, column=0, sticky="ew", padx=pad, pady=(pad, px(5))); r += 1
        s.files_box = tk.Frame(s.inner, bg=C.panel); s.files_box.grid(row=r, column=0, sticky="ew", padx=px(8)); r += 1
        bt = tk.Frame(s.inner, bg=C.panel); bt.grid(row=r, column=0, sticky="ew", padx=pad, pady=px(6)); r += 1
        bt.grid_columnconfigure((0, 1), weight=1)
        Btn(bt, "+ Vídeos", s.pick_files).grid(row=0, column=0, sticky="ew", padx=(0, px(3)))
        Btn(bt, "+ Pasta", s.pick_folder).grid(row=0, column=1, sticky="ew", padx=(px(3), 0))
        # ficha (avancado)
        s.ficha = tk.Frame(s.inner, bg=C.stage, highlightthickness=1, highlightbackground=C.line)
        s.ficha.grid(row=r, column=0, sticky="ew", padx=pad, pady=(px(4), px(8))); r += 1; s.adv_widgets.append(s.ficha)
        s.ficha.grid_columnconfigure(1, weight=1); s.fv = {}
        for i, k in enumerate(("Original", "Saída", "FPS", "Codec", "Duração")):
            s.lbl(s.ficha, k, fg=C.mute, font=fnt(8), bg=C.stage).grid(row=i, column=0, sticky="w", padx=(px(10), 0), pady=px(1))
            s.fv[k] = tk.StringVar(value="—")
            tk.Label(s.ficha, textvariable=s.fv[k], bg=C.stage, fg=C.fg, font=fnt(8, "m")).grid(row=i, column=1, sticky="e", padx=px(10))
        # ajustes valem pra todos ou um por video
        sg = tk.Frame(s.inner, bg=C.panel); sg.grid(row=r, column=0, sticky="ew", padx=pad, pady=(px(4), px(10))); r += 1
        s.lbl(sg, "AJUSTES PARA", fg=C.mute, font=fnt(8, "m"), anchor="w").pack(fill="x", pady=(0, px(4)))
        sb = tk.Frame(sg, bg=C.panel); sb.pack(fill="x"); s.segl = []
        for i, t in enumerate(("Todos os vídeos", "Cada vídeo")):
            lb = tk.Label(sb, text=t, font=fnt(8, "m"), pady=px(4), cursor="hand2", highlightthickness=1, highlightbackground=C.line)
            lb.bind("<Button-1>", lambda e, i=i: s.each.set(i)); lb.pack(side="left", fill="x", expand=True); s.segl.append(lb)
        s.seg_note = s.lbl(sg, "", fg=C.mute, font=fnt(7), anchor="w", justify="left", wraplength=px(200))
        s.seg_note.pack(fill="x", pady=(px(4), 0)); s.paint_seg()
        # predefinição
        pr = tk.Frame(s.inner, bg=C.panel); pr.grid(row=r, column=0, sticky="ew", padx=pad); r += 1
        pr.grid_columnconfigure((0, 1), weight=1)
        s.preset = ttk.Combobox(pr, values=list(s.presets), state="readonly", style="D.TCombobox", font=fnt(9))
        s.preset.grid(row=0, column=0, columnspan=2, sticky="ew"); s.preset.set("Predefinições…")
        s.preset.bind("<<ComboboxSelected>>", lambda e: s.apply_preset())
        Btn(pr, "Salvar", s.save_preset).grid(row=1, column=0, sticky="ew", padx=(0, px(3)), pady=(px(6), 0))
        Btn(pr, "Resetar", s.reset).grid(row=1, column=1, sticky="ew", padx=(px(3), 0), pady=(px(6), 0))
        ib = tk.Frame(s.inner, bg=C.panel); ib.grid(row=r, column=0, sticky="ew", padx=pad, pady=(px(10), 0)); r += 1
        ib.grid_columnconfigure(0, weight=1); ib._r = 0
        s.srow(ib, "Intensidade", "inten", 0, 150, 5, "{:.0f}%", var=s.inten)
        # secoes
        def sec(title, opened=True):
            nonlocal r
            sc = Section(s.inner, title, opened); sc.grid(row=r, column=0, sticky="ew", padx=pad); r += 1
            return sc.body
        n = sec("Nitidez"); s.srow(n, "Sharpen", "sharp", 0, 1.5, .05, "{:.2f}"); s.srow(n, "High-pass", "hp", 0, 100, 1, "{:.0f}%")
        s.srow(n, "CAS", "cas", 0, 1, .05, "{:.2f}"); s.srow(n, "Raio HP", "hp_r", 1, 20, .5, "{:.1f}", adv=True)
        c = sec("Cor"); s.srow(c, "Contraste", "contrast", .8, 1.4, .01, "{:.2f}"); s.srow(c, "Saturação", "sat", .5, 1.5, .01, "{:.2f}")
        s.srow(c, "Gamma", "gamma", .7, 1.4, .01, "{:.2f}"); s.srow(c, "Brilho", "bright", -.2, .2, .01, "{:.2f}", adv=True)
        s.srow(c, "Vibrance", "vib", -1, 2, .05, "{:.2f}", adv=True); s.trow(c, "HDR → SDR", "hdr")
        l = sec("Limpeza"); s.srow(l, "Ruído", "denoise", 0, 6, .5, "{:.1f}"); s.srow(l, "Grão", "grain", 0, 20, 1, "{:.0f}")
        s.trow(l, "Deband", "deband")
        o = sec("Saída")
        for lab, key, vals in (("Qualidade", "quality", list(E.QUALITY)), ("FPS máx.", "fps", ["30", "60", "original"])):
            f = tk.Frame(o, bg=C.panel); gadd(o, f, pady=(0, px(6))); f.grid_columnconfigure(1, weight=1)
            s.lbl(f, lab, fg=C.mute, font=fnt(8)).grid(row=0, column=0, sticky="w", padx=(0, px(8)))
            ttk.Combobox(f, textvariable=s.v[key], values=vals, state="readonly", style="D.TCombobox",
                         font=fnt(9)).grid(row=0, column=1, sticky="ew")
        s.inner.grid_rowconfigure(r, minsize=px(16))

        # --- area principal ---
        m = tk.Frame(body, bg=C.bg); m.grid(row=0, column=1, sticky="nsew")
        m.grid_rowconfigure(0, weight=1); m.grid_columnconfigure(0, weight=1)
        s.stage = tk.Canvas(m, bg=C.stage, highlightthickness=0); s.stage.grid(row=0, column=0, sticky="nsew")
        s.stage.bind("<Configure>", lambda e: s.after_idle(lambda: (s.rebuild_disp(), s.draw_stage())))
        s.stage.bind("<Button-1>", s.drag); s.stage.bind("<B1-Motion>", s.drag)
        s.build_strip(m)
        bar = tk.Frame(m, bg=C.panel); bar.grid(row=2, column=0, sticky="ew"); tk.Frame(m, bg=C.line, height=1).grid(row=2, column=0, sticky="new")
        bar.grid_columnconfigure(1, weight=1)
        z = tk.Frame(bar, bg=C.panel); z.grid(row=0, column=0, padx=(px(14), px(8)), pady=px(9))
        s.zl = []
        for i, t in enumerate(("Quadro", "100%")):
            lb = tk.Label(z, text=t, font=fnt(8, "m"), padx=px(8), pady=px(2), cursor="hand2", highlightthickness=1, highlightbackground=C.line)
            lb.bind("<Button-1>", lambda e, i=i: (s.zoom.set(i), s.paint_zoom())); lb.pack(side="left", padx=px(2)); s.zl.append(lb)
        s.paint_zoom()
        sc = Slider(bar, s.pos, 0, 1, .001); sc.grid(row=0, column=1, sticky="ew", padx=px(6))
        sc.bind("<ButtonRelease-1>", lambda e: s.request_preview(0), add="+")
        s.time = tk.StringVar(value=""); tk.Label(bar, textvariable=s.time, bg=C.panel, fg=C.mute, font=fnt(8), width=11).grid(row=0, column=2)
        s.est = tk.Label(bar, bg=C.panel, fg=C.fg, font=fnt(8, "m"), justify="right", anchor="e", width=24)
        s.est.grid(row=0, column=3, padx=px(8))
        s.go = Btn(bar, "Converter", s.start, primary=True); s.go.grid(row=0, column=4, padx=(0, px(14)))
        s.prog = tk.Canvas(m, height=px(3), bg=C.line, highlightthickness=0); s.prog.grid(row=3, column=0, sticky="ew")

    def build_strip(s, m):
        a = tk.Frame(m, bg=C.panel); a.grid(row=1, column=0, sticky="ew"); s.strip = a; a.grid_columnconfigure(0, weight=1)
        tk.Frame(a, bg=C.line, height=1).grid(row=0, column=0, sticky="ew")
        hd = tk.Frame(a, bg=C.panel); hd.grid(row=1, column=0, sticky="ew", padx=px(14), pady=(px(6), 0))
        s.an_title = s.lbl(hd, "ANÁLISE", fg=C.mute, font=fnt(8, "m")); s.an_title.pack(side="left")
        x = tk.Label(hd, text="✕", bg=C.panel, fg=C.mute, font=fnt(9), cursor="hand2", padx=px(6)); x.pack(side="right")
        x.bind("<Button-1>", lambda e: s.hide_panel())
        s.apply_btn = Btn(hd, "Aplicar recomendações", s.apply_current); s.apply_btn.pack(side="right", padx=px(6))
        s.apply_all_btn = Btn(hd, "Aplicar a todos", s.apply_all)
        mt = tk.Frame(a, bg=C.panel); mt.grid(row=2, column=0, sticky="ew", padx=px(14), pady=(px(6), 0)); s.adv_widgets.append(mt)
        s.mv = {}
        for k in ("Nitidez", "Ruído", "Brilho", "Faixa"):
            f = tk.Frame(mt, bg=C.panel); f.pack(side="left", padx=(0, px(22)))
            s.lbl(f, k, fg=C.mute, font=fnt(8)).pack(anchor="w")
            v = tk.Label(f, text="—", bg=C.panel, fg=C.fg, font=fnt(11, "b")); v.pack(anchor="w")
            t = tk.Label(f, text="", bg=C.panel, fg=C.acc, font=fnt(7)); t.pack(anchor="w"); s.mv[k] = (v, t)
        s.hist = tk.Canvas(mt, width=px(130), height=px(36), bg=C.panel, highlightthickness=0); s.hist.pack(side="right")
        s.an_text = tk.Text(a, height=4, wrap="word", font=fnt(8), bg=C.panel, fg=C.fg, bd=0, highlightthickness=0, cursor="arrow", spacing3=px(2))
        s.an_text.grid(row=3, column=0, sticky="ew", padx=px(14), pady=(px(4), px(8)))
        a.grid_remove()

    def srow(s, body, label, key, lo, hi, step, fmt, adv=False, var=None):
        f = tk.Frame(body, bg=C.panel); gadd(body, f, pady=(0, px(4))); f.grid_columnconfigure(1, weight=1)
        f.grid_columnconfigure(0, minsize=px(58))
        s.lbl(f, label, fg=C.mute, font=fnt(8)).grid(row=0, column=0, sticky="w")
        var = var or s.v[key]
        Slider(f, var, lo, hi, step).grid(row=0, column=1, sticky="ew", padx=px(4))
        val = tk.Label(f, bg=C.panel, fg=C.mute, font=fnt(8), width=5, anchor="e"); val.grid(row=0, column=2)
        upd = lambda *a: val.config(text=fmt.format(var.get())); var.trace_add("write", upd); upd()
        if key in HINTS:
            h = s.lbl(f, HINTS[key], fg=C.mute, font=fnt(7), anchor="w", justify="left"); h.grid(row=1, column=0, columnspan=3, sticky="w")
            s.adv_widgets.append(h)
        if adv: s.adv_widgets.append(f)

    def trow(s, body, label, key):
        f = tk.Frame(body, bg=C.panel); gadd(body, f, pady=(0, px(6)))
        s.lbl(f, label, fg=C.mute, font=fnt(8)).pack(side="left"); Switch(f, s.v[key]).pack(side="right")

    # ---------- modo / configuracao ----------
    def apply_mode(s, *_):
        adv = s.adv.get()
        s.side.configure(width=px(310 if adv else 232))
        for w in s.adv_widgets: w.grid() if adv else w.grid_remove()
        s.refresh_files(); s.update_est(); s.fill_strip(); s.fill_ficha()

    def close(s):
        g = s.glob if s.each.get() and s.glob else s.snapshot()
        s.cfg.update(opts={k: g[k] for k in E.DEFAULTS}, advanced=s.adv.get(), each=s.each.get(), intensity=g.get("_k", 100))
        s.cfg["presets"] = {k: v for k, v in s.presets.items() if k not in E.PRESETS}
        cfg_save(s.cfg)
        if s.proc: s.proc.terminate()
        s.destroy()

    def opts(s):
        return {k: v.get() for k, v in s.v.items()}

    def apply_preset(s):
        d = {**E.DEFAULTS, **s.presets[s.preset.get()]}
        for k, val in d.items(): s.v[k].set(val)

    def save_preset(s):
        name = simpledialog.askstring("Salvar predefinição", "Nome da predefinição:", parent=s)
        if name and name.strip():
            s.presets[name.strip()] = s.opts(); s.preset.configure(values=list(s.presets)); s.preset.set(name.strip())
            s.say(f"Predefinição “{name.strip()}” salva.")

    def say(s, t): s.status.set(t)

    def reset(s):
        for k, val in E.DEFAULTS.items(): s.v[k].set(val)
        s.inten.set(100); s.preset.set("Predefinições…"); s.say("Ajustes voltaram ao padrão.")

    def paint_seg(s):
        for i, lb in enumerate(s.segl):
            on = s.each.get() == i; lb.config(bg=C.acc if on else C.panel, fg=C.on if on else C.mute)
        s.seg_note.config(text="Mesmos ajustes para todos." if not s.each.get() else "Cada vídeo guarda os próprios ajustes e análise.")

    def snapshot(s):
        d = s.opts(); d["_k"] = s.inten.get(); return d

    def load(s, d):
        s.loading = True
        try:
            for k, v in d.items():
                if k == "_k": s.inten.set(v)
                elif k in s.v: s.v[k].set(v)
        finally: s.loading = False
        s.update_est()

    def on_each(s, *_):
        if s.each.get():  # Todos -> Cada: guarda os ajustes comuns e comeca cada video a partir deles
            s.glob = s.snapshot()
            if s.sel: s.vs[s.sel] = s.vs.get(s.sel) or dict(s.glob); s.load(s.vs[s.sel])
        else:  # Cada -> Todos: volta aos ajustes comuns
            if s.sel: s.vs[s.sel] = s.snapshot()
            if s.glob: s.load(s.glob)
        s.paint_seg(); s.fill_strip(); s.update_est(); s.request_preview(0)

    def pull_settings(s):
        f = s.sel
        if f and s.each.get():
            if f in s.vs: s.load(s.vs[f])
            else: s.vs[f] = s.snapshot()

    def settings_for(s, f):
        if s.each.get(): return s.vs.get(f) or s.glob or s.snapshot()
        return s.snapshot()

    def eff_opts(s, f):
        """Ajustes que valem de verdade pro video f, ja com a intensidade."""
        d = dict(s.settings_for(f)); k = d.pop("_k", 100) / 100
        return E.apply_intensity(d, k)


    def touch(s, key):
        if s.loading: return
        if s.each.get() and s.sel: s.vs[s.sel] = s.snapshot()
        s.update_est()
        if key not in ("quality", "fps"): s.request_preview(450)

    # ---------- lista de videos ----------
    def add(s, paths):
        new = [f for f in E.collect(paths) if f not in s.files]
        s.files += new
        if new and s.sel is None: s.sel = new[0]; s.pull_settings()
        s.refresh_files()
        for f in new: threading.Thread(target=s._load_info, args=(f,), daemon=True).start()

    def pick_files(s):
        r = filedialog.askopenfilenames(title="Escolha vídeos", filetypes=[("Vídeos", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mts *.mxf *.wmv"), ("Todos", "*.*")])
        if r: s.add(r)

    def pick_folder(s):
        d = filedialog.askdirectory(title="Escolha a pasta de vídeos")
        if d: s.add([d])

    def _load_info(s, f):
        try: inf = E.probe(f)
        except Exception: inf = dict(dur=0, w=0, h=0, fps=0, kbps=0, codec="?", hdr=False)
        img = None
        try:
            tmp = Path(tempfile.gettempdir()) / f"iq_th_{abs(hash(str(f)))}.png"
            r = E.run([E.FFMPEG, "-y", "-v", "error", "-ss", str(min(1, inf["dur"] / 2)), "-i", str(f), "-frames:v", "1",
                       "-vf", "scale=-2:76", str(tmp)])
            if r.returncode == 0: img = Image.open(tmp).convert("RGB"); img.load(); tmp.unlink(missing_ok=True)
        except Exception: pass
        s.after(0, s._info_ready, f, inf, img)

    def _info_ready(s, f, inf, img):
        if f not in s.files: return
        s.info[f] = inf
        if img: img.thumbnail((px(44), px(44))); s.thumbs[f] = ImageTk.PhotoImage(img)
        s.refresh_files()
        if f == s.sel: s.on_select()
        if inf.get("hdr") and f == s.sel: s.say("Vídeo HDR: ligue “HDR → SDR” em Cor (ou use Analisar).")

    def refresh_files(s):
        for w in s.files_box.winfo_children(): w.destroy()
        s.files_hdr.config(text=f"VÍDEOS   {len(s.files)}")
        adv = s.adv.get(); w_chars = 30 if adv else 20
        for f in s.files:
            on = f == s.sel; bg = C.sel if on else C.panel
            row = tk.Frame(s.files_box, bg=bg, cursor="hand2"); row.pack(fill="x", pady=1)
            if f in s.thumbs: th = tk.Label(row, image=s.thumbs[f], bg=bg)
            else: th = tk.Frame(row, bg="#2a2a2a", width=px(28), height=px(38))
            th.pack(side="left", padx=(px(6), px(8)), pady=px(4))
            txt = tk.Frame(row, bg=bg); txt.pack(side="left", fill="x", expand=True)
            name = f.name if len(f.name) <= w_chars else f.name[:w_chars - 1] + "…"
            tk.Label(txt, text=("✓ " if f in s.done else "") + name, bg=bg, fg=C.fg if on else C.mute, font=fnt(8, "m"), anchor="w").pack(fill="x")
            if adv:
                i = s.info.get(f)
                sub = f"{i['w']}×{i['h']} · {i['fps']:.0f} fps · {i['kbps']/1000:.0f} Mbps" if i and i["w"] else "lendo…"
                tk.Label(txt, text=sub, bg=bg, fg=C.mute, font=fnt(7), anchor="w").pack(fill="x")
            x = tk.Label(row, text="✕", bg=bg, fg=C.mute, font=fnt(8), cursor="hand2", padx=px(6)); x.pack(side="right")
            x.bind("<Button-1>", lambda e, f=f: s.remove(f))
            for wdg in (row, txt, th) + tuple(txt.winfo_children()): wdg.bind("<Button-1>", lambda e, f=f: s.select(f))

    def remove(s, f):
        s.files.remove(f)
        s.vs.pop(f, None); s.analysis.pop(f, None)
        if s.sel == f: s.sel = s.files[0] if s.files else None; s.pv_b = s.pv_a = s.disp = None; s.pv_key = None; s.pull_settings()
        s.refresh_files(); s.on_select()

    def select(s, f):
        s.sel = f; s.pull_settings(); s.refresh_files(); s.on_select()

    def on_select(s):
        s.update_time(); s.update_est(); s.fill_strip(); s.fill_ficha(); s.request_preview(0)
        if not s.sel: s.draw_stage()

    def dur(s): return s.info.get(s.sel, {}).get("dur", 0) if s.sel else 0

    def update_time(s):
        d = s.dur(); t = s.pos.get() * d
        s.time.set(f"{int(t//60)}:{int(t%60):02d} / {int(d//60)}:{int(d%60):02d}" if d else "")

    def fill_ficha(s):
        i = s.info.get(s.sel)
        if not i or not i["w"]:
            for v in s.fv.values(): v.set("—")
            return
        W, H = E.final_size(i["w"], i["h"])
        s.fv["Original"].set(f"{i['w']}×{i['h']}"); s.fv["Saída"].set(f"{W}×{H}")
        s.fv["FPS"].set(f"{i['fps']:.0f} → 30" if i["fps"] > 30 and s.v["fps"].get() == "30" else f"{i['fps']:.0f}")
        s.fv["Codec"].set(f"{i['codec']} → H.264"); s.fv["Duração"].set(f"{int(i['dur']//60)}:{int(i['dur']%60):02d}")

    def update_est(s):
        d = s.dur()
        if not d: return s.est.config(text="", fg=C.fg)
        o = s.eff_opts(s.sel); q = o["quality"]
        if q not in E.QUALITY: return
        nom, mx = E.estimate_mb(d, q); txt = f"≈ {nom:.0f} MB"; warn = d > 180
        if s.adv.get():
            i = s.info.get(s.sel); W, H = E.final_size(i["w"], i["h"]) if i and i["w"] else (0, 0)
            txt += f"  (máx. {mx:.0f})\n{W}×{H} · {E.NOMINAL[q]} Mbps · {o['fps']} fps"
        if warn: txt += "\n⚠ acima de 3 min (limite de Reels)"
        s.est.config(text=txt, fg=C.warn if warn else C.fg)

    def paint_zoom(s):
        for i, lb in enumerate(s.zl):
            on = s.zoom.get() == i; lb.config(bg=C.sel if on else C.panel, fg=C.fg if on else C.mute)

    # ---------- preview ----------
    def request_preview(s, delay=450):
        if s.pv_after: s.after_cancel(s.pv_after)
        s.pv_after = s.after(delay, s._start_preview)

    def _start_preview(s):
        s.pv_after = None
        f = s.sel
        if not f or f not in s.info: return
        o = s.eff_opts(f)
        s.pv_tok += 1; s.pv_busy = True; s.pv_err = ""
        threading.Thread(target=s._pv_work, args=(s.pv_tok, f, s.pos.get(), o, s.pv_key), daemon=True).start()
        s.draw_stage()

    def _pv_work(s, tok, f, frac, o, old_key):
        t = max(0, min(s.info[f]["dur"] * frac, s.info[f]["dur"] - 0.2)); key = (f, round(t, 2), o["hdr"])
        base = dict(o, sharp=0, cas=0, hp=0, contrast=1, sat=1, bright=0, gamma=1, vib=0, denoise=0, deband=0, grain=0)
        tmp = Path(tempfile.gettempdir())
        def grab(oo, name):
            png = tmp / f"iq_pv_{name}_{tok}.png"
            vf = E.build_vf(oo).rsplit(",format=yuv420p", 1)[0]
            r = E.run([E.FFMPEG, "-y", "-v", "error", "-ss", str(t), "-i", str(f), "-frames:v", "1", "-vf", vf, str(png)])
            if r.returncode != 0 or not png.exists(): raise RuntimeError(r.stderr[-200:] or "falha ao gerar quadro")
            im = Image.open(png).convert("RGB"); im.load(); png.unlink(missing_ok=True); return im
        try:
            before = s.pv_b if key == old_key and s.pv_b is not None else grab(base, "b")
            after = grab(o, "a"); err = ""
        except Exception as e: before = after = None; err = str(e)
        s.after(0, s._pv_done, tok, key, before, after, err)

    def _pv_done(s, tok, key, before, after, err):
        if tok != s.pv_tok: return
        s.pv_busy = False; s.pv_err = err
        if before is not None: s.pv_key, s.pv_b, s.pv_a = key, before, after; s.rebuild_disp()
        s.draw_stage()

    def rebuild_disp(s):
        if s.pv_b is None: s.disp = None; return
        cw, ch = max(1, s.stage.winfo_width() - px(32)), max(1, s.stage.winfo_height() - px(32))
        def fit(im):
            if s.zoom.get():  # 100%: recorte central sem reduzir
                w, h = im.size; bw, bh = min(w, cw), min(h, ch); x, y = (w - bw) // 2, (h - bh) // 2
                return im.crop((x, y, x + bw, y + bh))
            k = min(cw / im.width, ch / im.height); return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
        s.disp = (fit(s.pv_b), fit(s.pv_a))

    def draw_stage(s):
        c = s.stage; c.delete("all"); cw, ch = c.winfo_width(), c.winfo_height()
        if s.disp is None:
            msg = s.pv_err and ("Erro no preview:\n" + s.pv_err) or ("Gerando preview…" if s.pv_busy else
                  "Adicione um vídeo para ver o antes e depois." if not s.files else "Carregando…")
            return c.create_text(cw // 2, ch // 2, text=msg, fill=C.mute, font=fnt(10), justify="center")
        b, a = s.disp; W, H = b.size; x = int(W * s.split); comp = b.copy(); comp.paste(a.crop((x, 0, W, H)), (x, 0))
        s.photo = ImageTk.PhotoImage(comp); ox, oy = (cw - W) // 2, (ch - H) // 2; s.geom = (ox, oy, W, H)
        c.create_image(ox, oy, image=s.photo, anchor="nw")
        c.create_rectangle(ox, oy, ox + W, oy + H, outline=C.line)
        c.create_line(ox + x, oy, ox + x, oy + H, fill=C.acc, width=px(2))
        r = px(14); cy = oy + H // 2
        c.create_oval(ox + x - r, cy - r, ox + x + r, cy + r, fill=C.acc, outline=""); c.create_text(ox + x, cy, text="↔", fill=C.on, font=fnt(10, "b"))
        for txt, xx, an in (("ANTES", ox + px(8), "nw"), ("DEPOIS", ox + W - px(8), "ne")):
            c.create_text(xx, oy + px(8), text=txt, fill="#fff", font=fnt(7, "m"), anchor=an)
        if s.pv_busy: c.create_text(ox + W // 2, oy + H - px(12), text="atualizando…", fill=C.acc, font=fnt(8))

    def drag(s, e):
        if s.geom and s.disp:
            ox, oy, W, H = s.geom; s.split = min(1, max(0, (e.x - ox) / W)); s.draw_stage()

    # ---------- analise ----------
    def analyze_ui(s):
        f = s.sel
        if not f: return messagebox.showinfo("Analisar", "Adicione um vídeo primeiro.")
        s.an_hidden.discard(f); s.say(f"Analisando {f.name}…")
        threading.Thread(target=s._analyze, args=(f,), daemon=True).start()

    def _analyze(s, f):
        try: res = E.analyze(f)
        except Exception as e: return s.after(0, lambda: (s.say("Falha na análise."), messagebox.showerror("Análise", str(e))))
        s.after(0, s._an_one, f, res, False)

    def analyze_all(s):
        if not s.files: return messagebox.showinfo("Analisar todos", "Adicione vídeos primeiro.")
        if not s.each.get(): s.each.set(1)  # cada video precisa dos proprios ajustes
        s.an_hidden.clear()
        threading.Thread(target=s._analyze_all, args=(list(s.files),), daemon=True).start()

    def _analyze_all(s, files):
        n = len(files)
        for i, f in enumerate(files, 1):
            s.after(0, s.say, f"Analisando {i}/{n}: {f.name}…")
            try: res = E.analyze(f)
            except Exception: res = None
            if res: s.after(0, s._an_one, f, res, True)
        s.after(0, s.say, f"Pronto: {n} vídeo(s) analisado(s); cada um recebeu os próprios ajustes.")

    def _an_one(s, f, res, apply):
        if f not in s.files: return
        s.analysis[f] = res
        if apply: s.apply_to(f, res[0])
        else: s.say("Análise pronta.")
        s.fill_strip()

    def apply_to(s, f, rec):
        """Aplica as recomendacoes: no video f (modo Cada video) ou nos ajustes comuns (modo Todos)."""
        if s.each.get():
            d = {**rec, "_k": (s.vs.get(f) or {}).get("_k", s.inten.get() if f == s.sel else 100)}
            s.vs[f] = d
            if f == s.sel: s.load(d); s.request_preview(0)
        else: s.apply_rec(rec)

    def apply_rec(s, rec):
        for k, val in rec.items(): s.v[k].set(val)
        s.preset.set("Predefinições…")

    def apply_current(s):
        a = s.analysis.get(s.sel)
        if a: s.apply_to(s.sel, a[0]); s.say("Recomendações aplicadas."); s.hide_panel()

    def apply_all(s):
        """Copia as recomendacoes deste video pra todos os videos da lista."""
        a = s.analysis.get(s.sel)
        if not a: return
        for f in s.files: s.apply_to(f, a[0])
        s.say(f"Recomendações aplicadas a {len(s.files)} vídeo(s)."); s.hide_panel()

    def hide_panel(s):
        if s.sel: s.an_hidden.add(s.sel)
        s.fill_strip()

    def fill_strip(s):
        f = s.sel; a = s.analysis.get(f)
        if not a or f in s.an_hidden: return s.strip.grid_remove()
        s.strip.grid(); m = a[2]["m"]
        s.an_title.config(text="ANÁLISE · " + (f.name if len(f.name) <= 42 else f.name[:41] + "…"))
        if s.each.get(): s.apply_btn.config(text="Aplicar neste vídeo"); s.apply_all_btn.pack(side="right", padx=px(6))
        else: s.apply_btn.config(text="Aplicar nos ajustes"); s.apply_all_btn.pack_forget()
        txt = a[1].split("Recomendações:\n", 1)[-1]
        t = s.an_text; t.config(state="normal"); t.delete("1.0", "end"); t.insert("1.0", txt)
        t.config(height=min(5, txt.count("\n") + 1), state="disabled")
        def tag(x, cuts, names): return names[0] if x < cuts[0] else names[1] if x < cuts[1] else names[2]
        vals = {"Nitidez": (f"{m['g95']:.0f}", tag(m["g95"], (18, 35), ("macia", "normal", "nítida"))),
                "Ruído": (f"{m['noise']:.1f}", tag(m["noise"], (2.01, 3.5), ("limpo", "moderado", "alto"))),
                "Brilho": (f"{m['mean']:.0f}", tag(m["mean"], (80, 175), ("escuro", "médio", "claro"))),
                "Faixa": (f"{m['spread']:.0f}", tag(m["spread"], (170, 205), ("baixa", "média", "alta")))}
        for k, (v, tg) in vals.items(): s.mv[k][0].config(text=v); s.mv[k][1].config(text=tg)
        h = a[2]["hist"]; W, H = px(130), px(36); bw = W / len(h); mx = max(h) or 1; s.hist.delete("all")
        for i, x in enumerate(h):
            bh = max(1, (x / mx) * (H - 2)); s.hist.create_rectangle(i * bw + 1, H - bh, (i + 1) * bw - 1, H, fill=C.mute, outline="")

    # ---------- conversao ----------
    def start(s):
        if s.busy: return s.do_cancel()
        if not s.files: return messagebox.showinfo("Converter", "Adicione vídeos primeiro.")
        plan = {f: s.eff_opts(f) for f in s.files}
        s.cancel = False; s.busy = True; s.go.config(text="Cancelar"); s.done.clear()
        threading.Thread(target=s.worker, args=(list(s.files), plan), daemon=True).start()

    def do_cancel(s):
        s.cancel = True
        if s.proc: s.proc.terminate()

    def ui(s, text=None, pct=None):
        if text is not None: s.after(0, lambda: s.say(text))
        if pct is not None: s.after(0, lambda: s.set_prog(pct))

    def set_prog(s, pct):
        s.prog.delete("all"); s.prog.create_rectangle(0, 0, s.prog.winfo_width() * pct / 100, px(3), fill=C.acc, outline="")

    def worker(s, files, plan):
        E.OUT.mkdir(exist_ok=True); ok = 0; n_all = len(files)
        for i, f in enumerate(files):
            if s.cancel: break
            o = plan[f]
            out = E.OUT / f"{f.stem}_insta.mp4"; n = 2
            while out.exists(): out = E.OUT / f"{f.stem}_insta_{n}.mp4"; n += 1
            vf, args = E.build_vf(o), E.encode_args(o)
            s.ui(f"[{i+1}/{n_all}] Convertendo {f.name}…"); dur = E.duration(f) or 1
            s.proc = subprocess.Popen([E.FFMPEG, "-y", "-v", "error", "-progress", "pipe:1", "-nostats", "-i", str(f), "-vf", vf, *args, str(out)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=E.NOWIN)
            for line in s.proc.stdout:
                if line.startswith("out_time_us="):
                    try: s.ui(pct=(i + min(int(line[12:]) / 1e6 / dur, 1)) / n_all * 100)
                    except ValueError: pass
            err = s.proc.stderr.read(); rc = s.proc.wait()
            if rc == 0: ok += 1; s.done.add(f); s.after(0, s.refresh_files)
            elif not s.cancel: s.after(0, lambda e=err, nm=f.name: messagebox.showerror("Erro", f"{nm}\n\n{e[-600:]}"))
            if rc != 0 and out.exists(): out.unlink()
        s.proc = None; s.busy = False
        s.ui(("Cancelado. " if s.cancel else "Pronto! ") + f"{ok}/{n_all} convertidos em: {E.OUT}", 100 if not s.cancel else 0)
        s.after(0, lambda: s.go.config(text="Converter"))

    def open_out(s):
        E.OUT.mkdir(exist_ok=True); os.startfile(E.OUT)


if __name__ == "__main__":
    App(sys.argv[1:]).mainloop()
