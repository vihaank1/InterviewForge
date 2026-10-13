import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas import Rubric, Evaluation
from app.scoring import interview_score, missing_component_hints


def test_health_and_validation(context):
    client, _, _ = context
    assert client.get('/api/health').json()['ok'] is True
    assert client.post('/api/sessions', json={'role':'x','track':'fake'}).status_code == 422
    assert client.post('/api/designs', json={'prompt':'short'}).status_code == 422
    assert client.get('/api/sessions/no-such-id').status_code == 404


def test_round_context_and_progress(context):
    client, coach, _ = context
    start = client.post('/api/sessions', json={'role':'Backend Engineer','track':'backend','difficulty':'Medium'})
    assert start.status_code == 201
    sid = start.json()['id']
    assert start.json()['round'] == 1
    result = client.post(f'/api/sessions/{sid}/answers', json={'answer':'I would add an API gateway and cache.'})
    assert result.status_code == 200
    body = result.json()
    assert body['round'] == 2
    assert body['question'] != start.json()['question']
    assert body['progress']['completed_rounds'] == 1
    assert body['progress']['average_score'] == 7.5
    assert body['progress']['weak_spots'] == ['caching']
    assert coach.histories[0] == []
    assert len(coach.histories[1]) == 1
    assert coach.histories[1][0]['weak_spots'] == ['caching']
    assert len(body['history']) == 1
    assert body['history'][0]['score'] == 7.5


def test_sqlite_persists_across_app_recreation(context):
    client, coach, path = context
    sid = client.post('/api/sessions', json={'role':'Software Engineer','track':'frontend'}).json()['id']
    client.post(f'/api/sessions/{sid}/answers', json={'answer':'Use component state and consider retries.'})
    with TestClient(create_app(database_path=path, coach=coach)) as second_client:
        session = second_client.get(f'/api/sessions/{sid}').json()
    assert session['round'] == 2
    assert session['history'][0]['answer'] == 'Use component state and consider retries.'


def test_completed_session_and_errors(context):
    client, _, _ = context
    sid = client.post('/api/sessions', json={'role':'Engineer'}).json()['id']
    assert client.post(f'/api/sessions/{sid}/complete').json()['status'] == 'completed'
    assert client.post(f'/api/sessions/{sid}/answers', json={'answer':'My valid response'}).status_code == 409
    assert client.post('/api/sessions/missing/complete').status_code == 404
    assert client.post(f'/api/sessions/{sid}/answers', json={'answer':'no'}).status_code == 422


def test_design_candidate_vs_reference(context):
    client, coach, _ = context
    req = {'prompt':'Design a feed service handling regional traffic',
           'candidate_design':'One API service and a SQL database. No caching or replication.'}
    response = client.post('/api/designs', json=req)
    assert response.status_code == 201
    did = response.json()['id']
    evaluated = client.post(f'/api/designs/{did}/review')
    assert evaluated.status_code == 200
    data = evaluated.json()
    assert data['review_target'] == 'candidate'
    assert data['score'] == 7.3
    assert len(data['hints']) >= 1
    assert coach.review_targets[-1] == req['candidate_design']
    assert client.get(f'/api/designs/{did}').json()['review'] is not None
    assert client.get('/api/designs/unknown').status_code == 404


def test_scores_and_heuristics_are_explicit():
    e = Evaluation(rubric=Rubric(accuracy=8, reasoning=7, tradeoffs=6, clarity=9),
        strengths=['Correct'], improvements=['Provide evidence'], weak_spots=[], feedback='Useful feedback for this response.')
    assert interview_score(e) == 7.5
    assert 'CDN not mentioned' in missing_component_hints('Redis, replication, queue, load balancer')
    assert missing_component_hints('cache load balancer replication CDN queue') == []


def test_scoring_boundaries_and_candidate_normalization(context):
    from pydantic import ValidationError
    from app.schemas import DesignRequest, Rubric, Architecture
    client, coach, _ = context
    with pytest.raises(ValidationError):
        Rubric(accuracy=11, reasoning=7, tradeoffs=6, clarity=9)
    with pytest.raises(ValidationError):
        Architecture(
            summary='Reference', services=['API'], databases=[], caching=[], apis=[],
            scaling_strategy='horizontal', tradeoffs=['latency'], assumptions=['users'],
            diagram='invalid diagram syntax'
        )
    assert DesignRequest(prompt='Design a content delivery network', candidate_design='    ').candidate_design is None
    result = client.post('/api/designs', json={'prompt': 'Design a content delivery network', 'candidate_design': '   '})
    assert result.status_code == 201
    did = result.json()['id']
    result = client.post(f'/api/designs/{did}/review')
    assert result.status_code == 200
    assert result.json()['review_target'] == 'generated reference'
    assert 'summary' in coach.review_targets[-1]


def test_two_completed_rounds_are_preserved(context):
    client, coach, _ = context
    sid = client.post('/api/sessions', json={'role':'ML Engineer','track':'ml'}).json()['id']
    for answer in ['I would analyze the training data and choose a baseline.',
                   'I would check the validation loss, leakage and feature distributions.']:
        outcome = client.post(f'/api/sessions/{sid}/answers', json={'answer':answer})
        assert outcome.status_code == 200
    data = client.get(f'/api/sessions/{sid}').json()
    assert len(data['history']) == 2
    assert data['round'] == 3
    assert len(coach.histories[-1]) == 2
    assert data['progress']['completed_rounds'] == 2
