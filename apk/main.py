"""APK 版主入口：用 Flet 复刻 Windows/Tkinter 版的界面与交互。

说明：
- 本文件仅用于 `flet build apk` 打包，与仓库根目录的 Tkinter 版
  （main.py / window.py / theme.py 等）相互独立、互不影响。
- 数据内嵌在 data.py 中，内容与根目录 data/*.json 保持一致。
- 配色与字号沿用根目录 theme.py 的 Nord 柔和配色。
"""

import asyncio
import json
import re
import zlib
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

from data import APP_VERSION, BIRTHDAYS, GITHUB_URL, NAMES, TRANSLATIONS

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
ERROR = "#BF616A"        # 表单错误提示文字

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

# 自定义角色（应用内添加）在客户端存储中的键名
CUSTOM_STORAGE_KEY = "custom_characters"
# 已删除的内置角色（墓碑）：内置数据随包分发不能改，只能记下"别显示它"
DELETED_STORAGE_KEY = "deleted_characters"

# ---------- 生日提醒（Android AlarmManager 定时通知） ----------
# 以前只在 App 运行（前台/后台）时才发通知，因为那是 Python 的每秒循环里判断的；
# 现在改用系统闹钟提前排好，到点由系统的 receiver 自己发通知，
# 与 App 是否在前台/后台/已被杀死无关。
NOTIFY_HOUR = 9           # 生日当天几点提醒（本机时区）
NOTIFY_MINUTE = 0
REMINDER_OCCURRENCES = 2  # 每个角色往后排几次生日（排得多，长期不打开 App 也还能响）
REMINDER_ID_BASE = 1000   # 定时通知 id 起点，避开即时通知用的 id=1
REMINDER_CHANNEL_ID = "birthday_reminders"


def _next_lang(current):
    """返回切换顺序中的下一个语言代码。"""
    return LANG_ORDER[(LANG_ORDER.index(current) + 1) % len(LANG_ORDER)]


def _normalize_birthday(text):
    """把生日文本规范成 "MM-DD"（允许 4-1、04/01 这类写法）；非法时返回 None。

    月份 1~12、日期 1~32：日期超过当月天数时按「设定日期」处理
    （例如 08-32 会按 9 月 1 日那一刻倒计时，且永远不会真正到达）。
    """
    match = re.fullmatch(r"\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*", text or "")
    if match is None:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 32):
        return None
    return f"{month:02d}-{day:02d}"


def _storage(page):
    """取客户端的键值存储：Flet 1.0 起 client_storage 更名为 shared_preferences。"""
    return getattr(page, "shared_preferences", None) or getattr(page, "client_storage", None)


# 每个月最多允许的"日期"（2 月留到 29 日，闰年由 _make_date 处理）
_MAX_DAY = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _parse_birthday(birthday):
    """把 "MM-DD" 拆成 (月, 日)；格式不对时返回 None。

    只拆格式、不校验日期真伪 —— 设定上的 8 月 32 日这种日期也要能存。
    """
    try:
        month, day = (int(part) for part in birthday.split("-"))
    except (AttributeError, ValueError):
        return None
    if not (1 <= month <= 12) or not (1 <= day <= 32):
        return None
    return month, day


def _is_virtual_date(month, day):
    """日期是否在现实中不存在（超过当月最大天数，如 8 月 32 日）。"""
    return day > _MAX_DAY[month]


def _virtual_date(year, month):
    """设定日期对应的时刻：下个月 1 日（8 月 32 日 → 9 月 1 日）。"""
    return date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)


def _virtual_moment(year, month):
    """同上，返回 datetime（当天 00:00:00）。"""
    return (datetime(year + 1, 1, 1) if month == 12
            else datetime(year, month + 1, 1))


