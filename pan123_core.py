"""
123pan 网盘内核模块
所有公开方法统一返回 Result 字典::
    {
        "code": int,       # 0 = 成功，小于 0 = 失败 大于 0 = 警告
        "message": str,    # 结果描述
        "data": Any        # 业务数据，失败时为 None
    }
"""

import hashlib
import json
import os
import random
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import requests

# ════════════════════════════════════════════════════════════════
#  全局常量 —— URL / 端点 / 超时 / 分块 / 设备信息
# ════════════════════════════════════════════════════════════════

# ── 基础域名 ──────────────────────────────────────────────────
API_BASE_URL = "https://www.123pan.com"
"""123pan API 根地址"""

# ── 接口端点（相对路径，使用时拼接 API_BASE_URL）────────────────
URL_LOGIN = "/b/api/user/sign_in"
"""登录接口"""

URL_FILE_LIST = "/api/file/list/new"
"""文件列表接口（GET，支持目录浏览与回收站查询）"""

URL_FILE_TRASH = "/a/api/file/trash"
"""文件删除 / 恢复接口"""

URL_SHARE_CREATE = "/a/api/share/create"
"""创建分享接口"""

URL_DOWNLOAD_INFO = "/a/api/file/download_info"
"""单文件下载信息接口"""

URL_BATCH_DOWNLOAD = "/a/api/file/batch_download_info"
"""批量（文件夹）下载信息接口 服务端会进行打包下载"""

URL_UPLOAD_REQUEST = "/b/api/file/upload_request"
"""上传请求接口（含创建目录）"""

URL_UPLOAD_PARTS = "/b/api/file/s3_repare_upload_parts_batch"
"""分块上传预签名 URL 获取接口"""

URL_UPLOAD_COMPLETE_S3 = "/b/api/file/s3_complete_multipart_upload"
"""S3 分块合并接口"""

URL_UPLOAD_COMPLETE = "/b/api/file/upload_complete"
"""上传完成确认接口"""

URL_MKDIR = "/a/api/file/upload_request"
"""创建目录接口（复用 upload_request，type=1）"""

URL_USER_INFO = "/b/api/user/info"
"""获取用户信息接口"""

URL_DETAILS = "/b/api/restful/goapi/v1/file/details"
"""获取文件夹详情接口"""

SHARE_URL_TEMPLATE = "{base}/s/{key}"
"""分享链接模板，{base} = API_BASE_URL，{key} = ShareKey"""

# ── 超时配置（秒）────────────────────────────────────────────
TIMEOUT_DEFAULT = 15
"""默认请求超时"""

TIMEOUT_FILE_LIST = 30
"""文件列表请求超时（数据量可能较大）"""

TIMEOUT_UPLOAD_CHUNK = 30
"""单个分块上传超时"""

TIMEOUT_DOWNLOAD = 30
"""下载请求超时"""

TIMEOUT_TRASH = 10
"""删除 / 恢复操作超时"""

# ── 上传 / 下载参数 ──────────────────────────────────────────
UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024
"""分块上传单块大小（5 MB）"""

DOWNLOAD_CHUNK_SIZE = 8192
"""下载流式读取单块大小（8 KB）"""

MD5_READ_CHUNK_SIZE = 65536
"""计算文件 MD5 时的读取块大小（64 KB）"""

# ── 翻页 / 限频 ─────────────────────────────────────────────
FILE_LIST_PAGE_LIMIT = 100
"""单页最大文件数"""

RATE_LIMIT_INTERVAL = 10
"""连续翻页时的限频等待秒数"""

RATE_LIMIT_PAGES = 5
"""每翻多少页触发一次限频等待"""

S3_MERGE_DELAY = 1
"""S3 分块合并后等待服务器处理的秒数"""

# ── 业务错误码 ───────────────────────────────────────────────
CODE_OK = 0
"""统一成功码"""

CODE_LOGIN_OK = 200
"""123pan 登录接口成功时返回的原始码"""

CODE_DUPLICATE_FILE = 5060
"""上传时同名文件已存在的错误码"""

CODE_CONFLICT = 1
"""自定义：本地文件冲突（下载时目标已存在）"""

# ── 设备信息池（Android 协议伪装）─────────────────────────────
DEVICE_TYPES: List[str] = [
    "24075RP89G", "24076RP19G", "24076RP19I", "M1805E10A", "M2004J11G",
    "M2012K11AG", "M2104K10I", "22021211RG", "22021211RI", "21121210G",
    "23049PCD8G", "23049PCD8I", "23013PC75G", "24069PC21G", "24069PC21I",
    "23113RKC6G", "M1912G7BI", "M2007J20CI", "M2007J20CG", "M2007J20CT",
    "M2102J20SG", "M2102J20SI", "21061110AG", "2201116PG", "2201116PI",
    "22041216G", "22041216UG", "22111317PG", "22111317PI", "22101320G",
    "22101320I", "23122PCD1G", "23122PCD1I", "2311DRK48G", "2311DRK48I",
    "2312FRAFDI", "M2004J19PI",
]
"""可选的 Android 设备型号列表"""

OS_VERSIONS: List[str] = [
    "Android_7.1.2", "Android_8.0.0", "Android_8.1.0", "Android_9.0",
    "Android_10", "Android_11", "Android_12", "Android_13",
    "Android_6.0.1", "Android_5.1.1", "Android_4.4.4", "Android_4.3",
    "Android_4.2.2", "Android_4.1.2",
]
"""可选的 Android 系统版本列表"""

# ── Android 协议版本号 ──────────────────────────────────────
ANDROID_APP_VERSION = "61"
ANDROID_X_APP_VERSION = "2.4.0"
ANDROID_DEVICE_BRAND = "Xiaomi"

# ── Web 协议 User-Agent ─────────────────────────────────────
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
)
WEB_APP_VERSION = "3"


# ─── 事件类型 ────────────────────────────────────────────────
@dataclass
class Pan123EventType:
    DOWNLOAD_START_FILE = "download_start_file"
    DOWNLOAD_START_DIRECTORY = "download_start_directory"
    DOWNLOAD_PROGRESS: str = "download_progress"
    UPLOAD_PROGRESS: str = "upload_progress"


# ════════════════════════════════════════════════════════════════
#  工具函数
# ════════════════════════════════════════════════════════════════

def make_result(code: int = CODE_OK, message: str = "ok", data: Any = None) -> Dict[str, Any]:
    """构造统一返回结构。

    Args:
        code:    状态码，0 表示成功，小于 0 表示失败，大于 0 表示成功但有警告信息
        message: 人类可读的结果描述。
        data:    业务数据，失败时通常为 None。

    Returns:
        {"code": int, "message": str, "data": Any}
    """
    return {"code": code, "message": message, "data": data}


def format_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小字符串。

    Args:
        size_bytes: 文件大小（字节）。

    Returns:
        格式化后的字符串，例如 "1.23 GB"、"456.78 MB"、"789 KB"、"12 B"。
    """
    for unit, threshold in [("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]:
        if size_bytes >= threshold:
            return f"{size_bytes / threshold:.2f} {unit}"
    return f"{size_bytes} B"


def calc_file_md5(file_path: str) -> str:
    """计算文件的 MD5 哈希值。

    Args:
        file_path: 文件在本地的绝对或相对路径。

    Returns:
        32 位小写十六进制 MD5 字符串。

    Raises:
        IOError: 文件读取失败时抛出。
    """
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(MD5_READ_CHUNK_SIZE):
            md5.update(chunk)
    return md5.hexdigest()


# ════════════════════════════════════════════════════════════════
#  进度回调类型别名
# ════════════════════════════════════════════════════════════════

ProgressCallback = Optional[Callable[..., None]]
"""进度回调类型。

