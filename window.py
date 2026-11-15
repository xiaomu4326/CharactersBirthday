import os
import re
import tkinter as tk
import tkinter.ttk as ttk
import webbrowser
from datetime import date
from tkinter import messagebox

import appInfo
import fileOperations
import paths
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


def _load_app_icon(size=96):
    """加载 data/icon.png 并缩放到大约 size 像素；文件缺失或格式不支持时返回 None。"""
    path = os.path.join(paths.data_dir(), "icon.png")
    try:
        image = tk.PhotoImage(file=path)
    except Exception:
        return None
    factor = max(1, round(image.width() / size))
    if factor > 1:
        image = image.subsample(factor, factor)
    return image


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
        settings_button.config(text=t("settings"))
        _refresh_badges()
        _refresh_detail()

    def _toggle_lang():
        # 点击语言按钮：切换到下一语言并刷新界面文案
        translator.set_lang(_next_lang(translator.lang))
        _apply_lang()

    # ---------- 设置：添加 / 删除角色 ----------
    def _open_settings():
        # 设置窗口：先选功能（添加 / 删除），选中后再进入各自的子页
        dialog = tk.Toplevel(root)
        dialog.title(t("settings"))
        dialog.configure(bg=theme.BG)
        dialog.transient(root)
        dialog.resizable(False, False)
        dialog.minsize(300, 0)   # 设置菜单里的按钮按文字宽度会很窄，这里兜住最小宽度

        body = tk.Frame(dialog, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        view = {"name": "menu"}

        # 固定在顶部的标题（「设置」/「设置 · 添加角色」…）；切换视图时只重建下面的内容区
        heading = tk.Label(body, text=t("settings"), bg=theme.BG, fg=theme.TEXT,
                           font=theme.FONT_TITLE, anchor="w")
        heading.pack(fill="x", pady=(0, 12))

        content = tk.Frame(body, bg=theme.BG)
        content.pack(fill="both", expand=True)

        def _clear():
            for child in content.winfo_children():
                child.destroy()

        def _center():
            dialog.update_idletasks()
            x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_reqwidth()) // 2
            y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_reqheight()) // 2
            dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        def _hint(text):
            tk.Label(content, text=text, bg=theme.BG, fg=theme.SUBTEXT,
                     font=theme.FONT_META, anchor="w").pack(fill="x", pady=(2, 0))

        def _field(label_text, hint_text=None):
            # 一个字段 = 标题 + 输入框（+ 灰色提示行）
            tk.Label(content, text=label_text, bg=theme.BG, fg=theme.SUBTEXT,
                     font=theme.FONT_SUB, anchor="w").pack(fill="x", pady=(10, 0))
            entry = tk.Entry(content, font=theme.FONT_SUB, bg=theme.CARD_BG,
                             fg=theme.TEXT, relief="flat", width=28,
                             highlightthickness=1,
                             highlightbackground=theme.CARD_BORDER,
                             highlightcolor=theme.ACCENT,
                             insertbackground=theme.TEXT)
            entry.pack(fill="x", ipady=5, pady=(3, 0))
            if hint_text:
                _hint(hint_text)
            return entry

        def _error_label():
            label = tk.Label(content, text="", bg=theme.BG, fg=theme.ERROR,
                             font=theme.FONT_META, anchor="w", justify="left",
                             wraplength=260)
            label.pack(fill="x", pady=(4, 0))
            return label

        def _button_row():
            row = tk.Frame(content, bg=theme.BG)
            row.pack(fill="x", pady=(14, 0))
            return row

        def _plain_button(parent, text, command):
            return tk.Button(parent, text=text, command=command,
                             bg=theme.CARD_BG, fg=theme.SUBTEXT,
                             activebackground=theme.CARD_BORDER,
                             activeforeground=theme.TEXT,
                             relief="flat", bd=0, font=theme.FONT_SUB,
                             cursor="hand2", padx=16, pady=5,
                             highlightthickness=1,
                             highlightbackground=theme.CARD_BORDER)

        def _primary_button(parent, text, command, danger=False):
            color = theme.ERROR if danger else theme.ACCENT
            return tk.Button(parent, text=text, command=command,
                             bg=color, fg="white",
                             activebackground=color, activeforeground="white",
                             relief="flat", bd=0, font=theme.FONT_SUB,
                             cursor="hand2", padx=16, pady=5)

        # ---------- 菜单：选择要做的事 ----------
        def _render_menu():
            view["name"] = "menu"
            _clear()
            dialog.title(t("settings"))
            heading.config(text=t("settings"))

            for text, command, danger in (
                (f"＋ {t('add_character')}", _render_add, False),
                (f"－ {t('delete_character')}", _render_delete, True),
                (t("about"), _render_about, False),
            ):
                tk.Button(content, text=text, command=command, anchor="w",
                          bg=theme.CARD_BG,
                          fg=(theme.ERROR if danger else theme.TEXT),
                          activebackground=theme.CARD_BORDER,
                          activeforeground=(theme.ERROR if danger else theme.TEXT),
                          relief="flat", bd=0, font=theme.FONT_SUB,
                          cursor="hand2", padx=14, pady=10,
                          highlightthickness=1,
                          highlightbackground=theme.CARD_BORDER).pack(
                              fill="x", pady=(0, 8))

            _plain_button(_button_row(), t("btn_close"), dialog.destroy).pack(side="right")
            _center()

        # ---------- 添加子页 ----------
        def _render_add():
            view["name"] = "add"
            _clear()
            dialog.title(f"{t('settings')} · {t('add_character')}")
            heading.config(text=f"{t('settings')} · {t('add_character')}")

            key_entry = _field(t("field_key"))
            name_entry = _field(t("field_name"), t("hint_name_default"))
            birthday_entry = _field(t("field_birthday"), t("hint_birthday_format"))
            add_error = _error_label()

            def _commit_add():
                # 校验 → 写盘 → 刷新主界面；成功后清空输入，留在本页继续添加
                key = key_entry.get().strip()
                name = name_entry.get().strip()
                birthday = _normalize_birthday(birthday_entry.get())

                if not key:
                    add_error.config(text=t("err_key_required"))
                    key_entry.focus_set()
                    return
                if birthday is None:
                    add_error.config(text=t("err_birthday_invalid"))
                    birthday_entry.focus_set()
                    return
                if fileOperations.character_exists(key):
                    add_error.config(text=t("err_key_exists", key=key))
                    key_entry.focus_set()
                    return
                try:
                    fileOperations.add_character(key, name, birthday)
                except (OSError, ValueError) as exc:
                    add_error.config(text=t("err_save_failed", error=exc))
                    return

                add_error.config(text="")
                for entry in (key_entry, name_entry, birthday_entry):
                    entry.delete(0, "end")
                _reload_characters(key)
                key_entry.focus_set()

            for entry in (key_entry, name_entry, birthday_entry):
                entry.bind("<Return>", lambda event: _commit_add())

            row = _button_row()
            _primary_button(row, t("btn_save"), _commit_add).pack(side="right")
            _plain_button(row, t("btn_back"), _render_menu).pack(side="right", padx=(0, 8))
            _center()
            key_entry.focus_set()

        # ---------- 删除子页 ----------
        def _render_delete():
            view["name"] = "delete"
            _clear()
            dialog.title(f"{t('settings')} · {t('delete_character')}")
            heading.config(text=f"{t('settings')} · {t('delete_character')}")

            _hint(t("delete_pick"))
            delete_combo = ttk.Combobox(content, state="readonly", font=theme.FONT_SUB)
            delete_combo.pack(fill="x", pady=(4, 0))
            delete_error = _error_label()

            def _refresh_picker(select_key=None):
                # 重建候选；角色被删除后调用
                values = [f"{names.get(en, en)} · {en}" for en in all_characters]
                delete_combo.config(values=values)
                if not values:
                    delete_combo.set("")
                    delete_error.config(text=t("no_characters"))
                    return
                if select_key is not None and select_key in all_characters:
                    delete_combo.current(all_characters.index(select_key))
                elif delete_combo.current() < 0:
                    delete_combo.current(0)
                delete_error.config(text="")

            def _commit_delete():
                index = delete_combo.current()
                if index < 0 or index >= len(all_characters):
                    delete_error.config(text=t("err_no_selection"))
                    return
                en = all_characters[index]
                if not messagebox.askyesno(t("delete_character"),
                                           t("delete_confirm", name=names.get(en, en)),
                                           parent=dialog):
                    return
                try:
                    removed = fileOperations.remove_character(en)
                except OSError as exc:
                    delete_error.config(text=t("err_delete_failed", error=exc))
                    return
                if not removed:
                    delete_error.config(text=t("err_no_selection"))
                    return
                delete_error.config(text="")
                _reload_characters()
                _refresh_picker()

            _refresh_picker(selected["en"])

            row = _button_row()
            _primary_button(row, t("btn_delete"), _commit_delete,
                            danger=True).pack(side="right")
            _plain_button(row, t("btn_back"), _render_menu).pack(side="right", padx=(0, 8))
            _center()

        # ---------- 关于子页 ----------
        def _render_about():
            view["name"] = "about"
            _clear()
            dialog.title(f"{t('settings')} · {t('about')}")
            heading.config(text=f"{t('settings')} · {t('about')}")

            icon = _load_app_icon(96)
            if icon is not None:
                dialog._icon_image = icon    # 保持引用，避免被垃圾回收后图标消失
                tk.Label(content, image=icon, bg=theme.BG, bd=0,
                         highlightthickness=0).pack(pady=(0, 10))

            tk.Label(content, text=t("about_intro"), bg=theme.BG, fg=theme.TEXT,
                     font=theme.FONT_SUB, anchor="w", justify="left",
                     wraplength=250).pack(fill="x")

            version_row = tk.Frame(content, bg=theme.BG)
            version_row.pack(fill="x", pady=(14, 0))
            tk.Label(version_row, text=t("version_label"), bg=theme.BG,
                     fg=theme.SUBTEXT, font=theme.FONT_META,
                     anchor="w").pack(side="left")
            tk.Label(version_row, text=appInfo.APP_VERSION, bg=theme.BG,
                     fg=theme.TEXT, font=theme.FONT_SUB,
                     anchor="w").pack(side="left", padx=(8, 0))

            license_row = tk.Frame(content, bg=theme.BG)
            license_row.pack(fill="x", pady=(6, 0))
            tk.Label(license_row, text=t("license_label"), bg=theme.BG,
                     fg=theme.SUBTEXT, font=theme.FONT_META,
                     anchor="w").pack(side="left")
            tk.Label(license_row, text=t("license_text"), bg=theme.BG,
                     fg=theme.TEXT, font=theme.FONT_META, anchor="w",
                     justify="left", wraplength=200).pack(side="left", padx=(8, 0))

            tk.Label(content, text=t("github_label"), bg=theme.BG, fg=theme.SUBTEXT,
                     font=theme.FONT_META, anchor="w").pack(fill="x", pady=(10, 0))
            link = tk.Label(content, text=appInfo.GITHUB_URL, bg=theme.BG,
                            fg=theme.ACCENT, font=theme.FONT_META, anchor="w",
                            justify="left", wraplength=250, cursor="hand2")
            link.pack(fill="x", pady=(2, 0))
            link.bind("<Button-1>", lambda event: webbrowser.open(appInfo.GITHUB_URL))

            row = _button_row()
            _plain_button(row, t("btn_back"), _render_menu).pack(side="right")
            _center()

        # Esc：子页里返回菜单，菜单里关闭窗口
        def _on_escape(event):
            if view["name"] == "menu":
                dialog.destroy()
            else:
                _render_menu()

        dialog.bind("<Escape>", _on_escape)
        _render_menu()
        dialog.grab_set()

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

    settings_button = tk.Button(topbar, command=_open_settings,
                                bg=theme.HEADER_BG, fg=theme.HEADER_SUB,
                                activebackground=theme.HEADER_BG,
                                activeforeground=theme.HEADER_FG,
                                relief="flat", bd=0, font=theme.FONT_META,
                                cursor="hand2", padx=8, pady=2)
    settings_button.pack(side="right", padx=(12, 0), pady=(10, 0))

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
        """重新从 data 读取角色数据并重建界面；新增/删除角色后调用。"""
        nonlocal names
        names = fileOperations.read_all_characters_names()
        _build_cards()   # 内部会重算 characters / all_characters / top_count，并刷新下拉框
        _apply_lang()    # 刷新日期、统计与徽章文案
        if select_key is not None and select_key in all_characters:
            _select(select_key)
            return
        # 选中的角色已不存在（刚被删除）：退回最近生日的角色；一个都不剩就清空
        fallback = characters[0][0] if characters else None
        if fallback is None:
            selected["en"] = None
            _refresh_detail()
        else:
            _select(fallback)

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
