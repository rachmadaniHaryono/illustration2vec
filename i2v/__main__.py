#!/usr/bin/env python
from pprint import pprint
import hashlib
import sys

from flask import Flask, __version__ as flask_version
from flask.cli import FlaskGroup
from flask_admin import Admin
from PIL import Image
import click

from . import make_i2v_with_chainer, views


__version__ = '0.2.1'


class CustomFlaskGroup(FlaskGroup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.params[0].help = 'Show the program version'
        self.params[0].callback = get_custom_version


def get_custom_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    message = 'Illustration2Vec %(app_version)s\nFlask %(version)s\nPython %(python_version)s'
    click.echo(message % {
        'app_version': __version__,
        'version': flask_version,
        'python_version': sys.version,
    }, color=ctx.color)
    ctx.exit()


def create_app():
    app = Flask(__name__)
    # other setup
    admin = Admin(
        app, name='Youtube-beets', template_mode='bootstrap3', url='/',
        index_view=views.HomeView()
    )
    return app


@click.group(cls=CustomFlaskGroup, create_app=create_app)
def cli():
    """Illustration2Vec."""
    pass


@cli.command()
@click.option('--output', default='default')
@click.argument('images', nargs=-1)
def estimate_plausible_tags(images, output='default'):
    """Estimate plausible tags."""
    illust2vec = make_i2v_with_chainer(
        "illust2vec_tag_ver200.caffemodel", "tag_list.json")
    image_sets = map(lambda x: {'value': x, 'sha256':sha256_checksum(x)}, images)
    for idx, img_set in enumerate(image_sets):
        img = Image.open(img_set['value'])
        res = illust2vec.estimate_plausible_tags([img], threshold=0.5)
        if isinstance(res[idx]['rating'], zip):
            res[idx]['rating'] = list(res[idx]['rating'])
        print("image: {}\nsha256: {}".format(
            img_set['value'], img_set['sha256']))
        if output == 'pprint':
            pprint(res)
        else:
            print(res)


def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()


if __name__ == '__main__':
    cli()
