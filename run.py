import yaml
import re
import requests
import json
import base64
from functools import wraps
from flask import Flask, request, abort, make_response

clash_config_template = '''
port: 1081
socks-port: 1080
allow-lan: false
mode: Direct
log-level: info
external-controller: 127.0.0.1:9090
Rule:
- FINAL,DIRECT
'''

custom_filter = lambda x: '维护' not in x and \
                '倍率' not in x and \
                ('美国' in x or '专线' in x or '[自建]' in x)

def collect():
    '''collect from all sources and return a list of vmess urls
    '''
    with open('config.yml') as f:
        config = yaml.safe_load(f.read())
    vmess_list = []
    if 'subscribe' in config:
        for x in config['subscribe']:
            r = requests.get(x)
            vmesses = base64.b64decode(r.text).decode('ascii').splitlines()
            vmess_list.extend(vmesses)
    if 'vmess' in config:
        for x in config['vmess']:
            vmess_list.append(x)
    return vmess_list

def export_clash_config():
    vmess_list = collect()
    proxies = []
    for x in vmess_list:
        j = vmess_to_clash_json(x)
        if custom_filter(j['name']):
            proxies.append(j)
    names = [x['name'] for x in proxies]
    y = yaml.safe_load(clash_config_template)
    y['Proxy'] = proxies
    y['Proxy Group'] = [{
        'name': 'Bundle',
        'type': 'url-test',
        'url': 'http://www.gstatic.com/generate_204',
        'interval': 600,
        'proxies': names
    }]
    return yaml.safe_dump(y, encoding='utf-8', allow_unicode=True)

def vmess_to_clash_json(vmess_url):
    vmess_raw = base64.b64decode(vmess_url.replace('vmess://', ''))
    j = json.loads(vmess_raw)
    r = {
        'name': j['ps'].replace('233v2.com_', '[自建] '),
        'type': 'vmess',
        'server': j['add'],
        'port': int(j['port']),
        'alterId': int(j['aid']),
        'uuid': j['id'],
        'cipher': 'auto',
        'tls': True
    }
    if j['net'] == 'ws':
        r.update({
            'network': j['net'],
            'ws-path': j['path'],
            'ws-headers': {
                'Host': j['host']
            }
        })
    return r


def require_auth(f):
    with open('config.yml') as fp:
        token = yaml.safe_load(fp.read())['token']
    def g():
        x = request.args.get('token', '')
        if x != token:
            abort(401)
        return f()
    g.__name__ = f.__name__
    return g

app = Flask(__name__) #记住这里的变量名app

@app.route('/')
def hello():
    return 'Hey, fuck gfw!'

@app.route('/stat')
@require_auth
def stat():
    with open('config.yml') as f:
        return f.read()

@app.route('/clash')
@require_auth
def export_clash():
    response = make_response(export_clash_config())
    response.headers['Content-Type'] = 'application/octet-stream; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="config.yml"'
    return response

@app.route('/subscribe')
@require_auth
def export_subscribe():
    return base64.b64encode('\n'.join(collect()))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)