import json
import os
import tempfile

import paths


def _data_file(relative_path):
    """返回 data 目录下某个文件的绝对路径。"""
    return os.path.join(paths.data_dir(), relative_path)


#查询所有角色的生日
def read_all_characters_birthday():
    with open(_data_file("characters_birthday_data.json"), 'r', encoding='utf-8') as file:
        character_birthday_data = json.load(file)
    return character_birthday_data

#查询单个角色的生日
def read_selected_character_birthday(character_name):
    character_birthday_data_select = read_all_characters_birthday()
    return character_birthday_data_select.get(character_name, None)

#查询所有角色的日文名
def read_all_characters_names():
    with open(_data_file("characters_name.json"), 'r', encoding='utf-8') as file:
        character_names_data = json.load(file)
    return character_names_data

#查询单个角色的日文名
def read_selected_character_name(character_name):
    character_names_data_select = read_all_characters_names()
    return character_names_data_select.get(character_name, None)


#---------- 写入 ----------

def _newline_style(path):
    """沿用目标文件原有的换行风格（CRLF / LF），文件不存在时用当前系统默认。"""
    try:
        with open(path, "rb") as file:
            head = file.read(4096)
    except OSError:
        return os.linesep
    return "\r\n" if b"\r\n" in head else "\n"


def _write_json(relative_path, data):
    """把数据原子地写回 data 目录：先写临时文件再替换，避免写到一半损坏原文件。"""
    target = _data_file(relative_path)
    directory = os.path.dirname(target)
    fd, temp_path = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=_newline_style(target)) as file:
            # 与仓库现有文件保持一致：4 空格缩进、保留中文、末尾不额外加换行
            json.dump(data, file, ensure_ascii=False, indent=4)
        os.replace(temp_path, target)
    except BaseException:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def character_exists(character_name):
    """判断 data 中是否已有该键名。"""
    return character_name in read_all_characters_birthday()


def add_character(character_name, display_name, birthday):
    """新增一个角色，把生日与显示名分别写回 data 下的两个 JSON。

    参数:
        character_name: 键名（程序内唯一标识，不可与已有键重复）。
        display_name: 显示名；留空时直接使用键名。
        birthday: 生日，格式 "MM-DD"。

    返回:
        (键名, 显示名, 生日) 三元组，其中显示名已填充为最终值。

    异常:
        ValueError: 键名为空或已存在。
    """
    character_name = (character_name or "").strip()
    if not character_name:
        raise ValueError("character name is empty")
    # 没填角色名时，用键名占位
    display_name = (display_name or "").strip() or character_name
    birthday = (birthday or "").strip()

    birthdays = read_all_characters_birthday()
    if character_name in birthdays:
        raise ValueError(f"character already exists: {character_name}")
    names = read_all_characters_names()

    birthdays[character_name] = birthday
    names[character_name] = display_name
    # 两个文件依次原子替换；即便中途失败，读取端也能容忍缺项
    _write_json("characters_birthday_data.json", birthdays)
    _write_json("characters_name.json", names)
    return character_name, display_name, birthday

"""if __name__ == "__main__":
    character_birthday_data = read_all_characters_birthday()
    print(character_birthday_data)
    input_character_name = input("Enter the character's English name to get their birthday: ")
    birthday = read_selected_character_birthday(input_character_name)
    print(f"{input_character_name}'s birthday is: {birthday}")"""