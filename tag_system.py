import typing
import pathlib


class TagPath(pathlib.Path):
    """
    解析TagString

    Parameters
    ---
    string : str | pathlib.Path
        path-like-object
    """

    # type(pathlib.Path())是pathlib.Path根据当前系统判断, 实例化哪种类型的Path
    _flavour = type(pathlib.Path())._flavour

    @classmethod
    def from_tag_data(
        cls, items: list[str | dict], beautify: bool = False
    ) -> typing.Self:
        """
        将列表格式化为TagString字符串

        Notions
        ---
        如果启用beautify, 那么
        - 列表中的所有字典会合并到同一个字典中, 首层key会被排序
        - 为避免反复转义, 列表中的所有字符串会被加入到字典中, 键为""(空字符串)的列表中

        Parameters
        ---
        items : list[str | dict]
            ...
        beautify : bool
            是否启用美化
        """
        if beautify:
            return cls(cls.Formater.beautify_join(items))
        return cls(cls.Formater.join(items))

    def __new__(cls, string: str | pathlib.Path):
        return super(TagPath, cls).__new__(cls, string)

    def __init__(self, string: str | pathlib.Path):
        super().__init__()  # Path.__init__不接受参数(在__new__已经完成了)
        self._some_instance_ppath_value = self.exists()  # Path method

    def __iter__(self):
        return self.parsed.__iter__()

    @property
    def parsed(self) -> list[str | dict]:
        """分段解析字符串, TagString解析为字典, 其他保留原样"""
        return self.Parser(self.stem).resolute()

    @property
    def combined_tagdata(self) -> dict:
        """将所有解析出的TagString字典进行合并, 有重复键则其值以后者为准"""
        result = {}
        for i in self.parsed:
            if isinstance(i, dict):
                result.update(i)
        return result

    @property
    def formated(self) -> typing.Self:
        """格式化自身TagString"""
        tag_data = self.parsed
        for i in tag_data:
            if isinstance(i, dict):
                break
        else:
            # 如果tag_data中没有从TagString中解析出的dict, 那么该字符串不需要美化
            return self

        formated_filestem = str(self.from_tag_data(self.parsed))
        if self.is_dir():
            # 如果原路径指向文件夹, 那么pathlib.Path的stem不会用"."划分stem和suffix
            # 但是格式化后的新路径不一定指向文件夹, 那么其中的"."就会导致stem和suffix错误地被划分
            # 所以要转义"."
            formated_filestem = formated_filestem.replace(".", "`x2e")
        return self.with_stem(formated_filestem)

    @property
    def _test_parser_eq_format(self) -> bool:
        par_for = self.with_stem(self.from_tag_data(self.parsed).__str__())
        if self == par_for:
            return True
        print(
            f"""===============NOT EQUAL===============
> {self.name}
< {par_for.name}
======================================="""
        )
        return False

    @property
    def _test_folder(self) -> None:
        from tikilib import system as ts

        n = 0
        for i in ts.Path.traversing_generator(self):
            i = self.__class__(i)
            i._test_parser_eq_format
            n += 1
            if n % 10000 == 0:
                print(n)

    class Parser:
        TRAN_TAG = set("`#=,{}[]")
        TRAN_C1 = set("\\abnvtrf\"'")
        TRAN_C3 = set("x" + "01234567")
        TRAN_C4 = set("u")

        class TagStringDecodeError(ValueError):
            """TagString解析错误"""

            def __init__(self, *args: object, position=None, msg=None) -> None:
                self.position = position
                if not args:
                    errmsg = "TagString解析错误。"
                    if msg is not None:
                        errmsg += f"{msg}。"
                    if position is not None:
                        errmsg += f"错误出现在{position}。"
                    args = [errmsg]

                super().__init__(*args)

        def __init__(self, string: str) -> None:
            self.__set_string(string)

        @property
        def __cursor_chara(self):
            return self.__string[self.__cursor]

        def __set_string(self, string: str) -> None:
            """
            right_limit是开区间边界
            """
            self.__string = string
            self.__length = len(string)

        def __init_cursor(self, left_limit=0, right_limit=None):
            """
            初始化游标

            Parameters
            ---
            left_limit, right_limit : int, default = 0, len(self.__string)
                匹配区间[left_limit, right_limit)
            """
            self.__right_limit = self.__length if right_limit is None else right_limit
            self.__left_limit = left_limit
            self.__cursor = left_limit

        def __show_cursor_position(self) -> str:
            if self.__cursor < 0:
                return f"before {self.__string[0:self.__length].__repr__()}"
            elif not self.__cursor < self.__length:
                return f"after {self.__string[0:self.__length].__repr__()}"
            else:
                l = [
                    self.__string[0 : self.__cursor],
                    self.__cursor_chara,
                    self.__string[self.__cursor + 1 : self.__length],
                ]
                return f"middle of {l}"

        def __cursor_add(self, step=1, check_limit=True, do_warning=True):
            self.__cursor += step
            if not self.__cursor < self.__right_limit and check_limit:
                e = self.TagStringDecodeError(
                    position=self.__show_cursor_position(), msg="游标越界"
                )
                if do_warning:
                    print(e)
                raise e

        def __decode_assert(self, item):
            if not item:
                e = self.TagStringDecodeError(
                    position=self.__show_cursor_position(),
                    msg=f"不应出现的字符'{self.__cursor_chara}'",
                )
                print(e)
                raise e

        def __catch_tran(self) -> str:
            """
            转义字符匹配
            开始时指针指向: 转义字符"`"
            结束时指针指向: 转义字符串的最后一个字符

            Parameters
            ---
            """
            self.__decode_assert(self.__cursor_chara == "`")
            # 指向转义字符的下一个字符
            self.__cursor_add()

            # 确定转义字符串长度
            cursor_chara = self.__cursor_chara
            # TagString特殊字符转义
            if cursor_chara in self.TRAN_TAG:
                # 1字符
                return cursor_chara
            # 其他转义
            elif cursor_chara in self.TRAN_C1:
                cursor_add = 0  # 1字符
            elif cursor_chara in self.TRAN_C3:
                cursor_add = 2  # 3字符
            elif cursor_chara == "u":
                cursor_add = 3  # 4字符
            else:
                # 1字符
                print(f"Warning: invalid escape sequence '\\{cursor_chara}'")
                return "`" + cursor_chara

            slice_start = self.__cursor
            self.__cursor_add(cursor_add)

            tran_slice = self.__string[slice_start : self.__cursor + 1]
            return f"\\{tran_slice}".encode().decode("unicode_escape")

        def __catch_before_tagstring(self) -> str:
            """匹配#(TagString开始标志), 并将前面的普通字符串返回

            开始时指针指向: 字符串的第一个字符字符
            结束时指针指向: "#"
            """
            result = ""
            self.__cursor_add(0, do_warning=False)

            while True:
                cursor_chara = self.__cursor_chara
                if cursor_chara == "#":
                    return result
                result += cursor_chara
                # 指针自增
                self.__cursor_add(do_warning=False)

        def __catch_string(self, end_chara: str, error_chara: set = set()) -> str:
            """
            匹配字符串
            开始时指针指向: 字符串的第一个字符字符
            结束时指针指向: 结束字符

            Parameters
            ---
            end_chara : str
                结束字符
            error_chara : set
                错误字符(遇到该字符则报错, 除非字符被转义豁免)
            """
            result = ""
            self.__cursor_add(0)

            while True:
                cursor_chara = self.__cursor_chara
                # 匹配结束字符
                if cursor_chara in end_chara:
                    return result
                # 匹配错误字符
                self.__decode_assert(cursor_chara not in error_chara)
                # 匹配转义字符(指针会自动跳到转义字符串的最后一个)
                normal_chara = (
                    self.__catch_tran() if cursor_chara == "`" else cursor_chara
                )

                result += normal_chara

                # 指针自增
                self.__cursor_add()

        def __catch_dict(self) -> dict:
            """
            匹配字典
            开始时指针指向: 字典的第一个字符字符
            结束时指针指向: 字典之后的第一个字符 ("}"之后)
            """
            self.__decode_assert(self.__cursor_chara == "{")
            self.__cursor_add()
            result = {}

            while 1:
                # 检查结束
                if self.__cursor_chara == "}":
                    self.__cursor_add()
                    return result
                # 检查逗号
                elif self.__cursor_chara == ",":
                    self.__cursor_add()

                # 捕捉key
                key = self.__catch_string("=", set("#,{}[]"))
                self.__decode_assert(self.__cursor_chara == "=")

                self.__cursor_add()

                # 捕捉value
                match self.__cursor_chara:
                    case "{":
                        value = self.__catch_dict()
                    case "[":
                        value = self.__catch_list()
                    case _:
                        value = self.__catch_string(",}", set("#={[]"))
                if key in result:
                    print(
                        f"Warning: the value {repr(result[key])} of key {repr(key)} has been replaced by {repr(value)}"
                    )
                result[key] = value

        def __catch_list(self) -> list:
            """
            匹配列表
            开始时指针指向: 列表的第一个字符字符
            结束时指针指向: 列表之后的第一个字符 ("]"之后)
            """
            self.__decode_assert(self.__cursor_chara == "[")
            self.__cursor_add()
            result = []

            while 1:
                # 检查结束
                if self.__cursor_chara == "]":
                    self.__cursor_add()
                    return result
                # 检查逗号
                elif self.__cursor_chara == ",":
                    self.__cursor_add()

                # 捕捉value
                match self.__cursor_chara:
                    case "{":
                        value = self.__catch_dict()
                    case "[":
                        value = self.__catch_list()
                    case _:
                        value = self.__catch_string(",]", set("#={}["))
                result.append(value)

        def __catch_value(self) -> str | list[typing.Any] | dict[str, typing.Any]:
            """
            匹配值
            开始时指针指向: 值的第一个字符字符
            结束时指针指向: 值之后的第一个字符"#"
            """
            while True:
                match self.__cursor_chara:
                    case "{":
                        value = self.__catch_dict()
                        self.__decode_assert(self.__cursor_chara == "#")
                        return value
                    case "[":
                        value = self.__catch_list()
                        self.__decode_assert(self.__cursor_chara == "#")
                        return value
                    case _:
                        # 字符串类型
                        return self.__catch_string("#", set(",={}[]"))

        def __catch_tagstring(self):
            result = {}

            while True:
                # 跳过每个键值对开始的"#"
                self.__decode_assert(self.__cursor_chara == "#")
                self.__cursor_add()
                # 匹配结束
                if self.__cursor_chara == "#":
                    self.__decode_assert(
                        self.__cursor - self.__left_limit > 1
                    )  # 避免将以"##"开头的字符串, 识别为结束
                    self.__init_cursor(self.__cursor + 1)
                    return result

                # 捕捉key, 直到指针达到"="
                key = self.__catch_string("=", set("#,{}[]"))
                self.__decode_assert(self.__cursor_chara == "=")

                # 捕捉value, 直到达到"#"
                self.__cursor_add()
                value = self.__catch_value()
                if key in result:
                    print(
                        f"Warning: the value {repr(result[key])} of key '{repr(key)}' has been replaced by {repr(value)}"
                    )
                result[key] = value

        def resolute(self) -> list[str | dict]:
            """
            解析TagString
            """
            result = []
            new_item = [{}]  # 方便传引用

            def append_result(item=None, result: list = result):
                if item is None:
                    item = new_item[0]

                if not item:
                    return
                elif not result:
                    result.append(item)

                elif isinstance(result[-1], str) and isinstance(item, str):
                    result[-1] += item
                elif isinstance(item, dict):
                    result.append(item)
                else:
                    result.append(item)

                new_item[0] = {}

            self.__init_cursor()

            while self.__left_limit < self.__length:
                try:
                    # 开始前的普通字符串
                    value = self.__catch_before_tagstring()
                    append_result(value)
                    self.__init_cursor(self.__cursor)
                    # 尝试解析TagString
                    value = self.__catch_tagstring()
                    append_result(value)

                except self.TagStringDecodeError as e:
                    # print(f"Warning: except TagStringDecodeError:\n{e}")
                    # 在self.__cursor处出现解析错误, 将前面的部分视作普通字符串
                    append_result(self.__string[self.__left_limit : self.__cursor])
                    self.__init_cursor(self.__cursor)

            return result

    class Formater:
        @staticmethod
        def chr_escape(
            chara: str,
            tran_chr: str = "`",
            head_escape: set = set("`#=,{}[]"),
            save_escape: set = set('\\/:*?"<>|'),
        ) -> str:
            """
            判断字符是否需要转义

            Parameters
            ---
            chara : str
                单个字符
            tran_chr : str, default = "`"
                转义字符
            head_escape : set, default = set("`#=,{}[]")
                有特殊含义的字符, 需要前面加上转义字符使其表达原义
            save_escape : set, default = set(r'\/:*?"<>|')
                不可打印或不安全的字符

            Notes
            ---
            https://zh.wikipedia.org/wiki/Unicode%E5%AD%97%E7%AC%A6%E5%88%97%E8%A1%A8
            Unicode中的不可打印字符:
            C0: 0~31
            C1: 128~159
            127: delete
            """
            chara_ord: int = ord(chara)
            if chara_ord < 32 or (126 < chara_ord < 160):
                return tran_chr + chara.encode("unicode_escape").decode()[1:]
            if chara in save_escape:
                return f"`x{chara_ord:x}"
            if chara in head_escape:
                return tran_chr + chara
            # 无需转义
            return chara

        @classmethod
        def encode_string(cls, string: str) -> str:
            """
            对字符串特殊字符转义

            Notes
            ---
            - 转义字符为"`"
            - "`#=,{}[]"中的字符会在前面添加转义字符"`_"
            - 不可打印字符与Windows中无法作为路径名的字符"\\/:*?"<>|"会被转义为"`"与安全字符的组合

            Exameple
            ---
            >>> encode_string(r"https://cn.bing.com/##")
            https`x3a`x2f`x2fcn.bing.com`x2f`#`#
            """
            if not isinstance(string, str):
                print(f"Warning: var string type is {type(string)}")
                string = str(string)
            return "".join(map(cls.chr_escape, string))

        @classmethod
        def join(cls, list_: list[str | dict]):
            """
            将列表中的字典格式化为TagString字符串

            Parameters
            ---
            list_ : list[str | dict]
                ...
            """
            assert isinstance(list_, typing.Sequence)

            def convertor(item):
                match item:
                    case str():
                        return item
                    case dict():
                        return cls._encode_root_item(item)
                    case _:
                        raise TypeError(f"{type(item)}")

            return "".join(map(convertor, list_))

        @classmethod
        def beautify_join(cls, list_: list[str | dict]):
            """
            将列表格式化为TagString字符串

            Notions
            ---
            - 列表中的所有字典会合并到同一个字典中, 首层key会被排序
            - 为避免反复转义, 列表中的所有字符串会被加入到字典中, 键为""(空字符串)的列表中

            Parameters
            ---
            list_ : list[str | dict]
                ...
            """
            assert isinstance(list_, typing.Sequence)
            dict_data = {}
            for item in list_:
                match item:
                    case str():
                        if "" not in dict_data:
                            dict_data[""] = []
                        if not isinstance(dict_data[""], list):
                            raise ValueError("dictionarys have key''")
                            # dict_data[""] = [dict_data[""]]
                        dict_data[""].append(item)
                    case dict():
                        if item.keys() & dict_data.keys():
                            raise ValueError("dictionarys have same key")
                        dict_data.update(item)
            dict_data = {k: dict_data[k] for k in sorted(dict_data.keys())}
            return cls._encode_root_item(dict_data)

        @classmethod
        def _encode_dict(cls, dictionary: dict) -> str:
            assert isinstance(dictionary, dict)
            stem = ",".join(
                map(
                    lambda x: f"{cls.encode_string(x[0])}={cls._encode_value(x[1])}",
                    dictionary.items(),
                )
            )
            return "{" + stem + "}"

        @classmethod
        def _encode_list(cls, list_: list) -> str:
            assert isinstance(list_, list)
            stem = ",".join(map(lambda x: cls._encode_value(x), list_))
            return f"[{stem}]"

        @classmethod
        def _encode_value(cls, item: dict | list | str) -> str:
            match item:
                case str():
                    return cls.encode_string(item)
                case list():
                    return cls._encode_list(item)
                case dict():
                    return cls._encode_dict(item)
                case _:
                    raise TypeError(type(item))

        @classmethod
        def _encode_root_item(cls, item: str | dict):
            match item:
                # case str():
                #     return cls.encode_string(item)
                case dict():
                    stem = "#".join(
                        map(
                            lambda x: f"{cls.encode_string(x[0])}={cls._encode_value(x[1])}",
                            item.items(),
                        )
                    )
                    return "#" + stem + "##"
                case _:
                    raise ValueError(type(item))
