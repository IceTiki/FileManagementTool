# 标准库
import os as _os
import json as _json
import hashlib as _hashlib
import traceback as _traceback
import sys as _sys
import io as _io
import uuid as _uuid
import time as _time
import sqlite3 as _sqlite3
import re as _re
import typing as _typing

# 第三方库
import yaml as _yaml  # pyyaml
import py7zr  # py7zr
from Crypto.Cipher import AES  # pycryptodome


class Decorators:
    @staticmethod
    def except_all_error(func):
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(_traceback.format_exc())

        return new_func


class FileOut:
    """
    代替stdout和stderr, 使print同时输出到文件和终端中。
    start()方法可以直接用自身(self)替换stdout和stderr
    close()方法可以还原stdout和stderr
    """

    stdout = _sys.stdout
    stderr = _sys.stderr
    log: str = ""  # 同时将所有输出记录到log字符串中
    logFile: _io.TextIOWrapper = None
    start_time = _time.time()

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
                path = _os.path.abspath(path)
                logDir = _os.path.dirname(path)
                if not _os.path.isdir(logDir):
                    _os.makedirs(logDir)
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
        if type(_sys.stdout) != cla and type(_sys.stderr) != cla:
            _sys.stdout = cla
            _sys.stderr = cla
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
        _sys.stdout = cla.stdout
        _sys.stderr = cla.stderr


class System:
    """独立函数"""

    @staticmethod
    def dir_traversing(path):
        """输入路径，层次遍历返回文件和文件夹的绝对路径列表"""
        fileList = []
        folderlist = []
        for root, dirs, files in _os.walk(path, topdown=False):
            for name in files:
                fileDir = _os.path.join(root, name)
                fileDir = _os.path.abspath(fileDir)
                fileList.append(fileDir)
            for name in dirs:
                folderDir = _os.path.join(root, name)
                folderDir = _os.path.abspath(folderDir)
                folderlist.append(folderDir)
        return fileList, folderlist

    @staticmethod
    def get_device_id():
        return _uuid.getnode()

    @staticmethod
    def get_mac_address():
        mac = _uuid.UUID(int=_uuid.getnode()).hex[-12:]
        mac = ":".join([mac[e : e + 2] for e in range(0, 11, 2)])
        return mac

    @staticmethod
    def path_join(path, start_path):
        """相对路径转绝对路径(相对稳定, 测试中, 半成品)(os模块中, 无法拼接相对路径和其他盘符的绝对路径)"""  # TODO
        # 检查是否为路径
        if not (
            _os.path.isdir(path) or _os.path.isdir(start_path) or _os.path.isfile(path)
        ):
            raise Exception("error!")
        # 检查起点是否为文件，是：取其目录
        if _os.path.isfile(start_path):
            start_path = _os.path.dirname(start_path)
        # 检查路径是否为绝对路径，是：返回目录
        if _os.path.isabs(path):
            return path

        # 格式化路径
        start_path = _os.path.abspath(start_path)
        path = _os.path.normpath(path)

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
                return _os.path.normpath(relpath_)
            else:
                relpath_ += path_split[1]
                return _os.path.normpath(relpath_)


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
        if _os.path.isfile(path):
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
        return text[: -ord(text[-1])]


