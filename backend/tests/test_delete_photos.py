from uuid import uuid4
from fastapi.testclient import TestClient
from psycopg import OperationalError
from app.main import app
from app.db.connection import connect
from app.api import router as routes
from test_workflow import isolated_database, worker
from test_pallet_orders import new_trip, photo


def setup_pallet(client, trip_id):
    payload={'id':str(uuid4()),'store_code':'1001','orders':['ORDER-DELETE']}
    assert client.post(f'/api/trips/{trip_id}/pallets',json=payload).status_code==200
    return payload['id']


def test_delete_photo_authorization_retries_and_completion_rules():
    client=worker();trip,_=new_trip(client);other,_=new_trip(client)
    tid=trip['id'];pallet=setup_pallet(client,tid);second=setup_pallet(client,tid)
    other_pallet=setup_pallet(client,other['id'])
    pid=photo(client,tid,pallet).json()['id']
    path=f'/api/trips/{tid}/pallets/{pallet}/photos/{pid}'
    assert TestClient(app).delete(path).status_code==401
    assert worker().delete(path).status_code==404
    assert client.delete(f'/api/trips/{tid}/pallets/{second}/photos/{pid}').status_code==404
    assert client.delete(f'/api/trips/{other["id"]}/pallets/{other_pallet}/photos/{pid}').status_code==404
    result=client.delete(path)
    assert result.status_code==200,result.text
    assert result.json()['photos']==[] and result.json()['pallets'][0]['photos']==[]
    assert client.get(f'/api/photos/{pid}').status_code==404
    with connect(True) as images:
        assert not images.execute('SELECT 1 FROM photo_blobs WHERE id=%s',(pid,)).fetchone()
    assert client.delete(path).status_code==200
    with connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM audit_log WHERE event='photo.delete' AND target_id=%s",(pid,)).fetchone()['n']==1
        assert conn.execute('SELECT 1 FROM deleted_photos WHERE id=%s',(pid,)).fetchone()
    assert photo(client,tid,pallet,pid).status_code==410
    assert client.post(f'/api/trips/{tid}/complete').status_code==409
    replacement=photo(client,tid,pallet).json()['id']
    assert client.post(f'/api/trips/{tid}/complete').status_code==200
    assert client.delete(f'/api/trips/{tid}/pallets/{pallet}/photos/{replacement}').status_code==409


def test_cancelled_trip_cannot_delete_photos():
    client=worker();trip,_=new_trip(client);tid=trip['id'];pallet=setup_pallet(client,tid)
    pid=photo(client,tid,pallet).json()['id']
    assert client.post('/api/admin/login',json={'username':'admin','password':' test-password-123 '}).status_code==200
    assert client.post(f'/api/admin/trips/{tid}/cancel').status_code==200
    assert client.delete(f'/api/trips/{tid}/pallets/{pallet}/photos/{pid}').status_code==409
    assert len(client.get(f'/api/trips/{tid}').json()['photos'])==1


def test_image_cleanup_failure_can_be_retried_without_restoring_photo(monkeypatch):
    client=worker();trip,_=new_trip(client);tid=trip['id'];pallet=setup_pallet(client,tid)
    pid=photo(client,tid,pallet).json()['id']
    path=f'/api/trips/{tid}/pallets/{pallet}/photos/{pid}'
    original=routes.connect
    def unavailable(images=False):
        if images:raise OperationalError('Test image database outage')
        return original()
    monkeypatch.setattr(routes,'connect',unavailable)
    assert client.delete(path).status_code==200
    assert client.get(f'/api/trips/{tid}').json()['photos']==[]
    monkeypatch.setattr(routes,'connect',original)
    assert client.delete(path).status_code==200
    with connect(True) as images:
        assert not images.execute('SELECT 1 FROM photo_blobs WHERE id=%s',(pid,)).fetchone()


def test_business_transaction_failure_keeps_the_original_image(monkeypatch):
    client=worker();trip,_=new_trip(client);tid=trip['id'];pallet=setup_pallet(client,tid)
    pid=photo(client,tid,pallet).json()['id']
    def failed_audit(*args):raise OperationalError('Test business write failure')
    monkeypatch.setattr(routes,'audit',failed_audit)
    assert client.delete(f'/api/trips/{tid}/pallets/{pallet}/photos/{pid}').status_code==503
    assert client.get(f'/api/photos/{pid}').status_code==200
    with connect() as conn:
        assert not conn.execute('SELECT 1 FROM deleted_photos WHERE id=%s',(pid,)).fetchone()
