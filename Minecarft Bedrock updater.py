import os
import re
import time
import json
import shutil
import subprocess
import sys
import tempfile
import locale
import warnings
import ctypes
import atexit
import winreg
import traceback

import requests
import win32api
from tqdm import tqdm

warnings.filterwarnings("ignore", category=DeprecationWarning)

ONIX_RELEASES_API = (
    "https://api.github.com/repos/OnixClient/onix_compatible_appx/releases"
)
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "BedrockUpdater/1.0 (Python requests)",
}

PYROCLASTIC_DLL_URL = (
    "https://github.com/Aetopia/Pyroclastic/releases/latest/download/gamelaunchhelper.dll"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(BASE_DIR, "languages")
DEFAULT_LANG = "en"

CACHE_DIR = os.path.join(BASE_DIR, "cache")
UPDATE_CHECK_INTERVAL = 24 * 60 * 60

MINECRAFT_PFN = "Microsoft.MinecraftUWP_8wekyb3d8bbwe"
RELEASES_PER_PAGE = 10

ELEVATION_MARKER = os.path.join(
    tempfile.gettempdir(), "bedrock_updater_elevated.marker"
)
CRASH_LOG = os.path.join(tempfile.gettempdir(), "bedrock_updater_crash.log")

DEFAULT_MESSAGES = {
    "language_name": "English",
    "main_menu": {
        "title": "========== Minecraft Bedrock Edition Updater ==========",
        "update_check": "Check for Updates",
        "downgrade": "Version Downgrade",
        "install_pyroclastic": "Install / Uninstall Pyroclastic (Auto-Update Bypass)",
        "language": "Language Settings",
        "exit": "Exit",
        "select": "Select",
        "invalid_input": "Invalid input",
    },
    "update": {
        "auto_checking": "Checking for updates automatically...",
        "new_version_available": "New version available: {0}",
        "proceed_with_update": "Proceed with update? (y/n): ",
        "no_update": "You are on the latest version",
        "current_version": "Current version: {0}",
        "latest_version": "Latest version: {0}",
        "get_failed": "Failed to get version",
        "updating": "Updating...",
        "update_complete": "Update complete",
        "update_failed": "Update failed",
        "downloading": "Downloading {0}...",
        "download_complete": "Download complete: {0}",
        "download_failed": "Download failed: {0}",
        "installing": "Installing...",
        "install_complete": "Installation complete",
        "install_failed": "Installation failed: {0}",
        "no_releases": "Could not fetch release information",
        "version_not_found": "Installer for version {0} not found",
        "using_fallback": "Using version {0} instead",
        "selected_release": "Selected release: {0} / {1}",
        "opening_store": "Opening Microsoft Store updates page...",
    },
    "downgrade": {
        "warning": "Downgrade is at your own risk.",
        "proceed": "Proceed? (y/n): ",
        "select_version": "Select version",
        "select_mode": (
            "\n1: Auto install\n"
            "2: Manual install\n"
            "3: Uninstall → Auto install\n"
            "Select (1/2/3): "
        ),
        "cancelled": "Cancelled",
        "success": "Downgrade successful!",
        "auto_failed": "Auto install failed — continue manually",
        "manual_instructions": (
            "\nManual install steps\n"
            " 1. Open file in Explorer: {0}\n"
            " 2. Allow install → wait for completion\n"
        ),
        "open_folder": "Open download folder? (y/n): ",
        "page_help": (
            "\nOperation: enter a number / n=next page / p=previous page / q=cancel"
        ),
        "page_title": "=== Version list (Page {0}/{1} / Total {2}) ===",
        "select_prompt": "Select: ",
        "last_page": "Already on the last page",
        "first_page": "Already on the first page",
        "out_of_range": "Number out of range",
        "invalid_input": "Invalid input",
        "no_versions": "No installable versions (.appx/.msixbundle etc.)",
        "total_installable": "Installable versions: {0} ({1} per page)",
    },
    "pyroclastic": {
        "menu_title": "=== Pyroclastic (Auto-Update Bypass) ===",
        "status_installed": "Current status: Installed",
        "status_not_installed": "Current status: Not installed",
        "status_unknown": "Current status: Minecraft not found",
        "menu_prompt": "\n1: Install  2: Uninstall  0: Back\nSelect: ",
        "installing": "Installing Pyroclastic (auto-update bypass)...",
        "download_failed": "Failed to download gamelaunchhelper.dll",
        "install_failed": "Failed to install Pyroclastic",
        "installed": "Pyroclastic installed successfully",
        "already_installed": "Pyroclastic is already installed",
        "not_installed": "Pyroclastic is not installed",
        "uninstalled": "Pyroclastic uninstalled successfully",
        "uninstall_failed": "Failed to uninstall: {0}",
        "minecraft_not_found": "Minecraft installation folder not found",
        "folder_not_found": "Minecraft installation folder does not exist: {0}",
        "downloading": "Downloading gamelaunchhelper.dll...",
        "copying": "Copying gamelaunchhelper.dll...",
        "verify": "Verifying installation...",
        "location": "Installed to: {0}",
    },
}


class Translator:
    def __init__(self):
        self.messages = {}
        self.current_lang = DEFAULT_LANG
        self.available_languages = self._get_available_languages()

        config_path = os.path.join(BASE_DIR, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                    saved_lang = config.get("language")
                    if saved_lang in self.available_languages:
                        self.current_lang = saved_lang
            except Exception:
                pass
        else:
            try:
                sys_lang = locale.getlocale()[0]
                if sys_lang:
                    sys_lang = sys_lang[:2]
                    if sys_lang in self.available_languages:
                        self.current_lang = sys_lang
            except Exception:
                pass

        self._load_messages()
        if not self.messages:
            self.messages = DEFAULT_MESSAGES

    def _get_available_languages(self):
        languages = {}
        if os.path.exists(LANG_DIR):
            for file in os.listdir(LANG_DIR):
                if file.endswith(".json"):
                    lang_code = file[:-5]
                    try:
                        with open(
                            os.path.join(LANG_DIR, file), encoding="utf-8"
                        ) as f:
                            lang_data = json.load(f)
                            languages[lang_code] = lang_data.get(
                                "language_name", lang_code
                            )
                    except Exception:
                        pass
        return languages or {"en": "English", "ja": "日本語"}

    def _load_messages(self):
        try:
            file_path = os.path.join(LANG_DIR, f"{self.current_lang}.json")
            if os.path.exists(file_path):
                with open(file_path, encoding="utf-8") as f:
                    self.messages = json.load(f)
        except Exception:
            self.messages = {}

    def get(self, key, *args):
        try:
            value = self.messages
            for k in key.split("."):
                value = value[k]
            return value.format(*args) if args else value
        except Exception:
            try:
                value = DEFAULT_MESSAGES
                for k in key.split("."):
                    value = value[k]
                return value.format(*args) if args else value
            except Exception:
                return key

    def save_language_setting(self):
        config_path = os.path.join(BASE_DIR, "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"language": self.current_lang}, f, indent=4)
        except Exception:
            pass

    def change_language(self):
        print("\n=== 言語設定 / Language Settings ===")
        langs = list(self.available_languages.items())
        if not langs:
            print("No languages available.")
            return False
        for i, (code, name) in enumerate(langs, 1):
            print(f"{i}: {name} ({code})")
        try:
            choice = int(
                input("\n選択 / Select (1-{}): ".format(len(langs)))
            )
            if 1 <= choice <= len(langs):
                self.current_lang = langs[choice - 1][0]
                self._load_messages()
                if not self.messages:
                    self.messages = DEFAULT_MESSAGES
                self.save_language_setting()
                print("✅ 言語を変更しました / Language changed")
                return True
        except ValueError:
            pass
        return False


tr = Translator()


def is_admin():
    test_name = "BedrockUpdaterAdminTest"
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            f"SOFTWARE\\{test_name}",
            0,
            winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY,
        ) as k:
            winreg.SetValueEx(k, "t", 0, winreg.REG_DWORD, 1)
        try:
            winreg.DeleteKey(
                winreg.HKEY_LOCAL_MACHINE, f"SOFTWARE\\{test_name}"
            )
        except Exception:
            pass
        return True
    except OSError:
        return False


def elevate_and_exit():
    try:
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)

        try:
            with open(ELEVATION_MARKER, "w") as f:
                f.write("1")
        except Exception:
            pass

        if getattr(sys, "frozen", False):
            target = [sys.executable] + sys.argv[1:]
        else:
            target = [sys.executable, script] + sys.argv[1:]

        args_str = " ".join(f'"{a}"' for a in target)

        bat_path = os.path.join(
            tempfile.gettempdir(), "bedrock_updater_elevate.bat"
        )

        bat_lines = [
            "@echo off",
            "chcp 65001 > nul",
            f'cd /d "{script_dir}"',
            args_str,
            "set RC=%ERRORLEVEL%",
            "if not %RC%==0 (",
            "  echo.",
            "  echo ========================================",
            "  echo  エラー終了コード: %RC%",
            "  echo ========================================",
            "  echo ログ: %TEMP%\\bedrock_updater_crash.log",
            "  pause",
            ")",
        ]
        bat_content = "\r\n".join(bat_lines) + "\r\n"

        write_ok = False
        for enc in ("cp932", "mbcs", "utf-8"):
            try:
                with open(bat_path, "w", encoding=enc) as f:
                    f.write(bat_content)
                write_ok = True
                break
            except Exception:
                continue
        if not write_ok:
            print("❌ 昇格用バッチの作成に失敗")
            return False

        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", bat_path, None, script_dir, 1
        )
        return int(ret) > 32
    except Exception as e:
        print(f"❌ 昇格実行に失敗: {e}")
        return False


