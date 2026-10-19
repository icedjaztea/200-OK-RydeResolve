'use client';

/**
 * Case activity timeline.
 *
 * REVIEWER: receives full case document including `events` — renders
 *   a detailed timeline from actual recorded event records.
 *
 * RIDER / DRIVER: `events` is stripped by safe_response.py for security.
 *   The timeline is derived ONLY from permitted fields they already
 *   receive: `status`, `path`, `clarifications`, `notifications`,
 *   `mock_action`. No historical events are invented. Only the current
 *   known state is shown as a simple status progression.
 *
 * @param {object} detail - Case detail from GET /cases/{id}
 * @param {string} [role='reviewer'] - 'reviewer' | 'rider' | 'driver'
 * @returns {JSX.Element|null}
 */
export function CaseTimeline({detail, role='reviewer'}){
  if(!detail) return null;

  // Reviewer gets full events — render detailed timeline.
  if(role==='reviewer' && detail.events && detail.events.length>0){
    return <ReviewerTimeline events={detail.events}/>;
  }

  // Rider/Driver: events are stripped. Build a minimal, accurate
  // status progression from permitted fields only. Do NOT invent
  // timestamps, historical events, or internal traces.
  return <PartyTimeline detail={detail} role={role}/>;
}

/* ── Reviewer: full timeline from recorded events ─────────────────── */

function ReviewerTimeline({events}){
  const items=events.map(e=>{
    const isEscalated=e.kind==='mandatory_safety_escalation'||e.kind==='clarification_unresolved_to_reviewer';
    const isDone=e.kind==='mock_action_completed'||e.kind==='reviewer_mock_remedy'||e.kind==='human_review_completed';
    const isActive=e.kind==='clarification_requested'||e.kind==='routing_index_read'||e.kind==='policy_gate_applied';
    let label=eventLabel(e.kind);
    let desc=eventDescription(e);
    let dotClass=isDone?'done':isEscalated?'escalated':isActive?'active':'pending';
    return {label,desc,dotClass,timestamp:e.timestamp,kind:e.kind};
  });

  return <div className="timeline">
    {items.map((item,i)=>(
      <div key={i} className="timeline-item">
        <div className={`timeline-dot ${item.dotClass}`}/>
        <div className="timeline-body">
          <div className="tl-label">{item.label}</div>
          {item.timestamp&&<div className="tl-time">{item.timestamp}</div>}
          {item.desc&&<div className="tl-desc">{item.desc}</div>}
        </div>
      </div>
    ))}
  </div>;
}

/* ── Rider/Driver: minimal status progression from permitted fields ── */

function PartyTimeline({detail, role}){
  const items=[];

  // 1. Case filed — always known from case existence
  items.push({
    label:'Case filed',
    desc:`Category: ${friendlyCategory(detail.category)}`,
    dotClass:'done',
  });

  // 2. Clarification requested — derived from recipient-filtered clarifications
  const myClarifications=detail.clarifications||[];
  const hasPending=myClarifications.some(c=>c.status==='PENDING');
  const hasAnswered=myClarifications.some(c=>c.status==='ANSWERED');
  if(hasPending){
    items.push({
      label:'Information requested',
      desc:`The reviewer has asked you for more information`,
      dotClass:'active',
    });
  }
  if(detail.status==='AWAITING_CLARIFICATION'&&!hasPending){
    items.push({label:'Waiting for the other party',desc:'The other party has been asked to respond',dotClass:'active'});
  }
  if(hasAnswered){
    items.push({
      label:'Information provided',
      desc:'Your response has been recorded as an unverified claim',
      dotClass:'done',
    });
  }

  // 3. Current decision path — derived from `path` field (permitted)
  const path=detail.path;
  if(path){
    if(path==='IMMEDIATE_HUMAN_REVIEW'){
      items.push({
        label:'Safety escalation',
        desc:'Safety allegation requires immediate human review',
        dotClass:'escalated',
      });
    } else if(path==='HUMAN_REVIEW'){
      items.push({
        label:'Under review',
        desc:'Case requires human reviewer assessment',
        dotClass:'pending',
      });
    } else if(path==='AUTO_ELIGIBLE'){
      items.push({
        label:'Policy evaluation',
        desc:'Case approved for automatic resolution',
        dotClass:'done',
      });
    }
  }

  // 4. Resolution — derived from `mock_action` (permitted, already filtered)
  const action=detail.mock_action;
  if(action && action.receipt){
    items.push({
      label:'Resolution processed',
      desc:`Simulated record · Receipt: ${action.receipt}`,
      dotClass:'done',
    });
  }

  // 5. Final status — derived from `status` field (permitted)
  const status=detail.status;
  if(status==='RESOLVED'||status==='REVIEWED_AND_RESOLVED'){
    items.push({
      label:'Case resolved',
      desc:'This case has been closed',
      dotClass:'done',
    });
  }

  if(items.length===0) return null;

  return <div className="timeline">
    {items.map((item,i)=>(
      <div key={i} className="timeline-item">
        <div className={`timeline-dot ${item.dotClass}`}/>
        <div className="timeline-body">
          <div className="tl-label">{item.label}</div>
          {item.desc&&<div className="tl-desc">{item.desc}</div>}
        </div>
      </div>
    ))}
  </div>;
}

