import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import torch
from ultralytics.engine.results import Boxes
from ultralytics.trackers.byte_tracker import BYTETracker

from app import processor
from app.player_tracking import tracker_thresholds


def detections(rows):
    return Boxes(np.array(rows,dtype=np.float32).reshape(-1,6),orig_shape=(200,200))


def test_bytetrack_preserves_existing_identity_with_low_score_without_spawning_weak_new_people():
    tracker=BYTETracker(SimpleNamespace(**tracker_thresholds(.3)),frame_rate=30)
    strong=tracker.update(detections([[10,10,70,100,.9,0]]))
    assert len(strong)==1
    identity=int(strong[0,4])
    weak=tracker.update(detections([[12,10,72,100,.15,0],[130,110,180,190,.15,0]]))
    assert len(weak)==1 and int(weak[0,4])==identity
    tracker=BYTETracker(SimpleNamespace(**tracker_thresholds(.3)),frame_rate=30)
    assert len(tracker.update(detections([[10,10,70,100,.15,0]])))==0


def test_trace_distinguishes_changed_ids_from_no_tracker_output(tmp_path,monkeypatch):
    source=tmp_path/'in.mp4';out=tmp_path/'out';out.mkdir()
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(200,200))
    for _ in range(3):writer.write(np.zeros((200,200,3),np.uint8))
    writer.release()
    calls=iter([
        ([10,20],[[10,10,70,100],[120,10,180,100]]),
        ([99,20],[[10,10,70,100],[120,10,180,100]]),
        ([],[]),
    ])
    def track(frame,**kwargs):
        assert kwargs['conf']==.1
        config=json.loads(Path(kwargs['tracker']).read_text())
        assert config['track_high_thresh']==config['new_track_thresh']==.3
        ids,boxes=next(calls)
        return [SimpleNamespace(boxes=SimpleNamespace(id=torch.tensor(ids),xyxy=torch.tensor(boxes).reshape(-1,4)))]
    monkeypatch.setattr(processor,'YOLO',lambda *a:SimpleNamespace(track=track))
    processor.process_video(source,out,None,lambda *a:None,{
        'player_count':2,'player_names':['An','Bình'],'player_seeds':[[.2,.25],[.75,.25]],'inference_stride':1,
    })
    frames=json.loads((out/'positions.json').read_text())
    assert frames[0]['tracking']['missing_players']==[]
    assert frames[1]['tracking']['track_output_count']==2
    assert frames[1]['tracking']['unassigned_track_ids']==[99]
    assert frames[1]['tracking']['missing_players']==[{'player':'P1','name':'An'}]
    assert frames[2]['tracking']['track_output_count']==0
    assert len(frames[2]['tracking']['missing_players'])==2
    summary=json.loads((out/'summary.json').read_text())
    assert summary['tracking']['complete_frames']==1
    assert summary['tracking']['missing_frames']==2
    assert summary['tracking']['unassigned_track_ids']==[99]
    assert summary['tracking']['players'][0]['observed_inference_frames']==1
    assert summary['tracking']['players'][1]['observed_inference_frames']==2
    assert any('chưa gán' in w for w in summary['warnings'])
    assert not (out/'player_tracker.yaml').exists()
