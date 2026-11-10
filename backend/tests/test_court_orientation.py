import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
import torch
from pydantic import ValidationError

from app import processor
from app.options import AnalysisOptions
from app.overlays import CourtOverlay, W, H

# Court seen sideways, like the reported view: image 1-3 and 2-4 are baselines.
CORNERS = [[.02, .16], [.69, .07], [.94, .34], [.35, .99]]


def on_segment(point, a, b, tolerance=1.5):
    a, b, point = map(np.array, (a, b, point))
    distance = abs(np.linalg.det(np.array([b-a, point-a]))) / np.linalg.norm(b-a)
    assert distance <= tolerance
    fraction = np.dot(point-a, b-a)/np.dot(b-a, b-a)
    assert 0 <= fraction <= 1


def test_sideways_net_joins_image_top_and_bottom_edges_and_positions_share_transform():
    width, height = 860, 480
    overlay = CourtOverlay(width, height, CORNERS, court_orientation='left_right')
    image = np.float32([[x*width, y*height] for x,y in CORNERS])
    net = overlay.projected_lines[4]
    on_segment(net[0], image[0], image[1])
    on_segment(net[1], image[3], image[2])
    # Both image-left corners are on the near baseline; both right corners are far.
    points = cv2.perspectiveTransform(image.reshape(-1,1,2), overlay.image_to_court).reshape(-1,2)
    assert np.allclose(points, [[0,H-1],[0,0],[W-1,0],[W-1,H-1]], atol=.001)
    assert CourtOverlay(width,height,CORNERS).projected_lines[4].tolist() != net.tolist()


def test_invalid_orientation_is_rejected():
    with pytest.raises(ValidationError):
        AnalysisOptions(court_orientation='auto')
    with pytest.raises(ValueError):
        CourtOverlay(640,480,CORNERS,court_orientation='auto')


@pytest.mark.parametrize('orientation', ['top_bottom', 'left_right'])
def test_processing_uses_selected_axis_for_each_named_player(tmp_path, monkeypatch, orientation):
    width, height = 640, 480
    overlay = CourtOverlay(width,height,CORNERS,court_orientation=orientation)
    expected = np.float32([[[80,720]],[[300,180]]])
    feet = cv2.perspectiveTransform(expected,np.linalg.inv(overlay.image_to_court)).reshape(-1,2)
    boxes = [[x-12,y-40,x+12,y] for x,y in feet]
    ids = [11,22]
    # Detector order intentionally reversed: assignment must follow clicked athletes.
    result = SimpleNamespace(boxes=SimpleNamespace(xyxy=torch.tensor(boxes[::-1]),id=torch.tensor(ids[::-1])))
    monkeypatch.setattr(processor,'YOLO',lambda *a:SimpleNamespace(track=lambda *a,**kw:[result]))
    source=tmp_path/'input.mp4'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(width,height))
    for _ in range(4):writer.write(np.zeros((height,width,3),np.uint8))
    writer.release()
    out=tmp_path/'output';out.mkdir()
    processor.process_video(source,out,CORNERS,lambda *a:None,{
        'player_count':2,'player_names':['BoBo','Lân Quân'],
        'player_seeds':[[(x1+x2)/2/width,(y1+y2)/2/height] for x1,y1,x2,y2 in boxes],
        'minimap_overlay':True,'court_lines':True,'court_orientation':orientation,
    })
    frames=json.loads((out/'positions.json').read_text())
    for frame in frames:
        by_name={p['name']:p for p in frame['players']}
        assert by_name['BoBo']['player']=='P1' and by_name['Lân Quân']['player']=='P2'
        assert np.allclose(by_name['BoBo']['court_xy'],expected[0,0],atol=.01)
        assert np.allclose(by_name['Lân Quân']['court_xy'],expected[1,0],atol=.01)
    summary=json.loads((out/'summary.json').read_text())
    assert summary['calibration']['court_orientation']==orientation


def test_teammates_on_same_end_do_not_split_across_minimap_halves():
    # Reproduces the report's pattern: players have very different image y, but
    # share one physical end of a sideways court. Image-y is not court length.
    width, height = 860, 480
    correct = CourtOverlay(width,height,CORNERS,court_orientation='left_right')
    old_axis = CourtOverlay(width,height,CORNERS)
    expected = np.float32([[[100,650]],[[300,700]]])
    feet = cv2.perspectiveTransform(expected,np.linalg.inv(correct.image_to_court))
    wrong = cv2.perspectiveTransform(feet,old_axis.image_to_court).reshape(-1,2)
    assert wrong[0,1] < H/2 < wrong[1,1]
    observations=[]
    for slot, foot in enumerate(feet[:,0],1):
        point = cv2.perspectiveTransform(np.float32([[foot]]),correct.image_to_court)[0,0]
        assert point[1] > H/2
        observations.append({'player':f'P{slot}','court_xy':point})
    correct.update(observations)
    frame=np.zeros((height,width,3),np.uint8)
    correct.draw_minimap(frame,animated=False)
    assert all(correct.map_point(o['court_xy'])[1]>correct.map_point([0,H/2])[1] for o in observations)
    correct.update_ball(tuple(feet[0,0]))
    assert np.allclose(correct.ball_current,expected[0,0],atol=.001)
