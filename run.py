import yaml
import requests
import json
import base64
from flask import Flask, request, abort, make_response

def _filter(sub):
    name = sub['name']
    return '维护' not in name and \
            '倍' not in name and \
            ('美国' in name or '专线' in name or '[自建]' in name)

grouped_vmess = []


def collect():
    '''collect from all sources to `grouped_vmess`
    '''
    global grouped_vmess
    grouped_vmess = []
    with open('config.yml') as f:
        config = yaml.safe_load(f.read())
    if 'subscribe' in config:
        sub = config['subscribe'][0]
        url = sub['url']
        r = requests.get(url)
        vmesses = base64.b64decode(r.text).decode('ascii').splitlines()
        grouped_vmess.append({
            'name': f'sub-{sub["name"]}',
            'vmesses': vmesses
        })
    if 'vmess' in config:
        grouped_vmess.append({
            'name': 'other',
            'vmesses': config['vmess']
        })


def export_clash_config():
    global grouped_vmess

    vmesses = []
    for group in grouped_vmess[:-1]:
        vmesses.extend(group['vmesses'])    
    sub_proxies = [*filter(_filter, map(vmess_to_clash_json, vmesses))]

    vmesses = grouped_vmess[-1]['vmesses']
    other_proxies = [*filter(_filter, map(vmess_to_clash_json, vmesses))]
    
    yaml_scratch = ''
    with open('Head.yml') as f:
        yaml_scratch += f.read() + '\n'
    with open('Rule.yml') as f:
        yaml_scratch += f.read() + '\n'
    y = yaml.safe_load(yaml_scratch)

    y['Proxy'] = sub_proxies + other_proxies
    y['Proxy Group'] = [{
        'name': 'Proxy',
        'type': 'select',
        'proxies': ['sub', 'other']
        }, {
        'name': 'sub',
        'type': 'url-test',
        'url': 'http://www.gstatic.com/generate_204',
        'interval': 600,
        'proxies': [*map(lambda x: x['name'], sub_proxies)]
        }, {
        'name': 'other',
        'type': 'select',
        'proxies': [*map(lambda x: x['name'], other_proxies)]
    }]
    y['Rule']
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


app = Flask(__name__)


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
    collect()
    response = make_response(export_clash_config())
    response.headers['Content-Type'] = \
        'application/octet-stream; charset=utf-8'
    response.headers['Content-Disposition'] = \
        'attachment; filename="config.yml"'
    return response


@app.route('/subscribe')
@require_auth
def export_subscribe():
    collect()
    all_vmess = []
    for x in grouped_vmess:
        all_vmess.extend(x['vmesses'])
    return base64.b64encode('\n'.join(set(all_vmess)))

@app.route('/clash_saved')
@require_auth
def get_clash_saved():
    with open('Clash.yml') as f:
        response = make_response(f.read())
    response.headers['Content-Type'] = \
        'application/octet-stream; charset=utf-8'
    response.headers['Content-Disposition'] = \
        'attachment; filename="config.yml"'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
