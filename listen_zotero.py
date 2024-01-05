import sys
import glob
import json
from pathlib import Path
import random
import asyncio
import websockets

import requests
import frontmatter
import peewee as pw

import common
from common import IlmException


config = common.load_config()
api_key = config['zotero_api_key']
check_limit = config['check_limit']
notes_dir = config['notes_dir']
zotero_dir = config['zotero_notes_dir']

subscribe_msg = {
    "action": "createSubscriptions",
    "subscriptions": [
        {
            "apiKey": api_key,
        }
    ]
}

def item_is_ilm(item):
    tags = [x['tag'].lower() for x in item['tags']]
    return 'ilm' in tags

def process_item(item):
    metadata = common.gen_metadata(config['timezone'])
    metadata['zotero'] = f'zotero://select/library/items/{item["key"]}'

    aliases = []
    if (t := item.get('title')) is not None and t != '':
        aliases.append(t)
    if (t := item.get('shortTitle')) is not None and t != '':
        aliases.append(t)
    if len(aliases) > 0:
        metadata['aliases'] = aliases

    post = frontmatter.Post('', **metadata)
    return post

def process_updates(topic):
    print('Topic updated, checking for changes.')
    s = requests.Session()
    s.headers.update({'Zotero-API-Key': api_key})
    base_url = f'https://api.zotero.org{topic}'
    payload = {'sort': 'dateAdded', 'limit': check_limit}
    try:
        r = s.get(f'{base_url}/items', params=payload)
    except Exception as e:
        print('Something went wrong retrieving latest items from Zotero.')
        raise e
    if r.status_code != 200:
        raise IlmException(f'Something went wrong retrieving latest items from Zotero: status code {r.status_code}')

    for item in r.json():
        d = item['data']
        if not item_is_ilm(d):
            continue
        print('Found Ilm item with title:' + d.get('title', 'NA'))

        post = process_item(item)

        # Determine file name
        if len(post.get('aliases', [])) == 0:
            filename = d['key']
        else:
            filename = post['aliases'].pop()

        # Save to disk
        path = zotero_dir / f'{filename}.md'
        if not path.is_file():
            with open(path, 'w') as f:
                f.write(frontmatter.dumps(post))
            print('Item created.')
        else:
            print('Item already processed, removing tag from Zotero.')
        
        # Remove ilm tag from zotero item
        try:
            tags = [x for x in d['tags'] if x['tag'].lower() != 'ilm']
            payload = {'version': item['version'], 'tags': tags}
            r = s.patch(f'{base_url}/items/{d["key"]}', json=payload)
            if r.status_code != 204:
                raise IlmException(f'Something went wrong removing tag: status code {r.status_code}')
        except Exception as e:
            print('Something went wrong updating item without ilm tag.')
            raise e
        print('Removed ilm tag from Zotero item.')

async def hello():
    uri = 'wss://stream.zotero.org'
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(subscribe_msg))
        async for message in websocket:
            message = json.loads(message)
            print(message)
            if message['event'] == 'topicUpdated':
                topic = message['topic']
                try:
                    process_updates(topic)
                except IlmException as e:
                    print(f'Ilm error: {e}')
                except Exception as e:
                    print(f'Error: {str(e)}')

if __name__ == '__main__':
    process_updates('/users/5357939')
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        sys.exit()
    asyncio.run(hello())
