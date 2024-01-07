"""
Check for new items added to zotero with the "ilm" tag
and create a note for them.
"""
import sys
import json
import asyncio
import websockets

import requests
import frontmatter

import common
from common import IlmException
from database import Ilm

config = common.load_config()
api_key = config['zotero_api_key']
check_limit = config['zotero_check_limit']
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
    metadata['zotero'] = item["key"]

    aliases = []
    if (t := item.get('title')) is not None and t != '':
        aliases.append(t)
    if (t := item.get('shortTitle')) is not None and t != '':
        aliases.append(t)
    if len(aliases) > 0:
        metadata['aliases'] = aliases
    
    metadata['source'] = [
        f'zotero://select/library/items/{item["key"]}',
        f'https://www.zotero.org/charmo/items/{item["key"]}'
    ]

    content = ''
    post = frontmatter.Post(content, **metadata)
    return post

@common.with_db
def process_topic(topic):
    s = requests.Session()
    s.headers.update({'Zotero-API-Key': api_key})
    base_url = f'https://api.zotero.org{topic}'
    payload = {'sort': 'dateModified', 'limit': check_limit}
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

        post = process_item(d)

        # Determine file name.
        # TODO: Determine if this should be the title if there is one.
        # For now find it more convenient to have key as file name.
        """
        if len(post.get('aliases', [])) == 0:
            filename = d['key']
        else:
            filename = post['aliases'].pop()
        """
        filename = d['key']

        # It might be in db and user removed file later on.
        # This edge case should not happen as deleted ilm notes
        # are removed from db as well.
        path = zotero_dir / f'{filename}.md'
        if not path.exists():
            with open(path, 'w') as f:
                f.write(frontmatter.dumps(post))

        # Save item to disk and index
        if Ilm.select().where(Ilm.zot_key == d['key']).exists():
            print('Item already processed, removing tag from Zotero.')
        else:
            common.ilm_from_post(post, path, create=True)
            print('Item created.')

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
                    print('Topic updated, checking for changes.')
                    process_topic(topic)
                except IlmException as e:
                    print(f'Ilm error: {e}')
                except Exception as e:
                    print(f'Error: {str(e)}')

if __name__ == '__main__':
    process_topic('/users/5357939')
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        sys.exit()
    asyncio.run(hello())
