import fileOperations
from datetime import date, datetime


def get_selected_characters_remaining_days(character_name):
    """根据角色英文名，计算距离其生日还有多少天。

    参数:
        character_name: 角色的英文名。

    返回:
        距离生日的剩余天数（整数）；若找不到该角色则返回 None。
    """
    # 从文件中读取该角色的生日（格式为 "MM-DD"）
    birthday = fileOperations.read_selected_character_birthday(character_name)
    # 找不到生日数据时返回 None
    if birthday is None:
        return None

    # 生日字符串格式为 "MM-DD"，拆成月份和日期
    month, day = map(int, birthday.split("-"))

    # 今天的日期
    today = date.today()

    # 计算今年生日所在的日期（2 月 29 日在非闰年时归到 2 月 28 日）
    birthday_this_year = _make_date(today.year, month, day)

    # 如果今年生日已过，则计算明年的生日
    if birthday_this_year < today:
        birthday_this_year = _make_date(today.year + 1, month, day)

    # 返回剩余天数
    return (birthday_this_year - today).days


def _make_date(year, month, day):
    """构造一个日期; 2 月 29 日遇到非闰年时，回退到 2 月 28 日。"""
    try:
        # 正常情况下直接构造日期对象
        return date(year, month, day)
    except ValueError:
        # 非法日期（例如非闰年的 2 月 29 日）时，回退到 2 月 28 日
        return date(year, 2, 28)

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

    month, day = map(int, birthday.split("-"))
    now = datetime.now()
    next_birthday = _make_datetime(now.year, month, day)
    # 今年的生日时刻已过，则取明年
    if next_birthday <= now:
        next_birthday = _make_datetime(now.year + 1, month, day)
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
    """构造当天 00:00:00 的 datetime; 2 月 29 日遇到非闰年时回退到 2 月 28 日。"""
    try:
        return datetime(year, month, day)
    except ValueError:
        return datetime(year, 2, 28)


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