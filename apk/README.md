# APK 版（Flet）

本目录是 **Android APK** 版本，用 Flet 复刻仓库根目录的 Tkinter 桌面版（`main.py` / `window.py` 等），二者相互独立、互不影响。

## 文件说明

| 文件 / 目录 | 说明 |
| --- | --- |
| `main.py` | Flet 主入口（`ft.run(main)`），复刻原版界面、配色、语言切换与每秒倒计时；支持应用内添加角色；倒计时为 0 天时发送**系统级通知** |
| `data.py` | 内嵌数据（角色生日 / 日文名 / 三语言文案），内容与根目录 `data/*.json` 一致 |
| `pyproject.toml` | Flet 打包元数据（应用名、包名、通知依赖、权限、自定义模板） |
| `flet-template/` | 自定义构建模板：在官方模板基础上为 `flutter_local_notifications` 预置 core library desugaring + multidex + `desugar_jdk_libs` |

> 数据内嵌为 Python 常量是为了规避 Android 上打包资源目录解析的兼容性问题，
> 保证 APK 效果与桌面版一致。修改数据时请同步根目录 `data/*.json` 与 `data.py`。

## 添加 / 删除角色

界面右上角有「设置」按钮，添加与删除都在这个设置页里完成（先选「添加角色」或「删除角色」再进入子页），交互与桌面版一致：添加子页填写**键名**（必填、不可重复）、**角色名**（留空则用键名占位）、**生日**（支持 `MM-DD`、`M-D`、`MM/DD`、`MM.DD`，保存时统一成 `MM-DD`，`02-29` 合法）。

- APK 内的 `data.py` 是打包进应用的**只读**数据，运行时不会被改写；自定义角色改存到设备的键值存储
  中（Flet 1.x 的 `page.shared_preferences`，旧版本自动回退到 `page.client_storage`），键名为
  `custom_characters`，内容形如 `{"键名": {"name": "显示名", "birthday": "MM-DD"}}`。
- 启动时读取该存储并并入内存数据；新增或读取成功后都会重建卡片、刷新下拉框与统计，并自动选中新角色。
- 写入失败会回滚内存中的改动，不会出现"界面上有、重启后没了"的半条数据。
- 卸载应用会连同这些自定义角色一起清除；内置角色不受影响。

**删除角色**：在设置页下半部分从「选择要删除的角色」里选中目标，点删除并确认即可；删完设置页保持打开，候选列表同步刷新。

- 应用内添加的角色直接从 `custom_characters` 中移除。
- 内置角色的数据在包内改不了，删除时改记一条**墓碑**到 `deleted_characters`（键名数组），启动时据此把它们从内存数据里剔除，所以重启后依旧不显示。
- 重新用「＋ 添加角色」加回同一个键名，会自动清掉对应墓碑（生日需要重新填写）。
- 同样地，写存储失败时不会改动内存数据，并弹出提示。

## 系统通知

倒计时等于 0 天（角色生日当天）时，通过 [`flet-android-notifications`](https://pypi.org/project/flet-android-notifications/)
（底层为 `flutter_local_notifications`）发送一条**系统通知**（出现在通知栏，退到后台也可见）。

- 依赖只在 Android 打包时安装（`tool.flet.android.dependencies`），本地 Windows 运行时自动退化为应用内 SnackBar。
- 需要的权限 `POST_NOTIFICATIONS` / `RECEIVE_BOOT_COMPLETED` 由 `tool.flet.android.permission` 注入。
- `flet build` 本身没有构建前钩子，而 `flutter_local_notifications` 要求对生成的
  Android 工程做 Gradle 反糖/多 dex 改动，因此改用**自定义构建模板**（`flet-template/`）
  在生成工程时就带好这些改动，`pyproject.toml` 通过 `tool.flet.template.url` 指向它。

## 打包命令

在**本目录（`apk/`）**内执行（需要已安装 Flet CLI 与网络）：

```bash
flet build apk . --arch arm64-v8a --yes --skip-flutter-doctor
```

- 产物输出到 `apk/build/apk/`。
- `--arch` 可选 `arm64-v8a`、`armeabi-v7a`、`x86_64`；省略则打包全部架构。
- 首次打包会自动下载 Flutter SDK、Android SDK、通知插件依赖（耗时较长）。
- `tool.flet.template.url = "flet-template"` 是相对于**当前工作目录**的路径，
  所以必须在 `apk/` 目录里执行上述命令。

## 发布签名

`flet build` 每次重新渲染 Android 工程时，签名配置来自环境变量；少了就退回 debug
签名，装到已安装正式签名的手机上会报 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`。

- 发布构建：`pwsh -File build_apk_signed.ps1 -KeystoreInfo "<keystore 说明文件.txt>"`  
  脚本从说明文件里读 store 口令，设置 `FLET_ANDROID_SIGNING_KEY_*` 四个环境变量，
  构建后自动用 `apksigner` 校验证书。
- `build_apk.bat`：不带签名的快速构建（debug 签名），只适合模拟器或全新安装的设备。
