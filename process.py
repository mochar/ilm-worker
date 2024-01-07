"""
Checks which items have been marked as reviewed and updates them. 
"""
import datetime

from frontmatter import Post

from database import Ilm, Review
import common
from common import ReviewState


config = common.load_config()

def process_ilm(ilm: Ilm, post: Post):
    reviewed = post['reviewed']
    now = common.dt_now(config['timezone'])
    prev_review = Review.get_or_none(ilm=ilm)
    prev_date = ilm.created_date.date() if prev_review is None else prev_review.review_date
    interval = (now.date() - prev_date).days

    # Schedule, i.e. calculate new interval.
    # Reviewed same day as created then interval=0, so set to 1.
    new_interval = max(interval, 1) * ilm.multiplier
    review_date = prev_date + datetime.timedelta(days=new_interval)
    print(f'- New review date: {review_date}')
    ilm.review_date = review_date
    post['review'] = review_date

    ## Update score
    if reviewed:
        ilm.score = ilm.score + 1
        post['score'] = ilm.score

    # Save and store
    ilm.save()
    post['reviewed'] = False
    common.write_post(post, ilm.path)

    # Add review record
    Review.create(ilm=ilm, reviewed=reviewed,
        update_date=now, review_date=ilm.review_date,
        score=ilm.score, multiplier=ilm.multiplier,
        next_review_date=ilm.review_date)

@common.with_db
def process():
    """
    Go through every ilm in db and read their corresponding
    files to determine if it has been reviewed or not.
    """
    for ilm in Ilm.select():
        post = common.read_post(ilm.path)
        reviewed = post['reviewed']
        now = common.dt_now(config['timezone']).date()
        review_state = ReviewState.determine(now, ilm.review_date,
            reviewed)
        
        # Also process ilms for which review date has passed but
        # somehow did not get updated.
        if reviewed or review_state is ReviewState.PAST:
            reason = 'reviewed' if reviewed else 'late'
            print(f'Processing ilm because {reason}: {ilm.path}')
            process_ilm(ilm, post)

if __name__ == '__main__':
    process()
