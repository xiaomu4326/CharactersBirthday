<div align="center">

<img src="apk/assets/icon.png" width="170" alt="Character Birthday Countdown">

# Character Birthday Countdown

**角色生日倒计时**

Keep your favorite characters' birthdays in one small window — sorted by how soon they are, counted down to the second, switchable between Chinese / English / Japanese.

[中文](README.md) · **English**

**Windows desktop (Tkinter, zero third-party dependencies)** · **Android (Flet)**

</div>

---

## Features

| Feature | Description |
| --- | --- |
| Second-level countdown | The detail card refreshes `Nd HH:MM:SS` every second until the next birthday — no manual refresh |
| Next 5 birthdays | Cards are sorted from nearest to farthest by remaining days and scroll with the mouse wheel |
| Full selection | A read-only dropdown lists every character, ordered by upcoming birthday as well |
| Today's birthdays highlighted | At 0 days the badge turns warm `#D08770` and reads "Today"; 1 day reads "Tomorrow" |
| Automatic midnight rollover | After midnight the cards are rebuilt and the date and labels refreshed — no restart needed |
| Three languages | The top-right button cycles 中文 → English → 日本語 |
| Leap-day fallback | February 29 falls back to February 28 in non-leap years |
| HiDPI support | Calls `SetProcessDpiAwareness(1)` on Windows so the UI stays crisp |
| Birthday reminder (APK only) | Pushes a system notification on the birthday, at most once per day |
| Add characters in-app | Click "＋ Add character" in the top-right, fill in key / name / birthday; the desktop build writes back to `data/` while the APK stores it on the device — either way the UI refreshes immediately |

The UI uses the soft Nord palette (defined in [theme.py](theme.py)) — clear contrast without being harsh:

| Purpose | Color |
| --- | --- |
| Window background | `#ECEFF4` |
| Header bar | `#2E3440` |
| Card / border | `#FFFFFF` / `#E5E9F0` |
| Accent (regular badge) | `#5E81AC` |
| Accent (birthday today) | `#D08770` |

## Layout

The window defaults to `380 × 640` (minimum `340 × 520`), is centered on screen at startup, and is split into five blocks from top to bottom:

1. **Dark header** — app title, today's date, and the "Add character" / language buttons in the top-right corner
2. **Character picker** — a label plus a read-only dropdown (`DisplayName · EnglishName`)
3. **Detail card** — the selected character's name, `Birthday MM-DD · EnglishName`, and a second-level countdown to the next birthday
4. **Preview list** — "Next 5 birthdays": each card carries a rank badge, the name and birthday, and a remaining-days badge; clicking a card selects it and syncs the dropdown
5. **Footer summary** — for example "28 characters · showing top 5 by upcoming birthday"

## Quick start

### Run from source (Windows desktop)

Requires **Python 3.8+** (verified on 3.12 / 3.14). `tkinter` ships with the official installer — **there are no third-party dependencies at all**.

```bat
python main.py
```

> The font is hard-coded to `Microsoft YaHei UI` and DPI handling goes through `ctypes`, so the desktop build targets Windows.

### Build a portable exe

Double-click [build.bat](build.bat), or run it manually:

```bat
python -m PyInstaller --noconfirm --clean --onedir --windowed --name CharactersBirthday main.py
xcopy /E /I /Y data "dist\CharactersBirthday\data"
```

The output lands in `dist\CharactersBirthday\`; the whole folder can be copied anywhere and run from there.

**Key detail**: `data\` must sit next to the exe. After packaging, [paths.py](paths.py) detects how it is running through `sys.frozen` — when frozen it uses the directory of `sys.executable`, when running from source the directory of `paths.py`. Both modes share the same relative-path logic, so always ship `data` inside the exe folder.

### Build the Android APK

```bash
flet build apk ./apk --arch arm64-v8a --yes --skip-flutter-doctor
```

This must be run from the **repository root** (`tool.flet.template.url` in `apk/pyproject.toml` is resolved relative to the current working directory). The output is in `apk/build/apk/`. The first build downloads the Flutter SDK, the Android SDK and the notification plugin dependencies, so it takes a while.

See [apk/README.md](apk/README.md) for details.

## Project structure

```
CharactersBirthday/
├── main.py                     # Desktop entry point
├── window.py                   # UI assembly: header / dropdown / detail countdown / Top-5 cards / scroll area
├── theme.py                    # Color and font-size constants
├── remainDays.py               # Remaining days, next-birthday instant, second-level countdown
├── fileOperations.py           # Reads the JSON files under data/
├── paths.py                    # Locates the app directory; works from source and under PyInstaller
├── translator.py               # Loads data/lang/*.json and fills placeholders
├── data/                       # Birthdays, display names, translations
├── build.bat                   # One-command PyInstaller build
├── CharactersBirthday.spec     # PyInstaller config (onedir + windowed)
├── LICENSE                     # MIT license
└── apk/                        # Android version (standalone Flet project)
    ├── main.py                 # Flet entry point; mirrors the desktop UI and interactions
    ├── data.py                 # Embedded data (avoids Android asset-directory issues)
    ├── pyproject.toml          # App name, package id, notification dependency and permissions
    ├── assets/icon.png         # App icon
    └── flet-template/          # Custom Android build template (see below)
