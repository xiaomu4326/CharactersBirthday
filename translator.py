"""语言切换与文案翻译：从 data/lang 下的 JSON 文件读取键值文案。"""

import json
import os

import paths


class Translator:
    def __init__(self, lang="zh", base_dir=None):
        self._base_dir = base_dir or os.path.join(paths.data_dir(), "lang")
        self.set_lang(lang)

    def set_lang(self, lang):
        """切换语言，例如 "zh" 或 "en"。"""
        self.lang = lang
        path = f"{self._base_dir}/{lang}.json"
        with open(path, "r", encoding="utf-8") as file:
            self._text = json.load(file)

    def translate(self, key, **kwargs):
        """取 key 对应的文案，可用关键字参数填充占位符（如 {n}）。"""
        text = self._text.get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
