import os
import os.path
import hashlib
import yaml
import time
import uuid
import random


class GeneralTools:
    def __init__(self):
        self.time = time.time()
        self.allErr = ''
        self.allLog = ''
        self.get_mac_address()

    def err(self, *arg):
        for item in arg:
            errStr = '|%fs:err|%s' % (time.time()-self.time, str(item))
            print(errStr)
            self.allErr += errStr+'\n'

    def log(self, *arg):
        for item in arg:
            logStr = '|%fs:log|%s' % (time.time()-self.time, str(item))
            print(logStr)
            self.allLog += logStr+'\n'

    def pr(self, *arg):
        for item in arg:
            prStr = '|%fs|%s' % (time.time()-self.time, str(item))
            print(prStr)

    # 相对路径转绝对路径(稳定性待定)
    def pathJoin(self, path, startPath):
        # 检查是否为路径
        if not (os.path.isdir(path) or os.path.isdir(startPath) or os.path.isfile(path)):
            self.err('error!')
            raise Exception('error!')
        # 检查起点是否为文件，是：取其目录
        if os.path.isfile(startPath):
            startPath = os.path.dirname(startPath)
        # 检查路径是否为绝对路径，是：返回目录
        if os.path.isabs(path):
            return path

        # 格式化路径
        startPath = os.path.abspath(startPath)
        path = os.path.normpath(path)

        # 检查是否没有追溯上层目录
        for c in path.split('\\')[0]:
            if c != '.':
                return startPath+'\\'+path

        # 追溯上层目录
        path_split = path.split('\\', 1)
        startPath = startPath.split('\\')
        backTimes = len(path_split[0])  # 统计点的数量
        if backTimes > len(startPath):
            self.err('error!')
            raise Exception('error!')
        else:
            relpath_ = ''
            for i in range(len(startPath)-backTimes+1):
                relpath_ += startPath[i]+'\\'
            if len(path_split) == 1:
                return os.path.normpath(relpath_)
            else:
                relpath_ += path_split[1]
                return os.path.normpath(relpath_)

    def loadYml(self, ymlFileName='dict.yml'):
        self.pr('正在载入%s' % ymlFileName)
        with open(ymlFileName, 'r', encoding="utf-8") as file:
            item = yaml.load(file, Loader=yaml.FullLoader)
            self.pr('载入完成')
            return item

    def writeYml(self, item, ymlFileName='dict.yml'):
        self.pr('正在写入%s' % ymlFileName)
        with open(ymlFileName, 'w', encoding='utf-8') as file:
            yaml.dump(item, file, allow_unicode=True)
            self.pr('写入完成')
    # 计算单个文件的哈希值

    def fileHashing(self, absPath: str, HashType: int):
        if os.path.isfile(absPath):
            try:
                with open(absPath, "rb") as f:
                    if HashType == 1:
                        hashObj = hashlib.sha1()
                    if HashType == 224:
                        hashObj = hashlib.sha224()
                    if HashType == 256:
                        hashObj = hashlib.sha256()
                    if HashType == 384:
                        hashObj = hashlib.sha384()
                    if HashType == 512:
                        hashObj = hashlib.sha512()
                    if HashType == 5:
                        hashObj = hashlib.md5()

                    for byte_block in iter(lambda: f.read(1048576), b""):
                        hashObj.update(byte_block)
                    return hashObj.hexdigest()
            except Exception as e:
                self.err('%s计算哈希出错:%s' % (absPath, e))
                return 'Error!'
        else:
            self.err('"%s"是文件夹，不能计算哈希值' % absPath)
            return 'Error!I\'m a folder!'

    def get_mac_address(self):
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        mac = ":".join([mac[e:e+2] for e in range(0, 11, 2)])
        self.mac = mac
        return self.mac

    def writefile(self,path,str_:str):
        with open(path,'w',encoding='utf-8') as f:
            f.write(str_)

    def readfile(self,path):
        with open(path,'r',encoding='utf-8') as f:
            str_=f.read()
        return str_

