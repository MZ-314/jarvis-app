# backend/app/blueprints/voice/routes.py

import logging
import uuid
import asyncio
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.blueprints.voice import voice_bp
from app.services.livekit_service import livekit_service
from app.services.deepgram_service import deepgram_service
from app.services.cartesia_service import cartesia_service
from app.services.agent_orchestrator import agent_orchestrator, TurnContext
from app.models.conversation import Conversation
from app.models.message import Message
from app.extensions import db

logger = logging.getLogger(__name__)


@voice_bp.route("/token", methods=["POST"])
@jwt_required()
def get_voice_token():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    room_name = data.get("room_name") or f"room_{user_id}_{uuid.uuid4().hex[:8]}"
    participant_identity = str(user_id)
    participant_name = data.get("display_name", "User")

    try:
        token = livekit_service.create_token(
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=participant_name,
        )
        return jsonify({"token": token, "room_name": room_name, "url": livekit_service.url}), 200
    except Exception as e:
        logger.exception("Failed to create LiveKit token")
        return jsonify({"error": "Could not create voice token"}), 500


@voice_bp.route("/room", methods=["POST"])
@jwt_required()
def create_room():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    room_name = data.get("room_name") or f"room_{user_id}_{uuid.uuid4().hex[:8]}"

    try:
        room = asyncio.run(livekit_service.create_room(room_name=room_name))
        return jsonify(room), 201
    except Exception as e:
        logger.exception("Failed to create LiveKit room")
        return jsonify({"error": "Could not create room"}), 500


@voice_bp.route("/room/<room_name>", methods=["DELETE"])
@jwt_required()
def delete_room(room_name: str):
    try:
        asyncio.run(livekit_service.delete_room(room_name=room_name))
        return jsonify({"message": "Room deleted"}), 200
    except Exception as e:
        logger.exception("Failed to delete LiveKit room")
        return jsonify({"error": "Could not delete room"}), 500


@voice_bp.route("/transcribe", methods=["POST"])
@jwt_required()
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    mimetype = audio_file.mimetype or "audio/wav"

    try:
        transcript = asyncio.run(deepgram_service.transcribe_file(audio_bytes, mimetype))
        return jsonify({"transcript": transcript}), 200
    except Exception as e:
        logger.exception("Transcription failed")
        return jsonify({"error": "Transcription failed"}), 500


@voice_bp.route("/speak", methods=["POST"])
@jwt_required()
def synthesize_speech():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400
    if len(text) > 1000:
        return jsonify({"error": "Text too long (max 1000 chars)"}), 400

    try:
        audio_bytes = asyncio.run(cartesia_service.synthesize(text))
        return current_app.response_class(
            audio_bytes,
            mimetype="audio/pcm",
            headers={"Content-Disposition": "inline; filename=speech.pcm"},
        )
    except Exception as e:
        logger.exception("Speech synthesis failed")
        return jsonify({"error": "Speech synthesis failed"}), 500


@voice_bp.route("/turn", methods=["POST"])
@jwt_required()
def voice_turn():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")
    history = data.get("history", [])
    store_memory = data.get("store_memory", False)

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    context = TurnContext(
        user_id=str(user_id),
        conversation_id=conversation_id,
        history=history,
        is_voice=True,
        fast_mode=True,
    )

    try:
        response_text = asyncio.run(agent_orchestrator.process_turn(
            context=context,
            user_message=user_message,
            store_memory=store_memory,
        ))

        if conversation_id:
            user_msg = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=user_message,
            )
            assistant_msg = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=response_text,
            )
            db.session.add_all([user_msg, assistant_msg])
            db.session.commit()

        audio_bytes = asyncio.run(cartesia_service.synthesize(response_text))

        return current_app.response_class(
            audio_bytes,
            mimetype="audio/pcm",
            headers={
                "X-Transcript": response_text[:500],
                "Content-Disposition": "inline; filename=response.pcm",
            },
        )
    except Exception as e:
        logger.exception("Voice turn failed")
        return jsonify({"error": "Voice turn failed"}), 500