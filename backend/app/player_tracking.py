"""Separate detector admission from ByteTrack's identity association thresholds."""
def tracker_thresholds(confidence):
    return {
        'tracker_type': 'bytetrack',
        'track_high_thresh': confidence,
        'track_low_thresh': .1,
        'new_track_thresh': confidence,
        'track_buffer': 30,
        'match_thresh': .8,
        'fuse_score': True,
    }
