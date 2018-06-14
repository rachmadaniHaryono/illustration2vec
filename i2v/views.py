from flask import url_for, request
from flask_admin import AdminIndexView, expose, BaseView, form
from flask_admin.contrib.sqla import ModelView
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from jinja2 import Markup
from PIL import Image

from . import models
from . import make_i2v_with_chainer


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
        if False and not model.checksum.plausible_tag_estimations:
            img = Image.open(model.full_path)
            #  illust2vec = make_i2v_with_chainer(
                #  "illust2vec_tag_ver200.caffemodel", "tag_list.json")
            # res = illust2vec.estimate_plausible_tags([img], threshold=0.5)
            res = illust2vec.estimate_plausible_tags([img])
            res = res[0]
            tags = model.checksum.update_plausible_tag_estimation(res)
            session = models.db.session
            list(map(session.add, tags))
            session.commit()
        else:
            res = [{
                'character': [],
                'copyright': [],
                'general': [
                    ('1girl', 0.9720268249511719),
                    ('blue eyes', 0.9339820146560669),
                    ('blonde hair', 0.8899785876274109),
                    ('solo', 0.8786220550537109),
                    ('long hair', 0.832091748714447),
                    ('hair ornament', 0.39239054918289185)],
                'rating': [
                    ('safe', 0.9953395128250122),
                    ('questionable', 0.003477811813354492),
                    ('explicit', 0.00037872791290283203)]
            }]
            plausible_tags = res[0]
        return self.render('i2v/image_plausible_tag.html', plausible_tags=plausible_tags, model=model)

    def after_model_change(self, form, model, is_created):
        if is_created:
            session = models.db.session
            model.update_checksum(session)
            session.commit()
