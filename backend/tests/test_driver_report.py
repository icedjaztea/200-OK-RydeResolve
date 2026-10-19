import base64
from fastapi.testclient import TestClient
from app.main import app
from app.repository import repo


def test_driver_report_upload_and_isolation(monkeypatch,tmp_path):
    from app import storage
    monkeypatch.setattr(storage,'ROOT',tmp_path)
    client=TestClient(app)
    driver={'X-Demo-Key':'driver_b'}
    payload={'case_id':'DRIVER-SEAT-STAIN','trip_id':'TRIP-SEAT-STAIN',
             'category':'property_damage','filed_by':'driver',
             'description':'Synthetic seat stain noticed after the trip.',
             'dispute_amount':30,'synthetic':True}
    response=client.post('/cases',headers=driver,json=payload)
    assert response.status_code==200
    case=repo().get_case(payload['case_id'])
    assert case['driver_id']=='driver_b'
    assert case['filed_by']=='driver'
    assert case['status']=='NEW'
    assert case['source_trust']=='UNVERIFIED_USER_REPORT'
    assert case['trip_id']==payload['trip_id']
    assert client.get('/cases',headers=driver).json()[0]['case_id']==payload['case_id']
    for other in ('driver_a','rider_a','rider_b'):
        assert client.get('/cases',headers={'X-Demo-Key':other}).json()==[]
        assert client.get('/cases/'+payload['case_id'],headers={'X-Demo-Key':other}).status_code==404
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1sAAAAASUVORK5CYII=')
    response=client.post('/cases/'+payload['case_id']+'/files',headers=driver,
                         files={'file':('synthetic.png',png,'image/png')})
    assert response.status_code==200,response.text
    detail=client.get('/cases/'+payload['case_id'],headers=driver).json()
    assert len(detail['evidence'])==1
    assert detail['evidence'][0]['verification']=='camera_origin_unverified'
    assert len(client.get('/cases/'+payload['case_id'],headers={'X-Demo-Key':'reviewer'}).json()['evidence'])==1
    assert client.post('/cases/'+payload['case_id']+'/process',headers=driver).status_code==403
