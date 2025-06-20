import unittest
import os
from pathlib import Path
from .. import gif_util


class TestGifUtil(unittest.TestCase):

    def test_download_video_calls_yt_dlp_with_correct_args(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        save_path = "test_video.mp4"

        # Remove existing test file if any
        if os.path.exists(save_path):
            os.remove(save_path)

        # Call the real download_video (this will download the video)
        gif_util.download_video(url, save_path)

        # Assert the file was actually created (downloaded)
        self.assertTrue(os.path.exists(save_path))
        # Clean up test video file
        os.remove(save_path)

    def test_video_to_gif_generates_gif_correctly(self):
        # For this test, ensure a short sample video file named "sample_video.mp4" exists in the test directory
        video_path = os.path.join(os.path.dirname(__file__), "sample_video.mp4")
        output_path = "output.gif"
        start_time = 0
        duration = 3
        fps = 10

        if not os.path.exists(video_path):
            pytest.skip("Input video file 'sample_video.mp4' not found for integration test")

        gif_util.video_to_gif(video_path, output_path, start_time, duration, fps)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
        os.remove(output_path)  # Clean up

    def test_video_to_gif_handles_duration_overflow(self):
        input_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_video.mp4"))
        print("Checking path:", input_path)

        if not os.path.exists(input_path):
            pytest.skip(f"Input video file '{input_path}' not found for integration test")

        output_path = "output_overflow.gif"
        start_time = 1  # adjusted so it's < duration
        duration = 5    # will overflow if clip is shorter than start_time + duration

        if os.path.exists(output_path):
            os.remove(output_path)

        gif_util.video_to_gif(input_path, output_path, start_time, duration)

        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0


if __name__ == "__main__":
    unittest.main()
