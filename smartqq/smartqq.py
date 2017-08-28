#!/usr/bin/env python
# coding: utf-8

from utils import *
from smartqq_apis import WebQQApi
from config import ConfigManager
from config import Constant
from config import Log

import re
import sys
import time
import random
import traceback
from datetime import timedelta
import pickle
import requests.utils


class SmartQQ(WebQQApi):

    def __init__(self):
        super(SmartQQ, self).__init__()

        self.start_time = time.time()
        self.ask_login = True
        self.exit_code = 0

        self.msg_handler = None
        self.bot = None

        # 用于处理信息的类内全局
        self.CommandList = []
        self.DBStoreMSGList = []
        self.NeedReplyList = []
        self.ReplyList = []
        self.DBStoreBOTReplyList = []

    def start(self):

        login_flag = False

        if self.ask_login:
            reply = raw_input('是否使用恢复登录[Y/N]:')
            if reply == 'Y':
                self.ask_login = False
            else:
                echo('放弃恢复登录\n')

        if not self.ask_login:
            try:
                run('开始恢复登录数据\n', self.recover_login_data)
                echo('尝试登录\n')
                login_flag = self.TestLogin()
                if login_flag:
                    echo('恢复登录成功！\n')
                    self.send_png = True  # 用于重启登录发送二维码
                else:
                    echo('恢复登录失败!\n')
            except:
                error(traceback.format_exc())
                echo('恢复登录失败!\n')
        if not login_flag:
            run('开始二维码登录\n', self.Login)

        self.ask_login = False

        run('保存登录信息\n', self.save_login_data)
        time.sleep(0.5)
        run('开始获取联系人\n', self.GetContact)
        time.sleep(0.5)
        run('开始获取群\n', self.GetGroup)
        time.sleep(0.5)
        run('开始获取讨论组\n', self.GetDiscuss)
        echo('共获取到联系人 %d名，群 %d个，讨论组 %d个\n' % (len(self.contact), len(self.group), len(self.discuss)))
        time.sleep(0.5)
        run('开始拉取群、讨论组成员\n', self.fetch_group_discuss_member)

        while True:
            # 目前对于webqq的返回码并没有完全掌握，如果遇到掉线问题，特别是100001 login error
            # 如果掉线立刻尝试重新连接，可能会导致意外情况，为了保险起见将会延时1分钟重连
            r = self.PollMsg()
            if 'retcode' in r:
                if r['retcode'] == 0:
                    self.exit_code = 0
                    if 'result' in r and len(r['result']):
                        echo('in handler\n')
                        self.handle_mod(r['result'])
                    else:
                        echo(str(r) + '\n')
                elif r['retcode'] == 103:
                    self.exit_code = 0
                    echo(str(r) + '\n')
                    break
                else:
                    self.exit_code = 0
                    echo(str(r) + '\n')
                    time.sleep(60)  # 当前有封号风险，尝试等待一分钟重连
                    break
            # 下面情况出现将会直接退出
            elif 'errCode' in r:
                # 不明情况
                self.exit_code = 1
                echo(str(r) + '\n')
                break
            else:
                # 更加不明情况
                self.exit_code = 1
                echo(str(r) + '\n')
                break

    def stop(self):
        echo('运行时长： %s\n' % self.get_run_time())
        run('保存登录信息\n', self.save_login_data)
        echo('关闭会话\n')
        self.session.close()

    def save_login_data(self):
        cm = ConfigManager()
        # 保存鉴权参数
        cm.set('login_data', 'clientid', self.clientid)
        cm.set('login_data', 'url_ptwebqq', self.urlPtwebqq)
        cm.set('login_data', 'ptwebqq', self.ptwebqq)
        cm.set('login_data', 'vfwebqq', self.vfwebqq)
        cm.set('login_data', 'uin', self.uin)
        cm.set('login_data', 'psessionid', self.psessionid)
        cm.set('login_data', 'hash', self.hash)
        cm.set('login_data', 'bkn', self.bkn)
        cm.set('login_data', 'user_qq', self.user['qq'])
        cm.set('login_data', 'user_nick', self.user['nick'])

        # 保存cookies
        file_dir = cm.getpath('cookie')
        with open(file_dir, 'wb') as f:
            pickle.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)

        return True

    def recover_login_data(self):
        cm = ConfigManager()
        # 恢复鉴权参数
        self.clientid = int(cm.get('login_data', 'clientid'))
        self.urlPtwebqq = cm.get('login_data', 'url_ptwebqq')
        self.ptwebqq = cm.get('login_data', 'ptwebqq')
        self.vfwebqq = cm.get('login_data', 'vfwebqq')
        self.uin = int(cm.get('login_data', 'uin'))
        self.psessionid = cm.get('login_data', 'psessionid')
        self.hash = cm.get('login_data', 'hash')
        self.bkn = int(cm.get('login_data', 'bkn'))
        self.user['qq'] = cm.get('login_data', 'user_qq')
        self.user['nick'] = cm.get('login_data', 'user_nick')

        # 恢复cookies
        file_dir = cm.getpath('cookie')
        with open(file_dir, 'rb') as f:
            cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
            self.session = requests.session()
            self.session.cookies = cookies
            self.session.headers.update({
                'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9;'
                               ' rv:27.0) Gecko/20100101 Firefox/27.0'),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
            })

        return True

    def get_run_time(self):
        total_time = int(time.time() - self.start_time)
        t = timedelta(seconds=total_time)
        return '%s Day %s' % (t.days, t)

    def fetch_group_discuss_member(self):
        echo('获取群成员\n')
        count = 0
        self.group_member = {}  # 重置群成员列表
        for g in self.group:
            m_count = 0
            while True:
                time.sleep(0.2)
                all_info = self.GetGroupMember(g['code'])
                if all_info:
                    self.group_member[g['gid']] = []
                    minfo = all_info['result']['minfo']
                    if 'cards' in all_info['result']:
                        cards = all_info['result']['cards']
                    else:
                        cards = []
                    for m in minfo:
                        add_member = {}
                        add_member['uin'] = m['uin']
                        add_member['nick'] = m['nick']
                        for i in cards:
                            if m['uin'] == i['muin']:
                                add_member['markname'] = i['card']
                                break
                        else:
                            add_member['markname'] = ''
                        self.group_member[g['gid']].append(add_member)
                        m_count += 1
                    break
                else:
                    # 一般在与服务器断开链接才会出现
                    echo('%d:获取群 %s（gid:%s）成员时出错\n' % (count + 1, g['name'], g['gid']))
                    return False
            count += 1
            echo('%d：获取到群 %s 成员 %d 名\n' % (count, g['name'], m_count))

        echo('获取讨论组成员\n')
        count = 0
        self.discuss_member = {}  # 重置讨论组成员列表
        for d in self.discuss:
            m_count = 0
            while True:
                time.sleep(0.2)
                all_info = self.GetDiscussMember(d['did'])
                if all_info:
                    self.discuss_member[d['did']] = []
                    mem_info = all_info['result']['mem_info']
                    for m in mem_info:
                        add_member = {}
                        add_member['uin'] = m['uin']
                        add_member['nick'] = m['nick']
                        self.discuss_member[d['did']].append(add_member)
                        m_count += 1
                    break
                else:
                    # 一般在与服务器断开链接才会出现
                    echo('%d:获取讨论组 %s（did:%s）成员时出错\n' % (count + 1, d['name'], d['did']))
                    return False
            count += 1
            echo('%d：获取到讨论组 %s 成员 %d 名\n' % (count, d['name'], m_count))

        return True

    def handle_mod(self, msgs):
        for raw_msg in msgs:
            rmsg = {}
            value = raw_msg['value']
            rmsg['value'] = value
            op_flag = True

            if raw_msg['poll_type'] == 'message':
                # 好友消息
                rmsg['type'] = 1
                from_user = self.get_user_by_uin(value['from_uin'])
                if re.match(r'^unknown_\d+$', str(from_user['nick'])):
                    op_flag = False
                if from_user['nick'] == 0:
                    from_info = self.get_user_info(from_user['uin'])
                    if from_info:
                        from_user['nick'] = from_info['nick']
                        self.contact.append(from_user)  # 添加为新好友的信息
                    else:
                        op_flag = False
                        error('never in can not get user info\n')
                        from_user['nick'] = 'unknown_' + str(value['from_uin'])
                        self.contact.append(from_user)  # 减少网络请求次数
                rmsg['from_user'] = from_user

            # 对于群信息和讨论组信息有个奇怪的现象，就是当前帐号通过其他客户端发的信息会出现
            # 但是并不是以帐号QQ作为uin，所以基本无法识别，而通知等消息的uin也无法识别，
            # 所以不能简单将无法识别的用户发来的信息看作自己发的
            # 现在暂时不对此类信息作处理
            elif raw_msg['poll_type'] == 'group_message':
                # 群消息
                rmsg['type'] = 2
                from_group = self.get_group_by_gid(value['from_uin'])
                if from_group['name'] == 0:
                    # 遇见新群，需要重新获取群列表，以获取gcode来获取群的成员信息
                    echo('未识别群，需重新获取群信息\n')
                    if self.GetGroup():
                        pass
                    else:
                        error('登录信息可能已经失效，退出程序\n')
                        exit()
                    from_group = self.get_group_by_gid(value['from_uin'])
                    from_group_info = self.GetGroupMember(from_group['code'])
                    if from_group_info:
                        # 添加新群的成员信息
                        self.group_member[from_group['gid']] = []
                        minfo = from_group_info['result']['minfo']
                        if 'cards' in from_group_info['result']:
                            cards = from_group_info['result']['cards']
                        else:
                            cards = []
                        for m in minfo:
                            add_member = {}
                            add_member['uin'] = m['uin']
                            add_member['nick'] = m['nick']
                            for i in cards:
                                if m['uin'] == i['muin']:
                                    add_member['markname'] = i['card']
                                    break
                            else:
                                add_member['markname'] = ''
                            self.group_member[from_group['gid']].append(add_member)
                    else:
                        op_flag = False
                        error('never in can not get group info make group name unknown\n')
                        if from_group['name'] == 0:
                            from_group['name'] = 'unknown_group_' + str(value['from_uin'])
                rmsg['from_group'] = from_group

                from_user = self.get_group_mem_by_uin(value['send_uin'], from_group['gid'])
                if re.match(r'^unknown_\d+$', str(from_user['nick'])):
                    op_flag = False
                if from_user['nick'] == 0:
                    from_group_info = self.GetGroupMember(from_group['code'])
                    if from_group_info:
                        # 刷新群成员信息
                        self.group_member[from_group['gid']] = []
                        minfo = from_group_info['result']['minfo']
                        if 'cards' in from_group_info['result']:
                            cards = from_group_info['result']['cards']
                        else:
                            cards = []
                        for m in minfo:
                            add_member = {}
                            add_member['uin'] = m['uin']
                            add_member['nick'] = m['nick']
                            for i in cards:
                                if m['uin'] == i['muin']:
                                    add_member['markname'] = i['card']
                                    break
                            else:
                                add_member['markname'] = ''
                            self.group_member[from_group['gid']].append(add_member)
                        from_user = self.get_group_mem_by_uin(value['send_uin'], from_group['gid'])
                        if from_user['nick'] == 0:
                            op_flag = False
                            from_user['nick'] = 'unknown_' + str(value['send_uin'])
                            self.group_member[from_group['gid']].append(from_user)  # 减少网络请求次数
                    else:
                        op_flag = False
                        error('never in can not get group info make mem nick unknown\n')
                        from_user['nick'] = 'unknown_' + str(value['send_uin'])
                rmsg['from_user'] = from_user

            elif raw_msg['poll_type'] == 'discu_message':
                rmsg['type'] = 3
                from_discuss = self.get_discuss_by_did(value['did'])
                if from_discuss['name'] == 0:
                    from_discuss_info = self.GetDiscussMember(from_discuss['did'])
                    if from_discuss_info:
                        from_discuss['name'] = from_discuss_info['result']['info']['discu_name']
                        self.discuss.append(from_discuss)  # 添加新讨论组的信息
                        # 添加新讨论组成员的信息
                        self.discuss_member[from_discuss['did']] = []
                        mem_info = from_discuss_info['result']['mem_info']
                        for m in mem_info:
                            add_member = {}
                            add_member['uin'] = m['uin']
                            add_member['nick'] = m['nick']
                            self.discuss_member[from_discuss['did']].append(add_member)
                    else:
                        op_flag = False
                        # 当接收到讨论组文件时将会进入，在其他极端情况下也会进入，目前暂无好的解决方法
                        error('never in can not get discuss info make discuss name unknown\n')
                        from_discuss['name'] = 'unknown_discuss_' + str(value['from_uin'])
                rmsg['from_discuss'] = from_discuss

                from_user = self.get_discuss_mem_by_uin(value['send_uin'], from_discuss['did'])
                if re.match(r'^unknown_\d+$', str(from_user['nick'])):
                    op_flag = False
                if from_user['nick'] == 0:
                    from_discuss_info = self.GetDiscussMember(from_discuss['did'])
                    if from_discuss_info:
                        # 刷新讨论组成员信息
                        self.discuss_member[from_discuss['did']] = []
                        mem_info = from_discuss_info['result']['mem_info']
                        for m in mem_info:
                            add_member = {}
                            add_member['uin'] = m['uin']
                            add_member['nick'] = m['nick']
                            self.discuss_member[from_discuss['did']].append(add_member)
                        from_user = self.get_discuss_mem_by_uin(value['send_uin'], from_discuss['did'])
                        if from_user['nick'] == 0:
                            op_flag = False
                            from_user['nick'] = 'unknown_' + str(value['send_uin'])
                            self.discuss_member[from_discuss['did']].append(from_user)  # 减少网络请求次数
                    else:
                        op_flag = False
                        error('never in can not get discuss info make mem nick unknown\n')
                        from_user['nick'] = 'unknown_' + str(value['send_uin'])
                rmsg['from_user'] = from_user

            to_user = {}
            if value['to_uin'] == self.uin:
                to_user['uin'] = self.uin
                to_user['nick'] = self.user['nick']
                to_user['markname'] = ''
            else:
                op_flag = False
                error('never in to uin not my uin\n')
                # 现在webqq已经无法接收到自己在其他客户端发出的消息了，所以正常不会进入此步骤
                to_user['uin'] = value['to_uin']
                to_user['nick'] = 'unknown_' + str(value['to_uin'])
                to_user['markname'] = ''
            rmsg['to_user'] = to_user

            text = self.handle_content(value['content'][1:])
            rmsg['text'] = text

            if op_flag:
                self.add_operate_list(rmsg)

            self.show_msg(rmsg)

        try:
            if self.msg_handler:
                self.msg_handler.save_into_db(self.DBStoreMSGList)
                self.msg_handler.handle_commands(self.CommandList)
                self.msg_handler.get_bot_reply(self.NeedReplyList)
                self.msg_handler.auto_reply(self.ReplyList)
                self.msg_handler.save_into_db(self.DBStoreBOTReplyList)
        except:
            error(traceback.format_exc())
        finally:
            self.CommandList = []
            self.DBStoreMSGList = []
            self.NeedReplyList = []
            self.ReplyList = []
            self.DBStoreBOTReplyList = []

    def add_operate_list(self, msg):
        text = msg['text']

        if msg['type'] == 1:
            # 人 -> 我
            table = 'normalz' + trans_unicode_into_int(trans_coding(msg['from_user']['nick']))
            self.msg_handler.msg_db.create_table(table, self.msg_handler.msg_col)
            add_cmd = {}
            add_cmd['type'] = 1
            cmd_text = text.strip()
            if cmd_text == 'check_record_count':
                add_cmd['func'] = 'check_count'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)
            elif re.match(r'^check_record_\d+$', cmd_text):
                add_cmd['func'] = 'check_text'
                add_cmd['time'] = msg['value']['time']
                add_cmd['msg_order'] = int(re.sub(r'^check_record_', '', cmd_text))
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)
            elif cmd_text == 'runtime':
                add_cmd['func'] = 'check_time'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)
            elif cmd_text == '-help':
                add_cmd['func'] = 'help_person'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 个人聊天用于测试机器人，可以删除数据表
            elif cmd_text == 'clean_table':
                add_cmd['func'] = 'clean_table'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 添加机器人控制命令
            elif cmd_text == 'check_group':
                add_cmd['func'] = 'check_group'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            elif re.match(r'^output_group_\d+$', cmd_text):
                add_cmd['func'] = 'output_group'
                add_cmd['time'] = msg['value']['time']
                add_cmd['g_order'] = int(re.sub(r'^output_group_', '', cmd_text))
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 添加查看具体某个群的聊天记录
            elif re.match(r'^check_group_\d+_count$', cmd_text):
                add_cmd['func'] = 'check_group_count'
                add_cmd['time'] = msg['value']['time']
                add_cmd['g_order'] = int(re.sub(r'^check_group_', '', cmd_text).split('_')[0])
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)
            elif re.match(r'^check_group_\d+_\d+$', cmd_text):
                add_cmd['func'] = 'check_group_text'
                add_cmd['time'] = msg['value']['time']
                t = re.sub(r'^check_group_', '', cmd_text).split('_')
                add_cmd['g_order'] = int(t[0])
                add_cmd['msg_order'] = int(t[1])
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 添加邮箱发送
            elif re.match(r'^send_group_\d+_\w+@\w+\.com$', cmd_text):
                add_cmd['func'] = 'send_file_group'
                add_cmd['time'] = msg['value']['time']
                t = re.sub(r'^send_group_', '', cmd_text).split('_')
                add_cmd['g_order'] = int(t[0])
                add_cmd['email_addr'] = '_'.join(t[1:])
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 机器人测试接口命令
            elif cmd_text == 'reply_e':
                add_cmd['func'] = 'test_emot'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_user']['uin']
                self.CommandList.append(add_cmd)

            # 在上面定义命令
            else:
                # 添加自动回复
                add_reply = {}
                add_reply['type'] = 1
                add_reply['text'] = text
                add_reply['time'] = msg['value']['time']
                add_reply['user'] = table
                add_reply['to_id'] = msg['from_user']['uin']
                self.NeedReplyList.append(add_reply)

                # 添加储存
                add_store = {}
                add_store['content'] = text
                add_store['time'] = msg['value']['time']
                add_store['from'] = msg['from_user']['nick']
                add_store['to'] = 'myself'
                add_store['table_name'] = table
                self.DBStoreMSGList.append(add_store)

        elif msg['type'] == 2:
            # 群 -> 我
            # 群的聊天已经取消了自动回复和命令，只保存聊天记录
            table = 'groupz' + trans_unicode_into_int(trans_coding(msg['from_group']['name']))
            self.msg_handler.msg_db.create_table(table, self.msg_handler.msg_col)
            # add_cmd = {}
            # add_cmd['type'] = 2
            # if text == 'check_record_count':
            #     pass
            #     add_cmd['func'] = 'check_count'
            #     add_cmd['time'] = msg['value']['time']
            #     add_cmd['table_name'] = table
            #     add_cmd['to_id'] = msg['from_group']['gid']
            #     self.CommandList.append(add_cmd)
            # elif re.match(r'^check_record_\d+$', text):
            #     add_cmd['func'] = 'check_text'
            #     add_cmd['time'] = msg['value']['time']
            #     add_cmd['msg_order'] = int(re.sub(r'^check_record_', '', text))
            #     add_cmd['table_name'] = table
            #     add_cmd['to_id'] = msg['from_group']['gid']
            #     self.CommandList.append(add_cmd)
            # elif text == 'runtime':
            #     add_cmd['func'] = 'check_time'
            #     add_cmd['time'] = msg['value']['time']
            #     add_cmd['to_id'] = msg['from_group']['gid']
            #     self.CommandList.append(add_cmd)

            # 在上面定义命令
            # else:
                # 添加自动回复
                # add_flag = False
                # for i in msg['value']['content'][1:]:
                #     if type(i) == str:
                #         if re.match(r'^@' + self.user['nick'] + r'$', i):
                #             add_flag = True
                #             break
                # if add_flag:
                #     s = re.sub(r'@' + self.user['nick'], '', text)
                #     add_reply = {}
                #     add_reply['type'] = 2
                #     add_reply['text'] = s
                #     add_reply['time'] = msg['value']['time']
                #     add_reply['user'] = table
                #     add_reply['to_id'] = msg['from_group']['gid']
                #     add_reply['to_who'] = msg['from_user']['nick']
                #     self.NeedReplyList.append(add_reply)

                # 添加储存
            add_store = {}
            add_store['content'] = text
            add_store['time'] = msg['value']['time']
            add_store['from'] = msg['from_user']['nick']
            add_store['to'] = 'Group'
            add_store['table_name'] = table
            self.DBStoreMSGList.append(add_store)

        elif msg['type'] == 3:
            # 讨论组 -> 我
            # 当前版本有特殊需求，故添加一些特殊功能
            if re.match(r'^\s*#.*$', text):  # 当发送信息以#开头时，将不对其进行存储等处理
                return
            table = 'discussz' + trans_unicode_into_int(trans_coding(msg['from_discuss']['name']))
            self.msg_handler.msg_db.create_table(table, self.msg_handler.msg_col)
            add_cmd = {}
            add_cmd['type'] = 3
            cmd_text = text.strip()
            if cmd_text == 'check_record_count':
                add_cmd['func'] = 'check_count'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif re.match(r'^check_record_\d+$', cmd_text):
                add_cmd['func'] = 'check_text'
                add_cmd['time'] = msg['value']['time']
                add_cmd['msg_order'] = int(re.sub(r'^check_record_', '', cmd_text))
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif cmd_text == 'runtime':
                add_cmd['func'] = 'check_time'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif cmd_text == '-help':
                add_cmd['func'] = 'help_discuss'
                add_cmd['time'] = msg['value']['time']
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)

            # 模板任务命令
            elif cmd_text == 'output_csv':
                add_cmd['func'] = 'output_csv'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif cmd_text == 'clean_table':
                add_cmd['func'] = 'clean_table'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif re.match(r'^delete_record_\d+$', cmd_text):
                add_cmd['func'] = 'delete_record'
                add_cmd['time'] = msg['value']['time']
                add_cmd['msg_order'] = int(re.sub(r'^delete_record_', '', cmd_text))
                add_cmd['table_name'] = table
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)
            elif re.match(r'^send_to_\w+@\w+\.com$', cmd_text):
                add_cmd['func'] = 'send_file_discuss'
                add_cmd['time'] = msg['value']['time']
                add_cmd['table_name'] = table
                add_cmd['email_addr'] = re.sub(r'^send_to_', '', cmd_text)
                add_cmd['to_id'] = msg['from_discuss']['did']
                self.CommandList.append(add_cmd)

            # 在上面定义命令
            else:
                # 添加自动回复
                add_flag = False
                for i in msg['value']['content'][1:]:
                    if type(i) == str:
                        if re.match(r'^@' + self.user['nick'] + r'$', i):
                            add_flag = True
                            break
                if add_flag:
                    s = re.sub(r'@' + self.user['nick'], '', text)
                    add_reply = {}
                    add_reply['type'] = 3
                    add_reply['text'] = s
                    add_reply['time'] = msg['value']['time']
                    add_reply['user'] = table
                    add_reply['to_id'] = msg['from_discuss']['did']
                    add_reply['to_who'] = msg['from_user']['nick']
                    self.NeedReplyList.append(add_reply)

                # 添加储存
                add_store = {}
                add_store['content'] = text
                add_store['time'] = msg['value']['time']
                add_store['from'] = msg['from_user']['nick']
                add_store['to'] = 'Discuss'
                add_store['table_name'] = table
                self.DBStoreMSGList.append(add_store)

    def handle_content(self, content):
        text = ''
        echo(str(content) + '\n')
        for c in content:
            if type(c) == list:
                # 尝试添加表情处理
                text += '[表情]'
            elif type(c) == str:
                text += c
            else:
                echo(str(c) + '\n')
        return text

    def show_msg(self, msg):
        t = time.strftime('%Y-%m-%d,%H:%M:%S', time.localtime(msg['value']['time']))
        if msg['type'] == 1:
            echo(
                '%s 好友消息 %s(%s) -> %s(%s): %s\n' %
                (
                    t,
                    msg['from_user']['nick'],
                    msg['from_user']['markname'],
                    msg['to_user']['nick'],
                    msg['to_user']['markname'],
                    msg['text']
                )
            )
        elif msg['type'] == 2:
            echo(
                '%s 群消息 %s(%s)| %s(%s) -> %s(%s): %s\n' %
                (
                    t,
                    msg['from_group']['name'],
                    msg['from_group']['markname'],
                    msg['from_user']['nick'],
                    msg['from_user']['markname'],
                    msg['to_user']['nick'],
                    msg['to_user']['markname'],
                    msg['text']
                )
            )
        elif msg['type'] == 3:
            echo(
                '%s 讨论组消息 %s| %s -> %s: %s\n' %
                (
                    t,
                    msg['from_discuss']['name'],
                    msg['from_user']['nick'],
                    msg['to_user']['nick'],
                    msg['text']
                )
            )
