import {describe,it,expect,vi} from 'vitest';
import {validateAttachments,uploadReportAttachments} from './reportAttachments';
const file=(name='seat.png',type='image/png')=>new File(['synthetic'],name,{type});

describe('report attachments',()=>{
  it('accepts supported files and rejects empty, oversized, or unsupported files',()=>{
    expect(validateAttachments([file(),file('receipt.pdf','application/pdf')])).toBe('');
    expect(validateAttachments([file('bad.txt','text/plain')])).toContain('PNG, JPEG, or PDF');
    expect(validateAttachments([{name:'large.png',type:'image/png',size:5*1024*1024+1}])).toContain('5 MB');
    expect(validateAttachments([new File([],'empty.png',{type:'image/png'})])).toContain('1 byte');
  });
  it('uploads to the saved case and retries only failed files without creating another case',async()=>{
    const files=[file('before.png'),file('after.png')];
    const call=vi.fn().mockResolvedValueOnce({}).mockRejectedValueOnce(new Error('Try again'));
    const progress=vi.fn();
    const failed=await uploadReportAttachments(call,'DRIVER-SAVED',files,progress);
    expect(failed).toEqual([{file:files[1],error:'Try again'}]);
    expect(call.mock.calls.every(([path])=>path==='cases/DRIVER-SAVED/files')).toBe(true);
    expect(call.mock.calls[0][1].body.get('file').name).toBe('before.png');
    expect(progress).toHaveBeenLastCalledWith(2,2);
    call.mockResolvedValueOnce({});
    expect(await uploadReportAttachments(call,'DRIVER-SAVED',failed.map(item=>item.file))).toEqual([]);
    expect(call).toHaveBeenCalledTimes(3);
    expect(call.mock.calls[2][1].body.get('file').name).toBe('after.png');
  });
});