下载回调签名: (downloaded_bytes: int, total_bytes: int, speed_bps: float) -> None
上传回调签名: (uploaded_bytes: int, total_bytes: int) -> None
"""


# ════════════════════════════════════════════════════════════════
#  内核类
# ════════════════════════════════════════════════════════════════

class Pan123Core:
    """123 网盘内核类。

    提供登录、目录浏览、上传、下载链接、分享、删除、回收站等纯逻辑接口。
    所有结果通过 ``make_result`` 统一返回，

    Attributes:
        user_name (str):        登录用户名 / 手机号。
        password (str):         登录密码。
        authorization (str):    Bearer Token，登录后自动填充。
        protocol (str):         请求协议，"android" 或 "web"。
        config_file (str):      配置文件路径。
        device_type (str):      Android 设备型号。 留空则随机选取 DEVICE_TYPES 中的一个。
        os_version (str):       Android 系统版本。 留空则随机选取 OS_VERSIONS 中的一个。
        cwd_id (int):           当前工作目录 FileId（0 = 根目录）。
        cwd_stack (List[int]):  目录 ID 导航栈。
        cwd_name_stack (List[str]): 目录名称导航栈。
        file_list (List[Dict]): 当前目录已加载的文件 / 文件夹列表。
        file_total (int):       当前目录文件总数（服务端返回）。
        all_loaded (bool):      当前目录是否已全部加载。
        cookies (Optional[Dict]): 登录后保存的 Cookie。
        headers (Dict[str, str]): 当前使用的请求头。

        nick_name (str): 当前用户昵称（获取用户信息时填充）。
        uid (int): 当前用户 UID（获取用户信息时填充）。

    :note:
        流程：初始化内核实例 -> 加载配置（可以初始化时提供）-> 初始化登录状态（self.init_login_state()） -> 进行目录浏览 / 上传 / 下载等操作 -> 需要时保存配置
        配置说明：如果传入了authorization，会先使用它尝试获取用户信息来验证登录状态，如果无效则根据提供的用户名和密码重新登录；如果未传入authorization，则直接根据用户名和密码登录。登录成功后会更新authorization属性。
    """

    # ── 协议常量 ──────────────────────────────────────────────
    PROTOCOL_ANDROID = "android"
    PROTOCOL_WEB = "web"

    def __init__(
            self,
            user_name: str = "",
            password: str = "",
            authorization: str = "",
            protocol: str = PROTOCOL_ANDROID,
            device_type: str = "",
            os_version: str = "",
            # config_file: str = "123pan_config.json",
    ):
        """初始化内核实例。

        Args:
            user_name:     登录用户名 / 手机号，可后续通过 load_config 或直接赋值设置。
            password:      登录密码。
            authorization: 已有的 Bearer Token，若提供则可跳过登录直接操作。
            protocol:      请求协议，"android"（默认）或 "web"。
            config_file:   配置文件路径，用于持久化账号和 Token。
            device_type:   指定 Android 设备型号，为空则随机选取。
            os_version:    指定 Android 系统版本，为空则随机选取。
                use_config_file: 是否在初始化时自动从配置文件加载账号信息和 Token，默认为 False，以避免内核直接依赖文件系统
        """
        # 账号信息
        self.user_name: str = user_name
        self.password: str = password
        self.authorization: str = authorization

        # 设备 / 协议
        self.protocol: str = protocol.lower()
        self.device_type: str = device_type or random.choice(DEVICE_TYPES)
        self.os_version: str = os_version or random.choice(OS_VERSIONS)
        self.login_uuid: str = uuid.uuid4().hex

        # 配置文件
        # self.config_file: str = config_file

        # 目录导航状态
        self.cwd_id: int = 0
        self.cwd_stack: List[int] = [0]
        self.cwd_name_stack: List[str] = []

        # 当前目录文件列表
        self.file_list: List[Dict] = []
        self.file_total: int = 0
        self.all_loaded: bool = False
        self._page: int = 0

        # Cookies
        self.cookies: Optional[Dict] = None

        # 请求头
        self.headers: Dict[str, str] = {}
        self._build_headers()

        # 运行参数
        self.nick_name = None
        self.uid = None

    # ════════════════════════════════════════════════════════════
    #  请求头构建
    # ════════════════════════════════════════════════════════════

    def _build_headers(self) -> None:
        """根据当前 protocol 构建请求头。

        会读取 self.protocol、self.authorization、self.login_uuid、
        self.os_version、self.device_type 等属性来组装 headers。
        """
        common = {
            "content-type": "application/json",
            "authorization": self.authorization,
            "LoginUuid": self.login_uuid,
        }

        if self.protocol == self.PROTOCOL_WEB:
            self.headers = {
                **common,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "App-Version": WEB_APP_VERSION,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Pragma": "no-cache",
                "Referer": f"{API_BASE_URL}/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": WEB_USER_AGENT,
                "platform": "web",
                "sec-ch-ua": "Microsoft",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "Windows",
            }
        else:
            self.headers = {
                **common,
                "user-agent": f"123pan/v{ANDROID_X_APP_VERSION}({self.os_version};{ANDROID_DEVICE_BRAND})",
                "accept-encoding": "gzip",
                "osversion": self.os_version,
                "platform": "android",
                "devicetype": self.device_type,
                "devicename": ANDROID_DEVICE_BRAND,
                "host": "www.123pan.com",
                "app-version": ANDROID_APP_VERSION,
                "x-app-version": ANDROID_X_APP_VERSION,
            }

    def _sync_authorization(self) -> None:
        """将 self.authorization 同步到 headers 中（兼容大小写 key）。"""
        for key in ("authorization", "Authorization"):
            if key in self.headers:
                self.headers[key] = self.authorization

    # ════════════════════════════════════════════════════════════
    #  配置持久化
    # ════════════════════════════════════════════════════════════

    def load_config(self, cfg: Dict) -> Dict[str, Any]:
        """从配置加载账号信息、Token 及协议设置。仅更新cfg中存在的字段，

        会自动重建 headers 并同步 authorization。

        Args:
            cfg: { userName: str, passWord: str, authorization: str, deviceType: str, osVersion: str, protocol: str }

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "配置加载成功", "data": {配置内容 dict}}
                失败: {"code": -1, "message": "错误描述", "data": None}
        """
        try:
            self.user_name = cfg.get("userName", self.user_name)
            self.password = cfg.get("passWord", self.password)
            self.authorization = cfg.get("authorization", self.authorization)
            self.device_type = cfg.get("deviceType", self.device_type)
            self.os_version = cfg.get("osVersion", self.os_version)
            self.protocol = cfg.get("protocol", self.protocol).lower()
            self._build_headers()
            self._sync_authorization()
            return make_result(CODE_OK, "配置加载成功", cfg)
        except Exception as e:
            return make_result(-1, f"加载配置失败: {e}")

    def get_current_config(self) -> Dict[str, Any]:
        """获取当前账号信息、Token 及协议设置的字典表示。

        Returns:
            当前配置的字典，例如::

                {
                    "userName": str,
                    "passWord": str,
                    "authorization": str,
                    "deviceType": str,
                    "osVersion": str,
                    "protocol": str,
                }
        """
        return {
            "userName": self.user_name,
            "passWord": self.password,
            "authorization": self.authorization,
            "deviceType": self.device_type,
            "osVersion": self.os_version,
            "protocol": self.protocol,
        }

    # ════════════════════════════════════════════════════════════
    #  统一网络请求
    # ════════════════════════════════════════════════════════════

    def _request(
            self,
            method: str,
            path: str,
            *,
            json_data: Any = None,
            params: Any = None,
            timeout: int = TIMEOUT_DEFAULT,
    ) -> Dict[str, Any]:
        """发送 HTTP 请求并返回统一 Result。

        内部方法，自动拼接 API_BASE_URL（当 path 以 "/" 开头时），
        统一处理网络异常和 JSON 解析。

        Args:
            method:    HTTP 方法，"GET" / "POST" / "PUT" 等。
            path:      接口路径（以 "/" 开头则自动拼接 API_BASE_URL）或完整 URL。
            json_data: POST 请求体（将被 json 序列化）。
            params:    GET 查询参数字典。
            timeout:   请求超时秒数。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "ok", "data": {API 原始响应 JSON}}
                失败: {"code": <0, "message": "错误描述", "data": {API响应} | None}
        """
        url = f"{API_BASE_URL}{path}" if path.startswith("/") else path
        try:
            resp = requests.request(
                method, url,
                headers=self.headers,
                json=json_data,
                params=params,
                timeout=timeout,
            )
            data = resp.json()
            api_code = data.get("code", -1)
            # 123pan 登录成功/退出登录 成功返回 code 200，其余接口成功返回 0
            if api_code not in (CODE_OK, CODE_LOGIN_OK):
                return make_result(-3, data.get("message", "未知错误"), data)
            return make_result(CODE_OK, "ok", data)
        except requests.RequestException as e:
            return make_result(-1, f"请求失败: {e}")
        except json.JSONDecodeError:
            return make_result(-2, "响应 JSON 解析错误")

    # ════════════════════════════════════════════════════════════
    #  用户信息
    # ════════════════════════════════════════════════════════════

    def get_user_info(self) -> Dict[str, Any]:
        """获取当前登录用户的信息。

        Returns:
            Result:
                成功: {"code": 0, "message": "ok", "data": {用户信息 dict}}
                失败: {"code": <错误码>, "message": "错误描述", "data": None}
                data: {
                        "UID": ,
                        "Nickname": "",
                        "SpaceUsed": ,
                        "SpacePermanent": ,
                        "SpaceTemp": 0,
                        "FileCount": ,
                        "SpaceTempExpr": "",
                        "Mail": "",
                        "Passport": ,
                        "HeadImage": "",
                        ......
                }
        """
        user_info_res = self._request("GET", URL_USER_INFO)
        if user_info_res["code"] != CODE_OK:
            return make_result(user_info_res["code"], f"获取用户信息失败: {user_info_res['message']}")
        self.nick_name = user_info_res["data"]["data"].get("Nickname", "")
        self.uid = user_info_res["data"]["data"].get("UID", None)
        return make_result(CODE_OK, "ok", user_info_res["data"]["data"])

    # ════════════════════════════════════════════════════════════
    #  登录 / 登出
    # ════════════════════════════════════════════════════════════

    def login(self) -> Dict[str, Any]:
        """使用 user_name 和 password 登录，成功后自动更新 authorization 并保存配置。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "登录成功", "data": None}
                失败: {"code": -1, "message": "错误描述", "data": None}
        """
        if not self.user_name or not self.password:
            return make_result(-1, "用户名和密码不能为空")
        payload = {
            "type": 1,
            "passport": self.user_name,
            "password": self.password,
        }
        result = self._request("POST", URL_LOGIN, json_data=payload)
        if result["code"] != CODE_OK:
            return result
        token = result["data"]["data"]["token"]
        self.authorization = f"Bearer {token}"
        self._build_headers()
        self._sync_authorization()
        # 为避免内核依赖文件系统，登录成功后不自动保存配置到文件，由上层调用者决定何时保存。
        # self.save_config_to_file()
        return make_result(CODE_OK, "登录成功")

    def logout(self) -> Dict[str, Any]:
        """登出：清除 authorization 和 cookies，并保存配置。

        Returns:
            Result 字典::

                {"code": 0, "message": "已登出", "data": None}
        """
        self.authorization = ""
        self._sync_authorization()
        self.cookies = None
        # self.save_config_to_file()
        return make_result(CODE_OK, "已登出")

    def clear_account(self) -> Dict[str, Any]:
        """清除已登录账号：清除用户名、密码、authorization 和 cookies，不保存配置，但重建请求头。

        Returns:
            Result 字典::

                {"code": 0, "message": "账号信息已清除", "data": None}
        """
        self.user_name = ""
        self.password = ""
        self.authorization = ""
        self._sync_authorization()
        self.cookies = None
        # self.save_config_to_file()
        return make_result(CODE_OK, "账号信息已清除")

    def check_login(self) -> Dict[str, Any]:
        """检查当前登录状态是否有效。

        通过尝试获取根目录列表来验证 Token 是否有效。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "登录状态有效", "data": None}
                失败: {"code": -1, "message": "登录状态无效: 错误描述", "data": None}
        """
        result = self.get_user_info()
        if result["code"] == CODE_OK:
            return make_result(CODE_OK, "登录状态有效")
        return make_result(-1, f"登录状态无效: {result['message']}")

    def init_login_state(self) -> Dict[str, Any]:
        """根据提供的配置初始化登录状态。

        Args:
            cfg: 包含账号信息和 Token 的配置字典，结构同 get_current_config() 的返回值。

        Returns:
            Result:
                {"code": Num, "message": "..."}
        """
        # 直接获取目录列表来验证登录状态和 Token 是否有效
        is_valid = self.check_login()
        if is_valid["code"] == CODE_OK:
            return make_result(CODE_OK, "登录状态初始化成功")
        else:
            # 登录状态无效，重新登录
            if not self.user_name or not self.password:
                return make_result(-1, "登录状态无效，且用户名或密码缺失，无法重新登录")
            login_result = self.login()
            if login_result["code"] == CODE_OK:
                return make_result(CODE_OK, "登录状态无效，重新登录成功")
            else:
                return make_result(-2, f"登录状态无效，重新登录失败: {login_result['message']}")

    # ════════════════════════════════════════════════════════════
    #  目录浏览
    # ════════════════════════════════════════════════════════════

    def get_folder_details(self, folder_id: int) -> Dict[str, Any]:
        """获取指定文件夹的详情信息。

        Args:
            folder_id: 目标文件夹的 FileId。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "ok", "data": {文件夹详情 dict}}
                失败: {"code": <错误码>, "message": "错误描述", "data": None}
        """
        # 要传递一个包含 folder_id 的列表，但接口只返回第一个文件夹的详情
        data = {"file_ids": [folder_id]}
        res = self._request("POST", URL_DETAILS, json_data=data)
        if res["code"] != CODE_OK:
            return make_result(-1, f"获取文件夹详情失败: {res['message']}", res["data"])
        details = res["data"]["data"]
        if not details:
            return make_result(-2, "文件夹详情数据为空", res["data"])
        return make_result(CODE_OK, "ok", details)


    def list_dir(
            self,
            parent_id: Optional[int] = None,
            page: int = 1,
            limit: int = FILE_LIST_PAGE_LIMIT,
    ) -> Dict[str, Any]:
        """获取指定目录的单页文件列表。

        Args:
            parent_id: 父目录 FileId，为 None 则使用当前工作目录 cwd_id。
            page:      页码，从 1 开始。
            limit:     单页最大条目数，默认 FILE_LIST_PAGE_LIMIT (100)。

        Returns:
            Result 字典::

                成功: {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "items": [文件信息 dict, ...],
                        "total": int  # 该目录下文件总数
                    }
                }
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        if parent_id is None:
            parent_id = self.cwd_id
        params = {
            "driveId": 0,
            "limit": limit,
            "next": 0,
            "orderBy": "file_id",
            "orderDirection": "desc",
            "parentFileId": str(parent_id),
            "trashed": False,
            "SearchData": "",
            "Page": str(page),
            "OnlyLookAbnormalFile": 0,
        }
        result = self._request("GET", URL_FILE_LIST, params=params, timeout=TIMEOUT_FILE_LIST)
        if result["code"] != CODE_OK:
            return result
        info = result["data"]["data"]
        return make_result(CODE_OK, "ok", {
            "items": info["InfoList"],
            "total": info["Total"],
        })

    def list_dir_all(
            self,
            parent_id: Optional[int] = None,
            limit: int = FILE_LIST_PAGE_LIMIT,
    ) -> Dict[str, Any]:
        """获取指定目录下的全部文件（自动翻页，含限频等待）。

        Args:
            parent_id: 父目录 FileId，为 None 则使用当前工作目录。
            limit:     单页最大条目数。

        Returns:
            Result 字典::

                成功: {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "items": [所有文件信息 dict, ...],
                        "total": int
                    }
                }
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        if parent_id is None:
            parent_id = self.cwd_id
        page = 1
        all_items: List[Dict] = []
        total = -1
        while total == -1 or len(all_items) < total:
            r = self.list_dir(parent_id, page=page, limit=limit)
            if r["code"] != CODE_OK:
                return r
            all_items.extend(r["data"]["items"])
            total = r["data"]["total"]
            page += 1
            # 限频：每 RATE_LIMIT_PAGES 页暂停 RATE_LIMIT_INTERVAL 秒
            if (page - 1) % RATE_LIMIT_PAGES == 0:
                time.sleep(RATE_LIMIT_INTERVAL)
        return make_result(CODE_OK, "ok", {"items": all_items, "total": total})

    def refresh(self) -> Dict[str, Any]:
        """刷新当前目录：清空 file_list 并重新加载第一页。

        Returns:
            与 load_more() 相同的 Result 字典。
        """
        self.file_list = []
        self.file_total = 0
        self.all_loaded = False
        self._page = 0
        return self.load_more()

    def load_more(self) -> Dict[str, Any]:
        """加载当前目录的下一页文件，追加到 file_list。

        Returns:
            Result 字典::

                成功: {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "items": [当前 file_list 全部内容],
                        "total": int,
                        "all_loaded": bool  # 是否已全部加载
                    }
                }
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        self._page += 1
        r = self.list_dir(page=self._page)
        if r["code"] != CODE_OK:
            return r
        self.file_list.extend(r["data"]["items"])
        self.file_total = r["data"]["total"]
        self.all_loaded = len(self.file_list) >= self.file_total
        return make_result(CODE_OK, "ok", {
            "items": self.file_list,
            "total": self.file_total,
            "all_loaded": self.all_loaded,
        })

    # ════════════════════════════════════════════════════════════
    #  目录导航
    # ════════════════════════════════════════════════════════════

    @property
    def cwd_path(self) -> str:
        """当前工作目录的完整路径字符串，例如 "/" 或 "/照片/2024"。"""
        return "/" + "/".join(self.cwd_name_stack) if self.cwd_name_stack else "/"

    def cd(self, folder_index: int) -> Dict[str, Any]:
        """进入 file_list 中指定下标的文件夹。

        Args:
            folder_index: file_list 中的 0-based 下标。

        Returns:
            Result 字典::

                成功: 等同于 refresh() 的返回（自动刷新新目录内容）。
                失败: {"code": -1, "message": "无效的文件编号" | "目标不是文件夹", "data": None}
        """
        if not (0 <= folder_index < len(self.file_list)):
            return make_result(-1, "无效的文件编号")
        item = self.file_list[folder_index]
        if item["Type"] != 1:
            return make_result(-1, "目标不是文件夹")
        self.cwd_id = item["FileId"]
        self.cwd_stack.append(self.cwd_id)
        self.cwd_name_stack.append(item["FileName"])
        return self.refresh()

    def cd_up(self) -> Dict[str, Any]:
        """返回上级目录。

        Returns:
            Result 字典::

                成功: 等同于 refresh() 的返回。
                失败: {"code": -1, "message": "已在根目录", "data": None}
        """
        if len(self.cwd_stack) <= 1:
            return make_result(-1, "已在根目录")
        self.cwd_stack.pop()
        self.cwd_id = self.cwd_stack[-1]
        self.cwd_name_stack.pop()
        return self.refresh()

    def cd_root(self) -> Dict[str, Any]:
        """返回根目录。

        Returns:
            等同于 refresh() 的返回。
        """
        self.cwd_id = 0
        self.cwd_stack = [0]
        self.cwd_name_stack = []
        return self.refresh()

    # ════════════════════════════════════════════════════════════
    #  创建目录
    # ════════════════════════════════════════════════════════════

    def mkdir(self, name: str) -> Dict[str, Any]:
        """在当前目录下创建子目录。

        Args:
            name: 新目录名称，不可为空。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "ok", "data": {API 响应}}
                失败: {"code": -1, "message": "...", "data": ...}
        """
        if not name:
            return make_result(-1, "目录名不能为空")
        payload = {
            "driveId": 0,
            "etag": "",
            "fileName": name,
            "parentFileId": self.cwd_id,
            "size": 0,
            "type": 1,
            "duplicate": 1,
            "NotReuse": True,
            "event": "newCreateFolder",
            "operateType": 1,
        }
        return self._request("POST", URL_MKDIR, json_data=payload)

    # ════════════════════════════════════════════════════════════
    #  删除 / 恢复
    # ════════════════════════════════════════════════════════════

    def trash(self, file_data: Any, delete: bool = True) -> Dict[str, Any]:
        """删除或恢复文件 / 文件夹。

        Args:
            file_data: 文件信息字典（需包含 "FileId" 等字段），
                       来自 file_list 中的条目或手动构造的 {"FileId": int}。
            delete:    True = 删除（移入回收站），False = 恢复（从回收站还原）。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "删除成功" | "恢复成功", "data": None}
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        action = "删除" if delete else "恢复"
        payload = {
            "driveId": 0,
            "fileTrashInfoList": file_data,
            "operation": delete,
        }
        r = self._request("POST", URL_FILE_TRASH, json_data=payload, timeout=TIMEOUT_TRASH)
        if r["code"] == CODE_OK:
            return make_result(CODE_OK, f"{action}成功")
        return make_result(r["code"], f"{action}失败: {r['message']}")

    def trash_by_index(self, index: int) -> Dict[str, Any]:
        """根据 file_list 的 0-based 下标删除文件。

        Args:
            index: file_list 中的 0-based 下标。

        Returns:
            与 trash() 相同的 Result 字典。
        """
        if not (0 <= index < len(self.file_list)):
            return make_result(-1, "无效的文件编号")
        return self.trash(self.file_list[index])

    # ════════════════════════════════════════════════════════════
    #  回收站
    # ════════════════════════════════════════════════════════════

    def list_recycle(self) -> Dict[str, Any]:
        """获取回收站中的文件列表。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "ok", "data": [文件信息 dict, ...]}
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        params = {
            "driveId": 0,
            "limit": FILE_LIST_PAGE_LIMIT,
            "next": 0,
            "orderBy": "fileId",
            "orderDirection": "desc",
            "parentFileId": 0,
            "trashed": True,
            "Page": 1,
        }
        r = self._request("GET", URL_FILE_LIST, params=params)
        if r["code"] != CODE_OK:
            return r
        return make_result(CODE_OK, "ok", r["data"]["data"]["InfoList"])

    def restore(self, file_id: int) -> Dict[str, Any]:
        """从回收站恢复指定文件。

        Args:
            file_id: 要恢复的文件 FileId。

        Returns:
            与 trash() 相同的 Result 字典。
        """
        return self.trash({"FileId": file_id}, delete=False)

    # ════════════════════════════════════════════════════════════
    #  分享
    # ════════════════════════════════════════════════════════════

    def share(
            self,
            file_ids: List[int],
            share_pwd: str = "",
            expiration: str = "2099-12-12T08:00:00+08:00",
    ) -> Dict[str, Any]:
        """创建分享链接。

        Args:
            file_ids:   要分享的 FileId 列表（注意是 FileId，不是 file_list 下标）。
            share_pwd:  提取码，留空表示无密码。
            expiration: 分享过期时间（ISO 8601 格式），默认 2099 年。

        Returns:
            Result 字典::

                成功: {
                    "code": 0,
                    "message": "分享创建成功",
                    "data": {
                        "share_url": "https://www.123pan.com/s/xxxxx",
                        "share_pwd": str
                    }
                }
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        if not file_ids:
            return make_result(-1, "未选择文件")
        payload = {
            "driveId": 0,
            "expiration": expiration,
            "fileIdList": ",".join(str(fid) for fid in file_ids),
            "shareName": "分享文件",
            "sharePwd": share_pwd,
            "event": "shareCreate",
        }
        r = self._request("POST", URL_SHARE_CREATE, json_data=payload)
        if r["code"] != CODE_OK:
            return r
        key = r["data"]["data"]["ShareKey"]
        share_url = SHARE_URL_TEMPLATE.format(base=API_BASE_URL, key=key)
        return make_result(CODE_OK, "分享创建成功", {
            "share_url": share_url,
            "share_pwd": share_pwd,
        })

    def share_by_indices(self, indices: List[int], share_pwd: str = "") -> Dict[str, Any]:
        """根据 file_list 的 0-based 下标列表创建分享。

        Args:
            indices:   file_list 中的 0-based 下标列表。
            share_pwd: 提取码，留空表示无密码。

        Returns:
            与 share() 相同的 Result 字典。
        """
        for i in indices:
            if not (0 <= i < len(self.file_list)):
                return make_result(-1, f"无效的文件编号: {i + 1}")
        file_ids = [self.file_list[i]["FileId"] for i in indices]
        return self.share(file_ids, share_pwd)

    # ════════════════════════════════════════════════════════════
    #  下载
    # ════════════════════════════════════════════════════════════

    def get_download_url(self, index: int) -> Dict[str, Any]:
        """获取 file_list 中指定下标文件的真实下载直链。

        会自动处理 302 重定向和 HTML 中的 href 提取。

        Args:
            index: file_list 中的 0-based 下标。

        Returns:
            Result 字典::
                来自 self.get_item_download_url() 的结果：
                    成功: {"code": 0, "message": "ok", "data": {"url": "https://..."}}
                    失败: {"code": -1, "message": "...", "data": None}
        """
        if not (0 <= index < len(self.file_list)):
            return make_result(-1, "无效的文件编号")
        item = self.file_list[index]
        return self.get_item_download_url(item)

    def get_item_download_url(self, item: Dict) -> Dict[str, Any]:
        """获取单个文件或文件夹的真实下载链接。
        Args:
            item: 文件信息字典，文件夹（Type = 1）需包含 "FileId"
                    文件（Type = 0）需包含 "FileId", "Etag", "S3KeyFlag", "Type", "FileName", "Size"。可以来自 file_list 中的条目或手动构造的 dict。

        Returns:
            Result 字典::
                成功: {"code": 0, "message": "ok", "data": {"url": "https://..."}}
                失败: {"code": -1, "message": "...", "data": None}
        """
        # 文件夹走批量下载接口，文件走单文件接口
        if item["Type"] == 1:
            api_path = URL_BATCH_DOWNLOAD
            payload = {"fileIdList": [{"fileId": int(item["FileId"])}]}
        else:
            api_path = URL_DOWNLOAD_INFO
            payload = {
                "driveId": 0,
                "etag": item["Etag"],
                "fileId": item["FileId"],
                "s3keyFlag": item["S3KeyFlag"],
                "type": item["Type"],
                "fileName": item["FileName"],
                "size": item["Size"],
            }

        r = self._request("POST", api_path, json_data=payload)
        if r["code"] != CODE_OK:
            return r

        download_url = r["data"]["data"]["DownloadUrl"]

        # 跟随重定向获取真实下载链接
        try:
            # 直接请求会报错证书错误
            # 此服务器无法证明它是 user-app-free-download-cdn.123295.com；它的安全证书来自 *.123pan.cn。这可能是由错误配置或者有攻击者截获你的连接而导致的。
            # 关闭 SSL 验证以避免下载链接获取失败
            # 仅在获取下载链接时关闭验证
            requests.packages.urllib3.disable_warnings()
            resp = requests.get(download_url, allow_redirects=False, timeout=TIMEOUT_DEFAULT, verify=False)
            if resp.status_code == 302:
                location = resp.headers.get("Location")
                if location:
                    return make_result(CODE_OK, "ok", {"url": location})
            # 尝试从 HTML 响应中提取 href
            match = re.search(r"href='(https?://[^']+)'", resp.text)
            if match:
                return make_result(CODE_OK, "ok", {"url": match.group(1)})
            return make_result(-1, "无法解析真实下载链接")
        except requests.RequestException as e:
            return make_result(-1, f"获取真实下载链接失败: {e}")

    # 文件交互，方法已移至 Pan123Tool
    # def download_file(
    #         self,
    #         index: int,
    #         save_dir: str = "download",
    #         on_progress: ProgressCallback = None,
    #         overwrite: bool = False,
    #         skip_existing: bool = False,
    # ) -> Dict[str, Any]:
    #     """下载 file_list 中指定下标的文件到本地。
    #
    #     如果目标是文件夹，则自动递归调用 download_directory()。
    #     下载过程中使用 ".123pan" 临时文件，完成后重命名。
    #
    #     Args:
    #         index:         file_list 中的 0-based 下标。
    #         save_dir:      本地保存目录路径，不存在会自动创建。
    #         on_progress:   下载进度回调函数，签名:
    #                        (downloaded_bytes: int, total_bytes: int, speed_bps: float) -> None
    #         overwrite:     True = 覆盖已存在的同名文件。
    #         skip_existing: True = 跳过已存在的同名文件。
    #
    #     Returns:
    #         Result 字典::
    #
    #             成功: {"code": 0, "message": "下载完成", "data": {"path": "本地文件路径"}}
    #             冲突: {"code": 1, "message": "文件已存在", "data": {"path": "...", "conflict": True}}
    #             跳过: {"code": 0, "message": "文件已存在，已跳过", "data": {"path": "..."}}
    #             失败: {"code": -1, "message": "...", "data": None}
    #     """
    #     if not (0 <= index < len(self.file_list)):
    #         return make_result(-1, "无效的文件编号")
    #     item = self.file_list[index]
    #
    #     # 文件夹递归下载
    #     if item["Type"] == 1:
    #         return self.download_directory(item, save_dir, on_progress, overwrite, skip_existing)
    #
    #     # 获取下载链接
    #     r = self.get_download_url(index)
    #     if r["code"] != CODE_OK:
    #         return r
    #     url = r["data"]["url"]
    #
    #     file_name = item["FileName"]
    #     os.makedirs(save_dir, exist_ok=True)
    #     full_path = os.path.join(save_dir, file_name)
    #
    #     # 文件冲突处理
    #     if os.path.exists(full_path):
    #         if skip_existing:
    #             return make_result(CODE_OK, "文件已存在，已跳过", {"path": full_path})
    #         if not overwrite:
    #             return make_result(CODE_CONFLICT, "文件已存在", {"path": full_path, "conflict": True})
    #         os.remove(full_path)
    #
    #     # 使用临时文件下载
    #     temp_path = full_path + ".123pan"
    #     try:
    #         resp = requests.get(url, stream=True, timeout=TIMEOUT_DOWNLOAD)
    #         total = int(resp.headers.get("Content-Length", 0))
    #         downloaded = 0
    #         start = time.time()
    #         with open(temp_path, "wb") as f:
    #             for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
    #                 if chunk:
    #                     f.write(chunk)
    #                     downloaded += len(chunk)
    #                     if on_progress:
    #                         elapsed = time.time() - start
    #                         speed = downloaded / elapsed if elapsed > 0 else 0.0
    #                         # on_progress(
    #
    #                         )
    #         os.rename(temp_path, full_path)
    #         return make_result(CODE_OK, "下载完成", {"path": full_path})
    #     except Exception as e:
    #         if os.path.exists(temp_path):
    #             os.remove(temp_path)
    #         return make_result(-1, f"下载失败: {e}")

    # 文件交互，方法已移至 Pan123Tool，Pan123Core 仅保留获取下载链接的功能，目录下载逻辑也移至工具类以避免内核依赖文件系统。
    # def download_directory(
    #         self,
    #         directory: Dict,
    #         save_dir: str = "download",
    #         on_progress: ProgressCallback = None,
    #         overwrite: bool = False,
    #         skip_existing: bool = False,
    # ) -> Dict[str, Any]:
    #     """递归下载整个目录到本地。
    #
    #     Args:
    #         directory:     文件夹信息字典（需包含 "FileId"、"FileName"、"Type" 字段）。
    #         save_dir:      本地保存根目录路径。
    #         on_progress:   下载进度回调函数（同 download_file）。
    #         overwrite:     True = 覆盖已存在文件。
    #         skip_existing: True = 跳过已存在文件。
    #
    #     Returns:
    #         Result 字典::
    #
    #             成功: {"code": 0, "message": "文件夹下载完成", "data": {"path": "本地目录路径"}}
    #             部分失败: {"code": -1, "message": "部分文件下载失败: ...", "data": {"path": "..."}}
    #             失败: {"code": <错误码>, "message": "...", "data": None}
    #     """
    #     if directory["Type"] != 1:
    #         return make_result(-1, "不是文件夹")
    #
    #     target_dir = os.path.join(save_dir, directory["FileName"])
    #     os.makedirs(target_dir, exist_ok=True)
    #
    #     r = self.list_dir_all(parent_id=directory["FileId"])
    #     if r["code"] != CODE_OK:
    #         return r
    #
    #     items = r["data"]["items"]
    #     if not items:
    #         return make_result(CODE_OK, "文件夹为空", {"path": target_dir})
    #
    #     errors: List[str] = []
    #     for item in items:
    #         if item["Type"] == 1:
    #             sub = self.download_directory(item, target_dir, on_progress, overwrite, skip_existing)
    #         else:
    #             # 临时替换 file_list 以复用 download_file 逻辑
    #             orig_list = self.file_list
    #             self.file_list = [item]
    #             sub = self.download_file(0, target_dir, on_progress, overwrite, skip_existing)
    #             self.file_list = orig_list
    #         if sub["code"] != CODE_OK:
    #             errors.append(f"{item['FileName']}: {sub['message']}")
    #
    #     if errors:
    #         return make_result(-1, f"部分文件下载失败: {'; '.join(errors)}", {"path": target_dir})
    #     return make_result(CODE_OK, "文件夹下载完成", {"path": target_dir})

    # ════════════════════════════════════════════════════════════
    #  上传
    # ════════════════════════════════════════════════════════════

    def upload_file(
            self,
            file_path: str,
            duplicate: int = 0,
            on_progress: ProgressCallback = None,
    ) -> Dict[str, Any]:
        """上传本地文件到当前目录。

        支持秒传（MD5 复用）和分块上传。

        Args:
            file_path:   本地文件路径。
            duplicate:   同名文件处理策略:
                         0 = 报冲突（返回 code=5060），
                         1 = 覆盖，
                         2 = 保留两者。
            on_progress: 上传进度回调函数，签名:
                         (uploaded_bytes: int, total_bytes: int) -> None

        Returns:
            Result 字典::

                秒传成功:   {"code": 0, "message": "秒传成功（MD5 复用）", "data": {"reuse": True}}
                上传成功:   {"code": 0, "message": "上传完成", "data": {"reuse": False}}
                同名冲突:   {"code": 5060, "message": "同名文件已存在，请指定 duplicate 参数", "data": None}
                失败:       {"code": -1, "message": "...", "data": None}
        """
        file_path = file_path.strip().replace('"', "").replace("\\", "/")
        if not os.path.exists(file_path):
            return make_result(-1, "文件不存在")
        if os.path.isdir(file_path):
            return make_result(-1, "暂不支持文件夹上传")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        try:
            md5 = calc_file_md5(file_path)
        except IOError as e:
            return make_result(-1, f"读取文件失败: {e}")

        payload = {
            "driveId": 0,
            "etag": md5,
            "fileName": file_name,
            "parentFileId": self.cwd_id,
            "size": file_size,
            "type": 0,
            "duplicate": duplicate,
        }
        r = self._request("POST", URL_UPLOAD_REQUEST, json_data=payload)
        if r["code"] != CODE_OK:
            # 特殊处理同名冲突
            if r.get("data") and r["data"].get("code") == CODE_DUPLICATE_FILE:
                return make_result(CODE_DUPLICATE_FILE, "同名文件已存在，请指定 duplicate 参数")
            return r

        resp_data = r["data"]["data"]
        if resp_data.get("Reuse", False):
            return make_result(CODE_OK, "秒传成功（MD5 复用）", {"reuse": True})

        # 需要分块上传
        return self._upload_chunks(
            file_path,
            bucket=resp_data["Bucket"],
            storage_node=resp_data["StorageNode"],
            key=resp_data["Key"],
            upload_id=resp_data["UploadId"],
            file_id=resp_data["FileId"],
            on_progress=on_progress,
        )

    def _upload_chunks(
            self,
            file_path: str,
            *,
            bucket: str,
            storage_node: str,
            key: str,
            upload_id: str,
            file_id: str,
            on_progress: ProgressCallback = None,
    ) -> Dict[str, Any]:
        """执行 S3 分块上传流程（内部方法）。

        流程: 循环读取文件分块 → 获取预签名 URL → PUT 上传 →
              合并分块 → 确认上传完成。

        Args:
            file_path:    本地文件路径。
            bucket:       S3 存储桶名。
            storage_node: 存储节点。
            key:          S3 对象 Key。
            upload_id:    S3 分块上传 ID。
            file_id:      123pan 文件 ID。
            on_progress:  上传进度回调，签名:
                          (uploaded_bytes: int, total_bytes: int) -> None

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "上传完成", "data": {"reuse": False}}
                失败: {"code": -1, "message": "...", "data": None}
        """
        total_size = os.path.getsize(file_path)
        uploaded = 0
        part_number = 1

        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(UPLOAD_CHUNK_SIZE)
                    if not chunk:
                        break

                    # 步骤 1: 获取分块预签名上传 URL
                    url_payload = {
                        "bucket": bucket,
                        "key": key,
                        "partNumberEnd": part_number + 1,
                        "partNumberStart": part_number,
                        "uploadId": upload_id,
                        "StorageNode": storage_node,
                    }
                    r = self._request("POST", URL_UPLOAD_PARTS, json_data=url_payload)
                    if r["code"] != CODE_OK:
                        return make_result(-1, f"获取上传 URL 失败: {r['message']}")
                    upload_url = r["data"]["data"]["presignedUrls"][str(part_number)]

                    # 步骤 2: PUT 上传分块数据
                    try:
                        resp = requests.put(upload_url, data=chunk, timeout=TIMEOUT_UPLOAD_CHUNK)
                        if resp.status_code not in (200, 201):
                            return make_result(-1, f"分块上传失败，HTTP {resp.status_code}")
                    except requests.RequestException as e:
                        return make_result(-1, f"分块上传请求失败: {e}")

                    uploaded += len(chunk)
                    if on_progress:
                        on_progress({
                            "type": Pan123EventType.UPLOAD_PROGRESS,
                            "uploaded": uploaded,
                            "total": total_size,
                            "percent": uploaded / total_size * 100,
                        })
                    part_number += 1

            # 步骤 3: 通知服务端合并所有分块
            merge_payload = {
                "bucket": bucket,
                "key": key,
                "uploadId": upload_id,
                "StorageNode": storage_node,
            }
            self._request("POST", URL_UPLOAD_COMPLETE_S3, json_data=merge_payload, timeout=TIMEOUT_TRASH)
            time.sleep(S3_MERGE_DELAY)

            # 步骤 4: 确认上传完成
            r = self._request("POST", URL_UPLOAD_COMPLETE, json_data={"fileId": file_id})
            if r["code"] == CODE_OK:
                return make_result(CODE_OK, "上传完成", {"reuse": False})
            return make_result(-1, f"上传确认失败: {r['message']}")

        except IOError as e:
            return make_result(-1, f"读取文件失败: {e}")

    # ════════════════════════════════════════════════════════════
    #  协议切换
    # ════════════════════════════════════════════════════════════

    def set_protocol(self, protocol: str) -> Dict[str, Any]:
        """切换请求协议并保存配置。

        切换后会重建 headers 并同步 authorization。

        Args:
            protocol: 目标协议，"android" 或 "web"（不区分大小写）。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "已切换到 xxx 协议", "data": None}
                失败: {"code": -1, "message": "不支持的协议...", "data": None}
        """
        protocol = protocol.lower()
        if protocol not in (self.PROTOCOL_ANDROID, self.PROTOCOL_WEB):
            return make_result(-1, "不支持的协议，仅支持 'android' 或 'web'")
        self.protocol = protocol
        self._build_headers()
        self._sync_authorization()
        # self.save_config_to_file()
        return make_result(CODE_OK, f"已切换到 {protocol} 协议")


