import time
import unittest

from app.services import video_service


class StreamSelectionTests(unittest.TestCase):
    def setUp(self):
        self.url = "https://example.com/video"
        video_service._info_cache[self.url] = (
            time.time(),
            {
                "formats": [
                    {
                        "format_id": "audio",
                        "url": "https://cdn.example.com/audio.m4a",
                        "vcodec": "none",
                        "acodec": "mp4a.40.2",
                    },
                    {
                        "format_id": "muxed-720",
                        "url": "https://cdn.example.com/muxed-720.mp4",
                        "vcodec": "avc1",
                        "acodec": "mp4a.40.2",
                        "height": 720,
                        "http_headers": {"User-Agent": "Test UA"},
                    },
                    {
                        "format_id": "video-1080",
                        "url": "https://cdn.example.com/video-1080.mp4",
                        "vcodec": "avc1",
                        "acodec": "none",
                        "height": 1080,
                        "http_headers": {"User-Agent": "Video Only UA"},
                    },
                ]
            },
        )

        self.video_only_url = "https://example.com/video-only"
        video_service._info_cache[self.video_only_url] = (
            time.time(),
            {
                "formats": [
                    {
                        "format_id": "video-360",
                        "url": "https://cdn.example.com/video-360.mp4",
                        "vcodec": "avc1",
                        "acodec": "none",
                        "height": 360,
                        "http_headers": {"User-Agent": "Fallback UA"},
                    },
                    {
                        "format_id": "audio",
                        "url": "https://cdn.example.com/audio.m4a",
                        "vcodec": "none",
                        "acodec": "mp4a.40.2",
                    },
                ]
            },
        )

    def tearDown(self):
        video_service._info_cache.pop(self.url, None)
        video_service._info_cache.pop(self.video_only_url, None)

    def test_prefers_muxed_stream_for_preview(self):
        self.assertEqual(video_service.get_best_stream_format_id(self.url), "muxed-720")

    def test_falls_back_to_video_only_when_no_muxed_stream_exists(self):
        self.assertEqual(video_service.get_best_stream_format_id(self.video_only_url), "video-360")

    def test_returns_stream_headers_for_proxy_requests(self):
        stream_url, headers = video_service.get_stream_source(self.url, "video-1080")
        self.assertEqual(stream_url, "https://cdn.example.com/video-1080.mp4")
        self.assertEqual(headers["User-Agent"], "Video Only UA")


if __name__ == "__main__":
    unittest.main()
