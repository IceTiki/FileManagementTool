import os
import time
import git
import yaml
import re
import typing
import random
from litetools import StandardAesStringCrypto, Hash, FileOut, Decorators, YamlRW

if True:
    start_time = time.time()

    def runtime():
        """返回运行时间"""
        return time.time() - start_time

    def eprint(msg, *args, **kwargs):
        """带时间的print"""
        kwargs.setdefault("flush", True)
        reltime = round(time.time() - start_time, 2)
        print(f"|{reltime}s|{msg}", *args, **kwargs)

    def find_git(repo_file_path: str = "."):
        """
        逐级向上寻找.git仓库(如果没找到, 则返回None)
        :param repo_path: 查找的初始路径
        """
        repo_file_path = os.path.abspath(repo_file_path)
        if os.path.isfile(repo_file_path):
            repo_file_path = os.path.dirname(repo_file_path)

        repo_path = repo_file_path
        while 1:
            if ".git" in os.listdir(repo_path):
                return repo_path
            if os.path.ismount(repo_path):
                # 已经追溯到挂载点
                return None
            repo_path = os.path.dirname(repo_path)

    def git_commit(files: list, msg: str, repo_path: str = "."):
        """
        将修改提交到git中(如果当前路径不存在.git文件夹, 则自动向上回溯寻找, 如果没有找到, 则在当前位置初始化git仓库)
        :param files: 要提交的文件的路径列表
        :param msg: 提交信息
        :param repo_path: 仓库位置
        """
        assert isinstance(files, list)
        # 寻找git仓库位置
        repo_path_found = find_git(repo_path)
        repo_path = repo_path_found if repo_path_found != None else repo_path
        # 根据仓库路径, 相对化文件路径
        repo_rel = lambda x: os.path.relpath(os.path.abspath(x), repo_path)
        files = [repo_rel(i) for i in files]
        # 提交
        repo = git.Repo.init(repo_path)
        repo.index.add(files)
        repo.index.commit(msg)

    def condition_input(prompt: str = "> ", condition=lambda x: None):
        """
        通过循环, 迫使用户输入满足格式的字符串
        :param promt: 提示语
        :param condition: 条件——输入用户输入的字符串, 返回None时表示满足格式|返回其他时表示不满足格式(一般返回的是错误信息String)继续循环
        """
        while 1:
            inp = input(prompt)
            condition_result = condition(inp)
            if condition_result == None:
                return inp
            else:
                print(condition_result)

    def multiline_input(prompt: str = "> ", end: str = "end"):
        """
        通过循环, 使用户输入多行
        :param promt: 提示语
        :param end: 结束语句, 当用户输入该行时, 返回多行字符串
        """
        multi_string = ""
        while 1:
            inp = input(prompt)
            if inp == end:
                return multi_string
            else:
                multi_string += "\n" + inp

    fileout_ = FileOut()
    fileout_.start()


