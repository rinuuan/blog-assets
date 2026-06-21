# Blog Mascot Assets

## Base character

Path: `mascot/blog-mascot.png`

- Original full-size transparent mascot illustration.
- Intended as the visual reference for future expressions and variants.

## Web-optimized sets

Paths:

- `mascot/chibi/*.png`
- `mascot/emotions/*.png`

- Intended for the Blogger theme mascot.
- 400 px wide, true-color RGBA transparent PNGs.
- Exported with anti-aliasing and prefiltering to suppress moire and edge artifacts.
- Keep these files in RGBA mode; palette quantization can reintroduce banding and dithering.
- jsDelivr base URLs:
  - `https://cdn.jsdelivr.net/gh/rinuuan/blog-assets@main/mascot/chibi`
  - `https://cdn.jsdelivr.net/gh/rinuuan/blog-assets@main/mascot/emotions`

## High-resolution sets

Paths:

- `mascot/chibi-hd/*.png`
- `mascot/emotions-hd/*.png`

- Original transparent PNG exports.
- Intended for archival use, future edits, and high-resolution output.
- Do not use these files for the 140 px-wide Blogger mascot unless full resolution is required.

All four directories contain: `happy`, `angry`, `sad`, `surprised`, `shy`, `confused`, `excited`, and `sleepy`.
