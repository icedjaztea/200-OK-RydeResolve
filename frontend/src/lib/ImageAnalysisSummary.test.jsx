import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {it,expect} from 'vitest';
import ImageAnalysisSummary,{imageCaption} from './ImageAnalysisSummary';
it('shows the one-line description without opening the image and retains full analysis',()=>{
  const html=renderToStaticMarkup(<ImageAnalysisSummary analysis={{mode:'ADK_GEMINI_PIXELS_ONLY',caption:'A brown stain on a grey seat.',pixel_observation:{description:'A grey rear seat has an oval brown mark.',uncertainty:'Timing cannot be determined.'}}}/>);
  expect(html).toContain('A brown stain on a grey seat.');
  expect(html).toContain('Full image analysis');
  expect(html).toContain('Timing cannot be determined.');
});
it('supports existing images and never presents offline captions as AI observations',()=>{
  expect(imageCaption({mode:'ADK_GEMINI_PIXELS_ONLY',pixel_observation:{description:'A grey seat.\nBrown mark.'}})).toBe('A grey seat. Brown mark.');
  expect(imageCaption({mode:'MOCK_NOT_MODEL_OUTPUT',caption:'Not model output'})).toBe('AI description unavailable.');
  expect(imageCaption({mode:'ADK_GEMINI_PIXELS_ONLY',caption:'x'.repeat(200)})).toHaveLength(158);
});
it('clearly labels fallback image analysis',()=>{
  const html=renderToStaticMarkup(<ImageAnalysisSummary analysis={{mode:'ADK_GEMINI_PIXELS_ONLY',caption:'A seat.',model_trace:{model:'gemini-3.6-flash',primary_model:'gemini-3.8-flash',fallback_used:true}}}/>);
  expect(html).toContain('Gemini 3.6 Flash');
  expect(html).toContain('Fallback after Gemini 3.8 Flash retries');
});
