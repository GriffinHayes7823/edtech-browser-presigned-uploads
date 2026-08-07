import unittest

from lesson_asset_upload import idempotency_key


class IdempotencyKeyTest(unittest.TestCase):
    def test_same_upload_has_the_same_key(self) -> None:
        first = idempotency_key("presign", "lesson-assets", "lessons/algebra-101/notes.pdf")
        second = idempotency_key("presign", "lesson-assets", "lessons/algebra-101/notes.pdf")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
