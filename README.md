# 1、123Pan Cli工具

123 网盘命令行工具，支持列出文件、下载、上传、分享、删除、创建目录及回收站管理。

<!-- TOC -->
* [1、123Pan Cli工具](#1123pan-cli工具)
  * [1.1 特性](#11-特性)
  * [1.2 脚本环境要求](#12-脚本环境要求)
  * [1.3 安装与运行](#13-安装与运行)
    * [1.3.1 脚本运行](#131-脚本运行)
    * [1.3.2 下载release版](#132-下载release版)
  * [1.4 配置文件（JSON）](#14-配置文件json)
  * [1.5 常用命令（交互式）](#15-常用命令交互式)
* [2、123Pan接口模块（pan123_core.py）](#2123pan接口模块pan123_corepy)
    * [2.1 核心类：`Pan123Core`](#21-核心类pan123core)
      * [2.1.1 属性说明](#211-属性说明)
      * [2.1.2 方法清单](#212-方法清单)
        * [2.1.2.1 （1）登录操作](#2121-1登录操作)
        * [2.1.2.2 （2）配置管理](#2122-2配置管理)
        * [2.1.2.3 （3）目录操作](#2123-3目录操作)
        * [2.1.2.4 （4）文件操作](#2124-4文件操作)
        * [2.1.2.5 （5）用户信息](#2125-5用户信息)
    * [2.2 工具类：`Pan123Tool`](#22-工具类pan123tool)
      * [2.2.1 属性说明](#221-属性说明)
      * [2.2.2 方法清单](#222-方法清单)
        * [2.2.2.1 （1）配置管理](#2221-1配置管理)
        * [2.2.2.2 （2）文件下载](#2222-2文件下载)
        * [2.2.2.3 （3）文件上传](#2223-3文件上传)
    * [2.3 全局配置参数](#23-全局配置参数)
      * [2.3.1 协议相关](#231-协议相关)
      * [2.3.2 设备伪装](#232-设备伪装)
    * [2.4 错误码说明](#24-错误码说明)
    * [2.5 典型使用示例](#25-典型使用示例)
* [3、下载说明](#3下载说明)
* [4、注意事项](#4注意事项)
* [5、免责声明](#5免责声明)
<!-- TOC -->

## 1.1 特性

- 登录 / 登出
- 列出当前目录文件（ls）
- 切换目录（cd）与刷新（refresh / re）
- 下载单文件或递归下载文件夹（download / d）
- 上传文件（upload）
- 创建文件夹（mkdir）
- 删除文件（rm）
- 创建分享链接（share）
- 获取文件直链（link）
- 回收站管理（recycle / restore）
- 协议切换（protocol android|web）
- 支持保存配置到 JSON 文件（authorization、device/os、protocol 等）

## 1.2 脚本环境要求

- Python 3
- 依赖库：requests  
  安装：
  ```bash  
  pip install requests  
  ```  

## 1.3 安装与运行

### 1.3.1 脚本运行

1. 克隆或下载本仓库到本地。
2. 进入项目目录。
3. 运行脚本：
   ```bash  
   python pan123_cli.py  
   ```  
   启动后会提示输入用户名 / 密码，或自动读取配置文件（默认 `123pan_config.json`，脚本内部根据传入参数使用该文件）。

### 1.3.2 下载release版

根据系统下载对应的 release 版本，解压后运行 `123pan.exe`（Windows）或 `123pan`（Linux）。

## 1.4 配置文件（JSON）

脚本会读取并保存一个配置文件（示例 `123pan_config.json`），保存登录状态与偏好，格式示例：

```json  
{
  "userName": "your_username",
  "passWord": "your_password",
  "authorization": "Bearer xxxxx",
  "deviceType": "M2007J20CI",
  "osVersion": "Android_10",
  "protocol": "android"
}  
```  

注意：保存密码或 token 到本地会有安全风险，请在可信环境下使用并妥善保护该文件。

## 1.5 常用命令（交互式）

在脚本交互提示符中输入命令，部分带参数：

| 指令                          | 用法示例                                   | 功能说明                             |
|-----------------------------|----------------------------------------|----------------------------------|
| 直接输入编号                      | `3`                                    | 若编号对应文件夹 → 进入该文件夹；若为文件 → 直接下载该文件 |
| ls                          | `ls`                                   | 显示当前目录的文件与文件夹列表                  |
| cd [编号&#124;..&#124;/]      | `cd 3`、`cd ..`、`cd /`                  | 切换目录：进入指定编号的文件夹、返回上级、返回根目录       |
| mkdir [名称]                  | `mkdir test`                           | 在当前目录创建文件夹                       |
| upload [路径]                 | `upload C:\Users\you\Desktop\file.txt` | 上传文件到当前目录（仅支持单个文件）               |
| rm [编号]                     | `rm 2`                                 | 删除当前列表中指定编号的文件/文件夹（移入回收站）        |
| share [编号 ...]              | `share 2 4`                            | 为指定文件创建一个或多个分享链接，可设置提取码（可为空）     |
| link [编号]                   | `link 3`                               | 获取指定文件的直链地址                      |
| download / d [编号]           | `download 5` 或 `d 5`                   | 下载指定编号的文件或文件夹（文件夹将递归下载）          |
| recycle                     | `recycle`                              | 查看回收站内容，可恢复指定编号项或输入 clear 清空回收站  |
| refresh / re                | `refresh` 或 `re`                       | 刷新当前目录列表                         |
| reload                      | `reload`                               | 重新加载配置文件并刷新目录                    |
| login / logout              | `login`、`logout`                       | 手动登录或登出（清除授权信息）                  |
| clearaccount                | clearaccount                           | 清除已登录账号（包括用户名和密码）                |
| more                        | `more`                                 | 当目录分页未加载完时，继续加载更多内容              |
| protocol [android&#124;web] | `protocol web`                         | 切换通信协议（如 android/web），并可选择保存配置   |
| exit                        | `exit`                                 | 退出程序                             |

---  

交互示例：

```  
/> cd demo  
无效命令，使用 '..' 返回上级，'/' 返回根目录，或输入文件夹编号  
/> cd 1     
当前目录为空  
/demo1> ls  
当前目录为空  
/demo1> mkdir test  
目录 'test' 创建成功  

/demo1> 1  
当前目录为空  
/demo1/test> upload 123pan.py  
上传进度: 100.0%  
上传完成，正在验证...  
文件上传成功  
------------------------------------------------------------  
编号    类型      大小          名称  
------------------------------------------------------------  
1     文件      38.66 KB    123pan.py  
============================================================  

/demo1/test> 1  
开始下载: 123pan.py  
进度: 100.0% | 38.66 KB/38.66 KB | 10.29 MB/s        
下载完成: 123pan.py  
/demo1/test>  
```

# 2、123Pan接口模块（pan123_core.py）

以下是基于代码实现的 **123pan 网盘 API**，按类结构分类说明：

---  

### 2.1 核心类：`Pan123Core`

负责与 123pan 服务器的通信，管理认证状态、目录浏览、文件操作等核心逻辑。

#### 2.1.1 属性说明

| 属性名             | 类型         | 描述                          |  
|-----------------|------------|-----------------------------|  
| `user_name`     | str        | 登录账号（手机号/用户名）               |  
| `password`      | str        | 登录密码                        |  
| `authorization` | str        | 认证 Token（登录后自动填充）           |  
| `protocol`      | str        | 请求协议（`"android"` 或 `"web"`） |  
| `cwd_id`        | int        | 当前工作目录 ID（0 表示根目录）          |  
| `file_list`     | List[dict] | 当前目录文件列表                    |  
| `nick_name`     | str        | 当前用户昵称                      |  
| `uid`           | int        | 当前用户 UID                    |  

---  

#### 2.1.2 方法清单

##### 2.1.2.1 （1）登录操作

| 方法名               | 参数说明 | 返回值类型  | 功能描述                       |  
|-------------------|------|--------|----------------------------|  
| `login()`         | 无    | Result | 使用 `user_name/password` 登录 |  
| `logout()`        | 无    | Result | 登出并清除 Token                |  
| `check_login()`   | 无    | Result | 检查当前 Token 是否有效            |  
| `clear_account()` | 无    | Result | 清除账号信息（不保存配置）              |  

##### 2.1.2.2 （2）配置管理

| 方法名                      | 参数说明                              | 返回值类型  | 功能描述                 |  
|--------------------------|-----------------------------------|--------|----------------------|  
| `load_config(cfg)`       | `cfg`: 包含账号信息的字典（见下方配置参数）         | Result | 加载配置并更新实例状态          |  
| `get_current_config()`   | 无                                 | dict   | 获取当前配置（账号、Token、协议等） |  
| `set_protocol(protocol)` | `protocol`: `"android"` 或 `"web"` | Result | 切换请求协议               |  

##### 2.1.2.3 （3）目录操作

| 方法名                                           | 参数说明                                                    | 返回值类型  | 功能描述         |  
|-----------------------------------------------|---------------------------------------------------------|--------|--------------|  
| `list_dir(parent_id=None, page=1, limit=100)` | `parent_id`: 父目录 ID<br>`page`: 页码<br>`limit`: 单页数量      | Result | 获取单页文件列表     |  
| `list_dir_all(parent_id=None, limit=100)`     | 同上                                                      | Result | 获取全部文件（自动翻页） |  
| `mkdir(name)`                                 | `name`: 目录名                                             | Result | 在当前目录创建子目录   |  
| `cd(folder_index)`                            | `folder_index`: `file_list` 中的目标文件夹下标                   | Result | 进入目标文件夹      |  
| `cd_up()`                                     | 无                                                       | Result | 返回上级目录       |  
| `cd_root()`                                   | 无                                                       | Result | 返回根目录        |  
| `trash(file_data, delete=True)`               | `file_data`: 文件信息字典<br>`delete`: 是否删除（True=删除，False=恢复） | Result | 删除或恢复文件      |  
| `list_recycle()`                              | 无                                                       | Result | 获取回收站文件列表    |  

##### 2.1.2.4 （4）文件操作

| 方法名                                                                     | 参数说明                                                                            | 返回值类型  | 功能描述            |  
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------|--------|-----------------|  
| `upload_file(file_path, duplicate=0, on_progress=None)`                 | `file_path`: 本地文件路径<br>`duplicate`: 冲突策略（0=报错，1=覆盖，2=保留）<br>`on_progress`: 进度回调 | Result | 上传文件（支持秒传和分块上传） |  
| `get_download_url(index)`                                               | `index`: `file_list` 中的目标文件下标                                                   | Result | 获取文件直链（自动处理重定向） |  
| `share(file_ids, share_pwd="", expiration="2099-12-12T08:00:00+08:00")` | `file_ids`: 文件 ID 列表<br>`share_pwd`: 提取码<br>`expiration`: 过期时间                  | Result | 创建分享链接          |  

##### 2.1.2.5 （5）用户信息

| 方法名               | 参数说明 | 返回值类型  | 功能描述                   |  
|-------------------|------|--------|------------------------|  
| `get_user_info()` | 无    | Result | 获取当前用户信息（UID、昵称、空间用量等） |  

---  

### 2.2 工具类：`Pan123Tool`

基于 `Pan123Core` 提供文件交互功能（依赖文件系统操作）。

#### 2.2.1 属性说明

| 属性名           | 类型         | 描述                                |  
|---------------|------------|-----------------------------------|  
| `core`        | Pan123Core | 关联的核心实例                           |  
| `config_file` | str        | 配置文件路径（默认 `"123pan_config.json"`） |  

---  

#### 2.2.2 方法清单

##### 2.2.2.1 （1）配置管理

| 方法名                       | 参数说明 | 返回值类型  | 功能描述       |  
|---------------------------|------|--------|------------|  
| `load_config_from_file()` | 无    | Result | 从文件加载配置    |  
| `save_config_to_file()`   | 无    | Result | 将当前配置保存到文件 |  

##### 2.2.2.2 （2）文件下载

| 方法名                                                                                                          | 参数说明                                                                                                          | 返回值类型  | 功能描述   |  
|--------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|--------|--------|  
| `download_file(index, save_dir="download", on_progress=None, overwrite=False, skip_existing=False)`          | `index`: 文件列表下标<br>`save_dir`: 保存路径<br>`on_progress`: 进度回调<br>`overwrite`: 是否覆盖<br>`skip_existing`: 是否跳过已存在文件 | Result | 下载单个文件 |  
| `download_directory(directory, save_dir="download", on_progress=None, overwrite=False, skip_existing=False)` | `directory`: 目录信息字典<br>其他参数同上                                                                                 | Result | 递归下载目录 |  

##### 2.2.2.3 （3）文件上传

| 方法名                                                     | 参数说明                       | 返回值类型  | 功能描述              |  
|---------------------------------------------------------|----------------------------|--------|-------------------|  
| `upload_file(file_path, duplicate=0, on_progress=None)` | 同 `Pan123Core.upload_file` | Result | 上传文件（与 Core 方法一致） |  

---  

### 2.3 全局配置参数

#### 2.3.1 协议相关

| 参数名                   | 默认值                        | 描述              |  
|-----------------------|----------------------------|-----------------|  
| `API_BASE_URL`        | `"https://www.123pan.com"` | API 根地址         |  
| `TIMEOUT_DEFAULT`     | `15`                       | 默认请求超时时间（秒）     |  
| `UPLOAD_CHUNK_SIZE`   | `5*1024*1024`              | 分块上传单块大小（5MB）   |  
| `DOWNLOAD_CHUNK_SIZE` | `8192`                     | 下载流式读取单块大小（8KB） |  

#### 2.3.2 设备伪装

| 参数名            | 默认值 | 描述                |  
|----------------|-----|-------------------|  
| `DEVICE_TYPES` | 见代码 | 可选 Android 设备型号列表 |  
| `OS_VERSIONS`  | 见代码 | 可选 Android 系统版本列表 |  

---  

### 2.4 错误码说明

| 错误码  | 含义     | 可能触发场景                     |  
|------|--------|----------------------------|  
| 0    | 操作成功   | 所有接口成功时返回                  |  
| -1   | 网络请求失败 | 连接超时、SSL 错误等               |  
| 5060 | 文件名冲突  | 上传时 `duplicate=0` 且目标文件已存在 |  
| 1    | 本地文件冲突 | 下载时目标文件已存在                 |  

---  

### 2.5 典型使用示例

```python  
import json

from pan123_core import Pan123Core, Pan123Tool, Pan123EventType, format_size

# 初始化核心对象（Android 协议）  
core = Pan123Core(
    user_name="13800138000",
    password="your_password",
    protocol=Pan123Core.PROTOCOL_ANDROID
)

# 登录  
result = core.login()
if result["code"] != 0:
    raise Exception("登录失败")

# 创建工具类实例  
tool = Pan123Tool(core)


# 下载文件  
def _download_progress(data) -> None:
    if data.get("type") == Pan123EventType.DOWNLOAD_PROGRESS:
        downloaded = data.get("downloaded", 0)
        total = data.get("total", 0)
        speed = data.get("speed", 0)
        if total > 0:
            pct = downloaded / total * 100
            print(
                f"\r进度: {pct:.1f}% | {format_size(downloaded)}/{format_size(total)} | {format_size(int(speed))}/s",
                end="     ",
                flush=True,
            )
    elif data.get("type") == Pan123EventType.DOWNLOAD_START_FILE:
        print(f"开始下载: {data.get('file_name', '未知文件')} ({format_size(data.get('file_size', 0))})")
    elif data.get("type") == Pan123EventType.DOWNLOAD_START_DIRECTORY:
        print(f"开始下载目录: {data.get('dir_name', '未知目录')}")
    else:
        print(json.dumps(data, indent=2))


result = tool.download_file(
    index=0,
    save_dir="downloads",
    on_progress=lambda e: print(f"下载进度: {e['percent']:.2f}%")
)

# 上传文件  
result = core.upload_file(
    file_path="local_file.txt",
    duplicate=1,  # 覆盖已有文件  
    on_progress=None  # ...  
)

# 创建分享链接  
result = core.share(
    file_ids=[12345],
    share_pwd="123456",
    expiration="2026-12-31T23:59:59+08:00"
)  
```  

---  

# 3、下载说明

- 下载到脚本所在目录的 `download` 文件夹，下载过程中使用临时后缀 `.123pan`，下载完成后会重命名为原文件名。
- 如果文件已存在，会提示覆盖 / 跳过 / 全部覆盖 / 全部跳过等选项。

# 4、注意事项

- 本工具用于学习与自用场景，请勿用于违法用途。对任何滥用造成的后果，本人概不负责。
- 模拟客户端协议可能存在账号或服务端策略风险，请谨慎使用。
- 建议不要在公用或不受信任的机器上保存明文密码或授权信息。

# 5、免责声明

本工具用于学习场景，请勿用于违法用途。对任何滥用造成的后果，作者概不负责。
任何未经允许的api调用都是不被官方允许的，对于因此产生的账号风险、数据损失等后果自负。