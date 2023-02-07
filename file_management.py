import os
import time
import re
import typing
import random
import shutil
from litetools import YamlRW, Hash, FileOut, System, ProcessStatus, Decorators

if True:
    start_time = time.time()

    def eprint(msg, *args, **kwargs):
        '''带时间的print'''
        kwargs.setdefault("flush", True)
        reltime = round(time.time()-start_time, 2)
        print(f'|{reltime}s|{msg}', *args, **kwargs)
    fileout_ = FileOut()
    fileout_.start()


class FolderStatus:
    def __init__(self, folder_path=".\\") -> None:
        '''
        获取文件夹的相关状态
        :param folder_path: 文件夹路径
        '''
        self.folder_path = os.path.abspath(folder_path)
        ps = ProcessStatus()
        eprint("初始化数据: ", end="")
        # 文件和文件夹扫描
        ps.rewritemsg("扫描文件夹(>>>)计算哈希值(...)")
        filepaths, folder_paths = System.dir_traversing(self.folder_path)
        filepaths.sort()
        folder_paths.sort()
        self.files_data = [
            {
                "abspath": path,
                "relpath": os.path.relpath(path, self.folder_path),
                "sha256": None,
                "size": os.path.getsize(path)
            }
            for path in filepaths]
        self.folders_data = [
            {
                "abspath": path,
                "relpath": os.path.relpath(path, self.folder_path)
            }
            for path in folder_paths]
        # 总体数据统计
        self.file_amount = len(self.files_data)
        self.folder_amount = len(self.folders_data)
        self.folder_size = sum((i["size"] for i in self.files_data))
        progress_count = 0
        progress_size = 0
        last_print_time = time.time()
        # 计算sha256
        ps.rewritemsg("扫描文件夹(done)计算哈希值(>>>)")
        for file in self.files_data:
            progress_count += 1
            progress_size += file["size"]
            path = file["abspath"]
            file["sha256"] = self.file_sha256(path)
            # 进度条
            if time.time() - last_print_time > 1:
                last_print_time = time.time()
                ps.rewritemsg(
                    f"扫描文件夹(done)计算哈希值({progress_count}/{self.file_amount}|{round(progress_size/self.folder_size*100,2 )}%)")
        ps.rewritemsg("扫描文件夹(done)计算哈希值(done)")
        eprint("初始化数据完成")

    @property
    def formatted_status(self):
        '''格式化获取到的文件夹状态'''
        eprint('开始格式化文件夹状态')
        meta_info = {
            'generated_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            'folder_amount': self.folder_amount,
            'file_amount': self.file_amount,
            'folder_size': self.folder_size,
            'folder_path': self.folder_path,
            'mac_address': System.get_mac_address()
        }
        file_status = ["|-|".join([file['relpath'], file['sha256'],
                                   str(file['size'])]) for file in self.files_data]
        folder_status = [i["relpath"] for i in self.folders_data]
        formatted_status = {
            'abstract': meta_info,
            'files': file_status,
            'folders': folder_status,
        }
        eprint('格式化文件夹状态完成')
        return formatted_status

    @staticmethod
    def file_sha256(absPath: str):
        '''带报错的sha256计算'''
        if os.path.isfile(absPath):
            try:
                return Hash.fileHash(absPath, 256)
            except Exception as e:
                eprint('%s计算哈希出错:%s' % (absPath, e))
                return 'sha-256_of_file_calculation_failed'
        else:
            eprint('"%s"是文件夹, 不能计算哈希值' % absPath)
            return "folder_has_no_sha-256"

    @staticmethod
    def list_difference(list_old, list_new) -> tuple[list, list]:
        '''
        获取两个列表的变化, 返回新增的值和删除的值
        :param list_old, list_new: 旧列表和新列表
        :returns deleted, added: 旧列表中删除的 和 新列表中新增的
        '''
        set_old = set(list_old)
        set_new = set(list_new)
        added = set_new.difference(set_old)
        deleted = set_old.difference(set_new)
        added, deleted = list(added), list(deleted)
        added.sort()
        deleted.sort()
        return deleted, added

    def save_data(self, file_dir: str = None):
        '''
        储存数据到yaml文件中
        :param file_dir: 数据文件位置
        '''
        folder_dir = os.path.dirname(file_dir)
        if not os.path.isdir(folder_dir):
            os.makedirs(folder_dir)
        YamlRW.write({
            "status": self.formatted_status,
            "meta": {
                "version": "1.0.0",
            }
        }, file_dir)

    def history_init(self, history_dir: str = None):
        '''
        保证「历史变更数据」文件存在, 如果不存在则初始化一个
        '''
        history_folder_dir = os.path.dirname(history_dir)
        if not os.path.isdir(history_folder_dir):
            os.makedirs(history_folder_dir)
        if not os.path.isfile(history_dir):
            YamlRW.write({
                "history": [],
                "meta": {
                    "version": "1.0.0",
                }
            }, history_dir)

    def update_data(self, data_dir: str = None, history_dir: str = None, only_scan_and_print=False):
        '''
        更新yaml文件中的数据
        :param data_dir: 数据文件位置
        :param history_dir: 历史变化记录数据
        :param only_scan_and_print: (bool)如果为True, 则仅扫描变化并输出, 不更新文件(但如果没有相应的数据文件, 还是会创建并保存)
        '''
        eprint("即将更新yaml中的数据")
        if not os.path.isfile(history_dir):
            eprint(f"「{history_dir}」不存在, 正在创建")
            self.history_init(history_dir)
            eprint("创建完毕")
        if not os.path.isfile(data_dir):
            eprint(f"「{data_dir}」不存在, 正在创建")
            self.save_data(data_dir)
            eprint("创建完毕")
            return
        # 载入数据
        eprint("正在载入数据")
        old_data = YamlRW.load(data_dir)
        old_status = old_data["status"]
        new_status = self.formatted_status
        # 扫描文件夹变化
        eprint("正在扫描文件夹变化")
        file_deleted, file_added = self.list_difference(
            old_status["files"], new_status["files"])
        folder_deleted, folder_added = self.list_difference(
            old_status["folders"], new_status["folders"])
        eprint("正在格式化数据")
        format_status_data = {
            "status": self.formatted_status,
            "meta": {
                "version": "1.0.0",
            }
        }
        # 输出
        if only_scan_and_print:
            print(f"="*20)
            print("\n".join([f"- {i}" for i in folder_deleted]))
            print("\n".join([f"+ {i}" for i in folder_added]))
            print("\n".join([f"- {i}" for i in file_deleted]))
            print("\n".join([f"+ {i}" for i in file_added]))
            print(f"="*20)
            return
        # 更新status数据文件
        eprint(f"正在更新状态文件「{data_dir}」")
        YamlRW.write(format_status_data, data_dir)
        eprint("更新完成")
        # 更新history数据文件
        eprint(f"正在记录变更「{history_dir}」")
        format_changes = {'folder_path': os.path.abspath(self.folder_path),
                          'generated_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                          'file_deleted': file_deleted,
                          'file_added': file_added,
                          'folder_deleted': folder_deleted,
                          'folder_added': folder_added,
                          'notion': "auto log",
                          'mac': System.get_mac_address()}
        old_history = YamlRW.load(history_dir)
        old_history["history"].append(format_changes)
        YamlRW.write(old_history, history_dir)
        eprint("记录完成")


