function failure(detail, status) {
  return Response.json({ detail }, { status, headers: { 'Cache-Control': 'no-store' } });
}

export async function handleRequest(request, env, fetchBackend = fetch) {
  const url = new URL(request.url);
  if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) {
    return env.ASSETS.fetch(request);
  }
  if (!env.BACKEND_ORIGIN) {
    return failure('Chưa kết nối máy chủ phân tích. Cấu hình BACKEND_ORIGIN trong Cloudflare Worker bằng URL HTTPS của backend Python/YOLO.', 503);
  }
  let origin;
  try {
    origin = new URL(env.BACKEND_ORIGIN);
    if (origin.protocol !== 'https:' || origin.username || origin.password ||
        origin.pathname !== '/' || origin.search || origin.hash || origin.host === url.host) {
      throw new Error('Invalid origin');
    }
  } catch {
    return failure('BACKEND_ORIGIN phải là địa chỉ gốc HTTPS của backend, không kèm /api, tài khoản, mật khẩu hoặc domain của Worker.', 503);
  }
  const target = new URL(url.pathname + url.search, origin);
  const headers = new Headers(request.headers);
  // Access cookies and identity tokens belong to Cloudflare, not the backend.
  for (const name of ['host', 'cookie', 'cf-access-jwt-assertion', 'cf-access-client-id', 'cf-access-client-secret']) {
    headers.delete(name);
  }
  if (env.BACKEND_PASSWORD) {
    const credentials = new TextEncoder().encode(`${env.BACKEND_USERNAME || 'kun'}:${env.BACKEND_PASSWORD}`);
    headers.set('Authorization', `Basic ${btoa(String.fromCharCode(...credentials))}`);
  }
  try {
    const upstream = await fetchBackend(target.href, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      redirect: 'manual',
      duplex: 'half',
    });
    const responseHeaders = new Headers(upstream.headers);
    responseHeaders.set('Cache-Control', 'no-store');
    return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders });
  } catch {
    return failure('Không kết nối được máy chủ phân tích. Kiểm tra backend đang chạy và BACKEND_ORIGIN đã đúng.', 502);
  }
}

export default {
  fetch(request, env) {
    return handleRequest(request, env);
  },
};
