import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tidyfiles.categories import category_for_extension
from tidyfiles.cli import main
from tidyfiles.organizer import LOG_NAME, apply_moves, plan_moves, undo_last


def touch(path: Path, content: str = "x", mtime: datetime | None = None) -> Path:
    path.write_text(content, encoding="utf-8")
    if mtime:
        stamp = mtime.timestamp()
        os.utime(path, (stamp, stamp))
    return path


class CategoryTests(unittest.TestCase):
    def test_known_extension_is_case_insensitive(self):
        self.assertEqual(category_for_extension(".PNG"), "Görseller")

    def test_unknown_extension_falls_back(self):
        self.assertEqual(category_for_extension(".xyz"), "Diğer")


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_files_are_moved_into_category_folders(self):
        touch(self.root / "a.png")
        touch(self.root / "b.pdf")
        apply_moves(self.root, plan_moves(self.root))
        self.assertTrue((self.root / "Görseller" / "a.png").exists())
        self.assertTrue((self.root / "Belgeler" / "b.pdf").exists())

    def test_dry_run_plan_does_not_touch_files(self):
        touch(self.root / "a.png")
        plan_moves(self.root)
        self.assertTrue((self.root / "a.png").exists())

    def test_hidden_and_partial_files_and_folders_are_skipped(self):
        touch(self.root / ".gizli.txt")
        touch(self.root / "indirme.crdownload")
        (self.root / "klasor").mkdir()
        self.assertEqual(plan_moves(self.root), [])

    def test_name_conflict_gets_numbered_suffix(self):
        (self.root / "Görseller").mkdir()
        touch(self.root / "Görseller" / "a.png", "eski")
        touch(self.root / "a.png", "yeni")
        apply_moves(self.root, plan_moves(self.root))
        self.assertEqual((self.root / "Görseller" / "a.png").read_text(encoding="utf-8"), "eski")
        self.assertEqual((self.root / "Görseller" / "a (1).png").read_text(encoding="utf-8"), "yeni")

    def test_by_date_creates_month_subfolder(self):
        touch(self.root / "a.png", mtime=datetime(2025, 3, 14))
        apply_moves(self.root, plan_moves(self.root, by_date=True))
        self.assertTrue((self.root / "Görseller" / "2025-03" / "a.png").exists())

    def test_undo_restores_files_and_removes_empty_folders(self):
        touch(self.root / "a.png", "icerik")
        apply_moves(self.root, plan_moves(self.root))
        restored = undo_last(self.root)
        self.assertEqual(restored, 1)
        self.assertEqual((self.root / "a.png").read_text(encoding="utf-8"), "icerik")
        self.assertFalse((self.root / "Görseller").exists())
        self.assertFalse((self.root / LOG_NAME).exists())

    def test_undo_without_history_returns_zero(self):
        self.assertEqual(undo_last(self.root), 0)

    def test_undo_skips_files_removed_after_organizing(self):
        touch(self.root / "a.png")
        touch(self.root / "b.pdf")
        apply_moves(self.root, plan_moves(self.root))
        (self.root / "Görseller" / "a.png").unlink()
        self.assertEqual(undo_last(self.root), 1)
        self.assertTrue((self.root / "b.pdf").exists())

    def test_missing_folder_raises(self):
        with self.assertRaises(NotADirectoryError):
            plan_moves(self.root / "yok")


class CliTests(unittest.TestCase):
    def test_organize_and_undo_through_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root / "a.mp3")
            self.assertEqual(main(["organize", str(root), "--dry-run"]), 0)
            self.assertTrue((root / "a.mp3").exists())
            self.assertEqual(main(["organize", str(root)]), 0)
            self.assertTrue((root / "Müzik" / "a.mp3").exists())
            self.assertEqual(main(["undo", str(root)]), 0)
            self.assertTrue((root / "a.mp3").exists())

    def test_missing_folder_returns_error_code(self):
        self.assertEqual(main(["organize", "bu-klasor-yok-123"]), 1)


def run_cli(*argv: str) -> tuple[int, str]:
    """Komutu çalıştırır; çıkış kodunu ve ekrana yazılan metni döndürür."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


class CliOutputTests(unittest.TestCase):
    def test_empty_folder_reports_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output = run_cli("organize", tmp)
        self.assertEqual(code, 0)
        self.assertIn("Düzenlenecek dosya bulunamadı.", output)

    def test_dry_run_prints_plan_and_summary_without_moving(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root / "rapor.pdf")
            touch(root / "not.txt")
            touch(root / "a.mp3")
            code, output = run_cli("organize", tmp, "--dry-run")

            self.assertEqual(code, 0)
            self.assertIn("rapor.pdf  ->  Belgeler/rapor.pdf", output)
            self.assertIn("Belgeler: 2 dosya", output)
            self.assertIn("Müzik: 1 dosya", output)
            self.assertIn("Kuru çalıştırma: hiçbir dosya taşınmadı.", output)
            self.assertTrue((root / "rapor.pdf").exists())
            self.assertFalse((root / LOG_NAME).exists())

    def test_by_date_destination_is_shown_in_the_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            touch(Path(tmp) / "a.mp3", mtime=datetime(2026, 9, 18))
            _, output = run_cli("organize", tmp, "--by-date", "--dry-run")
        self.assertIn("a.mp3  ->  Müzik/2026-09/a.mp3", output)

    def test_second_undo_reports_nothing_to_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            touch(Path(tmp) / "a.mp3")
            run_cli("organize", tmp)
            _, first = run_cli("undo", tmp)
            code, second = run_cli("undo", tmp)

        self.assertIn("1 dosya geri alındı.", first)
        self.assertEqual(code, 0)
        self.assertIn("Geri alınacak bir işlem yok.", second)


if __name__ == "__main__":
    unittest.main()
