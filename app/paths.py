"""定位程序根目录与数据目录，兼容源码运行与 PyInstaller 打包。"""

import os
import sys


def app_dir():
    """返回程序所在目录（data 目录与它同级）：
    - 打包后为 exe 所在目录；
    - 源码运行时为 app 包的上一级（项目根目录）。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    package_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(package_dir)


def data_dir():
    """返回 data 目录的绝对路径。"""
    return os.path.join(app_dir(), "data")
