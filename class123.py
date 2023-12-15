import re
import time
from sign_py import getSign
import requests
import hashlib
import os
import json
import base64


# 修改版，更加方便植入其他项目
# 1.mkdir()增加了parentFileId参数，可以指定父文件夹，会先切换到父文件夹
# 2.mkdir()增加了remake参数，如果remake为False，会先检查文件夹是否存在，存在则不创建，返回文件夹id
# 3.增加了getdir的new接口封ip检测，如果检测到ip被封，会等待20s后再次尝试
# 4.up_load()增加了parentFileId参数，可以指定父文件夹，会先切换到父文件夹


class Pan123:
    def __init__(self, readfile=True, user_name="", pass_word="", authorization="", input_pwd=True):
        self.RecycleList = None
        self.list = None
        if readfile:
            self.read_ini(user_name, pass_word, input_pwd, authorization)
        else:
            if user_name == "" or pass_word == "":
                print("读取已禁用，用户名或密码为空")
                if input_pwd:
                    user_name = input("请输入用户名:")
                    pass_word = input("请输入密码:")
                else:
                    raise Exception("用户名或密码为空：读取禁用时，userName和passWord不能为空")
            self.userName = user_name
            self.passWord = pass_word
            self.authorization = authorization
        self.headerOnlyUsage = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1474.0',
            "app-version": "2",
            "platform": "web", }
        self.headerLogined = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "App-Version": "3",
            "Authorization": self.authorization,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "LoginUuid": "z-uk_yT8HwR4raGX1gqGk",
            "Pragma": "no-cache",
            "Referer": "https://www.123pan.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "platform": "web",
            "sec-ch-ua": "^\\^Microsoft",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "^\\^Windows^^"
        }
        self.parentFileId = 0  # 路径，文件夹的id,0为根目录
        self.parentFileList = [0]
        code = self.get_dir()
        if code != 0:
            self.login()
            self.get_dir()

    def login(self):
        data = {"remember": True, "passport": self.userName, "password": self.passWord}
        sign = getSign('/b/api/user/sign_in')
        loginRes = requests.post("https://www.123pan.com/b/api/user/sign_in", headers=self.headerOnlyUsage, data=data,
                                 params={sign[0]: sign[1]})
        res_sign = loginRes.json()
        code = res_sign['code']
        if code != 200:
            print("code = 1 Error:" + str(code))
            print(res_sign['message'])
            return code
        token = res_sign['data']['token']
        self.authorization = 'Bearer ' + token
        headerLogined = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "App-Version": "3",
            "Authorization": self.authorization,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "LoginUuid": "z-uk_yT8HwR4raGX1gqGk",
            "Pragma": "no-cache",
            "Referer": "https://www.123pan.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "platform": "web",
            "sec-ch-ua": "^\\^Microsoft",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "^\\^Windows^^"
        }
        self.headerLogined = headerLogined
        # ret['cookie'] = cookie
        self.save_file()
        return code

    def save_file(self):
        with open("123pan.txt", "w") as f:
            saveList = {
                "userName": self.userName,
                "passWord": self.passWord,
                "authorization": self.authorization,
            }

            f.write(json.dumps(saveList))
        print("Save!")

    def get_dir(self):
        code = 0
        page = 1
        lists = []
        lenth_now = 0
        total = -1
        while lenth_now < total or total == -1:
            base_url = "https://www.123pan.com/b/api/file/list/new"

            # print(self.headerLogined)
            sign = getSign('/b/api/file/list/new')
            print(sign)
            params = {
                sign[0]: sign[1],
                "driveId": 0,
                "limit": 100,
                "next": 0,
                "orderBy": "file_id",
                "orderDirection": "desc",
                "parentFileId": str(self.parentFileId),
                "trashed": False,
                "SearchData": "",
                "Page": str(page),
                "OnlyLookAbnormalFile": 0
            }

            a = requests.get(base_url, headers=self.headerLogined, params=params)
            # print(a.text)
            # print(a.headers)
            text = a.json()
            # print(text)
            code = text['code']
            # code = 403
            if code != 0:
                print(a.text)
                print(a.headers)
                print("code = 2 Error:" + str(code))
                if code == 403 or code == "403":
                    print("sleep 20s")
                    time.sleep(20)
                    return self.get_dir()
                return code
            lists_page = text['data']['InfoList']
            lists += lists_page
            total = text['data']['Total']
            lenth_now += len(lists_page)
            page += 1
        FileNum = 0
        for i in lists:
            i["FileNum"] = FileNum
            FileNum += 1

        self.list = lists
        return code

    def show(self):
        print("--------------------")
        for i in self.list:
            size = i["Size"]
            if size > 1048576:
                size_print = str(round(size / 1048576, 2)) + "M"
            else:
                size_print = str(round(size / 1024, 2)) + "K"

            if i["Type"] == 0:

                print("\033[33m" + "编号:", self.list.index(i) + 1, "\033[0m \t\t" + size_print + "\t\t\033[36m",
                      i["FileName"], "\033[0m")
            elif i["Type"] == 1:
                print("\033[35m" + "编号:", self.list.index(i) + 1, " \t\t\033[36m",
                      i["FileName"], "\033[0m")

        print("--------------------")

    # fileNumber 从0开始，0为第一个文件，传入时需要减一 ！！！
    def link(self, file_number, showlink=True):
        fileDetail = self.list[file_number]
        typeDetail = fileDetail['Type']
        if typeDetail == 1:
            down_request_url = "https://www.123pan.com/a/api/file/batch_download_info"
            down_request_data = {"fileIdList": [{"fileId": int(fileDetail["FileId"])}]}

        else:
            down_request_url = "https://www.123pan.com/a/api/file/download_info"
            down_request_data = {"driveId": 0, "etag": fileDetail["Etag"], "fileId": fileDetail["FileId"],
                                 "s3keyFlag": fileDetail['S3KeyFlag'], "type": fileDetail['Type'],
                                 "fileName": fileDetail['FileName'], "size": fileDetail['Size']}
        # print(down_request_data)

        sign = getSign("/a/api/file/download_info")

        linkRes = requests.post(down_request_url, headers=self.headerLogined, params={sign[0]: sign[1]},
                                data=down_request_data)
        # print(linkRes.text)
        code = linkRes.json()['code']
        if code != 0:
            print("code = 3 Error:" + str(code))
            # print(linkRes.json())
            return code
        downloadLinkBase64 = linkRes.json()["data"]["DownloadUrl"]
        Base64Url = re.findall("params=(.*)&", downloadLinkBase64)[0]
        # print(Base64Url)
        downLoadUrl = base64.b64decode(Base64Url)
        downLoadUrl = downLoadUrl.decode("utf-8")

        nextToGet = requests.get(downLoadUrl).json()
        redirect_url = nextToGet['data']['redirect_url']
        if showlink:
            print(redirect_url)

        return redirect_url

    def download(self, file_number):
        fileDetail = self.list[file_number]
        downLoadUrl = self.link(file_number, showlink=False)
        name = fileDetail['FileName']  # 文件名
        if os.path.exists(name):
            print("文件 " + name + " 已存在，是否要覆盖？")
            sure = input("输入1覆盖，2取消：")
            if sure != '1':
                return
        down = requests.get(downLoadUrl, stream=True)

        size = int(down.headers['Content-Length'])  # 文件大小
        content_size = int(size)  # 文件总大小
        data_count = 0  # 当前已传输的大小
        if size > 1048576:
            size_print = str(round(size / 1048576, 2)) + "M"
        else:
            size_print = str(round(size / 1024, 2)) + "K"
        print(name + "    " + size_print)
        time1 = time.time()
        time_temp = time1
        data_count_temp = 0
        with open(name, "wb") as f:
            for i in down.iter_content(1024):
                f.write(i)
                done_block = int((data_count / content_size) * 50)
                data_count = data_count + len(i)
                # 实时进度条进度
                now_jd = (data_count / content_size) * 100
                # %% 表示%
                # 测速
                time1 = time.time()
                pass_time = time1 - time_temp
                if pass_time > 1:
                    time_temp = time1
                    pass_data = int(data_count) - int(data_count_temp)
                    data_count_temp = data_count
                    speed = pass_data / int(pass_time)
                    speed_M = speed / 1048576
                    if speed_M > 1:
                        speed_print = str(round(speed_M, 2)) + "M/S"
                    else:
                        speed_print = str(round(speed_M * 1024, 2)) + "K/S"
                    print(
                        "\r [%s%s] %d%%  %s" % (done_block * '█', ' ' * (50 - 1 - done_block), now_jd, speed_print),
                        end="")
                elif data_count == content_size:
                    print("\r [%s%s] %d%%  %s" % (50 * '█', '', 100, ""), end="")
            print("\nok")

    def recycle(self):
        recycle_id = 0
        url = "https://www.123pan.com/a/api/file/list/new?driveId=0&limit=100&next=0&orderBy=fileId&orderDirection=desc&parentFileId=" + str(
            recycle_id) + "&trashed=true&&Page=1"
        recycleRes = requests.get(url, headers=self.headerLogined)
        jsonRecycle = recycleRes.json()
        RecycleList = jsonRecycle['data']['InfoList']
        self.RecycleList = RecycleList

    # fileNumber 从0开始，0为第一个文件，传入时需要减一 ！！！
    def delete_file(self, file, by_num=True, operation=True):
        # operation = 'true' 删除 ， operation = 'false' 恢复
        if by_num:
            if not str(file).isdigit():
                print("请输入数字")
                return -1
            if 0 <= file < len(self.list):
                file_detail = self.list[file]
            else:
                print("不在合理范围内")
                return
        else:
            if file in self.list:
                file_detail = file
            else:
                print("文件不存在")
                return
        dataDelete = {"driveId": 0,
                      "fileTrashInfoList": file_detail,
                      "operation": operation}
        deleteRes = requests.post("https://www.123pan.com/a/api/file/trash", data=json.dumps(dataDelete),
                                  headers=self.headerLogined)
        DeleJson = deleteRes.json()
        print(DeleJson)
        message = DeleJson['message']
        print(message)

    def share(self):
        fileIdList = ""
        share_name_list = []
        add = '1'
        while str(add) == '1':
            share_num = input("分享文件的编号：")
            num_test2 = share_num.isdigit()
            if num_test2:
                share_num = int(share_num)
                if 0 < share_num < len(self.list) + 1:
                    share_id = self.list[int(share_num) - 1]['FileId']
                    share_name = self.list[int(share_num) - 1]['FileName']
                    share_name_list.append(share_name)
                    print(share_name_list)
                    fileIdList = fileIdList + str(share_id) + ","
                    add = input("输入1添加文件，0发起分享，其他取消")
            else:
                print("请输入数字，，")
                add = "1"
        if str(add) == "0":
            sharePwd = input("提取码，不设留空：")
            fileIdList = fileIdList.strip(',')
            data = {"driveId": 0,
                    "expiration": "2024-02-09T11:42:45+08:00",
                    "fileIdList": fileIdList,
                    "shareName": "我的分享",
                    "sharePwd": sharePwd,

                    }
            shareRes = requests.post("https://www.123pan.com/a/api/share/create", headers=self.headerLogined,
                                     data=json.dumps(data))
            shareResJson = shareRes.json()
            message = shareResJson['message']
            print(message)
            ShareKey = shareResJson['data']['ShareKey']
            share_url = 'https://www.123pan.com/s/' + ShareKey
            print('分享链接：\n' + share_url + "提取码：" + sharePwd)
        else:
            print("退出分享")

    def up_load(self, filePath, parentFileId=None, sure=None):
        if parentFileId is None:
            parentFileId = self.parentFileId
            self.cdById(parentFileId)

        filePath = filePath.replace("\"", "")
        filePath = filePath.replace("\\", "/")
        fileName = filePath.split("/")[-1]
        print("文件名:", fileName)
        if not os.path.exists(filePath):
            print("文件不存在，请检查路径是否正确")
            return
        if os.path.isdir(filePath):
            print("暂不支持文件夹上传")
            return
        fsize = os.path.getsize(filePath)
        with open(filePath, 'rb') as f:
            md5 = hashlib.md5()
            while True:
                data = f.read(64 * 1024)
                if not data:
                    break
                md5.update(data)
            readable_hash = md5.hexdigest()

        listUpRequest = {"driveId": 0, "etag": readable_hash, "fileName": fileName,
                         "parentFileId": parentFileId, "size": fsize, "type": 0, "duplicate": 0}

        sign = getSign("/b/api/file/upload_request")
        upRes = requests.post("https://www.123pan.com/b/api/file/upload_request", headers=self.headerLogined,
                              params={sign[0]: sign[1]},
                              data=listUpRequest)
        upResJson = upRes.json()
        code = upResJson['code']
        if code == 5060:
            print("检测到同名文件")
            if sure is None:
                sure = input("检测到1个同名文件,输入1覆盖，2保留两者，0取消：")

            if sure == '1':
                listUpRequest["duplicate"] = 1

            elif sure == '2':
                listUpRequest["duplicate"] = 2
            else:
                print("取消上传")
                return
            sign = getSign("/b/api/file/upload_request")
            upRes = requests.post("https://www.123pan.com/b/api/file/upload_request", headers=self.headerLogined,
                                  params={sign[0]: sign[1]},
                                  data=json.dumps(listUpRequest))
            upResJson = upRes.json()
        code = upResJson['code']
        if code == 0:
            # print(upResJson)
            # print("上传请求成功")
            Reuse = upResJson['data']['Reuse']
            if Reuse:
                print("上传成功，文件已MD5复用")
                return
        else:
            print(upResJson)
            print("上传请求失败")
            return

        bucket = upResJson['data']['Bucket']
        StorageNode = upResJson['data']['StorageNode']
        uploadKey = upResJson['data']['Key']
        uploadId = upResJson['data']['UploadId']
        upFileId = upResJson['data']['FileId']  # 上传文件的fileId,完成上传后需要用到
        print("上传文件的fileId:", upFileId)

        # 获取已将上传的分块
        startData = {"bucket": bucket, "key": uploadKey, "uploadId": uploadId, "storageNode": StorageNode}
        startRes = requests.post("https://www.123pan.com/b/api/file/s3_list_upload_parts", headers=self.headerLogined,
                                 data=json.dumps(startData))
        startResJson = startRes.json()
        code = startResJson['code']
        if code == 0:
            # print(startResJson)
            pass
        else:
            print(startData)
            print(startResJson)

            print("获取传输列表失败")
            return

        # 分块，每一块取一次链接，依次上传
        block_size = 5242880
        with open(filePath, 'rb') as f:
            partNumberStart = 1
            putSize = 0
            while True:
                data = f.read(block_size)

                precent = round(putSize / fsize, 2)
                print("\r已上传：" + str(precent * 100) + "%", end="")
                putSize = putSize + len(data)

                if not data:
                    break
                getLinkData = {"bucket": bucket, "key": uploadKey,
                               "partNumberEnd": partNumberStart + 1,
                               "partNumberStart": partNumberStart,
                               "uploadId": uploadId,
                               "StorageNode": StorageNode}

                getLinkUrl = "https://www.123pan.com/b/api/file/s3_repare_upload_parts_batch"
                getLinkRes = requests.post(getLinkUrl, headers=self.headerLogined, data=json.dumps(getLinkData))
                getLinkResJson = getLinkRes.json()
                code = getLinkResJson['code']
                if code == 0:
                    # print("获取链接成功")
                    pass
                else:
                    print("获取链接失败")
                    # print(getLinkResJson)
                    return
                # print(getLinkResJson)
                uploadUrl = getLinkResJson['data']['presignedUrls'][str(partNumberStart)]
                # print("上传链接",uploadUrl)
                requests.put(uploadUrl, data=data)
                # print("put")

                partNumberStart = partNumberStart + 1

        print("\n处理中")
        # 完成标志
        # 1.获取已上传的块
        uploadedListUrl = "https://www.123pan.com/b/api/file/s3_list_upload_parts"
        uploadedCompData = {"bucket": bucket, "key": uploadKey, "uploadId": uploadId, "storageNode": StorageNode}
        # print(uploadedCompData)
        requests.post(uploadedListUrl, headers=self.headerLogined, data=json.dumps(uploadedCompData))
        compmultipartUpUrl = "https://www.123pan.com/b/api/file/s3_complete_multipart_upload"
        requests.post(compmultipartUpUrl, headers=self.headerLogined,
                      data=json.dumps(uploadedCompData))

        # 3.报告完成上传，关闭upload session
        if fsize > 64 * 1024 * 1024:
            time.sleep(3)
        closeUpSessionUrl = "https://www.123pan.com/b/api/file/upload_complete"
        closeUpSessionData = {"fileId": upFileId}
        # print(closeUpSessionData)
        closeUpSessionRes = requests.post(closeUpSessionUrl, headers=self.headerLogined,
                                          data=json.dumps(closeUpSessionData))
        closeResJson = closeUpSessionRes.json()
        # print(closeResJson)
        code = closeResJson['code']
        if code == 0:
            print("上传成功")
        else:
            print("上传失败")
            print(closeResJson)
            return

    # dirId 就是 fileNumber，从0开始，0为第一个文件，传入时需要减一 ！！！（好像文件夹都排在前面）
    def cd(self, dir_num):
        if not dir_num.isdigit():
            if dir_num == "..":
                if len(self.parentFileList) > 1:
                    self.parentFileList.pop()
                    self.parentFileId = self.parentFileList[-1]
                    self.get_dir()
                    self.show()
                else:
                    print("已经是根目录")
                return
            elif dir_num == "/":
                self.parentFileId = 0
                self.parentFileList = [0]
                self.get_dir()
                self.show()
                return
            else:
                print("输入错误")
                return
        dir_num = int(dir_num) - 1
        if dir_num >= (len(self.list) - 1) or dir_num < 0:
            print("输入错误")
            return
        if self.list[dir_num]['Type'] != 1:
            print("不是文件夹")
            return
        self.parentFileId = self.list[dir_num]['FileId']
        self.parentFileList.append(self.parentFileId)
        self.get_dir()
        self.show()

    def cdById(self, id):

        self.parentFileId = id
        self.parentFileList.append(self.parentFileId)
        self.get_dir()
        self.get_dir()
        self.show()

    def read_ini(self, user_name, pass_word, input_pwd, authorization="", ):
        try:
            with open("123pan.txt", "r") as f:
                text = f.read()
            text = json.loads(text)
            user_name = text['userName']
            pass_word = text['passWord']
            authorization = text['authorization']

        except FileNotFoundError or json.decoder.JSONDecodeError:
            print("read failed")

            if user_name == "" or pass_word == "":
                if input_pwd:

                    user_name = input("userName:")
                    pass_word = input("passWord:")
                    authorization = ""
                else:
                    raise Exception("禁止输入模式下，没有账号或密码")

        self.userName = user_name
        self.passWord = pass_word
        self.authorization = authorization

    def mkdir(self, dirname, parentFileId=None, remake=False):
        if parentFileId:
            if self.parentFileId != parentFileId:
                self.cdById(parentFileId)
        if not remake:
            for i in self.list:
                if i['FileName'] == dirname:
                    print("文件夹已存在")
                    # print(self.list)
                    # print(i)
                    return i['FileId']

        if parentFileId is None:
            parentFileId = self.parentFileId
        url = "https://www.123pan.com/a/api/file/upload_request"
        dataMk = {"driveId": 0, "etag": "", "fileName": dirname, "parentFileId": parentFileId, "size": 0,
                  "type": 1, "duplicate": 1, "NotReuse": True, "event": "newCreateFolder", "operateType": 1}
        sign = getSign("/a/api/file/upload_request")
        resMk = requests.post(url, headers=self.headerLogined, data=json.dumps(dataMk), params={sign[0]: sign[1]})
        try:
            resJson = resMk.json()
        except json.decoder.JSONDecodeError:
            print("创建失败")
            print(resMk.text)
            return
        code = resJson['code']
        if code == 0:
            print("创建成功")
            self.get_dir()
            return resJson["data"]["Info"]["FileId"]
        else:
            print("创建失败")
            print(resJson)
            return
