"""Storage interfaces. Firestore is a drop-in durable option; memory is offline-only."""
from __future__ import annotations
import copy, threading
from .config import is_cloud

class MemoryRepository:
    def __init__(self):
        self.lock=threading.RLock()
        self.cases={}
        self.actions={}
        self.proposals={}
        self.precedents={}
    def reset(self):
        with self.lock:
            self.cases.clear();self.actions.clear();self.proposals.clear();self.precedents.clear()
    def get_case(self, case_id):
        with self.lock: return copy.deepcopy(self.cases.get(case_id))
    def save_case(self, record):
        with self.lock:
            self.cases[record['case_id']]=copy.deepcopy(record)
        return record
    def create_case_if_absent(self, record):
        with self.lock:
            if record['case_id'] in self.cases:
                return False
            self.cases[record['case_id']]=copy.deepcopy(record)
            return True
    def list_cases(self):
        with self.lock: return sorted(copy.deepcopy(list(self.cases.values())),key=lambda x:x['case_id'])
    def create_action(self,key,action):
        with self.lock:
            if key in self.actions: return copy.deepcopy(self.actions[key]),False
            self.actions[key]=copy.deepcopy(action)
            return copy.deepcopy(action),True
    def get_action(self,key):
        with self.lock:return copy.deepcopy(self.actions.get(key))
    def save_action(self,key,action):
        with self.lock:self.actions[key]=copy.deepcopy(action)
    def save_proposal(self,p):
        with self.lock:self.proposals[p['proposal_id']]=copy.deepcopy(p)
    def get_proposal(self,pid):
        with self.lock:return copy.deepcopy(self.proposals.get(pid))
    def list_proposals(self):
        with self.lock:return copy.deepcopy(list(self.proposals.values()))
    def save_precedent(self,p):
        with self.lock:self.precedents[p['precedent_id']]=copy.deepcopy(p)
    def list_precedents(self):
        with self.lock:return copy.deepcopy(list(self.precedents.values()))
    def get_precedent(self,pid):
        with self.lock:return copy.deepcopy(self.precedents.get(pid))

class FirestoreRepository:
    def __init__(self):
        from google.cloud import firestore
        self.db=firestore.Client()
    def get_case(self,case_id):
        item=self.db.collection('cases').document(case_id).get()
        return item.to_dict() if item.exists else None
    def save_case(self,record):
        self.db.collection('cases').document(record['case_id']).set(record)
        return record
    def create_case_if_absent(self, record):
        from google.api_core.exceptions import AlreadyExists
        try:
            self.db.collection('cases').document(record['case_id']).create(record)
            return True
        except AlreadyExists:
            return False
    def list_cases(self):
        return [x.to_dict() for x in self.db.collection('cases').stream()]
    def create_action(self,key,action):
        from google.api_core.exceptions import Conflict, AlreadyExists
        ref=self.db.collection('actions').document(key)
        try:
            ref.create(action)  # Firestore create precondition ensures at-most-once record
            return action,True
        except (Conflict,AlreadyExists):
            return ref.get().to_dict(),False
    def get_action(self,key):
        doc=self.db.collection('actions').document(key).get()
        return doc.to_dict() if doc.exists else None
    def save_action(self,key,action):
        self.db.collection('actions').document(key).set(action)
    def save_proposal(self,p):
        self.db.collection('learning_proposals').document(p['proposal_id']).set(p)
    def get_proposal(self,pid):
        doc=self.db.collection('learning_proposals').document(pid).get()
        return doc.to_dict() if doc.exists else None
    def list_proposals(self):
        return [x.to_dict() for x in self.db.collection('learning_proposals').stream()]
    def save_precedent(self,p):
        self.db.collection('approved_precedents').document(p['precedent_id']).set(p)
    def list_precedents(self):
        return [x.to_dict() for x in self.db.collection('approved_precedents').stream()]
    def get_precedent(self,pid):
        doc=self.db.collection('approved_precedents').document(pid).get()
        return doc.to_dict() if doc.exists else None

_instance=None

def repo():
    global _instance
    if _instance is None:
        _instance=FirestoreRepository() if is_cloud() else MemoryRepository()
    return _instance

def set_repo(value):
    global _instance
    _instance=value
