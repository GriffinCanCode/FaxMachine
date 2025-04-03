from flask import Blueprint, jsonify, request
from typing import Dict, List, Optional, Union
from http import HTTPStatus

from .models import ModelName
from .schemas import model_schema, models_schema
from .services import ModelService
from .exceptions import ResourceNotFoundError

# Create a blueprint for this resource
blueprint = Blueprint("resource_name", __name__, url_prefix="/api/resource")

@blueprint.route("/", methods=["GET"])
def get_all_resources():
    """
    Get all resources.
    ---
    tags:
      - Resources
    responses:
      200:
        description: A list of resources
    """
    try:
        resources = ModelService.get_all()
        return jsonify(models_schema.dump(resources)), HTTPStatus.OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@blueprint.route("/<int:resource_id>", methods=["GET"])
def get_resource(resource_id: int):
    """
    Get a specific resource by ID.
    ---
    tags:
      - Resources
    parameters:
      - name: resource_id
        in: path
        type: integer
        required: true
        description: ID of the resource
    responses:
      200:
        description: Resource details
      404:
        description: Resource not found
    """
    try:
        resource = ModelService.get_by_id(resource_id)
        if not resource:
            return jsonify({"error": "Resource not found"}), HTTPStatus.NOT_FOUND
        return jsonify(model_schema.dump(resource)), HTTPStatus.OK
    except ResourceNotFoundError:
        return jsonify({"error": "Resource not found"}), HTTPStatus.NOT_FOUND
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@blueprint.route("/", methods=["POST"])
def create_resource():
    """
    Create a new resource.
    ---
    tags:
      - Resources
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
            description:
              type: string
    responses:
      201:
        description: Resource created
      400:
        description: Invalid input
    """
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Name is required"}), HTTPStatus.BAD_REQUEST
        
        resource = ModelService.create(data)
        return jsonify(model_schema.dump(resource)), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@blueprint.route("/<int:resource_id>", methods=["PUT"])
def update_resource(resource_id: int):
    """
    Update a resource.
    ---
    tags:
      - Resources
    parameters:
      - name: resource_id
        in: path
        type: integer
        required: true
        description: ID of the resource
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
            description:
              type: string
    responses:
      200:
        description: Resource updated
      404:
        description: Resource not found
      400:
        description: Invalid input
    """
    try:
        data = request.get_json()
        resource = ModelService.update(resource_id, data)
        return jsonify(model_schema.dump(resource)), HTTPStatus.OK
    except ResourceNotFoundError:
        return jsonify({"error": "Resource not found"}), HTTPStatus.NOT_FOUND
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@blueprint.route("/<int:resource_id>", methods=["DELETE"])
def delete_resource(resource_id: int):
    """
    Delete a resource.
    ---
    tags:
      - Resources
    parameters:
      - name: resource_id
        in: path
        type: integer
        required: true
        description: ID of the resource
    responses:
      204:
        description: Resource deleted
      404:
        description: Resource not found
    """
    try:
        ModelService.delete(resource_id)
        return "", HTTPStatus.NO_CONTENT
    except ResourceNotFoundError:
        return jsonify({"error": "Resource not found"}), HTTPStatus.NOT_FOUND
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR 