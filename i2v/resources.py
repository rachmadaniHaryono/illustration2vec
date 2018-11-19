from flask import Flask
from flask_restful import Api, Resource, abort
from flask_restful_swagger import swagger

from . import models


# You may decorate your operation with @swagger.operation
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
                } for x in item.tag_estimations
            ],
        }
