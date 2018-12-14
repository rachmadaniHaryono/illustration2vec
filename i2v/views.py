import hashlib
import os
import shutil
import time

from flask import url_for, request
from flask_admin import AdminIndexView, expose, BaseView, form
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from jinja2 import Markup
from PIL import Image
from werkzeug import secure_filename
import arrow
import structlog

from . import models
from . import make_i2v_with_chainer


logger = structlog.getLogger(__name__)
ILLUST2VEC = None


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('i2v/home.html')


class ImageView(ModelView):

    def _list_thumbnail(view, context, model, name):
        res_templ = '<a class="btn btn-default" href="{}" role="button">Plausible Tag</a>'
        res = res_templ.format(url_for(
            '.plausible_tag_view', id=model.id))
        res_templ = '<a class="btn btn-default" href="{}" role="button">Top Tag</a>'
        res += res_templ.format(url_for(
            '.top_tag_view', id=model.id))
        res += '<br/>'
        if not model.path:
            return Markup(res)
        res += '<img src="%s">' % url_for(
            'file', filename=form.thumbgen_filename(model.path))
        return Markup(res)

    column_formatters = {
        'path': _list_thumbnail,
        'checksum': lambda v, c, m, n: m.checksum.value[:7] if m.checksum else '',
        'created_at': 
        lambda v, c, m, n: 
        Markup('<p data-toggle="tooltip" data-placement="top" '
        'title="{}">{}</p>'.format(
            m.created_at,
            arrow.Arrow.fromdatetime(m.created_at, tzinfo='local').humanize(arrow.now())
        )),
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
        return self._tag_view_base(mode=models.MODE_PLAUSIBLE_TAG)

    @expose('/top-tag')
    def top_tag_view(self):
        return self._tag_view_base(mode=models.MODE_TOP_TAG)

    def _tag_view_base(self, mode):
        return_url = get_redirect_target() or self.get_url('.index_view')
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)
        model = self.get_one(id)
        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)
        if mode not in [models.MODE_PLAUSIBLE_TAG, models.MODE_TOP_TAG]:
            flash(gettext('Unknown mode.'), 'error')
            return redirect(return_url)
        estimated_tags = model.checksum.get_estimated_tags(mode=mode)
        if  not any(estimated_tags.values()):
            img = Image.open(model.full_path)
            start_time = time.time()
            global ILLUST2VEC
            if not ILLUST2VEC:
                ILLUST2VEC = make_i2v_with_chainer(
                "illust2vec_tag_ver200.caffemodel", "tag_list.json")
            illust2vec = ILLUST2VEC
            end = time.time()
            logger.debug('i2v initiated', time=(time.time() - start_time))
            if mode == models.MODE_PLAUSIBLE_TAG:
                res = illust2vec.estimate_plausible_tags([img])
            else:
                res = illust2vec.estimate_top_tags([img])
            res = res[0]
            session = models.db.session
            tags = list(model.checksum.update_tag_estimation(
                res, mode=mode, session=session))
            list(map(session.add, tags))
            session.commit()
        estimated_tags = model.checksum.get_estimated_tags(mode=mode)
        return self.render('i2v/image_tag.html', estimated_tags=estimated_tags, model=model, mode=mode)

    def after_model_change(self, form, model, is_created):
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
