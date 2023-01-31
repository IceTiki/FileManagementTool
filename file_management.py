import os
import time
import re
import typing
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
        eprint("正在初始化数据")
        # 文件和文件夹扫描
        ps.rewritemsg("scan(>>>)hash(...)")
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
        # 计算sha256
        for file in self.files_data:
            progress_count += 1
            progress_size += file["size"]
            path = file["abspath"]
            file["sha256"] = self.file_sha256(path)
            # 进度条
            if progress_count % 100 == 0:
                ps.rewritemsg(
                    f"scan(done)hash({progress_count}/{self.file_amount}|{round(progress_size/self.folder_size*100,2 )}%)")
        ps.rewritemsg()
        eprint("数据初始化完成")

    @property
    def code_directory(self):
        return os.path.dirname(__file__)

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
        added = set_new.difference(set_new)
        deleted = set_old.difference(set_old)
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
            "history": [],
            "data_format_version": "1.0.0",
        }, file_dir)
        return

    def update_data(self, file_dir: str = None, only_scan_and_print=False):
        '''
        更新yaml文件中的数据
        :param file_dir: 数据文件位置
        :param only_scan_and_print: (bool)如果为True, 则仅扫描变化并输出, 不更新文件(但如果没有相应的数据文件, 还是会创建并保存)
        '''
        eprint("即将更新yaml中的数据")
        if not os.path.isfile(file_dir):
            eprint(f"「{file_dir}」不存在, 正在新建文件并保存")
            self.save_data(file_dir)
            eprint("保存完毕")
            return
        # 载入数据
        eprint("正在载入数据")
        history_data = YamlRW.load(file_dir)
        history_status = history_data["status"]
        history_history = history_data["history"]
        new_status = self.formatted_status
        # 扫描文件夹变化
        eprint("正在扫描文件夹变化")
        file_deleted, file_added = self.list_difference(
            history_status["files"], new_status["files"])
        folder_deleted, folder_added = self.list_difference(
            history_status["folders"], new_status["folders"])
        eprint("正在格式化数据")
        # 格式化文件变化
        format_changes = {'folder_path': os.path.abspath(self.path),
                          'generated_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                          'file_deleted': file_deleted,
                          'file_added': file_added,
                          'folder_deleted': folder_deleted,
                          'folder_added': folder_added,
                          'notion': "",
                          'mac': System.get_mac_address()}
        format_data = {
            "status": new_status,
            "history": history_history + [format_changes]
        }
        # 输出
        if not only_scan_and_print:
            eprint("正在更新数据")
            YamlRW.write(format_data, file_dir)
            eprint("更新数据完成")
        print(f"="*20)
        print("\n".join([f"- {i}" for i in folder_deleted]))
        print("\n".join([f"+ {i}" for i in folder_added]))
        print("\n".join([f"- {i}" for i in file_deleted]))
        print("\n".join([f"+ {i}" for i in file_added]))
        print(f"="*20)

class Tikicmd:
    all_commands: dict = {}

    def __init__(self):
        pass

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

# class CommandExecute:
#     def __init__(self, gt: GeneralTools = GeneralTools()):
#         self.folderPath = '.'
#         self.indexPath = '.fileManagement_Index'
#         self.gt = gt

#     def cmd_help(self):
#         print('''help                    打开帮助
# update                  初始化/更新索引信息
# exit                    退出
# cd [路径]               改变当前目录
# obj_init                **测试功能**''')

#     def cmd_cd(self, dir_):
#         self.folderPath = self.gt.pathJoin(dir_, self.folderPath)

#     def cmd_update(self):
#         fs = FolderStatus(self.folderPath, self.indexPath, self.gt)
#         fs.getAbsPathList()
#         fs.getAllFilesStatus()
#         fs.getAllFoldersStatus()
#         fs.formattingStatus()
#         fs.getChanges()
#         fs.updateStatus()

#     def cmd_obj_init(self):
#         name = input('请输入对象名\n>')
#         objIdlen = input('请输入对象类型(子对象:8|可变对象:12|不可变对象:16)\n>')
#         fm_ver = input('请输入文件管理版本\n>')
#         objId = str().join(random.choices(
#             '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=int(objIdlen)))
#         objexId = str().join(random.choices(
#             '0123456789abcdef', k=128))
#         obj_path = self.gt.pathJoin('%s_%s' % (name, objId), self.folderPath)
#         ftime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
#         os.makedirs(obj_path)
#         os.makedirs(obj_path+'\\.fileManagement_Index')
#         indexstr = f"fileManagement_version: '{fm_ver}' # 文件管理的版本\ntitle: '{name}' # 标题\ndescription: '' # 对此区域的描述\ncreator: '' # 创建者(邮箱)\ncreated_time: '{ftime}' # 创建时间(格式 YYYY-MM-DD HH:MM:SS)\nuuid: '{objId}' # 识别号\nexid: '{objexId}' # 128位16进制(小写字母)随机字符串，识别号创建/改变时随机生成"
#         self.gt.writefile(
#             obj_path+'\\.fileManagement_Index\\index.yml', indexstr)
#         tag_liststr = self.gt.readfile('./format/tag_list.yml')
#         self.gt.writefile(
#             obj_path+'\\.fileManagement_Index\\tag_list.yml', tag_liststr)
#         tag_exstr = self.gt.readfile('./format/tag_extension.yml')
#         self.gt.writefile(
#             obj_path+'\\.fileManagement_Index\\tag_extension.yml', tag_exstr)


# def main():
#     gt = GeneralTools()
#     ce = CommandExecute(gt)

#     ce.cmd_cd("D:\Domain")  # 临时性修改!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#     while 1:
#         print('请输入指令(输入“help”获取帮助)')
#         inputStr = input('%s>' % os.path.abspath(ce.folderPath))
#         inputArgs = inputStr.split(' ')
#         if inputArgs[0] == 'help':
#             ce.cmd_help()
#         elif inputArgs[0] == 'update':
#             ce.cmd_update()
#         elif inputArgs[0] == 'cd':
#             ce.cmd_cd(inputArgs[1])
#         elif inputArgs[0] == 'exit':
#             exit()
#         elif inputArgs[0] == 'quick_update':
#             pass
#         elif inputArgs[0] == 'check':
#             pass
#         elif inputArgs[0] == 'history':
#             pass
#         elif inputArgs[0] == 'obj_init':
#             ce.cmd_obj_init()
#         elif inputArgs[0] == 'domain_backup':
#             pass
#         elif inputArgs[0] == 'domain_environment':
#             pass
#         else:
            # print('指令错误(输入指令“help”获取帮助)')


nfs = FolderStatus(r"D:\Domain\Collection_MCfWXEVByGyk")
nfs.update_data(r"C:\Users\Tiki_\Desktop\tmp.yml")
