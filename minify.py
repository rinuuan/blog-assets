#!/usr/bin/env python3
"""Build theme.min.xml from theme.xml.

Blogger serves the theme file as-is (no build step), so to pass "minified
CSS/JS" checks the uploaded file itself must be minified. This keeps theme.xml
as the readable, commented source and writes a minified copy for upload.

Only the CSS in <b:skin> and the JS inside //<![CDATA[ ... //]]> script blocks
are minified, using whitespace/comment-only minifiers (rjsmin, rcssmin) that
never rename symbols — so behaviour is preserved. Blogger markup, expr/data
attributes, and non-CDATA inline scripts are left untouched.

    pip install rjsmin rcssmin
    python3 minify.py
"""
import re
import sys
import xml.dom.minidom
from pathlib import Path

import rcssmin
import rjsmin

SRC = Path(__file__).with_name("theme.xml")
OUT = Path(__file__).with_name("theme.min.xml")


def minify_css(m):
    return m.group(1) + rcssmin.cssmin(m.group(2)) + m.group(3)


def minify_js(m):
    return "//<![CDATA[\n" + rjsmin.jsmin(m.group(1)).strip() + "\n//]]>"


def main():
    text = SRC.read_text(encoding="utf-8")

    # CSS: the single <b:skin> CDATA block.
    text = re.sub(
        r"(<b:skin><!\[CDATA\[)(.*?)(\]\]></b:skin>)",
        minify_css, text, flags=re.S,
    )

    # JS: every //<![CDATA[ ... //]]> guarded script block.
    text = re.sub(r"//<!\[CDATA\[(.*?)//\]\]>", minify_js, text, flags=re.S)

    # HTML comments (<!-- -->). CSS/JS CDATA is already minified, so this only
    # hits markup comments; <!DOCTYPE> and <?xml?> are not comments and stay.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    # Drop indentation and blank lines. Safe here: the template has no
    # <pre>/<textarea> and no template literals, and a newline is kept between
    # tags, so inline spacing is unchanged (runs of whitespace already collapse
    # to a single space in HTML).
    text = "\n".join(line.lstrip() for line in text.splitlines() if line.strip()) + "\n"

    OUT.write_text(text, encoding="utf-8")

    # Fail loudly if the result is not well-formed XML.
    xml.dom.minidom.parse(str(OUT))

    before, after = SRC.stat().st_size, OUT.stat().st_size
    print(f"theme.xml     {before:>7,} bytes")
    print(f"theme.min.xml {after:>7,} bytes  ({100 * (before - after) // before}% smaller)")
    print("XML valid. Upload theme.min.xml to Blogger.")


if __name__ == "__main__":
    sys.exit(main())
