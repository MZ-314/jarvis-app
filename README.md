# Jarvis App

AI-powered voice-first engineering assistant with memory.

## Architecture

- **Backend** — Python / Flask (SocketIO, Celery, PostgreSQL, Qdrant, Groq LLM, Deepgram STT, Cartesia TTS, LiveKit, Redis)
- **Mobile** — React Native / Expo (NativeWind, Zustand, React Query, socket.io)

## Setup

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                            # fill in values
flask db upgrade
python wsgi.py
```

### Mobile
```bash
cd mobile
npm install
npx expo start
```

## Environment Variables

See `backend/.env.example` for the full list of required keys.