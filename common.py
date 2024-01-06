import sys
import json
import datetime
import zoneinfo
import random
from pathlib import Path

import shortuuid
import frontmatter

from database import db, Ilm

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


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
    zotero_dir = config['zotero_notes_dir'] = Path(config['zotero_notes_dir'])
    data_dir = config['data_dir'] = Path(config['data_dir'])
    if not zotero_dir.is_absolute():
        zotero_dir = config['zotero_notes_dir'] = notes_dir / zotero_dir
    if not zotero_dir.is_dir():
        print('Zotero notes directory does not exist.')
        sys.exit()
    if not data_dir.is_absolute():
        print('Data directory must be an absolute path to an existing folder.')
        sys.exit()

    return config

def dt_now(timezone):
    now = datetime.datetime.now(zoneinfo.ZoneInfo(timezone))
    # now += datetime.timedelta(days=1)
    return now

def set_timezone(dt, timezone):
    return dt.replace(tzinfo=zoneinfo.ZoneInfo(timezone))

def read_post(path):
    with open(path, 'r') as f:
        post = frontmatter.load(f)
    return post

def gen_metadata(timezone):
    now = dt_now(timezone)
    delay = random.choice(range(1, 6))
    review = now + datetime.timedelta(days=delay)
    # In format recognized by obsidian
    metadata = {
        'ilm': generate_id(),
        'review': review.date(),
        'reviewed': False,
        'score': 1,
        'multiplier': 2,
        'created': now
    }
    return metadata

def ilm_from_post(post, path, create: bool):
    ilm = Ilm(path=path, ilm_id=post['ilm'], zot_key=post.get('zotero'),
        created_date=post['created'], review_date=post['review'],
        score=post['score'], multiplier=post['multiplier'])
    if create:
        ilm.save()
    return ilm

def iter_ilm_notes(notes_path: Path):
    md_paths = notes_path.rglob('*.md')
    for path in md_paths:
        if path.parent.name == '.trash':
            continue

        # Read
        try:
            post = read_post(path)
        except Exception as e:
            print(e)
            continue

        # Only consider posts marked as ilm-posts.
        if 'ilm' not in post:
            continue

        yield path, post

def with_db(fun):
    def inner(*args, **kwargs):
        try:
            db.connect()
            fun(*args, **kwargs)
        finally:
            db.close()
    return inner

def parse_datetime(dt):
    return datetime.datetime.strptime(dt, DATETIME_FORMAT)

def parse_date(dt):
    return datetime.datetime.strptime(dt, DATE_FORMAT).date()