class FolderStatus:
    def __init__(self, path='.\\', indexPath='.FileManagement_Index\\', gt: GeneralTools = GeneralTools()):
        # 载入参数
        self.gt = gt

        self.path = os.path.abspath(path)+'\\'
        self.indexPath = self.gt.pathJoin(indexPath, self.path)+'\\'

        self.statusPath = self.indexPath + 'status.yml'
        self.historyPath = self.indexPath + 'history.yml'

    # 获取文件夹内所有文件夹和文件的路径
    def getAbsPathList(self):
        self.gt.pr('遍历获取文件夹(%s)内的所有路径' % (os.path.abspath(self.path)))
        filePath_List = []
        folderPath_List = [self.path]

        for root, dirs, files in os.walk(self.path):
            for name in files:
                filePath_List.append(os.path.join(root, name))
            for name in dirs:
                folderPath_List.append(os.path.join(root, name))

        # 写入数据
        self.filePath_List = filePath_List
        self.folderPath_List = folderPath_List

    # 获取所有文件的相对路径(相对于self.path)、哈希值(sha256)、大小。并组合为字符串存入列表。
    def getAllFilesStatus(self):
        fileStatus_List = []
        amountSize = 0
        fileAmount = len(self.filePath_List)
        progress = 0  # 执行进度显示

        self.gt.pr(f'计算文件({fileAmount})哈希值')
        for path in self.filePath_List:
            # 执行进度显示
            progress += 1
            if progress % 100 == 0:
                self.gt.pr('%d/%d' % (fileAmount, progress))

            FileSha256 = self.gt.fileHashing(path, 256)
            FileSize = os.path.getsize(path)
            amountSize += FileSize
            fileStatus_List.append('%s|-|%s|-|%d' %
                                   (os.path.relpath(path, self.path), FileSha256, FileSize))
        self.gt.pr('文件哈希计算完毕(大小:%d)(数量:%d)' % (amountSize, fileAmount))

        self.fileAmount = fileAmount
        self.fileStatus_List = fileStatus_List
        self.amountSize = amountSize

    # 获取所有文件夹的相对路径(相对于self.path)，并组合为字符串存入列表。
    def getAllFoldersStatus(self):
        foldersStatus_List = []
        for path in self.folderPath_List:
            foldersStatus_List.append(os.path.relpath(path, self.path))
        self.folderStatus_List = foldersStatus_List

    # 格式化获取到的文件夹状态
    def formattingStatus(self):
        self.gt.pr('开始格式化文件夹状态')
        info = {'generatedTime': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), 'folderAmount': len(self.folderPath_List), 'fileAmount': len(
            self.filePath_List), 'amountSize': self.amountSize, 'rootAbsPath': os.path.abspath(self.path), 'mac': self.gt.mac}
        formattedStatus = {'status': {
            'info': info, 'folderStatusList': self.folderStatus_List, 'fileStatusList': self.fileStatus_List}}

        self.formattedStatus = formattedStatus

    # 检查文件夹的变更
    def getChanges(self):
        statusPath = self.statusPath
        new_folderStatus = self.formattedStatus
        if os.path.isfile(statusPath):
            self.gt.pr('查询并生成文件和文件夹的更改')

            old_folderStatus = self.gt.loadYml(statusPath)

            new_folderStatusSet = set(
                new_folderStatus['status']['folderStatusList'])
            old_folderStatusSet = set(
                old_folderStatus['status']['folderStatusList'])
            new_fileStatusSet = set(
                new_folderStatus['status']['fileStatusList'])
            old_fileStatusSet = set(
                old_folderStatus['status']['fileStatusList'])

            foldersAdded = list(
                new_folderStatusSet.difference(old_folderStatusSet))
            foldersDeleted = list(
                old_folderStatusSet.difference(new_folderStatusSet))
            filesAdded = list(
                new_fileStatusSet.difference(old_fileStatusSet))
            filesDeleted = list(
                old_fileStatusSet.difference(new_fileStatusSet))

            changes = {'rootAbsPath': os.path.abspath(self.path), 'generatedTime': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), 'foldersAdded': foldersAdded, 'foldersDeleted': foldersDeleted,
                       'filesAdded': filesAdded, 'filesDeleted': filesDeleted, 'notion': "Update Status.", 'mac': self.gt.mac}
        else:
            changes = {'rootAbsPath': os.path.abspath(self.path), 'generatedTime': time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime()), 'notion': "Initialize.", 'mac': self.gt.mac}

        self.changes = changes

    # 更新信息
    def updateStatus(self):
        if not os.path.isdir(self.indexPath):
            os.makedirs(self.indexPath)

        self.gt.pr('更新文件夹状态数据')
        self.gt.writeYml(self.formattedStatus, self.statusPath)

        self.gt.pr('记录更新历史')
        if os.path.isfile(self.historyPath):
            history = self.gt.loadYml(self.historyPath)
            history.append(self.changes)
            self.gt.writeYml(history, self.historyPath)
        else:
            self.gt.writeYml([self.changes], self.historyPath)

    # 代码测试中!!!
    def showChangedFolder(self, changedFiles: set, folderAdded: set, folderDeleted: set, maxDeep: int = 3):
        # 逐级展示文件夹变动
        for deep in range(1, maxDeep+1):
            print('==%d级文件夹的变动==' % deep)
            # 新增的文件夹
            drf_added = set()
            for item in folderAdded:
                if item.count('\\') == deep:
                    drf_added.add(item)
            self.printSet(drf_added, '+ ')

            # 删除的文件夹
            drf_deleted = set()
            for item in folderDeleted:
                if item.count('\\') == deep:
                    drf_deleted.add(item)
            self.printSet(drf_deleted, '- ')

            # 有内部更改的文件夹
            drf_changed = set()
            for item in changedFiles:
                if item.count('\\') >= deep:
                    drf_changed.add(self.pathIntercept(item, deep))
            for item in folderAdded+folderDeleted:
                if item.count('\\') > deep:
                    drf_changed.add(self.pathIntercept(item, deep))
            drf_changed.difference_update(drf_added)
            drf_changed.difference_update(drf_deleted)
            self.printSet(drf_changed, '% ')

    # 将路径裁剪为level级
    @staticmethod
    def pathIntercept(path: str, level: int):
        new_path = ''
        for i in path.split("\\")[0:level]:
            new_path += i+'/'
        return new_path

    @staticmethod
    def printSet(set_: set = set(), head: str = ''):
        if set_:
            for item in set_:
                print(head+item)
        else:
            print('', end='')


