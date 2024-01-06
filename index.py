"""
Go through all markdown files, find ilm notes, and index them.
"""
from pathlib import Path
import tqdm.auto as tqdm
import frontmatter
import peewee as pw

import common
from common import IlmException
from database import Ilm, db


# TODO: remove file from db that were removed 

class Indexer:
    def __init__(self):
        self.config = common.load_config()

    def index(self):
        print('Indexing...')
        try:
            db.connect()
            notes_dir = self.config['notes_dir']
            ilm_ids = [x[0] for x in Ilm.select(Ilm.ilm_id).tuples()]
            for path, post in tqdm.tqdm(common.iter_ilm_notes(notes_dir)):
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
        if ilm is None:
            ilm = common.ilm_from_post(post, path, create=True)
            print('Added to index.')
        else:
            if ilm.path != str(path):
                ilm.path = str(path)
                print('Path changed.')

            # Review date updated by user.
            # TODO: change priority to reflect this?
            review_date = common.parse_date(post['review'])
            if (ilm.review_date - review_date).days != 0:
                ilm.review_date = review_date
            
            # Score has changed by user.
            # TODO: change review date to reflect this?
            if ilm.score != post['score']:
                if post['score'] > 0: # must be valid
                    ilm.score = post['score']
                else:
                    post['score'] = ilm.score

            # Multiplier has changed by user.
            # TODO: change review date / priority to reflect this?
            if ilm.multiplier != post['multiplier']:
                if post['multiplier'] > 0: # must be valid
                    ilm.multiplier = post['multiplier']
                else:
                    post['multiplier'] = ilm.multiplier

            ilm.save()

            # Creation date changed by user, not allowed
            # so change back.
            created_date = common.parse_datetime(post['created'])
            if ilm.created_date != created_date:
                post['created'] = ilm.created_date.strftime(common.DATETIME_FORMAT)

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
