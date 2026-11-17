from datetime import date, datetime

from . import fileOperations

# 每个月最多允许的"日期"（2 月留到 29 日，闰年由 _make_date 处理）
_MAX_DAY = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def _parse_birthday(birthday):
    """把 "MM-DD" 拆成 (月, 日)；格式不对时返回 None。

    只做格式拆分，不校验日期是否真实存在 —— 有些角色设定上的生日
    本身就不存在（例如《超かぐや姫！》的月見ヤチヨ是 8 月 32 日）。
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


def get_selected_characters_remaining_days(character_name):
    """根据角色英文名，计算距离其生日还有多少天。

    参数:
        character_name: 角色的英文名。

    返回:
        距离生日的剩余天数（整数）；若找不到该角色或日期无法解析则返回 None。
    """
    # 从文件中读取该角色的生日（格式为 "MM-DD"）
    birthday = fileOperations.read_selected_character_birthday(character_name)
    # 找不到生日数据时返回 None
    if birthday is None:
        return None

    # 生日字符串格式为 "MM-DD"，拆成月份和日期
    parsed = _parse_birthday(birthday)
    if parsed is None:
        return None
    month, day = parsed

    # 今天的日期
    today = date.today()

    # 设定上不存在的日期（8 月 32 日）：按"9 月 1 日 00:00"那一刻计算，
    # 但那一刻一到就翻到明年，所以永远到不了 0 天。
    if _is_virtual_date(month, day):
        target = _virtual_date(today.year, month)
        if target <= today:
            target = _virtual_date(today.year + 1, month)
        return (target - today).days

    # 计算今年生日所在的日期（2 月 29 日在非闰年时归到 2 月 28 日）
    birthday_this_year = _make_date(today.year, month, day)
    if birthday_this_year is None:
        return None

    # 如果今年生日已过，则计算明年的生日
    if birthday_this_year < today:
        birthday_this_year = _make_date(today.year + 1, month, day)
        if birthday_this_year is None:
            return None

    # 返回剩余天数
    return (birthday_this_year - today).days


def _make_date(year, month, day):
    """构造一个日期。

    - 2 月 29 日在平年回退到 2 月 28 日；
    - 其他不存在的日期（如 8 月 32 日这种设定日期）返回 None，交给上层按"无可计算日期"处理。
    """
    try:
        return date(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return date(year, 2, 28)
        return None

def get_selected_character_next_birthday(character_name):
    """返回角色下一次生日的时刻（当天 00:00:00 的 datetime）。

    参数:
        character_name: 角色的英文名。

    返回:
        下一次生日的 datetime；找不到角色则返回 None。
    """
    birthday = fileOperations.read_selected_character_birthday(character_name)
    if birthday is None:
        return None

    parsed = _parse_birthday(birthday)
    if parsed is None:
        return None
    month, day = parsed

    now = datetime.now()

    # 设定上不存在的日期：目标就是"下个月 1 日 00:00"，到点即翻到明年
    if _is_virtual_date(month, day):
        target = _virtual_moment(now.year, month)
        if target <= now:
            target = _virtual_moment(now.year + 1, month)
        return target

    next_birthday = _make_datetime(now.year, month, day)
    if next_birthday is None:
        return None
    # 今年的生日时刻已过，则取明年
    if next_birthday <= now:
        next_birthday = _make_datetime(now.year + 1, month, day)
        if next_birthday is None:
            return None
    return next_birthday


def get_selected_character_countdown(character_name):
    """计算距离角色下一次生日时刻的精确倒计时（精确到秒）。

    参数:
        character_name: 角色的英文名。

    返回:
        (days, hours, minutes, seconds) 元组；找不到角色则返回 None。
    """
    next_birthday = get_selected_character_next_birthday(character_name)
    if next_birthday is None:
        return None

    total_seconds = int((next_birthday - datetime.now()).total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, hours, minutes, seconds


def _make_datetime(year, month, day):
    """构造当天 00:00:00 的 datetime。

    - 2 月 29 日在平年回退到 2 月 28 日；
    - 其他不存在的日期返回 None。
    """
    try:
        return datetime(year, month, day)
    except ValueError:
        if month == 2 and day == 29:
            return datetime(year, 2, 28)
        return None


def get_all_characters_remaining_days():
    """计算所有角色距离生日的剩余天数。

    返回:
        字典，键为角色名，值为距离生日的剩余天数 (找不到生日的角色值为 None)。
    """
    # 读取全部角色的生日数据
    character_birthday_data = fileOperations.read_all_characters_birthday()
    remaining_days_dict = {}
    # 逐个角色计算剩余天数并存入字典
    for character_name, birthday in character_birthday_data.items():
        remaining_days = get_selected_characters_remaining_days(character_name)
        remaining_days_dict[character_name] = remaining_days
    return remaining_days_dict


"""if __name__ == "__main__":
    # 提示用户输入角色英文名，查询其生日剩余天数
    input_character_name = input("Enter the character's English name to get the remaining days until their birthday: ")
    selected_characters_remaining_days = get_selected_characters_remaining_days(input_character_name)
    if selected_characters_remaining_days is None:
        # 未找到该角色
        print(f"Character '{input_character_name}' not found.")
    else:
        # 打印该角色的生日剩余天数
        print(f"There are {selected_characters_remaining_days} days remaining until {input_character_name}'s birthday.")

    # 打印所有角色的生日剩余天数
    all_characters_remaining_days = get_all_characters_remaining_days()
    print(f"Remaining days until each character's birthday:\n{all_characters_remaining_days}")"""