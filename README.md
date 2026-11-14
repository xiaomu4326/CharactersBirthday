<div align="center">

<img src="apk/assets/icon.png" width="170" alt="角色生日倒计时">

# 角色生日倒计时

**Character Birthday Countdown**

把喜欢的角色生日收进一个小窗口 —— 按生日临近排序，倒计时精确到秒，中 / 英 / 日三语切换。

**中文** · [English](README.en.md)

**Windows 桌面版（Tkinter，零第三方依赖）** · **Android 版（Flet）**

</div>

---

## 功能

| 功能 | 说明 |
| --- | --- |
| 秒级倒计时 | 详情卡每秒刷新 `N天 HH:MM:SS` 直到下一次生日，无需手动刷新 |
| 最近生日 Top 5 | 卡片按剩余天数从近到远排序，支持鼠标滚轮滚动 |
| 全量选择 | 只读下拉框列出全部角色，顺序同样按生日临近排列 |
| 今天生日高亮 | 剩余 0 天时徽章转为暖色 `#D08770`，文案显示「今天」；1 天显示「明天」 |
| 跨天自动重排 | 零点过后自动重建卡片、更新日期与语言文案，不用重启程序 |
| 三语切换 | 右上角按钮在 中文 → English → 日本語 之间循环 |
| 闰日兜底 | 2 月 29 日遇到平年自动回退到 2 月 28 日 |
| 高分屏适配 | Windows 下调用 `SetProcessDpiAwareness(1)`，避免界面发虚 |
| 生日提醒（仅 APK） | 生日当天推送一条系统通知，同一天只发一次 |
| 应用内添加角色 | 右上角「＋ 添加角色」填键名 / 角色名 / 生日；桌面版写回 `data/`，APK 存入设备本地存储，保存后界面立即刷新 |

界面配色统一使用 Nord 风格柔和色板（定义在 [theme.py](theme.py)），深浅分明且不刺眼：

| 用途 | 色值 |
| --- | --- |
| 窗口背景 | `#ECEFF4` |
| 顶部栏 | `#2E3440` |
| 卡片 / 描边 | `#FFFFFF` / `#E5E9F0` |
| 强调色（常规徽章） | `#5E81AC` |
| 强调色（今天生日） | `#D08770` |

## 界面

窗口默认 `380 × 640`（最小 `340 × 520`），启动时在屏幕居中，自上而下分为五块：

1. **顶部深色栏** —— 应用标题、当天日期、右上角「添加角色」与语言切换按钮
2. **角色选择** —— 标签 + 只读下拉框（`中文名 · EnglishName`）
3. **详情卡** —— 选中角色的名字、`生日 MM-DD · 英文名`、距下次生日的秒级倒计时
4. **预览区** —— 「最近生日 Top 5」，每张卡片含序号徽章、名字与生日、剩余天数徽章；点击卡片即选中并同步下拉框
5. **底部统计** —— 例如「共 28 位角色 · 按生日临近排序显示前 5 位」

## 快速开始

### 源码运行（Windows 桌面版）

需要 **Python 3.8+**（开发与打包使用 3.12 / 3.14 验证）。`tkinter` 随官方安装包自带，**没有任何第三方依赖**。

```bat
python main.py
```

> 字体写死为 `Microsoft YaHei UI`、DPI 适配走 `ctypes`，因此桌面版面向 Windows。

### 打包成免安装 exe

双击 [build.bat](build.bat)，或手动执行：

```bat
python -m PyInstaller --noconfirm --clean --onedir --windowed --name CharactersBirthday main.py
xcopy /E /I /Y data "dist\CharactersBirthday\data"
```

