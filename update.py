"""
Update priority of ilm notes scheduled for today.
"""
from scipy.stats import dirichlet

import common
from database import Ilm
from index import Indexer
from process import process


config = common.load_config()

@common.with_db
def update():
    """
    Properties in db and in post are assumed to be the same due
    to the indexer syncing changes. The exception is the "reviewed"
    property only in the post.
    """
    today = common.dt_now(config['timezone']).date()
    ilms = Ilm.select().where(Ilm.review_date == today)
    num = len(ilms)
    
    if num == 0:
        print('No ilms for review today.')
        return

    print(f'Setting priorities of {num} ilms.')
    if num == 1:
        priorities = [100]
    else:
        scores = [ilm.score for ilm in ilms]
        priorities = dirichlet.rvs(scores, size=1)[0].tolist()
    
    for ilm, priority in zip(ilms, priorities):
        post = common.read_post(ilm.path)
        post['priority'] = round(float(priority)*100, 2)
        common.write_post(post, ilm.path)

if __name__ == '__main__':
    # First do an index to get latest changes
    Indexer().index()
    # Then process ilms to update their schedules
    process()
    # Finally set priorities of ilms due for today
    update()
