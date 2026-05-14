# backend/app/blueprints/memory/routes.py

import logging
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.blueprints.memory import memory_bp
from app.services.memory_service import memory_service
from app.models.memory import Memory
from app.extensions import db

logger = logging.getLogger(__name__)


@memory_bp.route("/", methods=["GET"])
@jwt_required()
def list_memories():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    paginated = (
        Memory.query
        .filter_by(user_id=user_id)
        .order_by(Memory.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "memories": [m.to_dict() for m in paginated.items],
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
    }), 200


@memory_bp.route("/search", methods=["POST"])
@jwt_required()
async def search_memories():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    top_k = min(data.get("top_k", 5), 20)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        results = await memory_service.recall(
            user_id=str(user_id),
            query=query,
            top_k=top_k,
        )
        return jsonify({"results": results}), 200
    except Exception as e:
        logger.exception("Memory search failed")
        return jsonify({"error": "Memory search failed"}), 500


@memory_bp.route("/extract", methods=["POST"])
@jwt_required()
async def extract_memory():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    conversation_id = data.get("conversation_id")

    if not text:
        return jsonify({"error": "No text provided"}), 400
    if len(text) > 4000:
        return jsonify({"error": "Text too long (max 4000 chars)"}), 400

    try:
        stored_ids = await memory_service.extract_and_store(
            user_id=str(user_id),
            text=text,
            conversation_id=conversation_id,
        )
        return jsonify({"stored": len(stored_ids), "ids": stored_ids}), 201
    except Exception as e:
        logger.exception("Memory extraction failed")
        return jsonify({"error": "Memory extraction failed"}), 500


@memory_bp.route("/<memory_id>", methods=["GET"])
@jwt_required()
def get_memory(memory_id: str):
    user_id = get_jwt_identity()
    memory = Memory.query.filter_by(id=memory_id, user_id=user_id).first()
    if not memory:
        return jsonify({"error": "Memory not found"}), 404
    return jsonify({"memory": memory.to_dict()}), 200


@memory_bp.route("/<memory_id>", methods=["DELETE"])
@jwt_required()
async def delete_memory(memory_id: str):
    user_id = get_jwt_identity()

    try:
        deleted = await memory_service.forget(
            user_id=str(user_id),
            memory_id=memory_id,
        )
        if not deleted:
            return jsonify({"error": "Memory not found"}), 404
        return jsonify({"message": "Memory deleted"}), 200
    except Exception as e:
        logger.exception("Memory deletion failed")
        return jsonify({"error": "Memory deletion failed"}), 500


@memory_bp.route("/", methods=["DELETE"])
@jwt_required()
async def delete_all_memories():
    user_id = get_jwt_identity()

    try:
        await memory_service.forget_all(user_id=str(user_id))
        return jsonify({"message": "All memories deleted"}), 200
    except Exception as e:
        logger.exception("Failed to delete all memories")
        return jsonify({"error": "Failed to delete all memories"}), 500