import React from 'react';
export function imageCaption(analysis) {
  if (analysis?.mode !== 'ADK_GEMINI_PIXELS_ONLY') return 'AI description unavailable.';
  const text = analysis.caption || analysis.pixel_observation?.description;
  if (typeof text !== 'string' || !text.trim()) return 'AI description unavailable.';
  const line = text.replace(/\s+/g, ' ').trim();
  return line.length > 160 ? line.slice(0, 157).trimEnd() + '…' : line;
}

export function ModelLabel({trace}) {
  if (!trace?.model) return null;
  const label = name => name?.replace(/^gemini-/, 'Gemini ').replace(/-flash$/, ' Flash');
  return <p className="muted" style={{fontSize:'12px'}}>Analysed by {label(trace.model)}{trace.fallback_used && ` · Fallback after ${label(trace.primary_model)} retries`}</p>;
}

export default function ImageAnalysisSummary({analysis}) {
  const observation = analysis?.pixel_observation;
  return <div className="image-analysis-summary">
    <p style={{margin:'6px 0',fontSize:'13px'}}><strong>AI description: </strong>{imageCaption(analysis)}</p>
    <ModelLabel trace={analysis?.model_trace}/>
    {analysis?.mode === 'ADK_GEMINI_PIXELS_ONLY' && observation && <details>
      <summary style={{fontSize:'12px',cursor:'pointer'}}>Full image analysis</summary>
      <p>{observation.description}</p>
      {observation.uncertainty && <p><strong>Limitations: </strong>{observation.uncertainty}</p>}
      <p className="muted">Visual description only. It does not verify when or where the photo was taken, or who caused the damage.</p>
    </details>}
  </div>;
}
