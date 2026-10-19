import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repository import repo


@pytest.mark.parametrize('owner',['driver_a','driver_b','rider_a','rider_b'])
@pytest.mark.parametrize('selection',['a','b',None])
def test_linked_case_visibility_and_reply(owner,selection,monkeypatch,tmp_path):
    from app import storage
    monkeypatch.setattr(storage,"ROOT",tmp_path)
    client=TestClient(app)
    role=owner.split('_')[0]
    other='rider' if role=='driver' else 'driver'
    counterpart=f'{other}_{selection}' if selection else None
    payload={'case_id':'LINK-TEST','trip_id':'TRIP-LINK-TEST','category':'property_damage',
             'description':'Synthetic seat stain dispute for counterpart testing.',
             'filed_by':other,'counterparty_id':counterpart,
             'rider_id':'rider_b','driver_id':'driver_b'}
    response=client.post('/cases',headers={'X-Demo-Key':owner},json=payload)
    assert response.status_code==200,response.text
    case=repo().get_case('LINK-TEST')
    assert case[f'{role}_id']==owner
    assert case[f'{other}_id']==counterpart
    assert case['filed_by']==role
    for identity in ('driver_a','driver_b','rider_a','rider_b','reviewer'):
        headers={'X-Demo-Key':identity}
        visible=identity in (owner,counterpart,'reviewer')
        assert bool(client.get('/cases',headers=headers).json())==visible
        assert client.get('/cases/LINK-TEST',headers=headers).status_code==(200 if visible else 404)
    if counterpart:
        attachment=client.post('/cases/LINK-TEST/files',headers={'X-Demo-Key':counterpart},
            files={'file':('counter-evidence.pdf',b'%PDF-1.4 synthetic test evidence','application/pdf')})
        assert attachment.status_code==200,attachment.text
        assert len(client.get('/cases/LINK-TEST',headers={'X-Demo-Key':owner}).json()['evidence'])==1
        response=client.post('/cases/LINK-TEST/clarifications',headers={'X-Demo-Key':'reviewer'},
                             json={'recipient':other,'question':'Please provide your account of the seat stain.'})
        assert response.status_code==200
        detail=client.get('/cases/LINK-TEST',headers={'X-Demo-Key':counterpart}).json()
        request=detail['clarifications'][0]
        reply=client.post(f"/cases/LINK-TEST/clarifications/{request['request_id']}/reply",
                          headers={'X-Demo-Key':counterpart},json={'answer':'The seat was already stained when the trip began.'})
        assert reply.status_code==200,reply.text
        stored=repo().get_case('LINK-TEST')
        assert stored['clarifications'][0]['status']=='ANSWERED'
        assert stored['clarifications'][0]['answer_verification']=='UNVERIFIED_PARTY_ACCOUNT'
        assert not stored.get('mock_action')


@pytest.mark.parametrize('owner,counterpart,status',[
    ('driver_a','driver_b',400),('rider_b','rider_a',400),
    ('driver_a','rider_c',422),('rider_a','reviewer',422),
    ('reviewer','driver_a',400),
])
def test_invalid_counterparty_rejected(owner,counterpart,status):
    response=TestClient(app).post('/cases',headers={'X-Demo-Key':owner},json={
        'case_id':'INVALID-LINK','category':'property_damage','description':'Synthetic test report',
        'counterparty_id':counterpart})
    assert response.status_code==status
    assert repo().get_case('INVALID-LINK') is None
