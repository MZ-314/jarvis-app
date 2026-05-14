# backend/app/blueprints/ai/routes.py

import logging
import asyncio
from flask import request, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.blueprints.ai import ai_bp
from app.services.agent_orchestrator import agent_orchestrator, TurnContext
from app.models.conversation import Conversation
from app.models.message import Message
from app.extensions import db

logger = logging.getLogger(__name__)


def _get_or_create_conversation(user_id: str, conversation_id: str | None, title: str | None = None) -> Conversation:
    if conversation_id:
        conv = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
        if conv:
            return conv
    conv = Conversation(user_id=user_id, title=title or "New Conversation")
    db.session.add(conv)
    db.session.flush()
    return conv


@ai_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")
    history = data.get("history", [])
    store_memory = data.get("store_memory", False)
    title = data.get("title")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    if len(user_message) > 8000:
        return jsonify({"error": "Message too long"}), 400

    context = TurnContext(
        user_id=str(user_id),
        conversation_id=conversation_id,
        history=history,
        is_voice=False,
        fast_mode=False,
    )

    try:
        conv = _get_or_create_conversation(str(user_id), conversation_id, title)
        conversation_id = str(conv.id)
        context.conversation_id = conversation_id

        response_text = asyncio.run(agent_orchestrator.process_turn(
            context=context,
            user_message=user_message,
            store_memory=store_memory,
        ))

        user_msg = Message(conversation_id=conversation_id, user_id=user_id, role="user", content=user_message)
        assistant_msg = Message(conversation_id=conversation_id, user_id=user_id, role="assistant", content=response_text)
        db.session.add_all([user_msg, assistant_msg])
        db.session.commit()

        return jsonify({
            "response": response_text,
            "conversation_id": conversation_id,
        }), 200

    except Exception as e:
        logger.exception("Chat failed")
        db.session.rollback()
        return jsonify({"error": "Chat failed"}), 500


@ai_bp.route("/chat/stream", methods=["POST"])
@jwt_required()
def chat_stream():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")
    history = data.get("history", [])
    title = data.get("title")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    context = TurnContext(
        user_id=str(user_id),
        conversation_id=conversation_id,
        history=history,
        is_voice=False,
        fast_mode=False,
    )

    try:
        conv = _get_or_create_conversation(str(user_id), conversation_id, title)
        conversation_id = str(conv.id)
        context.conversation_id = conversation_id
        db.session.commit()

        def generate():
            full_response = []
            loop = asyncio.new_event_loop()
            try:
                agen = agent_orchestrator.stream_response(context, user_message)
                while True:
                    try:
                        chunk = loop.run_until_complete(agen.__anext__())
                        full_response.append(chunk)
                        yield f"data: {chunk}\n\n"
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()

            response_text = "".join(full_response)
            user_msg = Message(conversation_id=conversation_id, user_id=user_id, role="user", content=user_message)
            assistant_msg = Message(conversation_id=conversation_id, user_id=user_id, role="assistant", content=response_text)
            db.session.add_all([user_msg, assistant_msg])
            db.session.commit()
            yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Conversation-ID": conversation_id,
            },
        )

    except Exception as e:
        logger.exception("Stream chat failed")
        return jsonify({"error": "Stream failed"}), 500


@ai_bp.route("/conversations", methods=["GET"])
@jwt_required()
def list_conversations():
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 50)

    paginated = (
        Conversation.query
        .filter_by(user_id=user_id, is_deleted=False)
        .order_by(Conversation.updated_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "conversations": [c.to_dict() for c in paginated.items],
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
    }), 200


@ai_bp.route("/conversations/<conversation_id>", methods=["GET"])
@jwt_required()
def get_conversation(conversation_id: str):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conversation_id, user_id=user_id, is_deleted=False).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    messages = (
        Message.query
        .filter_by(conversation_id=conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return jsonify({
        "conversation": conv.to_dict(),
        "messages": [m.to_dict() for m in messages],
    }), 200


@ai_bp.route("/conversations/<conversation_id>", methods=["DELETE"])
@jwt_required()
def delete_conversation(conversation_id: str):
    user_id = get_jwt_identity()
    conv = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404

    conv.is_deleted = True
    db.session.commit()
    return jsonify({"message": "Conversation deleted"}), 200