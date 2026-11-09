"""Stream decoded frames from a source timestamp without a second temporary video."""
import subprocess
import tempfile

import numpy as np


class TimestampDecoder:
    def __init__(self, path, start_time, width, height):
        self.width, self.height = width, height
        self.errors = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen([
                'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-threads', '1', '-ss', f'{start_time:.6f}', '-i', str(path),
                '-map', '0:v:0', '-an', '-sn', '-dn', '-fps_mode', 'passthrough',
                '-threads', '1', '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1',
            ], stdout=subprocess.PIPE, stderr=self.errors)
        except OSError as exc:
            self.errors.close()
            raise RuntimeError('Cần FFmpeg để bắt đầu phân tích từ khung hình đã chọn.') from exc

    def read(self):
        data = self.process.stdout.read(self.width * self.height * 3)
        if not data:
            if self.process.wait(timeout=10) != 0:
                raise RuntimeError('FFmpeg không đọc được video tại thời điểm đã chọn. Hãy chọn lại khung hình hoặc dùng MP4 H.264.')
            return False, None
        if len(data) != self.width * self.height * 3:
            raise RuntimeError('Video bị lỗi khi đọc khung hình đã chọn.')
        return True, np.frombuffer(data, np.uint8).reshape(self.height, self.width, 3).copy()

    def close(self):
        self.process.stdout.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.errors.close()
