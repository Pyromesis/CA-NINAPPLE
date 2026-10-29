#!/usr/bin/env python3
# NXNative Windows Builder: a window for win/build_ipa_windows.py. Pick the game's NSP / XCI files (base, update, DLC) and prod.keys, press Build IPA.
# It runs the same pipeline as the command line (python win/build_ipa_windows.py <folder> -k <keys> --progress json) with the pipeline's defaults
# (app name, bundle ID org.nxnativewindows.<title ID>, language, frame-rate counter) and shows its JSON progress events.
# The pipeline packs every game file in one folder; when the picked files share their folder with other games' files, they are hard-linked (copied on another drive)
# into a folder of their own first. Start: double-click Build-IPA-GUI.bat in the repository root, or this file (pythonw).
import json, math, os, queue, re, shutil, subprocess, sys, threading, time, tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

WIN = Path(__file__).resolve().parent
REPO = WIN.parent
sys.path.insert(0, str(WIN))
SETTINGS = WIN / 'gui_settings.json'   # the last picked files and keys (this PC only; git ignores it)
GAME_EXT = ('.nsp', '.xci', '.nsz', '.xcz')

# ---- theme: black and pink ----
BG, CARD, FIELD, FIELD_HI, BORDER = '#09090c', '#131318', '#1b1b22', '#25252f', '#26262f'
TEXT, MUTED, FAINT = '#f6f4f8', '#a19eaf', '#5f5c6c'
PINK, PINK_HI, PINK_LO, PINK_DEEP = '#ff2e88', '#ff63a8', '#d81b6e', '#2a0d1d'
GRAD = ((0xff, 0x2e, 0x88), (0xe8, 0x1c, 0x78))       # the Build button: pink with a slight fall-off, no second hue
GRAD_HI = ((0xff, 0x4d, 0x9a), (0xf2, 0x2c, 0x86))
OK, BAD = '#46e0a0', '#ff5c7a'
FONT = 'Segoe UI Variable Text'
FONT_D = 'Segoe UI Variable Display'
MONO = 'Cascadia Mono'
STAGE_NAMES = {'rewrite': 'Rewriting game code', 'IPA pack': 'Packing the IPA', 'app build': 'Building the app'}


def console_python():
    """python.exe beside this pythonw.exe: the build's output must come through a pipe, and no console window opens (CREATE_NO_WINDOW)"""
    exe = Path(sys.executable)
    if exe.name.lower() == 'pythonw.exe' and (exe.parent / 'python.exe').exists(): return str(exe.parent / 'python.exe')
    return str(exe)


def load_settings():
    try: return json.loads(SETTINGS.read_text(encoding='utf-8'))
    except (OSError, ValueError): return {}


def save_settings(d):
    try: SETTINGS.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding='utf-8')
    except OSError: pass


def title_id(files):
    return next((m.group(1).upper() for f in files if (m := re.search(r'\[([0-9A-Fa-f]{16})\]', Path(f).name))), None)


def stage_folder(files):
    """The folder to hand the pipeline: the files' own folder when it holds exactly these game files, else a folder of their own beside them with hard links (copies across drives)"""
    files = [Path(f).resolve() for f in files]
    parent = files[0].parent
    if all(f.parent == parent for f in files) and {p.resolve() for p in parent.iterdir() if p.suffix.lower() in GAME_EXT} == set(files): return parent, None
    tid = title_id(files)
    dst = parent / f'{(tid or files[0].stem)[:40]}_nxw'
    dst.mkdir(exist_ok=True)
    for p in dst.iterdir():
        if p.suffix.lower() in GAME_EXT and p.name not in {f.name for f in files}: p.unlink()   # files of an earlier pick no longer chosen
    copied = []
    for f in files:
        t = dst / f.name
        if t.exists() and t.stat().st_size == f.stat().st_size: continue
        if t.exists(): t.unlink()
        try: os.link(f, t)
        except OSError: shutil.copy2(f, t); copied.append(f.name)
    return dst, copied


def dark_title_bar(win):
    """Windows 11: a dark caption on the window's black, with a pink border (DWM attributes); ignored elsewhere"""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        for attr, val in ((20, 1), (35, 0x000C0909), (34, 0x00882EFF), (36, 0x00F8F4F6)):   # dark mode, caption #09090c, border #ff2e88, caption text (BGR)
            v = ctypes.c_int(val); ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
    except Exception: pass


def mix(a, b, t): return '#%02x%02x%02x' % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
def human(n): return f'{n / 2**30:.2f} GB' if n >= 2**30 else f'{n / 2**20:.0f} MB'


