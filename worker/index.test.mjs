import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { handleRequest } from './index.mjs';

const request = (path, options) => new Request(`https://app.workers.dev${path}`, options);
const env = {BACKEND_ORIGIN: 'https://backend.example.com'};

test('serves frontend assets without requiring a backend', async () => {
  const response = await handleRequest(request('/'), { ASSETS: {fetch: async () => new Response('frontend')} });
  assert.equal(await response.text(), 'frontend');
});
test('missing backend returns JSON, not the SPA shell', async () => {
  const response = await handleRequest(request('/api/health'), {});
  assert.equal(response.status, 503);
  assert.match((await response.json()).detail, /BACKEND_ORIGIN/);
});
for (const origin of ['http://backend.example.com', 'https://app.workers.dev', 'https://backend.example.com/api', 'https://user:secret@backend.example.com', 'https://backend.example.com?x=1', 'invalid']) {
  test(`rejects invalid backend origin: ${origin}`, async () => {
    const response = await handleRequest(request('/api/jobs'), {BACKEND_ORIGIN:origin});
    assert.equal(response.status,503);
  });
}
test('streams upload to the correct path and strips Cloudflare identity headers', async () => {
  const response = await handleRequest(request('/api/jobs?test=1', {
    method:'POST', body:'video bytes', headers:{'Content-Type':'multipart/form-data; boundary=abc',cookie:'CF_Authorization=private','cf-access-jwt-assertion':'private'},
  }), env, async (url, init) => {
    assert.equal(url,'https://backend.example.com/api/jobs?test=1');
    assert.equal(init.method,'POST');
    assert.equal(init.headers.get('content-type'),'multipart/form-data; boundary=abc');
    assert.equal(init.headers.get('cookie'),null);
    assert.equal(init.headers.get('cf-access-jwt-assertion'),null);
    assert.equal(await new Response(init.body).text(),'video bytes');
    assert.equal(init.redirect,'manual');
    return Response.json({id:'job'}, {status:202});
  });
  assert.equal(response.status,202);
  assert.equal((await response.json()).id,'job');
});
test('backend secret supports Unicode credentials and is only sent upstream', async () => {
  const response = await handleRequest(request('/api/health'), {...env, BACKEND_PASSWORD:'mật-khẩu'}, async (url, init) => {
    assert.equal(Buffer.from(init.headers.get('authorization').slice(6),'base64').toString(),'kun:mật-khẩu');
    return Response.json({ok:true});
  });
  assert.equal(response.headers.get('authorization'), null);
  assert.deepEqual(await response.json(),{ok:true});
});
test('streams output files and preserves disposition and status', async () => {
  const response = await handleRequest(request('/api/jobs/job/files/annotated.mp4'), env, async () => new Response('video', {headers:{'Content-Type':'video/mp4','Content-Disposition':'inline; filename="annotated.mp4"'}}));
  assert.equal(response.headers.get('content-type'),'video/mp4');
  assert.equal(response.headers.get('cache-control'),'no-store');
  assert.equal(await response.text(),'video');
});
test('preserves backend validation and authentication failures', async () => {
  for (const status of [401,413,422,500]) {
    const response = await handleRequest(request('/api/jobs'), env, async () => Response.json({detail:'Backend error'}, {status}));
    assert.equal(response.status,status);
    assert.equal((await response.json()).detail,'Backend error');
  }
});
test('unreachable backend becomes an actionable JSON error', async () => {
  const response = await handleRequest(request('/api/health'),env, async () => {throw Error('private network details');});
  assert.equal(response.status,502);
  assert.match((await response.json()).detail,/Không kết nối/);
});

test('Worker entrypoint accepts Cloudflare execution context', async () => {
  const response = await worker.fetch(request('/api/health'), {}, {waitUntil() {}});
  assert.equal(response.status, 503);
});