class AutoUpdate:
    '''半成品, 用于更新旧版的idx'''

    def __init__(self, folder_path=".\\"):
        self.folder_path = folder_path
        for path in os.listdir(folder_path):
            if re.match(r"^.*\.fileManagement_Index[\\\/]?$", path):
                self.version = "alpha"
                self.idx_path = path
                self.alpha_update()
                break

    def idx_item(self, path):
        '''基于索引文件夹的路径, 获取内部文件的路径'''
        return os.path.join(self.idx_path, path)

    def alpha_update(self):
        # index
        def index_replace(match: re.Match):
            if match.group() == "fileManagement_version":
                return "file_management_version"
            elif match.group() == "uuid":
                return "id"
            elif match.group() == "exid":
                return "status_id"
            else:
                return match.group()

        def index_replace2(match: re.Match):
            if match.group(2) == "创建者(邮箱)":
                return match.group(1)+"创建者"
            elif match.group(2) == "识别号":
                return match.group(1)+"对象识别号"
            elif match.group(2) == "128位16进制(小写字母)随机字符串，识别号创建/改变时随机生成":
                return match.group(1)+"对象状态识别号——128位16进制(小写字母)随机字符串，在创建/更新对象时随机生成"
            else:
                return match.group()

        with open(self.idx_item("index.yml"), "r", encoding="utf-8") as f:
            text = f.read()
            text = text.replace("fileManagement_version: '1.0.0'",
                                "file_management_version: '1.0.0-beta'")
            text = re.sub(r"^\w*", index_replace, text, flags=re.M)
            text = re.sub(r"(# )(.*)$", index_replace2, text, flags=re.M)
        with open(self.idx_item("index.yml"), "w", encoding="utf-8") as f:
            f.write(text)

        # status
        status_path = self.idx_item("status.yml")
        if os.path.isfile(status_path):
            old_data = YamlRW.load(status_path)
            old_data_info = old_data["status"]["info"]
            new_data = {
                "meta": {
                    "version": "1.0.0",
                },
                "status": {
                    "abstract": {
                        'generated_time': old_data_info["generatedTime"],
                        'folder_amount': old_data_info["folderAmount"],
                        'file_amount': old_data_info["fileAmount"],
                        'folder_size': old_data_info["amountSize"],
                        'folder_path': old_data_info["rootAbsPath"],
                        'mac_address': old_data_info["mac"],
                    },
                    "files": old_data["status"]["fileStatusList"],
                    "folders": old_data["status"]["folderStatusList"],
                },
            }
            YamlRW.write(new_data, status_path)

        # history
        history_path = self.idx_item("history.yml")
        if os.path.isfile(history_path):
            old_data = YamlRW.load(history_path)
            old_data_history = [{
                "file_added": i.get("filesAdded", []),
                "file_deleted": i.get("filesDeleted", []),
                "folder_added": i.get("foldersAdded", []),
                "folder_deleted": i.get("foldersDeleted", []),
                "folder_path": i["rootAbsPath"],
                "generated_time": i["generatedTime"],
                "mac": i["mac"],
                "notion": i["notion"],
            } for i in old_data]
            new_data = {
                "meta": {"version": "1.0.0", },
                "history": old_data_history
            }
            YamlRW.write(new_data, history_path)

        # 文件夹改名
        idx_data = YamlRW.load(self.idx_item("index.yml"))
        self.idx_path = os.path.normpath(self.idx_path)
        new_idx_name = f".fmi_{idx_data['id']}"
        new_idx_name = os.path.join(
            os.path.dirname(self.idx_path), new_idx_name)
        os.rename(self.idx_path, new_idx_name)
        self.idx_path = new_idx_name


