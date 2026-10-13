"""Klasör düzenleme, planlama ve geri alma mantığı."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .categories import SKIPPED_EXTENSIONS, category_for_extension

LOG_NAME = ".tidyfiles-log.json"


@dataclass(frozen=True)
class Move:
    """Tek bir dosyanın taşınma planı."""

    source: Path
    destination: Path


def _is_candidate(path: Path) -> bool:
    """Düzenlenecek bir dosya mı? Klasörleri, gizli ve yarım dosyaları atlar."""
    return (
        path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() not in SKIPPED_EXTENSIONS
    )


def _unique_destination(destination: Path, reserved: set[Path]) -> Path:
    """Aynı isimde dosya varsa 'ad (1).uzantı' biçiminde boş bir yol bulur."""
    candidate = destination
    counter = 1
    while candidate.exists() or candidate in reserved:
        candidate = destination.with_name(f"{destination.stem} ({counter}){destination.suffix}")
        counter += 1
    return candidate


def plan_moves(root: Path, *, by_date: bool = False) -> list[Move]:
    """Klasörün doğrudan altındaki dosyalar için taşıma planı üretir (dosyaya dokunmaz)."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"Klasör bulunamadı: {root}")

    moves: list[Move] = []
    reserved: set[Path] = set()
    for path in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not _is_candidate(path):
            continue
        target_dir = root / category_for_extension(path.suffix)
        if by_date:
            target_dir /= datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m")
        destination = _unique_destination(target_dir / path.name, reserved)
        reserved.add(destination)
        moves.append(Move(path, destination))
    return moves


def _read_log(root: Path) -> list[dict]:
    log_path = root / LOG_NAME
    if not log_path.exists():
        return []
    return json.loads(log_path.read_text(encoding="utf-8"))


def _write_log(root: Path, runs: list[dict]) -> None:
    log_path = root / LOG_NAME
    if runs:
        log_path.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    elif log_path.exists():
        log_path.unlink()


def apply_moves(root: Path, moves: list[Move]) -> int:
    """Planı uygular ve geri alınabilmesi için kaydını tutar. Taşınan dosya sayısını döndürür."""
    root = Path(root)
    done: list[dict] = []
    for move in moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.source), str(move.destination))
        done.append(
            {
                "from": move.source.relative_to(root).as_posix(),
                "to": move.destination.relative_to(root).as_posix(),
            }
        )
    if done:
        runs = _read_log(root)
        runs.append({"time": datetime.now().isoformat(timespec="seconds"), "moves": done})
        _write_log(root, runs)
    return len(done)


def undo_last(root: Path) -> int:
    """Son düzenlemeyi geri alır. Geri taşınan dosya sayısını döndürür."""
    root = Path(root)
    runs = _read_log(root)
    if not runs:
        return 0

    last = runs.pop()
    restored = 0
    for entry in reversed(last["moves"]):
        current = root / entry["to"]
        original = root / entry["from"]
        if not current.exists():
            continue  # Kullanıcı dosyayı sonradan silmiş veya taşımış olabilir
        original = _unique_destination(original, set())
        shutil.move(str(current), str(original))
        restored += 1
        # Taşıma sonucu boşalan kategori klasörlerini temizle
        parent = current.parent
        while parent != root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    _write_log(root, runs)
    return restored
