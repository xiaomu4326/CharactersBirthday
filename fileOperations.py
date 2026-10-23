import json
import os

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

"""if __name__ == "__main__":
    character_birthday_data = read_all_characters_birthday()
    print(character_birthday_data)
    input_character_name = input("Enter the character's English name to get their birthday: ")
    birthday = read_selected_character_birthday(input_character_name)
    print(f"{input_character_name}'s birthday is: {birthday}")"""