from flask_admin import AdminIndexView, expose, BaseView, form
from flask_admin.contrib.sqla import ModelView
from jinja2 import Markup
from flask import url_for

from . import models


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('i2v/home.html')


class ImageView(ModelView):

    def _list_thumbnail(view, context, model, name):
        if not model.path:
            return ''
        return Markup('<img src="%s">' % url_for(
            'file', filename=form.thumbgen_filename(model.path)))

    column_formatters = {'path': _list_thumbnail}
    form_extra_fields = {
        'path': form.ImageUploadField(
            'Image', base_path=models.file_path, thumbnail_size=(100, 100, True))
    }
