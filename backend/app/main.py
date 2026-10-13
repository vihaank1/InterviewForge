"""InterviewForge HTTP application."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .database import Database
from .ai import OpenAICoach
from .schemas import StartSession, SubmitAnswer, DesignRequest
from .scoring import interview_score, design_score, missing_component_hints, progress_summary

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def now():
    return datetime.now(timezone.utc).isoformat()


def create_app(database_path=None, coach=None):
    app = FastAPI(title='InterviewForge API', version='1.0.0',
                  description='Uncalibrated AI interview practice; no hiring predictions.')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type'],
    )
    db_path = database_path or os.getenv('INTERVIEW_DB_PATH') or str(Path(__file__).resolve().parents[1] / 'data' / 'interviewforge.db')
    app.state.db = Database(db_path)
    app.state.coach = coach if coach is not None else OpenAICoach()

    def session_payload(session_id):
        with app.state.db.connect() as conn:
            row = conn.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
            if not row:
                raise HTTPException(404, detail='Session not found')
            records = conn.execute('SELECT * FROM rounds WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
        history = [{
            'question': r['question'], 'answer': r['answer'], 'focus': r['focus'],
            'score': r['score'], 'evaluation': json.loads(r['evaluation_json']),
            'created_at': r['created_at']
        } for r in records]
        return {
            'id': row['id'], 'role': row['role'], 'track': row['track'],
            'difficulty': row['difficulty'], 'status': row['status'],
            'question': row['current_question'], 'focus': row['current_focus'],
            'round': len(history) + 1, 'history': history,
            'progress': progress_summary(history), 'created_at': row['created_at']
        }

    @app.get('/api/health')
    def health():
        return {'ok': True, 'service': 'interviewforge'}

    @app.post('/api/sessions', status_code=201)
    def start_session(req: StartSession):
        question = app.state.coach.question(req.role, req.track, req.difficulty, [])
        sid = str(uuid.uuid4())
        with app.state.db.connect() as conn:
            conn.execute('INSERT INTO sessions (id,role,track,difficulty,current_question,current_focus,status,version,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                (sid, req.role, req.track, req.difficulty, question.question, question.focus, 'active', 0, now()))
            conn.commit()
        return session_payload(sid)

    @app.get('/api/sessions/{sid}')
    def get_session(sid: str):
        return session_payload(sid)

    @app.post('/api/sessions/{sid}/answers')
    def submit_answer(sid: str, req: SubmitAnswer):
        snapshot = session_payload(sid)
        if snapshot['status'] != 'active':
            raise HTTPException(409, detail='Session is already completed')
        evaluation = app.state.coach.evaluate(snapshot['question'], req.answer, snapshot['track'])
        score = interview_score(evaluation)
        history_for_model = [
            {'question': turn['question'], 'answer': turn['answer'],
             'weak_spots': turn['evaluation'].get('weak_spots', []), 'score': turn['score']}
            for turn in snapshot['history'][-3:]
        ] + [{'question': snapshot['question'], 'answer': req.answer,
              'weak_spots': evaluation.weak_spots, 'score': score}]
        next_question = app.state.coach.question(snapshot['role'], snapshot['track'], snapshot['difficulty'], history_for_model)
        with app.state.db.connect() as conn:
            with conn:
                updated = conn.execute('UPDATE sessions SET current_question=?,current_focus=?,version=version+1 '
                    'WHERE id=? AND current_question=? AND status=? AND version=?',
                    (next_question.question, next_question.focus, sid, snapshot['question'], 'active', len(snapshot['history']))).rowcount
                if updated != 1:
                    raise HTTPException(409, detail='Session changed; reload before submitting again')
                conn.execute('INSERT INTO rounds (session_id,question,answer,focus,score,evaluation_json,created_at) VALUES (?,?,?,?,?,?,?)',
                    (sid, snapshot['question'], req.answer, snapshot['focus'], score, evaluation.model_dump_json(), now()))
        return session_payload(sid)

    @app.post('/api/sessions/{sid}/complete')
    def complete_session(sid: str):
        with app.state.db.connect() as conn:
            row = conn.execute('UPDATE sessions SET status=? WHERE id=?', ('completed', sid))
            if row.rowcount == 0:
                raise HTTPException(404, detail='Session not found')
            conn.commit()
        return session_payload(sid)

    def load_design(did):
        with app.state.db.connect() as conn:
            row = conn.execute('SELECT * FROM designs WHERE id=?', (did,)).fetchone()
        if row is None:
            raise HTTPException(404, detail='Design not found')
        return {
            'id': row['id'], 'prompt': row['prompt'], 'candidate_design': row['candidate_design'],
            'architecture': json.loads(row['architecture_json']),
            'review': json.loads(row['review_json']) if row['review_json'] else None,
            'score': row['score'], 'hints': json.loads(row['hints_json']) if row['hints_json'] else [],
            'review_target': 'candidate' if row['candidate_design'] else 'generated reference',
            'created_at': row['created_at']
        }

    @app.post('/api/designs', status_code=201)
    def generate_design(req: DesignRequest):
        architecture = app.state.coach.architecture(req.prompt)
        did = str(uuid.uuid4())
        with app.state.db.connect() as conn:
            conn.execute('INSERT INTO designs (id,prompt,candidate_design,architecture_json,created_at) VALUES (?,?,?,?,?)',
                (did, req.prompt, req.candidate_design, architecture.model_dump_json(), now()))
            conn.commit()
        return load_design(did)

    @app.get('/api/designs/{did}')
    def get_design(did: str):
        return load_design(did)

    @app.post('/api/designs/{did}/review')
    def review_design(did: str):
        design = load_design(did)
        candidate = design['candidate_design']
        target = candidate if candidate and candidate.strip() else json.dumps(design['architecture'])
        review = app.state.coach.design_review(design['prompt'], target)
        score = design_score(review)
        hints = missing_component_hints(target)
        with app.state.db.connect() as conn:
            conn.execute('UPDATE designs SET review_json=?, score=?, hints_json=? WHERE id=?',
                (review.model_dump_json(), score, json.dumps(hints), did))
            conn.commit()
        return load_design(did)

    return app

app = create_app()