def run_ps(cmd: str, capture=True):
    try:
        result = subprocess.run(
            ["powershell", "-NoLogo", "-NoProfile", "-Command", cmd],
            capture_output=capture,
            text=True,
            encoding="cp932",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_minecraft_install_folder():
    try:
        rc, out, _ = run_ps(
            'Get-AppxPackage -Name "Microsoft.MinecraftUWP" | '
            "Select -ExpandProperty InstallLocation"
        )
        loc = out.strip()
        if loc and os.path.exists(loc):
            return loc
    except Exception:
        pass

    new_path = r"C:\XboxGames\Minecraft for Windows\Content"
    if os.path.exists(new_path):
        return new_path

    return None


def is_pyroclastic_installed():
    folder = get_minecraft_install_folder()
    if not folder:
        return False
    return os.path.exists(os.path.join(folder, "gamelaunchhelper.dll"))


def install_pyroclastic():
    print(f"\n{tr.get('pyroclastic.installing')}")

    if is_pyroclastic_installed():
        print(f"ℹ️ {tr.get('pyroclastic.already_installed')}")
        return True

    folder = get_minecraft_install_folder()
    if not folder:
        print(f"❌ {tr.get('pyroclastic.minecraft_not_found')}")
        return False
    if not os.path.exists(folder):
        print(
            f"❌ {tr.get('pyroclastic.folder_not_found', folder)}"
        )
        return False

    print(tr.get("pyroclastic.downloading"))
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "gamelaunchhelper.dll")

        with requests.get(
            PYROCLASTIC_DLL_URL, stream=True, timeout=60
        ) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with tqdm(
                total=total, unit="iB", unit_scale=True
            ) as bar, open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

        print("✅ ダウンロード完了")
        print(tr.get("pyroclastic.copying"))

        target = os.path.join(folder, "gamelaunchhelper.dll")

        try:
            shutil.copy2(temp_path, target)
        except PermissionError:
            run_ps(
                f'Copy-Item -Path "{temp_path}" '
                f'-Destination "{target}" -Force; "ok"'
            )
            if not os.path.exists(target):
                print(
                    "⚠️ 権限エラー。管理者権限で実行しているか確認してください。"
                )
                return False

        try:
            os.remove(temp_path)
        except Exception:
            pass

        print(tr.get("pyroclastic.verify"))
        if os.path.exists(target):
            print(f"✅ {tr.get('pyroclastic.installed')}")
            print(tr.get("pyroclastic.location", target))
            return True
        else:
            print(f"❌ {tr.get('pyroclastic.install_failed')}")
            return False

    except requests.RequestException as e:
        print(f"❌ {tr.get('pyroclastic.download_failed')}: {e}")
        return False
    except Exception as e:
        print(f"❌ {tr.get('pyroclastic.install_failed')}: {e}")
        return False


