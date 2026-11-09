from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnalysisOptions(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    player_count: Literal[2, 4] = 4
    player_names: list[str] | None = None
    confidence: float = Field(default=0.3, ge=0.1, le=0.9)
    inference_stride: int = Field(default=2, ge=1, le=4)
    player_trails: bool = True
    heatmap_overlay: bool = False
    ball_tracking: bool = False
    ball_seed: tuple[float, float] | None = None
    ball_radius: int = Field(default=6, ge=2, le=30)
    ball_tolerance: int = Field(default=15, ge=5, le=40)

    @field_validator('player_names')
    @classmethod
    def clean_names(cls, names):
        if names is None:
            return None
        cleaned = []
        for name in names:
            name = unicodedata.normalize('NFC', name.strip())
            if len(name) > 40 or any(unicodedata.category(c).startswith('C') for c in name):
                raise ValueError('Tên vận động viên tối đa 40 ký tự và không chứa ký tự điều khiển.')
            cleaned.append(name)
        return cleaned

    @field_validator('ball_seed')
    @classmethod
    def normalized_seed(cls, value):
        if value is not None and any(v < 0 or v > 1 for v in value):
            raise ValueError('Vị trí bóng phải nằm trong khung hình.')
        return value

    @model_validator(mode='after')
    def require_ball_seed(self):
        if self.player_names is not None and len(self.player_names) != self.player_count:
            raise ValueError('Số tên phải khớp số người chơi (2 hoặc 4).')
        self.player_names = [name or f'P{i+1}' for i, name in enumerate(self.player_names or [''] * self.player_count)]
        if self.ball_tracking and self.ball_seed is None:
            raise ValueError('Hãy chọn tâm bóng trên khung hình đầu tiên.')
        return self
