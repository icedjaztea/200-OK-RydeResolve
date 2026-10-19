import {describe,it,expect,vi,afterEach} from 'vitest';
import {processCaseRequest} from './processCase';
afterEach(()=>vi.useRealTimers());
describe('slow case evaluation',()=>{
  it('continues waiting beyond 25 seconds and returns the real result',async()=>{
    vi.useFakeTimers();let resolve;
    const call=vi.fn(()=>new Promise(r=>{resolve=r}));const slow=vi.fn();
    let finished=false;
    const pending=processCaseRequest(call,'DEMO-FARE-OVER50',slow).then(r=>{finished=true;return r});
    await vi.advanceTimersByTimeAsync(30000);
    expect(slow).toHaveBeenCalledOnce();expect(finished).toBe(false);expect(call).toHaveBeenCalledOnce();
    resolve({status:'REVIEW_REQUIRED'});
    expect(await pending).toEqual({status:'REVIEW_REQUIRED'});
  });
  it('clears the slow notice timer after an error',async()=>{
    vi.useFakeTimers();const slow=vi.fn();
    await expect(processCaseRequest(()=>Promise.reject(new Error('Connection lost')),'CASE-1',slow)).rejects.toThrow('Connection lost');
    await vi.advanceTimersByTimeAsync(30000);expect(slow).not.toHaveBeenCalled();
  });
});