def uninstall_pyroclastic():
    folder = get_minecraft_install_folder()
    if not folder:
        print(f"❌ {tr.get('pyroclastic.minecraft_not_found')}")
        return False

    target = os.path.join(folder, "gamelaunchhelper.dll")
    if not os.path.exists(target):
        print(f"ℹ️ {tr.get('pyroclastic.not_installed')}")
        return True

    try:
        os.remove(target)
        print(f"✅ {tr.get('pyroclastic.uninstalled')}")
        return True
    except Exception as e:
        print(f"❌ {tr.get('pyroclastic.uninstall_failed', e)}")
        return False


def pyroclastic_menu():
    print("\n" + tr.get("pyroclastic.menu_title"))
    folder = get_minecraft_install_folder()
    if not folder:
        print(tr.get("pyroclastic.status_unknown"))
    elif is_pyroclastic_installed():
        print(tr.get("pyroclastic.status_installed"))
    else:
        print(tr.get("pyroclastic.status_not_installed"))

    sel = input(tr.get("pyroclastic.menu_prompt")).strip()
    if sel == "1":
        install_pyroclastic()
    elif sel == "2":
        if is_pyroclastic_installed():
            uninstall_pyroclastic()
        else:
            print(f"ℹ️ {tr.get('pyroclastic.not_installed')}")
    elif sel == "0":
        return
    else:
        print(tr.get("main_menu.invalid_input"))