def _make_date(year, month, day):
    """构造日期；2 月 29 日在平年回退到 2 月 28 日，其它不存在的日期返回 None。"""
    try:
        return date(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date(year, 2, 28)
        return None


def _make_datetime(year, month, day):
    """构造当天 00:00:00 的 datetime；规则同 _make_date。"""
    try:
        return datetime(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return datetime(year, 2, 28)
        return None


def _remaining_days(name, today=None):
    """返回角色距离下次生日的剩余天数；找不到角色或日期无法解析时返回 None。"""
    birthday = BIRTHDAYS.get(name)
    if birthday is None:
        return None
    parsed = _parse_birthday(birthday)
    if parsed is None:
        return None
    month, day = parsed
    today = today or date.today()

    # 设定上不存在的日期：按"下个月 1 日"计算，到点即翻到明年，永远到不了 0
    if _is_virtual_date(month, day):
        target = _virtual_date(today.year, month)
        if target <= today:
            target = _virtual_date(today.year + 1, month)
        return (target - today).days

    bd = _make_date(today.year, month, day)
    if bd is None:
        return None
    if bd < today:
        bd = _make_date(today.year + 1, month, day)
        if bd is None:
            return None
    return (bd - today).days


def _next_birthday(name):
    """返回角色下一次生日的时刻（当天 00:00:00）；日期无法解析时返回 None。"""
    birthday = BIRTHDAYS.get(name)
    if birthday is None:
        return None
    parsed = _parse_birthday(birthday)
    if parsed is None:
        return None
    month, day = parsed
    now = datetime.now()

    if _is_virtual_date(month, day):
        target = _virtual_moment(now.year, month)
        if target <= now:
            target = _virtual_moment(now.year + 1, month)
        return target

    nxt = _make_datetime(now.year, month, day)
    if nxt is None:
        return None
    if nxt <= now:
        nxt = _make_datetime(now.year + 1, month, day)
        if nxt is None:
            return None
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


def _reminder_datetime(name, occurrence=0, now=None):
    """该角色第 occurrence 次未来生日的提醒时刻（本机时区的 naive datetime）。

    设定上不存在的日期（如 8 月 32 日）永远等不到"当天"，与 _remaining_days
    的口径一致，直接不排提醒。日期无法解析时同样返回 None。
    """
    birthday = BIRTHDAYS.get(name)
    if birthday is None:
        return None
    parsed = _parse_birthday(birthday)
    if parsed is None:
        return None
    month, day = parsed
    if _is_virtual_date(month, day):
        return None

    now = now or datetime.now()
    upcoming = []
    for year in range(now.year, now.year + 4):
        moment = _make_datetime(year, month, day)
        if moment is None:
            continue
        remind = moment.replace(hour=NOTIFY_HOUR, minute=NOTIFY_MINUTE,
                                second=0, microsecond=0)
        if remind > now:            # 今天已过提醒时刻就顺延到明年
            upcoming.append(remind)
    if occurrence >= len(upcoming):
        return None
    return upcoming[occurrence]


def _reminder_id(name, occurrence=0):
    """定时通知的 id：按角色名取稳定哈希，重复排同一角色只会覆盖、不会堆叠。"""
    digest = zlib.crc32(name.encode("utf-8")) % 900000
    return REMINDER_ID_BASE + digest * REMINDER_OCCURRENCES + occurrence


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
        "custom": {},      # 应用内添加的角色：键名 -> {"name", "birthday"}
        "deleted": set(),  # 已删除的内置角色键名（重启后也不显示）
    }
    state["today_key"] = f"{state['today'].month:02d}-{state['today'].day:02d}"

    # 系统通知服务（仅 Android 打包环境可用）；本地运行时为 None，退化为 SnackBar
    notifications = _BaseNotifications() if _BaseNotifications is not None else None

    card_refs = {}     # en -> (card, rank_box, rank_text)
    card_badges = []   # (badge_box, badge_text, en)

    def t(text_key, **kwargs):
        """取 text_key 对应的文案，可用关键字参数填充占位符（如 {n}）。

        参数名不用 key，是为了让文案占位符可以直接叫 {key}。
        """
        text = TRANSLATIONS[state["lang"]].get(text_key, text_key)
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

    settings_button = ft.TextButton(
        content=ft.Text("", size=FONT_META, color=HEADER_SUB),
        on_click=lambda e: _open_settings(),
        style=ft.ButtonStyle(color=HEADER_SUB),
    )

    select_label = ft.Text("", size=FONT_SUB, color=SUBTEXT)

    def _dropdown_menu_height():
        # 菜单最多占屏幕高度的 40%（夹在 140~420 dp 之间）。
        # 不限制时，角色一多菜单会往下铺满并超出屏幕，最下面的条目既看不到也点不到；
        # 显式给高度后，菜单内部可滚动。
        screen_height = page.height or 800
        return max(140, min(int(screen_height * 0.4), 420))

    dropdown = ft.Dropdown(
        options=[],
        on_select=lambda e: _select(e.control.value),
        text_size=FONT_SUB,
        fill_color=CARD_BG,
        border_color=CARD_BORDER,
        color=TEXT,
        expand=True,
        menu_height=_dropdown_menu_height(),
        # 角色很多时可以直接输入名字筛选，不用在长列表里翻
        enable_filter=True,
    )

    def _sync_dropdown_menu_height():
        # 屏幕尺寸变化（首次布局完成 / 旋转 / 分屏）后重新计算菜单高度
        height = _dropdown_menu_height()
        if dropdown.menu_height != height:
            dropdown.menu_height = height
            page.update()

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
            # 生日写在那里、但现实中没有这一天（例如 8 月 32 日）：给个明确说法
            detail_countdown.value = t("no_such_date") if birthday else "--"
            detail_countdown.color = SUBTEXT if birthday else ACCENT
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
        # 切换选中角色：同步下拉框显示、高亮对应卡片，并刷新详情卡片
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
        settings_button.content.value = t("settings")
        _refresh_badges()
        _refresh_detail()

    def _toggle_lang():
        # 点击语言按钮：切换到下一语言并刷新界面文案
        state["lang"] = _next_lang(state["lang"])
        _apply_lang()
        page.update()
        # 文案变了，已排的闹钟正文也要跟着换成新语言
        page.run_task(_schedule_reminders, list(BIRTHDAYS))

    # ---------- 页面栈：设置与详情都是整页 ----------
    def _push_page(view):
        # 压入一层整页；安卓返回键会触发 page.on_view_pop
        page.views.append(view)
        page.update()

    def _pop_page(view=None):
        # 返回上一页：系统返回键会把被弹出的页传进来
        if len(page.views) <= 1:
            return
        if view is not None and view in page.views:
            page.views.remove(view)
        else:
            page.views.pop()
        page.update()

    page.on_view_pop = lambda e: _pop_page(getattr(e, "view", None))

    def _page_appbar(title):
        # 每个整页统一的顶栏：返回箭头 + 标题
        return ft.AppBar(
            title=title,
            bgcolor=HEADER_BG,
            color=HEADER_FG,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=HEADER_FG,
                tooltip=t("btn_back"),
                on_click=lambda e: _pop_page(),
            ),
        )

    def _page(title, controls, route, spacing=12):
        # 整页骨架：顶栏 + 可滚动内容
        return ft.View(
            route=route,
            appbar=_page_appbar(
                ft.Text(title, size=FONT_SUB, weight="bold", color=HEADER_FG)
            ),
            controls=[
                ft.SafeArea(
                    content=ft.Column(
                        controls,
                        spacing=spacing,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    expand=True,
                )
            ],
            bgcolor=BG,
            padding=ft.Padding(16, 12, 16, 16),
        )

    def _settings_entry(text, color, on_click):
        # 设置菜单里的一行
        return ft.Container(
            content=ft.Text(text, size=FONT_SUB, color=color),
            bgcolor=CARD_BG,
            border=_border(1, CARD_BORDER),
            border_radius=8,
            padding=ft.Padding(14, 12, 14, 12),
            on_click=on_click,
        )

    def _action_button(text, on_click, color=ACCENT):
        # 页面底部的主操作按钮
        return ft.TextButton(
            content=ft.Text(text, size=FONT_SUB, weight="bold", color=color),
            style=ft.ButtonStyle(
                bgcolor=CARD_BG,
                padding=ft.Padding(18, 12, 18, 12),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=on_click,
        )

    def _open_settings(view="menu"):
        # 设置：菜单 / 添加 / 删除 / 关于，各自压一层整页
        _push_page(_settings_view(view))

    def _settings_view(view):
        # 按名称构造设置页（每次打开重新构造，文案与候选都是最新的）
        if view == "menu":
            return _page(
                t("settings"),
                [
                    _settings_entry(
                        f"＋ {t('add_character')}", TEXT,
                        lambda e: _open_settings("add"),
                    ),
                    _settings_entry(
                        f"－ {t('delete_character')}", ERROR,
                        lambda e: _open_settings("delete"),
                    ),
                    _settings_entry(
                        t("about"), TEXT,
                        lambda e: _open_settings("about"),
                    ),
                ],
                "/settings",
            )

        if view == "add":
            key_field = ft.TextField(label=t("field_key"), text_size=FONT_SUB,
                                     color=TEXT, border_color=CARD_BORDER,
                                     filled=True, fill_color=CARD_BG,
                                     autofocus=True)
            name_field = ft.TextField(label=t("field_name"), text_size=FONT_SUB,
                                      color=TEXT, border_color=CARD_BORDER,
                                      filled=True, fill_color=CARD_BG,
                                      hint_text=t("hint_name_default"))
            birthday_field = ft.TextField(label=t("field_birthday"),
                                          text_size=FONT_SUB,
                                          color=TEXT, border_color=CARD_BORDER,
                                          filled=True, fill_color=CARD_BG,
                                          hint_text=t("hint_birthday_format"))
            error_text = ft.Text("", size=FONT_META, color=ERROR)

            return _page(
                f"{t('settings')} · {t('add_character')}",
                [
                    key_field,
                    name_field,
                    birthday_field,
                    error_text,
                    _action_button(
                        t("btn_save"),
                        lambda e: page.run_task(
                            _commit_add, key_field, name_field,
                            birthday_field, error_text, lambda: None,
                        ),
                    ),
                ],
                "/settings/add",
            )

        if view == "delete":
            delete_dropdown = ft.Dropdown(
                label=t("delete_pick"),
                options=[
                    ft.dropdown.Option(key=en, text=f"{NAMES.get(en, en)} · {en}")
                    for en in state["all"]
                ],
                value=state["selected"],
                text_size=FONT_SUB,
                fill_color=CARD_BG,
                border_color=CARD_BORDER,
                color=TEXT,
                menu_height=_dropdown_menu_height(),
                enable_filter=True,
            )
            delete_error = ft.Text("", size=FONT_META, color=ERROR)

            def _refresh_delete_options():
                # 删除成功后重建候选，停留在删除页
                current = delete_dropdown.value
                delete_dropdown.options = [
                    ft.dropdown.Option(key=en, text=f"{NAMES.get(en, en)} · {en}")
                    for en in state["all"]
                ]
                if current not in state["all"]:
                    delete_dropdown.value = state["all"][0] if state["all"] else None
                delete_error.value = "" if state["all"] else t("no_characters")

            def _delete(e):
                en = delete_dropdown.value
                if not en or en not in BIRTHDAYS:
                    delete_error.value = t("err_no_selection")
                    page.update()
                    return
                _confirm_delete(en, _refresh_delete_options)

            return _page(
                f"{t('settings')} · {t('delete_character')}",
                [
                    delete_dropdown,
                    delete_error,
                    _action_button(t("btn_delete"), _delete, ERROR),
                ],
                "/settings/delete",
            )

        # about
        return _page(
            f"{t('settings')} · {t('about')}",
            [
                ft.Row(
                    [ft.Image(src="icon.png", width=88, height=88)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(t("about_intro"), size=FONT_SUB, color=TEXT),
                ft.Row(
                    [
                        ft.Text(t("version_label"), size=FONT_META, color=SUBTEXT),
                        ft.Text(APP_VERSION, size=FONT_SUB, color=TEXT),
                    ],
                    spacing=8,
                ),
                ft.Text(f"{t('license_label')}  {t('license_text')}",
                        size=FONT_META, color=SUBTEXT),
                ft.Text(t("github_label"), size=FONT_META, color=SUBTEXT),
                ft.Container(
                    content=ft.Text(GITHUB_URL, size=FONT_META, color=ACCENT),
                    on_click=lambda e: page.run_task(_open_github),
                ),
            ],
            "/settings/about",
        )

    async def _open_github():
        # 打开仓库页面；没有可用浏览器时静默失败，不影响其他功能
        try:
            await ft.UrlLauncher().launch_url(GITHUB_URL)
        except Exception:
            pass

    async def _commit_add(key_field, name_field, birthday_field, error_text,
                          stay_open=None):
        # 校验 → 写本地存储 → 关闭弹窗并刷新界面；失败时留在弹窗内提示
        key = (key_field.value or "").strip()
        name = (name_field.value or "").strip()
        birthday = _normalize_birthday(birthday_field.value)

        if not key:
            error_text.value = t("err_key_required")
            page.update()
            return
        if birthday is None:
            error_text.value = t("err_birthday_invalid")
            page.update()
            return
        if key in BIRTHDAYS:
            error_text.value = t("err_key_exists", key=key)
            page.update()
            return

        display = name or key          # 没填角色名时用键名占位
        # 先在副本上算好，存储成功后再落到内存，避免写盘失败留下半条数据
        new_custom = dict(state["custom"])
        new_custom[key] = {"name": display, "birthday": birthday}
        new_deleted = set(state["deleted"]) - {key}   # 重新添加：顺手清掉墓碑
        storage = _storage(page)
        if storage is None:
            error_text.value = t("err_save_failed", error="storage unavailable")
            page.update()
            return
        try:
            await storage.set(
                CUSTOM_STORAGE_KEY,
                json.dumps(new_custom, ensure_ascii=False),
            )
            await storage.set(
                DELETED_STORAGE_KEY,
                json.dumps(sorted(new_deleted), ensure_ascii=False),
            )
        except Exception as exc:       # 存储失败则放弃，不留下半条数据
            error_text.value = t("err_save_failed", error=str(exc))
            page.update()
            return

        state["custom"] = new_custom
        state["deleted"] = new_deleted
        BIRTHDAYS[key] = birthday
        NAMES[key] = display
        _build_cards()
        _apply_lang()
        _select(key)
        if stay_open is None:
            _pop_page()            # 没有回调时，保存后直接退回上一页
        else:
            # 设置面板：清空输入、刷新删除候选，保持在面板内
            key_field.value = ""
            name_field.value = ""
            birthday_field.value = ""
            error_text.value = ""
            stay_open()
        page.update()
        # 新角色的生日也排进系统闹钟（保存后立刻生效，不必等下次启动）
        await _schedule_reminders([key])

    # ---------- 删除角色 ----------
    def _confirm_delete(en=None, after_success=None):
        # 删除指定角色（默认取当前选中的）：先弹确认框
        en = en if en is not None else state["selected"]
        if en is None or en not in BIRTHDAYS:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(t("err_no_selection"), size=FONT_SUB, color="#FFFFFF"),
                    bgcolor=ACCENT_TODAY,
                )
            )
            return
        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(t("delete_character"), size=FONT_NAME, weight="bold",
                          color=TEXT),
            content=ft.Text(t("delete_confirm", name=NAMES.get(en, en)),
                            size=FONT_SUB, color=TEXT),
            actions=[
                ft.TextButton(
                    content=ft.Text(t("btn_cancel"), size=FONT_SUB, color=SUBTEXT),
                    on_click=lambda e: page.pop_dialog(),
                ),
                ft.TextButton(
                    content=ft.Text(t("btn_delete"), size=FONT_SUB, color=ERROR),
                    on_click=lambda e: page.run_task(
                        _commit_delete, en, after_success),
                ),
            ],
        )
        page.show_dialog(dialog)

    async def _commit_delete(en, after_success=None):
        # 从内存和客户端存储里移除角色；内置数据在包内不可改，只能记"墓碑"
        if en not in BIRTHDAYS:
            page.pop_dialog()
            return

        new_custom = dict(state["custom"])
        new_deleted = set(state["deleted"])
        if en in new_custom:
            new_custom.pop(en)      # 应用内添加的角色：直接从自定义里去掉
        else:
            new_deleted.add(en)     # 内置角色：记墓碑，重启后不再显示

        storage = _storage(page)
        if storage is None:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(t("err_delete_failed", error="storage unavailable"),
                            size=FONT_SUB, color="#FFFFFF"),
                    bgcolor=ACCENT_TODAY,
                )
            )
            return
        try:
            await storage.set(
                CUSTOM_STORAGE_KEY,
                json.dumps(new_custom, ensure_ascii=False),
            )
            await storage.set(
                DELETED_STORAGE_KEY,
                json.dumps(sorted(new_deleted), ensure_ascii=False),
            )
        except Exception as exc:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(t("err_delete_failed", error=str(exc)),
                            size=FONT_SUB, color="#FFFFFF"),
                    bgcolor=ACCENT_TODAY,
                )
            )
            return

        state["custom"] = new_custom
        state["deleted"] = new_deleted
        BIRTHDAYS.pop(en, None)
        NAMES.pop(en, None)
        page.pop_dialog()
        # 撤掉这个角色已经排好的闹钟，删了就不该再提醒
        await _cancel_reminders(en)
        _build_cards()
        _apply_lang()
        # 删掉的正好是当前选中项：回退到最近生日的角色，一个不剩就清空
        fallback = state["top"][0][0] if state["top"] else (
            state["all"][0] if state["all"] else None
        )
        if fallback is not None:
            _select(fallback)
        else:
            state["selected"] = None
            _refresh_detail()
        if after_success is not None:
            after_success()          # 设置面板：刷新删除候选并保持打开
        page.update()

    async def _load_custom_characters():
        # 启动时读回：应用内添加的角色 + 已删除的内置角色（墓碑），并入内存后刷新界面
        changed = False
        storage = _storage(page)
        raw = None
        raw_deleted = None
        if storage is not None:
            try:
                raw = await storage.get(CUSTOM_STORAGE_KEY)
            except Exception:
                raw = None
            try:
                raw_deleted = await storage.get(DELETED_STORAGE_KEY)
            except Exception:
                raw_deleted = None
        if raw:
            try:
                stored = json.loads(raw)
            except (TypeError, ValueError):
                stored = {}
            if isinstance(stored, dict):
                for key, item in stored.items():
                    if not isinstance(item, dict):
                        continue
                    birthday = _normalize_birthday(item.get("birthday", ""))
                    if birthday is None or key in BIRTHDAYS:
                        continue
                    display = (item.get("name") or key).strip() or key
                    state["custom"][key] = {"name": display, "birthday": birthday}
                    BIRTHDAYS[key] = birthday
                    NAMES[key] = display
                    changed = True
        if raw_deleted:
            try:
                deleted = json.loads(raw_deleted)
            except (TypeError, ValueError):
                deleted = []
            if isinstance(deleted, list):
                for name in deleted:
                    if not isinstance(name, str) or name in state["deleted"]:
                        continue
                    state["deleted"].add(name)
                    if BIRTHDAYS.pop(name, None) is not None:
                        NAMES.pop(name, None)
                        changed = True
        if changed:
            _build_cards()
            _apply_lang()
            if state["selected"] is not None:
                _select(state["selected"])
            page.update()
        _maybe_notify()
        # 读回数据后再排一遍定时通知：新加/删除的角色都要跟着更新
        await _schedule_reminders(list(BIRTHDAYS))

    def _maybe_notify():
        # 当天有角色生日时在应用内弹一次提示（同一天只弹一次）。
        # 通知栏那条由系统闹钟负责（见 _schedule_reminders），这里不再重复发系统通知，
        # 否则"闹钟已经响过 + 打开 App 又响一次"会变成两条。
        now = date.today()
        key = now.isoformat()
        if state["notified_date"] == key:
            return
        names = [n for n in BIRTHDAYS if _remaining_days(n, today=now) == 0]
        if not names:
            return
        state["notified_date"] = key
        display = "、".join(NAMES.get(n, n) for n in names)
        page.show_dialog(
            ft.SnackBar(
                ft.Text(t("birthday_notification", name=display),
                        size=FONT_SUB, color="#FFFFFF"),
                bgcolor=ACCENT_TODAY,
            )
        )

    # ---------- 定时通知：交给系统闹钟，App 不在也能响 ----------
    async def _schedule_reminders(names):
        # 给这些角色的未来生日排 AlarmManager 闹钟。系统到点会自己拉起
        # ScheduledNotificationReceiver 发通知，与 App 进程是否存活无关。
        if notifications is None:
            return
        mode = "inexact_allow_while_idle"
        try:
            if await notifications.can_schedule_exact_notifications():
                mode = "exact_allow_while_idle"
        except Exception:
            pass
        for name in names:
            for occurrence in range(REMINDER_OCCURRENCES):
                when = _reminder_datetime(name, occurrence)
                if when is None:
                    continue
                if not await _schedule_one(name, occurrence, when, mode):
                    # 精确闹钟被系统拒（未授权/厂商限制）时退回不精确模式，
                    # 时间点会有几分钟到一小时的浮动，但照样能响。
                    if mode == "exact_allow_while_idle":
                        await _schedule_one(name, occurrence, when,
                                            "inexact_allow_while_idle")

    async def _schedule_one(name, occurrence, when, mode):
        try:
            await notifications.schedule_notification(
                notification_id=_reminder_id(name, occurrence),
                title=t("app_title"),
                body=t("birthday_notification", name=NAMES.get(name, name)),
                scheduled_time=when,
                channel_id=REMINDER_CHANNEL_ID,
                channel_name=t("app_title"),
                channel_description=t("app_title"),
                importance="high",
                schedule_mode=mode,
                payload=f"birthday:{name}",
                category="reminder",
            )
            return True
        except Exception:
            return False

    async def _cancel_reminders(name):
        # 角色被删掉后，把它已经排上的闹钟撤掉，免得删了还响
        if notifications is None:
            return
        for occurrence in range(REMINDER_OCCURRENCES):
            try:
                await notifications.cancel(
                    notification_id=_reminder_id(name, occurrence))
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
            # 页面高度可能要等首帧之后才拿得到，这里兜底同步一次菜单高度（无变化时不会触发更新）
            height = _dropdown_menu_height()
            if dropdown.menu_height != height:
                dropdown.menu_height = height
            page.update()
            await asyncio.sleep(1)

    # ---------- 组装界面 ----------
    page.bgcolor = BG
    page.padding = 0

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row([settings_button, lang_button],
                       alignment=ft.MainAxisAlignment.END),
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
    # 首帧渲染后才知道真实窗口高度：立即算一次，之后旋转/分屏再跟着更新
    page.on_resize = lambda e: _sync_dropdown_menu_height()
    page.update()
    _sync_dropdown_menu_height()
    page.run_task(_tick)
    # 读回应用内添加过的角色（读完会刷新界面，并顺带做当天的生日通知）
    page.run_task(_load_custom_characters)
    if notifications is not None:
        # 应用在前台时尽早请求通知权限（Android 13+ 运行时权限）
        page.run_task(notifications.request_permissions)


ft.run(main)
