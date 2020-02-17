## 翻墙工具包 - Config 服务器

V2Ray 的配置很复杂, 来源有 config.json, vmess url, subscribe url (V2RayN / Clash)

这里做一个简单的整合, 将不同来源的配置合并后统一导出为目标格式

### 使用指南

创建一个 `config.yml` 文件，包含如下内容

```
subscribe:
- https://jichang.com/sub.php?token=???pid=???

vmess:
- vmess://blablabla

token: fuckgfw
```

然后运行

```
docker run -d -v `pwd`/config.yml:/config.yml -p 9000:80 aur3l14no/fq-config-server
```

### API

#### /

什么都不做, 仅用于检测服务器在线情况

#### /stat 查看配置文件

args:
- token: 用于认证的 token

#### /clash clash 订阅地址

args:
- token: 用于认证的 token

#### /subscribe V2RayN 等的订阅地址

args:
- token: 用于认证的 token

### 其他

`run.py` 中对服务器进行了过滤, 使用时请务必注意