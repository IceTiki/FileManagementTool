import scrypt
import time
import psutil
from Crypto.Cipher import AES
from argon2 import PasswordHasher
import math
import hashlib
import os
import yaml
import re
import random


class Lite_AesStringCrypto:
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
        decrypto_str = Lite_AesStringCrypto(password).decrypt(str_)
        if writeIn:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(decrypto_str)
        return decrypto_str

    @staticmethod
    def encrypto(password: str, path: str, str_: str = None, writeIn=True):
        if str_ == None:
            with open(path, 'r', encoding='utf-8') as f:
                str_ = f.read()
        encrypto_str = Lite_AesStringCrypto(password).encrypt(str_)
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
    def getInfomationEntropy(str_: str, pr=1):
        strLen = len(str_)
        set_ = set(str_)
        infomationEntropy = 0
        for i in set_:
            charCount = str_.count(i)
            entroptForChar = -(charCount/strLen)*math.log(charCount/strLen, 2)
            infomationEntropy += entroptForChar
        if pr:
            print('='*64+'\n密码长度——%d\n信息熵(单个字符)——%f\n编码极限(bit)——%f\n\n单字符信息量%f/字符集大小%d=字符利用率%f' %
                  (len(str_), infomationEntropy, infomationEntropy*len(str_), 2**infomationEntropy, len(set(str_)), 2**infomationEntropy/len(set(str_))))
        return infomationEntropy

    @staticmethod
    def creatGitIgnore():
        with open('.gitignore', 'w', encoding='utf-8') as f:
            f.write('*.key')

def creatNewKey():
    # 说明
    print('='*64+'\n使用scrypt进行硬内存哈希生成密钥\n参数:N=2^20, salt=\'TikiEssential.Security\'(utf-8), r=8, p=1, buflen=64')
    # 初始化
    var_N = 2**20
    salt = 'TikiEssential.Security'
    password = input('='*64+'\n请输入 密码\n>')
    # 内存检查
    mem = psutil.virtual_memory()
    if mem.free < var_N:
        input('内存不足警告!!!!!计算需求内存为%dMB，计算机空余内存为%dMB' %
              (1024, mem.free/1024/1024))
        return

    getInfomationEntropy(password)
    st = time.time()
    # scrypt生成密钥
    h = scrypt.hash(password, salt, var_N).hex()
    # argon2id生成密码验证字符串
    ph = PasswordHasher(time_cost=10, memory_cost=var_N)
    checkstr = ph.hash(password)

    ext = time.time()-st

    print('='*64+'\n计算时间%fs\n参数:r=8,p=1,buflen=64,N=%d,sale=\'TikiEssential.Security\'(utf-8)\n密钥:     %s\n密码验证字符串:     %s' %
          (ext, var_N, h, checkstr))
    input('按Enter继续\n')


def checkPassword():
    checkstr = input('='*64+'\n请输入 密码验证字符串\n>')
    password = input('='*64+'\n请输入 密码\n>')
    ph = PasswordHasher()
    try:
        re = ph.verify(checkstr, password)
        print('密码正确:%s' % re)
    except:
        print('密码错误')
    input('按Enter继续\n')


def getInfomationEntropy(str_: str):
    strLen = len(str_)
    set_ = set(str_)
    infomationEntropy = 0
    for i in set_:
        charCount = str_.count(i)
        entroptForChar = -(charCount/strLen)*math.log(charCount/strLen, 2)
        infomationEntropy += entroptForChar
    print('='*64+'\n密码长度——%d\n信息熵(单个字符)——%f\n编码极限(bit)——%f\n\n单字符信息量%f/字符集大小%d=字符利用率%f' %
          (len(str_), infomationEntropy, infomationEntropy*len(str_), 2**infomationEntropy, len(set(str_)), 2**infomationEntropy/len(set(str_))))
    return infomationEntropy


