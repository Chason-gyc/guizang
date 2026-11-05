"""Provider-specific text requests; secrets never leave the backend configuration."""
import json
import os
import ssl
import urllib.request
import urllib.error
from pathlib import Path


def config():
    return json.loads((Path(__file__).resolve().parents[1] / 'schema/providers.json').read_text(encoding='utf-8'))


def list_providers():
    return [dict(id=k, label=v['label'], models=v['models'], configured=bool(os.getenv(v['env']))) for k, v in config().items()]


def call_model(provider, model, system, text):
    if not isinstance(provider, str) or not isinstance(model, str):
        raise ValueError('供应商和模型必须为文本')
    cfg = config().get(provider)
    if not cfg or model not in [m['id'] for m in cfg['models']]:
        raise ValueError('供应商或模型不在配置列表中')
    key = os.getenv(cfg['env'])
    if not key:
        raise ValueError('请配置 ' + cfg['env'])
    base = os.getenv(cfg.get('base_env', ''), cfg['base_url']).rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('模型地址必须使用 HTTPS')
    protocol = cfg['protocol']
    headers = {'Content-Type':'application/json', 'Authorization':'Bearer ' + key}
    if protocol == 'openai_chat':
        endpoint = '/chat/completions'
        body = dict(model=model, messages=[dict(role='system',content=system), dict(role='user',content=text)], stream=False)
        if provider == 'bailian':
            body['enable_thinking'] = False
    elif protocol == 'openai_responses':
        endpoint = '/responses'
        body = dict(model=model, instructions=system, input=text, store=False)
    else:
        endpoint = '/v1/messages'
        headers = {'Content-Type':'application/json', 'x-api-key':key, 'anthropic-version':'2023-06-01'}
        body = dict(model=model, system=system, max_tokens=4096, messages=[dict(role='user',content=text)])
    try:
        request = urllib.request.Request(base + endpoint, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read(1024*1024))
        if protocol == 'openai_chat':
            choice = result['choices'][0]
            if choice.get('finish_reason') != 'stop':
                raise ValueError('模型输出未完成，请重试')
            answer = choice['message']['content']
        elif protocol == 'openai_responses':
            if result.get('status') != 'completed':
                raise ValueError('模型输出未完成，请重试')
            answer = '\n'.join(c['text'] for item in result['output'] if item.get('type') == 'message' for c in item.get('content',[]) if c.get('type') == 'output_text')
        else:
            if result.get('stop_reason') != 'end_turn':
                raise ValueError('模型输出未完成，请重试')
            answer = '\n'.join(c['text'] for c in result['content'] if c.get('type') == 'text')
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError('模型未返回有效文本')
        return answer.strip()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"{cfg['label']} 返回 HTTP {exc.code}，请检查密钥、模型权限、额度及接口地址") from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            message = 'HTTPS 证书校验失败，请检查代理证书和系统时间'
        elif isinstance(reason, TimeoutError):
            message = '连接超时，请检查网络和代理是否能访问该模型厂商'
        else:
            message = 'HTTPS 连接未建立，请检查系统代理及其线路；尚未完成密钥和模型权限校验'
        raise ValueError(f"{cfg['label']}：{message}") from exc
    except (TimeoutError, ssl.SSLError) as exc:
        raise ValueError('模型网络连接超时或 TLS 握手失败，请检查网络和代理') from exc
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('模型接口返回格式异常，请检查接口地址和协议') from exc
    except OSError as exc:
        raise ValueError('模型网络请求失败，请检查网络和代理') from exc
