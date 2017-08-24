#!/usr/bin/env python
# coding: utf-8

from smartqq.utils import *
from config import ConfigManager
from config import Constant
from config import Log

import os
import time
import csv
import traceback


class QQMsgHandler(object):

    def __init__(self, msg_db):

        self.smartqq = None
        self.msg_db = msg_db

        cm = ConfigManager()
        self.data_file = cm.getpath('datafile')
        if not os.path.exists(self.data_file):
            os.makedirs(self.data_file)

        self.msg_col = '''
                    MsgOrder integer primary key,
                    Time text,
                    FromNick text,
                    ToNick text,
                    content text
                '''
        self.user_type = ['normal', 'group', 'discuss']

    def get_time_string(self, second=0):
        if second:
            return time.strftime('%Y-%m-%d,%H:%M:%S', time.localtime(second))
        return time.strftime('%Y-%m-%d,%H:%M:%S', time.localtime(time.time()))

    def save_into_db(self, store_list):
        stores = sorted(store_list, key=lambda x: x['time'])
        for s in stores:
            col = (
                None,
                self.get_time_string(s['time']),
                s['from'],
                s['to'],
                s['content']
            )
            self.msg_db.insert(s['table_name'], col)

    def handle_commands(self, command_list):
        commands = sorted(command_list, key=lambda x: x['time'])
        for cmd in commands:
            add_reply = {}
            add_reply['type'] = cmd['type']
            if cmd['func'] == 'check_count':
                max_count = self.msg_db.select_max(cmd['table_name'], "MsgOrder")
                add_reply['text'] = str(max_count)
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)
            elif cmd['func'] == 'check_text':
                record = self.msg_db.select(cmd['table_name'], "MsgOrder", cmd['msg_order'])
                if record:
                    record_msg = 'MsgOrder:' + str(record[0]['MsgOrder']) + ' ' + \
                                 'Time:' + record[0]['Time'] + ' ' + \
                                 'From:' + record[0]['FromNick'] + ' ' + \
                                 'To:' + record[0]['ToNick'] + ' ' + \
                                 'content:' + record[0]['content']
                else:
                    record_msg = '记录无效'
                add_reply['text'] = record_msg
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)
            elif cmd['func'] == 'check_time':
                add_reply['text'] = self.smartqq.get_run_time()
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)

            # 爬取聊天
            elif cmd['func'] == 'check_group':
                text = ''
                for i in xrange(0, len(self.smartqq.group)):
                    text += str(i) + self.smartqq.group[i]['name'] + '\n'
                for i in xrange(0, len(text), 500):
                    add_reply = {
                        'type': cmd['type'],
                        'text': text[i:i+500],
                        'to_id': cmd['to_id']
                    }
                    self.smartqq.ReplyList.append(add_reply)
            elif cmd['func'] == 'output_group':
                add_reply['to_id'] = cmd['to_id']
                if cmd['g_order'] >= len(self.smartqq.group):
                    add_reply['text'] = '无效编号'
                else:
                    table_name = 'groupz' + \
                                 trans_unicode_into_int(trans_coding(self.smartqq.group[cmd['g_order']]['name']))
                    try:
                        msg_count = self.msg_db.select_max(table_name, 'MsgOrder')
                        try:
                            file_name = table_name + '.csv'
                            file_dir = os.path.join(self.data_file, file_name)
                            records = self.msg_db.select(table_name)
                            datas = []
                            for rec in records:
                                d = [
                                    rec['MsgOrder'],
                                    rec['Time'],
                                    trans_coding(rec['FromNick']).encode('gbk', 'ignore'),
                                    trans_coding(rec['content']).encode('gbk', 'ignore')
                                ]
                                datas.append(d)
                            add_line = [0, 0, 0, 0]
                            datas.append(add_line)
                            out_file = open(file_dir, 'ab+')
                            write_file = csv.writer(out_file)
                            write_file.writerows(datas)
                            out_file.close()
                            add_reply['text'] = '导出成功：' + file_name
                        except:
                            error(traceback.format_exc())
                            add_reply['text'] = '导出失败'
                    except:
                        add_reply['text'] = '无记录表'
                self.smartqq.ReplyList.append(add_reply)

            # 模板任务
            elif cmd['func'] == 'output_csv':
                try:
                    file_name = cmd['table_name'] + '.csv'
                    file_dir = os.path.join(self.data_file, file_name)
                    records = self.msg_db.select(cmd['table_name'])
                    datas = []
                    person = {}
                    for rec in records:
                        if rec['FromNick'] not in person:
                            person[rec['FromNick']] = 0
                        d = [
                            rec['MsgOrder'],
                            rec['Time'],
                            trans_coding(rec['FromNick']).encode('gbk', 'ignore'),
                            trans_coding(rec['content']).encode('gbk', 'ignore')
                        ]
                        datas.append(d)
                        person[rec['FromNick']] += 1
                    add_line = []
                    for p in person.keys():
                        add_line.append(p)
                        add_line.append(person[p])
                    datas.append(add_line)
                    out_file = open(file_dir, 'ab+')
                    write_file = csv.writer(out_file)
                    write_file.writerows(datas)
                    out_file.close()
                    add_reply['text'] = '导出成功：' + file_name
                except:
                    error(traceback.format_exc())
                    add_reply['text'] = '导出失败'
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)
            elif cmd['func'] == 'clean_table':
                try:
                    self.msg_db.delete_table(cmd['table_name'])
                    add_reply['text'] = '成功清除'
                except:
                    error(traceback.format_exc())
                    add_reply['text'] = '清除失败'
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)
            elif cmd['func'] == 'delete_record':
                try:
                    self.msg_db.delete(cmd['table_name'], 'MsgOrder', cmd['msg_order'])
                    add_reply['text'] = '成功删除'
                except:
                    error(traceback.format_exc())
                    add_reply['text'] = '删除失败'
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)

            # 测试用命令
            elif cmd['func'] == 'test_emot':
                add_reply['text'] = '[微笑]'
                add_reply['to_id'] = cmd['to_id']
                self.smartqq.ReplyList.append(add_reply)

    def get_bot_reply(self, r_list):
        if len(r_list) == 0:
            return

        r_s = sorted(r_list, key=lambda x: x['time'])
        rs = self.smartqq.bot.get_many_reply(r_s)
        for i in xrange(0, len(rs)):
            if r_s[i]['type'] == 1:
                add_reply = {}
                add_reply['type'] = 1
                add_reply['text'] = rs[i].encode('utf-8')
                add_reply['to_id'] = r_s[i]['to_id']
                add_reply['table'] = r_s[i]['user']
                self.smartqq.ReplyList.append(add_reply)
            elif r_s[i]['type'] == 2:
                add_reply = {}
                add_reply['type'] = 2
                text = u'@' + trans_coding(r_s[i]['to_who']) + u'\u2005' + trans_coding(rs[i])
                add_reply['text'] = text.encode('utf-8')
                add_reply['to_id'] = r_s[i]['to_id']
                add_reply['table'] = r_s[i]['user']
                self.smartqq.ReplyList.append(add_reply)
            elif r_s[i]['type'] == 3:
                add_reply = {}
                add_reply['type'] = 3
                text = u'@' + trans_coding(r_s[i]['to_who']) + u'\u2005' + trans_coding(rs[i])
                add_reply['text'] = text.encode('utf-8')
                add_reply['to_id'] = r_s[i]['to_id']
                add_reply['table'] = r_s[i]['user']
                self.smartqq.ReplyList.append(add_reply)

    def auto_reply(self, reply_list):
        for reply in reply_list:
            try:
                flag = self.smartqq.send_text(reply['type'], reply['to_id'], reply['text'])
            except:
                flag = False
            if 'table' in reply:
                add_store = {}
                add_store['time'] = int(time.time())
                add_store['content'] = reply['text']
                add_store['from'] = self.smartqq.bot.active_bot
                if reply['type'] == 2:
                    add_store['to'] = 'Group'
                if reply['type'] == 3:
                    add_store['to'] = 'Discuss'
                else:
                    add_store['to'] = trans_int_into_unicode(reply['table'])[1].encode('utf-8')
                add_store['table_name'] = reply['table']
                self.smartqq.DBStoreBOTReplyList.append(add_store)
            if flag:
                echo('自动回复成功\n')
            else:
                echo('自动回复失败\n')
            time.sleep(0.05)