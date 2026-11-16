# DM Fonts

This repository contains for DM suite of fonts: Sans, Serif Text and Serif Display.

# LawnStarter Release

This fork of [googlefonts/dm-fonts](https://github.com/googlefonts/dm-fonts) publishes DM Sans with tabular digits that line amounts up in a column. The fonts keep the family name DM Sans, so a tool that takes the release serves it in place of the Google Fonts copy.

The release holds every style of DM Sans, static and variable, as TrueType and WOFF2 files. It is built from the fonts exported under [Sans/fonts](Sans/fonts) and from the DM Mono files under [Mono](Mono), with the differences that [FONTLOG.txt](FONTLOG.txt) records:

- With the tabular figures feature (`tnum`) on, every digit takes the same width and the zero is plain. In the Light, Regular and Medium styles, upright and italic, the digits one to nine are the digits of [DM Mono](https://github.com/googlefonts/dm-mono), and the zero is the plain zero of DM Sans at the same width, since DM Mono draws only a slashed zero. Each of those fonts carries the DM Mono copyright notice beside its own.
- The other weights and the variable fonts, which DM Mono does not draw, keep the tabular digits upstream draws in that same style.
- The feature changes the ten digits and nothing else. Upstream also widens the space, the period, the comma, the colon and the semicolon.
- No glyph kerns against a tabular digit.
- The version string of each font ends with `;lawnstarter` and the release version.

With the feature off, text is set as upstream sets it. The PostScript-flavoured `.otf` files and the optical size statics, which upstream exported without the feature, are left out of the release.

## Turning the Tabular Digits On

- In Figma, select the text, open the type details and turn tabular numbers on.
- On the web, set `font-variant-numeric: tabular-nums`.
- In React Native, set `fontVariant: ['tabular-nums']`.

## Building

The build needs [uv](https://docs.astral.sh/uv/).

```sh
uv run pytest
uv run scripts/build_release.py <version>
```

The build writes the fonts and `DMSans-<version>.zip` to `dist/`.

## Releasing

Every merge to `main` runs the [Release workflow](.github/workflows/release.yml), where [release-please](https://github.com/googleapis/release-please) opens or updates a release pull request with the next version and the changelog, both read from the conventional commits since the last release. Merging that pull request creates the tag and the GitHub release, and the same workflow tests, builds and attaches `DMSans-<version>.zip` to it.

For Figma, an organization admin uploads the fonts of the release as a [shared font](https://help.figma.com/hc/en-us/articles/4403175325719-Manage-conflicting-fonts), which takes precedence over the Google Fonts copy.
# DM Serif

The [Serif](Serif) families are derived from [Source Serif Pro](https://github.com/adobe-fonts/source-serif-pro).

![Sans](Documentation/image3.png)
![Sans](Documentation/image4.png)

# DM Sans
The [Sans](Sans) family is derived from [Poppins](https://github.com/itfoundry/Poppins).

![Sans](Documentation/image1.png)
![Sans](Documentation/image2.png)

The type design and font development was commissioned from [Colophon Foundry](https://www.colophon-foundry.org), with Creative Direction from [MultiAdaptor](https://multiadaptor.com) and the DeepMind team.

These fonts are not officially supported Google products.

## License

All fonts are licensed under the [SIL Open Font License](https://scripts.sil.org/ofl).
