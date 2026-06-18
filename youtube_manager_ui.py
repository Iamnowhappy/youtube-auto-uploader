"""
YouTube 자동화 통합 관리 UI  v4
탭 구성:
  🏠 대시보드   — 시트 현황 실시간 표시
  🚀 영상 처리  — 드롭박스 업로드 + 예약 배정 (기존)
  ⚡ 즉시 업로드 — 파일 선택 → 드롭박스 → YouTube 직행 (신규)
  ⚙️  설정       — 키/경로 저장
"""

import os, sys, json, time, re, threading, tempfile, webbrowser
from pathlib import Path
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

sys.path.insert(0, str(Path(__file__).parent))

KST = timezone(timedelta(hours=9))

CHANNEL_NAMES = {
    "1": "데일리인사이트",   "2": "모먼트랩",
    "3": "생활정보TV",       "4": "오늘의회사썰",
    "5": "행복시니어TV",     "6": "데일리AI브리핑",
    "7": "HealthierLivingToday", "8": "TalkToMeInKorean",
    "9": "GlobalTopTier",
}
CHANNEL_MAP = {
    "1": "UCuyhcW0c4QCcCRtA5oeMn1w", "2": "UCMujLGISA9sRh0ki9H5xXLg",
    "3": "UCqr08lng11l-14li4vaLc3g",  "4": "UC7wgb4aG0ytHl8MtOJwNBfw",
    "5": "UCjysxDKwgwejYuMx3-WDKjg",  "6": "UCw8ETbGpdnXc8NJpdgmwrqw",
    "7": "UCAdzqsKoItMWxKmhoC8aSrg",  "8": "UCjdqO74OEmNt9EL4H33VWUQ",
    "9": "UCQ7JqaT39C1IuDelJcNVI1Q",
}
STATUS_COLOR = {"기록전": "#f59e0b", "업로드전": "#3b82f6", "업로드완료": "#22c55e"}
CONFIG_PATH  = Path(__file__).parent / "config.json"

# ───────────────────────────────────────────────
# 색상 팔레트
# ───────────────────────────────────────────────
BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
BORDER  = "#30363d"
TEXT    = "#e6edf3"
TEXT2   = "#8b949e"
BLUE    = "#58a6ff"
GREEN   = "#3fb950"
YELLOW  = "#d29922"
RED     = "#f85149"
PURPLE  = "#bc8cff"
ORANGE  = "#e3b341"

