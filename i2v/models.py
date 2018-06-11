#!/usr/bin/env python3
"""Model module."""
import os
import os.path as op
from datetime import datetime

from appdirs import user_data_dir
from flask_admin import form
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from sqlalchemy.types import TIMESTAMP


db = SQLAlchemy()
file_path = op.join(user_data_dir('Illustration2Vec', 'Masaki Saito'), 'files')


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(TIMESTAMP, default=datetime.now, nullable=False)


class Image(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    path = db.Column(db.String)
    checksum_id = db.Column(db.Integer, db.ForeignKey('checksum.id'))
    checksum = db.relationship(
        'Checksum', foreign_keys='Image.checksum_id', lazy='subquery',
        backref=db.backref('images', lazy=True, cascade='delete'))

    def __repr__(self):
        return self.name


@listens_for(Image, 'after_delete')
def del_image(mapper, connection, target):
    if target.path:
        # Delete image
        try:
            os.remove(op.join(file_path, target.path))
        except OSError:
            pass
        # Delete thumbnail
        try:
            os.remove(op.join(file_path, form.thumbgen_filename(target.path)))
        except OSError:
            pass


class Checksum(Base):
    value = db.Column(db.String, unique=True)