class SecurityTools:
    """密码库专用工具"""

    @staticmethod
    def formated_time():
        """格式化的现在时间"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


class StdAesEncryptedFile:
    """
    用标准AES加密的文件

    key: sha256(secret_key)[0:32]
    iv: sha256(secret_key)[32:48]
    mode: CBC
    padding: pkcs7padding
    charset: utf-8
    encode: Hex
    """

    def __init__(self, filepath: str, password: str) -> None:
        """
        :param filepath: 加密文件路径
        :param password: 加密文件密码
        """
        self.filepath = filepath
        assert os.path.isfile(filepath)
        self.password = password

    def gene_temporary_filepath(self, extension: str = ".yml"):
        """生成临时文件路径"""
        random_word = "".join(
            random.choices(
                "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4
            )
        )
        temporary_filepath = os.path.abspath(
            f"tmp_{random_word}_{int(time.time())}{extension}"
        )
        return temporary_filepath

    @property
    def isexist(self) -> bool:
        """
        判断加密文件是否存在
        """
        return os.path.isfile(self.filepath)

    def read(self) -> str:
        """
        读取文件、解密
        """
        assert self.isexist
        with open(self.filepath, "r", encoding="utf-8") as f:
            encrypted_content = f.read()
        content = StandardAesStringCrypto(self.password).decrypt(encrypted_content)
        assert isinstance(content, str)
        return content

    def write(self, content: str) -> None:
        """
        加密、写入文件
        """
        assert self.isexist
        assert isinstance(content, str)
        encrypted_content = StandardAesStringCrypto(self.password).encrypt(content)
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(encrypted_content)

    def read_yaml(self) -> dict:
        """
        读取文件、解密、解析yaml
        """
        data = yaml.load(self.read(), Loader=yaml.FullLoader)
        return data

    def write_yaml(self, data: dict) -> None:
        """
        yaml编码、加密、写入文件
        """
        content: str = yaml.dump(data).__str__()
        assert isinstance(content, str)
        self.write(content)

    def modify(self, extension: str = ".yml") -> bool:
        """
        创建临时文件以供修改
        :param extension: 临时文件的扩展名
        :returns bool: 文件是否被修改(已修改:True, 未修改False)
        """
        assert self.isexist
        temporary_filepath = self.gene_temporary_filepath(extension)
        # 解密数据到临时文件
        content = self.read()
        hash_before_modify = Hash.strHash(content, 256)
        with open(temporary_filepath, "w", encoding="utf-8") as f:
            f.write(content)
        # 打开文件以供修改
        os.startfile(temporary_filepath)
        while 1:
            is_commit = input("是否保存修改? (y/n)> ")
            if is_commit in ("y", "n"):
                break
            else:
                continue
        if is_commit == "y":
            # 保存修改
            with open(temporary_filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.write(content)
            eprint("修改已保存")

        # 清空并删除临时文件
        with open(temporary_filepath, "w", encoding="utf-8") as f:
            f.write("")
        os.remove(temporary_filepath)

        return hash_before_modify != Hash.strHash(self.read(), 256)


class CoreBank(StdAesEncryptedFile):
    """核心密码库"""

    filepath = "Core.keybank"

    def __init__(self, corekey: str = None) -> None:
        """
        :param corekey: 核心密钥(如果传入为None, 则通过input输入)
        """
        if not os.path.isfile(self.filepath):
            raise Exception("请先创建核心密码库")
        if corekey == None:
            corekey = input("请输入核心密钥> ")
        # 初始化
        self.filepath = self.filepath
        self.password = self.uniform_corekey(corekey)
        super().__init__(self.filepath, self.password)

    @property
    def corekey(self):
        return self.password

    @classmethod
    def uniform_corekey(cls, corekey):
        """返回正确格式的corekey"""
        if os.path.isfile(corekey) and re.match("^.*[a-f0-9]{64}.key$", corekey):
            # !如果输入内容是文件(此部分配合core_key.py模块, 属于测试中功能)
            core_key_path = corekey
            file_key = Hash.strHash(
                core_key_path[-68:-4] + "TikiEssential.Security", 256
            )
            corekey = StdAesEncryptedFile(core_key_path, file_key).read()
        else:
            raise OSError("读取密钥文件错误")

        if not re.match("^[a-f0-9]{128}$", corekey):
            raise ValueError("核心密钥是128位的十六进制数!!!")
        return corekey

    @classmethod
    def bank_init(cls, corekey):
        """
        初始化核心密码库(当核心密码库文件不存在时)
            会自动向git提交更改
        :param corekey: 核心密钥
        """
        assert re.match("^[a-f0-9]{128}$", corekey)
        # 检查文件
        if os.path.isfile(cls.filepath):
            raise Exception("Core.yml已经存在，请检查删除后进行创建")

        # 创建Core.yml
        password = cls.uniform_corekey(corekey)
        core_bank = StdAesEncryptedFile(cls.filepath, password)
        core_bank.write_yaml({"banks": []})

        # git记录
        git_commit([cls.filepath], "创建核心密码库")
        eprint("创建核心密码库成功")
        return cls(corekey)

    def append_new_bank_info(self, bankname, bank_key, bank_details):
        """
        在核心密码库中, 新增新密码库的信息
            会自动向git提交更改
        :params bankname, bank_key, bank_details: 新增密码库的名称, 密钥, 详细信息
        """
        assert re.match("^[A-Z][A-Z0-9]*$", bankname)
        core_bank_data: dict = self.read_yaml()
        banks_data: list = core_bank_data["banks"]
        banks_data.append(
            {
                "bankName": bankname,
                "key": bank_key,
                "details": bank_details,
                "decommissionTime": None,
                "createdTime": SecurityTools.formated_time(),
            }
        )
        self.write_yaml(core_bank_data)
        # git记录
        git_commit([self.filepath], "更新核心密码库(新增新密码库的信息)")
        eprint("已将新密码库的信息记录入核心密码库")

    def modify(self):
        """创建临时文件以供修改(会自动向git提交更改)"""
        ismodify = super().modify(".yml")
        if ismodify:
            # git记录
            git_commit([self.filepath], f"修改核心密码库")
            eprint(f"修改核心密码库完成")
        return ismodify


class KeyBank(StdAesEncryptedFile):
    bank_extension = ".keybank"

    def __init__(self, bankname: str, password: str) -> None:
        """
        :param bankname: 密码库名称
        :param password: 密码库密码
        """
        assert re.match("^[A-Z][A-Z0-9]*$", bankname)
        self.bankname = bankname
        filepath = self.bankname + self.bank_extension
        if not os.path.isfile(filepath):
            raise Exception(f"「{filepath}」不存在, 请先创建密码库")
        super().__init__(filepath, password)

    @classmethod
    def gene_init_content(cls, bankname, corekey):
        """
        生成KeyBank初始内容
        """
        assert re.match("^[A-Z][A-Z0-9]*$", bankname)
        assert re.match("^[a-f0-9]{128}$", corekey)

        init_bank_str = f"""keys: 
  - keyIndex: "{bankname}index" # 密钥索引
    key: "{Hash.strHash(corekey + bankname, 256)}" # 密钥
    details: 核心密码库分配密钥(核心密钥与密码库名拼接后字符串的sha-256值) # 详情
    # 时间格式 YYYY-MM-DD HH:MM:SS
    decommissionTime:  # 弃用时间，默认为空。当密钥索引不再使用时，不进行删除，而是填入弃用时间。
    createdTime: {SecurityTools.formated_time()} # 创建时间
    functions: 
  - funcIndex: {bankname}index()
    details: | # 详情
      f(string):核心密码库分配生成函数
        return 核心密码库分配密钥({bankname}index)与string拼接后字符串的sha-256值
    # 时间格式 YYYY-MM-DD HH:MM:SS
    decommissionTime:  # 弃用时间，默认为空。当生成函数不再使用时，不进行删除，而是填入弃用时间。
    createdTime: {SecurityTools.formated_time()} # 创建时间"""
        return init_bank_str

    @classmethod
    def bank_init(cls, bankname: str, bankkey: str, corekey: str):
        """
        初始化密码库(当密码库文件不存在时)
            会自动向git提交更改
            请配合CoreBank.append_new_bank_info使用
        :param bankname: 密码库名
        :param bankkey: 密码库密钥
        :param corekey: 核心密钥
        """
        assert re.match("^[A-Z][A-Z0-9]*$", bankname)
        assert re.match("^[a-f0-9]{128}$", corekey)
        # 检查文件
        filepath = bankname + cls.bank_extension
        if os.path.isfile(filepath):
            raise Exception(f"{filepath}已经存在，请检查删除后进行创建")

        # 创建密码库文件
        init_bank_str = KeyBank.gene_init_content(bankname, corekey)
        keybank = StdAesEncryptedFile(filepath, bankkey)
        keybank.write(init_bank_str)

        # git记录
        git_commit([filepath], f"创建密码库「{bankname}」")
        eprint(f"创建密码库「{bankname}」成功")
        return cls(bankname, bankkey)

    def modify(self):
        """创建临时文件以供修改(会自动向git提交更改)"""
        ismodify = super().modify(".yml")
        if ismodify:
            # git记录
            git_commit([self.filepath], f"修改密码库「{self.bankname}」")
            eprint(f"修改密码库「{self.bankname}」完成")
        return ismodify


