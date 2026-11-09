import test from 'node:test';
import assert from 'node:assert/strict';
import { requestJson } from './api.js';

test('accepts an actual backend response', async () => {
  const result = await requestJson(Response.json({id: 'job-123'}, {status:202}), 'Upload failed', data => typeof data.id === 'string');
  assert.equal(result.id, 'job-123');
});
for (const [name, body, status] of [
  ['empty Worker response', '', 405],
  ['SPA fallback', '<!doctype html><div id="root"></div>', 200],
  ['proxy failure', 'Bad Gateway', 502],
  ['malformed JSON', '{', 200],
  ['empty successful response', '', 200],
]) {
  test(name, async () => {
    await assert.rejects(requestJson(new Response(body, {status}), 'Không tải được.'), /backend Python\/YOLO/);
  });
}
test('rejects unrelated successful JSON', async () => {
  await assert.rejects(requestJson(Response.json({hello:'world'}), 'Không kết nối được.', data => data.ok === true), /backend Python\/YOLO/);
});
test('preserves backend validation messages', async () => {
  await assert.rejects(requestJson(Response.json({detail:'Chọn đủ vị trí người chơi.'}, {status:422}), 'Failed'), /Chọn đủ vị trí người chơi/);
});
test('explains proxy upload limits without trying to parse HTML', async () => {
  await assert.rejects(requestJson(new Response('<html>Too large</html>', {status:413}), 'Failed'), /giới hạn tải lên/);
});
test('explains authentication errors', async () => {
  await assert.rejects(requestJson(new Response('', {status:401}), 'Failed'), /đăng nhập/);
});
