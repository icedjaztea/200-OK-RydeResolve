import json
from pathlib import Path
import pytest
from app import policy
from app.repository import MemoryRepository,set_repo

@pytest.fixture(autouse=True)
def empty_memory_repo(monkeypatch,tmp_path):
    monkeypatch.setenv('APP_MODE','memory')
    monkeypatch.setenv('AI_MODE','mock')
    set_repo(MemoryRepository())
    # Synthetic demo contract signoff for tests ONLY; production file must be reviewed separately.
    actual=policy.contract_report()
    path=tmp_path/'team_signoff.json'
    path.write_text(json.dumps({
      'team_review_acknowledged':True,'reviewer':'TEST_ONLY',
      'source_sha256':actual['source_sha256'],
      'policy_version':'2.1','rulebook_version':policy.load_rulebook()['version']
    }))
    monkeypatch.setattr(policy,'signoff_path',lambda:path)
    yield