class FMcmd:
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
        '''开始执行循环'''
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

    '''
    在类初始化过程中, 类当然不可能实例化。所以调用时候也不会传入self。
    而这些函数在 (初始化过程中, 实例化之前) 就被修改并加入到all_commands中, 
    在后续调用中, 其实不是调用实例化对象中的方法, 而是all_commands字典里面的方法。
    这些方法在加入all_commands时 (初始化过程中, 实例化之前) , 还不需要self参数, 而且修饰器也没有把self传递进去,
    所以调用时需要手动传入self。
    '''
    def set_command(command: str = "command", document: str = "no document", all_commands=all_commands):
        '''返回装饰器, 为函数绑定命令'''
        def decorator(method: typing.Callable) -> typing.Callable:
            '''将命令绑定的方法, 添加到命令列表中'''
            all_commands[command] = {
                "method": method,
                "document": document
            }
            return method
        return decorator

    def set_document(command: str, document: str = "no document", all_commands=all_commands):
        '''更改对应命令的文档'''
        if command not in all_commands:
            all_commands[command] = {
                "method": lambda x: x,
                "document": "no document"
            }
        all_commands[command]["document"] = document

    @staticmethod
    def content_resolution(content) -> tuple[list, dict]:
        '''
        [测试中!!!]
        -m asd asdasd -c "ass" 解析为['asdasd']和{'m': 'asd', 'c': 'ass'}
        '''
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
                [f"「{k}」\n{v['document']}" for k, v in self.all_commands.items()])
            print(f"""====================help====================
{all_command_help}
「exit」「quit」
退出
====================help====================""")
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

    # @set_command(command="command", document="document")
    # def f(self, content):
    #     pass

    @set_command(command="init", document="新建fm对象")
    def fm_init(self, content):
        fmo_name = input('请输入对象名\n>')
        fmo_id_len = input('请输入对象类型(子对象:8|可变对象:12|不可变对象:16)\n>')
        fm_ver = "1.0.0-beta"
        print('fm_ver: 1.0.0-beta')
        # 生成基本信息
        fmo_id = str().join(random.choices(
            '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=int(fmo_id_len)))
        fmo_exid = str().join(random.choices(
            '0123456789abcdef', k=128))
        fmo_dir = System.path_join(f"{fmo_name}_{fmo_id}", self.work_dir)
        fmo_inx_dir = os.path.join(fmo_dir, f'.fmi_{fmo_id}')
        fmo_created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

        os.makedirs(fmo_inx_dir)

        file_index_content = f"""file_management_version: '{fm_ver}' # 文件管理的版本
title: '{fmo_name}' # 标题
description: '' # 对此区域的描述
creator: '' # 创建者
created_time: '{fmo_created_time}' # 创建时间(格式 YYYY-MM-DD HH:MM:SS)
id: '{fmo_id}' # 对象识别号
status_id: '{fmo_exid}' # 对象状态识别号——128位16进制(小写字母)随机字符串，在创建/更新对象时随机生成"""
        with open(os.path.join(fmo_inx_dir, "index.yml"), "w", encoding="utf-8") as f:
            f.write(file_index_content)

        shutil.copy2(self.repository_assets(
            "file_management_index_folder_template\\tag_list.yml"), os.path.join(fmo_inx_dir, "tag_list.yml"))
        shutil.copy2(self.repository_assets("file_management_index_folder_template\\tag_extension.yml"),
                     os.path.join(fmo_inx_dir, "tag_extension.yml"))

        fs = FolderStatus(fmo_dir)
        fs.update_data(data_dir=os.path.join(fmo_inx_dir, "status.yml"),
                       history_dir=os.path.join(fmo_inx_dir, "history.yml"))
        eprint("创建完成")

    @set_command(command="update", document="更新fm对象")
    def fm_update(self, content):
        fs = FolderStatus(self.work_dir)
        for i in os.listdir():
            if re.match(r"^.*\.fmi_[\da-zA-Z]+$", i):
                fmo_inx_dir = i
                break
        else:
            eprint("出错了!!!未能找到索引文件夹")
        eprint("找到索引文件夹「{fmo_inx_dir}」")
        fs.update_data(data_dir=os.path.join(fmo_inx_dir, "status.yml"),
                       history_dir=os.path.join(fmo_inx_dir, "history.yml"))

    @set_command(command="scan", document="检查fm对象变动")
    def fm_scan(self, content):
        fs = FolderStatus(self.work_dir)
        for i in os.listdir():
            if re.match(r"^.*\.fmi_[\da-zA-Z]+$", i):
                fmo_inx_dir = i
                break
        else:
            eprint("出错了!!!未能找到索引文件夹")
        eprint("找到索引文件夹「{fmo_inx_dir}」")
        fs.update_data(data_dir=os.path.join(fmo_inx_dir, "status.yml"),
                       history_dir=os.path.join(fmo_inx_dir, "history.yml"), only_scan_and_print=True)

    @set_command(command="test_update", document="[测试功能]将本文件夹的fmi更新")
    def test(self, content):
        au = AutoUpdate(self.work_dir)


if __name__ == "__main__":
    cmd = FMcmd()
    cmd.start()
