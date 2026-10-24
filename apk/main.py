"""APK 版主入口：用 Flet 复刻 Windows/Tkinter 版的界面与交互。

说明：
- 本文件仅用于 `flet build apk` 打包，与仓库根目录的 Tkinter 版
  （main.py / window.py / theme.py 等）相互独立、互不影响。
- 数据内嵌在 data.py 中，内容与根目录 data/*.json 保持一致。
- 配色与字号沿用根目录 theme.py 的 Nord 柔和配色。
"""

import asyncio
from datetime import date, datetime

import flet as ft

# 系统通知（仅 Android 打包环境会安装该包；Windows 本地运行时退化为应用内 SnackBar）。
# flet-android-notifications 底层是 flutter_local_notifications。
try:
    from flet_android_notifications import FletAndroidNotifications as _BaseNotifications
except Exception:  # pragma: no cover - 包未安装（非打包环境）
    _BaseNotifications = None

if _BaseNotifications is not None and not getattr(_BaseNotifications, "_c", None):
    # 兼容 Flet 1.0.5：该包 0.12.0 未用 @control 声明 Dart 控件类型名，
    # 而 1.0.5 的控件在实例化时会校验 _c，缺失会抛 ValueError。这里补上。
    _BaseNotifications._c = "flet_android_notifications"

from data import BIRTHDAYS, NAMES, TRANSLATIONS

# ---------- 配色（与 theme.py 一致） ----------
BG = "#ECEFF4"           # 页面背景
HEADER_BG = "#2E3440"    # 顶部栏
HEADER_FG = "#ECEFF4"    # 顶部标题文字
HEADER_SUB = "#88C0D0"   # 顶部日期文字
CARD_BG = "#FFFFFF"      # 卡片背景
CARD_BORDER = "#E5E9F0"  # 卡片描边
TEXT = "#2E3440"         # 主要文字
SUBTEXT = "#7B8794"      # 次要文字
RANK_BG = "#88C0D0"      # 序号底色
RANK_FG = "#2E3440"      # 序号文字
ACCENT = "#5E81AC"       # 强调色 / 剩余天数徽章（常规）
ACCENT_TODAY = "#D08770"  # 剩余天数徽章（今天生日）

# ---------- 字号（与 theme.py 一致） ----------
FONT_TITLE = 16
FONT_SUB = 10
FONT_NAME = 13
FONT_META = 9
FONT_DAYS = 11
FONT_RANK = 12
FONT_COUNTDOWN = 18

LANG_ORDER = ["zh", "en", "ja"]
LANG_NAMES = {"zh": "中文", "en": "English", "ja": "日本語"}


def _next_lang(current):
    """返回切换顺序中的下一个语言代码。"""
    return LANG_ORDER[(LANG_ORDER.index(current) + 1) % len(LANG_ORDER)]


def _make_date(year, month, day):
    """构造日期；2 月 29 日遇到非闰年时回退到 2 月 28 日。"""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, 2, 28)


def _make_datetime(year, month, day):
    """构造当天 00:00:00 的 datetime；2 月 29 日非闰年时回退到 2 月 28 日。"""
    try:
        return datetime(year, month, day)
    except ValueError:
        return datetime(year, 2, 28)


def _remaining_days(name, today=None):
    """返回角色距离下次生日的剩余天数；找不到角色返回 None。"""
    birthday = BIRTHDAYS.get(name)
    if birthday is None:
        return None
    month, day = map(int, birthday.split("-"))
    today = today or date.today()
    bd = _make_date(today.year, month, day)
    if bd < today:
        bd = _make_date(today.year + 1, month, day)
    return (bd - today).days


def _next_birthday(name):
    """返回角色下一次生日的时刻（当天 00:00:00）。"""
    birthday = BIRTHDAYS.get(name)
    if birthday is None:
        return None
    month, day = map(int, birthday.split("-"))
    now = datetime.now()
    nxt = _make_datetime(now.year, month, day)
    if nxt <= now:
        nxt = _make_datetime(now.year + 1, month, day)
    return nxt


