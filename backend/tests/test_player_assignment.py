import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from pydantic import ValidationError

from app.options import AnalysisOptions
from app.processor import bind_player_seeds


def test_assignment_follows_clicked_people_instead_of_detection_order():
    boxes = [[120, 10, 180, 100], [10, 10, 70, 100], [80, 110, 110, 190]]
    assert bind_player_seeds(boxes, [20, 10, 99], [(0.2, 0.25), (0.75, 0.25)], 200, 200) == {10: 1, 20: 2}


@pytest.mark.parametrize('seeds', [[(0.2, 0.25), (0.9, 0.9)], [(0.2, 0.25), (0.21, 0.26)]])
def test_missing_or_duplicate_detection_does_not_assign_another_person(seeds):
    with pytest.raises(ValueError, match='Không nhận diện đủ người'):
        bind_player_seeds([[10, 10, 70, 100], [120, 10, 180, 100]], [10, 20], seeds, 200, 200)


@pytest.mark.parametrize('seeds', [[], [[.1, .2]], [[-.1, .2], [.5, .5]], [[.1, .2], [.1, .2]], [[float('nan'), .2], [.5, .5]]])
def test_invalid_player_positions(seeds):
    with pytest.raises(ValidationError):
        AnalysisOptions(player_count=2, player_seeds=seeds)


def test_processor_keeps_names_bound_and_does_not_name_a_new_tracker(tmp_path, monkeypatch):
    from app import processor
    source = tmp_path / 'input.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (200, 200))
    for _ in range(3):
        writer.write(np.zeros((200, 200, 3), dtype=np.uint8))
    writer.release()
    calls = iter([
        ([20, 10], [[120, 10, 180, 100], [10, 10, 70, 100]]),
        ([10, 20], [[10, 10, 70, 100], [120, 10, 180, 100]]),
        ([99, 20], [[10, 10, 70, 100], [120, 10, 180, 100]]),
    ])
    def track(*args, **kwargs):
        ids, boxes = next(calls)
        return [SimpleNamespace(boxes=SimpleNamespace(id=torch.tensor(ids), xyxy=torch.tensor(boxes)))]
    monkeypatch.setattr(processor, 'YOLO', lambda *args: SimpleNamespace(track=track))
    out = tmp_path / 'output'
    out.mkdir()
    processor.process_video(source, out, None, lambda *args: None, {
        'player_count': 2, 'player_names': ['An', 'Bình'],
        'player_seeds': [[.2, .25], [.75, .25]], 'inference_stride': 1,
    })
    frames = json.loads((out / 'positions.json').read_text())
    for frame in frames[:2]:
        assert {p['track_id']: p['name'] for p in frame['players']} == {10: 'An', 20: 'Bình'}
    assert [(p['track_id'], p['name']) for p in frames[2]['players']] == [(20, 'Bình')]
