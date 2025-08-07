import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    """Test the index page."""
    rv = client.get('/')
    assert rv.status_code == 200

def test_start_chat(client):
    """Test the start chat endpoint."""
    rv = client.post('/start')
    assert rv.status_code == 200
    json_data = rv.get_json()
    assert 'session_id' in json_data
    assert 'responses' in json_data

def test_chat_invalid_session(client):
    """Test the chat endpoint with an invalid session ID."""
    rv = client.post('/chat', json={'session_id': 'invalid', 'message': 'hello'})
    assert rv.status_code == 400
    json_data = rv.get_json()
    assert 'error' in json_data
    assert json_data['error'] == 'Invalid session ID.'
