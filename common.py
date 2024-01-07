import sys
import json
import datetime
import zoneinfo
import random
from enum import Enum
from pathlib import Path

import shortuuid
import frontmatter

from database import db, Ilm

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class IlmException(Exception):
    pass

class ReviewState(Enum):
    """
    The review state depends on 
    1. Difference today and review date in days ("delta").
    2. Whether or not the ilm has been marked as reviewed.

    PAST:
    The ilm review date was some day before today. This can happen when:
    - The ilm was not reviewed and therefore not processed by the 
      `process_reviews` script. Processing is therefore happening by
      the daily run `update` script. (delta=1)
    - The ilm was reviewed close to midgnight so the `process_reviews` 
      script did not catch it on time. (delta=1)
    - Both scripts for some reason did not run (bugs/server down/etc),
      The review date has thus passed but the ilm has not been assigned 
      a new review date yet. (delta>1)

    TODAY:
    The ilm is in the queue for today, and can be reviewed or not (yet).
    (delta=0)

    FUTURE:
    The ilm is scheduled for review in the future AND has not been
    reviewed. (delta<0)

    EARLY:
    The ilm is scheduled for review in the future AND has been reviewed.
    (delta<0)
    """
    PAST = 1
    TODAY = 2
    FUTURE = 3
    EARLY = 4

    @staticmethod
    def determine(date_now, date_review, reviewed: bool):
        delta = (date_now - date_review).days
        if delta > 0:
            return ReviewState.PAST
        if delta == 0:
            return ReviewState.TODAY
        if reviewed:
            return ReviewState.EARLY
        else:
            return ReviewState.FUTURE

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

def write_post(post, path):
    with open(path, 'w') as f:
        f.write(frontmatter.dumps(post))