def _countdown(name):
    """返回 (days, hours, minutes, seconds) 精确倒计时；找不到返回 None。"""
    nxt = _next_birthday(name)
    if nxt is None:
        return None
    total = int((nxt - datetime.now()).total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return days, hours, minutes, seconds


def _all_characters():
    """返回全部角色英文名列表，按生日临近排序（缺失生日的排最后）。"""
    items = [(name, _remaining_days(name)) for name in BIRTHDAYS]
    items.sort(key=lambda item: (item[1] is None, item[1] if item[1] is not None else 0))
    return [name for name, _ in items]


def _top_characters(limit=5):
    """按生日剩余天数从近到远排序，返回前 limit 个 (英文名, 剩余天数)。"""
    items = [(name, days) for name, days in
             ((n, _remaining_days(n)) for n in BIRTHDAYS) if days is not None]
    items.sort(key=lambda item: item[1])
    return items[:limit]


def _border(width, color):
    """构造四边等宽描边（Flet 1.x 无 border.all 便捷方法）。"""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def main(page: ft.Page):
    # 可变状态：语言、当前选中角色、今天日期、全部角色列表、Top 数量等
    state = {
        "lang": "zh",
        "selected": None,
        "today": date.today(),
        "today_key": "",
        "all": [],
        "top": [],
        "top_count": 0,
        "notified_date": None,
    }
    state["today_key"] = f"{state['today'].month:02d}-{state['today'].day:02d}"

    # 系统通知服务（仅 Android 打包环境可用）；本地运行时为 None，退化为 SnackBar
    notifications = _BaseNotifications() if _BaseNotifications is not None else None

    card_refs = {}     # en -> (card, rank_box, rank_text)
    card_badges = []   # (badge_box, badge_text, en)

    def t(key, **kwargs):
        """取 key 对应的文案，可用关键字参数填充占位符（如 {n}）。"""
        text = TRANSLATIONS[state["lang"]].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def _days_text(days):
        """把剩余天数转成显示文案，并标记是否为今天生日。"""
        if days == 0:
            return t("today"), True
        if days == 1:
            return t("tomorrow"), False
        return f"{days} {t('days_unit')}", False

    # ---------- 控件（先创建，供回调与布局共同引用） ----------
    title_text = ft.Text("", size=FONT_TITLE, weight="bold", color=HEADER_FG,
                         text_align=ft.TextAlign.CENTER)
    subtitle_text = ft.Text("", size=FONT_SUB, color=HEADER_SUB,
                            text_align=ft.TextAlign.CENTER)

    lang_button = ft.TextButton(
        content=ft.Text(LANG_NAMES[state["lang"]], size=FONT_META, color=HEADER_SUB),
        on_click=lambda e: _toggle_lang(),
        style=ft.ButtonStyle(color=HEADER_SUB),
    )

    select_label = ft.Text("", size=FONT_SUB, color=SUBTEXT)
    dropdown = ft.Dropdown(
        options=[],
        on_select=lambda e: _select(e.control.value),
        text_size=FONT_SUB,
        fill_color=CARD_BG,
        border_color=CARD_BORDER,
        color=TEXT,
        expand=True,
    )

    detail_name = ft.Text("", size=FONT_NAME, weight="bold", color=TEXT)
    detail_caption = ft.Text("", size=FONT_META, color=SUBTEXT)
    detail_meta = ft.Text("", size=FONT_META, color=SUBTEXT)
    detail_countdown = ft.Text("--", size=FONT_COUNTDOWN, weight="bold",
                               color=ACCENT, text_align=ft.TextAlign.CENTER)

    section = ft.Text("", size=FONT_META, color=SUBTEXT)
    footer = ft.Text("", size=FONT_META, color=SUBTEXT,
                     text_align=ft.TextAlign.CENTER)

    cards_list = ft.ListView(controls=[], spacing=0, expand=True,
                             padding=ft.Padding(0, 4, 0, 4))

    # ---------- 交互逻辑 ----------
    def _refresh_detail():
        # 根据当前选中的角色刷新详情区的名字、生日和秒级倒计时
        en = state["selected"]
        if en is None:
            detail_name.value = t("no_data")
            detail_meta.value = ""
            detail_countdown.value = "--"
            detail_countdown.color = ACCENT
            return

        birthday = BIRTHDAYS.get(en)
        detail_name.value = NAMES.get(en, en)
        detail_meta.value = f"{t('birthday')} {birthday} · {en}"

        if birthday == state["today_key"]:
            detail_countdown.value = t("today")
            detail_countdown.color = ACCENT_TODAY
            return

        countdown = _countdown(en)
        if countdown is None:
            detail_countdown.value = "--"
            detail_countdown.color = ACCENT
            return
        days, hours, minutes, seconds = countdown
        detail_countdown.value = (
            f"{days}{t('days_unit')} {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        detail_countdown.color = ACCENT

    def _refresh_badges():
        # 重新计算各卡片徽章的剩余天数，刷新文案与“今天生日”配色
        for badge_box, badge_text, en in card_badges:
            days = _remaining_days(en)
            if days is None:
                continue
            days_text, is_today = _days_text(days)
            badge_text.value = days_text
            badge_box.bgcolor = ACCENT_TODAY if is_today else ACCENT

    def _select(en):
        # 切换选中角色：同步下拉框显示、高亮对应卡片，并刷新详情
        state["selected"] = en
        if en is not None:
            dropdown.value = en
        for key, (card, rank_box, rank_text) in card_refs.items():
            if key == en:
                card.border = _border(2, ACCENT)
                rank_box.bgcolor = ACCENT
                rank_text.color = "#FFFFFF"
            else:
                card.border = _border(2, CARD_BORDER)
                rank_box.bgcolor = RANK_BG
                rank_text.color = RANK_FG
        _refresh_detail()

    def _build_cards():
        # 重建预览卡片：清空旧卡片，按最新剩余天数重新排序 Top5
        state["all"] = _all_characters()
        state["top"] = _top_characters(5)
        state["top_count"] = len(state["top"])

        dropdown.options = [
            ft.dropdown.Option(key=en, text=f"{NAMES.get(en, en)} · {en}")
            for en in state["all"]
        ]

        card_refs.clear()
        card_badges.clear()
        cards_list.controls.clear()

        for index, (en, days) in enumerate(state["top"], start=1):
            days_text, is_today = _days_text(days)
            badge_bg = ACCENT_TODAY if is_today else ACCENT

            rank_text = ft.Text(str(index), size=FONT_RANK, weight="bold",
                                color=RANK_FG)
            rank_box = ft.Container(
                content=rank_text,
                bgcolor=RANK_BG,
                width=28, height=28,
                alignment=ft.Alignment.CENTER,
                border_radius=14,
            )

            name_block = ft.Column(
                [
                    ft.Text(NAMES.get(en, en), size=FONT_NAME, weight="bold",
                            color=TEXT),
                    ft.Text(f"{BIRTHDAYS.get(en, '')} · {en}", size=FONT_META,
                            color=SUBTEXT),
                ],
                spacing=2,
                expand=True,
            )

            badge_text = ft.Text(days_text, size=FONT_DAYS, weight="bold",
                                 color="#FFFFFF")
            badge_box = ft.Container(
                content=badge_text,
                bgcolor=badge_bg,
                border_radius=6,
                padding=ft.Padding(12, 5, 12, 5),
            )

            card = ft.Container(
                content=ft.Row(
                    [rank_box, name_block, badge_box],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=CARD_BG,
                border=_border(2, CARD_BORDER),
                border_radius=8,
                padding=ft.Padding(12, 12, 12, 12),
                margin=ft.Margin(16, 6, 16, 6),
                on_click=lambda e, en=en: _select(en),
            )

            card_refs[en] = (card, rank_box, rank_text)
            card_badges.append((badge_box, badge_text, en))
            cards_list.controls.append(card)

    def _apply_lang():
        # 按当前语言刷新所有静态文案与徽章
        page.title = t("app_title")
        title_text.value = t("app_title")
        subtitle_text.value = t(
            "date_format",
            year=state["today"].year,
            month=state["today"].month,
            day=state["today"].day,
        )
        select_label.value = t("select_character")
        detail_caption.value = t("until_next_birthday")
        section.value = t("preview_title", top=state["top_count"])
        footer.value = t("total_count", n=len(state["all"]), top=state["top_count"])
        lang_button.content.value = LANG_NAMES[state["lang"]]
        _refresh_badges()
        _refresh_detail()

    def _toggle_lang():
        # 点击语言按钮：切换到下一语言并刷新界面文案
        state["lang"] = _next_lang(state["lang"])
        _apply_lang()
        page.update()

    def _maybe_notify():
        # 当天有角色生日（剩余天数==0）时发一次通知；同一天只发一次
        now = date.today()
        key = now.isoformat()
        if state["notified_date"] == key:
            return
        names = [n for n in BIRTHDAYS if _remaining_days(n, today=now) == 0]
        if not names:
            return
        state["notified_date"] = key
        display = "、".join(NAMES.get(n, n) for n in names)

        if notifications is not None:
            # 系统级通知（出现在通知栏，退到后台也可见）
            page.run_task(_send_system_notification, display)
        else:
            # 无原生插件时退化为应用内弹条
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(t("birthday_notification", name=display),
                            size=FONT_SUB, color="#FFFFFF"),
                    bgcolor=ACCENT_TODAY,
                )
            )

    async def _send_system_notification(display):
        # 请求通知权限并发送系统通知；失败不影响主流程
        try:
            await notifications.request_permissions()
            await notifications.show_notification(
                notification_id=1,
                title=t("app_title"),
                body=t("birthday_notification", name=display),
            )
        except Exception:
            pass

    async def _tick():
        # 每秒刷新一次倒计时；跨天时重新排序卡片并刷新日期相关文案
        while True:
            _refresh_detail()
            new_today = date.today()
            if new_today != state["today"]:
                state["today"] = new_today
                state["today_key"] = (
                    f"{state['today'].month:02d}-{state['today'].day:02d}"
                )
                _build_cards()
                _apply_lang()
                if state["selected"] is not None:
                    _select(state["selected"])
                _maybe_notify()
            page.update()
            await asyncio.sleep(1)

    # ---------- 组装界面 ----------
    page.bgcolor = BG
    page.padding = 0

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row([lang_button], alignment=ft.MainAxisAlignment.END),
                title_text,
                subtitle_text,
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        bgcolor=HEADER_BG,
        padding=ft.Padding(0, 8, 0, 18),
    )

    select_row = ft.Container(
        content=ft.Row(
            [select_label, dropdown],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(16, 14, 16, 0),
    )

    detail = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [detail_name, detail_caption],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                detail_meta,
                detail_countdown,
            ],
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        bgcolor=CARD_BG,
        border=_border(1, CARD_BORDER),
        border_radius=8,
        padding=ft.Padding(14, 12, 14, 12),
        margin=ft.Margin(16, 10, 16, 0),
    )

    section_row = ft.Container(
        content=section,
        margin=ft.Margin(18, 10, 18, 0),
    )

    footer_row = ft.Container(
        content=footer,
        margin=ft.Margin(0, 6, 0, 14),
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                [header, select_row, detail, section_row, cards_list, footer_row],
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            ),
            expand=True,
        )
    )

    # 应用文案、初始选中最近生日的角色，并启动每秒刷新
    _build_cards()
    if state["top"]:
        state["selected"] = state["top"][0][0]
    _apply_lang()
    if state["selected"] is not None:
        _select(state["selected"])
    _maybe_notify()
    page.run_task(_tick)
    if notifications is not None:
        # 应用在前台时尽早请求通知权限（Android 13+ 运行时权限）
        page.run_task(notifications.request_permissions)


ft.run(main)
