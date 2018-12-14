import hashlib
import os
import shutil
import time

from flask import flash, redirect, request, url_for
from flask_admin import AdminIndexView, expose, BaseView, form
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView, filters
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


class ChecksumView(ModelView):

    #  can_export = True
    column_default_sort = ('created_at', True)
    column_formatters = {
        'created_at': 
        lambda v, c, m, n: 
        Markup('<p data-toggle="tooltip" data-placement="top" title="{}">{}</p>'.format(
            m.created_at,
            arrow.Arrow.fromdatetime(m.created_at, tzinfo='local').humanize(arrow.now())
        )),
        'value': lambda v, c, m, n: Markup('<a href="{}">{}</a> {}'.format(
            url_for('tagestimation.index_view', flt4_checksum_value_equals=getattr(m, n)),
            '(tag estimation)',
            getattr(m, n)
        ))
    }
    edit_modal = True
    #  export_types = ['json']


class HomeView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('i2v/home.html')


class ImageView(ModelView):

    def _list_thumbnail(view, context, model, name):
        btn_templ = '<a class="btn btn-default" href="{}" role="button">{}</a>'
        pt_button =  btn_templ.format(url_for('.plausible_tag_view', id=model.id), 'Plausible Tag')
        tt_button =  btn_templ.format(url_for( '.top_tag_view', id=model.id), 'Top Tag')
        img_figure = '<figure><img src="{}"><figcaption>{}</figcaption></figure>'.format(
            url_for('file', filename=form.thumbgen_filename(model.path)),
            model.checksum.value[:7]
        )
        res = '<div>{}</div><div>{}{}</div>'.format(img_figure, pt_button, tt_button)
        return Markup(res)

    can_edit = False
    column_default_sort = ('created_at', True)
    column_exclude_list = ('checksum', )
    create_modal = True
    form_excluded_columns = ('checksum', 'created_at')
    form_extra_fields = {
        'path': form.ImageUploadField(
            'Image', base_path=models.file_path, thumbnail_size=(100, 100, True))
    }
    column_formatters = {
        'path': _list_thumbnail,
        'created_at': 
        lambda v, c, m, n: 
        Markup('<p data-toggle="tooltip" data-placement="top" '
        'title="{}">{}</p>'.format(
            m.created_at,
            arrow.Arrow.fromdatetime(m.created_at, tzinfo='local').humanize(arrow.now())
        )),
    }

    @expose('/plausible-tag')
    def plausible_tag_view(self):
        return self._tag_view_base(mode=models.MODE_PLAUSIBLE_TAG)

    @expose('/top-tag')
    def top_tag_view(self):
        return self._tag_view_base(mode=models.MODE_TOP_TAG)

    @expose('/all-tag')
    def all_tag_view(self):
        return self._tag_view_base(mode=models.MODE_ALL_TAG)

    def _tag_view_base(self, mode):
        return_url = get_redirect_target() or self.get_url('.index_view')
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)
        model = self.get_one(id)
        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)
        valid_mode = [models.MODE_PLAUSIBLE_TAG, models.MODE_TOP_TAG, models.MODE_ALL_TAG]
        if mode not in valid_mode:
            flash(gettext('Unknown mode.'), 'error')
            return redirect(return_url)
        estimated_tags = model.checksum.get_estimated_tags(mode=mode)
        if  not any(estimated_tags.values()):
            img = Image.open(model.full_path)
            start_time = time.time()
            global ILLUST2VEC
            if not ILLUST2VEC:
                model_path = os.getenv('ILLUSTRATION2VEC_MODEL')
                if not model_path:
                    model_path =  "illust2vec_tag_ver200.caffemodel"
                ILLUST2VEC = make_i2v_with_chainer(model_path, "tag_list.json")
            illust2vec = ILLUST2VEC
            end = time.time()
            logger.debug('i2v initiated', time=(time.time() - start_time))
            if mode == models.MODE_PLAUSIBLE_TAG:
                res = illust2vec.estimate_plausible_tags([img])
            elif mode == models.MODE_TOP_TAG:
                res = illust2vec.estimate_top_tags([img])
            elif mode == models.MODE_ALL_TAG:
                res1 = illust2vec.estimate_plausible_tags([img])
                res2 = illust2vec.estimate_top_tags([img])
                res = {k: dict(v) for k, v in res1[0].items()}
                for main_key, item in res2[0].items():
                    dict_item = dict(item)
                    for key, value in dict_item.items():
                        if key in res[main_key]:
                            res[main_key][key] = (value + res[main_key][key])/2
                        else:
                            res[main_key][key] = value
                for main_key, item in res.items():
                    res[main_key] = [(k, v) for k, v in item.items()]
                res = [res]
            else:
                flash(gettext('Unknown mode.'), 'error')
                return redirect(return_url)
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
            if thumbgen_filename != new_thumbgen_filename:
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

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        res = super().create_view()
        if get_redirect_target() == url_for('image.plausible_tag_view') and \
                request.method == 'POST':
            form = self.create_form()
            if self.validate_form(form):
                model = self.create_model(form)
                return redirect(url_for('image.plausible_tag_view', id=model.id))
        return res

    def create_model(self, form):
        """
            Create model from form.

            :param form:
                Form instance
        """
        try:
            model = self.model()
            form.populate_obj(model)
            checksum = models.sha256_checksum(model.full_path)
            checksum_m = models.get_or_create(self.session, models.Checksum, value=checksum)[0]
            instance = self.session.query(self.model).filter_by(checksum=checksum_m).first()
            if instance:
                model = instance
            self.session.add(model)
            self._on_model_change(form, model, True)
            self.session.commit()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
                logger.exception('Failed to create record.')
            self.session.rollback()
            return False
        else:
            self.after_model_change(form, model, True)
        return model


class TagEstimationModeFilter(filters.BaseSQLAFilter):

    def apply(self, query, value, alias=None):
        res =  query.filter(self.column.mode == value)
        return res

    def operation(self):
        return 'equal'


class TagEstimationView(ModelView):

    column_default_sort = ('created_at', True)
    column_formatters = {
        'checksum': lambda v, c, m, n: getattr(m, n).value[:7] if hasattr(getattr(m,n), 'value') else 'None',
        'created_at': 
        lambda v, c, m, n: 
        Markup('<p data-toggle="tooltip" data-placement="top" '
        'title="{}">{}</p>'.format(
            m.created_at,
            arrow.Arrow.fromdatetime(m.created_at, tzinfo='local').humanize(arrow.now())
        )),
        'mode': lambda v, c, m, n: getattr(m, n).code,
        'tag': lambda v, c, m, n: getattr(m, n).fullname,
        'value': lambda v, c, m, n: '{0:0.2f}'.format(getattr(m, n) * 100),
    }
    column_filters = (
        'checksum', 'tag', 'value', 
        TagEstimationModeFilter(models.TagEstimation, 'mode', options=models.TagEstimation.MODES)
    )
    column_list = ('created_at', 'checksum', 'mode', 'tag', 'value')
    form_excluded_columns = ('created_at', )
    named_filter_urls = True
    page_size = 100
