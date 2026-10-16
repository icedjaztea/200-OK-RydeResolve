/**
 * Focused tests for the Next.js → Cloud Run authenticated proxy.
 *
 * Covers:
 * - Local mode forwarding
 * - Cloud Run ID-token forwarding
 * - Missing credentials failing safely
 * - Rejection of invalid auth mode
 * - JSON and multipart request handling
 * - No Google token leaking to frontend responses
 *
 * Tests mock fetch and google-auth-library to avoid real network calls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mock google-auth-library
//
// The real IdTokenClient returned by GoogleAuth.getIdTokenClient(audience)
// exposes the token fetch via client.idTokenProvider.fetchIdToken(audience),
// NOT via client.fetchIdToken directly. The mock must match this shape so
// tests catch incorrect method usage.
// See: https://cloud.google.com/run/docs/authenticating/service-to-service
// ---------------------------------------------------------------------------

let mockFetchIdToken = vi.fn();
let mockGetIdTokenClient = vi.fn();

vi.mock('google-auth-library', () => ({
  GoogleAuth: class {
    constructor() {}
    async getIdTokenClient(audience) {
      mockGetIdTokenClient(audience);
      return {
        // The real IdTokenClient nests the token provider under idTokenProvider
        idTokenProvider: {
          fetchIdToken: mockFetchIdToken,
        },
      };
    }
  },
}));

// ---------------------------------------------------------------------------
// Helpers: build a Next.js-style route context
// ---------------------------------------------------------------------------

function makeCtx(pathParts) {
  return {
    params: Promise.resolve({ path: pathParts }),
  };
}

function makeRequest(method, { headers, body, contentType } = {}) {
  const h = headers || {};
  const init = { method, headers: {} };

  if (h['x-demo-key']) init.headers['x-demo-key'] = h['x-demo-key'];
  if (h['content-type']) init.headers['content-type'] = h['content-type'];

  if (body !== undefined) {
    if (body === '__formdata__') {
      // Simulate multipart form data
      const boundary = '----TestBoundary1234';
      init.headers['content-type'] = `multipart/form-data; boundary=${boundary}`;
      const bodyText = `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\nfake-png-data\r\n--${boundary}--\r\n`;
      init.body = bodyText;
    } else {
      init.headers['content-type'] = contentType || 'application/json';
      init.body = typeof body === 'string' ? body : JSON.stringify(body);
    }
  }

  return new Request('http://localhost:3000/api/proxy/health', init);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Proxy route — local mode', () => {
  let originalEnv;
  let fetchSpy;

  beforeEach(() => {
    originalEnv = { ...process.env };
    process.env.BACKEND_URL = 'http://127.0.0.1:8000';
    process.env.BACKEND_AUTH_MODE = 'local';

    fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('forwards GET requests to backend without auth header', async () => {
    // Re-import after env is set — each test gets a fresh module
    vi.resetModules();

    const mod = await import('./route.js');
    const req = makeRequest('GET', { headers: { 'x-demo-key': 'test-key' } });
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    const data = await resp.json();

    expect(resp.status).toBe(200);
    expect(data).toEqual({ ok: true });

    // fetch should have been called with the backend URL
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/health');

    // In local mode, no Authorization header
    expect(init.headers['Authorization']).toBeUndefined();
    // But X-Demo-Key is preserved
    expect(init.headers['X-Demo-Key']).toBe('test-key');
  });

  it('forwards POST with JSON body and preserves content-type', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('POST', {
      headers: { 'x-demo-key': 'rider-key', 'content-type': 'application/json' },
      body: { hello: 'world' },
    });
    const ctx = makeCtx(['cases']);

    const resp = await mod.POST(req, ctx);
    expect(resp.status).toBe(200);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/cases');
    expect(init.method).toBe('POST');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.headers['X-Demo-Key']).toBe('rider-key');
  });

  it('forwards POST with multipart form data', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('POST', {
      headers: { 'x-demo-key': 'reviewer-key' },
      body: '__formdata__',
    });
    const ctx = makeCtx(['cases', 'CASE-1', 'files']);

    const resp = await mod.POST(req, ctx);
    expect(resp.status).toBe(200);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/cases/CASE-1/files');
    expect(init.headers['Content-Type']).toContain('multipart/form-data');
  });

  it('preserves backend response status codes', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not found' }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      })
    );

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['cases', 'DOES-NOT-EXIST']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(404);
  });
});

describe('Proxy route — cloud_run mode', () => {
  let originalEnv;
  let fetchSpy;

  beforeEach(() => {
    originalEnv = { ...process.env };
    process.env.BACKEND_URL = 'https://ryderesolve-api-xxxx-de.a.run.app';
    process.env.BACKEND_AUTH_MODE = 'cloud_run';

    fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', fetchSpy);

    // Mock Google auth to return a fake token
    mockFetchIdToken.mockResolvedValue('fake-google-id-token-abc123');
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('attaches Google identity token as Bearer in Authorization header', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('GET', { headers: { 'x-demo-key': 'test-key' } });
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(200);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('https://ryderesolve-api-xxxx-de.a.run.app/health');
    expect(init.headers['Authorization']).toBe('Bearer fake-google-id-token-abc123');
    expect(init.headers['X-Demo-Key']).toBe('test-key');
  });

  it('uses BACKEND_URL origin as audience, not the request path', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['cases', 'CASE-1', 'review-packet']);

    await mod.GET(req, ctx);

    // getIdTokenClient should have been called with the backend origin,
    // not with the full path /cases/CASE-1/review-packet
    expect(mockGetIdTokenClient).toHaveBeenCalledWith(
      'https://ryderesolve-api-xxxx-de.a.run.app'
    );
  });

  it('regression: calls idTokenProvider.fetchIdToken, not client.fetchIdToken', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['health']);

    await mod.GET(req, ctx);

    // The correct API path: client.idTokenProvider.fetchIdToken(audience)
    expect(mockFetchIdToken).toHaveBeenCalledTimes(1);
    expect(mockFetchIdToken).toHaveBeenCalledWith(
      'https://ryderesolve-api-xxxx-de.a.run.app'
    );
  });

  it('regression: IdTokenClient mock does NOT expose fetchIdToken directly', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['health']);

    await mod.GET(req, ctx);

    // Verify the token came through the correct path — if the route code
    // called client.fetchIdToken directly, it would be undefined on the mock
    // and the request would fail closed with 503.
    const [url, init] = fetchSpy.mock.calls[0];
    expect(init.headers['Authorization']).toBe('Bearer fake-google-id-token-abc123');
  });

  it('fails closed (503) when identity token retrieval fails', async () => {
    vi.resetModules();

    mockFetchIdToken.mockRejectedValueOnce(new Error('No credentials'));

    const mod = await import('./route.js');

    const req = makeRequest('GET', { headers: { 'x-demo-key': 'test-key' } });
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(503);

    const data = await resp.json();
    expect(data.error).toContain('Authentication required');
    expect(data.error).not.toContain('credential');
    expect(data.error).not.toContain('No credentials');

    // fetch (to backend) should NOT have been called
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('fails closed (503) when token is empty string', async () => {
    vi.resetModules();

    mockFetchIdToken.mockResolvedValueOnce('');

    const mod = await import('./route.js');

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(503);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('does not leak Google token to the frontend response', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    // Mock backend returning an Authorization header (shouldn't happen but test for safety)
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          'content-type': 'application/json',
          'authorization': 'Bearer secret-should-not-leak',
        },
      })
    );

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(200);

    // Authorization header must NOT be present in the browser response
    expect(resp.headers.get('authorization')).toBeNull();
    expect(resp.headers.get('content-type')).toBe('application/json');
  });

  it('handles multipart uploads with auth in cloud_run mode', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    const req = makeRequest('POST', {
      headers: { 'x-demo-key': 'reviewer-key' },
      body: '__formdata__',
    });
    const ctx = makeCtx(['cases', 'CASE-1', 'files']);

    const resp = await mod.POST(req, ctx);
    expect(resp.status).toBe(200);

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toContain('/cases/CASE-1/files');
    expect(init.headers['Authorization']).toBe('Bearer fake-google-id-token-abc123');
    expect(init.headers['Content-Type']).toContain('multipart/form-data');
  });

  it('error response does not leak internal details', async () => {
    vi.resetModules();
    const mod = await import('./route.js');

    // Override the default resolved mock to reject for this test
    mockFetchIdToken.mockImplementationOnce(() =>
      Promise.reject(new Error('Could not load default credentials'))
    );

    const req = makeRequest('GET', {});
    const ctx = makeCtx(['health']);

    const resp = await mod.GET(req, ctx);
    const data = await resp.json();

    // Should fail closed with 503
    expect(resp.status).toBe(503);

    // Generic error, no credential details
    expect(data.error).toBe('Authentication required and unavailable.');
    expect(JSON.stringify(data)).not.toContain('credentials');
    expect(JSON.stringify(data)).not.toContain('default');
    expect(JSON.stringify(data)).not.toContain('token');
  });
});

describe('Proxy route — invalid auth mode', () => {
  let originalEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.resetModules();
  });

  it('throws on invalid BACKEND_AUTH_MODE', async () => {
    process.env.BACKEND_URL = 'http://127.0.0.1:8000';
    process.env.BACKEND_AUTH_MODE = 'something-invalid';

    // The module's top-level validation should throw on import.
    // vi.resetModules() forces re-evaluation so the env vars are read fresh.
    vi.resetModules();
    // Unmock google-auth-library so the real module evaluation path runs.
    vi.doUnmock('google-auth-library');

    await expect(import('./route.js')).rejects.toThrow(/Invalid BACKEND_AUTH_MODE/);
  });

  it('throws when cloud_run mode uses non-https BACKEND_URL', async () => {
    process.env.BACKEND_URL = 'http://127.0.0.1:8000';
    process.env.BACKEND_AUTH_MODE = 'cloud_run';

    await expect(import('./route.js')).rejects.toThrow(/https:\/\/ URL/);
  });
});

describe('Proxy route — security', () => {
  let originalEnv;
  let fetchSpy;

  beforeEach(() => {
    originalEnv = { ...process.env };
    process.env.BACKEND_URL = 'http://127.0.0.1:8000';
    process.env.BACKEND_AUTH_MODE = 'local';

    fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it('rejects path traversal (..) with 400', async () => {
    const mod = await import('./route.js');
    const req = makeRequest('GET', {});
    const ctx = makeCtx(['..', 'secret']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(400);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('rejects path with forward slashes', async () => {
    const mod = await import('./route.js');
    const req = makeRequest('GET', {});
    const ctx = makeCtx(['cases/something']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(400);
  });

  it('never forwards query string as audience (local mode has no token)', async () => {
    const mod = await import('./route.js');

    const req = new Request('http://localhost:3000/api/proxy/cases?category=fare_dispute');
    const ctx = makeCtx(['cases']);

    const resp = await mod.GET(req, ctx);
    expect(resp.status).toBe(200);

    // The backend URL should include the query string
    const [url] = fetchSpy.mock.calls[0];
    expect(url).toContain('?category=fare_dispute');
  });
});