class CommandExecute:
    def __init__(self, gt: GeneralTools = GeneralTools()):
        self.folderPath = '.'
        self.indexPath = '.fileManagement_Index'
        self.gt = gt

    def cmd_help(self):
        print('''help                    打开帮助
update                  初始化/更新索引信息
exit                    退出
cd [路径]               改变当前目录
obj_init                **测试功能**''')

    def cmd_cd(self, dir_):
        self.folderPath = self.gt.pathJoin(dir_, self.folderPath)

    def cmd_update(self):
        fs = FolderStatus(self.folderPath, self.indexPath, self.gt)
        fs.getAbsPathList()
        fs.getAllFilesStatus()
        fs.getAllFoldersStatus()
        fs.formattingStatus()
        fs.getChanges()
        fs.updateStatus()

    def cmd_obj_init(self):
        name = input('请输入对象名\n>')
        objIdlen = input('请输入对象类型(子对象:8|可变对象:12|不可变对象:16)\n>')
        fm_ver = input('请输入文件管理版本\n>')
        objId = str().join(random.choices(
            '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=int(objIdlen)))
        objexId = str().join(random.choices(
            '0123456789abcdef', k=128))
        obj_path = self.gt.pathJoin('%s_%s' % (name, objId), self.folderPath)
        ftime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        os.makedirs(obj_path)
        os.makedirs(obj_path+'\\.fileManagement_Index')
        indexstr=f"fileManagement_version: '{fm_ver}' # 文件管理的版本\ntitle: '{name}' # 标题\ndescription: '' # 对此区域的描述\ncreator: '' # 创建者(邮箱)\ncreated_time: '{ftime}' # 创建时间(格式 YYYY-MM-DD HH:MM:SS)\nuuid: '{objId}' # 识别号\nexid: '{objexId}' # 128位16进制(小写字母)随机字符串，识别号创建/改变时随机生成"
        self.gt.writefile(obj_path+'\\.fileManagement_Index\\index.yml',indexstr)
        tag_liststr=self.gt.readfile('./format/tag_list.yml')
        self.gt.writefile(obj_path+'\\.fileManagement_Index\\tag_list.yml',tag_liststr)
        tag_exstr=self.gt.readfile('./format/tag_extension.yml')
        self.gt.writefile(obj_path+'\\.fileManagement_Index\\tag_extension.yml',tag_exstr)


def main():
    gt = GeneralTools()
    ce = CommandExecute(gt)

    ce.cmd_cd("D:\Domain") # 临时性修改!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    while 1:
        print('请输入指令(输入“help”获取帮助)')
        inputStr = input('%s>' % os.path.abspath(ce.folderPath))
        inputArgs = inputStr.split(' ')
        if inputArgs[0] == 'help':
            ce.cmd_help()
        elif inputArgs[0] == 'update':
            ce.cmd_update()
        elif inputArgs[0] == 'cd':
            ce.cmd_cd(inputArgs[1])
        elif inputArgs[0] == 'exit':
            exit()
        elif inputArgs[0] == 'quick_update':
            pass
        elif inputArgs[0] == 'check':
            pass
        elif inputArgs[0] == 'history':
            pass
        elif inputArgs[0] == 'obj_init':
            ce.cmd_obj_init()
        elif inputArgs[0] == 'domain_backup':
            pass
        elif inputArgs[0] == 'domain_environment':
            pass
        else:
            print('指令错误(输入指令“help”获取帮助)')


if __name__ == '__main__':
    main()
