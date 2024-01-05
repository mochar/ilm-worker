import sys
import json
import datetime
import zoneinfo
import random
from pathlib import Path
import shortuuid


class IlmException(Exception):
    pass

def generate_id():
    return shortuuid.uuid()[:8]

def load_config():
    config_path = Path.home() / '.config' / 'ilm' / 'config.json'
    if not config_path.exists():
        print(f'Config "{config_path}" does not exist.')
        sys.exit()

    with open(config_path, 'r') as f:
        config = json.load(f)

    notes_dir = config['notes_dir'] = Path(config['notes_dir'])
    zotero_dir = config['zotero_dir'] = Path(config['zotero_notes_dir'])
    if not zotero_dir.is_absolute():
        zotero_dir = config['zotero_dir'] = notes_dir / zotero_dir
    if not zotero_dir.is_dir():
        print('Zotero notes directly does not exist.')
        sys.exit()

    return config

def dt_now(timezone):
    return datetime.datetime.now(zoneinfo.ZoneInfo(timezone))

def gen_metadata(timezone):
    now = dt_now(timezone)
    delay = random.choice(range(1, 6))
    review = now + datetime.timedelta(days=delay)
    metadata = {
        'ilm': generate_id(),
        'review': review.strftime('%Y-%m-%d'), 
        'score': 1,
        'created': now.strftime('%Y-%m-%dT%H:%M:%S')
    }
    return metadata