class Pan123Tool:
    """123pan 工具类，提供更高层次的文件交互方法，依赖 Pan123Core 实现具体 API 调用。

    Args:
        core: Pan123Core 实例，负责 API 请求和状态管理。
        config_file: 配置文件路径，默认为 "123pan_config.json"，用于保存和加载账号信息、Token 及协议设置。

    :note
        Pan123Tool 主要负责文件下载、上传、目录操作等依赖文件系统的功能，而 Pan123Core 负责 API 请求、认证和状态管理。
    """

    def __init__(self, core: Pan123Core, config_file: str = "123pan_config.json"):
        self.core = core
        self.config_file = config_file

    def load_config_from_file(self) -> Dict[str, Any]:
        """从配置文件加载账号信息、Token 及协议设置。

        会自动重建 headers 并同步 authorization。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "配置加载成功", "data": {配置内容 dict}}
                失败: {"code": -1, "message": "错误描述", "data": None}
        """
        if not os.path.exists(self.config_file):
            return make_result(-1, "配置文件不存在")
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return self.core.load_config(cfg)
        except Exception as e:
            return make_result(-1, f"加载配置失败: {e}")

    def save_config_to_file(self) -> Dict[str, Any]:
        """将当前账号信息、Token 及协议设置保存到配置文件。

        Returns:
            Result 字典::

                成功: {"code": 0, "message": "配置已保存", "data": {配置内容 dict}}
                失败: {"code": -1, "message": "错误描述", "data": None}
        """
        cfg = {
            "userName": self.core.user_name,
            "passWord": self.core.password,
            "authorization": self.core.authorization,
            "deviceType": self.core.device_type,
            "osVersion": self.core.os_version,
            "protocol": self.core.protocol,
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            return make_result(CODE_OK, "配置已保存", cfg)
        except Exception as e:
            return make_result(-1, f"保存配置失败: {e}")

    def download_file(
            self,
            index: int,
            save_dir: str = "download",
            on_progress: ProgressCallback = None,
            overwrite: bool = False,
            skip_existing: bool = False,
    ) -> Dict[str, Any]:
        """下载 file_list 中指定下标的文件到本地。

        如果目标是文件夹，则自动递归调用 download_directory()。
        下载过程中使用 ".123pan" 临时文件，完成后重命名。

        Args:
            index:         file_list 中的 0-based 下标。
            save_dir:      本地保存目录路径，不存在会自动创建。
            on_progress:   下载进度回调函数，签名:
                           (downloaded_bytes: int, total_bytes: int, speed_bps: float) -> None
            overwrite:     True = 覆盖已存在的同名文件。
            skip_existing: True = 跳过已存在的同名文件。

        Returns:
            Result 字典:: 来自 download_url() 或 download_directory() 的结果：
                成功: {"code": 0, "message": "下载完成", "data": {"path": "本地文件路径"}}
                冲突: {"code": 1, "message": "文件已存在", "data": {"path": "...", "conflict": True}}
                跳过: {"code": 0, "message": "文件已存在，已跳过", "data": {"path": "..."}}
                失败: {"code": -1, "message": "...", "data": None}
        """
        if not (0 <= index < len(self.core.file_list)):
            return make_result(-1, "无效的文件编号")
        item = self.core.file_list[index]
        return self.download_item(item, save_dir, on_progress, overwrite, skip_existing)

    def download_item(
            self,
            item: Dict,
            save_dir: str = "download",
            on_progress: ProgressCallback = None,
            overwrite: bool = False,
            skip_existing: bool = False,
    ):
        """下载单个文件或文件夹项，自动区分类型并处理。
        Args:
            item:          文件信息字典，文件夹（Type = 1）需包含 "FileId"
                            文件（Type = 0）需包含 "FileId", "Etag", "S3KeyFlag", "Type", "FileName", "Size"。
            save_dir:      本地保存目录路径，不存在会自动创建。
            on_progress:   下载进度回调函数，签名:
                           (downloaded_bytes: int, total_bytes: int, speed_bps: float) -> None
            overwrite:     True = 覆盖已存在的同名文件。
            skip_existing: True = 跳过已存在的同名文件。
        Returns:
            Result 字典:: 来自 download_url() 或 download_directory() 的结果：
                成功: {"code": 0, "message": "下载完成", "data": {"path": "本地文件路径"}}
                冲突: {"code": 1, "message": "文件已存在", "data": {"path": "...", "conflict": True}}
                跳过: {"code": 0, "message": "文件已存在，已跳过", "data": {"path": "..."}}
                失败: {"code": -1, "message": "...", "data": None}
        """
        # 文件夹递归下载
        if item["Type"] == 1:
            return self.download_directory(item, save_dir, on_progress, overwrite, skip_existing)

        # 获取下载链接
        r = self.core.get_item_download_url(item)
        if r["code"] != CODE_OK:
            return r
        url = r["data"]["url"]
        file_name = item["FileName"]
        return self.download_url(url, file_name, save_dir, on_progress, overwrite, skip_existing)

    def download_url(
            self,
            url: str,
            file_name: str,
            save_dir: str = "download",
            on_progress: ProgressCallback = None,
            overwrite: bool = False,
            skip_existing: bool = False,
    ) -> Dict[str, Any]:
        """根据下载链接下载文件到本地，支持进度回调和冲突处理。

        Args:
            url:           真实下载链接。
            file_name:     保存的文件名（不含路径）。
            save_dir:      本地保存目录路径，不存在会自动创建。
            on_progress:   下载进度回调函数，签名:
                           (downloaded_bytes: int, total_bytes: int, speed_bps: float) -> None
            overwrite:     True = 覆盖已存在的同名文件。
            skip_existing: True = 跳过已存在的同名文件。

        Returns:
            Result 字典::
                成功: {"code": 0, "message": "下载完成", "data": {"path": "本地文件路径"}}
                冲突: {"code": 1, "message": "文件已存在", "data": {"path": "...", "conflict": True}}
                跳过: {"code": 0, "message": "文件已存在，已跳过", "data": {"path": "..."}}
                失败: {"code": -1, "message": "...", "data": None}
        """

        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, file_name)

        # 文件冲突处理
        if os.path.exists(full_path):
            if skip_existing:
                return make_result(CODE_OK, "文件已存在，已跳过", {"path": full_path})
            if not overwrite:
                return make_result(CODE_CONFLICT, "文件已存在", {"path": full_path, "conflict": True})
            os.remove(full_path)

        # TODO: 可以考虑断点续传
        # 使用临时文件下载
        temp_path = full_path + ".123pan"
        try:
            resp = requests.get(url, stream=True, timeout=TIMEOUT_DOWNLOAD)
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            start = time.time()
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if on_progress:
                            elapsed = time.time() - start
                            speed = downloaded / elapsed if elapsed > 0 else 0.0
                            on_progress({
                                "type": Pan123EventType.DOWNLOAD_PROGRESS,
                                "downloaded": downloaded,
                                "total": total,
                                "speed": speed,
                            })
            os.rename(temp_path, full_path)
            return make_result(CODE_OK, "下载完成", {"path": full_path})
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return make_result(-1, f"下载失败: {e}")

    def download_directory(
            self,
            directory: Dict,
            save_dir: str = "download",
            on_progress: ProgressCallback = None,
            overwrite: bool = False,
            skip_existing: bool = False,
    ) -> Dict[str, Any]:
        """递归下载整个目录到本地。

        Args:
            directory:     文件夹信息字典（需包含 "FileId"、"FileName"、"Type" 字段）。
            save_dir:      本地保存根目录路径。
            on_progress:   下载进度回调函数（同 download_file）。
            overwrite:     True = 覆盖已存在文件。
            skip_existing: True = 跳过已存在文件。

        Returns:
                成功: {"code": 0, "message": "文件夹下载完成", "data": {"path": "本地目录路径"}}
                部分失败: {"code": -1, "message": "部分文件下载失败: ...", "data": {"path": "..."}}
                失败: {"code": <错误码>, "message": "...", "data": None}
        """
        if directory["Type"] != 1:
            return make_result(-1, "不是文件夹")

        target_dir = os.path.join(save_dir, directory["FileName"])
        os.makedirs(target_dir, exist_ok=True)

        r = self.core.list_dir_all(parent_id=directory["FileId"])
        if r["code"] != CODE_OK:
            return r

        items = r["data"]["items"]
        if not items:
            return make_result(CODE_OK, "文件夹为空", {"path": target_dir})

        errors: List[str] = []
        for item in items:
            if item["Type"] == 1:
                # 递归下载子目录
                if on_progress:
                    on_progress({
                        "type": Pan123EventType.DOWNLOAD_START_DIRECTORY,
                        "file_name": item["FileName"],
                        "dir_name": item["FileName"],
                        "message": f"正在下载目录: {item['FileName']}",
                    })
                sub = self.download_directory(item, target_dir, on_progress, overwrite, skip_existing)
            else:
                if on_progress:
                    on_progress({
                        "type": Pan123EventType.DOWNLOAD_START_FILE,
                        "file_name": item["FileName"],
                        "file_size": item["Size"],
                        "message": f"正在下载文件: {item['FileName']}",
                    })
                sub = self.download_item(item, target_dir, on_progress, overwrite, skip_existing)
            if sub["code"] != CODE_OK:
                errors.append(f"{item['FileName']}: {sub['message']}")

        if errors:
            return make_result(-1, f"部分文件下载失败: {'; '.join(errors)}", {"path": target_dir})
        return make_result(CODE_OK, "文件夹下载完成", {"path": target_dir})