# ═══════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube 자동화 관리자  v4")
        self.geometry("1060x800")
        self.minsize(920, 680)
        self.configure(bg=BG)
        self.cfg = self._load_cfg()
        self._build()
        self.after(700, self._refresh_sheet)
        self.after(900, self._show_login_reminder)

    def _show_login_reminder(self):
        messagebox.showwarning(
            "⚠️ 구글 로그인 확인",
            "구글 시트는 반드시\n\n"
            "        a34365460@gmail.com\n\n"
            "계정으로 로그인되어 있어야 수정됩니다.\n"
            "(다른 계정이면 시트 수정 불가)")
        webbrowser.open("https://docs.google.com/spreadsheets/d/1VGHH_xkbNWKfzMLWIXeJRM3GHvjVEm_nvZM8FEhTK40/edit?gid=0#gid=0")

    # ── 설정 ────────────────────────────────────
    def _load_cfg(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cfg(self):
        cfg = {
            "sheet_id":              self.v_sheet_id.get().strip(),
            "sheet_name":            self.v_sheet_name.get().strip() or "숏츠시트",
            "google_sa_path":        self.v_sa.get().strip(),
            "dropbox_app_key":       self.v_dbx_key.get().strip(),
            "dropbox_app_secret":    self.v_dbx_sec.get().strip(),
            "dropbox_refresh_token": self.v_dbx_tok.get().strip(),
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self.cfg = cfg
        messagebox.showinfo("저장", "✅ 설정이 저장되었습니다.")

    # ── 메인 UI ─────────────────────────────────
    def _build(self):
        # ── 헤더
        hdr = tk.Frame(self, bg=BG, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="▶  YouTube 자동화 관리자",
                 font=("Malgun Gothic", 16, "bold"),
                 fg=TEXT, bg=BG).pack(side="left", padx=20, pady=10)
        self._lbl_clock = tk.Label(hdr, text="", font=("Consolas", 9),
                                    fg=TEXT2, bg=BG)
        self._lbl_clock.pack(side="right", padx=20)
        self._tick()
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Notebook
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("X.TNotebook",       background=BG, borderwidth=0, tabmargins=0)
        s.configure("X.TNotebook.Tab",   background=BG2, foreground=TEXT2,
                    padding=[16, 8], font=("Malgun Gothic", 10))
        s.map("X.TNotebook.Tab",
              background=[("selected", BG3)],
              foreground=[("selected", BLUE)])
        s.configure("X.Treeview",
                    background=BG2, foreground=TEXT,
                    fieldbackground=BG2, rowheight=26,
                    font=("Malgun Gothic", 9))
        s.configure("X.Treeview.Heading",
                    background=BG3, foreground=TEXT2,
                    font=("Malgun Gothic", 9, "bold"), relief="flat")
        s.map("X.Treeview", background=[("selected", "#1f6feb")])

        nb = ttk.Notebook(self, style="X.TNotebook")
        nb.pack(fill="both", expand=True, padx=10, pady=8)
        self.nb = nb

        self.t_dash = tk.Frame(nb, bg=BG2)
        self.t_run  = tk.Frame(nb, bg=BG2)
        self.t_now  = tk.Frame(nb, bg=BG2)   # ⚡ 즉시 업로드 (신규)
        self.t_cfg  = tk.Frame(nb, bg=BG2)

        nb.add(self.t_dash, text="  🏠  대시보드  ")
        nb.add(self.t_run,  text="  📅  예약 업로드  ")
        nb.add(self.t_now,  text="  ⚡  즉시 업로드  ")
        nb.add(self.t_cfg,  text="  ⚙️   설정  ")

        self._build_dash()
        self._build_run()
        self._build_now()
        self._build_cfg()

    # ════════════════════════════════════════════
    # 탭 1 : 대시보드
    # ════════════════════════════════════════════
    def _build_dash(self):
        p = self.t_dash

        # 카드 행
        cr = tk.Frame(p, bg=BG2)
        cr.pack(fill="x", padx=14, pady=12)
        self._c_total   = self._card(cr, "전체",      "0", TEXT2)
        self._c_rec     = self._card(cr, "기록전",    "0", YELLOW)
        self._c_ready   = self._card(cr, "업로드전",  "0", BLUE)
        self._c_done    = self._card(cr, "완료",      "0", GREEN)
        for c in [self._c_total, self._c_rec, self._c_ready, self._c_done]:
            c.pack(side="left", padx=5, fill="x", expand=True)

        # 툴바
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1VGHH_xkbNWKfzMLWIXeJRM3GHvjVEm_nvZM8FEhTK40/edit?gid=0#gid=0"
        tb = tk.Frame(p, bg=BG2)
        tb.pack(fill="x", padx=14, pady=(0, 6))
        self._btn(tb, "🔄 새로고침", self._refresh_sheet,
                  BG3, BLUE).pack(side="left")
        self._btn(tb, "📊 구글 시트 열기",
                  lambda: webbrowser.open(SHEET_URL),
                  "#0d2b1f", GREEN).pack(side="left", padx=8)
        self._lbl_upd = tk.Label(tb, text="", font=("Malgun Gothic", 9),
                                  fg=TEXT2, bg=BG2)
        self._lbl_upd.pack(side="left", padx=10)

        # Treeview
        tf = tk.Frame(p, bg=BG3, bd=1, relief="solid")
        tf.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        cols = ("행","제목","채널","소스","예약시간","상태","링크")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                  style="X.Treeview")
        for col, w in zip(cols, [38, 270, 120, 72, 130, 80, 200]):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=30)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._open_link)

        # 태그 색상
        for st, col in STATUS_COLOR.items():
            self.tree.tag_configure(st, foreground=col)

    # ════════════════════════════════════════════
    # 탭 2 : 예약 업로드
    # ════════════════════════════════════════════
    def _build_run(self):
        # 스크롤 가능 컨테이너
        outer = self.t_run
        canvas = tk.Canvas(outer, bg=BG2, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        p = tk.Frame(canvas, bg=BG2)
        cwin = canvas.create_window((0, 0), window=p, anchor="nw")

        def _on_config(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        p.bind("<Configure>", _on_config)
        # 캔버스 폭에 맞춰 내부 프레임 폭 조정
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cwin, width=e.width))
        # 마우스 휠 스크롤
        def _on_wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_wheel)

        # 안내 배너
        self._banner(p,
            "📅  예약 업로드 흐름 (원클릭)\n"
            "① 제목 · 대본 입력 → 파일 선택 (경로 자동 입력)\n"
            "② '추가 + 업로드' 버튼 클릭 → 시트 추가 + 즉시 드롭박스 업로드 → 예약시간에 자동 YouTube 업로드",
            BLUE)

        # 파일 선택 섹션
        s1 = self._sec(p, "📁  로컬 영상 파일 선택")
        drop = tk.Frame(s1, bg="#0d1f33", cursor="hand2", bd=2, relief="solid")
        drop.pack(fill="x", padx=12, pady=(6, 6))
        drop_lbl = tk.Label(drop,
                 text="📂  여기를 클릭하여 영상 파일 선택\n(mp4 / mov — 여러 개 선택 가능)",
                 font=("Malgun Gothic", 12, "bold"), fg=BLUE, bg="#0d1f33",
                 pady=24, cursor="hand2")
        drop_lbl.pack(fill="x")
        # 영역 전체 + 라벨 모두 클릭 가능
        drop.bind("<Button-1>", lambda e: self._pick_run_file())
        drop_lbl.bind("<Button-1>", lambda e: self._pick_run_file())

        self.run_lb = tk.Listbox(s1, bg=BG, fg=TEXT, font=("Consolas", 10),
                                  height=4, selectmode="extended",
                                  highlightthickness=0, bd=0)
        self.run_lb.pack(fill="x", padx=12)

        br = tk.Frame(s1, bg=BG3)
        br.pack(fill="x", padx=12, pady=6)
        tk.Button(br, text="🗑  목록 지우기",
                  command=lambda: self.run_lb.delete(0, "end"),
                  font=("Malgun Gothic", 10, "bold"),
                  fg="#ffffff", bg="#6e2730",
                  activebackground="#8a3540", activeforeground="#fff",
                  cursor="hand2", bd=0, padx=16, pady=7
                  ).pack(side="left")

        # 채널 / 제목
        cr2 = tk.Frame(s1, bg=BG3)
        cr2.pack(fill="x", padx=12, pady=(6, 4))
        tk.Label(cr2, text="채널:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3).pack(side="left")
        self.run_ch = tk.StringVar(value="1")
        ttk.Combobox(cr2, textvariable=self.run_ch, state="readonly", width=24,
                     values=[f"{k} - {v}" for k, v in CHANNEL_NAMES.items()]
                     ).pack(side="left", padx=6)
        tk.Label(cr2, text="제목:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3).pack(side="left", padx=(14, 0))
        self.run_title = tk.StringVar()
        tk.Entry(cr2, textvariable=self.run_title, bg=BG, fg=TEXT,
                 insertbackground=TEXT, font=("Malgun Gothic", 10),
                 width=40, bd=0, highlightthickness=1,
                 highlightcolor=BORDER).pack(side="left", padx=6)

        # 대본 / 설명 입력
        cr3 = tk.Frame(s1, bg=BG3)
        cr3.pack(fill="x", padx=12, pady=(2, 4))
        tk.Label(cr3, text="대본/설명:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3, anchor="nw").pack(side="left", anchor="n")
        self.run_desc = tk.Text(cr3, bg=BG, fg=TEXT, insertbackground=TEXT,
                                 font=("Malgun Gothic", 10), height=3,
                                 bd=0, highlightthickness=1, highlightcolor=BORDER)
        self.run_desc.pack(side="left", fill="x", expand=True, padx=6)

        # PC 파일경로 (파일 선택 시 자동 채워짐, 직접 수정도 가능)
        cr4 = tk.Frame(s1, bg=BG3)
        cr4.pack(fill="x", padx=12, pady=(2, 6))
        tk.Label(cr4, text="PC 경로:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3).pack(side="left")
        self.run_path = tk.StringVar()
        tk.Entry(cr4, textvariable=self.run_path, bg=BG, fg=TEXT,
                 insertbackground=TEXT, font=("Consolas", 9),
                 bd=0, highlightthickness=1,
                 highlightcolor=BORDER).pack(side="left", fill="x",
                                             expand=True, padx=6)
        tk.Label(cr4, text="(위 파일선택 시 자동 입력)",
                 font=("Malgun Gothic", 8), fg=TEXT2, bg=BG3).pack(side="left")

        # ── 예약 일시 직접 입력 (항상 활성화)
        sched_row = tk.Frame(s1, bg=BG3)
        sched_row.pack(fill="x", padx=12, pady=(2, 8))

        tk.Label(sched_row, text="예약 일시  →  날짜:",
                 font=("Malgun Gothic", 10, "bold"), fg=TEXT2, bg=BG3
                 ).pack(side="left")

        self.run_sched_date = tk.StringVar(
            value=datetime.now(KST).strftime("%Y-%m-%d"))
        self._sched_date_ent = tk.Entry(
            sched_row, textvariable=self.run_sched_date,
            bg=BG, fg=TEXT, insertbackground=TEXT,
            font=("Malgun Gothic", 11), width=12,
            bd=0, highlightthickness=1, highlightcolor=BORDER)
        self._sched_date_ent.pack(side="left", padx=(6, 0))

        tk.Label(sched_row, text="  시간:",
                 font=("Malgun Gothic", 10, "bold"), fg=TEXT2, bg=BG3
                 ).pack(side="left")

        self.run_sched_time = tk.StringVar(value="17:00")
        self._sched_time_cb = ttk.Combobox(
            sched_row, textvariable=self.run_sched_time,
            width=8, state="readonly",
            values=["09:00","10:00","11:00","12:00","13:00","14:00",
                    "15:00","16:00","17:00","18:00","19:00","20:00",
                    "21:00","22:00","23:00"])
        self._sched_time_cb.pack(side="left", padx=6)

        tk.Label(sched_row, text="KST   ← '직접 입력 시간으로 실행' 버튼에만 적용됨",
                 font=("Malgun Gothic", 9), fg=TEXT2, bg=BG3
                 ).pack(side="left")

        # ── 메인 실행 — 원스톱 버튼 2개 (추가 + 즉시 드롭박스 업로드)
        s2 = self._sec(p, "🚀  시트 추가 + 드롭박스 즉시 업로드  (원클릭)")
        tk.Label(s2,
                 text="위 입력값(제목·대본·경로)을 시트에 추가하고, 드롭박스에 지금 바로 업로드합니다.\n"
                      "YouTube 업로드는 아래 예약 시간에 GitHub Actions 가 자동 실행합니다.\n"
                      "• 🗓 자동 슬롯 : 17:00 / 19:00 빈 시간에 자동 배정\n"
                      "• ⏰ 직접 입력 : 위에서 고른 날짜·시간으로 예약",
                 font=("Malgun Gothic", 9), fg=TEXT2, bg=BG3,
                 justify="left").pack(anchor="w", padx=12, pady=(4, 6))

        btn_row2 = tk.Frame(s2, bg=BG3)
        btn_row2.pack(fill="x", padx=12, pady=(0, 8))

        tk.Button(btn_row2,
                  text="🗓  추가 + 자동 슬롯 업로드",
                  font=("Malgun Gothic", 11, "bold"),
                  fg="#ffffff", bg="#1f6feb",
                  activebackground="#388bfd", activeforeground="#fff",
                  cursor="hand2", bd=0, pady=12,
                  command=lambda: self._add_and_upload(force_auto=True)
                  ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(btn_row2,
                  text="⏰  추가 + 직접 시간 업로드",
                  font=("Malgun Gothic", 11, "bold"),
                  fg="#ffffff", bg="#5a3e00",
                  activebackground="#7a5a00", activeforeground="#fff",
                  cursor="hand2", bd=0, pady=12,
                  command=lambda: self._add_and_upload(force_auto=False)
                  ).pack(side="left", fill="x", expand=True)

        # ── 보조 : 이미 시트에 입력해둔 '기록전' 행 일괄 처리
        s3 = self._sec(p, "🔁  시트에 이미 입력한 '기록전' 행 일괄 처리 (선택)")
        tk.Label(s3,
                 text="구글 시트에 직접 입력해둔 E열='기록전' 행들을 한 번에 드롭박스 업로드합니다.",
                 font=("Malgun Gothic", 9), fg=TEXT2, bg=BG3,
                 justify="left").pack(anchor="w", padx=12, pady=(4, 6))

        btn_row3 = tk.Frame(s3, bg=BG3)
        btn_row3.pack(fill="x", padx=12, pady=(0, 8))

        tk.Button(btn_row3,
                  text="🗓 자동 슬롯 일괄",
                  font=("Malgun Gothic", 10),
                  fg="#ffffff", bg=BG3,
                  activebackground="#374151", activeforeground="#fff",
                  cursor="hand2", bd=1, pady=8,
                  command=lambda: self._run_schedule(force_auto=True)
                  ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(btn_row3,
                  text="⏰ 직접 시간 일괄",
                  font=("Malgun Gothic", 10),
                  fg="#ffffff", bg=BG3,
                  activebackground="#374151", activeforeground="#fff",
                  cursor="hand2", bd=1, pady=8,
                  command=lambda: self._run_schedule(force_auto=False)
                  ).pack(side="left", fill="x", expand=True)

        # 로그
        self._log_run = self._logbox(p)

    # ════════════════════════════════════════════
    # 탭 3 : ⚡ 즉시 업로드 (신규)
    # ════════════════════════════════════════════
    def _build_now(self):
        p = self.t_now

        self._banner(p,
            "⚡  즉시 업로드 — 파일 선택 → 드롭박스 업로드 → YouTube 즉시 공개\n"
            "예약 없이 바로 올리고 싶을 때 사용합니다. 구글 시트에도 결과가 기록됩니다.",
            ORANGE)

        # 파일 선택
        s1 = self._sec(p, "📁  업로드할 영상 파일")
        drop2 = tk.Frame(s1, bg="#1a1200", cursor="hand2", bd=1, relief="solid")
        drop2.pack(fill="x", padx=12, pady=(4, 6))
        tk.Label(drop2,
                 text="📂  클릭하여 영상 파일 선택  (mp4 / mov)",
                 font=("Malgun Gothic", 10), fg=ORANGE, bg="#1a1200",
                 pady=14).pack()
        drop2.bind("<Button-1>", lambda e: self._pick(self.now_lb))

        self.now_lb = tk.Listbox(s1, bg=BG, fg=TEXT, font=("Consolas", 9),
                                  height=3, selectmode="extended",
                                  highlightthickness=0, bd=0)
        self.now_lb.pack(fill="x", padx=12)

        br = tk.Frame(s1, bg=BG3)
        br.pack(fill="x", padx=12, pady=4)
        self._btn(br, "파일 선택",  lambda: self._pick(self.now_lb), BG3, ORANGE
                  ).pack(side="left", padx=(0, 6))
        self._btn(br, "목록 지우기", lambda: self.now_lb.delete(0, "end"), BG3, RED
                  ).pack(side="left")

        # 채널 / 제목 / 설명
        s2 = self._sec(p, "📋  업로드 정보")
        g = tk.Frame(s2, bg=BG3)
        g.pack(fill="x", padx=12, pady=(4, 8))

        def lbl_ent(parent, text, var, row, width=36, show=""):
            tk.Label(parent, text=text, font=("Malgun Gothic", 10, "bold"),
                     fg=TEXT2, bg=BG3, anchor="w", width=10
                     ).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 6))
            e = tk.Entry(parent, textvariable=var, show=show,
                         bg=BG, fg=TEXT, insertbackground=TEXT,
                         font=("Malgun Gothic", 10), width=width,
                         bd=0, highlightthickness=1, highlightcolor=BORDER)
            e.grid(row=row, column=1, sticky="w", pady=4)
            return e

        self.now_ch    = tk.StringVar(value="1")
        self.now_title = tk.StringVar()

        # 채널 콤보
        tk.Label(g, text="채널:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3, anchor="w", width=10
                 ).grid(row=0, column=0, sticky="w", pady=4)
        ch_box = ttk.Combobox(g, textvariable=self.now_ch, state="readonly",
                               width=26,
                               values=[f"{k} - {v}" for k, v in CHANNEL_NAMES.items()])
        ch_box.grid(row=0, column=1, sticky="w", pady=4)

        lbl_ent(g, "제목:", self.now_title, 1, width=44)

        # 설명 (태그 포함)
        tk.Label(g, text="설명/태그:", font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT2, bg=BG3, anchor="nw", width=10
                 ).grid(row=2, column=0, sticky="nw", pady=4)
        self.now_desc = tk.Text(g, bg=BG, fg=TEXT, insertbackground=TEXT,
                                 font=("Malgun Gothic", 9), width=50, height=4,
                                 bd=0, highlightthickness=1, highlightcolor=BORDER)
        self.now_desc.grid(row=2, column=1, sticky="w", pady=4)
        self.now_desc.insert("end", "#shorts ")

        # 시트 기록 여부
        self.now_sheet = tk.BooleanVar(value=True)
        tk.Checkbutton(g, text="구글 시트에 결과 기록",
                       variable=self.now_sheet,
                       fg=TEXT2, bg=BG3, selectcolor=BG,
                       activebackground=BG3, activeforeground=TEXT,
                       font=("Malgun Gothic", 9)
                       ).grid(row=3, column=1, sticky="w", pady=(2, 0))

        # 실행 버튼 2개
        btn_row = tk.Frame(p, bg=BG2)
        btn_row.pack(fill="x", padx=14, pady=6)

        tk.Button(btn_row,
                  text="📦  드롭박스만 업로드",
                  font=("Malgun Gothic", 11, "bold"),
                  fg="#ffffff", bg="#5a3e00",
                  activebackground="#7a5a00",
                  cursor="hand2", bd=0, pady=10,
                  command=self._now_dropbox_only
                  ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(btn_row,
                  text="🚀  드롭박스 → YouTube 즉시 업로드",
                  font=("Malgun Gothic", 11, "bold"),
                  fg="#ffffff", bg="#7c2d12",
                  activebackground="#9a3d18",
                  cursor="hand2", bd=0, pady=10,
                  command=self._now_full_upload
                  ).pack(side="left", fill="x", expand=True)

        # 진행바
        self.now_prog = ttk.Progressbar(p, mode="indeterminate", length=200)
        self.now_prog.pack(fill="x", padx=14, pady=(4, 0))

        # 로그
        self._log_now = self._logbox(p)

    # ════════════════════════════════════════════
    # 탭 4 : 설정
    # ════════════════════════════════════════════
    def _build_cfg(self):
        p = self.t_cfg
        cv = tk.Canvas(p, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(p, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(fill="both", expand=True)
        inn = tk.Frame(cv, bg=BG2)
        cv.create_window((0, 0), window=inn, anchor="nw")
        inn.bind("<Configure>",
                 lambda e: cv.configure(scrollregion=cv.bbox("all")))

        def row(parent, lbl, var, show="", w=52, browse=None):
            f = tk.Frame(parent, bg=BG3)
            f.pack(fill="x", padx=14, pady=3)
            tk.Label(f, text=lbl, font=("Malgun Gothic", 10, "bold"),
                     fg=TEXT2, bg=BG3, width=22, anchor="w").pack(side="left")
            tk.Entry(f, textvariable=var, show=show,
                     bg=BG, fg=TEXT, insertbackground=TEXT,
                     font=("Malgun Gothic", 10), width=w,
                     bd=0, highlightthickness=1,
                     highlightcolor=BORDER).pack(side="left", padx=6)
            if browse:
                self._btn(f, "찾아보기", browse, BG3, BLUE).pack(side="left")

        # 구글
        s1 = self._sec(inn, "🔑  구글 서비스 계정 / 시트")
        self.v_sa         = tk.StringVar(value=self.cfg.get("google_sa_path", ""))
        self.v_sheet_id   = tk.StringVar(value=self.cfg.get("sheet_id", ""))
        self.v_sheet_name = tk.StringVar(value=self.cfg.get("sheet_name", "숏츠시트"))
        row(s1, "서비스 계정 JSON", self.v_sa,
            browse=lambda: self._browse(self.v_sa, [("JSON","*.json")]))
        row(s1, "구글 시트 ID",     self.v_sheet_id)
        row(s1, "시트명",           self.v_sheet_name, w=20)
        tk.Label(s1, text="  ℹ️  시트 ID = URL의 /spreadsheets/d/  뒷 부분",
                 font=("Malgun Gothic", 8), fg=TEXT2, bg=BG3
                 ).pack(anchor="w", padx=14, pady=(0, 8))

        # 드롭박스
        s2 = self._sec(inn, "📦  드롭박스 API")
        self.v_dbx_key = tk.StringVar(value=self.cfg.get("dropbox_app_key", ""))
        self.v_dbx_sec = tk.StringVar(value=self.cfg.get("dropbox_app_secret", ""))
        self.v_dbx_tok = tk.StringVar(value=self.cfg.get("dropbox_refresh_token", ""))
        row(s2, "App Key",       self.v_dbx_key)
        row(s2, "App Secret",    self.v_dbx_sec, show="•")
        row(s2, "Refresh Token", self.v_dbx_tok, show="•", w=58)
        tk.Label(s2, text="  ℹ️  youtube-uploader2 앱 기준으로 입력",
                 font=("Malgun Gothic", 8), fg=TEXT2, bg=BG3
                 ).pack(anchor="w", padx=14, pady=(0, 8))

        # 예약 정책 안내
        s3 = self._sec(inn, "📅  예약 슬롯 정책")
        tk.Label(s3,
                 text="  • 하루 최대 2개 슬롯 : 17:00 KST / 19:00 KST\n"
                      "  • 초과 시 다음날로 자동 이월 (최대 14일 탐색)\n"
                      "  • 수동 지정 : 구글 시트 G열에 직접 입력  예) 2026-05-27 21:00",
                 font=("Malgun Gothic", 9), fg=TEXT2, bg=BG3,
                 justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        # 저장 + 테스트
        self._btn(inn, "💾  설정 저장", self._save_cfg,
                  "#0d2b1f", GREEN, 11).pack(fill="x", padx=14, pady=(8, 4))
        br = tk.Frame(inn, bg=BG2)
        br.pack(fill="x", padx=14, pady=(0, 20))
        self._btn(br, "🔗  시트 연결 테스트",
                  self._test_sheet, BG3, GREEN).pack(side="left", padx=(0, 8))
        self._btn(br, "📦  드롭박스 연결 테스트",
                  self._test_dbx,  BG3, GREEN).pack(side="left")

    # ════════════════════════════════════════════
    # 공통 위젯 헬퍼
    # ════════════════════════════════════════════
    def _card(self, parent, label, val, color):
        f = tk.Frame(parent, bg=BG3)
        tk.Label(f, text=label, font=("Malgun Gothic", 9),
                 fg=TEXT2, bg=BG3).pack(pady=(10, 2))
        lv = tk.Label(f, text=val, font=("Malgun Gothic", 20, "bold"),
                       fg=color, bg=BG3)
        lv.pack(pady=(0, 10))
        f._v = lv
        return f

    def _set_card(self, card, val):
        card._v.config(text=str(val))

    def _sec(self, parent, title):
        f = tk.Frame(parent, bg=BG3)
        f.pack(fill="both", expand=True, padx=14, pady=(8, 0))
        tk.Label(f, text=title, font=("Malgun Gothic", 10, "bold"),
                 fg=TEXT, bg=BG3).pack(anchor="w", padx=10, pady=(8, 4))
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=10)
        return f

    def _banner(self, parent, text, color):
        f = tk.Frame(parent, bg=BG3)
        f.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(f, text=text, font=("Malgun Gothic", 9),
                 fg=color, bg=BG3, justify="left",
                 wraplength=860).pack(padx=10, pady=8, anchor="w")

    def _btn(self, parent, text, cmd, bg, fg, size=9):
        return tk.Button(parent, text=text, command=cmd,
                         font=("Malgun Gothic", size),
                         fg=fg, bg=bg,
                         activebackground="#4b5563",
                         activeforeground="#fff",
                         cursor="hand2", bd=0, padx=10, pady=5)

    def _logbox(self, parent):
        s = self._sec(parent, "📋  실행 로그")
        box = scrolledtext.ScrolledText(
            s, bg=BG, fg="#a3e635", font=("Consolas", 9),
            height=8, insertbackground="#a3e635",
            highlightthickness=0, bd=0, state="disabled")
        box.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self._btn(s, "로그 지우기",
                  lambda: self._clear_log(box), BG3, TEXT2
                  ).pack(anchor="e", padx=10, pady=(0, 8))
        return box

    def _log(self, box, msg):
        def _do():
            box.config(state="normal")
            ts = datetime.now(KST).strftime("%H:%M:%S")
            box.insert("end", f"[{ts}] {msg}\n")
            box.see("end")
            box.config(state="disabled")
        self.after(0, _do)

    def _clear_log(self, box):
        box.config(state="normal")
        box.delete("1.0", "end")
        box.config(state="disabled")

    def _pick(self, listbox):
        files = filedialog.askopenfilenames(
            title="영상 파일 선택",
            filetypes=[("영상", "*.mp4 *.mov *.avi *.mkv"), ("모두", "*.*")])
        for f in files:
            listbox.insert("end", f)

    def _pick_run_file(self):
        """예약 탭 전용 — 파일 선택 시 목록 + PC경로 칸 + 제목 자동 채움"""
        files = filedialog.askopenfilenames(
            title="영상 파일 선택",
            filetypes=[("영상", "*.mp4 *.mov *.avi *.mkv"), ("모두", "*.*")])
        if not files:
            return
        self.run_lb.delete(0, "end")
        for f in files:
            self.run_lb.insert("end", f)
        # 첫 파일 경로를 PC경로 칸에 채움
        self.run_path.set(files[0])
        # 제목 비어있으면 파일명으로 자동 채움
        if not self.run_title.get().strip():
            self.run_title.set(Path(files[0]).stem)

    def _browse(self, var, ftypes):
        fp = filedialog.askopenfilename(filetypes=ftypes)
        if fp:
            var.set(fp)

    def _tick(self):
        self._lbl_clock.config(
            text=datetime.now(KST).strftime("%Y-%m-%d  %H:%M:%S  KST"))
        self.after(1000, self._tick)

    # ════════════════════════════════════════════
    # 대시보드 데이터
    # ════════════════════════════════════════════
    def _refresh_sheet(self):
        self._lbl_upd.config(text="불러오는 중...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        try:
            from genspark_to_dropbox import get_sheet
            sheet = get_sheet(self.cfg)
            rows  = sheet.get_all_values()
            self.after(0, lambda: self._fill_table(rows))
        except Exception as e:
            self.after(0, lambda: self._lbl_upd.config(
                text=f"❌ {str(e)[:60]}"))

    def _fill_table(self, rows):
        for i in self.tree.get_children():
            self.tree.delete(i)
        cnt = {"기록전": 0, "업로드전": 0, "업로드완료": 0}
        for i, row in enumerate(rows[1:], start=2):
            while len(row) < 8:
                row.append("")
            st  = row[4].strip()
            src = "로컬" if (row[2].startswith("C:\\") or
                              row[2].startswith("/")) else "젠스파크"
            ch  = CHANNEL_NAMES.get(row[5].strip(), row[5])
            tag = st if st in STATUS_COLOR else "other"
            self.tree.insert("", "end",
                             values=(i, row[0][:38], ch, src,
                                     row[6], st, row[7]),
                             tags=(tag,))
            if st in cnt:
                cnt[st] += 1
        self._set_card(self._c_total,  len(rows) - 1)
        self._set_card(self._c_rec,    cnt["기록전"])
        self._set_card(self._c_ready,  cnt["업로드전"])
        self._set_card(self._c_done,   cnt["업로드완료"])
        self._lbl_upd.config(
            text="업데이트: " + datetime.now(KST).strftime("%H:%M:%S"))

    def _open_link(self, ev):
        item = self.tree.focus()
        if not item:
            return
        v = self.tree.item(item)["values"]
        if len(v) >= 7 and v[6]:
            webbrowser.open(str(v[6]))

    # ════════════════════════════════════════════
    # 예약 업로드 탭 — 액션
    # ════════════════════════════════════════════
    def _add_to_sheet(self):
        ch    = self.run_ch.get().split(" - ")[0].strip()
        title = self.run_title.get().strip()
        desc  = self.run_desc.get("1.0", "end").strip()
        path  = self.run_path.get().strip()

        # PC경로 칸이 채워져 있으면 → 직접 입력 방식 (제목+대본+경로 1행)
        if path:
            if not title:
                title = Path(path).stem
            if not desc:
                if not messagebox.askyesno("대본 비어있음",
                        "대본/설명이 비어있습니다.\n그래도 추가할까요?"):
                    return
            rows_to_add = [(title, desc, path)]
        else:
            # PC경로 비어있으면 → 파일 목록 방식 (여러 파일, 대본 없이)
            files = list(self.run_lb.get(0, "end"))
            if not files:
                messagebox.showwarning("입력 없음",
                    "PC 경로를 입력하거나 영상 파일을 선택하세요.")
                return
            rows_to_add = []
            for fp in files:
                t = title if (title and len(files) == 1) else Path(fp).stem
                rows_to_add.append((t, desc, fp))

        def worker():
            try:
                from genspark_to_dropbox import get_sheet
                sheet = get_sheet(self.cfg)
                for t, d, fp in rows_to_add:
                    # A제목 B대본 C경로 D빈 E기록전 F채널 G빈
                    sheet.append_row([t, d, fp, "", "기록전", ch, ""])
                    self._log(self._log_run, f"✅ 시트 추가: {t}")
                self.after(0, self._refresh_sheet)
                self.after(0, lambda: messagebox.showinfo(
                    "완료", f"{len(rows_to_add)}개 행이 시트에 추가되었습니다."))
                # 입력란 초기화
                self.after(0, self._clear_run_inputs)
            except Exception as e:
                self._log(self._log_run, f"❌ 오류: {e}")
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _clear_run_inputs(self):
        """예약 탭 입력란 초기화"""
        self.run_title.set("")
        self.run_path.set("")
        self.run_desc.delete("1.0", "end")
        self.run_lb.delete(0, "end")

    def _add_and_upload(self, force_auto=True):
        """입력 → 시트 행 추가 → 즉시 드롭박스 업로드 → 예약시간 기록 (원스톱)"""
        ch    = self.run_ch.get().split(" - ")[0].strip()
        title = self.run_title.get().strip()
        desc  = self.run_desc.get("1.0", "end").strip()
        path  = self.run_path.get().strip()

        # 입력 확인
        if not path:
            messagebox.showwarning("입력 없음",
                "PC 경로를 입력하거나 위에서 영상 파일을 선택하세요.")
            return
        norm = path  # 경로 정규화는 엔진에서 처리
        if not title:
            title = Path(path).stem

        # 수동 시간 검증
        manual_slot = ""
        if not force_auto:
            d = self.run_sched_date.get().strip()
            t = self.run_sched_time.get().strip()
            manual_slot = f"{d} {t}"
            try:
                dt_check = datetime.strptime(manual_slot, "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("입력 오류",
                    f"날짜/시간 형식이 잘못되었습니다.\n예시: 2026-06-09 17:00")
                return

        # 확인 팝업
        when = "자동 슬롯 (17:00/19:00)" if force_auto else f"{manual_slot} KST"
        if not messagebox.askyesno("추가 + 업로드 확인",
                f"📺 채널: {CHANNEL_NAMES.get(ch, ch)}\n"
                f"📝 제목: {title}\n"
                f"📅 예약: {when}\n\n"
                f"시트에 추가하고 지금 바로 드롭박스에 업로드합니다.\n계속할까요?"):
            return

        self._clear_log(self._log_run)
        self._log(self._log_run, "=" * 44)
        self._log(self._log_run, f"🚀 추가 + 드롭박스 업로드 시작")
        self._log(self._log_run, "=" * 44)

        def worker():
            try:
                from genspark_to_dropbox import get_sheet, process_pending_rows
                # ① 시트에 행 추가
                sheet = get_sheet(self.cfg)
                sheet.append_row([title, desc, path, "", "기록전", ch, ""])
                self._log(self._log_run, f"✅ 시트 추가: {title}")
                # ② 즉시 드롭박스 업로드 + 예약 배정
                r = process_pending_rows(
                    self.cfg,
                    log_fn=lambda m: self._log(self._log_run, m),
                    manual_slot=manual_slot if not force_auto else "")
                msg = (f"완료!\n✅ 성공 {r['success']}  "
                       f"⏭ 건너뜀 {r['skip']}  ❌ 오류 {r['error']}")
                self.after(0, lambda: messagebox.showinfo("완료", msg))
                self.after(0, self._clear_run_inputs)
                self.after(500, self._refresh_sheet)
            except Exception as e:
                self._log(self._log_run, f"❌ 오류: {e}")
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _run_schedule(self, force_auto=True):
        # 수동 시간 검증
        manual_slot = ""
        if not force_auto:
            d = self.run_sched_date.get().strip()
            t = self.run_sched_time.get().strip()
            manual_slot = f"{d} {t}"
            try:
                dt_check = datetime.strptime(manual_slot, "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("입력 오류",
                    f"날짜/시간 형식이 잘못되었습니다.\n"
                    f"입력값: {manual_slot}\n예시: 2026-06-08 19:00")
                return
            # 과거 시간 경고
            if dt_check.replace(tzinfo=KST) <= datetime.now(KST):
                if not messagebox.askyesno("과거 시간 확인",
                        f"입력한 시간이 현재보다 과거입니다.\n"
                        f"{manual_slot} KST\n\n"
                        f"이 경우 GitHub Actions 가 즉시 업로드합니다.\n계속할까요?"):
                    return
            confirm = messagebox.askyesno("직접 입력 시간 확인",
                f"⏰ 예약 시간: {manual_slot} KST\n\n"
                f"E열='기록전' 인 모든 행을 이 시간으로 예약합니다.\n계속할까요?")
            if not confirm:
                return

        self._clear_log(self._log_run)
        self._log(self._log_run, "=" * 44)
        if force_auto:
            self._log(self._log_run, "🗓 자동 슬롯 배정으로 실행 (17:00 / 19:00)")
        else:
            self._log(self._log_run, f"⏰ 수동 지정 시간: {manual_slot} KST")
        self._log(self._log_run, "=" * 44)

        def worker():
            try:
                from genspark_to_dropbox import process_pending_rows
                r = process_pending_rows(
                    self.cfg,
                    log_fn=lambda m: self._log(self._log_run, m),
                    manual_slot=manual_slot if not force_auto else "")
                if r["success"] == 0 and r["skip"] == 0 and r["error"] == 0:
                    msg = ("처리할 행이 없습니다.\n\n"
                           "구글 시트에서 E열이 '기록전' 이고\n"
                           "C열에 파일경로/URL이 있는 행이 있는지 확인하세요.")
                    self.after(0, lambda: messagebox.showwarning("대상 없음", msg))
                else:
                    msg = (f"완료!\n✅ 성공 {r['success']}  "
                           f"⏭ 건너뜀 {r['skip']}  ❌ 오류 {r['error']}")
                    self.after(0, lambda: messagebox.showinfo("완료", msg))
                self.after(500, self._refresh_sheet)
            except Exception as e:
                self._log(self._log_run, f"❌ {e}")
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ════════════════════════════════════════════
    # ⚡ 즉시 업로드 탭 — 핵심 신규 기능
    # ════════════════════════════════════════════
    def _now_dropbox_only(self):
        """드롭박스 업로드만 수행 (YouTube 업로드 없음)"""
        files = list(self.now_lb.get(0, "end"))
        if not files:
            messagebox.showwarning("파일 없음", "영상 파일을 먼저 선택하세요.")
            return
        self._clear_log(self._log_now)
        self._log(self._log_now, "=" * 44)
        self._log(self._log_now, "📦 드롭박스 업로드 시작")
        self._log(self._log_now, "=" * 44)
        self.now_prog.start(12)

        def worker():
            try:
                from genspark_to_dropbox import get_dropbox, upload_local_to_dropbox
                dbx = get_dropbox(self.cfg)
                results = []
                for fp in files:
                    self._log(self._log_now, f"\n파일: {Path(fp).name}")
                    dl_url = upload_local_to_dropbox(
                        fp, dbx,
                        log_fn=lambda m: self._log(self._log_now, m))
                    results.append((fp, dl_url))
                    self._log(self._log_now, f"✅ URL: {dl_url}")

                # 시트 기록 여부
                if self.now_sheet.get():
                    self._write_dropbox_results_to_sheet(results)

                self.after(0, lambda: messagebox.showinfo(
                    "완료", f"드롭박스 업로드 완료!\n{len(results)}개 파일"))
            except Exception as e:
                self._log(self._log_now, f"❌ 오류: {e}")
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
            finally:
                self.after(0, self.now_prog.stop)
        threading.Thread(target=worker, daemon=True).start()

    def _now_full_upload(self):
        """드롭박스 업로드 + YouTube 즉시 공개"""
        files = list(self.now_lb.get(0, "end"))
        if not files:
            messagebox.showwarning("파일 없음", "영상 파일을 먼저 선택하세요.")
            return
        title = self.now_title.get().strip()
        desc  = self.now_desc.get("1.0", "end").strip()
        ch    = self.now_ch.get().split(" - ")[0].strip()
        ch_name = CHANNEL_NAMES.get(ch, ch)

        if not title and len(files) == 1:
            title = Path(files[0]).stem

        confirm = messagebox.askyesno(
            "즉시 업로드 확인",
            f"📺 채널: {ch_name}\n"
            f"📁 파일 {len(files)}개를\n"
            f"지금 바로 YouTube에 즉시 공개 업로드합니다.\n\n"
            f"계속하시겠습니까?")
        if not confirm:
            return

        self._clear_log(self._log_now)
        self._log(self._log_now, "=" * 44)
        self._log(self._log_now, f"🚀 즉시 업로드 시작 → 채널: {ch_name}")
        self._log(self._log_now, "=" * 44)
        self.now_prog.start(12)

        def worker():
            try:
                from genspark_to_dropbox import get_dropbox, upload_local_to_dropbox
                import json as _json
                from google.oauth2.credentials import Credentials as OC
                from google.auth.transport.requests import Request
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaFileUpload

                dbx = get_dropbox(self.cfg)
                yt_token = os.environ.get("YOUTUBE_TOKEN_JSON", "")

                # 로컬 token 파일 fallback
                if not yt_token:
                    tok_path = Path(__file__).parent / "youtube_token.json"
                    if tok_path.exists():
                        with open(tok_path, "r", encoding="utf-8") as f:
                            yt_token = f.read()

                if not yt_token:
                    raise FileNotFoundError(
                        "youtube_token.json 파일이 없습니다.\n"
                        "프로젝트 폴더에 youtube_token.json 을 배치해주세요.")

                token_data = _json.loads(yt_token)
                creds = OC(
                    token=token_data.get("token"),
                    refresh_token=token_data["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=token_data["client_id"],
                    client_secret=token_data["client_secret"],
                )
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                yt = build("youtube", "v3", credentials=creds)

                uploaded = []
                for idx, fp in enumerate(files):
                    f_title = title if (title and len(files) == 1) \
                                    else Path(fp).stem
                    self._log(self._log_now,
                              f"\n[{idx+1}/{len(files)}] {f_title}")

                    # ① 드롭박스
                    self._log(self._log_now, "  📦 드롭박스 업로드...")
                    dl_url = upload_local_to_dropbox(
                        fp, dbx,
                        log_fn=lambda m: self._log(self._log_now, m))

                    # ② YouTube 업로드
                    self._log(self._log_now, "  🎬 YouTube 업로드...")
                    f_desc = desc
                    tags = [w.lstrip("#") for w in f_desc.split()
                            if w.startswith("#")]
                    if "shorts" not in [t.lower() for t in tags]:
                        tags.insert(0, "shorts")
                    if "#shorts" not in f_desc.lower():
                        f_desc += "\n\n#shorts"

                    body = {
                        "snippet": {
                            "title": f_title[:100],
                            "description": f_desc[:5000],
                            "tags": tags[:500],
                            "categoryId": "22",
                            "channelId": CHANNEL_MAP.get(ch, CHANNEL_MAP["1"]),
                        },
                        "status": {
                            "privacyStatus": "public",   # 즉시 공개
                            "selfDeclaredMadeForKids": False,
                        }
                    }
                    media = MediaFileUpload(fp, mimetype="video/mp4",
                                            resumable=True,
                                            chunksize=1024 * 1024 * 5)
                    req  = yt.videos().insert(
                        part="snippet,status", body=body, media_body=media)
                    resp = None
                    while resp is None:
                        s_obj, resp = req.next_chunk()
                        if s_obj:
                            pct = int(s_obj.progress() * 100)
                            self._log(self._log_now, f"  ⬆️  {pct}%")
                    vid = resp["id"]
                    yt_url = f"https://youtube.com/shorts/{vid}"
                    self._log(self._log_now, f"  ✅ 완료: {yt_url}")
                    uploaded.append((fp, dl_url, yt_url, f_title))

                    # 연속 업로드 방지
                    if idx < len(files) - 1:
                        self._log(self._log_now, "  ⏳ 60초 대기...")
                        time.sleep(60)

                # 시트 기록
                if self.now_sheet.get():
                    self._write_full_results_to_sheet(uploaded, ch, desc)

                self.after(0, self._refresh_sheet)
                links = "\n".join(u[2] for u in uploaded)
                self.after(0, lambda: messagebox.showinfo(
                    "업로드 완료! 🎉",
                    f"{len(uploaded)}개 업로드 완료!\n\n{links}"))

            except Exception as e:
                self._log(self._log_now, f"❌ 오류: {e}")
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
            finally:
                self.after(0, self.now_prog.stop)

        threading.Thread(target=worker, daemon=True).start()

    def _write_dropbox_results_to_sheet(self, results):
        """드롭박스 전용 업로드 결과를 시트에 기록"""
        try:
            from genspark_to_dropbox import get_sheet
            sheet = get_sheet(self.cfg)
            ch    = self.now_ch.get().split(" - ")[0].strip()
            for fp, dl_url in results:
                t = self.now_title.get().strip() or Path(fp).stem
                sheet.append_row([
                    t, "", fp, dl_url, "업로드전", ch, "", ""
                ])
                self._log(self._log_now, f"  📝 시트 기록: {t}")
        except Exception as e:
            self._log(self._log_now, f"  ⚠️ 시트 기록 실패: {e}")

    def _write_full_results_to_sheet(self, uploaded, ch, desc):
        """즉시 업로드 결과 전체를 시트에 기록"""
        try:
            from genspark_to_dropbox import get_sheet
            sheet = get_sheet(self.cfg)
            now   = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
            for fp, dl_url, yt_url, title in uploaded:
                sheet.append_row([
                    title, desc[:200], fp, dl_url,
                    "업로드완료", ch, now, yt_url
                ])
                self._log(self._log_now, f"  📝 시트 기록: {title}")
        except Exception as e:
            self._log(self._log_now, f"  ⚠️ 시트 기록 실패: {e}")

    # ════════════════════════════════════════════
    # 설정 저장 / 테스트
    # ════════════════════════════════════════════
    def _save_cfg(self):
        cfg = {
            "sheet_id":              self.v_sheet_id.get().strip(),
            "sheet_name":            self.v_sheet_name.get().strip() or "숏츠시트",
            "google_sa_path":        self.v_sa.get().strip(),
            "dropbox_app_key":       self.v_dbx_key.get().strip(),
            "dropbox_app_secret":    self.v_dbx_sec.get().strip(),
            "dropbox_refresh_token": self.v_dbx_tok.get().strip(),
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self.cfg = cfg
        messagebox.showinfo("저장 완료", "✅ 설정이 저장되었습니다.")

    def _test_sheet(self):
        def w():
            try:
                from genspark_to_dropbox import get_sheet
                s = get_sheet(self.cfg)
                r = s.get_all_values()
                messagebox.showinfo("연결 성공",
                    f"✅ 구글 시트 연결 OK\n시트: {s.title}\n행: {len(r)-1}개")
            except Exception as e:
                messagebox.showerror("실패", f"❌ {e}")
        threading.Thread(target=w, daemon=True).start()

    def _test_dbx(self):
        def w():
            try:
                from genspark_to_dropbox import get_dropbox
                d   = get_dropbox(self.cfg)
                acc = d.users_get_current_account()
                messagebox.showinfo("연결 성공",
                    f"✅ 드롭박스 연결 OK\n계정: {acc.email}")
            except Exception as e:
                messagebox.showerror("실패", f"❌ {e}")
        threading.Thread(target=w, daemon=True).start()


# ═══════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()
