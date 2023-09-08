import re as _re
import typing as _typing
import random as _random
import shutil as _shutil
import hashlib as _hashlib
import pathlib as _pathlib
import typing as _typing
import os as _os
import time as _time
import functools as _functools

from . import litetools as _lt

import loguru as _loguru
import tqdm as _tqdm


VERSION = "1.1.0"


class FolderStatus:
    path_sta = tuple[str, bool, str, int]
    list_sta = list[path_sta]
    varience = tuple[str, bool, str, int, float, bool]
    list_varience = list[varience]

    def __init__(
        self,
        folder_path: str | _pathlib.Path = "",
        dbpath: str | _pathlib.Path = "status.db",
    ) -> None:
        """
        Parameters
        ---
        folder_path : str | _pathlib.Path = ""
            文件夹路径
        dbpath : str | _pathlib.Path = "status.db"
            数据路径
        """
        self.__root = _pathlib.Path(folder_path).absolute()
        self.__dbpath = _pathlib.Path(dbpath).absolute()

    @staticmethod
    def __gene_varience(
        list_old: list_sta, list_new: list_sta, time_: float = _time.time()
    ) -> list_varience:
        """
        获取两个列表的变化, 返回变化
        Parameters
        ---
        list_old, list_new : typing.Sequence
            旧列表和新列表
        """
        set_old = set(list_old)
        set_new = set(list_new)
        added = set_new.difference(set_old)
        deleted = set_old.difference(set_new)
        added = [i + (time_, True) for i in added]
        deleted = [i + (time_, False) for i in deleted]
        varience = added + deleted
        varience.sort()
        return varience

    @staticmethod
    @_loguru.logger.catch
    def _file_sha256(file_path: _pathlib.Path) -> str | None:
        """
        Parameters
        ---
        file_path : _pathlib.Path
            指向文件的路径

        Returns
        ---
        如果计算出错返回None, 否则返回sha256(Hex编码)
        """
        hashobj = _hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(1048576), b""):
                hashobj.update(byte_block)
            return hashobj.hexdigest()

    @staticmethod
    @_loguru.logger.catch
    def __file_size(file_path: _pathlib.Path) -> str | None:
        """
        Parameters
        ---
        file_path : _pathlib.Path
            指向文件的路径

        Returns
        ---
        如果计算出错返回None, 否则返回文件大小
        """
        return file_path.stat().st_size

    @staticmethod
    def find_fmi(folder_path: _pathlib.Path) -> _pathlib.Path:
        """
        优先查找名为".fmi"的文件夹, 其次查找名为".fmi_[id-8/12/16]"的文件夹
        如果未能找到唯一fmi文件夹, 则报错

        Raises
        ---
        OSError
        """
        folder_path = folder_path.absolute()
        assert folder_path.is_dir()

        if match_ := _re.match(
            r".*_([a-zA-Z0-9]{8}(?:[a-zA-Z0-9]{4})?(?:[a-zA-Z0-9]{4})?)",
            folder_path.name,
        ):
            may_id = match_.group(1)
        else:
            may_id = None

        fmi_list = [
            i for i in folder_path.iterdir() if i.is_dir() and i.name[:4] == ".fmi"
        ]
        match len(fmi_list):
            case 0:
                raise OSError("未能找到.fmi文件")
            case 1:
                return fmi_list.pop()
            case _:
                for i in fmi_list:
                    if i.name == ".fmi":
                        return i

                for i in fmi_list:
                    if match_ := _re.match(
                        r"\.fmi_([a-zA-Z0-9]{8}(?:[a-zA-Z0-9]{4})?(?:[a-zA-Z0-9]{4})?)",
                        i.name,
                    ):
                        if may_id == match_.group(1):
                            return i

                raise OSError("未能确定.fmi文件夹")

    @_loguru.logger.catch
    def __path_status(self, path: _pathlib.Path) -> path_sta:
        relpath: str = str(path.relative_to(self.__root))
        if path.is_file():
            return (relpath, True, self._file_sha256(path), self.__file_size(path))
        else:
            return (relpath, False, None, None)

    @property
    def iterdirs(self) -> _typing.Generator[_pathlib.Path, None, None]:
        """
        遍历文件夹中的文件或文件夹的生成器(生成绝对路径)

        Yields
        ---
        item : pathlib.Path
            文件夹内的文件/文件夹的绝对路径
        """
        for root, dirs, files in _os.walk(self.__root):
            root = _pathlib.Path(root)
            for name in files + dirs:
                item_dir: _pathlib.Path = root / name
                item_dir = item_dir.absolute()
                yield item_dir

    @property
    def __gene_update_info(self):
        """TIME ROOT MAC COMMENT VERSION"""
        return (
            _time.time(),
            str(self.__root),
            _lt.System.get_mac_address(),
            "",
            VERSION,
        )

    @property
    @_functools.cache
    def __folder_status(self) -> list_sta:
        path_seq = _tqdm.tqdm(
            list(self.iterdirs), desc=f"扫描文件夹'{self.__root.name}'内项目", mininterval=1
        )
        sta = [self.__path_status(path) for path in path_seq]
        sta.sort()
        return sta

    def __create_database(self) -> _lt.Decorators:
        """创建数据库"""
        dbpath = self.__dbpath
        _loguru.logger.info("创建数据库")
        db = _lt.DbOperator(dbpath)
        _loguru.logger.info("    初始化数据库表")
        # 创建STATUS表, 记录当前文件夹状态
        # PATH ISFILE SHA256 SIZE
        db.create_table(
            "STATUS",
            [
                ("PATH", "TEXT", "NOT NULL"),
                ("ISFILE", "TINYINT", "NOT NULL"),
                ("SHA256", "CHARACTER(64)"),
                ("SIZE", "BIGINT"),
            ],
        )
        # 创建INFO表, 每次更新数据库的信息, 最新的一次对应STATUS表的信息
        # TIME ROOT MAC COMMENT VERSION
        db.create_table(
            "INFO",
            [
                ("TIME", "DOUBLE", "NOT NULL"),
                ("ROOT", "TEXT"),
                ("MAC", "TEXT"),
                ("COMMENT", "TEXT"),
                ("VERSION", "TEXT"),
            ],
        )
        # 创建VARIANCE表, 记录每次更新, 文件夹内的文件增减情况
        # PATH ISFILE SHA256 SIZE TIME STATUS
        # TIME与INFO最新项一致
        # STATUS是布尔值, True代表新增的文件/文件夹, False代表删去的文件/文件夹
        db.create_table(
            "VARIANCE",
            [
                ("PATH", "TEXT", "NOT NULL"),
                ("ISFILE", "TINYINT", "NOT NULL"),
                ("SHA256", "CHARACTER(64)"),
                ("SIZE", "BIGINT"),
                ("TIME", "DOUBLE", "NOT NULL"),
                ("CHANGE", "TINYINT", "NOT NULL"),
            ],
        )
        # 载入基本数据
        _loguru.logger.info("    初始化数据库基础数据")
        db.insert_many(
            "STATUS", ["PATH", "ISFILE", "SHA256", "SIZE"], self.__folder_status
        )
        db.insert_many(
            "INFO",
            ["TIME", "ROOT", "MAC", "COMMENT", "VERSION"],
            [self.__gene_update_info],
        )
        _loguru.logger.info("    完成")
        return db

    def update_database(self) -> _lt.Decorators:
        if self.__dbpath.is_file():
            db = _lt.DbOperator(self.__dbpath)
        else:
            db = self.__create_database()
            return db
        info = self.__gene_update_info
        update_time = info[0]

        _loguru.logger.info("更新数据库")
        _loguru.logger.info("    载入数据库内旧的文件夹状态数据")
        old_folder_status: self.list_sta = db.select("STATUS")
        _loguru.logger.info("    扫描文件夹变动")
        varience = self.__gene_varience(
            old_folder_status, self.__folder_status, update_time
        )

        # 更新表
        _loguru.logger.info("    更新VARIANCE表")
        db.insert_many(
            "VARIANCE", ["PATH", "ISFILE", "SHA256", "TIME", "CHANGE"], varience
        )
        _loguru.logger.info("    更新STATUS表")
        db.insert_many(
            "STATUS", ["PATH", "ISFILE", "SHA256", "SIZE"], self.__folder_status
        )
        _loguru.logger.info("    更新INFO表")
        db.insert_many(
            "INFO",
            ["TIME", "ROOT", "MAC", "COMMENT", "VERSION"],
            [info],
        )

        _loguru.logger.info("    完成")
        return db


