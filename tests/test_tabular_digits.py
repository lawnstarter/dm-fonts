"""The release fonts against the fonts they are built from, shaped with HarfBuzz."""

import itertools
import math
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
import uharfbuzz as hb
from fontTools.misc.roundTools import otRound
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

from build_release import COPYRIGHT_NAME_ID, FONT_SUFFIXES, VERSION_NAME_ID, build
from tabular_digits import DIGITS as DIGIT_NAMES
from tabular_digits import has_tabular_feature

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Sans" / "fonts"
MONO = ROOT / "Mono"
VERSION = "0.0.0-test"
DIGITS = "0123456789"
TABULAR_ADVANCE = 600
# The ends of each axis of the variable fonts, plus the two weights Design sets numbers in.
WEIGHTS = (100, 400, 500, 1000)
OPTICAL_SIZES = (9, 14, 40)
SAMPLES = ["$1,050.00", "$1,111.11", "Nov 16 · 10:45", "AV To 7.1; Type 4,7", "fi fl 1/2 3rd"]
# The styles DM Mono also draws, each with the DM Mono file its tabular digits come from.
MONO_STYLES = {
    "Light": "DMMono-Light.ttf",
    "Regular": "DMMono-Regular.ttf",
    "Medium": "DMMono-Medium.ttf",
    "LightItalic": "DMMono-LightItalic.ttf",
    "Italic": "DMMono-Italic.ttf",
    "MediumItalic": "DMMono-MediumItalic.ttf",
}
MONO_FONTS = {
    f"{folder}/DMSans-{style}.{suffix}": mono_file
    for style, mono_file in MONO_STYLES.items()
    for folder, suffix in (("ttf", "ttf"), ("webfonts", "woff2"))
}
# Styles DM Mono does not draw, which keep the tabular digits of upstream.
UPSTREAM_FONTS = [
    "ttf/DMSans-Thin.ttf",
    "ttf/DMSans-SemiBold.ttf",
    "ttf/DMSans-Bold.ttf",
    "ttf/DMSans-BoldItalic.ttf",
    "ttf/DMSans-Black.ttf",
    "variable/DMSans[opsz,wght].ttf",
    "variable/DMSans-Italic[opsz,wght].ttf",
]
EACH_MONO_FONT = pytest.mark.parametrize("name", list(MONO_FONTS))
EACH_UPSTREAM_FONT = pytest.mark.parametrize("name", UPSTREAM_FONTS)
EACH_SAMPLED_FONT = pytest.mark.parametrize("name", list(MONO_FONTS) + UPSTREAM_FONTS)


@pytest.fixture(scope="session")
def release(tmp_path_factory) -> Path:
    output = tmp_path_factory.mktemp("dist")
    build(VERSION, SOURCE, MONO, output)
    return output


def fonts_under(folder: Path) -> list[str]:
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.suffix in FONT_SUFFIXES)


def instances(path: Path) -> list[dict[str, float]]:
    """The axis locations to shape a font at: one for a static font, a grid for a variable one."""
    if "fvar" not in TTFont(path):
        return [{}]
    return [
        {"wght": weight, "opsz": optical_size}
        for weight, optical_size in itertools.product(WEIGHTS, OPTICAL_SIZES)
    ]


def load(path: Path, location: dict[str, float] | None = None) -> hb.Font:
    # HarfBuzz reads sfnt data, so a woff2 is decompressed through fontTools first.
    if path.suffix == ".woff2":
        source = TTFont(path)
        source.flavor = None
        buffer = BytesIO()
        source.save(buffer)
        font = hb.Font(hb.Face(buffer.getvalue()))
    else:
        font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    if location:
        font.set_variations(location)
    return font


def shape(font: hb.Font, text: str, tabular: bool, also: tuple[str, ...] = ()):
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    features = {tag: True for tag in also}
    if tabular:
        features["tnum"] = True
    hb.shape(font, buffer, features)
    return [
        (font.glyph_to_string(info.codepoint), position.x_advance, position.x_offset)
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions)
    ]


def outline(font: TTFont, name: str):
    glyph_set = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.value


def lean(recorded) -> float:
    """How far a glyph leans: the run from its lowest points to its highest ones, over the rise."""
    points = [point for _, group in recorded for point in group]
    top, bottom = max(y for _, y in points), min(y for _, y in points)
    top_x = [x for x, y in points if y == top]
    bottom_x = [x for x, y in points if y == bottom]
    return (sum(top_x) / len(top_x) - sum(bottom_x) / len(bottom_x)) / (top - bottom)


def test_the_release_holds_every_truetype_font_with_the_tabular_feature(release):
    expected = [
        name
        for name in fonts_under(SOURCE)
        if "glyf" in TTFont(SOURCE / name) and has_tabular_feature(TTFont(SOURCE / name))
    ]
    built = fonts_under(release)
    assert built == expected
    assert set(MONO_FONTS) | set(UPSTREAM_FONTS) <= set(built)
    assert not [name for name in built if name.endswith(".otf")]


@EACH_MONO_FONT
def test_tabular_digits_one_to_nine_are_the_dm_mono_outlines(release, name):
    font, mono = TTFont(release / name), TTFont(MONO / MONO_FONTS[name])
    for digit in DIGIT_NAMES[1:]:
        assert outline(font, f"{digit}.tf") == outline(mono, digit), digit
        assert font["hmtx"][f"{digit}.tf"] == mono["hmtx"][digit], digit


