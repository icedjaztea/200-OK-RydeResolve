"""Local demo media or private Cloud Storage. Never claim EXIF proves camera origin."""
from __future__ import annotations
import hashlib,io,os,pathlib
from .config import ROOT,is_cloud,setting

ALLOWED_TYPES={'image/png':'.png','image/jpeg':'.jpg','application/pdf':'.pdf'}
MAX_BYTES=5*1024*1024

def store_blob(case_id:str,filename:str,content_type:str,data:bytes)->dict:
    if content_type not in ALLOWED_TYPES:raise ValueError('Only PNG, JPEG or PDF accepted')
    if not data or len(data)>MAX_BYTES:raise ValueError('File size must be 1 byte to 5 MB')
    is_valid={'image/png':lambda x:x.startswith(b'\x89PNG\r\n\x1a\n'),
              'image/jpeg':lambda x:x.startswith(b'\xff\xd8\xff'),
              'application/pdf':lambda x:x.startswith(b'%PDF-')}
    if not is_valid[content_type](data):raise ValueError('File signature does not match stated MIME type')
    sha=hashlib.sha256(data).hexdigest();obj=f"cases/{case_id}/{sha[:24]}{ALLOWED_TYPES[content_type]}"
    if is_cloud():
        from google.cloud import storage
        bucket=setting('GCS_BUCKET')
        if not bucket:raise ValueError('GCS_BUCKET not configured')
        blob=storage.Client().bucket(bucket).blob(obj)
        if not blob.exists():
            blob.upload_from_file(io.BytesIO(data),content_type=content_type,if_generation_match=0)
        uri=f'gs://{bucket}/{obj}'
    else:
        p=ROOT/'uploads'/obj;p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(data)
        uri=f'local://{obj}'
    return {'object_ref':uri,'sha256':sha,'size_bytes':len(data),'content_type':content_type,
            'origin_verified':False,'authenticity_verified':False,
            'note':'Image pixels/EXIF alone cannot validate trusted in-app camera provenance'}
