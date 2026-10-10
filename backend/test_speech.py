"""Real offline speech checks; run with python -m unittest backend.test_speech."""
from array import array
import io
import os
import unittest
import wave

from backend.speech import MAX_TEXT_LENGTH, speech_status, synthesize_wav


class SpeechValidationTests(unittest.TestCase):
    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            synthesize_wav("   ")

    def test_long_text_is_rejected(self):
        with self.assertRaises(ValueError):
            synthesize_wav("a" * (MAX_TEXT_LENGTH + 1))

    def test_invalid_speed_is_rejected(self):
        for speed in (0.1, 2.1, float("nan"), float("inf"), True, "fast"):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                synthesize_wav("This is local speech.", speed)


@unittest.skipUnless(os.name == "nt", "Windows SAPI is required")
class ActualWindowsSpeechTests(unittest.TestCase):
    def test_installed_voices_are_local(self):
        status = speech_status()
        self.assertTrue(status["available"], status.get("error"))
        self.assertTrue(status["offline"])
        self.assertTrue(status["voices"])
        self.assertTrue(all(voice["local"] for voice in status["voices"]))
        self.assertIn(status["default_voice"], [voice["name"] for voice in status["voices"]])

    def test_real_speech_is_nonempty_pcm(self):
        audio = synthesize_wav("Help. Yes. Learn. Every sign connects.")
        with wave.open(io.BytesIO(audio), "rb") as wav:
            self.assertEqual(wav.getcomptype(), "NONE")
            self.assertGreater(wav.getnframes() / wav.getframerate(), 1.0)
            pcm = wav.readframes(wav.getnframes())
            self.assertGreater(len(pcm), 1000)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertGreater(max(abs(value) for value in array("h", pcm)), 100)

    def test_speed_changes_actual_audio_duration(self):
        durations = []
        for rate in (0.7, 1.5):
            audio = synthesize_wav("Every sign connects.", rate=rate)
            with wave.open(io.BytesIO(audio), "rb") as wav:
                durations.append(wav.getnframes() / wav.getframerate())
        self.assertGreater(durations[0], durations[1] * 1.2)

    def test_unknown_voice_is_rejected(self):
        with self.assertRaises(ValueError):
            synthesize_wav("Hello.", voice="__not_an_installed_voice__")


if __name__ == "__main__":
    unittest.main()
