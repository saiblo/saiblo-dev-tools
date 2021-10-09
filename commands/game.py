import json
from argparse import ArgumentParser, Namespace
from sys import stderr, stdout

import requests

from utils.error import request_failed
from utils.path import make_dir, open_file
from utils.storage import read_config, read_cookie, read_db


def _test(config_path: str, result_dir: str) -> None:
    url = read_config()['url']
    db = read_db()
    cookie = read_cookie()
    config = json.load(open_file(config_path, encoding='utf-8'))

    def get_ai_from_tag(tag: str) -> str:
        if tag not in db['ai']:
            raise RuntimeError(f'AI `{tag}` 不存在')
        return db['ai'][tag]

    response = requests.post(f'{url}/admin/game/{config["game"]}/test/', cookies={'sessionid': cookie},
                             json={'ai': [get_ai_from_tag(tag) for tag in config['ai']],
                                   'config': config['config']})
    if response.status_code != 200:
        request_failed(response)
    else:
        make_dir(result_dir)
        data = response.json()
        json.dump(data['config'], open(f'{result_dir}/config.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        json.dump(data['info'], open(f'{result_dir}/info.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        open(f'{result_dir}/replay{data["replay"]["type"]}', 'w', encoding='utf-8') \
            .write(data['replay']['content'])
        stdout.write(f'{data["status"]}\n')


def _upload(game_id: str, game_path: str) -> None:
    url = read_config()['url']
    cookie = read_cookie()
    game = open_file(game_path, 'rb')
    response = requests.post(f'{url}/admin/game/{game_id}/upload/', cookies={'sessionid': cookie},
                             files={'file': game})
    if response.status_code != 200:
        request_failed(response)
    else:
        stdout.write('上传成功\n')
        response = requests.get(f'{url}/admin/make-compile/{game_id}/', cookies={'sessionid': cookie})
        if response.status_code != 200:
            request_failed(response)
        else:
            result = response.json()
            if 'error' in result:
                stderr.write(f'{result["error"]}\n')
            else:
                stdout.write('编译成功\n')


def subcommand_hook(parser: ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-t', '--test', nargs=2, help='测试游戏', metavar=('config_path', 'result_dir'))
    group.add_argument('-u', '--upload', nargs=2, help='上传游戏', metavar=('game_id', 'game_path'))


def main(args: Namespace) -> None:
    if args.test is not None:
        _test(*args.test)
    elif args.upload is not None:
        _upload(*args.upload)
    else:
        raise RuntimeError(f'无法识别参数：`{args}`')
