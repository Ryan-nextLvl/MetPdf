from pathlib import Path


def build_output_path(input_path: Path, output_dir: Path) -> Path:
    """Return a unique output PDF path inside output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / (input_path.stem + ".pdf")
    if not candidate.exists() or candidate.resolve() == input_path.resolve():
        return candidate
    # Avoid overwriting an existing file from a previous run with a different source.
    counter = 1
    while True:
        candidate = output_dir / f"{input_path.stem}_{counter}.pdf"
        if not candidate.exists():
            return candidate
        counter += 1


def collect_input_files(paths: list[Path], recursive: bool = False) -> list[Path]:
    """Expand directories to individual files; return plain files as-is."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(f for f in p.glob(pattern) if f.is_file())
        else:
            files.append(p)
    return files
