import sys
import glob
import json
import pathlib
import asyncio
import websockets
import requests

with open('config.json', 'r') as f:
    config = json.load(f)
    api_key = config['zotero_api_key']
    notes_dir = pathlib.Path(config['notes_dir'])

subscribe_msg = {
    "action": "createSubscriptions",
    "subscriptions": [
        {
            "apiKey": api_key,
        }
    ]
}

def add_item(topic):
    print('Topic updated, checking for changes')
    s = requests.Session()
    s.headers.update({'Zotero-API-Key': api_key})
    base_url = f'https://api.zotero.org{topic}'
    payload = {'sort': 'dateAdded', 'limit': 10}
    r = s.get(f'{base_url}/items', params=payload)
    if r.status_code != 200:
        print('Bad response')
        return
    for item in r.json():
        d = item['data']
        tags = [x['tag'] for x in d['tags']]
        if 'ir' not in tags:
            continue
        print('Found IR item with title:', d.get('title', 'NA'))
        p = notes_dir / f'{d["key"]}.md'
        if p.is_file():
            print('Already exists')
            continue
        with open(p, 'w') as f:
            aliases = ''
            if (t := d.get('title')) is not None and t != '':
                aliases += f'  - {t}\n'
            if (t := d.get('shortTitle')) is not None and t != '':
                aliases += f'  - {t}\n'
            if aliases != '':
                aliases = f'\naliases:\n{aliases}'
            f.write(f'---\nzotero_key: {d["key"]}\nzotero_type: {d["itemType"]}{aliases}---')
        print('Created', p)

async def hello():
    uri = 'wss://stream.zotero.org'
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(subscribe_msg))
        async for message in websocket:
            message = json.loads(message)
            print(message)
            if message['event'] == 'topicUpdated':
                topic = message['topic']
                add_item(topic)

if __name__ == '__main__':
    asyncio.run(hello())