def rounded(c, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# ---- widgets ----
class Surface(tk.Canvas):
    """A rounded card: the canvas draws the card, self.body (a Frame) holds the content and sets the card's height"""
    def __init__(self, master, pad=18, radius=16, fill=CARD, outline=BORDER, bg=BG):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, height=10)
        self.pad, self.radius, self.fill, self.outline = pad, radius, fill, outline
        self.body = tk.Frame(self, bg=fill)
        self.win = self.create_window(pad, pad, window=self.body, anchor='nw')
        self.bind('<Configure>', self._layout); self.body.bind('<Configure>', self._fit)

    def _layout(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete('card'); self.itemconfigure(self.win, width=max(1, w - 2 * self.pad))
        rounded(self, 1, 1, w - 1, h - 1, self.radius, fill=self.fill, outline=self.outline, tags='card'); self.tag_lower('card')

    def _fit(self, e=None):   # the card's height follows its content's requested height (the content of a too-short canvas is unmapped and reports no size)
        self.body.update_idletasks()
        h = self.body.winfo_reqheight() + 2 * self.pad
        if int(float(self['height'])) != h: self.configure(height=h)

    @staticmethod
    def fit_all(w):
        for c in w.winfo_children():
            Surface.fit_all(c)
            if isinstance(c, Surface): c._fit()


class Link(tk.Label):
    def __init__(self, master, text, command, color=PINK, bg=CARD, size=9):
        super().__init__(master, text=text, fg=color, bg=bg, font=(FONT, size, 'bold'), cursor='hand2')
        self.base = color
        self.bind('<Button-1>', lambda e: command()); self.bind('<Enter>', lambda e: self.configure(fg=PINK_HI)); self.bind('<Leave>', lambda e: self.configure(fg=self.base))


class Ghost(tk.Canvas):
    """A small rounded outline button"""
    def __init__(self, master, text, command, bg=CARD, height=32):
        w = int(len(text) * 7.4) + 34
        super().__init__(master, width=w, height=height, bg=bg, highlightthickness=0, cursor='hand2')
        self.text, self.command, self.hover = text, command, False
        self.bind('<Enter>', lambda e: self._h(True)); self.bind('<Leave>', lambda e: self._h(False)); self.bind('<ButtonRelease-1>', lambda e: self.command())
        self._draw()
    def _h(self, v): self.hover = v; self._draw()
    def _draw(self):
        self.delete('all'); w, h = int(self['width']), int(self['height'])
        rounded(self, 1, 1, w - 1, h - 1, h // 2, fill=FIELD_HI if self.hover else FIELD, outline=PINK if self.hover else BORDER)
        self.create_text(w // 2, h // 2, text=self.text, fill=TEXT, font=(FONT, 9, 'bold'))


class Badge(tk.Canvas):
    def __init__(self, master, text, bg=CARD, size=34, fill=PINK_DEEP, fg=PINK):
        super().__init__(master, width=size, height=size, bg=bg, highlightthickness=0)
        rounded(self, 1, 1, size - 1, size - 1, 10, fill=fill, outline='')
        self.create_text(size // 2, size // 2, text=text, fill=fg, font=(FONT_D, 8 if len(text) > 2 else 10, 'bold'))


class Choice(Surface):
    """A selectable tile: a radio mark, a title and one line; the selected one has a pink outline"""
    def __init__(self, master, title, sub, command):
        super().__init__(master, pad=14, radius=12, fill=FIELD, outline=BORDER, bg=CARD)
        self.command = command
        b = self.body
        self.mark = tk.Canvas(b, width=18, height=18, bg=FIELD, highlightthickness=0); self.mark.pack(side='left', anchor='n', pady=(1, 0))
        t = tk.Frame(b, bg=FIELD); t.pack(side='left', padx=(10, 0), fill='x', expand=True)
        t1 = tk.Label(t, text=title, bg=FIELD, fg=TEXT, font=(FONT, 10, 'bold'), anchor='w'); t1.pack(fill='x')
        t2 = tk.Label(t, text=sub, bg=FIELD, fg=MUTED, font=(FONT, 9), anchor='w', justify='left', wraplength=290); t2.pack(fill='x')
        for w in (self, b, self.mark, t, t1, t2):
            w.configure(cursor='hand2'); w.bind('<Button-1>', lambda e: self.command())
        self.select(False)

    def select(self, on):
        self.outline = PINK if on else BORDER; self._layout()
        m = self.mark; m.delete('all')
        m.create_oval(2, 2, 16, 16, outline=PINK if on else FAINT, width=1.5)
        if on: m.create_oval(6, 6, 12, 12, fill=PINK, outline='')


class BuildButton(tk.Canvas):
    """The main action: a pink pill that turns into the build's progress bar while it runs"""
    H = 58
    def __init__(self, master, command):
        super().__init__(master, height=self.H, bg=BG, highlightthickness=0, cursor='hand2')
        self.command, self.hover, self.state, self.frac, self.label, self.sub = command, False, 'ready', 0.0, 'Build IPA', ''
        self.bind('<Enter>', lambda e: self._h(True)); self.bind('<Leave>', lambda e: self._h(False))
        self.bind('<ButtonRelease-1>', lambda e: self.state in ('ready', 'done') and self.command()); self.bind('<Configure>', lambda e: self.draw())

    def _h(self, v): self.hover = v; self.draw()

    def set(self, state, label=None, frac=None, sub=None):
        self.state = state
        if label is not None: self.label = label
        if frac is not None: self.frac = max(0.0, min(1.0, frac))
        if sub is not None: self.sub = sub
        self.configure(cursor='hand2' if state in ('ready', 'done') else 'arrow'); self.draw()

    def _pill(self, w, upto, grad):   # the stadium shape filled with the gradient from x=0 to x=upto, one vertical line per pixel
        h, r = self.H - 6, (self.H - 6) / 2
        for x in range(int(upto)):
            d = r - math.sqrt(max(0.0, r * r - (r - x) ** 2)) if x < r else r - math.sqrt(max(0.0, r * r - (x - (w - r)) ** 2)) if x > w - r else 0
            self.create_line(x, 3 + d, x, 3 + h - d, fill=mix(grad[0], grad[1], x / max(1, w)))

    def draw(self):
        self.delete('all'); w = self.winfo_width()
        if w < 10: return
        h = self.H - 6
        if self.state == 'disabled':
            rounded(self, 0, 3, w - 1, 3 + h, h // 2, fill=FIELD, outline=BORDER)
            self.create_text(w // 2, self.H // 2, text=self.label, fill=FAINT, font=(FONT, 11, 'bold')); return
        if self.state == 'running':
            rounded(self, 0, 3, w - 1, 3 + h, h // 2, fill=FIELD, outline=BORDER)
            if self.frac > 0: self._pill(w, max(h, w * self.frac), GRAD)
            self.create_text(24, self.H // 2, text=self.label, anchor='w', fill='#ffffff', font=(FONT, 10, 'bold'))
            self.create_text(w - 24, self.H // 2, text=f'{int(self.frac * 100)}%', anchor='e', fill='#ffffff', font=(FONT_D, 12, 'bold'))
            return
        self._pill(w, w, GRAD_HI if self.hover else GRAD)
        self.create_text(w // 2, self.H // 2, text=self.label, fill='#ffffff', font=(FONT_D, 13, 'bold'))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NXNative for Windows'); self.configure(bg=BG)
        self.geometry('840x980'); self.minsize(720, 760)
        self.s = load_settings()
        self.files = [f for f in self.s.get('files', []) if Path(f).exists()]
        self.keys = self.s.get('keys', '') if Path(self.s.get('keys', '') or '.').is_file() else ''
        self.out = ''
        self.proc, self.q, self.out_ipa, self.started, self.n, self.details = None, queue.Queue(), None, 0, 1, False
        self._ttk(); self._build(); self._toggle_details(); self._intro(); self._refresh()
        threading.Thread(target=self._doctor, daemon=True).start()
        self.after(100, self._pump); self.after(60, lambda: dark_title_bar(self))
        self.protocol('WM_DELETE_WINDOW', self._close)

    def _ttk(self):
        st = ttk.Style(self); st.theme_use('clam')
        st.configure('Dark.Vertical.TScrollbar', background=FIELD_HI, troughcolor=BG, bordercolor=BG, arrowcolor=FAINT, lightcolor=FIELD_HI, darkcolor=FIELD_HI, gripcount=0)

    # ---- layout ----
    def _build(self):
        wrap = tk.Frame(self, bg=BG); wrap.pack(fill='both', expand=True, padx=28, pady=(22, 18))

        hdr = tk.Frame(wrap, bg=BG); hdr.pack(fill='x', pady=(0, 18))
        logo = tk.Canvas(hdr, width=46, height=46, bg=BG, highlightthickness=0); logo.pack(side='left')
        rounded(logo, 1, 1, 45, 45, 12, fill=PINK_DEEP, outline=PINK, width=1)   # a flat monogram tile
        logo.create_text(23, 23, text='NX', fill=PINK, font=(FONT_D, 15, 'bold'))
        tt = tk.Frame(hdr, bg=BG); tt.pack(side='left', padx=14)
        tk.Label(tt, text='NXNative', bg=BG, fg=TEXT, font=(FONT_D, 20, 'bold')).pack(anchor='w')
        tk.Label(tt, text='Native iPhone & iPad builds, made on Windows', bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor='w')
        self.pill = tk.Canvas(hdr, width=176, height=30, bg=BG, highlightthickness=0); self.pill.pack(side='right')
        self._pill('Checking tools…', FAINT)

        # 1. game files
        self.c1 = Surface(wrap); self.c1.pack(fill='x', pady=(0, 12))
        b = self.c1.body
        top = tk.Frame(b, bg=CARD); top.pack(fill='x')
        self._step(top, '1', 'Game files', 'Base game, plus its update and DLC if you have them')
        self.more = tk.Frame(top, bg=CARD); self.more.pack(side='right')
        Link(self.more, 'Add files', self._add_files).pack(side='left', padx=(0, 14))
        Link(self.more, 'Choose folder', self._add_folder).pack(side='left')
        self.files_box = tk.Frame(b, bg=CARD); self.files_box.pack(fill='x', pady=(14, 0))
        self.drop = tk.Canvas(self.files_box, height=118, bg=CARD, highlightthickness=0, cursor='hand2')
        self.drop.bind('<Configure>', lambda e: self._draw_drop()); self.drop.bind('<Button-1>', lambda e: self._add_files())
        self.drop.bind('<Enter>', lambda e: self._draw_drop(True)); self.drop.bind('<Leave>', lambda e: self._draw_drop(False))
        self.rows = tk.Frame(self.files_box, bg=CARD)

        # 2. prod.keys
        self.c2 = Surface(wrap); self.c2.pack(fill='x', pady=(0, 12))
        top = tk.Frame(self.c2.body, bg=CARD); top.pack(fill='x')
        self._step(top, '2', 'prod.keys', 'The keys dumped from your own Switch')
        Ghost(top, 'Browse', self._pick_keys).pack(side='right')
        self.key_row = tk.Frame(self.c2.body, bg=CARD); self.key_row.pack(fill='x', pady=(14, 0))

        # 3. package: one IPA, or a small app IPA plus a data folder
        self.c3 = Surface(wrap); self.c3.pack(fill='x', pady=(0, 16))
        top = tk.Frame(self.c3.body, bg=CARD); top.pack(fill='x')
        self._step(top, '3', 'Package', 'How the game reaches your iPhone or iPad')
        tiles = tk.Frame(self.c3.body, bg=CARD); tiles.pack(fill='x', pady=(14, 0))
        tiles.columnconfigure(0, weight=1, uniform='t'); tiles.columnconfigure(1, weight=1, uniform='t')
        self.split = bool(self.s.get('split', False))
        self.tiles = [Choice(tiles, 'Single IPA', 'Everything in one file. Simplest to install.', lambda: self._set_split(False)),
                      Choice(tiles, 'App + data folder', 'Small IPA that signs in seconds. Copy the data into the app once.', lambda: self._set_split(True))]
        self.tiles[0].grid(row=0, column=0, sticky='nsew', padx=(0, 6)); self.tiles[1].grid(row=0, column=1, sticky='nsew', padx=(6, 0))
        # Increased Memory Limit: the app asks for it in its own signature; SideStore / SideInstaller keeps it when the App ID allows it
        tk.Label(self.c3.body, text='Increased Memory Limit', bg=CARD, fg=TEXT, font=(FONT, 10, 'bold'), anchor='w').pack(fill='x', pady=(16, 0))
        tiles2 = tk.Frame(self.c3.body, bg=CARD); tiles2.pack(fill='x', pady=(8, 0))
        tiles2.columnconfigure(0, weight=1, uniform='t'); tiles2.columnconfigure(1, weight=1, uniform='t')
        self.iml = bool(self.s.get('iml', True))
        self.iml_tiles = [Choice(tiles2, 'On', 'More memory for big games (TotK). Needs the capability on in SideStore / SideInstaller.', lambda: self._set_iml(True)),
                          Choice(tiles2, 'Off', 'Plain app, no entitlement. For signers that refuse it.', lambda: self._set_iml(False))]
        self.iml_tiles[0].grid(row=0, column=0, sticky='nsew', padx=(0, 6)); self.iml_tiles[1].grid(row=0, column=1, sticky='nsew', padx=(6, 0))
        out = tk.Frame(self.c3.body, bg=CARD); out.pack(fill='x', pady=(12, 0))
        self.out_lbl = tk.Label(out, text='', bg=CARD, fg=MUTED, font=(FONT, 9), anchor='w'); self.out_lbl.pack(side='left')
        self.out_link = Link(out, 'Change', self._pick_out); self.out_link.pack(side='left', padx=8)
        self.out_reset = Link(out, 'Reset', self._reset_out, color=MUTED)

        # build
        self.btn = BuildButton(wrap, self._start); self.btn.pack(fill='x')
        under = tk.Frame(wrap, bg=BG); under.pack(fill='x', pady=(10, 0), padx=4)
        self.status = tk.Label(under, text='', bg=BG, fg=MUTED, font=(FONT, 9), anchor='w'); self.status.pack(side='left', fill='x', expand=True)
        self.cancel = Link(under, 'Cancel', self._cancel, bg=BG, color=BAD)
        self.det_link = Link(under, 'Show details', self._toggle_details, bg=BG, color=MUTED); self.det_link.pack(side='right')

        # result
        self.result = Surface(wrap, fill='#0f1a15', outline='#1f5a40')
        rb = self.result.body; rb.configure(bg='#0f1a15')
        tk.Label(rb, text='✓', bg='#0f1a15', fg=OK, font=(FONT_D, 18, 'bold')).pack(side='left', padx=(0, 12))
        rt = tk.Frame(rb, bg='#0f1a15'); rt.pack(side='left', fill='x', expand=True)
        tk.Label(rt, text='Your IPA is ready', bg='#0f1a15', fg=TEXT, font=(FONT, 11, 'bold'), anchor='w').pack(fill='x')
        self.res_path = tk.Label(rt, text='', bg='#0f1a15', fg=MUTED, font=(FONT, 9), anchor='w', justify='left'); self.res_path.pack(fill='x')
        self.res_hint = tk.Label(rt, text='', bg='#0f1a15', fg=FAINT, font=(FONT, 9), anchor='w', justify='left'); self.res_hint.pack(fill='x')
        Ghost(rb, 'Show in folder', self._open_out, bg='#0f1a15').pack(side='right')

        # details (the log)
        self.det = tk.Frame(wrap, bg=BG)
        self.log = tk.Text(self.det, height=12, wrap='word', font=(MONO, 9), state='disabled', relief='flat', bg='#0d0d11', fg='#cfccd8',
                           insertbackground=PINK, selectbackground=PINK_LO, padx=12, pady=10, highlightthickness=1, highlightbackground=BORDER, bd=0)
        sb = ttk.Scrollbar(self.det, command=self.log.yview, style='Dark.Vertical.TScrollbar'); self.log.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y'); self.log.pack(fill='both', expand=True)
        for tag, col in (('red', BAD), ('ok', OK), ('dim', FAINT), ('pink', PINK_HI)): self.log.tag_configure(tag, foreground=col)

    def _intro(self):   # what a build uses when nothing is changed: the pipeline's own defaults
        self._write('NXNative for Windows\n', 'pink')
        for k, v in (('App name', "the game's own name"), ('Bundle ID', 'org.nxnativewindows.<title ID>'), ('Language', "the game's default (en-US when it has it)"),
                     ('IPA', 'saved next to your game files'), ('Package', 'one IPA, or app + data folder (step 03)'), ('Memory', 'Increased Memory Limit asked for (step 03)'), ('Signing', 'ad-hoc; SideStore re-signs it when you install')):
            self._write(f'  {k:<10}', 'dim'); self._write(f'{v}\n')
        self._write('\nPick the game files and prod.keys above, then press Build IPA.\n', 'dim')

    def _step(self, parent, n, title, sub):
        tk.Label(parent, text=f'{int(n):02d}', bg=CARD, fg=PINK, font=(MONO, 10, 'bold')).pack(side='left', anchor='n', pady=(2, 0))
        t = tk.Frame(parent, bg=CARD); t.pack(side='left', padx=(10, 12))
        tk.Label(t, text=title, bg=CARD, fg=TEXT, font=(FONT, 11, 'bold'), anchor='w').pack(fill='x')
        tk.Label(t, text=sub, bg=CARD, fg=MUTED, font=(FONT, 9), anchor='w').pack(fill='x')

    def _pill(self, text, color):
        c = self.pill; c.delete('all'); w = int(c['width'])
        rounded(c, 1, 1, w - 1, 29, 14, fill=CARD, outline=BORDER)
        c.create_oval(14, 11, 22, 19, fill=color, outline='')
        c.create_text(30, 15, text=text, anchor='w', fill=TEXT if color != FAINT else MUTED, font=(FONT, 9))

    def _draw_drop(self, hover=False):
        c = self.drop; c.delete('all'); w, h = c.winfo_width(), c.winfo_height()
        rounded(c, 1, 1, w - 1, h - 1, 14, fill=FIELD if hover else '#16161c', outline=PINK if hover else '#3a3a48', dash=(6, 4), width=1)
        c.create_oval(w // 2 - 17, 22, w // 2 + 17, 56, fill=PINK_DEEP, outline='')
        c.create_text(w // 2, 38, text='+', fill=PINK, font=(FONT_D, 18, 'bold'))
        c.create_text(w // 2, 76, text='Click to choose your NSP / XCI files', fill=TEXT, font=(FONT, 10, 'bold'))
        c.create_text(w // 2, 96, text='NSZ and XCZ work too', fill=FAINT, font=(FONT, 9))

    def _refresh(self):
        for wdg in self.rows.winfo_children(): wdg.destroy()
        if not self.files:
            self.rows.pack_forget(); self.drop.pack(fill='x'); self.more.pack_forget()
        else:
            self.drop.pack_forget(); self.rows.pack(fill='x'); self.more.pack(side='right')
            for i, f in enumerate(self.files):
                p = Path(f); r = Surface(self.rows, pad=10, radius=12, fill=FIELD, outline=BORDER, bg=CARD); r.pack(fill='x', pady=(0, 6))
                rb = r.body; rb.configure(bg=FIELD)
                tid = title_id([f])   # base titles end in 000, updates in 800, DLC in anything else
                kind = (p.suffix[1:].upper() if not tid else 'BASE' if tid.endswith('000') else 'UPD' if tid.endswith('800') else 'DLC')
                Badge(rb, kind, bg=FIELD, size=32).pack(side='left')
                name = p.name if len(p.name) < 62 else p.name[:58] + '…'
                tk.Label(rb, text=name, bg=FIELD, fg=TEXT, font=(FONT, 10), anchor='w').pack(side='left', padx=12, fill='x', expand=True)
                x = tk.Label(rb, text='✕', bg=FIELD, fg=FAINT, font=(FONT, 10), cursor='hand2'); x.pack(side='right', padx=(10, 4))
                x.bind('<Button-1>', lambda e, i=i: self._remove(i)); x.bind('<Enter>', lambda e, x=x: x.configure(fg=BAD)); x.bind('<Leave>', lambda e, x=x: x.configure(fg=FAINT))
                tk.Label(rb, text=human(p.stat().st_size) if p.exists() else 'missing', bg=FIELD, fg=MUTED, font=(FONT, 9)).pack(side='right')
        for wdg in self.key_row.winfo_children(): wdg.destroy()
        r = Surface(self.key_row, pad=10, radius=12, fill=FIELD, outline=BORDER, bg=CARD); r.pack(fill='x')
        rb = r.body; rb.configure(bg=FIELD)
        if self.keys:
            Badge(rb, 'KEY', bg=FIELD, size=32).pack(side='left')
            tk.Label(rb, text=self.keys, bg=FIELD, fg=TEXT, font=(FONT, 10), anchor='w').pack(side='left', padx=12, fill='x', expand=True)
            tk.Label(rb, text='✓', bg=FIELD, fg=OK, font=(FONT, 11, 'bold')).pack(side='right', padx=4)
        else:
            Badge(rb, 'KEY', bg=FIELD, size=32, fill=FIELD_HI, fg=FAINT).pack(side='left')
            tk.Label(rb, text='No prod.keys selected yet', bg=FIELD, fg=FAINT, font=(FONT, 10), anchor='w').pack(side='left', padx=12)
        for i, tl in enumerate(self.tiles): tl.select(i == int(self.split))
        for i, tl in enumerate(self.iml_tiles): tl.select(i == int(not self.iml))
        what = 'The IPA and its data folder are' if self.split else 'The IPA is'
        if self.out: self.out_lbl.configure(text=f'Saves to  {self.out}'); self.out_reset.pack(side='left')
        else: self.out_lbl.configure(text=f'{what} saved next to your game files'); self.out_reset.pack_forget()
        if not self.proc:
            if self.files and self.keys: self.btn.set('ready', 'Build IPA')
            else: self.btn.set('disabled', 'Add game files and prod.keys to start')
        self.after_idle(lambda: Surface.fit_all(self))

    # ---- pickers ----
    def _initial(self): return self.s.get('dir') or str(Path.home())

    def _add_files(self):
        if self.proc: return
        fs = filedialog.askopenfilenames(title='Choose game files', initialdir=self._initial(), filetypes=[('Switch games', '*.nsp *.xci *.nsz *.xcz'), ('All files', '*.*')])
        if fs:
            self.s['dir'] = str(Path(fs[0]).parent)
            for f in fs:
                if str(Path(f)) not in self.files: self.files.append(str(Path(f)))
            self._after_pick()

    def _add_folder(self):
        if self.proc: return
        d = filedialog.askdirectory(title='Choose the game folder', initialdir=self._initial())
        if not d: return
        self.s['dir'] = d
        found = sorted(str(p) for p in Path(d).iterdir() if p.suffix.lower() in GAME_EXT)
        if not found: messagebox.showwarning('No game files', f'No NSP / XCI / NSZ / XCZ files in\n{d}'); return
        if len({title_id([f])[:12] for f in found if title_id([f])}) > 1:
            messagebox.showinfo('More than one game', 'This folder holds several games. Remove the other games\' files from the list (✕).')
        self.files = found
        if not self.keys and (Path(d) / 'prod.keys').is_file(): self.keys = str(Path(d) / 'prod.keys')
        self._after_pick()

    def _after_pick(self):
        if not self.keys:
            for f in self.files:
                k = Path(f).parent / 'prod.keys'
                if k.is_file(): self.keys = str(k); break
        self.result.pack_forget(); self._refresh()

    def _remove(self, i):
        if self.proc: return
        del self.files[i]; self._refresh()

    def _pick_keys(self):
        if self.proc: return
        f = filedialog.askopenfilename(title='Choose prod.keys', initialdir=str(Path(self.keys).parent) if self.keys else self._initial(), filetypes=[('Keys', '*.keys'), ('All files', '*.*')])
        if f: self.keys = str(Path(f)); self._refresh()

    def _pick_out(self):
        f = filedialog.asksaveasfilename(title='Save the IPA as', defaultextension='.ipa', filetypes=[('IPA', '*.ipa')], initialdir=self._initial())
        if f: self.out = str(Path(f)); self._refresh()

    def _reset_out(self): self.out = ''; self._refresh()

    def _set_split(self, v):
        if self.proc: return
        self.split = v; self.s['split'] = v; save_settings(self.s); self._refresh()

    def _set_iml(self, v):
        if self.proc: return
        self.iml = v; self.s['iml'] = v; save_settings(self.s); self._refresh()

    def _toggle_details(self):
        self.details = not self.details
        if self.details: self.det.pack(fill='both', expand=True, pady=(12, 0)); self.det_link.configure(text='Hide details')
        else: self.det.pack_forget(); self.det_link.configure(text='Show details')

    # ---- toolchain ----
    def _doctor(self):
        try:
            import doctor
            self.q.put(('doctor', [r for r in doctor.checks() if r['required'] and not r['ok']]))
        except Exception as e: self.q.put(('doctor', [{'name': f'doctor.py: {e}', 'how': ''}]))

    # ---- build ----
    def _start(self):
        if self.proc or not (self.files and self.keys): return
        if not Path(self.keys).is_file(): messagebox.showwarning('prod.keys', 'The prod.keys file is gone. Choose it again.'); return
        try: folder, copied = stage_folder(self.files)
        except OSError as e: messagebox.showerror('Game files', str(e)); return
        cmd = [console_python(), '-u', str(WIN / 'build_ipa_windows.py'), str(folder), '-k', self.keys, '--progress', 'json']
        if self.out: cmd += ['-o', self.out]
        if self.split: cmd += ['--split-data']
        cmd += ['--entitlements' if self.iml else '--no-entitlements']
        self.s.update(files=self.files, keys=self.keys); save_settings(self.s)
        self._clear_log()
        self._write(f'Game folder  {folder}' + ('  (hard links to your files)' if folder != Path(self.files[0]).parent else '') + '\n', 'dim')
        if copied: self._write(f'Copied (another drive, no hard link possible): {", ".join(copied)}\n', 'dim')
        self.out_ipa, self.started, self.warn = None, time.time(), []
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        mods = next((d for d in (Path(folder) / 'mods', Path(self.files[0]).parent / 'mods') if d.is_dir()), None)   # win/mods.py: the emulators' mod layout beside the game files
        if mods: env['NXW_MODS_DIR'] = str(mods); self._write(f'Mods  {mods}\n', 'dim')
        try:
            self.proc = subprocess.Popen(cmd, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), text=True, encoding='utf-8', errors='replace', bufsize=1)
        except OSError as e: messagebox.showerror('Cannot start the build', str(e)); self.proc = None; return
        self.result.pack_forget()
        self.btn.set('running', 'Starting…', 0.0); self.status.configure(text='', fg=MUTED)
        self.cancel.pack(side='right', padx=(14, 0))
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()

    def _reader(self, p):
        for line in p.stdout:
            line = line.rstrip('\n')
            try: ev = json.loads(line) if line.startswith('{') else None
            except ValueError: ev = None
            self.q.put(('ev', ev) if isinstance(ev, dict) else ('line', line))
        self.q.put(('exit', p.wait()))

    def _cancel(self):
        if self.proc and self.proc.poll() is None:
            subprocess.run(['taskkill', '/PID', str(self.proc.pid), '/T', '/F'], capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self._write('Cancelled.\n', 'red'); self.cancelled = True

    def _pump(self):
        try:
            while True:
                kind, v = self.q.get_nowait()
                if kind == 'ev': self._event(v)
                elif kind == 'line':
                    if v.strip(): self._write(v + '\n', 'red' if '[RED]' in v or 'Traceback' in v or 'Error' in v else None)
                elif kind == 'exit': self._done(v)
                elif kind == 'doctor': self._doctor_done(v)
        except queue.Empty: pass
        self.after(80, self._pump)

    def _stage_text(self, k, name, step=''):
        nice = STAGE_NAMES.get(name, name[:1].upper() + name[1:])
        return f'{nice}' + (f'  ·  {step}' if step else '') + f'      {k}/{self.n}'

    def _event(self, ev):
        e = ev.get('ev')
        if e == 'stage':
            k, self.n = ev.get('k', 0), max(ev.get('n', 1), 1); self.k = k
            self.btn.set('running', self._stage_text(k, ev.get('name', ''), ev.get('step', '')), (k - 1) / self.n); self.status.configure(text='')
        elif e == 'step':
            self.btn.set('running', self._stage_text(ev.get('k', 1), ev.get('name', ''), ev.get('step', '')))
        elif e == 'progress':
            k, f = ev.get('k', 1), ev.get('frac')
            if f is not None: self.btn.set('running', frac=(k - 1 + f) / self.n)
            parts = []
            if ev.get('done') is not None:
                d, t, u = ev['done'], ev.get('total'), ev.get('unit') or ''
                parts.append((human(d) + (f' of {human(t)}' if t else '')) if u == 'B' else f'{d:,}' + (f' of {t:,}' if t else '') + (f' {u}' if u else ''))
            if ev.get('eta'): parts.append(f'about {int(ev["eta"]) // 60}:{int(ev["eta"]) % 60:02d} left')
            if ev.get('note'): parts.append(ev['note'])
            self.status.configure(text='   ·   '.join(parts))
        elif e == 'stage_end':
            ok = ev.get('ok', True)
            self._write(f'{"✓" if ok else "✗"}  {ev.get("name", "")}', 'ok' if ok else 'red')
            self._write(f'   {ev.get("elapsed", 0):.0f} s' + (f' · {ev["summary"]}' if ev.get('summary') else '') + '\n', 'dim')
            self.btn.set('running', frac=ev.get('k', 0) / self.n)
        elif e == 'say':
            msg = ev.get('msg', '')
            m = re.search(r'done: (.+?\.ipa)\b', msg)
            if m: self.out_ipa = m.group(1)
            if '[RED]' in msg: self.warn.append(msg.split('[RED]', 1)[1].strip())
            self._write(msg + '\n', 'red' if '[RED]' in msg else 'dim')

    def _done(self, rc):
        self.proc = None; self.cancel.pack_forget()
        took = time.time() - self.started
        if rc == 0 and self.out_ipa:
            self.btn.set('done', 'Build again'); self.btn.frac = 0
            self.status.configure(text=f'Finished in {int(took) // 60}:{int(took) % 60:02d}' + (f'   ·   {len(self.warn)} warning(s), see details' if self.warn else ''),
                                  fg=MUTED)
            data = Path(self.out_ipa).with_name(Path(self.out_ipa).stem + '-data')
            if self.split and data.is_dir():
                self.res_path.configure(text=f'{self.out_ipa}\n{data}')
                self.res_hint.configure(text="Install the IPA in LiveContainer, then copy the data folder into the app's Documents\n(Files app, or the Apple Devices app on Windows). README.txt inside it explains.")
            else:
                self.res_path.configure(text=self.out_ipa); self.res_hint.configure(text='Install it in LiveContainer.')
            self.result.pack(fill='x', pady=(14, 0), before=self.det if self.details else None)
            self._write(f'\nIPA ready  →  {self.out_ipa}\n', 'ok')
        else:
            self._refresh()
            last = self.warn[-1] if self.warn else ''
            self.status.configure(text=('Build stopped: ' + last[:140] + ('…' if len(last) > 140 else '')) if last else ('Build stopped. See details.' if rc else 'Finished, but the log named no IPA.'), fg=BAD)
            if rc and not getattr(self, 'cancelled', False):
                self._write(f'\nThe build stopped (exit code {rc}). Each stage\'s full log is in <TitleID>_build\\logs next to the game files.\n', 'red')
                if not self.details: self._toggle_details()
            self.cancelled = False

    def _doctor_done(self, bad):
        if not bad: self._pill('All tools ready', OK); return
        self._pill(f'{len(bad)} tools missing', BAD)
        self._write('Missing tools (python win\\doctor.py explains each):\n', 'red')
        for r in bad: self._write(f'  • {r["name"]}' + (f' — {r["how"]}' if r.get('how') else '') + '\n', 'red')
        if not self.details: self._toggle_details()

    def _open_out(self):
        if self.out_ipa and Path(self.out_ipa).exists(): subprocess.run(['explorer', '/select,', str(Path(self.out_ipa))])

    def _write(self, text, tag=None):
        self.log.configure(state='normal'); self.log.insert('end', text, tag); self.log.see('end'); self.log.configure(state='disabled')

    def _clear_log(self):
        self.log.configure(state='normal'); self.log.delete('1.0', 'end'); self.log.configure(state='disabled')

    def _close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno('Build running', 'Stop the build and close?'): return
            self._cancel()
        self.s.update(files=self.files, keys=self.keys); save_settings(self.s)
        self.destroy()


if __name__ == '__main__':
    try:
        import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sharp text on scaled displays
    except Exception: pass
    App().mainloop()
