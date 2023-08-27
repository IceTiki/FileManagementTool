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

    def __new__(cls, string: str | pathlib.Path):
        return super(TagPath, cls).__new__(cls, string)

    def __init__(self, string: str | pathlib.Path):
        super().__init__()  # Path.__init__不接受参数(在__new__已经完成了)
        self._some_instance_ppath_value = self.exists()  # Path method

    def __iter__(self):
        return self.tag_data.__iter__()

    @property
    def tag_data(self):
        return self.Decoder(self.stem).resolute()

    class Decoder:
        TRAN_TAG = set("`#=,{}[]")
        TRAN_C1 = set("\\abnvtrf\"'")
        TRAN_C3 = set("x" + "01234567")
        TRAN_C4 = set("u")

        class TagStringDecodeError(ValueError):
            """TagString解析错误"""

            def __init__(self, *args: object, position=None, msg=None) -> None:
                self.position = position
                if not args:
                    errmsg = "TagString解析错误"
                    if msg is not None:
                        errmsg += f", {msg}"
                    if position is not None:
                        errmsg += f", 错误出现在{position}"
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
            if self.__cursor < self.__left_limit:
                return f"before {self.__string[self.__left_limit:self.__right_limit].__repr__()}"
            elif not self.__cursor < self.__right_limit:
                return f"after {self.__string[self.__left_limit:self.__right_limit].__repr__()}"
            else:
                l = [
                    self.__string[self.__left_limit : self.__cursor],
                    self.__cursor_chara,
                    self.__string[self.__cursor + 1 : self.__right_limit],
                ]
                return f"middle of {l}"

        def __cursor_add(self, step=1, check_limit=True):
            self.__cursor += step
            if not self.__cursor < self.__right_limit and check_limit:
                raise self.TagStringDecodeError(
                    position=self.__show_cursor_position(), msg="unexpect end"
                )

        def __decode_assert(self, item):
            if not item:
                raise self.TagStringDecodeError(
                    position=self.__show_cursor_position(), msg="unexpect char"
                )

        def __catch_tran(self) -> str:
            """
            转义字符匹配
            开始时指针指向: 转义字符"`"
            结束时指针指向: 转义字符串的最后一个字符
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

            return f"\\{self.__string[slice_start:self.__cursor + 1]}".encode().decode(
                "unicode_escape"
            )

        def __catch_string(self, end_chara: str) -> str:
            """
            匹配字符串
            开始时指针指向: 字符串的第一个字符字符
            结束时指针指向: 字符串的最后一个字符

            Parameters
            ---
            end_chara : str
                结束字符
            """
            result = ""
            self.__cursor_add(0)

            while True:
                cursor_chara = self.__cursor_chara
                # 匹配结束字符
                if cursor_chara in end_chara:
                    return result
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
            结束时指针指向: 字典之后的第一个字符
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
                key = self.__catch_string("=")
                self.__decode_assert(self.__cursor_chara == "=")

                self.__cursor_add()

                # 捕捉value
                match self.__cursor_chara:
                    case "{":
                        value = self.__catch_dict()
                    case "[":
                        value = self.__catch_list()
                    case _:
                        value = self.__catch_string(",}")
                result[key] = value

        def __catch_list(self) -> list:
            """
            匹配列表
            开始时指针指向: 列表的第一个字符字符
            结束时指针指向: 列表之后的第一个字符
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
                        value = self.__catch_string(",]")
                result.append(value)

        def __catch_value(self) -> str | list[typing.Any] | dict[str, typing.Any]:
            """
            匹配值
            开始时指针指向: 值的第一个字符字符
            结束时指针指向: 值之后的第一个字符
            """
            while True:
                match self.__cursor_chara:
                    case "{":
                        return self.__catch_dict()
                    case "[":
                        return self.__catch_list()
                    case _:
                        # 字符串类型
                        return self.__catch_string("#")

        def resolute(self) -> list:
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
                    value = self.__catch_string("#")
                    append_result(value)

                    self.__decode_assert(self.__cursor_chara == "#")
                    self.__cursor_add()
                    if self.__cursor_chara == "#":
                        self.__decode_assert(
                            self.__cursor - self.__left_limit > 1
                        )  # 避免将以"##"开头的字符串, 识别为结束
                        append_result()  # 达到TagString结束
                        self.__init_cursor(self.__cursor + 1)
                        continue

                    # 捕捉key, 直到指针达到"="
                    key = self.__catch_string("=")
                    self.__decode_assert(self.__cursor_chara == "=")

                    # 捕捉value, 直到指针越界或达到"#"
                    self.__cursor_add()
                    value = self.__catch_value()
                    new_item[0][key] = value

                except self.TagStringDecodeError:
                    # 在self.__cursor处出现解析错误, 将前面的部分视作普通字符串
                    append_result(self.__string[self.__left_limit : self.__cursor])
                    self.__init_cursor(self.__cursor)

            return result
