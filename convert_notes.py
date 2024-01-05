"""
User can set markdown file to be tracked by giving it an
empty ilm property. This scripts detects them and gives
them appropriate values.
"""
from pathlib import Path
import tqdm.auto as tqdm
import frontmatter
import common

config = common.load_config()

def replace_metadata(post, metadata, key):
    if (val := post.metadata.pop(key, None)) is not None:
        metadata[key] = val

md_paths = config['notes_dir'].rglob('*.md')
for path in tqdm.tqdm(md_paths):
    if path.parent.name == '.trash':
        continue

    # Read
    try:
        with open(path, 'r') as f:
            post = frontmatter.load(f)
    except Exception as e:
        print(e)
        continue

    # Only consider posts marked as ilm-posts.
    if 'ilm' not in post:
        continue

    print(f'Found ilm note: {path}')

    cur_metadata = post.metadata.copy()

    # If note already conatins a non-null value for
    # the keys in the generated metadata, use that
    # instead. This is so we don't replace the user
    # specified values.
    metadata = common.gen_metadata(config['timezone'])
    for key in metadata.keys():
        replace_metadata(post, metadata, key)
    metadata.update(post.metadata)
    new_post = frontmatter.Post(post.content, **metadata)

    # Save time writing if no changes made
    if cur_metadata == metadata:
        print('Unchanged.')
        continue

    # Write
    try:
        with open(path, 'w') as f:
            f.write(frontmatter.dumps(new_post))
        print('Updated file with new changes.')
    except Exception as e:
        print(e)
        continue
