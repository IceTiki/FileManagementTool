from Crypto.Cipher import AES
import hashlib
import os
import time
import git
import yaml
import re


class StandardAesStringCrypto:
    def __init__(self, secret_key: str):
        """
        :param secret_key: 密钥
        """
        self.charset = 'utf-8'

        hash = hashlib.sha256()
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


class GT:
    @staticmethod
    def decrypto(password: str, path: str, str_: str = None, writeIn=False):
        if str_ == None:
            with open(path, 'r', encoding='utf-8') as f:
                str_ = f.read()
        decrypto_str = StandardAesStringCrypto(password).decrypt(str_)
        if writeIn:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(decrypto_str)
        return decrypto_str

    @staticmethod
    def encrypto(password: str, path: str, str_: str = None, writeIn=True):
        if str_ == None:
            with open(path, 'r', encoding='utf-8') as f:
                str_ = f.read()
        encrypto_str = StandardAesStringCrypto(password).encrypt(str_)
        if writeIn:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(encrypto_str)
        return encrypto_str

    @staticmethod
    def formTime():
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    @staticmethod
    def yaml(item):
        '''dict与yaml互转'''
        if type(item) == dict:
            return str(yaml.dump(item, allow_unicode=True))
        elif type(item) == str:
            return dict(yaml.load(item, Loader=yaml.FullLoader))
        else:
            raise '转换错误'

    @staticmethod
    def sha256(str_: str):
        '''计算字符串的哈希256值'''
        bytes_ = str_.encode('utf-8')
        h = hashlib.sha256()
        h.update(bytes_)
        return h.hexdigest()

    @staticmethod
    def getCoreKey():
        coreKey = input('请输入核心密钥\n>')
        if re.match("^[a-f0-9]{128}$", coreKey):
            return coreKey
        elif os.path.isfile(coreKey) and re.match("^.*[a-f0-9]{64}.key$", coreKey):
            try:
                coreKeyPath = coreKey
                coreKey = GT.decrypto(GT.sha256(coreKeyPath[-68:-4]+'TikiEssential.Security'), coreKey)
                if re.match("^[a-f0-9]{128}$", coreKey):
                    print('读取密钥文件成功')
                    return coreKey
                else:
                    return None
            except:
                return None
        else:
            print('密钥错误，核心密钥是128位的十六进制数!!!')
            return None


