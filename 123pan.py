import hashlib
import json
import os
import random
import re
import time
import uuid
import requests
from typing import List, Dict, Tuple, Union, Optional

class Pan123:
    DEVICE_TYPES = [
        "24075RP89G", "24076RP19G", "24076RP19I", "M1805E10A", "M2004J11G", "M2012K11AG", "M2104K10I", "22021211RG",
        "22021211RI", "21121210G", "23049PCD8G", "23049PCD8I", "23013PC75G", "24069PC21G", "24069PC21I",
        "23113RKC6G", "M1912G7BI", "M2007J20CI", "M2007J20CG", "M2007J20CT", "M2102J20SG", "M2102J20SI",
        "21061110AG", "2201116PG", "2201116PI", "22041216G", "22041216UG", "22111317PG", "22111317PI", "22101320G",
        "22101320I", "23122PCD1G", "23122PCD1I", "2311DRK48G", "2311DRK48I", "2312FRAFDI", "M2004J19PI",
    ]
    
    OS_VERSIONS = [
        "Android_7.1.2", "Android_8.0.0", "Android_8.1.0", "Android_9.0", "Android_10", "Android_11", "Android_12",
        "Android_13", "Android_6.0.1", "Android_5.1.1", "Android_4.4.4", "Android_4.3", "Android_4.2.2",
        "Android_4.1.2",
    ]

    def __init__(
        self,
        readfile: bool = True,
        user_name: str = "",
        pass_word: str = "",
        authorization: str = "",
        input_pwd: bool = True,
        config_file: str = "123pan.txt",
        protocol: str = "android",  # 协议，默认为 android
    ):
        self.config_file = config_file
        self.protocol = protocol.lower()  # 'android' 或 'web'
        self.devicetype = random.choice(self.DEVICE_TYPES)
        self.osversion = random.choice(self.OS_VERSIONS)
        self.download_mode = 1
        self.cookies = None
        self.user_name = user_name
        self.password = pass_word
        self.authorization = authorization
        self.parent_file_id = 0
        self.parent_file_list = [0]
        self.parent_file_name_list = []
        self.all_file = False
        self.file_page = 0
        self.file_list = []
        self.dir_list = []
        self.name_dict = {}
        self.list = []
        self.total = 0
        
        self._init_headers()  # 根据 protocol 初始化 headers
        
        load_code = 0
        if readfile:
            load_code = self._load_config()
        if not load_code:
            if not (user_name and pass_word) and input_pwd:
                self.user_name = input("请输入用户名: ")
                self.password = input("请输入密码: ")
            elif not (user_name and pass_word):
                raise ValueError("用户名和密码不能为空")
        
        # 尝试获取目录，如果失败则登录
        if self.get_dir()[0] != 0:
            self.login()
            self.get_dir()

    def _init_headers(self):
        """初始化请求头，根据协议（android/web）选择不同 headers"""
        android_headers = {
            "user-agent": f"123pan/v2.4.0({self.osversion};Xiaomi)",
            "authorization": self.authorization,
            "accept-encoding": "gzip",
            "content-type": "application/json",
            "osversion": self.osversion,
            "loginuuid": uuid.uuid4().hex,
            "platform": "android",
            "devicetype": self.devicetype,
            "devicename": "Xiaomi",
            "host": "www.123pan.com",
            "app-version": "61",
            "x-app-version": "2.4.0"
        }

        # Web 协议头，来源于 web.py 的 header_logined / header_only_usage（适配为字典）
        web_headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "App-Version": "3",
            # 同时设置大小写两种 Authorization 以兼容不同接口要求
            # "Authorization": self.authorization,
            "authorization": self.authorization,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "LoginUuid": uuid.uuid4().hex,
            "Pragma": "no-cache",
            "Referer": "https://www.123pan.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "platform": "web",
            "sec-ch-ua": "Microsoft",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "content-type": "application/json",
        }

        if getattr(self, "protocol", "android").lower() == "web":
            self.headers = web_headers
        else:
            self.headers = android_headers

    def _load_config(self):
        """从配置文件加载账号信息及 protocol"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.user_name = config.get("userName", self.user_name)
                    self.password = config.get("passWord", self.password)
                    self.authorization = config.get("authorization", self.authorization)
                    self.devicetype = config.get("deviceType", self.devicetype)
                    self.osversion = config.get("osVersion", self.osversion)
                    # 新增 protocol 支持
                    self.protocol = config.get("protocol", getattr(self, "protocol", "android")).lower()
                    # 重新初始化 headers（确保 authorization 和 protocol 生效）
                    self._init_headers()
                    # 确保 headers 中 authorization 同步
                    if "authorization" in self.headers:
                        self.headers["authorization"] = self.authorization
                    if "Authorization" in self.headers:
                        self.headers["Authorization"] = self.authorization
                    print("配置加载成功")
                    return 1
            else:
                print("配置文件不存在，将使用传入参数")
                return 0
        except Exception as e:
            print(f"加载配置失败: {e}")
            return 0

    def _save_config(self):
        """保存账号信息到配置文件（包含 protocol）"""
        config = {
            "userName": self.user_name,
            "passWord": self.password,
            "authorization": self.authorization,
            "deviceType": self.devicetype,
            "osVersion": self.osversion,
            "protocol": getattr(self, "protocol", "android"),
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f)
            print("账号信息已保存")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _handle_response(self, response: requests.Response) -> dict:
        """处理API响应"""
        try:
            data = response.json()
            if data.get("code") != 0 and data.get("code") != 200:
                print(f"API错误: {data.get('message', '未知错误')} (代码: {data.get('code')})")
            return data
        except json.JSONDecodeError:
            print("响应解析错误")
            return {"code": -1, "message": "响应解析错误"}

    def login(self) -> int:
        """用户登录"""
        data = {"type": 1, "passport": self.user_name, "password": self.password}
        try:
            response = requests.post(
                "https://www.123pan.com/b/api/user/sign_in",
                headers=self.headers,
                json=data,
                timeout=15
            )
            result = self._handle_response(response)
            if result.get("code") == 200:
                # 更新授权令牌
                token = result["data"]["token"]
                self.authorization = f"Bearer {token}"
                self.headers["authorization"] = self.authorization
                
                # 保存cookie
                if "Set-Cookie" in response.headers:
                    self.cookies = requests.utils.dict_from_cookiejar(response.cookies)
                
                self._save_config()
                print("登录成功")
                return 0
            return result.get("code", -1)
        except requests.exceptions.RequestException as e:
            print(f"登录请求失败: {e}")
            return -1

    def get_dir(self, save: bool = True) -> Tuple[int, list]:
        """获取当前目录内容"""
        return self.get_dir_by_id(self.parent_file_id, save)

    def get_dir_by_id(
        self, 
        file_id: int, 
        save: bool = True, 
        all_files: bool = False, 
        limit: int = 100
    ) -> Tuple[int, list]:
        """获取指定目录内容"""
        page = self.file_page * 3 + 1 if not all_files else 1
        current_count = len(self.list) if all_files else 0
        items = []
        total = -1
        attempts = 0
        
        while (current_count < total or total == -1) and (attempts < 3 or all_files):
            params = {
                "driveId": 0,
                "limit": limit,
                "next": 0,
                "orderBy": "file_id",
                "orderDirection": "desc",
                "parentFileId": str(file_id),
                "trashed": False,
                "SearchData": "",
                "Page": str(page),
                "OnlyLookAbnormalFile": 0,
            }
            
            try:
                response = requests.get(
                    "https://www.123pan.com/api/file/list/new",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                result = self._handle_response(response)
                if result.get("code") != 0:
                    return result.get("code", -1), []
                
                page_items = result["data"]["InfoList"]
                items.extend(page_items)
                total = result["data"]["Total"]
                current_count += len(page_items)
                page += 1
                attempts += 1
                
                if attempts % 5 == 0:
                    print(f"获取文件中: {current_count}/{total}，暂停10秒...")
                    time.sleep(10)
            except requests.exceptions.RequestException:
                print("连接失败")
                return -1, []
        
        self.all_file = current_count >= total
        self.total = total
        self.file_page += 1 if not all_files else 0
        
        if save:
            self.list.extend(items)
        
        return 0, items

    def show(self):
        """显示当前目录内容"""
        if not self.list:
            print("当前目录为空")
            return
        
        print("\n" + "=" * 60)
        print(f"当前路径: /{'/'.join(self.parent_file_name_list)}")
        print("-" * 60)
        print(f"{'编号':<6}{'类型':<8}{'大小':<12}{'名称'}")
        print("-" * 60)
        
        for idx, item in enumerate(self.list, 1):
            item_type = "文件夹" if item["Type"] == 1 else "文件"
            size = self._format_size(item["Size"])
            
            # 使用颜色区分类型
            color_code = "\033[35m" if item["Type"] == 1 else "\033[33m"
            reset_code = "\033[0m"
            
            print(f"{color_code}{idx:<6}{item_type:<8}{size:<12}{item['FileName']}{reset_code}")
        
        if not self.all_file:
            remaining = self.total - len(self.list)
            print(f"\n还有 {remaining} 个文件未加载，输入 'more' 继续加载")
        print("=" * 60 + "\n")

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes >= 1073741824:
            return f"{size_bytes / 1073741824:.2f} GB"
        elif size_bytes >= 1048576:
            return f"{size_bytes / 1048576:.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        return f"{size_bytes} B"

    def delete_file(self, file_id: Union[int, dict], by_index: bool = True, delete: bool = True) -> bool:
        """删除或恢复文件"""
        if by_index:
            if not (0 <= file_id < len(self.list)):
                print("无效的文件编号")
                return False
            file_data = self.list[file_id]
        else:
            file_data = file_id
        
        payload = {
            "driveId": 0,
            "fileTrashInfoList": file_data,
            "operation": delete,
        }
        
        try:
            response = requests.post(
                "https://www.123pan.com/a/api/file/trash",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            result = self._handle_response(response)
            if result.get("code") == 0:
                action = "删除" if delete else "恢复"
                print(f"文件 {file_data['FileName']} {action}成功")
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"删除操作失败: {e}")
            return False

    def share(self, file_ids: List[int], share_pwd: str = "") -> Optional[str]:
        """创建分享链接"""
        if not file_ids:
            print("未选择文件")
            return None
        
        file_names = [self.list[i]["FileName"] for i in file_ids]
        print("分享文件:", ", ".join(file_names))
        
        payload = {
            "driveId": 0,
            "expiration": "2099-12-12T08:00:00+08:00",
            "fileIdList": ",".join(str(self.list[i]["FileId"]) for i in file_ids),
            "shareName": "分享文件",
            "sharePwd": share_pwd,
            "event": "shareCreate"
        }
        
        try:
            response = requests.post(
                "https://www.123pan.com/a/api/share/create",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            result = self._handle_response(response)
            if result.get("code") == 0:
                share_key = result["data"]["ShareKey"]
                share_url = f"https://www.123pan.com/s/{share_key}"
                print(f"分享创建成功!\n链接: {share_url}")
                if share_pwd:
                    print(f"提取码: {share_pwd}")
                return share_url
            return None
        except requests.exceptions.RequestException as e:
            print(f"创建分享失败: {e}")
            return None

    def upload(self, file_path: str) -> bool:
        """上传文件"""
        file_path = file_path.strip().replace('"', "").replace("\\", "/")
        if not os.path.exists(file_path):
            print("文件不存在")
            return False
        
        if os.path.isdir(file_path):
            print("暂不支持文件夹上传")
            return False
        
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # 计算文件MD5
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    md5_hash.update(chunk)
            file_md5 = md5_hash.hexdigest()
        except IOError as e:
            print(f"读取文件失败: {e}")
            return False
        
        # 上传请求
        payload = {
            "driveId": 0,
            "etag": file_md5,
            "fileName": file_name,
            "parentFileId": self.parent_file_id,
            "size": file_size,
            "type": 0,
            "duplicate": 0,
        }
        
        try:
            response = requests.post(
                "https://www.123pan.com/b/api/file/upload_request",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            result = self._handle_response(response)
            if result.get("code") == 5060:  # 文件已存在
                choice = input("检测到同名文件，输入 1 覆盖，2 保留两者，其他取消: ")
                if choice == "1":
                    payload["duplicate"] = 1
                elif choice == "2":
                    payload["duplicate"] = 2
                else:
                    print("上传取消")
                    return False
                
                response = requests.post(
                    "https://www.123pan.com/b/api/file/upload_request",
                    headers=self.headers,
                    json=payload,
                    timeout=15
                )
                result = self._handle_response(response)
            
            if result.get("code") != 0:
                return False
            
            # 检查是否MD5复用
            if result["data"].get("Reuse", False):
                print("文件已存在，MD5复用成功")
                return True
            
            # 分块上传
            return self._upload_chunks(
                file_path, 
                result["data"]["Bucket"],
                result["data"]["StorageNode"],
                result["data"]["Key"],
                result["data"]["UploadId"],
                result["data"]["FileId"]
            )
        except requests.exceptions.RequestException as e:
            print(f"上传失败: {e}")
            return False

    def _upload_chunks(
        self, 
        file_path: str, 
        bucket: str, 
        storage_node: str, 
        key: str, 
        upload_id: str, 
        file_id: str
    ) -> bool:
        """分块上传文件"""
        chunk_size = 5 * 1024 * 1024  # 5MB
        total_size = os.path.getsize(file_path)
        uploaded = 0
        part_number = 1
        
        try:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # 获取上传URL
                    url_data = {
                        "bucket": bucket,
                        "key": key,
                        "partNumberEnd": part_number + 1,
                        "partNumberStart": part_number,
                        "uploadId": upload_id,
                        "StorageNode": storage_node,
                    }
                    
                    try:
                        response = requests.post(
                            "https://www.123pan.com/b/api/file/s3_repare_upload_parts_batch",
                            headers=self.headers,
                            json=url_data,
                            timeout=15
                        )
                        url_result = self._handle_response(response)
                        if url_result.get("code") != 0:
                            return False
                        
                        upload_url = url_result["data"]["presignedUrls"][str(part_number)]
                    except requests.exceptions.RequestException:
                        return False
                    
                    # 上传分块
                    try:
                        upload_response = requests.put(upload_url, data=chunk, timeout=30)
                        if upload_response.status_code not in (200, 201):
                            return False
                    except requests.exceptions.RequestException:
                        return False
                    
                    uploaded += len(chunk)
                    progress = uploaded / total_size * 100
                    print(f"\r上传进度: {progress:.1f}%", end="", flush=True)
                    part_number += 1
            
            print("\n上传完成，正在验证...")
            time.sleep(1)  # 等待服务器处理
            
            # 完成上传
            compmultipart_up_url = (
                "https://www.123pan.com/b/api/file/s3_complete_multipart_upload"
            )
            requests.post(
                compmultipart_up_url,
                headers=self.headers,
                data=json.dumps({
                    "bucket": bucket,
                    "key": key,
                    "uploadId": upload_id,
                    "StorageNode": storage_node,
                    }),
                timeout=10
            )
            complete_data = {"fileId": file_id}
            try:
                response = requests.post(
                    "https://www.123pan.com/b/api/file/upload_complete",
                    headers=self.headers,
                    json=complete_data,
                    timeout=15
                )
                result = self._handle_response(response)
                if result.get("code") == 0:
                    print("文件上传成功")
                    return True
                return False
            except requests.exceptions.RequestException:
                return False
        except IOError as e:
            print(f"读取文件失败: {e}")
            return False

    def change_directory(self, target: str):
        """改变当前目录"""
        if target == "..":
            if len(self.parent_file_list) > 1:
                self.parent_file_list.pop()
                self.parent_file_id = self.parent_file_list[-1]
                self.parent_file_name_list.pop()
                self.refresh_directory()
            else:
                print("已经是根目录")
        elif target == "/":
            self.parent_file_id = 0
            self.parent_file_list = [0]
            self.parent_file_name_list = []
            self.refresh_directory()
        elif target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(self.list) and self.list[idx]["Type"] == 1:
                self.parent_file_id = self.list[idx]["FileId"]
                self.parent_file_list.append(self.parent_file_id)
                self.parent_file_name_list.append(self.list[idx]["FileName"])
                self.refresh_directory()
            else:
                print("无效的目录编号或不是文件夹")
                
        else:
            print("无效命令，使用 '..' 返回上级，'/' 返回根目录，或输入文件夹编号")

    def refresh_directory(self):
        """刷新当前目录内容"""
        self.all_file = False
        self.file_page = 0
        self.list = []
        self.get_dir()
        self.show()

    def create_directory(self, name: str) -> bool:
        """创建新目录"""
        if not name:
            print("目录名不能为空")
            return False
        
        # 检查是否已存在
        for item in self.list:
            if item["FileName"] == name and item["Type"] == 1:
                print("目录已存在")
                return True
        
        payload = {
            "driveId": 0,
            "etag": "",
            "fileName": name,
            "parentFileId": self.parent_file_id,
            "size": 0,
            "type": 1,
            "duplicate": 1,
            "NotReuse": True,
            "event": "newCreateFolder",
            "operateType": 1,
        }
        
        try:
            response = requests.post(
                "https://www.123pan.com/a/api/file/upload_request",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            result = self._handle_response(response)
            if result.get("code") == 0:
                print(f"目录 '{name}' 创建成功")
                self.get_dir()
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"创建目录失败: {e}")
            return False

    def get_download_link(self, file_index: int) -> Optional[str]:
        """获取文件下载链接"""
        if not (0 <= file_index < len(self.list)):
            print("无效的文件编号")
            return None
        
        file_detail = self.list[file_index]
        
        if file_detail["Type"] == 1:  # 文件夹
            url = "https://www.123pan.com/a/api/file/batch_download_info"
            data = {"fileIdList": [{"fileId": int(file_detail["FileId"])}]}
        else:  # 文件
            url = "https://www.123pan.com/a/api/file/download_info"
            data = {
                "driveId": 0,
                "etag": file_detail["Etag"],
                "fileId": file_detail["FileId"],
                "s3keyFlag": file_detail["S3KeyFlag"],
                "type": file_detail["Type"],
                "fileName": file_detail["FileName"],
                "size": file_detail["Size"],
            }
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=15)
            result = self._handle_response(response)
            if result.get("code") != 0:
                return None
            
            download_url = result["data"]["DownloadUrl"]
            # 获取重定向后的真实下载链接
            redirect_response = requests.get(download_url, allow_redirects=False, timeout=15)
            if redirect_response.status_code == 302:
                return redirect_response.headers.get("Location")
            
            # 尝试从HTML中提取下载链接
            url_pattern = re.compile(r"href='(https?://[^']+)'")
            match = url_pattern.search(redirect_response.text)
            if match:
                return match.group(1)
            
            return None
        except requests.exceptions.RequestException as e:
            print(f"获取下载链接失败: {e}")
            return None

    def download_file(self, file_index: int, download_path: str = "download") -> bool:
        """下载单个文件"""
        if not (0 <= file_index < len(self.list)):
            print("无效的文件编号")
            return False
        
        file_detail = self.list[file_index]
        
        # 文件夹需要特殊处理
        if file_detail["Type"] == 1:
            print("文件夹下载:")
            return self.download_directory(file_detail, download_path)
        
        # 获取下载链接
        download_url = self.get_download_link(file_index)
        if not download_url:
            print("无法获取下载链接")
            return False
        
        # 确定文件名
        file_name = file_detail["FileName"]
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        # 处理文件已存在的情况
        full_path = os.path.join(download_path, file_name)
        if os.path.exists(full_path):
            if self.download_mode == 4:  # 全部跳过
                print(f"文件已存在，跳过: {file_name}")
                return True
            
            print(f"文件已存在: {file_name}")
            choice = input("输入1覆盖，2跳过，3全部覆盖，4全部跳过: ")
            if choice == "2" or choice == "4":
                if choice == "4":
                    self.download_mode = 4
                print("跳过下载")
                return True
            elif choice == "3":
                self.download_mode = 3
            os.remove(full_path)
        
        # 临时文件名
        temp_path = full_path + ".123pan"
        
        try:
            # 开始下载
            print(f"开始下载: {file_name}")
            response = requests.get(download_url, stream=True, timeout=30)
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            start_time = time.time()
            
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 计算下载速度
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = downloaded / elapsed
                            speed_str = self._format_size(speed) + "/s"
                        else:
                            speed_str = "未知"
                        
                        # 显示进度
                        if total_size > 0:
                            percent = downloaded / total_size * 100
                            print(f"\r进度: {percent:.1f}% | {self._format_size(downloaded)}/{self._format_size(total_size)} | {speed_str}", end="     ")
            
            # 重命名文件
            os.rename(temp_path, full_path)
            print(f"\n下载完成: {file_name}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"\n下载失败: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def download_directory(self, directory: dict, download_path: str = "download") -> bool:
        """下载整个目录"""
        if directory["Type"] != 1:
            print("不是文件夹")
            return False
        
        print(f"开始下载文件夹: {directory['FileName']}")
        
        # 创建目标目录
        target_dir = os.path.join(download_path, directory["FileName"])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # 获取目录内容
        _, items = self.get_dir_by_id(directory["FileId"], save=False, all_files=True)
        if not items:
            print("文件夹为空")
            return True
        
        # 下载所有内容
        success = True
        for item in items:
            if item["Type"] == 1:  # 子文件夹
                sub_success = self.download_directory(item, target_dir)
                success = success and sub_success
            else:  # 文件
                # 临时将文件添加到列表中以便下载
                original_list = self.list
                self.list = [item]
                file_success = self.download_file(0, target_dir)
                self.list = original_list
                success = success and file_success
        
        print(f"文件夹下载完成: {directory['FileName']}")
        return success

    def get_recycle_bin(self):
        """获取回收站内容"""
        url = "https://www.123pan.com/a/api/file/list/new?driveId=0&limit=100&next=0&orderBy=fileId&orderDirection=desc&parentFileId=0&trashed=true&Page=1"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            result = self._handle_response(response)
            if result.get("code") == 0:
                return result["data"]["InfoList"]
            return []
        except requests.exceptions.RequestException:
            return []

    def restore_file(self, file_id: int) -> bool:
        """从回收站恢复文件"""
        payload = {
            "driveId": 0,
            "fileTrashInfoList": {"FileId": file_id},
            "operation": False  # False表示恢复
        }
        
        try:
            response = requests.post(
                "https://www.123pan.com/a/api/file/trash",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            result = self._handle_response(response)
            return result.get("code") == 0
        except requests.exceptions.RequestException:
            return False

    def logout(self):
        """登出：清除 authorization、cookies 并保存配置"""
        self.authorization = ""
        # 清理 headers 中的 authorization 字段（兼容大小写）
        if "authorization" in self.headers:
            self.headers["authorization"] = ""
        if "Authorization" in self.headers:
            self.headers["Authorization"] = ""
        self.cookies = None
        self._save_config()
        print("已登出，授权信息已清除")

    def set_protocol(self, protocol: str, save: bool = True):
        """切换协议：'android' 或 'web'，切换后会重新初始化 headers 并可选择保存配置"""
        protocol = protocol.lower()
        if protocol not in ("android", "web"):
            print("不支持的协议，仅支持 'android' 或 'web'")
            return False
        self.protocol = protocol
        self._init_headers()
        # 确保 authorization 字段更新到 headers
        if "authorization" in self.headers:
            self.headers["authorization"] = self.authorization
        if "Authorization" in self.headers:
            self.headers["Authorization"] = self.authorization
        if save:
            self._save_config()
        print(f"已切换到 {protocol} 协议")
        return True


if __name__ == "__main__":
    """主交互函数"""
    # 解决Windows下cmd颜色转义问题
    if os.name == "nt":
        os.system("")
    
    print("=" * 60)
    print("123网盘客户端".center(60))
    print("=" * 60)
    
    pan = Pan123(config_file="123pan_config.json")
    pan.show()
    
    while True:
        try:
            path = "/" + "/".join(pan.parent_file_name_list) if pan.parent_file_name_list else "/"
            command = input(f"\033[91m{path}>\033[0m ").strip()
            
            if not command:
                continue
            
            parts = command.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            # 命令映射
            if cmd == "ls":
                pan.show()
            elif cmd == "login":
                pan.login()
                pan.refresh_directory()
            elif cmd == "logout":
                pan.logout()
                pan.refresh_directory()
            elif cmd == "exit":
                break
            elif cmd == "cd":
                pan.change_directory(arg)
            elif cmd == "mkdir":
                pan.create_directory(arg)
                # 刷新当前目录
                pan.refresh_directory()
            elif cmd == "upload":
                pan.upload(arg)
                pan.refresh_directory()
            elif cmd == "rm":
                if arg.isdigit():
                    pan.delete_file(int(arg) - 1)
                    pan.refresh_directory()
                else:
                    print("无效的文件编号")
            elif cmd == "share":
                file_ids = [int(idx) - 1 for idx in arg.split() if idx.isdigit()]
                if file_ids:
                    pwd = input("输入提取码(留空跳过): ")
                    pan.share(file_ids, pwd)
                else:
                    print("请提供文件编号")
            elif cmd == "more":
                pan.get_dir()
                pan.show()
            elif cmd == "link":
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(pan.list):
                        link = pan.get_download_link(idx)
                        if link:
                            print(f"文件直链: {link}")
                        else:
                            print("获取直链失败")
                    else:
                        print("无效的文件编号")
                else:
                    print("请提供文件编号")
            elif cmd in ("download", "d"):
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(pan.list):
                        pan.download_file(idx)
                    else:
                        print("无效的文件编号")
                else:
                    print("请提供文件编号")
            elif cmd == "recycle":
                recycle_items = pan.get_recycle_bin()
                if recycle_items:
                    print("\n回收站内容:")
                    for i, item in enumerate(recycle_items, 1):
                        print(f"{i}. {item['FileName']} ({pan._format_size(item['Size'])})")
                    
                    action = input("\n输入编号恢复文件，或输入 'clear' 清空回收站: ").strip()
                    if action.isdigit():
                        idx = int(action) - 1
                        if 0 <= idx < len(recycle_items):
                            if pan.restore_file(recycle_items[idx]["FileId"]):
                                print("文件恢复成功")
                            else:
                                print("恢复失败")
                    elif action == "clear":
                        for item in recycle_items:
                            pan.delete_file(item, by_index=False)
                        print("回收站已清空")
                else:
                    print("回收站为空")
                # 刷新当前目录
                pan.refresh_directory()
            elif cmd in ("refresh", "re"):
                pan.refresh_directory()
            elif cmd == "reload":
                pan._load_config()
                pan.refresh_directory()
            elif cmd.isdigit():
                # 切换目录或下载文件
                idx = int(cmd) - 1
                if 0 <= idx < len(pan.list):
                    if pan.list[idx]["Type"] == 1:
                        pan.change_directory(cmd)
                    else:
                        pan.download_file(idx)
                else:
                    print("无效的文件编号")
                
            elif cmd == "protocol":
                if arg.lower() in ("android", "web"):
                    pan.set_protocol(arg.lower())
                    pan.refresh_directory()
                else:
                    print("请指定协议: android 或 web")
            else:
                # 帮助提示，列出支持的命令
                print("可用命令:")
                print("  ls                 - 显示当前目录")
                print("  cd [编号|..|/]     - 切换目录")
                print("  mkdir [名称]       - 创建目录")
                print("  upload [路径]      - 上传文件")
                print("  rm [编号]          - 删除文件")
                print("  share [编号 ...]   - 创建分享")
                print("  link [编号]        - 获取文件直链")
                print("  download/d [编号]  - 下载文件")
                print("  recycle            - 管理回收站")
                print("  refresh/re         - 刷新目录")
                print("  reload             - 重新加载配置并刷新")
                print("  login              - 登录")
                print("  logout             - 登出并清除 token")
                print("  more               - 继续加载更多文件")
                # print("  all                - 强制加载当前目录所有文件")
                print("  exit               - 退出程序")
                print("  protocol [android|web] - 切换协议")
        except KeyboardInterrupt:
            print("\n操作已取消")
        except Exception as e:
            print(f"发生错误: {e}")

