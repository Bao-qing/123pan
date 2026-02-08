"""
123pan 控制台交互界面 —— 仅负责用户 IO，所有业务调用 Pan123Core。
"""

import os
import sys
from typing import List

from pan123_core import Pan123Core, format_size, make_result


# ──────────────── 颜色工具 ────────────────

class Color:
    """ANSI 颜色常量"""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    PURPLE = "\033[35m"
    CYAN = "\033[96m"


def colored(text: str, color: str) -> str:
    return f"{color}{text}{Color.RESET}"


# ──────────────── CLI 类 ────────────────

class Pan123CLI:
    """控制台交互界面"""

    HELP_TEXT = """可用命令:
  ls                 - 显示当前目录
  cd [编号|..|/]     - 切换目录
  mkdir [名称]       - 创建目录
  upload [路径]      - 上传文件
  rm [编号]          - 删除文件
  share [编号 ...]   - 创建分享
  link [编号]        - 获取文件直链
  download/d [编号]  - 下载文件
  recycle            - 管理回收站
  refresh/re         - 刷新目录
  reload             - 重新加载配置并刷新
  login              - 登录
  logout             - 登出并清除 token
  clearaccount       - 清除已登录账号（包括用户名和密码）
  more               - 继续加载更多文件
  protocol [android|web] - 切换协议
  exit               - 退出程序"""

    def __init__(self, config_file: str = "123pan_config.json"):
        self.core = Pan123Core(config_file=config_file)
        self._download_mode: int = 0  # 0=询问, 3=全部覆盖, 4=全部跳过

    # ──────────────── 启动 ────────────────

    def run(self) -> None:
        """主入口"""
        # Windows cmd 颜色支持
        if os.name == "nt":
            os.system("")

        self._print_banner()
        self._init_login()

        while True:
            try:
                prompt = colored(f"{self.core.cwd_path}>", Color.RED) + " "
                command = input(prompt).strip()
                if not command:
                    continue
                self._dispatch(command)
            except KeyboardInterrupt:
                print("\n操作已取消")
            except EOFError:
                break
            except Exception as e:
                print(colored(f"发生错误: {e}", Color.RED))

    # ──────────────── 初始化 ────────────────

    def _print_banner(self) -> None:
        print("=" * 60)
        print("123网盘客户端".center(56))
        print("=" * 60)

    def _init_login(self) -> None:
        """尝试加载配置 -> 尝试访问目录 -> 必要时登录"""
        self.core.load_config()

        r = self.core.refresh()
        if r["code"] != 0:
            # 需要登录
            if not self.core.user_name:
                self.core.user_name = input("请输入用户名: ")
            if not self.core.password:
                self.core.password = input("请输入密码: ")
            lr = self.core.login()
            self._print_result(lr)
            if lr["code"] == 0:
                self.core.refresh()

        self._show_files()

    # ──────────────── 命令分发 ────────────────

    def _dispatch(self, command: str) -> None:
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        handler = {
            "ls": lambda: self._show_files(),
            "login": lambda: self._do_login(),
            "logout": lambda: self._do_logout(),
            "clearaccount": lambda: self._do_clear_account(),
            "exit": lambda: sys.exit(0),
            "cd": lambda: self._do_cd(arg),
            "mkdir": lambda: self._do_mkdir(arg),
            "upload": lambda: self._do_upload(arg),
            "rm": lambda: self._do_rm(arg),
            "share": lambda: self._do_share(arg),
            "more": lambda: self._do_more(),
            "link": lambda: self._do_link(arg),
            "download": lambda: self._do_download(arg),
            "d": lambda: self._do_download(arg),
            "recycle": lambda: self._do_recycle(),
            "refresh": lambda: self._do_refresh(),
            "re": lambda: self._do_refresh(),
            "reload": lambda: self._do_reload(),
            "protocol": lambda: self._do_protocol(arg),
            "help": lambda: print(self.HELP_TEXT),
        }.get(cmd)

        if handler:
            handler()
        elif cmd.isdigit():
            self._do_select(int(cmd))
        else:
            print(self.HELP_TEXT)

    # ──────────────── 显示 ────────────────

    def _show_files(self) -> None:
        items = self.core.file_list
        if not items:
            print("当前目录为空")
            return
        print()
        print("=" * 60)
        print(f"当前路径: {self.core.cwd_path}")
        print("-" * 60)
        print(f"{'编号':<6}{'类型':<8}{'大小':<12}{'名称'}")
        print("-" * 60)
        for idx, item in enumerate(items, 1):
            is_dir = item["Type"] == 1
            type_str = "文件夹" if is_dir else "文件"
            size_str = format_size(item["Size"])
            color = Color.PURPLE if is_dir else Color.YELLOW
            print(colored(f"{idx:<6}{type_str:<8}{size_str:<12}{item['FileName']}", color))
        if not self.core.all_loaded:
            remaining = self.core.file_total - len(items)
            print(f"\n还有 {remaining} 个文件未加载，输入 'more' 继续加载")
        print("=" * 60 + "\n")

    def _print_result(self, r: dict) -> None:
        """打印 Result 消息"""
        if r["code"] == 0:
            print(colored(r["message"], Color.GREEN))
        else:
            print(colored(f"[错误 {r['code']}] {r['message']}", Color.RED))

    # ──────────────── 命令实现 ────────────────

    def _do_login(self) -> None:
        if not self.core.user_name:
            self.core.user_name = input("请输入用户名: ")
        if not self.core.password:
            self.core.password = input("请输入密码: ")
        r = self.core.login()
        self._print_result(r)
        if r["code"] == 0:
            self._do_refresh()

    def _do_logout(self) -> None:
        r = self.core.logout()
        self._print_result(r)

    def _do_clear_account(self) -> None:
        """清除已登录账号：清除用户名、密码、token 等信息"""
        confirm = input("确定要清除已登录账号信息吗？(y/N): ").strip().lower()
        if confirm == 'y':
            r = self.core.clear_account()
            self._print_result(r)
        else:
            print("操作已取消")

    def _do_cd(self, arg: str) -> None:
        if arg == "..":
            r = self.core.cd_up()
        elif arg == "/":
            r = self.core.cd_root()
        elif arg.isdigit():
            r = self.core.cd(int(arg) - 1)
        else:
            print("用法: cd [编号|..|/]")
            return
        if r["code"] != 0:
            self._print_result(r)
        else:
            self._show_files()

    def _do_mkdir(self, name: str) -> None:
        if not name:
            name = input("请输入目录名: ")
        r = self.core.mkdir(name)
        self._print_result(r)
        if r["code"] == 0:
            self._do_refresh()

    def _do_upload(self, path: str) -> None:
        if not path:
            path = input("请输入文件路径: ")
        r = self.core.upload_file(path, on_progress=self._upload_progress)
        if r["code"] == 5060:
            choice = input("检测到同名文件，输入 1 覆盖，2 保留两者，其他取消: ")
            if choice == "1":
                r = self.core.upload_file(path, duplicate=1, on_progress=self._upload_progress)
            elif choice == "2":
                r = self.core.upload_file(path, duplicate=2, on_progress=self._upload_progress)
            else:
                print("上传取消")
                return
        print()  # 换行
        self._print_result(r)
        if r["code"] == 0:
            self._do_refresh()

    def _do_rm(self, arg: str) -> None:
        if not arg.isdigit():
            print("请提供文件编号")
            return
        r = self.core.trash_by_index(int(arg) - 1)
        self._print_result(r)
        if r["code"] == 0:
            self._do_refresh()

    def _do_share(self, arg: str) -> None:
        indices = [int(x) - 1 for x in arg.split() if x.isdigit()]
        if not indices:
            print("请提供文件编号")
            return
        # 显示待分享的文件
        names = [self.core.file_list[i]["FileName"] for i in indices if 0 <= i < len(self.core.file_list)]
        print("分享文件:", ", ".join(names))
        pwd = input("输入提取码(留空跳过): ").strip()
        r = self.core.share_by_indices(indices, pwd)
        self._print_result(r)
        if r["code"] == 0:
            print(f"链接: {r['data']['share_url']}")
            if r["data"]["share_pwd"]:
                print(f"提取码: {r['data']['share_pwd']}")

    def _do_more(self) -> None:
        r = self.core.load_more()
        if r["code"] != 0:
            self._print_result(r)
        else:
            self._show_files()

    def _do_link(self, arg: str) -> None:
        if not arg.isdigit():
            print("请提供文件编号")
            return
        r = self.core.get_download_url(int(arg) - 1)
        if r["code"] == 0:
            print(f"文件直链: {r['data']['url']}")
        else:
            self._print_result(r)

    def _do_download(self, arg: str) -> None:
        if not arg.isdigit():
            print("请提供文件编号")
            return
        idx = int(arg) - 1
        if not (0 <= idx < len(self.core.file_list)):
            print("无效的文件编号")
            return
        item = self.core.file_list[idx]
        print(f"开始下载: {item['FileName']}")

        overwrite = self._download_mode == 3
        skip = self._download_mode == 4
        r = self.core.download_file(
            idx,
            on_progress=self._download_progress,
            overwrite=overwrite,
            skip_existing=skip,
        )
        # 冲突处理
        if r["code"] == 1 and r.get("data", {}).get("conflict"):
            print(f"文件已存在: {item['FileName']}")
            choice = input("输入 1 覆盖，2 跳过，3 全部覆盖，4 全部跳过: ").strip()
            if choice == "4":
                self._download_mode = 4
                print("跳过下载")
                return
            elif choice == "2":
                print("跳过下载")
                return
            elif choice == "3":
                self._download_mode = 3
            r = self.core.download_file(idx, on_progress=self._download_progress, overwrite=True)

        print()  # 换行
        self._print_result(r)

    def _do_recycle(self) -> None:
        r = self.core.list_recycle()
        if r["code"] != 0:
            self._print_result(r)
            return
        items = r["data"]
        if not items:
            print("回收站为空")
            return
        print("\n回收站内容:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item['FileName']} ({format_size(item['Size'])})")
        action = input("\n输入编号恢复文件，或输入 'clear' 清空回收站: ").strip()
        if action.isdigit():
            idx = int(action) - 1
            if 0 <= idx < len(items):
                rr = self.core.restore(items[idx]["FileId"])
                self._print_result(rr)
            else:
                print("无效编号")
        elif action == "clear":
            for item in items:
                self.core.trash(item, delete=True)
            print("回收站已清空")
        self._do_refresh()

    def _do_refresh(self) -> None:
        self._download_mode = 0
        r = self.core.refresh()
        if r["code"] != 0:
            self._print_result(r)
        else:
            self._show_files()

    def _do_reload(self) -> None:
        r = self.core.load_config()
        self._print_result(r)
        self._do_refresh()

    def _do_protocol(self, arg: str) -> None:
        if arg.lower() not in ("android", "web"):
            print("请指定协议: android 或 web")
            return
        r = self.core.set_protocol(arg.lower())
        self._print_result(r)
        if r["code"] == 0:
            self._do_refresh()

    def _do_select(self, num: int) -> None:
        """数字选择：文件夹进入，文件下载"""
        idx = num - 1
        if not (0 <= idx < len(self.core.file_list)):
            print("无效的文件编号")
            return
        if self.core.file_list[idx]["Type"] == 1:
            self._do_cd(str(num))
        else:
            self._do_download(str(num))

    # ──────────────── 进度回调 ────────────────

    @staticmethod
    def _download_progress(downloaded: int, total: int, speed: float) -> None:
        if total > 0:
            pct = downloaded / total * 100
            print(
                f"\r进度: {pct:.1f}% | {format_size(downloaded)}/{format_size(total)} | {format_size(int(speed))}/s",
                end="     ",
                flush=True,
            )

    @staticmethod
    def _upload_progress(uploaded: int, total: int) -> None:
        if total > 0:
            pct = uploaded / total * 100
            print(f"\r上传进度: {pct:.1f}%", end="", flush=True)


# ──────────────── 入口 ────────────────

if __name__ == "__main__":
    Pan123CLI().run()