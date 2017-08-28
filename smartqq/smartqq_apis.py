#!/usr/bin/env python
# coding: utf-8

from utils import *

import sys
import requests
import time
import random
import json


class WebQQApi(object):

    def __init__(self):
        self.session = None
        self.clientid = 53999199  # 设备ID, 是一个固定值
        # 鉴权参数
        self.urlPtwebqq = None
        self.ptwebqq = None
        self.vfwebqq = None
        self.uin = None
        self.psessionid = None
        # 经过加密处理的鉴权参数
        self.hash = None
        self.bkn = None

        self.send_png = False  # 控制发送二维码

        # 用户信息
        self.user = {
            'qq': None,
            'nick': None
        }

        # 用户联系人，群，讨论组
        self.contact = []
        self.group = []
        self.discuss = []
        self.group_member = {}
        self.discuss_member = {}

    def Login(self):
        self.prepareSession()
        self.waitForAuth()
        self.getPtwebqq()
        self.getVfwebqq()
        self.getUinAndPsessionid()
        # 恢复登陆时只用先TestLogin,具体哪些参数需要保存到本地则需要进一步验证
        return self.TestLogin()

    def prepareSession(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9;'
                           ' rv:27.0) Gecko/20100101 Firefox/27.0'),
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })
        self.url_get(
            url='https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&'
            'style=16&mibao_css=m_webqq&appid=501004106&enable_qlogin=0&'
            'no_verifyimg=1&s_url=http%3A%2F%2Fw.qq.com%2Fproxy.html&'
            'f_url=loginerroralert&strong_login=1&login_state=10&t=20131024001')
        # 先进行一次请求的意义在于获取一些基础的cookies信息
        self.session.cookies.update({
            'RK': 'OfeLBai4FB',
            'pgv_pvi': '911366144',
            'pgv_info': 'ssid pgv_pvid=1051433466',
            'ptcz': ('ad3bf14f9da2738e09e498bfeb93dd9da7'
                     '540dea2b7a71acfb97ed4d3da4e277'),
            'qrsig': ('hJ9GvNx*oIvLjP5I5dQ19KPa3zwxNI'
                      '62eALLO*g2JLbKPYsZIRsnbJIxNe74NzQQ')
        })
        self.getAuthStatus()
        self.session.cookies.pop('qrsig')

    def getQrcode(self, qrcode_url):
        qrcode = self.url_get(url=qrcode_url).content
        return qrcode

    def waitForAuth(self):
        api_qrcode = 'https://ssl.ptlogin2.qq.com/ptqrshow?appid=501004106&e=0&l=M&s=5&d=72&v=4&t='
        try:
            qrcode_url = api_qrcode + str(int(time.time()))
            str2qr_terminal(self.getQrcode(qrcode_url), self.send_png)
            x, y = 1, 1
            count = 0
            while True:
                time.sleep(1)
                authStatus = self.getAuthStatus()
                if '二维码未失效' in authStatus:
                    if x:
                        echo('等待二维码扫描及授权...\n')
                        x = 0
                elif '二维码认证中' in authStatus:
                    if y:
                        echo('二维码已扫描，等待授权...\n')
                        y = 0
                elif '二维码已失效' in authStatus:
                    count += 1
                    if count >= 5:
                        echo('长时间无扫码操作，退出程序...\n')
                        sys.exit()

                    echo('二维码已失效, 重新获取二维码\n')
                    qrcode_url = api_qrcode + str(int(time.time()))
                    str2qr_terminal(self.getQrcode(qrcode_url), self.send_png)
                    x, y = 1, 1
                elif '登录成功' in authStatus:
                    echo('已获授权\n')
                    items = authStatus.split(',')
                    self.user['nick'] = str(items[-1].split("'")[1])
                    self.user['qq'] = str(int(self.session.cookies['superuin'][1:]))
                    self.urlPtwebqq = items[2].strip().strip("'")
                    self.send_png = True  # 重新登录将发送二维码
                    break
                else:
                    error('获取二维码扫描状态时出错, html="%s"\n' % authStatus)
                    sys.exit(1)
        except:
            error(traceback.format_exc())
            sys.exit()

    def getAuthStatus(self):
        result = self.url_get(
            url='https://ssl.ptlogin2.qq.com/ptqrlogin?ptqrtoken=' +
                str(bknHash(self.session.cookies['qrsig'], init_str=0)) +
                '&webqq_type=10&remember_uin=1&login2qq=1&aid=501004106' +
                '&u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1%26' +
                'webqq_type%3D10&ptredirect=0&ptlang=2052&daid=164&' +
                'from_ui=1&pttype=1&dumy=&fp=loginerroralert&action=0-0-' +
                repr(random.random() * 900000 + 1000000) +
                '&mibao_css=m_webqq&t=undefined&g=1&js_type=0' +
                '&js_ver=10141&login_sig=&pt_randsalt=0',
            referer=('https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&'
                     'target=self&style=16&mibao_css=m_webqq&appid=501004106&'
                     'enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2F'
                     'w.qq.com%2Fproxy.html&f_url=loginerroralert&'
                     'strong_login=1&login_state=10&t=20131024001')
        ).content
        return result

    def getPtwebqq(self):
        self.url_get(url=self.urlPtwebqq)
        self.ptwebqq = self.session.cookies['ptwebqq']
        echo('已获取ptwebqq\n')

    def getVfwebqq(self):
        result = self.url_get(
            url=('http://s.web2.qq.com/api/getvfwebqq?ptwebqq=%s&'
                 'clientid=%s&psessionid=&t=%s') %
                (self.ptwebqq, self.clientid, str(int(time.time()))),
            referer=('http://s.web2.qq.com/proxy.html?v=20130916001'
                     '&callback=1&id=1'),
            origin='http://s.web2.qq.com'
        )
        r = json.loads(result.content, object_hook=self._decode_data)
        self.vfwebqq = r['result']['vfwebqq']
        echo('已获取vfwebqq\n')

    def getUinAndPsessionid(self):
        result = self.url_get(
            url='http://d1.web2.qq.com/channel/login2',
            data={
                'r': json.dumps({
                    'ptwebqq': self.ptwebqq, 'clientid': self.clientid,
                    'psessionid': '', 'status': 'online'
                })
            },
            referer=('http://d1.web2.qq.com/proxy.html?v=20151105001'
                     '&callback=1&id=2'),
            origin='http://d1.web2.qq.com'
        )
        r = json.loads(result.content, object_hook=self._decode_data)
        self.uin = r['result']['uin']
        self.psessionid = r['result']['psessionid']
        self.hash = qHash(self.uin, self.ptwebqq)
        self.bkn = bknHash(self.session.cookies['skey'])
        echo('已获取uin和psessionid\n')

    def TestLogin(self):
        flag = False

        if not self.session.verify:
            disableInsecureRequestWarning()
        try:
            # 请求一下 get_online_buddies 页面，避免103错误。
            # 若请求无错误发生，则表明登录成功
            count = 0
            while not flag:
                count += 1
                result = self.url_get(
                    url=('http://d1.web2.qq.com/channel/get_online_buddies2?'
                         'vfwebqq=%s&clientid=%d&psessionid=%s&t=%s') %
                        (self.vfwebqq, self.clientid, self.psessionid, str(int(time.time()))),
                    referer=('http://d1.web2.qq.com/proxy.html?v=20151105001&'
                             'callback=1&id=2'),
                    origin='http://d1.web2.qq.com'
                )
                if result:
                    r = json.loads(result.content, object_hook=self._decode_data)
                    echo(str(r) + '\n')
                    if r['retcode'] == 0:
                        flag = True
                if count >= 3:
                    break
        finally:
            if flag:
                echo('登录账号：%s(%s)\n' % (self.user['nick'], self.user['qq']))
            return flag

    # 获取联系人
    def GetContact(self):
        count = 0
        while True:
            result = self.url_get(
                url='http://s.web2.qq.com/api/get_user_friends2',
                data={
                    'r': json.dumps({'vfwebqq': self.vfwebqq, 'hash': self.hash})
                },
                referer=('http://d1.web2.qq.com/proxy.html?v=20151105001&'
                         'callback=1&id=2')
            )
            count += 1
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                info = r['result']['info']
                friends = r['result']['friends']
                marknames = r['result']['marknames']

                contact = []

                for p in friends:
                    add_contact = {}
                    add_contact['uin'] = p['uin']
                    for i in info:
                        if p['uin'] == i['uin']:
                            add_contact['nick'] = i['nick']
                            break
                    else:
                        error('never in contact name = 0\n')
                        add_contact['nick'] = 0  # 一般不会出现
                    for m in marknames:
                        if p['uin'] == m['uin']:
                            add_contact['markname'] = m['markname']
                            break
                    else:
                        add_contact['markname'] = ''
                    contact.append(add_contact)

                self.contact = contact[:]  # 重置列表，防止重新登录时uin改变导致的错误
                return True
            elif count >= 5:
                break
            else:
                echo('重新获取联系人\n')
                time.sleep(0.2)
        return False

    def GetGroup(self):
        count = 0
        while True:
            result = self.url_get(
                url='http://s.web2.qq.com/api/get_group_name_list_mask2',
                data={
                    'r': json.dumps({'vfwebqq': self.vfwebqq, 'hash': self.hash})
                },
                referer=('http://d1.web2.qq.com/proxy.html?v=20151105001&'
                         'callback=1&id=2')
            )
            count += 1
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                gnamelist = r['result']['gnamelist']
                gmarklist = r['result']['gmarklist']

                group = []

                for g in gnamelist:
                    add_group = {}
                    add_group['gid'] = g['gid']
                    add_group['code'] = g['code']
                    add_group['name'] = g['name']
                    for i in gmarklist:
                        if g['gid'] == i['uin']:
                            add_group['markname'] = i['markname']
                            break
                    else:
                        add_group['markname'] = ''
                    group.append(add_group)

                self.group = group[:]  # 重置列表，防止重新登录时uin改变导致的错误
                return True
            elif count >= 5:
                break
            else:
                echo('重新获取群\n')
                time.sleep(0.2)
        return False

    def GetGroupMember(self, gcode):
        count = 0
        while True:
            result = self.url_get(
                url=('http://s.web2.qq.com/api/get_group_info_ext2?gcode=%s'
                     '&vfwebqq=%s&t=%s') % (gcode, self.vfwebqq, str(int(time.time()))),
                referer=('http://s.web2.qq.com/proxy.html?v=20130916001'
                         '&callback=1&id=1'),
            )
            count += 1
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                return r
            error(str(r) + '\n')
            time.sleep(0.2)
            if count >= 5:
                break
        return None

    def GetDiscuss(self):
        count = 0
        while True:
            result = self.url_get(
                url=('http://s.web2.qq.com/api/get_discus_list?clientid=%s&'
                     'psessionid=%s&vfwebqq=%s&t=%s') %
                    (self.clientid, self.psessionid, self.vfwebqq, str(int(time.time()))),
                referer=('http://d1.web2.qq.com/proxy.html?v=20151105001'
                         '&callback=1&id=2'),
            )
            count += 1
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                dnamelist = r['result']['dnamelist']

                discuss = []

                for d in dnamelist:
                    add_discuss = {}
                    add_discuss['did'] = d['did']
                    if d['name']:
                        add_discuss['name'] = d['name']
                    else:
                        error('never in discuss name = 0\n')
                        add_discuss['name'] = 0  # QQ不同于微信，这个一般也不会出现
                    discuss.append(add_discuss)

                self.discuss = discuss[:]  # 重置列表，防止重新登录时uin改变导致的错误
                return True
            elif count >= 5:
                break
            else:
                echo('重新获取讨论组\n')
                time.sleep(0.2)
        return False

    def GetDiscussMember(self, did):
        count = 0
        while True:
            result = self.url_get(
                url=('http://d1.web2.qq.com/channel/get_discu_info?'
                     'did=%s&psessionid=%s&vfwebqq=%s&clientid=%s&t=%s') %
                    (did, self.psessionid, self.vfwebqq, self.clientid, str(int(time.time()))),
                referer=('http://d1.web2.qq.com/proxy.html?v=20151105001'
                         '&callback=1&id=2')
            )
            count += 1
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                return r
            error(str(r) + '\n')
            time.sleep(0.2)
            if count >= 5:
                break
        return None

    # 消息操作
    def PollMsg(self):
        result = self.url_get(
            url='https://d1.web2.qq.com/channel/poll2',
            data={
                'r': json.dumps({
                    'ptwebqq': self.ptwebqq, 'clientid': self.clientid,
                    'psessionid': self.psessionid, 'key': ''
                })
            },
            referer=('http://d1.web2.qq.com/proxy.html?v=20151105001&'
                     'callback=1&id=2')
        )
        if result:
            r = json.loads(result.content, object_hook=self._decode_data)
        else:
            r = {
                'retcode': -1,
                'errmsg': 'timeout'
            }

        return r

    def send_text(self, s_type, to_id, text):
        if s_type == 1:
            r = self.send_user_text(to_id, text)
            if r and 'errCode' in r:
                return True
            else:
                error(str(r) + '\n')
                return False
        elif s_type == 2:
            r = self.send_group_text(to_id, text)
            if r and 'errCode' in r:
                return True
            else:
                error(str(r) + '\n')
                return False
        elif s_type == 3:
            r = self.send_discuss_text(to_id, text)
            if r and 'errCode' in r:
                return True
            else:
                error(str(r) + '\n')
                return False
        return False

    def send_user_text(self, uin, text):
        result = self.url_get(
            url='http://d1.web2.qq.com/channel/send_buddy_msg2',
            data={
                'r': json.dumps({
                    'to': uin,
                    'content': json.dumps([
                        text,
                        [
                            'font',
                            {
                                "name": "宋体",
                                "size": 10,
                                "style": [
                                    0,
                                    0,
                                    0
                                ],
                                "color": "000000"
                            }
                        ]
                    ]),
                    "face": 522,
                    "clientid": self.clientid,
                    "msg_id": 6000000 + int(time.time()) % 1000000,
                    "psessionid": self.psessionid,
                })
            },
            referer='http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        if result:
            r = json.loads(result.content, object_hook=self._decode_data)
        else:
            r = {
                'retcode': -1,
                'errmsg': 'timeout'
            }

        return r

    def send_group_text(self, gid, text):
        result = self.url_get(
            url='http://d1.web2.qq.com/channel/send_qun_msg2',
            data={
                'r': json.dumps({
                    'group_uin': gid,
                    'content': json.dumps([
                        text,
                        [
                            'font',
                            {
                                "name": "宋体",
                                "size": 10,
                                "style": [
                                    0,
                                    0,
                                    0
                                ],
                                "color": "000000"
                            }
                        ]
                    ]),
                    "face": 522,
                    "clientid": self.clientid,
                    "msg_id": 6000000 + int(time.time()) % 1000000,
                    "psessionid": self.psessionid,
                })
            },
            referer='http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        if result:
            r = json.loads(result.content, object_hook=self._decode_data)
        else:
            r = {
                'retcode': -1,
                'errmsg': 'timeout'
            }

        return r

    def send_discuss_text(self, did, text):
        result = self.url_get(
            url='http://d1.web2.qq.com/channel/send_discu_msg2',
            data={
                'r': json.dumps({
                    'did': did,
                    'content': json.dumps([
                        text,
                        [
                            'font',
                            {
                                "name": "宋体",
                                "size": 10,
                                "style": [
                                    0,
                                    0,
                                    0
                                ],
                                "color": "000000"
                            }
                        ]
                    ]),
                    "face": 522,
                    "clientid": self.clientid,
                    "msg_id": 6000000 + int(time.time()) % 1000000,
                    "psessionid": self.psessionid,
                })
            },
            referer='http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        if result:
            r = json.loads(result.content, object_hook=self._decode_data)
        else:
            r = {
                'retcode': -1,
                'errmsg': 'timeout'
            }

        return r


    # 下面是基础方法，用于发送请求
    def url_get(self, url, data=None, referer=None, origin=None):
        referer and self.session.headers.update({'Referer': referer})
        origin and self.session.headers.update({'Origin': origin})
        if url == 'https://d1.web2.qq.com/channel/poll2':
            timeout = 120
        elif url in ['http://d1.web2.qq.com/channel/send_buddy_msg2',
                     'http://d1.web2.qq.com/channel/send_qun_msg2',
                     'http://d1.web2.qq.com/channel/send_discu_msg2']:
            timeout = 2
        else:
            timeout = 10

        t = 0
        while True:
            try:
                if data is None:
                    return self.session.get(url, timeout=timeout)
                else:
                    return self.session.post(url, data=data, timeout=timeout)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                error(traceback.format_exc())

            if t < 5:
                t += 1
                time.sleep(0.2)
                echo('re request\n')
            else:
                echo('已与服务器断开链接\n')
                return None

    def _decode_data(self, data):
        """
        @brief      decode array or dict to utf-8
        @param      data   array or dict
        @return     utf-8
        """
        if isinstance(data, dict):
            rv = {}
            for key, value in data.iteritems():
                if isinstance(key, unicode):
                    key = key.encode('utf-8')
                rv[key] = self._decode_data(value)
            return rv
        elif isinstance(data, list):
            rv = []
            for item in data:
                item = self._decode_data(item)
                rv.append(item)
            return rv
        elif isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data

    def get_user_by_uin(self, uin):
        user = {}
        user['uin'] = uin
        user['nick'] = 0
        user['markname'] = ''
        for u in self.contact:
            if u['uin'] == uin:
                user['nick'] = u['nick']
                user['markname'] = u['markname']
                break
        return user

    def get_group_by_gid(self, gid):
        group = {}
        group['gid'] = gid
        group['code'] = 0
        group['name'] = 0
        group['markname'] = ''
        for g in self.group:
            if g['gid'] == gid:
                group['code'] = g['code']
                group['name'] = g['name']
                group['markname'] = g['markname']
                break
        return group

    def get_discuss_by_did(self, did):
        discuss = {}
        discuss['did'] = did
        discuss['name'] = 0
        for d in self.discuss:
            if d['did'] == did:
                discuss['name'] = d['name']
                break
        return discuss

    def get_group_mem_by_uin(self, uin, gid):
        user = {}
        user['uin'] = uin
        user['nick'] = 0
        user['markname'] = ''
        if gid in self.group_member:
            for m in self.group_member[gid]:
                if m['uin'] == uin:
                    user['nick'] = m['nick']
                    user['markname'] = m['markname']
                    break
        return user

    def get_discuss_mem_by_uin(self, uin, did):
        user = {}
        user['uin'] = uin
        user['nick'] = 0
        if did in self.discuss_member:
            for m in self.discuss_member[did]:
                if m['uin'] == uin:
                    user['nick'] = m['nick']
                    break
        return user

    def get_user_info(self, uin):
        result = self.url_get(
            url=('http://s.web2.qq.com/api/get_friend_info2?'
                 'tuin=%s&vfwebqq=%s&clientid=%s&psessionid=%s&t=%s' %
                 (uin, self.vfwebqq, self.clientid, self.psessionid, str(int(time.time())))),
            referer=('http://s.web2.qq.com/proxy.html?v=20130916001'
                     '&callback=1&id=1')
        )
        if result:
            r = json.loads(result.content, object_hook=self._decode_data)
            if r['retcode'] == 0:
                return r['result']
            else:
                return None
        else:
            return None