def get_minecraft_windows_path():
    new_path = (
        r"C:\XboxGames\Minecraft for Windows\Content\Minecraft.Windows.exe"
    )
    if os.path.exists(new_path):
        return new_path

    rc, out, _ = run_ps(
        'Get-AppxPackage -Name "Microsoft.MinecraftUWP" | '
        "Select -ExpandProperty InstallLocation"
    )
    loc = out.strip()
    if loc:
        exe_legacy = os.path.join(loc, "Minecraft.Windows.exe")
        if os.path.exists(exe_legacy):
            return exe_legacy
    return None


def get_current_version(exe_path):
    if not exe_path or not os.path.exists(exe_path):
        return None
    try:
        manifest_path = os.path.join(
            os.path.dirname(exe_path), "AppxManifest.xml"
        )
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(
                    r'<Identity.*?Version="(\d+\.\d+\.\d+\.\d+)"', content
                )
                if match:
                    return match.group(1)
    except Exception:
        pass
    try:
        info = win32api.GetFileVersionInfo(exe_path, "\\")
        ms, ls = info["FileVersionMS"], info["FileVersionLS"]
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        pass
    return None


def open_store_updates_page():
    print(tr.get("update.opening_store"))
    os.system("start ms-windows-store://updates")


def get_latest_bedrock_version():
    try:
        r = requests.get("https://aka.ms/MinecraftStatus", timeout=5)
        if r.status_code == 200:
            data = r.json()
            for package in data.get("packages", []):
                if package.get("name") == "Microsoft.MinecraftUWP":
                    v = package.get("version")
                    if v:
                        return v
    except Exception:
        pass

    try:
        r = requests.get(
            "https://launcherapi.mojang.com/v1/products/mcgp/manifest.json",
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            for v in data.get("versions", []):
                if (
                    v.get("platform") == "windows-x64"
                    and v.get("type") == "release"
                ):
                    ver = v.get("version")
                    if ver:
                        return ver
    except Exception:
        pass

    try:
        r = requests.get(
            "https://feedback.minecraft.net/hc/en-us/sections/"
            "360001186971-Release-Changelogs",
            timeout=5,
        )
        if r.status_code == 200:
            match = re.search(
                r"Minecraft — (\d+\.\d+\.\d+(?:\.\d+)?)", r.text
            )
            if match:
                v = match.group(1)
                if v.count(".") == 2:
                    v += ".0"
                return v
    except Exception:
        pass

    return None


def version_tuple(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return ()


def compare_versions(a, b):
    names = ["メジャー", "マイナー", "パッチ", "ビルド"]
    result = []
    n = max(len(a), len(b))
    for i in range(n):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x != y:
            label = names[i] if i < len(names) else f"その他{i}"
            result.append(f"{label}: {x} → {y}")
    return result


def get_onix_versions():
    try:
        r = requests.get(
            ONIX_RELEASES_API, headers=GITHUB_HEADERS, timeout=10
        )
        r.raise_for_status()
        releases = r.json()
        return [
            (rel["tag_name"], rel["assets"])
            for rel in releases
            if rel["assets"]
        ]
    except Exception as e:
        print(f"⚠️ Onix バージョン一覧取得失敗: {e}")
        return []


def find_asset_url(
    assets, exts=(".msixbundle", ".appxbundle", ".appx", ".msixvc")
):
    for asset in assets:
        name = asset.get("name", "")
        if name.lower().endswith(exts):
            return asset.get("browser_download_url"), name

    for asset in assets:
        name = asset.get("name", "").lower()
        if "minecraft" in name and name.endswith((".zip", ".rar")):
            return asset.get("browser_download_url"), asset.get("name")

    return None, None


def filter_installable_releases(vers):
    result = []
    for tag, assets in vers:
        url, fname = find_asset_url(assets)
        if url and fname:
            result.append((tag, url, fname))
    return result


def select_release_paged(releases, page_size=RELEASES_PER_PAGE):
    total = len(releases)
    if total == 0:
        print(tr.get("downgrade.no_versions"))
        return None

    total_pages = (total + page_size - 1) // page_size
    page = 0

    while True:
        start = page * page_size
        end = min(start + page_size, total)

        print(
            "\n"
            + tr.get(
                "downgrade.page_title",
                page + 1,
                total_pages,
                total,
            )
        )
        for i in range(start, end):
            tag = releases[i][0]
            fname = releases[i][2]
            print(f"{i + 1}: {tag}  ({fname})")

        print(tr.get("downgrade.page_help"))
        sel = input(tr.get("downgrade.select_prompt")).strip().lower()

        if sel == "q":
            return None
        if sel == "n":
            if page < total_pages - 1:
                page += 1
            else:
                print(tr.get("downgrade.last_page"))
            continue
        if sel == "p":
            if page > 0:
                page -= 1
            else:
                print(tr.get("downgrade.first_page"))
            continue
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < total:
                return idx
            print(tr.get("downgrade.out_of_range"))
            continue
        print(tr.get("downgrade.invalid_input"))


def download_bundle(url, filename):
    print(f"\n{tr.get('update.downloading', filename)}")
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)

        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with tqdm(
                total=total, unit="iB", unit_scale=True
            ) as bar, open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))

        print(f"✅ {tr.get('update.download_complete', temp_path)}")

        def cleanup_temp_file():
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print("✨ 一時ファイルを削除しました")
            except Exception as e:
                print(f"⚠️ 一時ファイルの削除に失敗: {e}")

        atexit.register(cleanup_temp_file)
        return temp_path
    except Exception as e:
        print(f"❌ {tr.get('update.download_failed', e)}")
        return None


