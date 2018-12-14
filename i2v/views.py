import hashlib
import os
import shutil

from flask import url_for, request
from flask_admin import AdminIndexView, expose, BaseView, form
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from jinja2 import Markup
from PIL import Image
from werkzeug import secure_filename
import structlog

from . import models
from . import make_i2v_with_chainer


logger = structlog.getLogger(__name__)


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('i2v/home.html')


class ImageView(ModelView):

    def _list_thumbnail(view, context, model, name):
        res_templ = '<a class="btn btn-default" href="{}" role="button">Tag</a>'
        res = res_templ.format(url_for(
            '.plausible_tag_view', id=model.id))
        res += '<br/>'
        if not model.path:
            return Markup(res)
        res += '<img src="%s">' % url_for(
            'file', filename=form.thumbgen_filename(model.path))
        return Markup(res)

    column_formatters = {
        'path': _list_thumbnail,
        'checksum': lambda v, c, m, n: m.checksum.value[:7] if m.checksum else '',
    }
    form_extra_fields = {
        'path': form.ImageUploadField(
            'Image', base_path=models.file_path, thumbnail_size=(100, 100, True))
    }
    can_view_details = True
    create_modal = True
    form_excluded_columns = ('checksum', 'created_at')

    @expose('/plausible-tag')
    def plausible_tag_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)
        model = self.get_one(id)
        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)
        if not model.checksum.plausible_tag_estimations:
            img = Image.open(model.full_path)
            illust2vec = make_i2v_with_chainer(
                "illust2vec_tag_ver200.caffemodel", "tag_list.json")
            res = illust2vec.estimate_plausible_tags([img])
            res = res[0]
            tags = model.checksum.update_plausible_tag_estimation(res)
            session = models.db.session
            list(map(session.add, tags))
            session.commit()
        plausible_tags = model.checksum.get_plausible_tags()
        return self.render('i2v/image_plausible_tag.html', plausible_tags=plausible_tags, model=model)

    def after_model_change(self, form, model, is_created):
        def get_new_filename(src_filename, no_ext_basename=None, new_basename=None):
            assert not (no_ext_basename and new_basename)
            basename = os.path.basename(src_filename)
            if no_ext_basename:
                ext = os.path.splitext(basename)[1]
                new_basename = '{}{}'.format(no_ext_basename, ext)
            new_full_path = os.path.join(os.path.dirname(src_filename), new_basename)
            return new_full_path

        if is_created:
            session = models.db.session
            model.update_checksum(session)
            # old path
            full_path = model.full_path
            thumbgen_filename = model.thumbgen_filename
            #
            model.path = '{}{}'.format(
                model.checksum.value, os.path.splitext(full_path)[1])
            shutil.move(full_path, model.full_path)
            new_thumbgen_filename = model.thumbgen_filename
            try:
                shutil.move(
                    os.path.join(models.file_path, thumbgen_filename),
                    os.path.join(models.file_path, new_thumbgen_filename))
                logger.debug('Thumbnail moved.'.format(
                    src_thumb=thumbgen_filename, dst_thumb=new_thumbgen_filename))
            except FileNotFoundError as e:
                logger.debug('Thumbnail not found.'.format(
                    thumb=thumbgen_filename))
            session.commit()
