const TYPES = new Set(['image/png', 'image/jpeg', 'application/pdf']);
export function validateAttachments(files) {
  for (const file of files) {
    if (!TYPES.has(file.type)) return `${file.name}: choose a PNG, JPEG, or PDF.`;
    if (!file.size || file.size > 5 * 1024 * 1024) return `${file.name}: each file must be between 1 byte and 5 MB.`;
  }
  return '';
}

// Upload only the supplied queue. Failures stay retryable on the saved case.
export async function uploadReportAttachments(call, caseId, files, onProgress = () => {}) {
  const failed = [];
  for (const [index, file] of files.entries()) {
    onProgress(index + 1, files.length);
    const body = new FormData();
    body.append('file', file);
    try {
      await call(`cases/${caseId}/files`, {method: 'POST', body});
    } catch (error) {
      failed.push({file, error: error.message || 'Upload failed'});
    }
  }
  return failed;
}
