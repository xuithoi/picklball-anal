from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AnalysisOptions(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    player_count: Literal[2, 4] = 4
    confidence: float = Field(default=0.3, ge=0.1, le=0.9)
    inference_stride: int = Field(default=2, ge=1, le=4)
    player_trails: bool = True
    heatmap_overlay: bool = False
    ball_tracking: bool = False
    ball_seed: tuple[float, float] | None = None
    ball_radius: int = Field(default=6, ge=2, le=30)
    ball_tolerance: int = Field(default=15, ge=5, le=40)

    @field_validator('ball_seed')
    @classmethod
    def normalized_seed(cls, value):
        if value is not None and any(v < 0 or v > 1 for v in value):
            raise ValueError('Vị trí bóng phải nằm trong khung hình.')
        return value

    @model_validator(mode='after')
    def require_ball_seed(self):
        if self.ball_tracking and self.ball_seed is None:
            raise ValueError('Hãy chọn tâm bóng trên khung hình đầu tiên.')
        return self
