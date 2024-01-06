"""
Update priority and schedule of ilm notes.
"""
from pathlib import Path
import datetime

import tqdm.auto as tqdm
import frontmatter
from scipy.stats import dirichlet

import common
from database import db, Ilm, Review
from index import Indexer


config = common.load_config()

def write_post(post, path):
    with open(path, 'w') as f:
        f.write(frontmatter.dumps(post))

@common.with_db
def update():
    """
    Properties in db and in post are assumed to be the same due
    to the indexer syncing changes. The exception is the "reviewed"
    property only in the post.
    """
    today_ilms = []
    for ilm in Ilm.select():
        print(f'Processing: {ilm.path}')
        post = common.read_post(ilm.path)
        original_metadata = post.metadata.copy()
        reviewed = post['reviewed']

        # Program is run at night which means timely reviews 
        # are done yesterday. It can happen that the update
        # script is run too late, so that the review date is
        # before yesterday. Deal with it the same way as a 
        # timely review for now.
        now = common.dt_now(config['timezone'])
        delta = (now.date() - ilm.review_date).days
        is_timely = delta == 1
        is_past = delta > 1
        is_today = delta == 0
        is_future = delta < 0
        is_early = is_future and reviewed
        print(f'- Now: {now}')
        print(f'- Review date: {ilm.review_date}')
        print(f'- Delta now and review date: {delta}')

        # Review date has passed or item reviewed early
        if is_past or is_timely or is_early:
            print(f'- Review date passed or reviewed too early (delta={delta})')
            # The order is important
            prev_review = Review.get_or_none(ilm=ilm)
            Review.create(ilm=ilm, reviewed=reviewed, 
                update_date=now, review_date=ilm.review_date,
                score=ilm.score, multiplier=ilm.multiplier)

            # Update schedule of ilm
            prev_date = ilm.created_date if prev_review is None else prev_review.review_date
            prev_date = datetime.datetime(prev_date.year, prev_date.month, prev_date.day)
            prev_date = common.set_timezone(prev_date, config['timezone'])
            interval = (now - prev_date).days
            # Reviewed same day as created interval=0, so set to 1
            new_interval = max(interval * ilm.multiplier, 1)
            print(f'- Prev review date: {prev_date}')
            print(f'- Cur interval: {interval}, New interval: {new_interval}')
            ilm.review_date = prev_date + datetime.timedelta(days=new_interval)
            ilm.save()
            post['review'] = ilm.review_date.strftime(common.DATE_FORMAT)
            post['reviewed'] = False

        if post.get('priority') is not None:
            post['priority'] = None
        
        if post.metadata != original_metadata:
            print('- Updating note.')
            write_post(post, ilm.path)

        # New review up today. Note that an ilm can be
        # reviewed two days successifily, so we cannot do an
        # elif statement here.
        if is_today:
            today_ilms.append(dict(ilm=ilm, post=post))
    
    # Update priorities
    if len(today_ilms) == 0:
        return
    print(f'Updating priorities of {len(today_ilms)} ilms.')
    if len(today_ilms) == 1:
        priorities = [1]
    else:
        scores = [ilm.score for ilm in today_ilms]
        priorities = dirichlet.rvs(scores, size=1, random_state=1)[0]
    for item, priority in zip(today_ilms, priorities):
        post = item['post']
        ilm = item['ilm']
        post['priority'] = priority
        write_post(post, ilm.path)

if __name__ == '__main__':
    # First do an index to get latest changes
    Indexer().index()
    update()