class DbOperator(_sqlite3.Connection):
    """
    python中SQL语句特性
    ---
    - 表、列名不能用?占位符
    - select中, 列名如果用""括起来, 就会被识别为字符串值, 返回结果时不会返回列对应的值, 而是该字符串。填入其他值同理。
    """

    SQLITE_KEYWORD_SET = set(
        "ABORT ACTION ADD AFTER ALL ALTER ANALYZE AND AS ASC ATTACH AUTOINCREMENT BEFORE BEGIN BETWEEN BY CASCADE CASE CAST CHECK COLLATE COLUMN COMMIT CONFLICT CONSTRAINT CREATE CROSS CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP DATABASE DEFAULT DEFERRABLE DEFERRED DELETE DESC DETACH DISTINCT DROP EACH ELSE END ESCAPE EXCEPT EXCLUSIVE EXISTS EXPLAIN FAIL FOR FOREIGN FROM FULL GLOB GROUP HAVING IF IGNORE IMMEDIATE IN INDEX INDEXED INITIALLY INNER INSERT INSTEAD INTERSECT INTO IS ISNULL JOIN KEY LEFT LIKE LIMIT MATCH NATURAL NO NOT NOTNULL NULL OF OFFSET ON OR ORDER OUTER PLAN PRAGMA PRIMARY QUERY RAISE RECURSIVE REFERENCES REGEXP REINDEX RELEASE RENAME REPLACE RESTRICT RIGHT ROLLBACK ROW SAVEPOINT SELECT SET TABLE TEMP TEMPORARY THEN TO TRANSACTION TRIGGER UNION UNIQUE UPDATE USING VACUUM VALUES VIEW VIRTUAL WHEN WHERE WITH WITHOUT".split(
            " "
        )
    )

    @classmethod
    def check_name_normal(cls, name: str):
        """检查名字仅含[a-zA-Z0-9_]且并非关键字"""
        if name.upper() in cls.SQLITE_KEYWORD_SET:
            return False
        if not _re.match(r"^\w+$", name):
            return False
        return True

    def __init__(
        self,
        database: str | bytes | _os.PathLike[str] | _os.PathLike[bytes],
        *args,
        **kwargs,
    ):
        """
        database: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        timeout: float = ...,
        detect_types: int = ...,
        isolation_level: str | None = ...,
        check_same_thread: bool = ...,
        factory: type[sqlite3.Connection] | None = ...,
        cached_statements: int = ...,
        uri: bool = ...,
        """
        super().__init__(database, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def table_list(self) -> list[str]:
        """
        Returns
        ---
        表名列表
        """
        sentence = "SELECT NAME FROM SQLITE_MASTER WHERE TYPE='table' ORDER BY NAME"  # SQLITE_MASTER不区分大小写, table必须为小写
        return [i[0] for i in self.cursor_execute(sentence)]

    def get_table_info(self, tbl_name: str):
        """
        获取表详情

        Warning: 没有对传入参数进行检查, 有sql注入风险
        """
        res = self.execute(f"PRAGMA table_info('{tbl_name}')")
        return list(res.fetchall())

    def try_exe(self, *args, **kwargs) -> _sqlite3.Cursor:
        """execute的自动commit版本, 如果出错会自动rollback"""
        try:
            result = self.execute(*args, **kwargs)
            self.commit()
            return result
        except Exception as e:
            self.rollback()
            raise e

    def try_exemany(self, *args, **kwargs) -> _sqlite3.Cursor:
        """executemany的自动commit版本, 如果出错会自动rollback"""
        try:
            result = self.executemany(*args, **kwargs)
            self.commit()
            return result
        except Exception as e:
            self.rollback()
            raise e

    def create_table(self, table: str, columns: list[tuple[str]]) -> _sqlite3.Cursor:
        """
        创建表(如果表已存在, 则不执行创建)

        Warning: 没有对传入参数进行检查, 有sql注入风险

        Parameters
        ---
        table : str
            表名
        columns : list[tuple[str]]
            列属性, 应为(name, type, *constraints)
        """

        def fcolumn(column: tuple[str]):
            column = tuple(column)
            return f"'{column[0]}' " + " ".join(column[1:])

        columns = ",\n".join(map(fcolumn, columns))

        sentence = f"CREATE TABLE IF NOT EXISTS '{table}' ({columns});"
        return self.try_exe(sentence)

    def select(
        self,
        table: str,
        column_name: str | _typing.Iterable[str] = "*",
        clause: str = "",
    ) -> _sqlite3.Cursor:
        """
        查询

        Warning: 没有对传入参数进行检查, 有sql注入风险

        Parameters
        ---
        table : str
            表名
        column_name : str | typing.Iterable[str], default = "*"
            列名
        clause : str
            子句(比如WHERE ORDER等)
        """
        if isinstance(column_name, str):
            if column_name == "*":
                pass
            else:
                column_name = f"{column_name}"
        elif isinstance(column_name, _typing.Iterable):
            column_name = ", ".join((f"{i}" for i in column_name))

        sentence = f"""SELECT {column_name} FROM {table} {clause};"""
        return self.execute(sentence)

    def insert_many(
        self,
        table: str,
        column_name: str | _typing.Iterable[str],
        data: list[tuple[_typing.Any]],
        clause: str = "",
    ) -> _sqlite3.Cursor:
        """
        插入

        Warning: 没有对传入参数进行检查, 有sql注入风险

        Parameters
        ---
        table : str
            表名
        column_name : str | Iterable[str]
            列名
        data : list[tuple[Any]]
            tuple[Any]代表单行数据包装为一个元组
        clause : str
            子句
        """
        if isinstance(column_name, str):
            column_name = f"('{column_name}')"
            placeholder = "(?)"
        elif isinstance(column_name, _typing.Iterable):
            placeholder = "(" + ", ".join(map(lambda x: "?", column_name)) + ")"
            column_name = ", ".join((f"'{i}'" for i in column_name))
            column_name = f"({column_name})"

        sentence = f"INSERT INTO '{table}' {column_name} VALUES {placeholder} {clause};"
        return self.try_exemany(sentence, data)

    _update = "UPDATE table SET column_name1 = ? where column_name2 = ?;"
