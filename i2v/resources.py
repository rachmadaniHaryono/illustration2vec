from flask import Flask
from flask_restful import Api, Resource, abort
from flask_restful_swagger import swagger

from . import models


class Checksum(Resource):
    "Checksum"
    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Checksum doesn't exist" },
          ]
        )
    def get(self, c_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        return {
            'created_at': str(item.created_at),
            'id': item.id, 'value': item.value,
            'tag_estimations': [
                {
                    'mode': x.mode.value,
                    'tag': x.tag.fullname,
                    'confidence': x.value,
                    'tag_id': x.tag.id,
                } for x in item.tag_estimations
            ],
        }


class ChecksumTag(Resource):
    "Checksum"
    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
            {
              "name": "t_id",
              "description": "Tag id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def get(self, c_id, t_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tags = {}
        for est_item in item.tag_estimations:
            if est_item.tag_id == t_id:
                tags.setdefault(est_item.tag.fullname, []).append(
                    {'mode': est_item.mode.value, 'confidence': est_item.value}
                )
        tags = [v for _, v in tags.items()]
        tag_item = session.query(models.Tag).filter_by(id=t_id).first()
        return {
            'checksum_id': item.id, 'checksum_value': item.value,
            'tag_id': tag_item.id, 'tag_value': tag_item.fullname,
            'estimations': tags,
        }

    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
            {
              "name": "t_id",
              "description": "Tag id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def post(self, c_id, t_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tag_item = session.query(models.Tag).filter_by(id=t_id).first()
        if not tag_item:
            abort(404, message="Tag {} doesn't exist".format(c_id))
        item.tags.append(tag_item)
        session.add(item)
        session.commit()
        tag_estimations = {}
        for est_item in item.tag_estimations:
            if est_item.tag_id == t_id:
                tag_estimations.setdefault(est_item.tag.fullname, []).append(
                    {'mode': est_item.mode.value, 'confidence': est_item.value}
                )
        tag_estimations = [v for _, v in tag_estimations.items()][0]
        return {
            'checksum_id': item.id, 'checksum_value': item.value,
            'tag_id': tag_item.id, 'tag_value': tag_item.fullname,
            'estimations': tag_estimations,
            'status': 'valid'
        }

    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
            {
              "name": "t_id",
              "description": "Tag id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def delete(self, c_id, t_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tag_item = session.query(models.Tag).filter_by(id=t_id).first()
        if not tag_item:
            abort(404, message="Tag {} doesn't exist".format(c_id))
        if tag_item in item.tags:
            item.tags.remove(tag_item)
        session.add(item)
        session.commit()


class ChecksumInvalidTag(Resource):
    "Checksum"

    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
            {
              "name": "t_id",
              "description": "Tag id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def post(self, c_id, t_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tag_item = session.query(models.Tag).filter_by(id=t_id).first()
        if not tag_item:
            abort(404, message="Tag {} doesn't exist".format(c_id))
        item.invalid_tags.append(tag_item)
        session.add(item)
        session.commit()
        tag_estimations = {}
        for est_item in item.tag_estimations:
            if est_item.tag_id == t_id:
                tag_estimations.setdefault(est_item.tag.fullname, []).append(
                    {'mode': est_item.mode.value, 'confidence': est_item.value}
                )
        tag_estimations = [v for _, v in tag_estimations.items()][0]
        return {
            'checksum_id': item.id, 'checksum_value': item.value,
            'tag_id': tag_item.id, 'tag_value': tag_item.fullname,
            'estimations': tag_estimations,
            'status': 'valid'
        }

    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
            {
              "name": "t_id",
              "description": "Tag id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def delete(self, c_id, t_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tag_item = session.query(models.Tag).filter_by(id=t_id).first()
        if not tag_item:
            abort(404, message="Tag {} doesn't exist".format(c_id))
        if tag_item in item.invalid_tags:
            item.invalid_tags.remove(tag_item)
        session.add(item)
        session.commit()
        return { "code": 201, "message": "Success" }


class ChecksumTagList(Resource):
    "Checksum tag list."
    @swagger.operation(
        notes='Checksum api',
        responseClass='checksum',
        nickname='checksum',
        parameters=[
            {
              "name": "c_id",
              "description": "Checksum id",
              "required": False,
              "allowMultiple": False,
              "dataType": 'int',
              "paramType": "path"
            },
          ],
        responseMessages=[
            { "code": 201, "message": "Success" },
            { "code": 405, "message": "Invalid input" },
            { "code": 404, "message": "Item doesn't exist" },
          ]
        )
    def get(self, c_id):
        session = models.db.session
        item = session.query(models.Checksum).filter_by(id=c_id).first()
        if not item:
            abort(404, message="Checksum {} doesn't exist".format(c_id))
        tags = {}
        tag_id_name = {}
        for est_item in item.tag_estimations:
            tag_id_name[est_item.tag.fullname] = est_item.tag.id
            tags.setdefault(est_item.tag.fullname, []).append(
                {'mode': est_item.mode.value, 'confidence': est_item.value}
            )
        tags = [
            {'tag_value': k, 'tag_id': tag_id_name[k], 'estimations': v}
            for k, v in tags.items()
        ]
        return {
            'checksum_id': item.id, 'checksum_value': item.value,
            'tags': tags,
        }