```

The two versions are **completely independent**: the desktop build never references `apk/`, and the APK never references the root Python modules. The only things kept in sync are the palette, font sizes and data.

## Data format

### Character birthdays

[data/characters_birthday_data.json](data/characters_birthday_data.json) — keys are the characters' **English names** (the program's unique IDs), values are `MM-DD`:

```json
{
    "OumiShiori": "04-01",
    "NanamiTōko": "02-19"
}
```

If a character has no birthday, it still appears in the dropdown but is sorted last and its remaining days show as blank.

### Display names

[data/characters_name.json](data/characters_name.json) — its keys must **match the file above exactly**:

```json
{
    "OumiShiori": "近江汐莉"
}
```

The UI shows "DisplayName · EnglishName", and the English name doubles as the internal key for dropdown and card selection.

### Adding a character

**Option 1 — inside the app.** Click **＋ Add character** in the top-right corner, fill in the key, display name and birthday, then save. The desktop build immediately rewrites both JSON files; the APK keeps custom characters in the device's local storage (it does not touch the embedded `data.py`, and they are removed when the app is uninstalled). Either way the UI refreshes right away with the new character selected.

- The key is required and must not collide with an existing one. The display name may be left empty — the key is then used as the name.
- The birthday accepts `MM-DD`, `M-D`, `MM/DD`, `MM.DD` and similar; it is normalized to `MM-DD` on save. `02-29` is valid.

**Option 2 — edit the JSON by hand.** Add the same key to **both** `characters_birthday_data.json` and `characters_name.json`; if you also maintain the APK build, sync `BIRTHDAYS` and `NAMES` in [apk/data.py](apk/data.py).

The order of entries in the JSON files does not matter — everything is re-sorted by remaining days at startup.

### Text and localization

[data/lang/](data/lang) contains `zh.json` / `en.json` / `ja.json`; all three must share exactly the same key set, and values accept `str.format` placeholders:

| Placeholder | Used by |
| --- | --- |
| `{top}` | `preview_title`, `total_count` (size of the Top-N list) |
| `{n}` | `total_count` (total number of characters) |
| `{year}` `{month}` `{day}` | `date_format` (the date in the header) |

**Adding a language** takes three changes:

1. Create `data/lang/xx.json` (same keys as `zh.json`)
2. `LANG_ORDER` and `LANG_NAMES` near the top of [window.py](window.py)
3. APK: `LANG_ORDER` / `LANG_NAMES` in [apk/main.py](apk/main.py), plus `TRANSLATIONS` in [apk/data.py](apk/data.py)

> `birthday_notification` (the birthday notification text) is an APK-only key: it lives in `apk/data.py` and is not part of `data/lang/*.json`.

## Build artifacts and version control

The repository **only tracks source code**; everything a build produces is excluded through [.gitignore](.gitignore):

| Ignored | Reason |
| --- | --- |
| `/build/` | PyInstaller intermediates (`.toc`, `PYZ`, staged exe, …) |
| `/dist/` | Packaged exe folder and release zips |
| `/apk/build/` | The Android project generated by `flet build`; can exceed 1 GB |
| `__pycache__/`, `*.py[cod]` | Python bytecode cache |
| `.idea/`, `.venv/` | IDE settings and virtualenv |
| `*.log`, `*.zip` | Build logs and release packages |
| `.gradle/`, `.dart_tool/`, `/apk/.flet/` | Gradle / Flutter caches |

**Exception**: `apk/flet-template/` must be committed — it is a **hand-modified** copy of the official template, not generated output. The modifications are:

- `isCoreLibraryDesugaringEnabled = true` + `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")` — `flutter_local_notifications` uses APIs such as `java.time`, which require desugaring below `minSdk` 26
- `multiDexEnabled = true` — `serious_python` plus the notification plugin pushes the method count past 64K
- `jniLibs` `pickFirsts` / `excludes` — works around AGP conflicts when `.so` files come from multiple sources

`flet build` has no pre-build hook, so the Gradle configuration cannot be patched after the project has been generated; pointing `tool.flet.template.url` at this custom template is the only way.


## Development notes

- To check the midnight rollover: at the end of `window.py` there is a commented-out "simulate +1 day" test block (including a test button). Uncomment it temporarily and delete it once you are done.
- To change colors or font sizes, edit [theme.py](theme.py) (desktop) and the constants with the same names at the top of [apk/main.py](apk/main.py) (APK).
- `_make_date` / `_make_datetime` in both `remainDays.py` and `apk/main.py` implement the leap-day fallback — keep them in sync when changing either.

## Notes on the data

Birthday data was compiled from public sources and is intended for personal use and reference only; where it differs from official settings, the official version wins. Character names and the related works remain the property of their original authors and rights holders.

The data itself is dedicated to the public domain under CC0 1.0 and is free to reuse — see [data/LICENSE](data/LICENSE).

<details>
<summary><b>Bundled characters (28, grouped by source work)</b></summary>

| English name (JSON key) | Display name | Birthday | Source work (official site) |
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

> Work titles are given in the original Japanese; the links point to **official sites** (TV anime official site or the publisher's special page). 「わたなれ」 is the official short title of 『わたしが恋人になれるわけないじゃん、ムリムリ！（※ムリじゃなかった!?）』. The original 「安達としまむら」 site (`adashima.jp`) is no longer online, so the TBS anime site is linked instead.

</details>

## License

**Source code** is released under the [MIT License](LICENSE), Copyright (c) 2026 近江汐莉.

**Character birthday data** (in `data/`, plus the identical copy in `apk/data.py`) is released under [CC0 1.0](data/LICENSE) and dedicated to the public domain: you may copy, modify and redistribute it freely — even commercially — with no attribution required.

The following are not covered by the above and remain the property of their respective owners:

- **Character names and the related works** — copyright their original authors and rights holders; this project merely collects and displays them for personal use. The CC0 dedication covers only the birthday data and UI strings, and neither does nor intends to change the ownership of the character names or the works.
- **`apk/flet-template/`** — derived from the official Flet Flutter build template; its licensing follows the upstream Flet project.
