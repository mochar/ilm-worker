from pathlib import Path
import json
from peewee import *

config_path = Path.home() / '.config' / 'ilm' / 'config.json'
with open(config_path, 'r') as f:
    config = json.load(f)
db = PostgresqlDatabase('ilm', user=config['postgres_user'])

class BaseModel(Model):
    class Meta:
        database = db

class Ilm(BaseModel):
    # peewee will automatically add an auto-incrementing integer 
    # primary key field named id.
    ilm_id = CharField(unique=True)
    zot_key = CharField(null=True)
    path = CharField(unique=True)
    created_date = DateTimeField()

    review_date = DateField()
    score = FloatField()
    multiplier = FloatField()

class Review(BaseModel):
    ilm = ForeignKeyField(Ilm, backref='reviews', 
        on_delete='CASCADE')
    update_date = DateTimeField()
    # Ilm properties at time of review
    review_date = DateField()
    reviewed = BooleanField()
    score = FloatField()
    multiplier = FloatField()
    # Decided at update
    next_review_date = DateField()