/* ── Shared helpers ───────────────────────────────────────────────── */

function friendlyCategory(cat){
  const labels={
    fare_dispute:'Fare dispute',
    route_deviation:'Route deviation',
    no_show_charge:'No-show charge',
    driver_no_show:'Driver no-show',
    property_damage:'Property damage',
    safety_incident:'Safety incident',
  };
  return labels[cat]||cat||'—';
}

function eventLabel(kind){
  const labels={
    case_created:'Case filed',
    appeal_created:'Appeal submitted',
    automatic_learning_checked:'Future review guidance checked',
    automatic_learning_failed:'Guidance publication failed',
    routing_index_read:'Routing analysis',
    policy_gate_applied:'Policy evaluation',
    mandatory_safety_escalation:'Safety escalation',
    clarification_requested:'Information requested',
    clarification_answered:'Information provided',
    clarification_unresolved_to_reviewer:'Escalated to reviewer',
    mock_action_completed:'Resolution processed',
    human_review_completed:'Reviewer decision',
    reviewer_mock_remedy:'Reviewer remedy recorded',
    image_evidence_recorded:'Evidence uploaded',
    synthetic_source_record_added:'Verified fact added',
    learning_proposal_staged:'Learning proposal staged',
  };
  return labels[kind]||kind.replaceAll('_',' ');
}

function eventDescription(e){
  const d=e.details||{};
  if(e.kind==='case_created')return `Category: ${friendlyCategory(d.category)}`;
  if(e.kind==='routing_index_read')return `${d.count||0} candidate rules identified`;
  if(e.kind==='policy_gate_applied'){
    if(d.path==='AUTO_ELIGIBLE')return 'Case approved for automatic resolution';
    if(d.path==='HUMAN_REVIEW')return 'Case requires human review';
    if(d.path==='IMMEDIATE_HUMAN_REVIEW')return 'Immediate human review required';
    return d.path||'';
  }
  if(e.kind==='mandatory_safety_escalation')return 'Safety allegation detected — AI cannot determine fault';
  if(e.kind==='clarification_requested')return `Asked ${d.recipient||'party'} for more information`;
  if(e.kind==='clarification_answered')return 'Party provided an unverified response';
  if(e.kind==='clarification_unresolved_to_reviewer')return 'Unverified response cannot resolve the case';
  if(e.kind==='mock_action_completed')return `Test transaction: ${d.receipt||'—'}`;
  if(e.kind==='human_review_completed')return `${d.disposition||'—'}: ${d.reason||''}`;
  if(e.kind==='reviewer_mock_remedy')return `Test transaction: ${d.receipt||'—'}`;
  if(e.kind==='image_evidence_recorded')return `File: ${d.object_ref||'—'}`;
  if(e.kind==='synthetic_source_record_added')return `Field: ${d.field||'—'}`;
  if(e.kind==='learning_proposal_staged')return `Proposal: ${d.proposal_id||'—'}`;
  return '';
}