def uninstall_minecraft():
    if not is_admin():
        print("⚠️ 管理者権限が必要です。")
        return False
    rc, _, err = run_ps(
        'Get-AppxPackage -Name "Microsoft.MinecraftUWP" | Remove-AppxPackage'
    )
    if rc == 0:
        print("✅ アンインストール完了")
        return True
    print("❌ アンインストール失敗:", err.strip())
    return False


def install_appx(path, force=False):
    if not is_admin():
        print("⚠️ 管理者権限が必要です。")
        return False

    print(tr.get("update.installing"))
    try:
        ps = [
            "Add-AppxPackage",
            f'-Path "{path}"',
            "-AllowUnsigned",
            "-ForceApplicationShutdown",
        ]
        if force:
            ps.append("-ForceUpdateFromAnyVersion")
        rc, _, err = run_ps(" ".join(ps))

        if rc == 0:
            print(f"✅ {tr.get('update.install_complete')}")
            return True

        if "0x80073D06" in err and not force:
            print("↺ 新しいバージョンが存在 → 強制インストールで処理開始")
            return install_appx(path, force=True)

        print(f"❌ {tr.get('update.install_failed', err.strip())}")
        return False
    except Exception as e:
        print(f"❌ {tr.get('update.install_failed', e)}")
        return False


