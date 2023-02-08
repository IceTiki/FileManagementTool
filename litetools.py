# 标准库
import os
import json as _json
import hashlib as _hashlib
import os
import traceback
import sys
from io import TextIOWrapper
import uuid
import time

# 第三方库
import yaml as _yaml  # pyyaml
import py7zr  # py7zr
from Crypto.Cipher import AES  # pycryptodome


class Decorators:
    @staticmethod
    def except_all_error(func):
        def new_func(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(traceback.format_exc())

        return new_func


class FileOut:
    """
    代替stdout和stderr, 使print同时输出到文件和终端中。
    start()方法可以直接用自身(self)替换stdout和stderr
    close()方法可以还原stdout和stderr
    """

    stdout = sys.stdout
    stderr = sys.stderr
    log: str = ""  # 同时将所有输出记录到log字符串中
    logFile: TextIOWrapper = None
    start_time = time.time()

    @classmethod
    def setFileOut(cla, path: str = None):
        """
        设置日志输出文件
        :params path: 日志输出文件路径, 如果为空则取消日志文件输出
        """
        # 关闭旧文件
        if cla.logFile:
            cla.logFile.close()
            cla.logFile = None

        # 更新日志文件输出
        if path:
            try:
                path = os.path.abspath(path)
                logDir = os.path.dirname(path)
                if not os.path.isdir(logDir):
                    os.makedirs(logDir)
                cla.logFile = open(path, "w+", encoding="utf-8")
                cla.logFile.write(cla.log)
                cla.logFile.flush()
                return
            except Exception as e:
                print(2, f"设置日志文件输出失败, 错误信息: [{e}]")
                cla.logFile = None
                return
        else:
            cla.logFile = None
            return

    @classmethod
    def start(cla):
        """开始替换stdout和stderr"""
        if type(sys.stdout) != cla and type(sys.stderr) != cla:
            sys.stdout = cla
            sys.stderr = cla
        else:
            print("sysout/syserr已被替换为FileOut")

    @classmethod
    def write(cla, str_):
        r"""
        :params str: print传来的字符串
        :print(s)等价于sys.stdout.write(s+"\n")
        """
        str_ = str(str_)
        cla.log += str_
        if cla.logFile:
            cla.logFile.write(str_)
        cla.stdout.write(str_)
        cla.flush()

    @classmethod
    def flush(cla):
        """刷新缓冲区"""
        cla.stdout.flush()
        if cla.logFile:
            cla.logFile.flush()

    @classmethod
    def close(cla):
        """关闭"""
        if cla.logFile:
            cla.logFile.close()
        cla.log = ""
        sys.stdout = cla.stdout
        sys.stderr = cla.stderr


class System:
    """独立函数"""

    @staticmethod
    def dir_traversing(path):
        """输入路径，层次遍历返回文件和文件夹的绝对路径列表"""
        fileList = []
        folderlist = []
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                fileDir = os.path.join(root, name)
                fileDir = os.path.abspath(fileDir)
                fileList.append(fileDir)
            for name in dirs:
                folderDir = os.path.join(root, name)
                folderDir = os.path.abspath(folderDir)
                folderlist.append(folderDir)
        return fileList, folderlist

    @staticmethod
    def get_device_id():
        return uuid.getnode()

    @staticmethod
    def get_mac_address():
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        mac = ":".join([mac[e : e + 2] for e in range(0, 11, 2)])
        return mac

    @staticmethod
    def path_join(path, start_path):
        """相对路径转绝对路径(相对稳定, 测试中, 半成品)(os模块中, 无法拼接相对路径和其他盘符的绝对路径)"""  # TODO
        # 检查是否为路径
        if not (
            os.path.isdir(path) or os.path.isdir(start_path) or os.path.isfile(path)
        ):
            raise Exception("error!")
        # 检查起点是否为文件，是：取其目录
        if os.path.isfile(start_path):
            start_path = os.path.dirname(start_path)
        # 检查路径是否为绝对路径，是：返回目录
        if os.path.isabs(path):
            return path

        # 格式化路径
        start_path = os.path.abspath(start_path)
        path = os.path.normpath(path)

        # 检查是否没有追溯上层目录
        for c in path.split("\\")[0]:
            if c != ".":
                return start_path + "\\" + path

        # 追溯上层目录
        path_split = path.split("\\", 1)
        start_path = start_path.split("\\")
        backTimes = len(path_split[0])  # 统计点的数量
        if backTimes > len(start_path):
            raise Exception("error!")
        else:
            relpath_ = ""
            for i in range(len(start_path) - backTimes + 1):
                relpath_ += start_path[i] + "\\"
            if len(path_split) == 1:
                return os.path.normpath(relpath_)
            else:
                relpath_ += path_split[1]
                return os.path.normpath(relpath_)


class YamlRW:
    @staticmethod
    def load(ymlFile="data.yml", encoding="utf-8"):
        """读取Yaml文件"""
        with open(ymlFile, "r", encoding=encoding) as f:
            return _yaml.load(f, Loader=_yaml.FullLoader)

    @staticmethod
    def write(item, ymlFile="data.yml", encoding="utf-8"):
        """写入Yaml文件"""
        with open(ymlFile, "w", encoding=encoding) as f:
            _yaml.dump(item, f, allow_unicode=True)


class JsonRW:
    @staticmethod
    def load(jsonFile="data.json", encoding="utf-8"):
        """读取Json文件"""
        with open(jsonFile, "r", encoding=encoding) as f:
            return _json.load(f)

    @staticmethod
    def write(item, jsonFile="data.json", encoding="utf-8", ensure_ascii=False):
        """写入Json文件"""
        with open(jsonFile, "w", encoding=encoding) as f:
            _json.dump(item, f, ensure_ascii=ensure_ascii)

    @staticmethod
    def any2json(item, *args, **kwargs):
        kwargs.setdefault("ensure_ascii", False)
        return _json.dumps(item, *args, **kwargs)


class Zip_7z_py7zr:
    @staticmethod
    def decompression(zip_path: str, output_folder: str, password: str = None):
        """
        7z解压
        """
        password = password if password else None
        with py7zr.SevenZipFile(zip_path, password=password, mode="r") as z:
            z.extractall(output_folder)

    @staticmethod
    def compression(zip_path: str, input_folder: str, password: str = None):
        """
        7z压缩——默认无压缩。若有密码则使用AES256且加密文件名。
        """
        password = password if password else None
        if password:
            crypyto_kwargs = {
                "header_encryption": True,
                "filters": [
                    {"id": py7zr.FILTER_COPY},
                    {"id": py7zr.FILTER_CRYPTO_AES256_SHA256},
                ],
            }
        else:
            crypyto_kwargs = {
                "header_encryption": False,
                "filters": [{"id": py7zr.FILTER_COPY}],
            }
        with py7zr.SevenZipFile(
            zip_path, password=password, mode="w", **crypyto_kwargs
        ) as z:
            z.writeall(input_folder)

    @staticmethod
    def test(zip_path: str, password: str = None):
        """测试压缩包中各个文件的CRC值"""
        password = password if password else None
        with py7zr.SevenZipFile(zip_path, password=password, mode="r") as z:
            return z.test()


class Hash:
    """Hashing String And File"""

    @staticmethod
    def geneHashObj(hash_type):
        if hash_type == 1:
            return _hashlib.sha1()
        elif hash_type == 224:
            return _hashlib.sha224()
        elif hash_type == 256:
            return _hashlib.sha256()
        elif hash_type == 384:
            return _hashlib.sha384()
        elif hash_type == 512:
            return _hashlib.sha512()
        elif hash_type == 5:
            return _hashlib.md5()
        elif hash_type == 3.224:
            return _hashlib.sha3_224()
        elif hash_type == 3.256:
            return _hashlib.sha3_256()
        elif hash_type == 3.384:
            return _hashlib.sha3_384()
        elif hash_type == 3.512:
            return _hashlib.sha3_512()
        else:
            raise Exception("类型错误, 初始化失败")

    @staticmethod
    def fileHash(path, hash_type):
        """计算文件哈希
        :param path: 文件路径
        :param hash_type: 哈希算法类型
            1       sha-1
            224     sha-224
            256      sha-256
            384     sha-384
            512     sha-512
            5       md5
            3.256   sha3-256
            3.384   sha3-384
            3.512   sha3-512
        """
        hashObj = Hash.geneHashObj(hash_type)
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    for byte_block in iter(lambda: f.read(1048576), b""):
                        hashObj.update(byte_block)
                    return hashObj.hexdigest()
            except Exception as e:
                raise Exception("%s计算哈希出错: %s" % (path, e))
        else:
            raise Exception('路径错误, 没有指向文件: "%s"')

    @staticmethod
    def strHash(str_: str, hash_type, charset="utf-8"):
        """计算字符串哈希
        :param str_: 字符串
        :param hash_type: 哈希算法类型
        :param charset: 字符编码类型
            1       sha-1
            224     sha-224
            256      sha-256
            384     sha-384
            512     sha-512
            5       md5
            3.256   sha3-256
            3.384   sha3-384
            3.512   sha3-512
        """
        hashObj = Hash.geneHashObj(hash_type)
        bstr = str_.encode(charset)
        hashObj.update(bstr)
        return hashObj.hexdigest()

    @staticmethod
    def bytesHash(bytes_: bytes, hash_type):
        """计算字节串哈希
        :param bytes_: 字节串
        :param hash_type: 哈希算法类型
            1       sha-1
            224     sha-224
            256      sha-256
            384     sha-384
            512     sha-512
            5       md5
            3.256   sha3-256
            3.384   sha3-384
            3.512   sha3-512
        """
        hashObj = Hash.geneHashObj(hash_type)
        hashObj.update(bytes_)
        return hashObj.hexdigest()


class StandardAesStringCrypto:
    """
    在线加密解密见https://www.ssleye.com/aes_cipher.html
    key: sha256(secret_key)[0:32]
    iv: sha256(secret_key)[32:48]
    mode: CBC
    padding: pkcs7padding
    charset: utf-8
    encode: Hex
    """

    def __init__(self, secret_key: str):
        """
        :param secret_key: 密钥
        """
        self.charset = "utf-8"

        hash = _hashlib.sha256()
        hash.update(secret_key.encode(self.charset))
        keyhash = hash.hexdigest()
        self.key = keyhash[0:32]
        self.iv = keyhash[32:48]
        self.key = self.key.encode(self.charset)
        self.iv = self.iv.encode(self.charset)

    def encrypt(self, text):
        """加密"""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

        text = self.pkcs7padding(text)  # 填充
        text = text.encode(self.charset)  # 编码
        text = cipher.encrypt(text)  # 加密
        text = text.hex()  # Hex编码
        return text

    def decrypt(self, text):
        """解密"""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

        text = bytes.fromhex(text)  # Hex解码
        text = cipher.decrypt(text)  # 解密
        text = text.decode(self.charset)  # 解码
        text = self.pkcs7unpadding(text)  # 删除填充
        return text

    def pkcs7padding(self, text: str):
        """明文使用PKCS7填充"""
        remainder = 16 - len(text.encode(self.charset)) % 16
        return str(text + chr(remainder) * remainder)

    def pkcs7unpadding(self, text: str):
        """去掉填充字符"""
        return text[:-ord(text[-1])]


class ProcessStatus:
    def __init__(self):
        self.old_msg = ""

    def rewritemsg(self, msg: str = ""):
        '''重写旧句子(似乎只支持ascii)'''
        msg = str(msg)
        old_msg_len = len(self.old_msg)
        for letter in self.old_msg:  # 检测长宽度中文字符
            if (letter >= '\u4e00' and letter <= '\u9fa5') or letter in ['；', '：', '，', '（', '）', '！', '？', '—', '…', '、', '》', '《']:
                old_msg_len += 1
        clean = "\b"*old_msg_len + " "*old_msg_len + "\b" * old_msg_len  # 清除上一帧进度条
        print(clean+msg, end="", flush=True)
        self.old_msg = msg
