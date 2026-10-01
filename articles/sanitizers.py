"""
HTML sanitization for article bodies.

The body comes from the Quill editor as raw HTML and is rendered with `|safe`,
so anything not on the allow-list below (e.g. <script>, onerror=..., javascript: links)
must be stripped before it is stored.
"""
import re

import nh3

ALLOWED_TAGS = {
    "p", "br", "span", "strong", "b", "em", "i", "u", "s", "strike", "sub", "sup",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre", "code",
    "ul", "ol", "li",
    "a", "img", "video", "source", "iframe",
    "figure", "figcaption", "hr",
}

ALLOWED_ATTRIBUTES = {
    "*": {"class", "style"},  # style is reduced to ALLOWED_STYLE_PROPERTIES
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "video": {"src", "controls", "width", "height", "poster"},
    "source": {"src", "type"},
    "iframe": {"src", "width", "height", "allowfullscreen", "frameborder"},
    "pre": {"spellcheck"},
    "li": {"data-list"},
}

# Only harmless inline styles that Quill produces
ALLOWED_STYLE_PROPERTIES = {"color", "background-color", "text-align"}

# Only Quill's own CSS classes (alignment, indent, code blocks, video embeds…)
QUILL_CLASS_RE = re.compile(r"^ql-[a-z0-9-]+$")

# Embedded videos (Quill "video" button) may only come from these hosts
IFRAME_SRC_RE = re.compile(
    r"^https://(www\.)?(youtube\.com|youtube-nocookie\.com|player\.vimeo\.com)/"
)
DATA_IMAGE_RE = re.compile(r"^data:image/(png|jpe?g|gif|webp);base64,", re.IGNORECASE)


def _attribute_filter(tag, attr, value):
    if attr == "class":
        classes = [c for c in value.split() if QUILL_CLASS_RE.match(c)]
        return " ".join(classes) or None
    if tag == "iframe" and attr == "src":
        return value if IFRAME_SRC_RE.match(value) else None
    if attr in ("src", "href") and value.strip().lower().startswith("data:"):
        # Pasted images are stored by Quill as base64 data URIs — allow images only.
        return value if tag == "img" and DATA_IMAGE_RE.match(value.strip()) else None
    return value


def sanitize_html(html):
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        attribute_filter=_attribute_filter,
        url_schemes={"http", "https", "mailto", "data"},
        filter_style_properties=ALLOWED_STYLE_PROPERTIES,
        link_rel="noopener noreferrer nofollow",
    )