class cmd:
    @staticmethod
    def gene():
        # 说明
        print('='*64+'\n使用scrypt进行硬内存哈希生成密钥\n参数:N=2^20, salt=\'TikiEssential.Security\'(utf-8), r=8, p=1, buflen=64')
        # 初始化
        var_N = 2**20
        salt = 'TikiEssential.Security'
        password = input('='*64+'\n请输入 密码\n>')
        # 内存检查
        mem = psutil.virtual_memory()
        if mem.free < var_N*1024:
            input('内存不足警告!!!!!计算需求内存为%dMB，计算机空余内存为%dMB' %
                  (1024, mem.free/1024/1024))
            return
        # 检查密码强度
        getInfomationEntropy(password)

        # 开始生成加密字符串
        st = time.time()
        # scrypt生成密钥
        corekey = scrypt.hash(password, salt, var_N).hex()
        # argon2id生成密码验证字符串
        checkstr = PasswordHasher(
            time_cost=10, memory_cost=var_N).hash(password)
        ext = time.time()-st

        resu_str = '='*64 + \
            '\n计算时间%fs\n参数:r=8,p=1,buflen=64,N=%d,sale=\'TikiEssential.Security\'(utf-8)\n核心密钥:\n%s\n密码验证字符串:\n%s' % (
                ext, var_N, corekey, checkstr)

        while 1:
            i_str = input(
                '='*64+'\n是否请选择密钥输出模式，可多选(T:命令行输出,F:文件输出,E:生成密钥文件,C:生成密钥验证文件)\n>')
            rdid = ''.join(random.choices('0123456789abcdef', k=64))
            if 'F' in i_str:
                with open(rdid+'.txt', 'w', encoding='utf-8') as f:
                    f.write(resu_str)
                print('='*64+'\n文件输出成功')
            if 'E' in i_str:
                GT.encrypto(GT.sha256(rdid+'TikiEssential.Security'), rdid+'.key', corekey)
                GT.creatGitIgnore()
                print('='*64+'\n生成密钥文件成功')
            if 'C' in i_str:
                with open(rdid+'.check', 'w', encoding='utf-8') as f:
                    f.write(checkstr)
                print('='*64+'\n生成密钥验证文件成功')
            if 'T' in i_str:
                print(resu_str)
                input('按Enter继续\n')
            break

    @staticmethod
    def check():
        i_str = input('='*64+'\n请输入密钥验证字符串或密钥验证文件的路径\n>')
        if re.match('^\\$argon2i?d?\\$v=\\d+\\$m=\\d+,t=\\d+,p=\\d+\\$[a-zA-Z0-9\\/\\+]{22}\\$[a-zA-Z0-9\\/\\+]{22}$', i_str):
            checkstr = i_str
        elif re.match('^.*[a-f0-9]{64}.check$', i_str):
            with open(i_str, 'r', encoding='utf-8') as f:
                f_str = f.read()
            if re.match('^\\$argon2i?d?\\$v=\\d+\\$m=\\d+,t=\\d+,p=\\d+\\$[a-zA-Z0-9\\/\\+]{22}\\$[a-zA-Z0-9\\/\\+]{22}$', f_str):
                checkstr = f_str
            else:
                print('密钥验证文件错误')
                return
        else:
            print('输入错误')
            return

        i_key = input('='*64+'\n请输入 密码\n>')

        # 内存检查
        mem = psutil.virtual_memory()
        if mem.free < 2**30:
            input('内存不足警告!!!!!计算需求内存为%dMB，计算机空余内存为%dMB' %
                  (1024, mem.free/1024/1024))
            return

        try:
            PasswordHasher().verify(checkstr, i_key)
            input('='*64+'\n密码正确')
        except:
            input('='*64+'\n密码错误')

    @staticmethod
    def help():
        print('''
        指令列表
        help: 帮助
        gene: 生成核心密钥
        check: 检查核心密钥
        exit: 退出
        ''')


if __name__ == '__main__':
    while 1:
        i_str = input('开始|输入help获取帮助\n>')
        if i_str == 'help':
            cmd.help()
        elif i_str == 'gene':
            cmd.gene()
        elif i_str == 'check':
            cmd.check()
        elif i_str == 'exit':
            exit()
        else:
            print('输入错误')