class AutoUpdate:
    """半成品, 用于更新旧版的idx"""

    def __init__(self, folder_path=".\\"):
        self.folder_path = folder_path
        for path in _os.listdir(folder_path):
            if _re.match(r"^.*\.fileManagement_Index[\\\/]?$", path):
                VERSION = "alpha"
                self.idx_path = path
                self.alpha_update()
                break

    def idx_item(self, path):
        """基于索引文件夹的路径, 获取内部文件的路径"""
        return _os.path.join(self.idx_path, path)

    def alpha_update(self):
        # index
        def index_replace(match: _re.Match):
            if match.group() == "fileManagement_version":
                return "file_management_version"
            elif match.group() == "uuid":
                return "id"
            elif match.group() == "exid":
                return "status_id"
            else:
                return match.group()

        def index_replace2(match: _re.Match):
            if match.group(2) == "创建者(邮箱)":
                return match.group(1) + "创建者"
            elif match.group(2) == "识别号":
                return match.group(1) + "对象识别号"
            elif match.group(2) == "128位16进制(小写字母)随机字符串，识别号创建/改变时随机生成":
                return match.group(1) + "对象状态识别号——128位16进制(小写字母)随机字符串，在创建/更新对象时随机生成"
            else:
                return match.group()

        with open(self.idx_item("index.yml"), "r", encoding="utf-8") as f:
            text = f.read()
            text = text.replace(
                "fileManagement_version: '1.0.0'",
                "file_management_version: '1.0.0-beta'",
            )
            text = _re.sub(r"^\w*", index_replace, text, flags=_re.M)
            text = _re.sub(r"(# )(.*)$", index_replace2, text, flags=_re.M)
        with open(self.idx_item("index.yml"), "w", encoding="utf-8") as f:
            f.write(text)

        # status
        status_path = self.idx_item("status.yml")
        if _os.path.isfile(status_path):
            old_data = _lt.YamlRW.load(status_path)
            old_data_info = old_data["status"]["info"]
            new_data = {
                "meta": {
                    "version": "1.0.0",
                },
                "status": {
                    "abstract": {
                        "generated_time": old_data_info["generatedTime"],
                        "folder_amount": old_data_info["folderAmount"],
                        "file_amount": old_data_info["fileAmount"],
                        "folder_size": old_data_info["amountSize"],
                        "folder_path": old_data_info["rootAbsPath"],
                        "mac_address": old_data_info["mac"],
                    },
                    "files": old_data["status"]["fileStatusList"],
                    "folders": old_data["status"]["folderStatusList"],
                },
            }
            _lt.YamlRW.write(new_data, status_path)

        # history
        history_path = self.idx_item("history.yml")
        if _os.path.isfile(history_path):
            old_data = _lt.YamlRW.load(history_path)
            old_data_history = [
                {
                    "file_added": i.get("filesAdded", []),
                    "file_deleted": i.get("filesDeleted", []),
                    "folder_added": i.get("foldersAdded", []),
                    "folder_deleted": i.get("foldersDeleted", []),
                    "folder_path": i["rootAbsPath"],
                    "generated_time": i["generatedTime"],
                    "mac": i["mac"],
                    "notion": i["notion"],
                }
                for i in old_data
            ]
            new_data = {
                "meta": {
                    "version": "1.0.0",
                },
                "history": old_data_history,
            }
            _lt.YamlRW.write(new_data, history_path)

        # 文件夹改名
        idx_data = _lt.YamlRW.load(self.idx_item("index.yml"))
        self.idx_path = _os.path.normpath(self.idx_path)
        new_idx_name = f".fmi_{idx_data['id']}"
        new_idx_name = _os.path.join(_os.path.dirname(self.idx_path), new_idx_name)
        _os.rename(self.idx_path, new_idx_name)
        self.idx_path = new_idx_name

    @staticmethod
    def yml2db_1_1_0(fmi_path: str | _pathlib.Path):
        fmi_path: _pathlib.Path = _pathlib.Path(fmi_path)
        status: str | _pathlib.Path = fmi_path / "status.yml"
        history: str | _pathlib.Path = fmi_path / "history.yml"
        db_path: str | _pathlib.Path = fmi_path / "status.db"
        status_data = _lt.YamlRW.load(status)["status"]
        history_data = _lt.YamlRW.load(history)

        db_sta = []
        for i in status_data["files"]:
            i: str
            i = i.split("|-|")
            db_sta.append((i[0], True, i[1], int(i[2])))
        for i in status_data["folders"]:
            i: str
            db_sta.append((i, False, None, None))

        db_var = []
        for i in history_data["history"]:
            time_ = _time.mktime(
                _time.strptime(i["generated_time"], "%Y-%m-%d %H:%M:%S")
            )
            for j in i["file_added"]:
                # PATH ISFILE SHA256 SIZE TIME STATUS
                j = j.split("|-|")
                db_var.append((j[0], True, j[1], int(j[2]), time_, True))
            for j in i["file_deleted"]:
                # PATH ISFILE SHA256 SIZE TIME STATUS
                j = j.split("|-|")
                db_var.append((j[0], True, j[1], int(j[2]), time_, False))
            for j in i["folder_added"]:
                # PATH ISFILE SHA256 SIZE TIME STATUS
                j = j.split("|-|")
                db_var.append((j[0], False, None, None, time_, True))
            for j in i["folder_deleted"]:
                # PATH ISFILE SHA256 SIZE TIME STATUS
                j = j.split("|-|")
                db_var.append((j[0], False, None, None, time_, False))

        db_info = []
        for i in history_data["history"]:
            # TIME ROOT MAC COMMENT VERSION
            time_ = _time.mktime(
                _time.strptime(i["generated_time"], "%Y-%m-%d %H:%M:%S")
            )
            db_info.append((time_, i["folder_path"], i["mac"], i["notion"], "1.1.0"))

        sta_ab = status_data["abstract"]
        time_ = _time.mktime(
            _time.strptime(sta_ab["generated_time"], "%Y-%m-%d %H:%M:%S")
        )
        db_info.append(
            (time_, sta_ab["folder_path"], sta_ab["mac_address"], "", "1.1.0")
        )

        db = _lt.DbOperator(db_path)

        db.create_table(
            "STATUS",
            [
                ("PATH", "TEXT", "NOT NULL"),
                ("ISFILE", "TINYINT", "NOT NULL"),
                ("SHA256", "CHARACTER(64)"),
                ("SIZE", "BIGINT"),
            ],
        )
        # 创建INFO表, 每次更新数据库的信息, 最新的一次对应STATUS表的信息
        # TIME ROOT MAC COMMENT VERSION
        db.create_table(
            "INFO",
            [
                ("TIME", "DOUBLE", "NOT NULL"),
                ("ROOT", "TEXT"),
                ("MAC", "TEXT"),
                ("COMMENT", "TEXT"),
                ("VERSION", "TEXT"),
            ],
        )
        # 创建VARIANCE表, 记录每次更新, 文件夹内的文件增减情况
        # PATH ISFILE SHA256 SIZE TIME STATUS
        # TIME与INFO最新项一致
        # STATUS是布尔值, True代表新增的文件/文件夹, False代表删去的文件/文件夹
        db.create_table(
            "VARIANCE",
            [
                ("PATH", "TEXT", "NOT NULL"),
                ("ISFILE", "TINYINT", "NOT NULL"),
                ("SHA256", "CHARACTER(64)"),
                ("SIZE", "BIGINT"),
                ("TIME", "DOUBLE", "NOT NULL"),
                ("CHANGE", "TINYINT", "NOT NULL"),
            ],
        )

        db.insert_many("STATUS", ["PATH", "ISFILE", "SHA256", "SIZE"], db_sta)
        db.insert_many(
            "VARIANCE", ["PATH", "ISFILE", "SHA256", "SIZE", "TIME", "CHANGE"], db_var
        )
        db.insert_many(
            "INFO",
            ["TIME", "ROOT", "MAC", "COMMENT", "VERSION"],
            db_info,
        )


