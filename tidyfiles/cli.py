"""Komut satırı arayüzü."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .organizer import apply_moves, plan_moves, undo_last


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tidyfiles",
        description="Karışık bir klasörü dosya türüne (ve isteğe bağlı tarihe) göre düzenler.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    organize = sub.add_parser("organize", help="Klasördeki dosyaları kategori klasörlerine taşır")
    organize.add_argument("folder", type=Path, help="Düzenlenecek klasör")
    organize.add_argument("--by-date", action="store_true", help="Kategori içinde YYYY-AA alt klasörleri oluşturur")
    organize.add_argument("--dry-run", action="store_true", help="Hiçbir şeyi taşımadan planı gösterir")

    undo = sub.add_parser("undo", help="Son düzenlemeyi geri alır")
    undo.add_argument("folder", type=Path, help="Daha önce düzenlenmiş klasör")
    return parser


def _run_organize(folder: Path, by_date: bool, dry_run: bool) -> int:
    moves = plan_moves(folder, by_date=by_date)
    if not moves:
        print("Düzenlenecek dosya bulunamadı.")
        return 0

    summary = Counter(move.destination.relative_to(folder).parts[0] for move in moves)
    for move in moves:
        print(f"  {move.source.name}  ->  {move.destination.relative_to(folder).as_posix()}")
    print()
    for category, count in sorted(summary.items()):
        print(f"{category}: {count} dosya")

    if dry_run:
        print("\nKuru çalıştırma: hiçbir dosya taşınmadı.")
        return 0

    moved = apply_moves(folder, moves)
    print(f"\n{moved} dosya taşındı. Geri almak için: tidyfiles undo \"{folder}\"")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "organize":
            return _run_organize(args.folder, args.by_date, args.dry_run)
        restored = undo_last(args.folder)
        print(f"{restored} dosya geri alındı." if restored else "Geri alınacak bir işlem yok.")
        return 0
    except NotADirectoryError as error:
        print(error, file=sys.stderr)
        return 1
