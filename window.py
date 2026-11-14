import re
import tkinter as tk
import tkinter.ttk as ttk
from datetime import date

import fileOperations
import remainDays
import theme
from translator import Translator

# 让 Windows 高分屏显示更清晰
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


LANG_ORDER = ["zh", "en", "ja"]
LANG_NAMES = {"zh": "中文", "en": "English", "ja": "日本語"}


def _normalize_birthday(text):
    """把生日文本规范成 "MM-DD"（允许 4-1、04/01 这类写法）；非法时返回 None。"""
    match = re.fullmatch(r"\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*", text or "")
    if match is None:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    try:
        # 用闰年（2000）校验，顺带允许 02-29
        date(2000, month, day)
    except ValueError:
        return None
    return f"{month:02d}-{day:02d}"


def _next_lang(current):
    """返回切换顺序中的下一个语言代码。"""
    return LANG_ORDER[(LANG_ORDER.index(current) + 1) % len(LANG_ORDER)]


def _top_characters(limit=5):
    """按生日剩余天数从近到远排序，返回前 limit 个 (英文名, 剩余天数)。"""
    remaining = remainDays.get_all_characters_remaining_days()
    items = [(name, days) for name, days in remaining.items() if days is not None]
    items.sort(key=lambda item: item[1])
    return items[:limit]


def _all_characters():
    """返回全部角色英文名列表，按生日临近排序（缺失生日的排最后）。"""
    remaining = remainDays.get_all_characters_remaining_days()
    items = [(name, days) for name, days in remaining.items()]
    items.sort(key=lambda item: (item[1] is None, item[1] if item[1] is not None else 0))
    return [name for name, _ in items]


def _bind_click(widget, callback):
    """给控件及其所有子控件绑定点击事件，并显示手型光标。"""
    widget.bind("<Button-1>", callback)
    try:
        widget.config(cursor="hand2")
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _bind_click(child, callback)


