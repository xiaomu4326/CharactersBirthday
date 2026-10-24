# APK 版（Flet）

本目录是 **Android APK** 版本，用 Flet 复刻仓库根目录的 Tkinter 桌面版（`main.py` / `window.py` 等），二者相互独立、互不影响。

## 文件说明

| 文件 / 目录 | 说明 |
| --- | --- |
| `main.py` | Flet 主入口（`ft.run(main)`），复刻原版界面、配色、语言切换与每秒倒计时；倒计时为 0 天时发送**系统级通知** |
| `data.py` | 内嵌数据（角色生日 / 日文名 / 三语言文案），内容与根目录 `data/*.json` 一致 |
| `pyproject.toml` | Flet 打包元数据（应用名、包名、通知依赖、权限、自定义模板） |
| `flet-template/` | 自定义构建模板：在官方模板基础上为 `flutter_local_notifications` 预置 core library desugaring + multidex + `desugar_jdk_libs` |

> 数据内嵌为 Python 常量是为了规避 Android 上打包资源目录解析的兼容性问题，
> 保证 APK 效果与桌面版一致。修改数据时请同步根目录 `data/*.json` 与 `data.py`。

## 系统通知

倒计时等于 0 天（角色生日当天）时，通过 [`flet-android-notifications`](https://pypi.org/project/flet-android-notifications/)
（底层为 `flutter_local_notifications`）发送一条**系统通知**（出现在通知栏，退到后台也可见）。

- 依赖只在 Android 打包时安装（`tool.flet.android.dependencies`），本地 Windows 运行时自动退化为应用内 SnackBar。
- 需要的权限 `POST_NOTIFICATIONS` / `RECEIVE_BOOT_COMPLETED` 由 `tool.flet.android.permission` 注入。
- `flet build` 本身没有构建前钩子，而 `flutter_local_notifications` 要求对生成的
  Android 工程做 Gradle 反糖/多 dex 改动，因此改用**自定义构建模板**（`flet-template/`）
  在生成工程时就带好这些改动，`pyproject.toml` 通过 `tool.flet.template.url` 指向它。

## 打包命令

在**仓库根目录**执行（需要已安装 Flet CLI 与网络）：

```bash
flet build apk ./apk --arch arm64-v8a --yes --skip-flutter-doctor
```

- 产物输出到 `apk/build/apk/`。
- `--arch` 可选 `arm64-v8a`、`armeabi-v7a`、`x86_64`；省略则打包全部架构。
- 首次打包会自动下载 Flutter SDK、Android SDK、通知插件依赖（耗时较长）。
- `tool.flet.template.url = "apk/flet-template"` 是相对于当前工作目录的路径，
  因此必须在仓库根目录执行上述命令。
