export const cornerNames = ["Trên trái · phía xa", "Trên phải · phía xa", "Dưới trái · phía gần", "Dưới phải · phía gần"];

// Click in reading order (1/2 far end, 3/4 near end); API uses clockwise TL/TR/BR/BL.
export const orderedCourtCorners = points => points.length === 4 ? [points[0], points[1], points[3], points[2]] : points;
export const cornerError = "Chọn lại 4 góc ngoài của toàn sân: 1 trên trái → 2 trên phải → 3 dưới trái → 4 dưới phải. Không dùng góc lưới hoặc vùng bếp.";

export function validCorners(points) {
  if (points.length !== 4 || points.some(p => p.length !== 2 || p.some(v => !Number.isFinite(v) || v < 0 || v > 1))) return false;
  const [tl, tr, br, bl] = points;
  if (!(tl[0] < tr[0] && bl[0] < br[0] && tl[1] < bl[1] && tr[1] < br[1])) return false;
  let area = 0;
  for (let i = 0; i < 4; i++) {
    const a = points[i], b = points[(i + 1) % 4], c = points[(i + 2) % 4];
    if ((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0) return false;
    area += a[0] * b[1] - a[1] * b[0];
  }
  return area / 2 >= .005;
}

// Solve the same projective geometry as the backend, in normalized image space.
export function courtProjection(corners) {
  if (!validCorners(corners)) return null;
  const unit = [[0, 0], [1, 0], [1, 1], [0, 1]];
  const rows = unit.flatMap(([u, v], i) => {
    const [x, y] = corners[i];
    return [[u, v, 1, 0, 0, 0, -u*x, -v*x, x], [0, 0, 0, u, v, 1, -u*y, -v*y, y]];
  });
  for (let column = 0; column < 8; column++) {
    let pivot = column;
    for (let row = column + 1; row < 8; row++) if (Math.abs(rows[row][column]) > Math.abs(rows[pivot][column])) pivot = row;
    [rows[column], rows[pivot]] = [rows[pivot], rows[column]];
    const divisor = rows[column][column];
    if (Math.abs(divisor) < 1e-12) return null;
    rows[column] = rows[column].map(v => v / divisor);
    for (let row = 0; row < 8; row++) {
      if (row === column) continue;
      const factor = rows[row][column];
      rows[row] = rows[row].map((v, i) => v - factor * rows[column][i]);
    }
  }
  const h = rows.map(row => row[8]);
  return ([u, v]) => {
    const denominator = h[6]*u + h[7]*v + 1;
    return [(h[0]*u + h[1]*v + h[2])/denominator, (h[3]*u + h[4]*v + h[5])/denominator];
  };
}
