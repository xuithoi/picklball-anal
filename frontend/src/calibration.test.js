import test from 'node:test';
import assert from 'node:assert/strict';
import { validCorners, courtProjection, orderedCourtCorners } from './calibration.js';
const corners = [[.3,.1],[.75,.14],[.9,.9],[.1,.85]];
test('rejects reversed and cyclically shifted corner clicks', () => {
  assert.ok(validCorners(corners));
  for(let i=0;i<4;i++) {
    const shifted=[...corners.slice(i),...corners.slice(0,i)];
    if(i) assert.equal(validCorners(shifted),false);
    assert.equal(validCorners([...shifted].reverse()),false);
  }
  assert.equal(validCorners([[0,0],[1,1],[1,0],[0,1]]),false);
  assert.equal(validCorners([[0,0],[1,0],[1,0],[0,1]]),false);
});
test('perspective preview matches calibrated corners and straight net', () => {
  const project=courtProjection(corners);
  [[0,0],[1,0],[1,1],[0,1]].forEach((p,i)=>project(p).forEach((v,j)=>assert.ok(Math.abs(v-corners[i][j])<1e-9)));
  const [a,b,c]=[[0,.5],[.5,.5],[1,.5]].map(project);
  assert.ok(Math.abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))<1e-9);
  assert.ok(project([.1,.9])[1]>project([.9,.6])[1]);
  assert.equal(courtProjection([...corners].reverse()),null);
});

test('two-row UI corners are converted once to the API clockwise order', () => {
  const clicks=[corners[0],corners[1],corners[3],corners[2]];
  assert.deepEqual(orderedCourtCorners(clicks),corners);
  assert.ok(validCorners(orderedCourtCorners(clicks)));
  assert.deepEqual(orderedCourtCorners(clicks.slice(0,2)),clicks.slice(0,2));
});

test('sideways court net joins the top/bottom image edges and shares player coordinates', () => {
  const corners=[[.02,.16],[.69,.07],[.94,.34],[.35,.99]];
  const project=courtProjection(corners,'left_right');
  const expected=[corners[1],corners[2],corners[3],corners[0]];
  [[0,0],[1,0],[1,1],[0,1]].forEach((p,i)=>project(p).forEach((v,j)=>assert.ok(Math.abs(v-expected[i][j])<1e-9)));
  const onSegment=(point,a,b)=>{
    const cross=(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]);
    assert.ok(Math.abs(cross)<1e-9);
    assert.ok(point[0]>=Math.min(a[0],b[0])&&point[0]<=Math.max(a[0],b[0]));
  };
  onSegment(project([0,.5]),corners[0],corners[1]);
  onSegment(project([1,.5]),corners[3],corners[2]);
  assert.equal(courtProjection(corners,'auto'),null);
});
