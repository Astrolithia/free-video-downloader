import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.services.video_service import DOWNLOADS_DIR, DownloadTask, _tasks


class DownloadPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.video_path = DOWNLOADS_DIR / "playable-task.mp4"
        self.video_path.write_bytes(b"fake-video")

        _tasks["playable-task"] = DownloadTask(
            task_id="playable-task",
            url="https://example.com/video",
            title="sample",
            status="done",
            filename=str(self.video_path),
        )

    def tearDown(self):
        _tasks.pop("playable-task", None)
        if self.video_path.exists():
            self.video_path.unlink()

    def test_play_route_serves_inline_video(self):
        response = self.client.get("/api/play/playable-task")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertIn("inline", response.headers.get("content-disposition", ""))

    def test_play_route_falls_back_to_downloaded_file_when_task_cache_is_missing(self):
        _tasks.pop("playable-task", None)

        response = self.client.get("/api/play/playable-task")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "video/mp4")
        self.assertIn("inline", response.headers.get("content-disposition", ""))


if __name__ == "__main__":
    unittest.main()