class KBcmd:
    all_commands: dict = {}

    def __init__(self):
        pass

    def repository_assets(self, filename: str):
        return os.path.join(os.path.dirname(__file__), "assets", filename)

    @property
    def work_dir(self):
        return os.getcwd()

    def get_input(self, message=""):
        return input(f"● {self.work_dir}●{message}> ")

    def start(self):
        """开始执行循环"""
        print("发送「help」获取帮助")
        while 1:
            # 输入内容
            inp = input(f"● {self.work_dir}> ")
            # 解析内容
            if re.match(r"\w* .*", inp):
                inp: re.Match = re.search("^(\w*) (.*)", inp)
                command = inp.group(1)
                content = inp.group(2)
            else:
                command = inp
                content = ""
            # 命令执行
            if command in ("exit", "quit"):
                break
            elif command in self.all_commands:
                method: typing.Callable = self.all_commands[command]["method"]
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

        def decorator(method: typing.Callable) -> typing.Callable:
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
        result = re.finditer(pattern, content)
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
    @Decorators.except_all_error
    def cd(self, content):
        os.chdir(content)

    @set_command(command="edit", document="编辑tikifm")
    def edit(self, content):
        os.startfile(__file__)

    # ====================附加命令====================
    """
    CoreBank类和KeyBank类, 在修改内容后, 默认会进行git提交
    """

    @Decorators.except_all_error
    @set_command(command="init_core", document="创建核心密码库")
    def init_core(self, content):
        core_key = input("请输入核心密钥> ")
        CoreBank.bank_init(core_key)

    @Decorators.except_all_error
    @set_command(command="init_bank", document="创建密码库")
    def init_bank(self, content):
        # 打开核心密码库
        core_bank = CoreBank(None)
        core_key = core_bank.corekey

        # 输入新建密码库配置(名称, 密码, 简介)
        def bank_name_condition(bank_name_inp):
            if not re.match("^[A-Z][A-Z0-9]*$", bank_name_inp):
                return "密码库名格式错误"
            elif os.path.isfile(f"{bank_name_inp}.yml"):
                return "密码库已存在"
            else:
                return None

        bank_name = condition_input("请输入密码库名\n> ", bank_name_condition)
        bank_key = input("请输入密码库密码\n> ")
        print("请输入密码库简介(多行，输入「end」结束)")
        bank_details = multiline_input()

        # 更新核心密码库
        core_bank.append_new_bank_info(bank_name, bank_key, bank_details)

        # 创建密码库
        KeyBank.bank_init(bank_name, bank_key, core_key)

    @set_command(command="update_bank", document="更新密码库")
    def update_bank(self, content):
        bankname = input("请输入密码库名> ")
        bankkey = input("请输入密码库密码> ")
        kb = KeyBank(bankname, bankkey)
        kb.modify()

    @set_command(command="delete_bank", document="删除密码库")
    def delete_bank(self, content):
        assert False
        # TODO========================================================================================================
        # 读取核心密码库
        if not os.path.isfile("Core.yml"):
            eprint("请先创建核心密码库")
            return
        # 输入核心密钥
        core_key = SecurityTools.input_core_key()
        content = SecurityTools.read_encrypted_file(core_key, "Core.yml")
        # 获取要删除的密码库
        bank_name = input("请输入密码库名\n> ")
        if not os.path.isfile(f"{bank_name}.yml"):
            eprint("密码库不存在")
            return
        confirm_i = input(f'请输入"delete {bank_name}"确认删除\n> ')
        if confirm_i != "delete %s" % bank_name:
            print("输入错误")
            return
        # 修改
        #
        dict_ = KeyBankTools.yaml(content)
        finded = 0
        for item in dict_["banks"]:
            if item["bankName"] == bank_name and item["decommissionTime"] == None:
                item["decommissionTime"] = KeyBankTools.formTime()
                print("在核心密钥库中找到此密码库的记录")
                finded = 1
                break
        if not finded:
            print("未能在核心密钥库中找到此密码库的记录")
            return
        content = KeyBankTools.yaml(dict_)
        # 将修改写入核心密码库
        KeyBankTools.encrypto_file(core_key, "Core.yml", content)
        # 删除密码库
        os.remove("%s.yml" % bank_name)

        # git
        repo = git.Repo.init(".")
        repo.index.add(["Core.yml"])
        repo.index.commit("删除密码库(%s)" % bank_name)

        print("删除密码库(%s)成功" % bank_name)

    # @set_command(command="command", document="document")
    # def f(self, content):
    #     pass


if __name__ == "__main__":
    cmd = KBcmd()
    cmd.start()
