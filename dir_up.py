import time

from class123 import Pan123
import os
import threading
from concurrent.futures import ThreadPoolExecutor

upload_type = [".py", ".js", ".txt"]

def upload_file(filepath, parent_id):
    pan.up_load(filepath, parent_id,sure="0")

def upload_dir(path, pardir_id=0):
    # 读取文件夹名称
    filePath = path.replace("\"", "")
    filePath = filePath.replace("\\", "/")
    fileName = filePath.split("/")[-1]
    print("文件名:", fileName)
    # 上传文件

    mkdir_list = {path: pardir_id}
    with ThreadPoolExecutor(max_workers=3) as executor:
        for filepath, dirnames, filenames in os.walk(path):
            if "venv" in filepath or ".idea" in filepath or "__pycache__" in filepath:
                continue
            #print(filepath, dirnames, filenames)
            if len(filenames) > 0:
                for filename in filenames:
                    for type in upload_type:
                        if filename.endswith(type):
                            file_path = os.path.join(filepath, filename)
                            executor.submit(upload_file, file_path, mkdir_list[filepath])
                            break

            if len(dirnames) > 0:
                for dirname in dirnames:
                    mk_id = pan.mkdir(dirname, mkdir_list[filepath])
                    time.sleep(0.2)
                    mkdir_list[os.path.join(filepath, dirname)] = mk_id

    print("mkdir_list,", mkdir_list)


if __name__ == "__main__":
    pan = Pan123(readfile=True, input_pwd=True)
    pan.cdById(0)
    mk_id = pan.mkdir("code")
    time.sleep(0.2)
    # upload_dir("demo", mk_id)
    upload_dir("D:\Desktop\coder\code", mk_id)