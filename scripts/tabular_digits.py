"""Make the `tnum` feature of DM Sans change the digits alone, to the digits of DM Mono."""

import math

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

DIGITS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
# Every glyph a digit can become while `tnum` is on: its tabular form, the slashed zero of the
# `zero` feature and the alternates of `ss09`.
TABULAR_DIGITS = frozenset(f"{digit}.tf" for digit in DIGITS) | {
    "zero.tf.zero",
    "three.ss09",
    "four.ss09",
    "six.ss09",
    "nine.ss09",
}
# The DM Mono file that carries the digits of each DM Sans style, by weight and slant.
MONO_STYLES = {
    (300, False): "DMMono-Light.ttf",
    (400, False): "DMMono-Regular.ttf",
    (500, False): "DMMono-Medium.ttf",
    (300, True): "DMMono-LightItalic.ttf",
    (400, True): "DMMono-Italic.ttf",
    (500, True): "DMMono-MediumItalic.ttf",
}

SINGLE_SUBSTITUTION = 1
PAIR_POSITIONING = 2


def _subtables(lookup):
    """Yield each subtable of a lookup with its lookup type, unwrapping extension subtables."""
    for subtable in lookup.SubTable:
        if hasattr(subtable, "ExtSubTable"):
            yield subtable.ExtSubTable, subtable.ExtSubTable.LookupType
        else:
            yield subtable, lookup.LookupType


def has_tabular_feature(font: TTFont) -> bool:
    """Whether the font carries a `tnum` feature."""
    if "GSUB" not in font or font["GSUB"].table.FeatureList is None:
        return False
    return any(r.FeatureTag == "tnum" for r in font["GSUB"].table.FeatureList.FeatureRecord)


def mono_file_for(font: TTFont) -> str | None:
    """The DM Mono file whose digits fit the font, or None when DM Mono has no such style.

    DM Mono is drawn in static TrueType outlines, so only a font of that kind takes them.
    """
    if "glyf" not in font or "fvar" in font:
        return None
    return MONO_STYLES.get((font["OS/2"].usWeightClass, font["post"].italicAngle != 0))


def narrowing(x_scale: float, italic_angle: float) -> tuple[float, float, float, float, int, int]:
    """The affine that scales a glyph along x and keeps the slant of an italic as it was."""
    slant = math.tan(math.radians(-italic_angle))
    return (x_scale, 0, (1 - x_scale) * slant, 1, 0, 0)


def _outline(font: TTFont, name: str, transform=(1, 0, 0, 1, 0, 0)):
    """The glyph's outline as a TrueType glyph, components decomposed, through the transform."""
    glyph_set = font.getGlyphSet()
    recording = DecomposingRecordingPen(glyph_set)
    glyph_set[name].draw(recording)
    pen = TTGlyphPen(None)
    recording.replay(RoundingPen(TransformPen(pen, transform)))
    return pen.glyph()


def _place(font: TTFont, name: str, glyph, advance: int) -> None:
    glyph.recalcBounds(font["glyf"])
    font["glyf"][name] = glyph
    font["hmtx"][name] = (advance, glyph.xMin)


def draw_mono_digits(font: TTFont, mono: TTFont) -> None:
    """Redraw the tabular digits: one to nine from DM Mono, the zero the font's own plain one.

    DM Mono's only zero is slashed, so the plain zero of the font is narrowed to DM Mono's
    advance instead.
    """
    if font["head"].unitsPerEm != mono["head"].unitsPerEm:
        raise ValueError("the font and DM Mono are drawn on different units per em")
    advance = mono["hmtx"]["zero"][0]
    for digit in DIGITS[1:]:
        if mono["hmtx"][digit][0] != advance:
            raise ValueError(f"the DM Mono {digit} is not {advance} wide")
        _place(font, f"{digit}.tf", _outline(mono, digit), advance)
    transform = narrowing(advance / font["hmtx"]["zero"][0], font["post"].italicAngle)
    _place(font, "zero.tf", _outline(font, "zero", transform), advance)


def narrow_tabular_feature(font: TTFont) -> None:
    """Keep only the digit substitutions of `tnum` and their reversals in `pnum`."""
    gsub = font["GSUB"].table
    for record in gsub.FeatureList.FeatureRecord:
        if record.FeatureTag not in ("tnum", "pnum"):
            continue
        for index in record.Feature.LookupListIndex:
            for subtable, lookup_type in _subtables(gsub.LookupList.Lookup[index]):
                if lookup_type != SINGLE_SUBSTITUTION:
                    raise ValueError(
                        f"{record.FeatureTag} lookup {index} has type {lookup_type}, "
                        "a single substitution is expected"
                    )
                for source, target in list(subtable.mapping.items()):
                    digit = source if record.FeatureTag == "tnum" else target
                    if digit not in DIGITS:
                        del subtable.mapping[source]


def drop_tabular_kerning(font: TTFont) -> None:
    """Remove every tabular digit from both sides of every pair-positioning subtable."""
    if "GPOS" not in font:
        return
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for subtable, lookup_type in _subtables(lookup):
            if lookup_type != PAIR_POSITIONING:
                continue
            if subtable.Format == 1:
                _drop_from_glyph_pairs(subtable)
            elif subtable.Format == 2:
                _drop_from_class_pairs(subtable)


def _drop_from_glyph_pairs(subtable) -> None:
    glyphs, pair_sets = [], []
    for glyph, pair_set in zip(subtable.Coverage.glyphs, subtable.PairSet):
        if glyph in TABULAR_DIGITS:
            continue
        records = [r for r in pair_set.PairValueRecord if r.SecondGlyph not in TABULAR_DIGITS]
        pair_set.PairValueRecord = records
        pair_set.PairValueCount = len(records)
        glyphs.append(glyph)
        pair_sets.append(pair_set)
    subtable.Coverage.glyphs = glyphs
    subtable.PairSet = pair_sets
    subtable.PairSetCount = len(pair_sets)


def _drop_from_class_pairs(subtable) -> None:
    subtable.Coverage.glyphs = [g for g in subtable.Coverage.glyphs if g not in TABULAR_DIGITS]
    # Out of the second class table a glyph falls into class 0, the class of every unlisted glyph.
    for class_def in (subtable.ClassDef1, subtable.ClassDef2):
        for glyph in TABULAR_DIGITS:
            class_def.classDefs.pop(glyph, None)


def make_digits_tabular_only(font: TTFont, mono: TTFont | None) -> None:
    """Narrow the feature and drop the kerning, and redraw the digits when `mono` has them."""
    if not has_tabular_feature(font):
        raise ValueError("the font has no tnum feature")
    if mono is not None:
        draw_mono_digits(font, mono)
    narrow_tabular_feature(font)
    drop_tabular_kerning(font)