class cmd:
    @staticmethod
    def help():
        print('''
        指令列表
        help: 帮助
        init_core: 创建核心密码库
        init_bank: 创建密码库
        delete_bank: 删除密码库
        update_bank: 更新密码库
        exit: 退出
        ''')

    @staticmethod
    def init_core():
        # 检查文件
        if os.path.isfile('KeyBank/Core.yml'):
            print('Core.yml已经存在，请检查删除后进行创建')
            return

        # 输入核心密钥
        coreKey = GT.getCoreKey()

        GT.encrypto(coreKey, 'KeyBank/Core.yml', 'banks: []', True)

        repo = git.Repo.init('.')
        repo.index.add(['KeyBank/Core.yml'])
        repo.index.commit('创建核心密码库')
        print('创建核心密码库成功')

    @staticmethod
    def init_bank():
        # 读取核心密码库
        if not os.path.isfile('KeyBank/Core.yml'):
            print('请先创建核心密码库')
            return
        coreKey = GT.getCoreKey()
        try:
            text = GT.decrypto(coreKey, 'KeyBank/Core.yml')
        except Exception as e:
            print('解密失败:%s' % e)
            return
        # 输入新建密码库配置
        while 1:
            bankName = input('请输入密码库名\n>')
            if not re.match('^[A-Z][A-Z0-9]*$', bankName):
                print('密码库名格式错误')
            elif os.path.isfile('KeyBank/%s.yml' % bankName):
                print('密码库已存在')
                return
            else:
                break
        bankKey = input('请输入密码库密码\n>')
        bankdetails = ''
        print('请输入密码库简介(多行，输入end结束)')
        while 1:
            i_str = input('>')
            if i_str == 'end':
                break
            else:
                bankdetails += i_str + '\n'
        # 修改核心密码库
        dict_ = GT.yaml(text)
        dict_['banks'].append(
            {'bankName': bankName, 'key': bankKey, 'details': bankdetails, 'decommissionTime': None, 'createdTime': GT.formTime()})
        text = GT.yaml(dict_)
        # 写入核心密码库
        GT.encrypto(coreKey, 'KeyBank/Core.yml', text)
        # 创建密码库
        init_bank_str = '''keys: \n  - keyIndex: "%sindex" # 密钥索引\n    key: "%s" # 密钥\n    details: 核心密码库分配密钥(核心密钥与密码库名拼接后字符串的sha-256值) # 详情\n    # 时间格式 YYYY-MM-DD HH:MM:SS\n    decommissionTime:  # 弃用时间，默认为空。当密钥索引不再使用时，不进行删除，而是填入弃用时间。\n    createdTime: %s # 创建时间\nfunctions: \n  - funcIndex: %sindex()\n    details: | # 详情\n      f(string):核心密码库分配生成函数\n        return 核心密码库分配密钥(%sindex)与string拼接后字符串的sha-256值\n    # 时间格式 YYYY-MM-DD HH:MM:SS\n    decommissionTime:  # 弃用时间，默认为空。当生成函数不再使用时，不进行删除，而是填入弃用时间。\n    createdTime: %s # 创建时间''' % (
            bankName, GT.sha256(coreKey+bankName), GT.formTime(), bankName, bankName, GT.formTime())
        GT.encrypto(bankKey, 'KeyBank/%s.yml' %
                    bankName, init_bank_str)

        # git
        repo = git.Repo.init('.')
        repo.index.add(['KeyBank/Core.yml', 'KeyBank/%s.yml' % bankName])
        repo.index.commit('创建密码库(%s)' % bankName)

        print('创建密码库(%s)成功' % bankName)

    @staticmethod
    def update_bank():
        bankName = input('请输入密码库名\n>')
        if not os.path.isfile('KeyBank/%s.yml' % bankName):
            print('密码库不存在')
            return
        bankKey = input('请输入密码库密码\n>')

        # 解密文件
        try:
            GT.decrypto(bankKey, 'KeyBank/%s.yml' % bankName, writeIn=True)
        except Exception as e:
            print('解密失败:%s' % e)
            return

        # 等待修改
        input('解密完成: 按Enter重新加密文件\n(警告:请勿退出此界面)\n>')

        # 加密文件
        GT.encrypto(bankKey, 'KeyBank/%s.yml' % bankName, writeIn=True)

        # git
        repo = git.Repo.init('.')
        repo.index.add(['KeyBank/%s.yml' % bankName])
        repo.index.commit('更新密码库(%s)' % bankName)

        print('更新密码库(%s)成功' % bankName)

    @staticmethod
    def delete_bank():
        # 读取核心密码库
        if not os.path.isfile('KeyBank/Core.yml'):
            print('请先创建核心密码库')
            return
        # 输入核心密钥
        coreKey = GT.getCoreKey()
        try:
            text = GT.decrypto(coreKey, 'KeyBank/Core.yml')
        except Exception as e:
            print('解密失败:%s' % e)
            return
        # 获取要删除的密码库
        bankName = input('请输入密码库名\n>')
        if not os.path.isfile('KeyBank/%s.yml' % bankName):
            print('密码库不存在')
            return
        confirm_i = input('请输入"delete %s"确认删除\n>' % bankName)
        if confirm_i != 'delete %s' % bankName:
            print('输入错误')
            return
        # 修改
        dict_ = GT.yaml(text)
        finded = 0
        for item in dict_['banks']:
            if item['bankName'] == bankName and item['decommissionTime'] == None:
                item['decommissionTime'] = GT.formTime()
                print('在核心密钥库中找到此密码库的记录')
                finded = 1
                break
        if not finded:
            print('未能在核心密钥库中找到此密码库的记录')
            return
        text = GT.yaml(dict_)
        # 将修改写入核心密码库
        GT.encrypto(coreKey, 'KeyBank/Core.yml', text)
        # 删除密码库
        os.remove('KeyBank/%s.yml' % bankName)

        # git
        repo = git.Repo.init('.')
        repo.index.add(['KeyBank/Core.yml'])
        repo.index.commit('删除密码库(%s)' % bankName)

        print('删除密码库(%s)成功' % bankName)


def main():
    while 1:
        i_str = input('开始|输入help获取帮助\n>')
        if i_str == 'help':
            cmd.help()
        elif i_str == 'init_core':
            cmd.init_core()
        elif i_str == 'init_bank':
            cmd.init_bank()
        elif i_str == 'delete_bank':
            cmd.delete_bank()
        elif i_str == 'update_bank':
            cmd.update_bank()
        elif i_str == 'exit':
            exit()
        else:
            print('指令错误(输入help获取帮助)\n>')


if __name__ == '__main__':
    main()
