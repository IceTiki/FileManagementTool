import re as _re
import typing as _typing
import hashlib as _hashlib
import pathlib as _pathlib
import os as _os
import time as _time
import shutil as _shutil
import functools as _functools

from . import litetools as _lt

import loguru as _loguru
import tqdm as _tqdm


FSDB_VERSION = "1.1.0"
FM_VERSION = "1.0.0-beta"


class ObjectFolder:
    """「对象」文件夹"""

    def __init__(self, folder_path: str | _pathlib.Path) -> None:
        self.root = folder_path

    @property
    def root(self) -> _pathlib.Path:
        return self.__root

    @root.setter
    def root(self, new_root: str | _pathlib.Path):
        self.__root: _pathlib.Path = _pathlib.Path(new_root).absolute()
        self.__cache: dict = {}

    @staticmethod
    def find_fmi(folder_path: str | _pathlib.Path) -> _pathlib.Path:
        """
        优先查找名为".fmi"的文件夹, 其次查找名为".fmi_[id-8/12/16]"的文件夹
        如果未能找到唯一fmi文件夹, 则报错

        Raises
        ---
        OSError
        """
        folder_path = _pathlib.Path(folder_path).absolute()
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

    @property
    def fmi_dir(self):
        if "fmi_dir" not in self.__cache:
            self.__cache["fmi_dir"] = self.find_fmi(self.root)
        return self.__cache["fmi_dir"]

    @property
    def status_database_dir(self):
        return self.fmi_dir / "status.db"

    @property
    def folder_status(self):
        return FolderStatus(self.root, self.status_database_dir)


