import click
import peewee as pw

from database import *


@click.group()
def ilm():
    pass

@ilm.command()
def create():
    db.create_tables([Ilm, Review])

@ilm.command()
def drop():
    db.drop_tables([Ilm, Review])

@ilm.command()
def recreate():
    db.drop_tables([Ilm, Review])
    db.create_tables([Ilm, Review])

if __name__ == '__main__':
    ilm()