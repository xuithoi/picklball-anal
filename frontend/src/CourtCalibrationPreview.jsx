import React from 'react';
import { courtProjection } from './calibration.js';

export default function CourtCalibrationPreview({ corners }) {
  const project = courtProjection(corners);
  if (!project) return null;
  const kitchen = 7 / 44;
  const segments = [
    [[0, 0], [1, 0]], [[1, 0], [1, 1]], [[1, 1], [0, 1]], [[0, 1], [0, 0]],
    [[0, .5], [1, .5]], [[0, .5-kitchen], [1, .5-kitchen]], [[0, .5+kitchen], [1, .5+kitchen]],
    [[.5, 0], [.5, .5-kitchen]], [[.5, .5+kitchen], [.5, 1]],
  ];
  const net = project([.5, .5]);
  return <svg className="calibration-preview" viewBox="0 0 1 1" preserveAspectRatio="none" aria-label="Xem trước hiệu chỉnh vạch sân và lưới">
    {segments.map(([a,b],i) => {
      const [x1,y1] = project(a), [x2,y2] = project(b);
      return <line key={i} {...{x1,y1,x2,y2}} stroke={i === 4 ? '#73d8ea' : '#d5ff70'} strokeWidth={i === 4 ? 3 : 1.5} vectorEffect="non-scaling-stroke" />;
    })}
    <text x={net[0]} y={net[1]-.015} textAnchor="middle" fontSize=".025" fill="#73d8ea" stroke="#0c140d" strokeWidth=".004" paintOrder="stroke">LƯỚI</text>
  </svg>;
}
