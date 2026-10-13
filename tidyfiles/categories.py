"""Dosya uzantılarının kategorilere eşlenmesi."""

# Kategori adı -> o kategoriye giren uzantılar (küçük harf, noktalı)
CATEGORIES: dict[str, frozenset[str]] = {
    "Görseller": frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".tiff", ".heic", ".avif"}),
    "Belgeler": frozenset({".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".md"}),
    "Videolar": frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv"}),
    "Müzik": frozenset({".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}),
    "Arşivler": frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}),
    "Kurulum": frozenset({".exe", ".msi", ".apk", ".dmg", ".iso"}),
    "Kod": frozenset({".py", ".js", ".ts", ".html", ".css", ".json", ".dart", ".java", ".kt", ".c", ".cpp", ".cs", ".sh"}),
}

FALLBACK_CATEGORY = "Diğer"

# Tarayıcıların henüz tamamlamadığı indirmeler gibi dokunulmaması gereken uzantılar
SKIPPED_EXTENSIONS = frozenset({".crdownload", ".part", ".tmp", ".download", ".partial"})


def category_for_extension(extension: str) -> str:
    """Uzantıya (örn. '.PNG') karşılık gelen kategori adını döndürür."""
    extension = extension.lower()
    for name, extensions in CATEGORIES.items():
        if extension in extensions:
            return name
    return FALLBACK_CATEGORY
