const backendHint = "API phân tích chưa phản hồi đúng. Nếu dùng Cloudflare, cần kết nối /api tới backend Python/YOLO; chỉ triển khai giao diện sẽ không xử lý được video.";

export async function requestJson(response, fallback, validate = () => true) {
  if (response.status === 413)
    throw new Error("Video vượt giới hạn tải lên của máy chủ hoặc proxy. Hãy dùng video ngắn hơn.");
  if ([401, 403].includes(response.status))
    throw new Error("Bạn chưa có quyền truy cập API phân tích. Hãy đăng nhập lại hoặc kiểm tra quyền truy cập backend.");
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`${fallback} ${backendHint} (HTTP ${response.status})`);
  }
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : fallback;
    throw new Error(`${detail} (HTTP ${response.status})`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data) || !validate(data))
    throw new Error(`${fallback} ${backendHint}`);
  return data;
}
