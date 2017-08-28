# smartqqbot project

使用smartqq API接口，可以实现自动回复和获取聊天记录

使用前首先添加外部依赖：

apt-get install libzbar-dev

然后添加库：

pip install -r requirements.txt

支持绑定登录，一般一次扫码以后可以维持一天左右的登录状态

登录掉线后会先尝试三次重新登录请求，若登录信息过期则需要重新扫码

重新登录二维码会发送到指定邮箱，可以在config/constant.py中指定，发出CSV文件邮箱亦可

使用-help在聊天窗口中获取命令

当前无法获得用户好友，群，讨论组等的唯一信息，所以使用昵称来区别

数据库储存内容为：

表名：normal/group/discuss + z + 昵称的每个unicode字符对应数字以z分隔

MsgOrder integer primary key,

Time text,

FromNick text,

ToNick text,

content text

登录后的机器人不需要其他用户端同时在线，可以接收到他人发出的消息

但是无法接收到自己通过其他客户端发出的信息

（群和讨论组可以收到，但是无法识别，因为uin不是自己的qq号，每次登录都会改变，也无法获取到昵称信息）

注意：

输出的csv文件名均为对应表名称

讨论组中#开头的消息不记录

所有聊天中命令均不记录

命令前后可以有空白字符，中间不能有

好友聊天中对非命令消息使用图灵机器人自动回复

讨论组聊天中，对@消息使用图灵机器人自动回复


