# backend/app/sockets.py

import logging
import asyncio
import threading
from flask_socketio import emit, disconnect
from flask_jwt_extended import decode_token
from flask import request

from app.extensions import socketio, db
from app.services.groq_service import groq_service
from app.services.memory_service import memory_service
from app.services.agent_orchestrator import agent_orchestrator, TurnContext
from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)

# One persistent event loop running in a background thread
_loop = asyncio.new_event_loop()
_loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_loop_thread.start()

# Store active Deepgram connections per socket
_dg_connections = {}


def run_async(coro):
    """Schedule a coroutine on the persistent loop and wait for result."""
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=30)


def _get_user_from_token(token: str):
    try:
        decoded = decode_token(token)
        return decoded["sub"]
    except Exception:
        return None


@socketio.on("connect")
def on_connect():
    token = request.args.get("token")
    if not token:
        disconnect()
        return
    user_id = _get_user_from_token(token)
    if not user_id:
        disconnect()
        return
    logger.info(f"Socket connected: {request.sid} user={user_id}")


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    if sid in _dg_connections:
        conn = _dg_connections.pop(sid)
        try:
            run_async(conn.finish())
        except Exception:
            pass
    logger.info(f"Socket disconnected: {sid}")


@socketio.on("voice.start")
def on_voice_start(data):
    token = request.args.get("token")
    user_id = _get_user_from_token(token)
    if not user_id:
        disconnect()
        return

    sid = request.sid
    conversation_id = data.get("conversation_id")

    async def _start():
        from app.services.deepgram_service import deepgram_service

        conn = deepgram_service.create_live_connection()
        _dg_connections[sid] = conn
        options = deepgram_service.get_live_options()

        async def on_message(self, result, **kwargs):
            try:
                transcript = result.channel.alternatives[0].transcript
                is_final = result.speech_final
                if transcript:
                    socketio.emit("voice.transcript", {
                        "transcript": transcript,
                        "is_final": is_final,
                    }, to=sid)

                if is_final and transcript.strip():
                    await _handle_final_transcript(
                        sid=sid,
                        user_id=user_id,
                        transcript=transcript.strip(),
                        conversation_id=conversation_id,
                    )
            except Exception as e:
                logger.error(f"Transcript error: {e}")

        async def on_error(self, error, **kwargs):
            logger.error(f"Deepgram error: {error}")
            socketio.emit("voice.error", {"error": str(error)}, to=sid)

        conn.on(deepgram_service.LiveTranscriptionEvents.Transcript, on_message)
        conn.on(deepgram_service.LiveTranscriptionEvents.Error, on_error)

        await conn.start(options)
        socketio.emit("voice.ready", {}, to=sid)

    try:
        run_async(_start())
    except Exception as e:
        logger.error(f"voice.start error: {e}")
        emit("voice.error", {"error": "Failed to start voice session"})


@socketio.on("voice.audio")
def on_voice_audio(data):
    sid = request.sid
    conn = _dg_connections.get(sid)
    if conn:
        try:
            run_async(conn.send(data))
        except Exception as e:
            logger.error(f"voice.audio send error: {e}")


@socketio.on("voice.stop")
def on_voice_stop():
    sid = request.sid
    conn = _dg_connections.pop(sid, None)
    if conn:
        try:
            run_async(conn.finish())
        except Exception:
            pass


async def _handle_final_transcript(sid, user_id, transcript, conversation_id):
    try:
        from app import create_app
        from app.extensions import db

        if conversation_id:
            conv = Conversation.query.filter_by(
                id=conversation_id, user_id=user_id
            ).first()
        else:
            conv = None

        if not conv:
            conv = Conversation(
                user_id=user_id,
                title="Voice Conversation",
                mode="voice",
            )
            db.session.add(conv)
            db.session.flush()
            db.session.commit()

        conversation_id = str(conv.id)

        socketio.emit("voice.conversation_id", {
            "conversation_id": conversation_id
        }, to=sid)

        context = TurnContext(
            user_id=str(user_id),
            conversation_id=conversation_id,
            history=[],
            is_voice=True,
            fast_mode=True,
        )

        response_text = await agent_orchestrator.process_turn(
            context=context,
            user_message=transcript,
            store_memory=False,
        )

        socketio.emit("voice.response", {
            "response": response_text,
            "conversation_id": conversation_id,
        }, to=sid)

        user_msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=transcript,
        )
        assistant_msg = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=response_text,
        )
        db.session.add_all([user_msg, assistant_msg])
        db.session.commit()

    except Exception as e:
        logger.error(f"Handle transcript error: {e}")
        socketio.emit("voice.error", {"error": "AI response failed"}, to=sid)