@EACH_MONO_FONT
def test_tabular_zero_is_the_plain_zero_at_the_dm_mono_width(release, name):
    font, upstream = TTFont(release / name), TTFont(SOURCE / name)
    x_scale = TABULAR_ADVANCE / upstream["hmtx"]["zero"][0]
    # An italic zero is narrowed along its slant, so it leans as the digits beside it do.
    slant = math.tan(math.radians(-upstream["post"].italicAngle))
    narrowed = [
        (operator, tuple((otRound(x * x_scale + (1 - x_scale) * slant * y), y) for x, y in points))
        for operator, points in outline(upstream, "zero")
    ]
    assert outline(font, "zero.tf") == narrowed
    assert font["hmtx"]["zero.tf"][0] == TABULAR_ADVANCE
    assert sum(1 for operator, _ in narrowed if operator == "closePath") == 2
    assert lean(outline(font, "zero.tf")) == pytest.approx(lean(outline(upstream, "zero")), abs=0.01)


@EACH_UPSTREAM_FONT
def test_a_style_dm_mono_does_not_draw_keeps_the_upstream_tabular_digits(release, name):
    font, upstream = TTFont(release / name), TTFont(SOURCE / name)
    for digit in DIGIT_NAMES:
        assert outline(font, f"{digit}.tf") == outline(upstream, f"{digit}.tf"), digit


def test_digit_pairs_share_one_advance_in_every_font(release):
    for name in fonts_under(release):
        for location in instances(release / name):
            font = load(release / name, location)
            for first, second in itertools.product(DIGITS, repeat=2):
                glyphs = shape(font, first + second, tabular=True)
                widths = [(advance, offset) for _, advance, offset in glyphs]
                assert widths == [(TABULAR_ADVANCE, 0)] * 2, f"{first}{second} in {name} at {location}"


def test_the_tabular_zero_is_plain_in_every_font(release):
    for name in fonts_under(release):
        font = TTFont(release / name)
        (glyph_name, _, _), = shape(load(release / name), "0", tabular=True)
        contours = sum(1 for operator, _ in outline(font, glyph_name) if operator == "closePath")
        assert contours == 2, name


@EACH_SAMPLED_FONT
@pytest.mark.parametrize("also", [(), ("ss09",), ("zero",)], ids=["tnum", "tnum+ss09", "tnum+zero"])
def test_no_glyph_kerns_against_a_tabular_digit(release, name, also):
    codepoints = sorted(TTFont(release / name).getBestCmap())
    for location in instances(release / name):
        font = load(release / name, location)
        for codepoint, digit in itertools.product(codepoints, DIGITS):
            character = chr(codepoint)
            where = f"{character!r} and {digit} at {location}"
            alone = shape(font, character, True, also)
            before = shape(font, character + digit, True, also)
            after = shape(font, digit + character, True, also)
            assert before[: len(alone)] == alone, where
            assert before[-1][1:] == (TABULAR_ADVANCE, 0), where
            assert after[0][1:] == (TABULAR_ADVANCE, 0), where


def test_punctuation_keeps_its_width_in_every_font(release):
    for name in fonts_under(release):
        for location in instances(release / name):
            font = load(release / name, location)
            for character in " .,:;":
                assert shape(font, character, True) == shape(font, character, False), name


@EACH_SAMPLED_FONT
def test_shaping_is_unchanged_without_tnum(release, name):
    for location in instances(release / name):
        built, upstream = load(release / name, location), load(SOURCE / name, location)
        for sample in SAMPLES + [a + b for a, b in itertools.product(DIGITS, repeat=2)]:
            assert shape(built, sample, tabular=False) == shape(upstream, sample, tabular=False)


@EACH_MONO_FONT
def test_proportional_digits_keep_their_outlines(release, name):
    font, upstream = TTFont(release / name), TTFont(SOURCE / name)
    for digit in DIGIT_NAMES:
        assert outline(font, digit) == outline(upstream, digit), digit


def test_names_carry_the_release_version_and_the_copyrights(release):
    for name in fonts_under(release):
        font, upstream = TTFont(release / name), TTFont(SOURCE / name)
        names = font["name"].names
        versions = {record.toUnicode() for record in names if record.nameID == VERSION_NAME_ID}
        copyrights = {record.toUnicode() for record in names if record.nameID == COPYRIGHT_NAME_ID}
        own_copyright = upstream["name"].getDebugName(COPYRIGHT_NAME_ID)
        assert versions and all(v.endswith(f";lawnstarter {VERSION}") for v in versions), name
        assert font["name"].getDebugName(1) == upstream["name"].getDebugName(1), name
        if name in MONO_FONTS:
            mono_copyright = TTFont(MONO / MONO_FONTS[name])["name"].getDebugName(COPYRIGHT_NAME_ID)
            assert copyrights and all(
                own_copyright in notice and mono_copyright in notice for notice in copyrights
            ), name
        else:
            assert copyrights == {own_copyright}, name


def test_the_archive_holds_every_font_the_licenses_and_the_notes(release):
    with zipfile.ZipFile(release / f"DMSans-{VERSION}.zip") as bundle:
        names = set(bundle.namelist())
    assert set(fonts_under(release)) | {"OFL.txt", "OFL-DMMono.txt", "FONTLOG.txt"} == names
