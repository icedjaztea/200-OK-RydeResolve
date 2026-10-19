from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
from fastapi.testclient import TestClient
from google.api_core.exceptions import AlreadyExists
from app.main import app
from app.repository import FirestoreRepository, repo
from app.services import seed_cases
from app.identity import seed_case_owners


def test_startup_seeds_all_portals_and_preserves_results():
    with TestClient(app) as client:
        cases=client.get('/cases').json()
        assert len(cases)==12
        for role in ('rider_a','rider_b','driver_a','driver_b'):
            index=0 if role.startswith('rider') else 1
            expected={c['case_id'] for c in cases
                      if seed_case_owners(c['case_id'],c.get('filed_by'))[index]==role}
            response=client.get('/cases',headers={'X-Demo-Key':role})
            assert {c['case_id'] for c in response.json()}==expected
        assert len(client.get('/monitor').json()['cases'])==12
        saved=repo().get_case(cases[0]['case_id'])
        saved.update(status='RESOLVED',candidate={'preserve':'processed result'})
        repo().save_case(saved)
        assert client.post('/cases/seed').json()=={'created':0}
    with TestClient(app):
        assert repo().get_case(saved['case_id'])==saved
        assert len(repo().list_cases())==12


def test_concurrent_seeding_creates_once():
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts=list(pool.map(lambda _:seed_cases(),range(4)))
    assert sum(counts)==12
    assert len(repo().list_cases())==12


def test_firestore_seed_uses_create_precondition():
    repository=FirestoreRepository.__new__(FirestoreRepository)
    repository.db=Mock()
    document=repository.db.collection.return_value.document.return_value
    record={'case_id':'existing','status':'NEW'}
    assert repository.create_case_if_absent(record) is True
    document.create.assert_called_once_with(record)
    document.create.side_effect=AlreadyExists('existing')
    assert repository.create_case_if_absent(record) is False
    document.set.assert_not_called()
