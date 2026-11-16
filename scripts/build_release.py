"""Build the release files of the fork from the fonts exported under `Sans/fonts/`.

Usage: build_release.py <version> [--source Sans/fonts] [--mono Mono] [--output dist]

Every TrueType font that carries the tabular feature is copied with that feature narrowed to
the digits, no kerning on tabular digits, and `<version>` appended to its version string. A
style DM Mono also draws takes the tabular digits of DM Mono and its copyright notice. The
PostScript-flavoured `.otf` files and the fonts exported without the feature are left out, so
each style of the release has one drawing of its digits. The output folder mirrors the source
folder and gains `DMSans-<version>.zip` with every font built, the two licenses and the notes.
"""

import argparse
import shutil
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont

from tabular_digits import has_tabular_feature, make_digits_tabular_only, mono_file_for

FONT_SUFFIXES = {".ttf", ".otf", ".woff2"}
COPYRIGHT_NAME_ID = 0
VERSION_NAME_ID = 5
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
LICENSE_FILE = REPOSITORY_ROOT / "Sans" / "OFL.txt"
MONO_LICENSE_NAME = "OFL-DMMono.txt"
NOTES_FILE = REPOSITORY_ROOT / "FONTLOG.txt"


def stamp_names(font: TTFont, mono: TTFont | None, version: str) -> None:
    """Add the release version, and the DM Mono copyright notice when its digits are in the font."""
    mono_copyright = None if mono is None else mono["name"].getDebugName(COPYRIGHT_NAME_ID)
    for record in font["name"].names:
        if record.nameID == COPYRIGHT_NAME_ID and mono_copyright is not None:
            record.string = f"{record.toUnicode()}. Tabular digits: {mono_copyright}"
        elif record.nameID == VERSION_NAME_ID:
            record.string = f"{record.toUnicode()};lawnstarter {version}"


def build_font(source: Path, target: Path, mono_folder: Path, version: str) -> bool:
    """Build one font. Returns False, writing nothing, for a font the release leaves out."""
    font = TTFont(source)
    if "glyf" not in font or not has_tabular_feature(font):
        return False
    mono_file = mono_file_for(font)
    mono = None if mono_file is None else TTFont(mono_folder / mono_file)
    make_digits_tabular_only(font, mono)
    stamp_names(font, mono, version)
    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(target)
    return True


def build(version: str, source: Path, mono_folder: Path, output: Path) -> list[Path]:
    """Build the fonts under `source` into `output` and zip the result. Returns the fonts built."""
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    built = []
    for font_path in sorted(path for path in source.rglob("*") if path.suffix in FONT_SUFFIXES):
        target = output / font_path.relative_to(source)
        if build_font(font_path, target, mono_folder, version):
            built.append(target)
    if not built:
        raise SystemExit(f"no TrueType font with the tabular feature found under {source}")
    shutil.copy(LICENSE_FILE, output / LICENSE_FILE.name)
    shutil.copy(mono_folder / "OFL.txt", output / MONO_LICENSE_NAME)
    shutil.copy(NOTES_FILE, output / NOTES_FILE.name)
    archive = output / f"DMSans-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path != archive:
                bundle.write(path, path.relative_to(output))
    return built


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="the release version, such as 1.2.0")
    parser.add_argument("--source", type=Path, default=REPOSITORY_ROOT / "Sans" / "fonts")
    parser.add_argument("--mono", type=Path, default=REPOSITORY_ROOT / "Mono")
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "dist")
    arguments = parser.parse_args()
    built = build(arguments.version, arguments.source, arguments.mono, arguments.output)
    print(f"built {len(built)} fonts into {arguments.output}")


if __name__ == "__main__":
    main()
