/**
 * Server-side proxy for RydeResolve backend.
 *
 * Browsers never learn the backend network address. The backend independently
 * authorizes every request via X-Demo-Key (application-level authorization).
 *
 * When BACKEND_AUTH_MODE=cloud_run, every request is additionally authenticated
 * with a Google-signed OIDC identity token in the Authorization header. The
 * token audience is the canonical BACKEND_URL origin — never the requested path
 * or query string.
 *
 * The identity token, service credentials, and internal error details are never
 * exposed to the browser. Tokens are never logged.
 */

import { GoogleAuth } from 'google-auth-library';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BACKEND_URL = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const AUTH_MODE = process.env.BACKEND_AUTH_MODE || 'local';
const VALID_MODES = new Set(['cloud_run', 'local']);

// Fail closed on invalid auth mode — never silently fall back.
if (!VALID_MODES.has(AUTH_MODE)) {
  throw new Error(
    `Invalid BACKEND_AUTH_MODE "${AUTH_MODE}". Valid values: cloud_run, local.`
  );
}

// In cloud_run mode, BACKEND_URL must be an HTTPS URL (Cloud Run private service).
if (AUTH_MODE === 'cloud_run' && !BACKEND_URL.startsWith('https://')) {
  throw new Error(
    `BACKEND_URL must be an https:// URL when BACKEND_AUTH_MODE=cloud_run. Got: ${BACKEND_URL}`
  );
}

// The audience for Google OIDC tokens must be the canonical backend origin,
// never the requested API path or query string.
// See: https://cloud.google.com/run/docs/authenticating/service-to-service
const BACKEND_AUDIENCE = BACKEND_URL;

// GoogleAuth instance — created once and reused for token caching.
// In cloud_run mode, uses the runtime service account credentials
// (ryderesolve-web-runtime@ryderesolve-200-ok.iam.gserviceaccount.com).
let _googleAuth = null;

/**
 * Retrieve a Google-signed OIDC identity token for the backend audience.
 * Returns null in local mode.
 * Throws in cloud_run mode if credentials are missing or token retrieval fails.
 *
 * @returns {Promise<string|null>} The ID token, or null in local mode.
 */
async function getIdentityToken() {
  if (AUTH_MODE !== 'cloud_run') return null;

  if (!_googleAuth) {
    _googleAuth = new GoogleAuth({
      scopes: ['https://www.googleapis.com/auth/cloud-platform'],
    });
  }

  try {
    const client = await _googleAuth.getIdTokenClient(BACKEND_AUDIENCE);
    // Google's documented method: the IdTokenClient exposes the token fetch
    // via idTokenProvider.fetchIdToken(audience), not on the client itself.
    // See: https://cloud.google.com/run/docs/authenticating/service-to-service
    const token = await client.idTokenProvider.fetchIdToken(BACKEND_AUDIENCE);

    if (!token || typeof token !== 'string') {
      throw new Error('Empty or non-string token returned.');
    }

    return token;
  } catch (err) {
    // Never expose internal error details to the browser.
    // Fail closed — no unauthenticated request is sent.
    throw new Error('Identity token retrieval failed.');
  }
}

/**
 * Validate the backend URL to prevent arbitrary target URLs.
 * BACKEND_URL must come exclusively from server configuration.
 * @param {string} url
 * @returns {boolean}
 */
function isAllowedBackend(url) {
  try {
    const parsed = new URL(url);
    // Only allow http (local dev) and https (cloud_run).
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;
    // No userinfo (credentials) in URL.
    if (parsed.username || parsed.password) return false;
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate the incoming proxy path to prevent path traversal.
 * @param {string[]} parts
 * @returns {boolean}
 */
function isValidProxyPath(parts) {
  if (!Array.isArray(parts)) return false;
  return parts.every(s =>
    typeof s === 'string' &&
    s !== '..' &&
    !s.includes('/') &&
    !s.includes('\\') &&
    !s.includes('\0')
  );
}

/**
 * Core forwarding logic shared by GET and POST handlers.
 *
 * @param {Request} request - The incoming browser request.
 * @param {{params: Promise<{path: string[]}>}} ctx - Route context with params.
 * @returns {Promise<Response>}
 */
async function forward(request, ctx) {
  const parts = (await ctx.params).path || [];

  // --- Input validation ---
  if (!isValidProxyPath(parts)) {
    return new Response('Invalid path', { status: 400 });
  }

  if (!isAllowedBackend(BACKEND_URL)) {
    return Response.json(
      { error: 'Backend configuration error.' },
      { status: 500 }
    );
  }

  // --- Build backend URL ---
  const path = parts.map(s => encodeURIComponent(s)).join('/');
  const url = `${BACKEND_URL}/${path}${new URL(request.url).search}`;

  // --- Build headers ---
  // Start with the headers we control. We never blindly copy all
  // browser headers — only X-Demo-Key and Content-Type.
  const headers = {};

  // Application-level authorization (demo passcode).
  const key = request.headers.get('x-demo-key');
  const ct = request.headers.get('content-type');
  if (key) headers['X-Demo-Key'] = key;
  if (ct) headers['Content-Type'] = ct;

  // --- Cloud Run identity token (server-side only) ---
  let identityToken = null;
  try {
    identityToken = await getIdentityToken();
  } catch {
    // Fail closed: never send an unauthenticated request to a private backend.
    return Response.json(
      { error: 'Authentication required and unavailable.' },
      { status: 503 }
    );
  }

  // Attach the Google identity token as a standard Bearer token.
  // This header is server-to-server; it never reaches the browser.
  if (identityToken) {
    headers['Authorization'] = `Bearer ${identityToken}`;
  }

  // --- Forward the request ---
  try {
    const resp = await fetch(url, {
      method: request.method,
      headers,
      body: ['POST', 'PUT', 'PATCH'].includes(request.method)
        ? await request.arrayBuffer()
        : undefined,
      cache: 'no-store',
      redirect: 'manual',
    });

    const body = await resp.arrayBuffer();

    // --- Build response — strip any auth/token headers from upstream ---
    const responseHeaders = {
      'content-type': resp.headers.get('content-type') || 'application/json',
      'cache-control': 'no-store',
    };

    // Explicitly never copy Authorization, Set-Cookie, or other sensitive
    // upstream headers to the browser response.
    return new Response(body, {
      status: resp.status,
      headers: responseHeaders,
    });
  } catch {
    // Never expose internal network error details to the browser.
    return Response.json(
      { error: 'Backend unreachable.' },
      { status: 502 }
    );
  }
}

// ---------------------------------------------------------------------------
// Route handlers — use the Node.js runtime for google-auth-library.
// ---------------------------------------------------------------------------

export const runtime = 'nodejs';

export async function GET(req, ctx) {
  return forward(req, ctx);
}

export async function POST(req, ctx) {
  return forward(req, ctx);
}
