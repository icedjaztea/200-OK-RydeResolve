import {it,expect} from 'vitest';
import {driverNextAction,riderNextAction,notificationStatus} from './labels';
it('tells the appellant to wait, and the respondent to answer',()=>{
  const detail={status:'AWAITING_CLARIFICATION',clarifications:[{recipient:'rider',status:'PENDING'}]};
  expect(driverNextAction(detail)).toContain('Waiting for the rider');
  expect(riderNextAction(detail)).toContain('Please respond');
});
it('does not relabel historical or unlinked notifications as delivered',()=>{
  expect(notificationStatus({status:'SIMULATED_OUTBOX_NOT_DELIVERED'})).toContain('not delivered');
  expect(notificationStatus({status:'NO_LINKED_RECIPIENT'})).toBe('No linked recipient');
  expect(notificationStatus({status:'DELIVERED'})).toBe('Delivered in app');
});