class FolderStatus:
    """文件夹变动追踪数据库"""

    _t_path_sta = tuple[str, bool, str, int]
    _t_list_sta = list[_t_path_sta]
    _t_variance = tuple[str, bool, str, int, float, bool]
    _t_list_variance = list[_t_variance]

    _variance_column_name: tuple[str] = (
        "PATH",
        "ISFILE",
        "SHA256",
        "SIZE",
        "TIME",
        "CHANGE",
    )
    _status_column_name: tuple[str] = ("PATH", "ISFILE", "SHA256", "SIZE")
    _info_column_name: tuple[str] = ("TIME", "ROOT", "MAC", "COMMENT", "VERSION")

    force_hash: bool = False  # 是否强制计算所有文件哈希值(如果为False, 则通过mtime、size等参数判断文件是否需要重新计算哈希)

    def __init__(
        self,
        folder_path: str | _pathlib.Path,
        dbpath: str | _pathlib.Path,
    ) -> None:
        """
        Parameters
        ---
        folder_path : str | pathlib.Path
            文件夹路径
        dbpath : str | pathlib.Path
            数据路径
        """
        self.__root = _pathlib.Path(folder_path).absolute()
        self.__dbpath = _pathlib.Path(dbpath).absolute()
        self.__cache = {}

    @staticmethod
    def __gene_variance(
        list_old: _t_list_sta, list_new: _t_list_sta, time_: float
    ) -> _t_list_variance:
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
        variance = added + deleted
        variance.sort()
        return variance

    @staticmethod
    @_loguru.logger.catch
    def _cal_sha256(file_path: _pathlib.Path) -> str | None:
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
    def __get_file_size(file_path: _pathlib.Path) -> str | None:
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

    @_loguru.logger.catch
    def __calculating_path_status(self, path: _pathlib.Path) -> _t_path_sta:
        """
        整合统计路径状态, 生成路径状态信息。
        (所有文件都会计算sha256)

        Parameters
        ---
        path : pathlib.Path
            路径
        """
        relpath: str = str(path.relative_to(self.__root))
        if path.is_file():
            return (relpath, True, self._cal_sha256(path), self.__get_file_size(path))
        else:
            return (relpath, False, None, None)

    @property
    def __gene_path_status(self) -> _typing.Callable[[_pathlib.Path], _t_path_sta]:
        if self.force_hash:
            return self.__calculating_path_status
        else:
            update_time_list: float = map(
                lambda x: x[0], self._database.select("INFO", "TIME")
            )
            last_update_time: float = max(update_time_list, default=0)
            db_data: dict[str, self._t_path_sta] = {
                i[0]: i for i in self._database.select("STATUS")
            }

            @_loguru.logger.catch
            def lazy_calculating_path_status(path: _pathlib.Path):
                """
                整合统计路径状态, 生成路径状态信息。
                如果数据库中已有该文件的数据, 且通过mtime、size、is_file判断文件没有发生变动, 则直接返回数据库中的数据(减少sha256计算量)。

                Parameters
                ---
                path : pathlib.Path
                    路径
                """
                relpath: str = str(path.relative_to(self.__root))
                if not path.is_file():
                    return (relpath, False, None, None)
                if db_path_data := db_data.get(relpath, None):
                    _, db_isfile, _, db_size = db_path_data
                else:
                    return self.__calculating_path_status(path)

                # 比对信息
                stat = path.stat()
                if (
                    stat.st_mtime < last_update_time
                    and stat.st_size == db_size
                    and db_isfile == path.is_file()
                ):
                    return db_path_data
                else:
                    return self.__calculating_path_status(path)

            return lazy_calculating_path_status

    @property
    def _database(self) -> _lt.DbOperator:
        if "db" not in self.__cache:
            if self.__dbpath.is_file():
                db = _lt.DbOperator(self.__dbpath)
            else:
                db = self.__create_database()

            self.__cache["db"] = db
        return self.__cache["db"]

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
    def change_overview(self) -> str:
        """以markdown语法, 返回文件夹内文件和文件夹的变动"""
        _loguru.logger.info("扫描文件夹中被更改的项目")
        _loguru.logger.info("    载入数据库内旧的文件夹状态数据")
        old_folder_status: self._t_list_sta = self._database.select("STATUS")
        _loguru.logger.info("    扫描文件夹变动")
        variance = self.__gene_variance(
            old_folder_status, self.__scan_folder_status(), 0
        )

        # 装为dict
        sta_dict = {}
        for path, is_file, _, _, _, change in variance:
            path = _pathlib.Path(path)
            insert_target = sta_dict

            parts = path.parts
            last_idx = len(parts) - 1
            for i, p in enumerate(parts):
                i: int
                p: str
                insert_target: dict
                get_ = insert_target.get(p)

                if get_ is None:
                    insert_target.setdefault(p, {})

                if i == last_idx:
                    flag = "- [x] " if change else "- [ ] "
                    flag = (
                        flag
                        if {insert_target[p].get(0), flag} != {"- [x] ", "- [ ]"}
                        else "* "
                    )
                    insert_target[p][0] = f"{flag}{'`f`' if is_file else '`d`'}"

                insert_target = insert_target[p]

        # 解dict
        msg = [
            f"""# 符号说明

`d`——文件夹

`f`——文件

* 变动
- [x] 新增
- [ ] 删去

# 变更总览

根目录: `{self.__root}`
"""
        ]
        pathiter = None
        stack = [iter(sta_dict.items())]
        while stack or pathiter:
            if not pathiter:
                pathiter = stack.pop()
            for k, v in pathiter:
                k: str
                v: dict
                if tuple(v.keys()) == (0,):
                    # 到头了
                    msg.append("    " * len(stack) + v[0] + str(k))
                else:
                    # 没到头
                    head = v.pop(0, "* `d`")
                    msg.append("    " * len(stack) + head + str(k))
                    stack.append(pathiter)
                    pathiter = iter(v.items())
                    break
            else:
                pathiter = None

        return "\n".join(msg)

    @property
    def __gene_update_info(self):
        """TIME ROOT MAC COMMENT VERSION"""
        return (
            _time.time(),
            str(self.__root),
            _lt.System.get_mac_address(),
            "",
            FSDB_VERSION,
        )

    def __scan_folder_status(self, force_update=False) -> _t_list_sta:
        key = "folder_status"
        if force_update or key not in self.__cache:
            path_seq = _tqdm.tqdm(
                list(self.iterdirs), desc=f"扫描文件夹'{self.__root.name}'内项目", mininterval=1
            )
            sta = list(map(self.__gene_path_status, path_seq))
            sta.sort()
            self.__cache[key] = sta
        return self.__cache[key]

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
        db.try_exe("DELETE FROM STATUS;")
        db.insert_many("STATUS", self._status_column_name, self.__scan_folder_status())
        db.insert_many(
            "INFO",
            self._info_column_name,
            [self.__gene_update_info],
        )
        _loguru.logger.info("    完成")
        return db

    def update_database(self) -> _lt.Decorators:
        """根据文件夹当前状态, 更新数据库"""
        db = self._database
        info = self.__gene_update_info
        update_time = info[0]

        _loguru.logger.info("更新数据库")
        _loguru.logger.info("    载入数据库内旧的文件夹状态数据")
        old_folder_status: self._t_list_sta = db.select("STATUS")
        _loguru.logger.info("    扫描文件夹变动")
        variance = self.__gene_variance(
            old_folder_status, self.__scan_folder_status(), update_time
        )

        # 更新表
        _loguru.logger.info("    更新VARIANCE表")
        db.insert_many("VARIANCE", self._variance_column_name, variance)
        _loguru.logger.info("    更新STATUS表")
        db.try_exe("DELETE FROM STATUS;")
        db.insert_many("STATUS", self._status_column_name, self.__scan_folder_status())
        _loguru.logger.info("    更新INFO表")
        db.insert_many(
            "INFO",
            self._info_column_name,
            [info],
        )

        _loguru.logger.info("    完成")
        return db

    def combine_variance(
        self,
        start_time: float = 0,
        end_time: float = _time.time(),
        include_left: bool = True,
        include_right: bool = True,
    ) -> tuple[_t_list_variance, _t_list_variance]:
        """
        Paramters
        ---
        start_time, end_time : float
            将start_time到end_time范围内的多个VARIANCE记录合并为两个列表并返回
        include_left, include_right : bool
            是否包含左区间边界/右区间边界
        Returns
        ---
        added_item_list, deleted_item_list
        """
        added_item: dict[tuple[str, str], self._t_variance] = {}
        deleted_item: dict[tuple[str, str], self._t_variance] = {}

        variance_list: self._t_list_variance = self._database.select(
            "VARIANCE",
            self._variance_column_name,
            f"""WHERE
            TIME {'>=' if include_left else '>'} {start_time}
            AND
            TIME {'<=' if include_right else '<'} {end_time}
            ORDER BY TIME""",
        )

        for path, isfile, sha256, size, time, change in variance_list:
            key = (path, sha256)
            value = (path, isfile, sha256, size, time, change)

            if change:
                assert key not in added_item
                added_item[key] = value
                deleted_item.pop(key, None)
            else:
                assert key not in deleted_item
                deleted_item[key] = value
                added_item.pop(key, None)

        added_item_list: self._t_list_variance = list(added_item.values())
        deleted_item_list: self._t_list_variance = list(deleted_item.values())

        return added_item_list, deleted_item_list

    def extract_new_files(
        self, output_folder: str | _pathlib.Path, start_time: float, update: bool = True
    ):
        """
        从VARIANCE表中检索, 时间范围在(start_time, 现在时间]的新增现存文件, 并复制到output_folder中

        Parameters
        ---
        output_folder : str | _pathlib.Path
            新文件输出文件夹
        start_time : float
            时间范围为(start_time, 现在时间]
        update: bool, default = True
            是否在导出前更新数据库

        Notions
        ---
        - 请确保在最后一次更新数据库之后, 内部文件没有发生更改, 否则可能会使用错误的sha256
        """
        if update:
            self.update_database()

        sha256_set: set = set()
        output_folder = _pathlib.Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        added, deleted = self.combine_variance(start_time, include_left=False)
        added = _tqdm.tqdm(list(added), desc=f"导出'{self.__root.name}'中的新增文件")
        for path, isfile, sha256, size, time, change in added:
            file_path = self.__root / path
            if file_path.is_dir():
                continue
            if not file_path.is_file():
                _loguru.logger.debug(f"'{file_path}'不存在")
                continue
            if file_path == self.__dbpath:
                # status.db重新计算sha256
                sha256 = self._cal_sha256(file_path)
            if size != file_path.stat().st_size:
                # 简单检查文件是否被修改, 如果被修改, 重新计算sha256
                sha256 = self._cal_sha256(file_path)
            if not sha256:
                continue
            if sha256 in sha256_set:
                continue
            else:
                sha256_set.add(sha256)

            new_path = output_folder / f"{sha256}{file_path.suffix}"  # TODO no suffix
            _shutil.copy2(file_path, new_path)

        _shutil.copy2(self.__dbpath, output_folder / "status.db")


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
    def yml2db_1_1_0(
        status: str | _pathlib.Path,
        history: str | _pathlib.Path,
        db_path: str | _pathlib.Path,
    ):
        status, history, db_path = map(_pathlib.Path, (status, history, db_path))
        status_data = _lt.YamlRW.load(status)["status"]
        history_data = _lt.YamlRW.load(history)

        if db_path.is_file():
            _loguru.logger.info(f"'{db_path}'已经存在")
            return

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
        db.try_exe("DELETE FROM STATUS;")
        db.insert_many("STATUS", ["PATH", "ISFILE", "SHA256", "SIZE"], db_sta)
        db.insert_many(
            "VARIANCE", ["PATH", "ISFILE", "SHA256", "SIZE", "TIME", "CHANGE"], db_var
        )
        db.insert_many(
            "INFO",
            ["TIME", "ROOT", "MAC", "COMMENT", "VERSION"],
            db_info,
        )