class FMcmd:
    all_commands: dict = {}

    def __init__(self):
        pass

    def repository_assets(self, filename: str):
        return _os.path.join(_os.path.dirname(__file__), "assets", filename)

    @property
    def work_dir(self):
        return _os.getcwd()

    def get_input(self, message=""):
        return input(f"● {self.work_dir}●{message}> ")

    def start(self):
        """开始执行循环"""
        print("发送「help」获取帮助")
        while 1:
            # 输入内容
            inp = input(f"● {self.work_dir}> ")
            # 解析内容
            if _re.match(r"\w* .*", inp):
                inp: _re.Match = _re.search("^(\w*) (.*)", inp)
                command = inp.group(1)
                content = inp.group(2)
            else:
                command = inp
                content = ""
            # 命令执行
            if command in ("exit", "quit"):
                break
            elif command in self.all_commands:
                method: _typing.Callable = self.all_commands[command]["method"]
                method(self, content)
            else:
                print("未知命令")

    """
    在类初始化过程中, 类当然不可能实例化。所以调用时候也不会传入self。
    而这些函数在 (初始化过程中, 实例化之前) 就被修改并加入到all_commands中, 
    在后续调用中, 其实不是调用实例化对象中的方法, 而是all_commands字典里面的方法。
    这些方法在加入all_commands时 (初始化过程中, 实例化之前) , 还不需要self参数, 而且修饰器也没有把self传递进去,
    所以调用时需要手动传入self。
    """

    def set_command(
        command: str = "command",
        document: str = "no document",
        all_commands=all_commands,
    ):
        """返回装饰器, 为函数绑定命令"""

        def decorator(method: _typing.Callable) -> _typing.Callable:
            """将命令绑定的方法, 添加到命令列表中"""
            all_commands[command] = {"method": method, "document": document}
            return method

        return decorator

    def set_document(
        command: str, document: str = "no document", all_commands=all_commands
    ):
        """更改对应命令的文档"""
        if command not in all_commands:
            all_commands[command] = {"method": lambda x: x, "document": "no document"}
        all_commands[command]["document"] = document

    @staticmethod
    def content_resolution(content) -> tuple[list, dict]:
        """
        [测试中!!!]
        -m asd asdasd -c "ass" 解析为['asdasd']和{'m': 'asd', 'c': 'ass'}
        """
        content_pattern = r"(?:\"[^\"]*\"|[^- ][^ ]*)"
        pattern = r"(?:-(?P<key>\w+)(?: (?:\"(?P<value_1>[^\"]*)\"|(?P<value_2>[^- ][^ ]*)))?)|(?:(?:\"(?P<content_1>[^\"]*)\"|(?P<content_2>[^- ][^ ]*)))"
        result = _re.finditer(pattern, content)
        args = []
        kwargs = {}
        for i in result:
            i = i.groupdict()
            if i["key"] != None:
                key = i["key"]
                if i["value_1"] != None:
                    kwargs[key] = i["value_1"]
                else:
                    kwargs[key] = i["value_2"]
            else:
                if i["content_1"] != None:
                    args.append(i["content_1"])
                else:
                    args.append(i["content_2"])
        return args, kwargs

    # ====================基本命令====================

    @set_command("help", "帮助")
    def help(self, content):
        if not content:
            all_command_help = "\n".join(
                [f"「{k}」\n{v['document']}" for k, v in self.all_commands.items()]
            )
            print(
                f"""====================help====================
{all_command_help}
「exit」「quit」
退出
====================help===================="""
            )
        elif content in self.all_commands:
            print(self.all_commands[content]["document"])
        else:
            print("未知命令")

    @set_command(command="cd", document="改变工作路径")
    @_lt.Decorators.except_all_error
    def cd(self, content):
        _os.chdir(content)

    @set_command(command="edit", document="编辑tikifm")
    def edit(self, content):
        _os.startfile(__file__)

    # ====================附加命令====================

    # @set_command(command="command", document="document")
    # def f(self, content):
    #     pass

    @set_command(command="init", document="新建fm对象")
    def fm_init(self, content):
        fmo_name = input("请输入对象名\n>")
        fmo_id_len = input("请输入对象类型(子对象:8|可变对象:12|不可变对象:16)\n>")
        fm_ver = "1.0.0-beta"
        print("fm_ver: 1.0.0-beta")
        # 生成基本信息
        fmo_id = str().join(
            _random.choices(
                "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                k=int(fmo_id_len),
            )
        )
        fmo_exid = str().join(_random.choices("0123456789abcdef", k=128))
        fmo_dir = _lt.System.path_join(f"{fmo_name}_{fmo_id}", self.work_dir)
        fmo_inx_dir = _os.path.join(fmo_dir, f".fmi_{fmo_id}")
        fmo_created_time = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime())

        _os.makedirs(fmo_inx_dir)

        file_index_content = f"""file_management_version: '{fm_ver}' # 文件管理的版本
title: '{fmo_name}' # 标题
description: '' # 对此区域的描述
creator: '' # 创建者
created_time: '{fmo_created_time}' # 创建时间(格式 YYYY-MM-DD HH:MM:SS)
id: '{fmo_id}' # 对象识别号
status_id: '{fmo_exid}' # 对象状态识别号——128位16进制(小写字母)随机字符串，在创建/更新对象时随机生成"""
        with open(_os.path.join(fmo_inx_dir, "index.yml"), "w", encoding="utf-8") as f:
            f.write(file_index_content)

        _shutil.copy2(
            self.repository_assets(
                "file_management_index_folder_template\\tag_list.yml"
            ),
            _os.path.join(fmo_inx_dir, "tag_list.yml"),
        )
        _shutil.copy2(
            self.repository_assets(
                "file_management_index_folder_template\\tag_extension.yml"
            ),
            _os.path.join(fmo_inx_dir, "tag_extension.yml"),
        )

        fs = FolderStatus(fmo_dir)
        fs.update_data(
            data_dir=_os.path.join(fmo_inx_dir, "status.yml"),
            history_dir=_os.path.join(fmo_inx_dir, "history.yml"),
        )
        eprint("创建完成")

    @set_command(command="update", document="更新fm对象")
    def fm_update(self, content):
        fs = FolderStatus(self.work_dir)
        for i in _os.listdir():
            if _re.match(r"^.*\.fmi_[\da-zA-Z]+$", i):
                fmo_inx_dir = i
                break
        else:
            eprint("出错了!!!未能找到索引文件夹")
        eprint("找到索引文件夹「{fmo_inx_dir}」")
        fs.update_data(
            data_dir=_os.path.join(fmo_inx_dir, "status.yml"),
            history_dir=_os.path.join(fmo_inx_dir, "history.yml"),
        )

    @set_command(command="scan", document="检查fm对象变动")
    def fm_scan(self, content):
        fs = FolderStatus(self.work_dir)
        for i in _os.listdir():
            if _re.match(r"^.*\.fmi_[\da-zA-Z]+$", i):
                fmo_inx_dir = i
                break
        else:
            eprint("出错了!!!未能找到索引文件夹")
        eprint("找到索引文件夹「{fmo_inx_dir}」")
        fs.update_data(
            data_dir=_os.path.join(fmo_inx_dir, "status.yml"),
            history_dir=_os.path.join(fmo_inx_dir, "history.yml"),
            only_scan_and_print=True,
        )

    @set_command(command="test_update", document="[测试功能]将本文件夹的fmi更新")
    def test(self, content):
        au = AutoUpdate(self.work_dir)


if __name__ == "__main__":
    cmd = FMcmd()
    cmd.start()