def start_update_with_powershell():
    latest_version = get_latest_bedrock_version()
    if not latest_version:
        print(f"❌ {tr.get('update.get_failed')}")
        return

    vers = get_onix_versions()
    if not vers:
        print(f"❌ {tr.get('update.no_releases')}")
        return

    installable = filter_installable_releases(vers)
    if not installable:
        print(f"❌ {tr.get('update.no_releases')}")
        return

    url, fname, tag = None, None, None
    for r_tag, r_url, r_fname in installable:
        if r_tag.replace("v", "") == latest_version:
            url, fname, tag = r_url, r_fname, r_tag
            break

    if not url:
        print(
            f"❌ {tr.get('update.version_not_found', latest_version)}"
        )
        tag, url, fname = installable[0]
        print(f"⚠️ {tr.get('update.using_fallback', tag)}")

    print(tr.get("update.selected_release", tag, fname))

    path = download_bundle(url, fname)
    if not path:
        return

    try:
        subprocess.run(
            ["taskkill", "/IM", "Minecraft.Windows.exe", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    if install_appx(path):
        print(f"\n✨ {tr.get('update.update_complete')}: {tag}")
        if is_pyroclastic_installed():
            print("ℹ️ Pyroclastic は既にインストールされています")
        else:
            print("🔄 更新後の自動更新を防ぐため Pyroclastic を適用します...")
            install_pyroclastic()
    else:
        print(f"\n❌ {tr.get('update.update_failed')}")
        print(f"  エクスプローラーで開く: {path}")
        os.system(f'explorer /select,"{path}"')


def downgrade_minecraft():
    print("\n⚠️ " + tr.get("downgrade.warning"))
    if input(tr.get("downgrade.proceed")).lower() != "y":
        return

    if is_pyroclastic_installed():
        print("ℹ️ Pyroclastic は既にインストールされています")
    else:
        print("🔄 自動更新を防ぐため Pyroclastic をインストールします...")
        if not install_pyroclastic():
            print("⚠️ Pyroclastic のインストールに失敗しました。")
            print("   自動更新が有効なままダウングレードを続行しますか？")
            if input(tr.get("downgrade.proceed")).lower() != "y":
                return

    vers = get_onix_versions()
    if not vers:
        return

    installable = filter_installable_releases(vers)
    if not installable:
        print("❌ " + tr.get("downgrade.no_versions"))
        return

    print(
        "\n"
        + tr.get(
            "downgrade.total_installable",
            len(installable),
            RELEASES_PER_PAGE,
        )
    )

    idx = select_release_paged(installable, page_size=RELEASES_PER_PAGE)
    if idx is None:
        print(tr.get("downgrade.cancelled"))
        return

    tag, url, fname = installable[idx]

    mode = input(tr.get("downgrade.select_mode")).strip()

    if mode == "3":
        if not uninstall_minecraft():
            return

    path = download_bundle(url, fname)
    if not path:
        return

    if mode in {"1", "3"}:
        if install_appx(path):
            print(f"\n✨ {tr.get('downgrade.success')}")
            if not is_pyroclastic_installed():
                print("🔄 Pyroclastic を再適用します...")
                install_pyroclastic()
            else:
                print("✅ Pyroclastic は正常にインストールされています")
            return
        print("\n" + tr.get("downgrade.auto_failed"))

    print(tr.get("downgrade.manual_instructions", path))
    if input(tr.get("downgrade.open_folder")).lower() == "y":
        os.system(f'explorer /select,"{path}"')


def check_for_updates_auto():
    last_check_file = os.path.join(CACHE_DIR, "last_check.json")
    try:
        if os.path.exists(last_check_file):
            with open(last_check_file, "r") as f:
                data = json.load(f)
                if (
                    time.time() - data["last_check"]
                    < UPDATE_CHECK_INTERVAL
                ):
                    return False
    except Exception:
        pass

    print(tr.get("update.auto_checking"))
    exe = get_minecraft_windows_path()
    cur = get_current_version(exe) if exe else None
    lat = get_latest_bedrock_version()

    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(last_check_file, "w") as f:
            json.dump({"last_check": time.time()}, f)
    except Exception:
        pass

    if cur and lat:
        print(tr.get("update.current_version", cur))
        print(tr.get("update.latest_version", lat))
        c = version_tuple(cur)
        l = version_tuple(lat)
        if c and l and c < l:
            print(f"🚨 {tr.get('update.new_version_available', lat)}")
            return True
        else:
            print(tr.get("update.no_update"))
    return False


def main():
    was_elevated = os.path.exists(ELEVATION_MARKER)
    try:
        os.remove(ELEVATION_MARKER)
    except Exception:
        pass

    if not is_admin():
        print("⚠️ このツールは管理者権限が必要です。")
        print("   UAC を承認すると管理者権限で再起動します。")
        ans = input("昇格して再起動しますか？ (y/n): ").strip().lower()
        if ans == "y":
            if elevate_and_exit():
                sys.exit(0)
            print("❌ 昇格できませんでした。")
            input("Enter で終了…")
            sys.exit(1)
        else:
            print("⚠️ 非管理者モードで起動します。")
    else:
        if was_elevated:
            print("✅ 管理者権限で起動しました")

    if is_pyroclastic_installed():
        print("💡 Pyroclastic はインストール済みです（自動更新バイパス有効）")

    if check_for_updates_auto():
        if input(tr.get("update.proceed_with_update")).lower() == "y":
            start_update_with_powershell()

    while True:
        print("\n" + tr.get("main_menu.title"))
        options = [
            ("exit", "0"),
            ("update_check", "1"),
            ("downgrade", "2"),
            ("install_pyroclastic", "3"),
            ("language", "4"),
        ]

        for key, num in options:
            print(f"{num}: {tr.get(f'main_menu.{key}')}")

        sel = input(
            f"\n{tr.get('main_menu.select')} (0-4): "
        ).strip()

        if not sel.isdigit() or not (0 <= int(sel) <= 4):
            print(tr.get("main_menu.invalid_input"))
            continue

        sel_num = int(sel)
        if sel_num == 0:
            break
        elif sel_num == 1:
            exe = get_minecraft_windows_path()
            cur = get_current_version(exe) if exe else None
            lat = get_latest_bedrock_version()

            print("\n--- バージョン情報 ---")
            print(tr.get("update.current_version", cur or tr.get("update.get_failed")))
            print(tr.get("update.latest_version", lat or tr.get("update.get_failed")))

            if cur and lat:
                c = version_tuple(cur)
                l = version_tuple(lat)
                if c and l:
                    if c < l:
                        print(f"\n🚨 {tr.get('update.new_version_available', lat)}")
                        sub = input(
                            "\n1: 自動更新  2: Store を開く: "
                        ).strip()
                        if sub == "1":
                            start_update_with_powershell()
                        elif sub == "2":
                            open_store_updates_page()
                    else:
                        print(f"\n🎉 {tr.get('update.no_update')}")
        elif sel_num == 2:
            downgrade_minecraft()
        elif sel_num == 3:
            pyroclastic_menu()
        elif sel_num == 4:
            tr.change_language()


if __name__ == "__main__":
    was_elevated = os.path.exists(ELEVATION_MARKER)
    try:
        main()
    except KeyboardInterrupt:
        print("\n終了します…")
    except SystemExit:
        raise
    except BaseException:
        tb = traceback.format_exc()
        try:
            with open(CRASH_LOG, "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            pass
        print("\n" + "=" * 60)
        print("❌ 予期しないエラーが発生しました")
        print("=" * 60)
        print(tb)
        print(f"\nログ保存先: {CRASH_LOG}")
        if was_elevated:
            try:
                input("\nEnter で終了…")
            except EOFError:
                pass
        sys.exit(1)