产物位于 `dist\CharactersBirthday\`，整个文件夹可复制到任意位置运行。

**关键点**：`data\` 必须与 exe 同级。打包后 [paths.py](paths.py) 通过 `sys.frozen` 判断运行方式 —— 冻结状态下取 `sys.executable` 所在目录，源码运行时取 `paths.py` 所在目录，两种方式共用同一套相对路径逻辑，所以 exe 目录里务必带上 `data`。

### 打包 Android APK

```bash
flet build apk ./apk --arch arm64-v8a --yes --skip-flutter-doctor
```

必须在**仓库根目录**执行（`apk/pyproject.toml` 里的 `tool.flet.template.url` 是相对当前工作目录的路径）。产物在 `apk/build/apk/`。首次构建会下载 Flutter SDK、Android SDK 与通知插件依赖，耗时较长。

详见 [apk/README.md](apk/README.md)。

## 项目结构

```
CharactersBirthday/
├── main.py                     # 桌面版入口
├── window.py                   # 界面组装：标题栏 / 下拉框 / 详情倒计时 / Top5 卡片 / 滚动区
├── theme.py                    # 配色与字号常量
├── remainDays.py               # 剩余天数、下次生日时刻、秒级倒计时
├── fileOperations.py           # 读取 data/ 下的 JSON
├── paths.py                    # 定位程序目录，兼容源码运行与 PyInstaller
├── translator.py               # 读取 data/lang/*.json 并填充占位符
├── data/                       # 角色生日、角色名、三语文案
├── build.bat                   # PyInstaller 一键打包
├── CharactersBirthday.spec     # PyInstaller 配置（onedir + windowed）
├── LICENSE                     # MIT 许可证
└── apk/                        # Android 版（Flet 独立工程）
    ├── main.py                 # Flet 主入口，复刻桌面版界面与交互
    ├── data.py                 # 内嵌数据（规避 Android 资源目录解析问题）
    ├── pyproject.toml          # 应用名、包名、通知依赖与权限
    ├── assets/icon.png         # 应用图标
    └── flet-template/          # 自定义 Android 构建模板（见下文）
