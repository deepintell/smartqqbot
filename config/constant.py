#!/usr/bin/env python
# coding: utf-8

import time


class Constant(object):
    """
    @brief      All used constants are listed here
    """

    QQ_CONFIG_FILE = 'config/webqq.conf'
    LOGGING_LOGGER_NAME = 'WebQQ'

    QRCODE_BLACK = '\033[40m  \033[0m'
    QRCODE_WHITE = '\033[47m  \033[0m'

    # 发送邮件的邮箱配置
    send_mail_host = 'smtp.163.com'
    send_mail_ssl_port = 465
    send_mail_nor_port = 25
    send_mail_addr = 'record_sender@163.com'
    send_mail_apikey = 'send123456'
    send_login_addr = '835542226@qq.com'

    # tuling机器人配置
    BOT_TULING_API_KEY = '55e7f30895a0a10535984bae5ad294d1'
    BOT_TULING_API_URL = 'http://www.tuling123.com/openapi/api?key=%s&info=%s&userid=%s'
    BOT_TULING_BOT_REPLY = u'麻烦说的清楚一点，我听不懂你在说什么'
