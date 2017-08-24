#!/usr/bin/env python
# coding: utf-8

from config import ConfigManager
from config import Constant
from config import Log

import os
import sys
import requests
import qrcode
import time
import json
import traceback
import zbar
from PIL import Image


def echo(str):
    Log.info(str[:-1])
    sys.stdout.write(str)
    sys.stdout.flush()


def warn(str):
    Log.warning(str[:-1])
    sys.stdout.write(str)
    sys.stdout.flush()


def error(str):
    Log.error(str[:-1])
    sys.stdout.write(str)
    sys.stdout.flush()


def run(str, func, *args):
    t = time.time()
    echo(str)
    r = False
    try:
        r = func(*args)
    except:
        error(traceback.format_exc())
    if r:
        total_time = int(time.time() - t)
        echo('成功 %ds \n' % total_time)
    else:
        echo('失败\n')
        exit()


def disableInsecureRequestWarning():
    # 在 python 2.7.9以下版本，此warning会影响到requests请求的返回
    try:
        try:
            urllib3 = requests.packages.urllib3
        except AttributeError:
            import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception as e:
        echo('无法禁用 InsecureRequestWarning ，原因：%s' % e)


def str2qr_terminal(data):
    """
    @brief      convert string to qrcode matrix and outprint
    @param      data   The string
    """
    cm = ConfigManager()
    file_dir = cm.getpath('qrcode_path')
    with open(file_dir, 'wb') as f:
        f.write(data)
    scanner = zbar.ImageScanner()
    scanner.parse_config('enable')
    pil = Image.open(file_dir).convert('L')
    width, height = pil.size
    raw = pil.tobytes()
    image = zbar.Image(width, height, 'Y800', raw)
    scanner.scan(image)
    text = ''
    for symbol in image:
        text += symbol.data
    del image

    echo('二维码表示地址：%s\n' % text)

    qr = qrcode.QRCode()
    qr.border = 1
    qr.add_data(text)
    mat = qr.get_matrix()
    print_qr(mat)


def print_qr(mat):
    for i in mat:
        BLACK = Constant.QRCODE_BLACK
        WHITE = Constant.QRCODE_WHITE
        echo(''.join([BLACK if j else WHITE for j in i])+'\n')


def qHash(x, K):
    N = [0] * 4
    for T in range(len(K)):
        N[T%4] ^= ord(K[T])

    U, V = 'ECOK', [0] * 4
    V[0] = ((x >> 24) & 255) ^ ord(U[0])
    V[1] = ((x >> 16) & 255) ^ ord(U[1])
    V[2] = ((x >>  8) & 255) ^ ord(U[2])
    V[3] = ((x >>  0) & 255) ^ ord(U[3])

    U1 = [0] * 8
    for T in range(8):
        U1[T] = N[T >> 1] if T % 2 == 0 else V[T >> 1]

    N1, V1 = '0123456789ABCDEF', ''
    for aU1 in U1:
        V1 += N1[((aU1 >> 4) & 15)]
        V1 += N1[((aU1 >> 0) & 15)]

    return V1


def bknHash(skey, init_str=5381):
    hash_str = init_str
    for i in skey:
        hash_str += (hash_str << 5) + ord(i)
    hash_str = int(hash_str & 2147483647)
    return hash_str


def trans_coding(data):
    """
    @brief      Transform string to unicode
    @param      data  String
    @return     unicode
    """
    if not data:
        return data
    result = None
    if type(data) == unicode:
        result = data
    elif type(data) == str:
        result = data.decode('utf-8')
    return result


def trans_unicode_into_int(name):
    result = [ord(ch) for ch in name]
    return 'z'.join([str(ch) for ch in result])


def trans_int_into_unicode(table):
    tmp = table.split('z')
    result = [unichr(int(ch)) for ch in tmp[1:]]
    return [tmp[0], ''.join(result)]