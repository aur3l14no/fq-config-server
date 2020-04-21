import yaml
import requests
import json
import base64
import re
from collections import OrderedDict
from flask import Flask, request, abort, make_response


proxy_group = {}


def decode_vmess(vmess_url):
    vmess_raw = base64.b64decode(
        vmess_url.replace('vmess://', '')).decode('utf8')
    j = json.loads(vmess_raw)
    return j


def encode_vmess(j):
    s = json.dumps(j)
    return 'vmess://' + base64.b64encode(s.encode('utf8')).decode('utf8')


def collect():
    '''collect from all sources to `proxy_group`
    '''
    global proxy_group
    proxy_group = {}
    with open('config.yml') as f:
        config = yaml.safe_load(f.read())
    for proxy in config['proxies']:
        if not proxy['name'] in proxy_group:
            proxy_group[proxy['name']] = []
        vmesses = []

        if proxy['type'] == 'subscribe':
            r = requests.get(proxy['url'])
            vmesses = base64.b64decode(r.text).decode('utf8').splitlines()
        elif proxy['type'] == 'vmess':
            vmesses = [proxy['url']]

        if 'regex' in proxy:
            vmesses = [v for v in vmesses if re.match(
                proxy['regex'], decode_vmess(v)['ps'])]
        if 'rename_from' in proxy:
            def _repl(v):
                j = decode_vmess(v)
                j.update(
                    {'ps': re.sub(proxy['rename_from'], proxy['rename_to'], j['ps'])})
                return encode_vmess(j)
            vmesses = [_repl(v) for v in vmesses]

        proxy_group[proxy['name']].extend(vmesses)


def vmess_to_clash_json(vmess_url):
    vmess_raw = base64.b64decode(vmess_url.replace('vmess://', ''))
    j = json.loads(vmess_raw)
    r = {
        'name': j['ps'],
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


def debug_print(proxy_group):
    for p in proxy_group:
        print(p)
        for x in proxy_group[p]:
            print(decode_vmess(x))


app = Flask(__name__)


@app.route('/')
def hello():
    return 'Hey, fuck gfw!'


@app.route('/stat')
@require_auth
def stat():
    with open('config.yml') as f:
        return f.read()


@app.route('/subscribe')
@require_auth
def export_subscribe():
    collect()
    all_vmess = []
    for x in proxy_group:
        all_vmess.extend(proxy_group[x])
    return base64.b64encode('\n'.join(list(OrderedDict.fromkeys(all_vmess)))
                            .encode('utf8')).decode('utf8')

@app.route('/sub')
@require_auth
def export_public_subscribe():
    collect()
    all_vmess = []
    for x in proxy_group:
        if x == 'self':
            all_vmess.extend(proxy_group[x])
    return base64.b64encode('\n'.join(list(OrderedDict.fromkeys(all_vmess)))
                            .encode('utf8')).decode('utf8')

@app.route('/clash_saved')
@require_auth
def get_clash_saved():
    with open('Clash.yml') as f:
        response = make_response(f.read())
    response.headers['Content-Type'] = 'application/octet-stream; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="config.yml"'
    return response


if __name__ == '__main__':
    with open('config.yml') as fp:
        port = yaml.safe_load(fp.read())['port']
    app.run(host='0.0.0.0', port=port)
