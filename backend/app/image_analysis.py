"""Multimodal image analysis branch. Never equate pixels with authenticated capture provenance."""
from __future__ import annotations
import json,uuid
from .config import is_live_ai,setting

async def describe_damage_image(image_bytes:bytes,mime_type:str,case_id:str)->dict:
    if mime_type not in ('image/png','image/jpeg'):
        return {'mode':'NOT_ANALYZED','caption':'Not an image','source_origin_verified':False,
                'authenticity_verdict':'UNKNOWN'}
    if not is_live_ai():
        return {'mode':'MOCK_NOT_MODEL_OUTPUT','caption':'Image stored but NOT visually interpreted in offline mode',
                'source_origin_verified':False,'authenticity_verdict':'UNKNOWN',
                'pixel_damage_observation':None}
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from google.adk.runners import Runner
    from google.genai import types
    agent=LlmAgent(name='DamageImageAnalyst',model=setting('GEMINI_MODEL','gemini-2.5-flash'),
      instruction=('Describe only objects/damage you can actually see. Return JSON with keys '
        'visible_soiling_or_damage, description, uncertainty. Do not assert that the image '
        'is genuine or timestamp-authentic. Never determine rider fault, trip attribution or fees.'))
    svc=InMemorySessionService();sid=str(uuid.uuid4())
    await svc.create_session(app_name='ryderesolve-images',user_id='synthetic-demo',session_id=sid)
    runner=Runner(agent=agent,app_name='ryderesolve-images',session_service=svc)
    content=types.Content(role='user',parts=[types.Part(text=f'Synthetic vehicle photo for case {case_id}. Assess only visible pixels.'),
                    types.Part.from_bytes(data=image_bytes,mime_type=mime_type)])
    answers=[]
    async for event in runner.run_async(user_id='synthetic-demo',session_id=sid,new_message=content):
        if event.is_final_response() and event.content:
            answers.extend([p.text for p in (event.content.parts or []) if getattr(p,'text',None)])
    if not answers:raise RuntimeError('Image model returned no final text')
    response='\n'.join(answers)
    try:summary=json.loads(response.strip().strip('`').removeprefix('json').strip())
    except ValueError:summary={'description':response,'uncertainty':'Unstructured multimodal response'}
    return {'mode':'ADK_GEMINI_PIXELS_ONLY','pixel_observation':summary,
            'source_origin_verified':False,'authenticity_verdict':'UNKNOWN',
            'requires_trip_camera_attestation':True}