```

两个版本**完全独立**：桌面版不引用 `apk/`，APK 版也不引用根目录的 Python 模块，唯一需要保持一致的是界面配色、字号与数据内容。

## 数据格式

### 角色生日

[data/characters_birthday_data.json](data/characters_birthday_data.json) —— 键是角色的**英文名**（程序内唯一标识），值是 `MM-DD`：

```json
{
    "OumiShiori": "04-01",
    "NanamiTōko": "02-19"
}
```

缺少某个角色的生日时，该角色仍会出现在下拉框里并被排到最后，剩余天数显示为空。

### 角色显示名

[data/characters_name.json](data/characters_name.json) —— 与上面**键完全对应**：

```json
{
    "OumiShiori": "近江汐莉"
}
```

界面上展示「显示名 · 英文名」，英文名同时作为下拉框与卡片选中的内部 key。

### 添加一个新角色

**方式一：在程序里添加。** 点击右上角「＋ 添加角色」，填写键名、角色名与生日后保存。桌面版会立即把两个 JSON 写回 `data/`；APK 版则把自定义角色保存在设备本地存储里（不写内嵌的 `data.py`，卸载应用后随之清除）。两者保存后都会立刻刷新界面并选中新角色。

- 键名必填且不能与已有键重复；角色名可以留空，此时显示名直接用键名。
- 生日支持 `MM-DD`、`M-D`、`MM/DD`、`MM.DD` 等写法，保存时统一规范为 `MM-DD`；`02-29` 合法。

**方式二：手动改 JSON。** 在 `characters_birthday_data.json` 和 `characters_name.json` 中**同时**加入同名键；若同时维护 APK 版，还需要同步 [apk/data.py](apk/data.py) 里的 `BIRTHDAYS` 与 `NAMES`。

JSON 的书写顺序无关紧要 —— 程序启动时会按剩余天数重新排序。

### 文案与多语言

[data/lang/](data/lang) 下是 `zh.json` / `en.json` / `ja.json`，键集合必须完全一致，值支持 `str.format` 占位符：

| 占位符 | 使用位置 |
| --- | --- |
| `{top}` | `preview_title`、`total_count`（Top N 的数量） |
| `{n}` | `total_count`（角色总数） |
| `{year}` `{month}` `{day}` | `date_format`（顶部日期） |

**新增一门语言**需要改三处：

1. 新建 `data/lang/xx.json`（键与 `zh.json` 保持一致）
2. [window.py](window.py) 顶部的 `LANG_ORDER` 与 `LANG_NAMES`
3. APK 版：[apk/main.py](apk/main.py) 的 `LANG_ORDER` / `LANG_NAMES`，以及 [apk/data.py](apk/data.py) 的 `TRANSLATIONS`

> `birthday_notification`（生日通知文案）是 APK 版独有的键，只存在于 `apk/data.py`，不在 `data/lang/*.json` 中。

## 关于构建产物与版本管理

仓库**只提交源码**，构建产物全部由 [.gitignore](.gitignore) 排除：

| 被忽略 | 原因 |
| --- | --- |
| `/build/` | PyInstaller 中间产物（`.toc`、`PYZ`、中间 exe 等） |
| `/dist/` | 打包好的 exe 目录与发布 zip |
| `/apk/build/` | `flet build` 生成的 Android 工程，体积可达 1 GB 以上 |
| `__pycache__/`、`*.py[cod]` | Python 字节码缓存 |
| `.idea/`、`.venv/` | IDE 配置与虚拟环境 |
| `*.log`、`*.zip` | 构建日志与发布包 |
| `.gradle/`、`.dart_tool/`、`/apk/.flet/` | Gradle / Flutter 缓存 |

**例外**：`apk/flet-template/` 必须提交 —— 它是**手改过的**官方模板副本，不是自动生成物，改动包括：

- `isCoreLibraryDesugaringEnabled = true` + `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")` —— `flutter_local_notifications` 用到 `java.time` 等 API，`minSdk < 26` 必须开启
- `multiDexEnabled = true` —— `serious_python` 加通知插件后方法数超过 64K
- `jniLibs` 的 `pickFirsts` / `excludes` —— 规避 AGP 处理多来源 `.so` 的冲突

`flet build` 本身没有构建前钩子，无法在生成工程后再改 Gradle 配置，所以只能通过 `tool.flet.template.url` 指向这份自定义模板。


## 开发提示

- 想验证跨天重排效果：`window.py` 末尾有一段被注释掉的「模拟日期 +1 天」测试代码（含一个测试按钮），临时取消注释即可，验证完记得删掉。
- 修改配色或字号只需改 [theme.py](theme.py)（桌面版）与 [apk/main.py](apk/main.py) 顶部的同名常量（APK 版）。
- `remainDays.py` 与 `apk/main.py` 里的 `_make_date` / `_make_datetime` 都做了闰日回退，改动时请一并同步。

## 数据说明

角色生日资料整理自公开资料，仅供个人使用与参考，如与官方设定有出入以官方为准。角色名称及相关作品版权归原作者与版权方所有。

数据本身以 CC0 1.0 释出并进入公有领域，可以自由取用 —— 详见 [data/LICENSE](data/LICENSE)。

<details>
<summary><b>内置角色（28 位 · 按原作分组）</b></summary>

| 英文名（JSON 键） | 显示名 | 生日 | 原作（官网） |
| --- | --- | --- | --- |
| `OumiShiori` | 近江汐莉 | 04-01 | [私を喰べたい、ひとでなし](https://wata-tabe.com/) |
| `YashiroMiko` | 社美胡 | 10-22 | [私を喰べたい、ひとでなし](https://wata-tabe.com/) |
| `YaotoseHinako` | 八百歳比名子 | 07-02 | [私を喰べたい、ひとでなし](https://wata-tabe.com/) |
| `MiyagiShiori` | 宮城志緒里 | 09-25 | [週に一度クラスメイトを買う話](https://promo.kadokawa.co.jp/fantasiabunko/special/202302shuichi/) |
| `SendaiHatsuki` | 仙台葉月 | 08-23 | [週に一度クラスメイトを買う話](https://promo.kadokawa.co.jp/fantasiabunko/special/202302shuichi/) |
| `AdachiSakura` | 安達桜 | 10-19 | [安達としまむら](https://www.tbs.co.jp/anime/adashima/) |
| `ShimamuraHōgetsu` | 島村抱月 | 04-10 | [安達としまむら](https://www.tbs.co.jp/anime/adashima/) |
| `KinoHimari` | 木野ひまり | 07-18 | [ささやくように恋を唄う](https://sasakoi-anime.com/) |
| `AsanaGiyori` | 朝凪依 | 11-26 | [ささやくように恋を唄う](https://sasakoi-anime.com/) |
| `MizukguchiAki` | 水口亜季 | 04-12 | [ささやくように恋を唄う](https://sasakoi-anime.com/) |
| `IzumiShiho` | 泉志帆 | 10-16 | [ささやくように恋を唄う](https://sasakoi-anime.com/) |
| `KamiinaBotan` | 上伊那ぼたん | 04-07 | [上伊那ぼたん、酔へる姿は百合の花](https://kamiina-botan.com/) |
| `TonamiIbuki` | 砺波いぶき | 08-08 | [上伊那ぼたん、酔へる姿は百合の花](https://kamiina-botan.com/) |
| `NanamiTōko` | 七海燈子 | 02-19 | [やがて君になる](https://yagakimi.com/) |
| `KoitoYū` | 小糸侑 | 04-05 | [やがて君になる](https://yagakimi.com/) |
| `AmaoriRenako` | 甘織れな子 | 03-03 | [わたなれ](https://www.watanare-anime.com/) |
| `KoyanagiKaho` | 小柳香穂 | 04-10 | [わたなれ](https://www.watanare-anime.com/) |
| `AmaoriHaruna` | 甘織遥奈 | 05-28 | [わたなれ](https://www.watanare-anime.com/) |
| `KotoSatsuki` | 琴紗月 | 07-26 | [わたなれ](https://www.watanare-anime.com/) |
| `ŌdzukaMai` | 王塚真唯 | 08-31 | [わたなれ](https://www.watanare-anime.com/) |
| `SenaAjisai` | 瀬名紫陽花 | 12-12 | [わたなれ](https://www.watanare-anime.com/) |
| `Anisufia` | アニスフィア | 04-16 | [転生王女と天才令嬢の魔法革命](https://tenten-kakumei.com/) |
| `Yufiria` | ユフィリア | 11-10 | [転生王女と天才令嬢の魔法革命](https://tenten-kakumei.com/) |
| `TotsukiShīna` | トツキ・シーナ | 11-14 | [きみが死ぬまで恋をしたい](https://kimishinu-anime.com/) |
| `KagariMimi` | カガリ・ミミ | 12-03 | [きみが死ぬまで恋をしたい](https://kimishinu-anime.com/) |
| `SakayoriIroha` | 酒寄彩葉 | 05-11 | [超かぐや姫！](https://www.cho-kaguyahime.com/) |
| `Kaguya` | かぐや | 07-12 | [超かぐや姫！](https://www.cho-kaguyahime.com/) |
| `Tohru` | トール | 06-30 | [小林さんちのメイドラゴン](https://maidragon.jp/) |

> 作品名为原作的日文标题，链接指向**官方站点**（TV 动画官网或出版方特设页）。「わたなれ」是『わたしが恋人になれるわけないじゃん、ムリムリ！（※ムリじゃなかった!?）』的官方简称。《安達としまむら》原官网（`adashima.jp`）已失效，此处改用 TBS 动画官网。

</details>

## 许可证

**源代码**以 [MIT License](LICENSE) 授权，Copyright (c) 2026 近江汐莉。

**角色生日数据**（`data/` 以及 `apk/data.py` 中的同一份数据）以 [CC0 1.0](data/LICENSE) 释出并进入公有领域：可自由复制、修改、再分发，甚至商用，无需署名。

以下内容不在上述授权范围内，权利归各自所有者：

- **角色名称与相关作品** —— 版权归原作者与版权方所有，本项目仅作个人整理与展示。CC0 的释出只覆盖生日数据与界面文案本身，不能也不意图改变角色名与作品的权属。
- **`apk/flet-template/`** —— 派生自 Flet 官方的 Flutter 构建模板，授权以上游 Flet 项目为准。
