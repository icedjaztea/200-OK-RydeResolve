/**
 * Shared human-readable labels for RydeResolve frontend portals.
 *
 * Every raw status code, path, disposition, category, or notification kind
 * from the backend API is mapped to a professional, user-facing label.
 * Raw codes are never shown without a readable equivalent.
 *
 * These labels do not change backend behavior — they only improve the
 * presentation of existing API response fields.
 */

export const STATUS_LABELS = {
  NEW: 'New case — pending processing',
  AWAITING_CLARIFICATION: 'Awaiting response',
  REVIEW_REQUIRED: 'Human review required',
  RESOLVED: 'Resolved',
  REVIEWED_AND_RESOLVED: 'Resolved by reviewer',
};

export const PATH_LABELS = {
  IMMEDIATE_HUMAN_REVIEW: 'Immediate human review',
  CLARIFICATION: 'Clarification requested',
  HUMAN_REVIEW: 'Human review',
  RESOLVED: 'Resolved',
  HUMAN_REVIEW_COMPLETED: 'Human review completed',
};

export const TONES = {
  RESOLVED: 'good',
  REVIEWED_AND_RESOLVED: 'good',
  AWAITING_CLARIFICATION: 'warn',
  REVIEW_REQUIRED: 'bad',
  NEW: 'neutral',
};

export const CATEGORY_LABELS = {
  fare_dispute: 'Fare dispute',
  route_deviation: 'Route deviation',
  no_show_charge: 'No-show charge',
  driver_no_show: 'Driver no-show',
  property_damage: 'Property damage',
  safety_incident: 'Safety incident',
  other: 'Other / I\u2019m not sure',
};

export const DISPOSITION_LABELS = {
  refund: 'Refund (simulated)',
  credit: 'In-app credit (simulated)',
  no_action: 'No action taken',
  reject_claim: 'Claim rejected',
  undetermined: 'Pending determination',
};

export const NOTIF_KIND_LABELS = {
  CLARIFICATION_REQUEST: 'Clarification request',
  RESOLUTION_RECEIPT: 'Resolution receipt',
  SAFETY_REVIEW_ALERT: 'Safety review alert',
  SIMULATED_OUTBOX_NOT_DELIVERED: 'Simulated — not delivered',
};

/**
 * Case-specific outcome explanation derived from case detail fields.
 * Replaces the previous generic disposition dictionary.
 *
 * @param {object} detail - Full case detail from GET /cases/{id}
 * @returns {string|null} Human-readable outcome or null if no outcome yet.
 */
export function outcomeExplanation(detail) {
  if (!detail) return null;
  const action = detail.mock_action;
  if (!action) {
    if (detail.status === 'REVIEW_REQUIRED' || detail.status === 'NEW') {
      return 'Your case is awaiting review. No automated outcome has been determined — a reviewer will assess the evidence and decide.';
    }
    if (detail.status === 'AWAITING_CLARIFICATION') {
      return 'The case is waiting for requested information before the reviewer can continue.';
    }
    return null;
  }
  const amt = `SGD ${Number(action.amount || 0).toFixed(2)}`;
  const receipt = action.receipt;
  switch (action.disposition) {
    case 'refund':
      return `A simulated refund of ${amt} has been recorded against this case. The payment destination is not specified in this demo — no real card or wallet transfer was executed. Test receipt: ${receipt}.`;
    case 'credit':
      return `A simulated in-app credit of ${amt} has been applied. This is not a card refund — no real payment method was charged or credited. Test receipt: ${receipt}.`;
    case 'no_action':
      return `No monetary transfer was made. The decision was "no action" — ${amt} was not moved. No payment destination is involved. Test receipt: ${receipt}.`;
    case 'reject_claim':
      return `The claim has been rejected. No refund, credit, or transfer of ${amt} was made. Test receipt: ${receipt}.`;
    default:
      return `Case outcome recorded with disposition "${action.disposition}". Test receipt: ${receipt}.`;
  }
}

/**
 * Next-action guidance for the rider based on case status.
 * @param {object} detail
 * @returns {string}
 */
export function riderNextAction(detail) {
  if (!detail) return '';
  switch (detail.status) {
    case 'NEW':
      return 'Your case has been received and is awaiting initial processing by the review team.';
    case 'AWAITING_CLARIFICATION':
      return detail.clarifications?.some(q=>q.recipient==='rider'&&q.status==='PENDING')?'Please respond to the request below so the reviewer can continue.':'Waiting for the driver’s response. You do not need to respond right now.';
    case 'REVIEW_REQUIRED':
      return 'Your case is being reviewed by a human reviewer. No further action is needed from you at this time.';
    case 'RESOLVED':
    case 'REVIEWED_AND_RESOLVED':
      return 'This case has been resolved. Review the outcome below.';
    default:
      return 'Your case is being processed.';
  }
}

/**
 * Next-action guidance for the driver based on case status.
 * @param {object} detail
 * @returns {string}
 */
export function driverNextAction(detail) {
  if (!detail) return '';
  switch (detail.status) {
    case 'NEW':
      return 'This case has been filed and is awaiting processing.';
    case 'AWAITING_CLARIFICATION':
      return detail.clarifications?.some(q=>q.recipient==='driver'&&q.status==='PENDING')?'Please respond to the request below when it is safe to do so.':'Waiting for the rider’s response. You do not need to respond right now.';
    case 'REVIEW_REQUIRED':
      return 'This case is under human review. No further action is needed from you at this time.';
    case 'RESOLVED':
    case 'REVIEWED_AND_RESOLVED':
      return 'This case has been resolved. Review the outcome below.';
    default:
      return 'This case is being processed.';
  }
}

/**
 * Human-readable label for a raw status code.
 * Falls back to a prettified version of the raw code.
 */
export function statusLabel(status) {
  return STATUS_LABELS[status] || (status || '').replaceAll('_', ' ');
}

/**
 * Human-readable label for a decision path.
 */
export function pathLabel(path) {
  return PATH_LABELS[path] || (path || '').replaceAll('_', ' ');
}

/**
 * Human-readable label for a dispute category.
 */
export function categoryLabel(category) {
  return CATEGORY_LABELS[category] || (category || '').replaceAll('_', ' ');
}

/**
 * Human-readable label for a disposition code.
 */
export function dispositionLabel(disposition) {
  return DISPOSITION_LABELS[disposition] || (disposition || '').replaceAll('_', ' ');
}

/**
 * Human-readable label for a notification kind.
 */
export function notifKindLabel(kind) {
  if(kind==='APPEAL_SUBMITTED')return 'Appeal submitted';
  if(kind==='CASE_SUBMITTED')return 'New report';
  if(kind==='RESPONSE_RECEIVED')return 'Response received';
  return NOTIF_KIND_LABELS[kind] || (kind || '').replaceAll('_', ' ');
}

export function notificationStatus(note){
  if(note.status==='DELIVERED')return 'Delivered in app';
  if(note.status==='NO_LINKED_RECIPIENT')return 'No linked recipient';
  return 'Historical update · not delivered';
}
