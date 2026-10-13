import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app
from app.schemas import Question, Rubric, Evaluation, Architecture, DesignRubric, DesignEvaluation

class FakeCoach:
    def __init__(self):
        self.histories = []
        self.review_targets = []

    def question(self, role, track, difficulty, history):
        self.histories.append(history)
        focus = 'Caching' if history else 'API design'
        return Question(question=f'How would you improve {focus} in a {track} service?', focus=focus)

    def evaluate(self, question, answer, track):
        return Evaluation(
            rubric=Rubric(accuracy=8, reasoning=7, tradeoffs=6, clarity=9),
            strengths=['Identified a valid approach'],
            improvements=['Discuss failure handling'],
            weak_spots=['caching'], feedback='Good initial answer, but explain how failures are handled.'
        )

    def architecture(self, prompt):
        return Architecture(
            summary='Distributed content service with stateless APIs and storage.',
            services=['API service', 'worker'], databases=['Postgres'], caching=['Redis'],
            apis=['GET /content'], scaling_strategy='Scale the stateless API fleet horizontally.',
            tradeoffs=['Strong consistency costs latency'], assumptions=['One million users'],
            diagram='flowchart TD\n User-->API\n API-->DB'
        )

    def design_review(self, prompt, target):
        self.review_targets.append(target)
        return DesignEvaluation(
            rubric=DesignRubric(scalability=7,reliability=6,tradeoffs=8,clarity=9),
            strengths=['Has components'], risks=['Single database'], improvements=['Add failover'],
            feedback='The proposed design would benefit from a failover strategy.'
        )

@pytest.fixture
def context(tmp_path):
    coach = FakeCoach()
    path = str(tmp_path/'db.sqlite')
    app = create_app(database_path=path, coach=coach)
    with TestClient(app) as client:
        yield client, coach, path
