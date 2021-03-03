#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import re
import sys


def pointers_from_binary(line, binary_file_arch):
    if len(line) < 16:
        return None
    line = line[16:].strip().split(' ')
    pointers = set()
    # 模拟器
    if binary_file_arch == 'x86_64':
        if len(line) >= 8:
            pointers.add(''.join(line[4:8][::-1] + line[0:4][::-1]))
        if len(line) >= 16:
            pointers.add(''.join(line[12:16][::-1] + line[8:12][::-1]))
        return pointers
    # 真机
    if binary_file_arch.startswith('arm'):
        if len(line) >= 2:
            pointers.add(line[1] + line[0])
        if len(line) >= 4:
            pointers.add(line[3] + line[2])
        return pointers
    return None


# 引用的oc类
def refs_class_list(path, binary_file_arch):
    ref_pointers = set()
    lines_array = os.popen('/usr/bin/otool -v -s __DATA __objc_classrefs %s' % path).readlines()
    for line in lines_array:
        pointers = pointers_from_binary(line, binary_file_arch)
        if not pointers:
            continue
        ref_pointers = ref_pointers.union(pointers)
    if len(ref_pointers) == 0:
        exit('Error:木有找到列表啊')

    return ref_pointers


# 所有的oc类
def all_class_list(path, binary_file_arch):
    list_pointers = set()
    lines_array = os.popen('/usr/bin/otool -v -s __DATA __objc_classlist %s' % path).readlines()
    for line in lines_array:
        pointers = pointers_from_binary(line, binary_file_arch)
        if not pointers:
            continue
        list_pointers = list_pointers.union(pointers)
    if len(list_pointers) == 0:
        exit('Error:木有啊')

    return list_pointers


def class_symbols(path):
    print('开始扫描无用代码')
    symbols = {}
    re_class_name = re.compile('(\w{16}) .* _OBJC_CLASS_\$_(.+)')
    lines_array = os.popen('nm -nm %s' % path).readlines()
    for line in lines_array:
        result = re_class_name.findall(line)
        if result:
            (address, symbol) = result[0]
            symbols[address] = symbol
    if len(symbols) == 0:
        exit('Error:空的symbols')
    return symbols


# 无用oc类 = __DATA.__objc_classlist段(objc类列表)和__DATA.__objc_classrefs段(objc引用的class列表)
def unused_class_list(path, reserved_prefix, filter_prefix):
    binary_file_arch = os.environ['ARCHS']
    unused_refs_pointers_set = all_class_list(path, binary_file_arch) - refs_class_list(path, binary_file_arch)
    if len(unused_refs_pointers_set) == 0:
        exit('Finish:空的')

    symbols_dic = class_symbols(path)
    unused_refs_symbols_set = set()
    for unused_ref_pointer in unused_refs_pointers_set:
        if unused_ref_pointer in symbols_dic:
            unused_ref_symbol = symbols_dic[unused_ref_pointer]
            if len(reserved_prefix) > 0 and not unused_ref_symbol.startswith(reserved_prefix):
                continue
            if len(filter_prefix) > 0 and unused_ref_symbol.startswith(filter_prefix):
                continue
            unused_refs_symbols_set.add(unused_ref_symbol)
    if len(unused_refs_symbols_set) == 0:
        exit('Finish:空的')
    return unused_refs_symbols_set


if __name__ == '__main__':

    SCRIPT_DIR = sys.path[0]
    # 环境变量
    env_file_Path = SCRIPT_DIR + '/env.sh'

    envFile = open(env_file_Path, 'r')
    envRe = re.compile('export (.*)=\"(.*)\"')
    for line in envFile.readlines():
        result = envRe.findall(line)
        if result:
            (envKey, envValue) = result[0]
            os.environ[envKey] = envValue
    envFile.close()

    BUILT_PRODUCTS_DIR = os.environ['BUILT_PRODUCTS_DIR'].strip('\r')

    PRODUCT_BUNDLE_IDENTIFIER = os.environ['PRODUCT_BUNDLE_IDENTIFIER'].strip('\r')

    path = BUILT_PRODUCTS_DIR

    print('\n符号目录: %s' % path)

    if not path:
        sys.exit('Error:无效的app路径')
    # 类名前缀
    header_prefix = 'ZR'
    # 类名结尾
    end_prefix = ''

    CODESIGNING_FOLDER_PATH = os.environ['CODESIGNING_FOLDER_PATH'].strip('\r')

    EXECUTABLE_NAME = os.environ['EXECUTABLE_NAME'].strip('\r')

    unused_refs_symbols_set = unused_class_list(CODESIGNING_FOLDER_PATH + '/' + EXECUTABLE_NAME, header_prefix, end_prefix)
    script_path = sys.path[0].strip()

    find_class = open(script_path + '/unused_class.txt', 'w')

    find_class.write('未使用的类数量: %d\n' % len(unused_refs_symbols_set))

    for unused_refs_symbol in unused_refs_symbols_set:
        print('无用类: ' + unused_refs_symbol)
        find_class.write(unused_refs_symbol + "\n")

    find_class.close()

    print('扫描完成 结果已存在unused_class.txt中')

    exit(1)