def build_window():
    translator = Translator()
    t = translator.translate

    root = tk.Tk()
    root.configure(bg=theme.BG)

    # 设置窗口尺寸，并使其在屏幕居中显示
    width, height = 380, 640
    root.update_idletasks()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(340, 520)

    # 让下拉框（Combobox）贴合现有配色
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "TCombobox",
        fieldbackground=theme.CARD_BG,
        background=theme.CARD_BG,
        foreground=theme.TEXT,
        arrowcolor=theme.SUBTEXT,
        bordercolor=theme.CARD_BORDER,
        lightcolor=theme.CARD_BG,
        darkcolor=theme.CARD_BG,
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme.CARD_BG)],
        selectbackground=[("readonly", theme.CARD_BG)],
        selectforeground=[("readonly", theme.TEXT)],
        foreground=[("readonly", theme.TEXT)],
    )
    root.option_add("*TCombobox*Listbox.font", theme.FONT_SUB)
    root.option_add("*TCombobox*Listbox.background", theme.CARD_BG)
    root.option_add("*TCombobox*Listbox.foreground", theme.TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", theme.RANK_BG)
    root.option_add("*TCombobox*Listbox.selectForeground", theme.TEXT)

    # 读取角色数据：日文名、最近生日 Top5、以及全部角色列表
    names = fileOperations.read_all_characters_names()
    characters = _top_characters(5)
    all_characters = _all_characters()
    top_count = len(characters)
    # 当前选中的角色（默认最近生日的角色）；下方两个容器用于记录卡片与徽章控件
    selected = {"en": characters[0][0] if characters else None}
    card_refs = {}
    card_badges = []

    # 今天日期：用于判断“今天生日”以及生成日期文案
    today = date.today()
    today_key = f"{today.month:02d}-{today.day:02d}"

    def _days_text(days):
        """把剩余天数转成显示文案，并标记是否为今天生日。"""
        if days == 0:
            return t("today"), True
        if days == 1:
            return t("tomorrow"), False
        return f"{days} {t('days_unit')}", False

    def _refresh_detail():
        # 根据当前选中的角色刷新详情区的名字、生日和秒级倒计时
        en_name = selected["en"]
        if en_name is None:
            detail_name.config(text=t("no_data"))
            detail_meta.config(text="")
            detail_countdown.config(text="--", fg=theme.ACCENT)
            return

        birthday = fileOperations.read_selected_character_birthday(en_name)
        detail_name.config(text=names.get(en_name, en_name))
        detail_meta.config(text=f"{t('birthday')} {birthday} · {en_name}")

        if birthday == today_key:
            detail_countdown.config(text=t("today"), fg=theme.ACCENT_TODAY)
            return

        countdown = remainDays.get_selected_character_countdown(en_name)
        if countdown is None:
            detail_countdown.config(text="--", fg=theme.ACCENT)
            return
        days, hours, minutes, seconds = countdown
        detail_countdown.config(
            text=f"{days}{t('days_unit')} {hours:02d}:{minutes:02d}:{seconds:02d}",
            fg=theme.ACCENT,
        )

    def _select(en_name):
        # 切换选中角色：同步下拉框显示、高亮对应卡片，并刷新详情
        selected["en"] = en_name
        if en_name in all_characters:
            combobox.current(all_characters.index(en_name))
        for en, (card, rank_frame, rank_label) in card_refs.items():
            if en == en_name:
                card.config(highlightbackground=theme.ACCENT)
                rank_frame.config(bg=theme.ACCENT)
                rank_label.config(bg=theme.ACCENT, fg="white")
            else:
                card.config(highlightbackground=theme.CARD_BORDER)
                rank_frame.config(bg=theme.RANK_BG)
                rank_label.config(bg=theme.RANK_BG, fg=theme.RANK_FG)
        _refresh_detail()

    def _refresh_badges():
        # 重新计算各卡片徽章的剩余天数，刷新文案与“今天生日”配色
        remaining = remainDays.get_all_characters_remaining_days()
        for badge, en_name in card_badges:
            days = remaining.get(en_name)
            if days is None:
                continue
            days_text, is_today = _days_text(days)
            badge.config(
                text=days_text,
                bg=theme.ACCENT_TODAY if is_today else theme.ACCENT,
            )

    def _tick():
        # 每秒刷新一次倒计时；跨天时重新排序卡片并刷新日期相关文案
        nonlocal today, today_key
        _refresh_detail()
        new_today = date.today()
        if new_today != today:
            today = new_today
            today_key = f"{today.month:02d}-{today.day:02d}"
            _build_cards()
            _apply_lang()
            if selected["en"] is not None:
                _select(selected["en"])
        root.after(1000, _tick)

    def _apply_lang():
        # 按当前语言刷新所有静态文案与徽章
        root.title(t("app_title"))
        title.config(text=t("app_title"))
        subtitle.config(text=t("date_format",
                               year=today.year, month=today.month, day=today.day))
        select_label.config(text=t("select_character"))
        detail_caption.config(text=t("until_next_birthday"))
        section.config(text=t("preview_title", top=top_count))
        footer.config(text=t("total_count", n=len(all_characters), top=top_count))
        lang_button.config(text=LANG_NAMES[translator.lang])
        add_button.config(text=f"＋ {t('add_character')}")
        _refresh_badges()
        _refresh_detail()

    def _toggle_lang():
        # 点击语言按钮：切换到下一语言并刷新界面文案
        translator.set_lang(_next_lang(translator.lang))
        _apply_lang()

    # ---------- 添加角色 ----------
    def _open_add_dialog():
        # 弹出「添加角色」窗口：键名 + 角色名 + 生日；保存后写回 data 并刷新界面
        dialog = tk.Toplevel(root)
        dialog.title(t("add_character"))
        dialog.configure(bg=theme.BG)
        dialog.transient(root)
        dialog.resizable(False, False)

        body = tk.Frame(dialog, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)

        def _field(label_text, hint_text=None):
            # 一个字段 = 标题 + 输入框（+ 灰色提示行）
            tk.Label(body, text=label_text, bg=theme.BG, fg=theme.SUBTEXT,
                     font=theme.FONT_SUB, anchor="w").pack(fill="x")
            entry = tk.Entry(body, font=theme.FONT_SUB, bg=theme.CARD_BG,
                             fg=theme.TEXT, relief="flat", width=28,
                             highlightthickness=1,
                             highlightbackground=theme.CARD_BORDER,
                             highlightcolor=theme.ACCENT,
                             insertbackground=theme.TEXT)
            entry.pack(fill="x", ipady=5, pady=(3, 0))
            if hint_text:
                tk.Label(body, text=hint_text, bg=theme.BG, fg=theme.SUBTEXT,
                         font=theme.FONT_META, anchor="w").pack(fill="x", pady=(2, 0))
            tk.Frame(body, bg=theme.BG, height=8).pack(fill="x")
            return entry

        key_entry = _field(t("field_key"))
        name_entry = _field(t("field_name"), t("hint_name_default"))
        birthday_entry = _field(t("field_birthday"), t("hint_birthday_format"))

        error_label = tk.Label(body, text="", bg=theme.BG, fg=theme.ERROR,
                               font=theme.FONT_META, anchor="w", justify="left",
                               wraplength=260)
        error_label.pack(fill="x")

        def _commit():
            # 校验 → 写盘 → 刷新主界面；任何一步失败都留在弹窗里提示
            key = key_entry.get().strip()
            name = name_entry.get().strip()
            birthday = _normalize_birthday(birthday_entry.get())

            if not key:
                error_label.config(text=t("err_key_required"))
                key_entry.focus_set()
                return
            if birthday is None:
                error_label.config(text=t("err_birthday_invalid"))
                birthday_entry.focus_set()
                return
            if fileOperations.character_exists(key):
                error_label.config(text=t("err_key_exists", key=key))
                key_entry.focus_set()
                return
            try:
                fileOperations.add_character(key, name, birthday)
            except (OSError, ValueError) as exc:
                error_label.config(text=t("err_save_failed", error=exc))
                return

            dialog.destroy()
            # 已落盘：重读数据、重建卡片与下拉框，并直接选中新角色
            _reload_characters(key)

        buttons = tk.Frame(body, bg=theme.BG)
        buttons.pack(fill="x", pady=(12, 0))

        save_button = tk.Button(buttons, text=t("btn_save"), command=_commit,
                                bg=theme.ACCENT, fg="white",
                                activebackground=theme.ACCENT, activeforeground="white",
                                relief="flat", bd=0, font=theme.FONT_SUB,
                                cursor="hand2", padx=16, pady=5)
        save_button.pack(side="right")

        cancel_button = tk.Button(buttons, text=t("btn_cancel"), command=dialog.destroy,
                                  bg=theme.CARD_BG, fg=theme.SUBTEXT,
                                  activebackground=theme.CARD_BORDER,
                                  activeforeground=theme.TEXT,
                                  relief="flat", bd=0, font=theme.FONT_SUB,
                                  cursor="hand2", padx=16, pady=5,
                                  highlightthickness=1,
                                  highlightbackground=theme.CARD_BORDER)
        cancel_button.pack(side="right", padx=(0, 8))

        # 回车保存、Esc 关闭
        dialog.bind("<Return>", lambda event: _commit())
        dialog.bind("<Escape>", lambda event: dialog.destroy())

        # 居中显示在主窗口上方，焦点落在第一个输入框
        dialog.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_reqwidth()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        dialog.grab_set()
        key_entry.focus_set()

    # ---------- 顶部标题栏 ----------
    header = tk.Frame(root, bg=theme.HEADER_BG)
    header.pack(fill="x")

    topbar = tk.Frame(header, bg=theme.HEADER_BG)
    topbar.pack(fill="x")
    lang_button = tk.Button(topbar, command=_toggle_lang,
                            bg=theme.HEADER_BG, fg=theme.HEADER_SUB,
                            activebackground=theme.HEADER_BG,
                            activeforeground=theme.HEADER_FG,
                            relief="flat", bd=0, font=theme.FONT_META,
                            cursor="hand2", padx=8, pady=2)
    lang_button.pack(side="right", padx=12, pady=(10, 0))

    add_button = tk.Button(topbar, command=_open_add_dialog,
                           bg=theme.HEADER_BG, fg=theme.HEADER_SUB,
                           activebackground=theme.HEADER_BG,
                           activeforeground=theme.HEADER_FG,
                           relief="flat", bd=0, font=theme.FONT_META,
                           cursor="hand2", padx=8, pady=2)
    add_button.pack(side="right", padx=(12, 0), pady=(10, 0))

    title = tk.Label(header, bg=theme.HEADER_BG, fg=theme.HEADER_FG,
                     font=theme.FONT_TITLE)
    title.pack(pady=(4, 2))

    subtitle = tk.Label(header, bg=theme.HEADER_BG, fg=theme.HEADER_SUB,
                        font=theme.FONT_SUB)
    subtitle.pack(pady=(0, 20))

    # ---------- 角色选择下拉框（可滚动） ----------
    select_row = tk.Frame(root, bg=theme.BG)
    select_row.pack(fill="x", padx=16, pady=(14, 0))

    select_label = tk.Label(select_row, bg=theme.BG, fg=theme.SUBTEXT,
                            font=theme.FONT_SUB)
    select_label.pack(side="left")

    char_labels = [f"{names.get(en, en)} · {en}" for en in all_characters]
    combobox = ttk.Combobox(select_row, values=char_labels, state="readonly",
                            font=theme.FONT_SUB)
    combobox.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _on_select_character(event):
        # 用户在下拉框中选择后，切换到对应角色
        index = combobox.current()
        if 0 <= index < len(all_characters):
            _select(all_characters[index])

    combobox.bind("<<ComboboxSelected>>", _on_select_character)

    # ---------- 选中角色详情（精确到秒的倒计时） ----------
    detail = tk.Frame(root, bg=theme.CARD_BG,
                      highlightbackground=theme.CARD_BORDER, highlightthickness=1)
    detail.pack(fill="x", padx=16, pady=(10, 0))

    top = tk.Frame(detail, bg=theme.CARD_BG)
    top.pack(fill="x", padx=14, pady=(12, 0))
    detail_name = tk.Label(top, bg=theme.CARD_BG, fg=theme.TEXT,
                           font=theme.FONT_NAME, anchor="w")
    detail_name.pack(side="left")
    detail_caption = tk.Label(top, bg=theme.CARD_BG, fg=theme.SUBTEXT,
                              font=theme.FONT_META, anchor="e")
    detail_caption.pack(side="right")

    detail_meta = tk.Label(detail, bg=theme.CARD_BG, fg=theme.SUBTEXT,
                           font=theme.FONT_META, anchor="w")
    detail_meta.pack(fill="x", padx=14)

    detail_countdown = tk.Label(detail, bg=theme.CARD_BG, fg=theme.ACCENT,
                                font=theme.FONT_COUNTDOWN, anchor="center")
    detail_countdown.pack(fill="x", padx=14, pady=(2, 12))

    # ---------- 预览区标题 ----------
    section = tk.Label(root, bg=theme.BG, fg=theme.SUBTEXT,
                       font=theme.FONT_META, anchor="w")
    section.pack(fill="x", padx=18, pady=(10, 0))

    # ---------- 可滚动的卡片区域 ----------
    scroll_frame = tk.Frame(root, bg=theme.BG)
    scroll_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(scroll_frame, bg=theme.BG, highlightthickness=0, bd=0)
    scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # 卡片容器放在画布内，锚定左上角
    card_container = tk.Frame(canvas, bg=theme.BG)
    canvas_window = canvas.create_window((0, 0), window=card_container, anchor="nw")

    # 内容尺寸变化时，更新画布的可滚动范围
    card_container.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    # 画布宽度变化时，让卡片容器同步撑满宽度
    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfigure(canvas_window, width=e.width),
    )

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-event.delta / 120), "units")

    def _bind_wheel(widget):
        """给滚动区域内的控件递归绑定滚轮事件。"""
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            _bind_wheel(child)

    canvas.bind("<MouseWheel>", _on_mousewheel)

    # ---------- 卡片 ----------
    def _build_cards():
        # 重建预览卡片：清空旧卡片，按最新剩余天数重新排序 Top5
        nonlocal characters, all_characters, top_count

        for child in card_container.winfo_children():
            child.destroy()
        card_refs.clear()
        card_badges.clear()

        characters = _top_characters(5)
        all_characters = _all_characters()
        top_count = len(characters)

        combobox.config(
            values=[f"{names.get(en, en)} · {en}" for en in all_characters],
        )

        for index, (en_name, days) in enumerate(characters, start=1):
            # 每张卡片一个 Frame，2 像素描边（选中时改为强调色）
            card = tk.Frame(card_container, bg=theme.CARD_BG,
                            highlightbackground=theme.CARD_BORDER, highlightthickness=2)
            card.pack(fill="x", padx=16, pady=6)

            # 左侧序号徽章
            rank = tk.Frame(card, bg=theme.RANK_BG, width=28, height=28)
            rank.pack_propagate(False)
            rank.pack(side="left", padx=(12, 10), pady=12)
            rank_label = tk.Label(rank, text=str(index), bg=theme.RANK_BG,
                                  fg=theme.RANK_FG, font=theme.FONT_RANK)
            rank_label.pack(expand=True)

            # 右侧剩余天数徽章（今天生日用暖色）
            days_text, is_today = _days_text(days)
            badge_bg = theme.ACCENT_TODAY if is_today else theme.ACCENT
            badge = tk.Label(card, text=days_text, bg=badge_bg, fg="white",
                             font=theme.FONT_DAYS, padx=12, pady=5)
            badge.pack(side="right", padx=(0, 12))
            card_badges.append((badge, en_name))

            # 中间名字与生日信息
            name_block = tk.Frame(card, bg=theme.CARD_BG)
            name_block.pack(side="left", fill="x", expand=True, pady=10)

            ja_name = names.get(en_name, en_name)
            tk.Label(name_block, text=ja_name, bg=theme.CARD_BG, fg=theme.TEXT,
                     font=theme.FONT_NAME, anchor="w").pack(anchor="w")

            birthday = fileOperations.read_selected_character_birthday(en_name)
            tk.Label(name_block, text=f"{birthday} · {en_name}", bg=theme.CARD_BG,
                     fg=theme.SUBTEXT, font=theme.FONT_META, anchor="w").pack(anchor="w")

            # 记录卡片与序号控件，便于切换选中时更新颜色；并绑定点击选中
            card_refs[en_name] = (card, rank, rank_label)
            _bind_click(card, lambda e, en=en_name: _select(en))

        # 卡片构建完成后，给整个卡片容器及其子控件绑定滚轮
        _bind_wheel(card_container)

    def _reload_characters(select_key=None):
        """重新从 data 读取角色数据并重建界面；新增角色后调用。"""
        nonlocal names
        names = fileOperations.read_all_characters_names()
        _build_cards()   # 内部会重算 characters / all_characters / top_count，并刷新下拉框
        _apply_lang()    # 刷新日期、统计与徽章文案
        if select_key is not None:
            _select(select_key)

    # 初次构建卡片
    _build_cards()

    # ---------- 底部说明 ----------
    footer = tk.Label(root, bg=theme.BG, fg=theme.SUBTEXT, font=theme.FONT_META)
    footer.pack(pady=(6, 14))

    """# ===== 以下为测试代码：每次点击模拟日期 +1 天，可整体删除 =====
    import datetime as _dt

    class _SimDate(_dt.date):
        offset = 0
        @classmethod
        def today(cls):
            return _dt.date.today() + _dt.timedelta(days=cls.offset)

    def _test_rollover():
        # 每点一次让模拟日期前进 1 天，重建卡片观察跨天重排效果
        _SimDate.offset += 1
        real_date = remainDays.date
        remainDays.date = _SimDate
        try:
            _build_cards()
        finally:
            remainDays.date = real_date
        if selected["en"] is not None:
            _select(selected["en"])
        test_button.config(text=f"测试：+{_SimDate.offset}天")

    test_button = tk.Button(
        root, text="测试：+0天", command=_test_rollover,
        bg=theme.CARD_BG, fg=theme.SUBTEXT,
        activebackground=theme.CARD_BG, activeforeground=theme.TEXT,
        relief="flat", bd=0, font=theme.FONT_META, cursor="hand2", padx=8, pady=2,
    )
    test_button.pack(pady=(0, 6))
    # ===== 测试代码结束 ====="""

    # 应用文案、初始选中最近生日的角色，并启动每秒刷新
    _apply_lang()
    if selected["en"] is not None:
        _select(selected["en"])
    _tick()

    return root


if __name__ == "__main__":
    build_window().mainloop()
