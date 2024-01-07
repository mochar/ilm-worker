"""
Go through all markdown files, find ilm notes, and index them.
"""
import tqdm.auto as tqdm
import frontmatter
import peewee as pw

import common
from database import Ilm, db


class Indexer:
    def __init__(self):
        self.config = common.load_config()

    def index(self):
        print('Indexing...')
        try:
            db.connect()
            notes_dir = self.config['notes_dir']
            ilm_ids = [x[0] for x in Ilm.select(Ilm.ilm_id).tuples()]
            for path, post in tqdm.tqdm(common.iter_ilm_notes(notes_dir), disable=True):
                ilm_id = self.process_post(path, post)
                if ilm_id in ilm_ids:
                    ilm_ids.remove(ilm_id)
            n_deleted = Ilm.delete().where(Ilm.ilm_id.in_(ilm_ids)).execute()
            if n_deleted > 0:
                print(f'Removing {n_deleted} deleted ilms.')
        except Exception as e:
            print('Exception occured while indexing:')
            print(e)
        finally:
            db.close()

    def validate_post(self, post, ilm=None):
        template = common.gen_metadata(self.config['timezone'])
        now = template['created'] # hacky 

        if post['score'] <= 0: 
            print('Fixing invalid score value.')
            score = template['score'] if ilm is None else ilm.score
            post['score'] = score

        if post['multiplier'] <= 1:
            print('Fixing invalid multiplier value.')
            multiplier = template['multiplier'] if ilm is None else ilm.multiplier
            post['multiplier'] = multiplier

        if ilm is not None:
            # Uncommented because
            # - Maybe I want to change creation date
            # - Creation date always considered altered on first check,
            #   geen zin to check why.
            """
            # Creation date changed by user, not allowed
            # so change back.
            if ilm.created_date != post['created']:
                print('Fixing altered creation date.')
                post['created'] = ilm.created_date
            """

            # Can't move review date to the past. But user also cannot
            # move review date to today because priorities of today's 
            # reviews have already been determined. User can just review
            # item if he doesn't want to wait.
            if post['review'] != ilm.review_date and post['review'] <= now.date():
                print('Fixing invalid review date: review value.')
                review = template['review'] if ilm is None else ilm.review_date
                post['review'] = review

        return post

    def process_post(self, path, post):
        print(f'Found ilm note: {path}')

        # User can set markdown file to be tracked by giving it an
        # empty ilm property. It might also be the case that some
        # required properties are missing. Ilmifying will add any
        # missing properties.
        original_metadata = post.metadata.copy()
        post = self.ilmify(post)
        ilmified_metadata = post.metadata.copy()

        # Save index to db
        ilm = Ilm.get_or_none(ilm_id=post['ilm'])
        post = self.validate_post(post, ilm)
        if ilm is None:
            # Not yet indexed, so add it to db.
            try:
                ilm = common.ilm_from_post(post, path, create=True)
            except pw.IntegrityError as e:
                # It can be the case that the current post
                # has replaced the path of an old ilm. In that case, the
                # ilm index of the deleted post will still exist with the
                # path, so just creating a new one now will lead to an
                # error that the path already exists. So, delete.
                print('Deleting old ilm with overwritten path.')
                Ilm.get(path=str(path)).delete_instance()
                ilm = common.ilm_from_post(post, path, create=True)

            print('Added to index.')
        else:
            # Update index with new values
            if ilm.path != str(path):
                ilm.path = str(path)
                print('Path changed.')

            # Review date updated by user.
            # TODO: change priority to reflect this?
            review_date = post['review']
            if (ilm.review_date - review_date).days != 0:
                ilm.review_date = review_date
            
            # Score has changed by user.
            # TODO: change review date to reflect this?
            if ilm.score != post['score']:
                ilm.score = post['score']

            # Multiplier has changed by user.
            # TODO: change review date / priority to reflect this?
            if ilm.multiplier != post['multiplier']:
                ilm.multiplier = post['multiplier']

            ilm.save()

        # Write changes to disk if they exist.
        if original_metadata != ilmified_metadata or post.metadata != ilmified_metadata:
            with open(path, 'w') as f:
                f.write(frontmatter.dumps(post))
            print('Updated file with new changes.')
        
        return post['ilm']
        
    def ilmify(self, cur_post):
        """
        If note already conatins a non-null value for
        the keys in the generated metadata, use that
        instead. This is so we don't replace the user
        specified values.
        """
        new_metadata = common.gen_metadata(self.config['timezone'])
        for key in new_metadata.keys():
            if (val := cur_post.metadata.pop(key, None)) is not None:
                new_metadata[key] = val
        new_metadata.update(cur_post.metadata)
        new_post = frontmatter.Post(cur_post.content, **new_metadata)
        return new_post

if __name__ == '__main__':
    indexer = Indexer()
    indexer.index()
