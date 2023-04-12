from typing import Dict, List

from .contextual import Contextual
from .recommender import Recommender
from .toppop import TopPop, Random
from ..track import Track

FALLBACK_CNT = 10


class HWRecommender(Recommender):
    def __init__(self, track_redis, catalog, user_tracks, user_artists):
        self.track_redis = track_redis
        self.contextual_rec = Contextual(track_redis, catalog)
        self.top_rec = TopPop(track_redis, catalog.top_tracks[:100])
        self.random_rec = Random(track_redis)
        self.user_tracks: Dict[int, List[int]] = user_tracks
        self.user_artists: Dict[int, List[str]] = user_artists
        self.catalog = catalog

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:
        track_id = self.repeat(self.contextual_rec, user, prev_track, prev_track_time)
        if track_id is not None:
            return track_id

        track_id = self.repeat(self.top_rec, user, prev_track, prev_track_time)
        if track_id is not None:
            return track_id

        track_id = self.repeat(self.random_rec, user, prev_track, prev_track_time)
        if track_id is not None:
            return track_id

        track_id = self.random_rec.recommend_next(user, prev_track, prev_track_time)
        track: Track = self.catalog.from_bytes(self.track_redis.get(prev_track))
        self.user_tracks[user].append(track_id)
        self.user_artists[user].append(track.artist)
        return track_id

    def repeat(self, recommender: Recommender, user: int, prev_track: int, prev_track_time: float):
        fallback_cnt = FALLBACK_CNT
        while fallback_cnt:
            fallback_cnt -= 1
            track_id = recommender.recommend_next(user, prev_track, prev_track_time)
            if track_id in self.user_tracks[user]:
                continue
            track: Track = self.catalog.from_bytes(self.track_redis.get(prev_track))
            if track.artist in self.user_artists:
                continue
            self.user_tracks[user].append(track_id)
            self.user_artists[user].append(track.artist)
            return track_id

