#!/usr/bin/env python3
"""Build and validate the Blogger upload artifact from theme.xml."""
import ast
import html
import io
import os
import re
import json
import shutil
import subprocess
import sys
import tokenize
import xml.dom.minidom
from pathlib import Path

import rcssmin
import rjsmin

BASE = Path(__file__).resolve().parent
SRC = BASE / "theme.xml"
OUT = BASE / "theme.min.xml"
COMMENT_MAX_CHARS = 100
CJK_RE = re.compile(r"[\u3400-\u9fff]")
SCRIPT_BLOCK_RE = re.compile(
    r"<script[^>]*>\s*//<!\[CDATA\[(.*?)//\]\]>\s*</script>", re.S
)
INLINE_SCRIPT_RE = re.compile(r"<script\b(?![^>]*/>)([^>]*)>(.*?)</script>", re.S)
LOCAL_MASCOT_CDN_RE = re.compile(
    r"https://cdn\.jsdelivr\.net/gh/rinuuan/blog-assets@main/(mascot/[^'\"\s<]+)"
)
BSKIN_RE = re.compile(r"<b:skin><!\[CDATA\[(.*?)\]\]></b:skin>", re.S)
CSS_CONTRACT_CHECKS = (
    (
        "h2.post-title",
        {
            "min-width": "0",
            "max-width": "100%",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        "h2.post-title a",
        {
            "display": "block",
            "min-width": "0",
            "max-width": "100%",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        "h2.post-title .lang-zh",
        {
            "min-width": "0",
            "max-width": "100%",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        "h2.post-title .lang-en",
        {
            "min-width": "0",
            "max-width": "100%",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        "h2.post-title *",
        {
            "min-width": "0",
            "max-width": "100%",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".title-chunk",
        {
            "display": "contents",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".listing-title",
        {
            "min-width": "0",
            "max-width": "100%",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".listing-title .lang-zh",
        {
            "min-width": "0",
            "max-width": "100%",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".listing-title .lang-en",
        {
            "min-width": "0",
            "max-width": "100%",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".related-posts li a",
        {
            "display": "block",
            "min-width": "0",
            "max-width": "100%",
            "box-sizing": "border-box",
            "white-space": "normal",
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".post-body.full-content",
        {
            "overflow-wrap": "anywhere",
            "word-break": "normal",
            "line-break": "anywhere",
        },
    ),
    (
        ".post-body a",
        {
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".post-body.full-content code",
        {
            "overflow-wrap": "anywhere",
            "word-break": "break-all",
            "line-break": "anywhere",
        },
    ),
    (
        ".post-body.full-content pre",
        {
            "overflow-x": "auto",
            "overscroll-behavior-x": "contain",
        },
    ),
    (
        ".post-body.full-content pre code",
        {
            "overflow-wrap": "normal",
            "word-break": "normal",
            "line-break": "auto",
        },
    ),
    (
        ".comment-content",
        {
            "overflow-wrap": "anywhere",
            "word-break": "normal",
            "line-break": "anywhere",
        },
    ),
    (
        ".error-bubble",
        {
            "overflow-wrap": "anywhere",
            "word-break": "normal",
            "line-break": "anywhere",
        },
    ),
    (
        ".mascot-bubble",
        {
            "overflow-wrap": "anywhere",
            "word-break": "normal",
            "line-break": "anywhere",
        },
    ),
    (
        ".mascot-menu",
        {
            "max-height": "calc(100dvh - 16px)",
            "overflow-y": "auto",
            "overscroll-behavior-y": "contain",
        },
    ),
    (
        ".post-outer",
        {
            "min-width": "0",
            "max-width": "100%",
            "box-sizing": "border-box",
        },
    ),
    (
        ".blog-posts",
        {
            "min-width": "0",
            "max-width": "100%",
            "box-sizing": "border-box",
        },
    ),
    (
        ".post-outer > *",
        {
            "min-width": "0",
            "max-width": "100%",
            "box-sizing": "border-box",
        },
    ),
    (
        ".header-logo-link > span:last-child",
        {
            "min-width": "0",
            "max-width": "100%",
            "overflow-wrap": "anywhere",
            "line-break": "anywhere",
        },
    ),
    (
        ".post-body.full-content object",
        {
            "max-width": "100%",
        },
    ),
    (
        "#comment-actions",
        {
            "width": "1px",
            "height": "1px",
            "border": "0",
        },
    ),
    (
        ".reading-bar .bar-fill",
        {
            "transition": "background-color 0.3s var(--ease)",
            "will-change": "transform",
        },
    ),
    (
        ".comments .comment-block",
        {
            "min-width": "0",
            "max-width": "100%",
        },
    ),
    (
        ".comment-content img",
        {
            "max-width": "100%",
            "height": "auto",
        },
    ),
    (
        ".form-inner",
        {
            "min-height": "0",
            "overflow": "hidden",
        },
    ),
)
THEME_REGRESSION_CHECKS = (
    (
        re.compile(r"\.mascot-menu\s+button\s*\{[^}]*transition\s*:\s*(?=[^;}]*\b(?:color|background)\b)[^;}]*", re.I | re.S),
        "mascot menu buttons must not animate paint-only properties",
    ),
    (
        re.compile(r"querySelectorAll\(\"a,\s*span\"\)[\s\S]*?includes\(\"load more\"\)", re.I),
        "comment cleanup must not scan broad text nodes for pagination labels",
    ),
    (
        re.compile(r"document\.querySelectorAll\(\"\.comment-reply\.cancel-active\"\)", re.I),
        "comment reply state queries must stay inside the comments wrapper",
    ),
    (
        re.compile(r"document\.querySelectorAll\(\"\.(?:avatar-image-container|item-control|comment-replies)", re.I),
        "comment restructuring queries must stay inside the observed container",
    ),
    (
        re.compile(r"#custom-comment-form-container\.is-expanded\s+\.form-inner\s*\{[^}]*min-height", re.I | re.S),
        "comment form child min-height must not snap during grid expansion",
    ),
    (
        re.compile(r"applyEditorHeight\(editorIframe,\s*editorIframe\.getAttribute\(\"height\"\)", re.I),
        "main comment reopen must not adopt the iframe height written while hidden",
    ),
    (
        re.compile(r"\b(?:restoreExpandedEditor|focusCommentEditor|queueEditorFocus)\b|window\.scrollBy\(", re.I),
        "comment form relocation must not focus the outer iframe or add scroll compensation",
    ),
    (
        re.compile(r"@keyframes\s+comment-editor-theme-", re.I),
        "comment editor opacity keyframes break cross-frame blend compositing during theme changes",
    ),
    (
        re.compile(r"\b(?:waitForEditorLayout|commentThemeTimer|avatarReadyTimer)\b", re.I),
        "comment editor must not reintroduce delayed theme/load timer orchestration",
    ),
    (
        re.compile(r"\b(?:EDITOR_POINTER_PASS_MS|editorPointerRelockTimer)\b", re.I),
        "comment editor identity switching must not depend on a short click-through timer",
    ),
    (
        re.compile(r"comment-editor-dark", re.I),
        "comment editor must not apply an unsupported SVG filter to the iframe",
    ),
    (
        re.compile(r"\b(?:primeEditorAvatar|editorAvatarPreload)\b", re.I),
        "comment editor must not guess or preload another user's avatar",
    ),
    (
        re.compile(r"\b(?:avatarCover|primeCompactEditorBeforeOpen|editorExpansionSettled|revealEditorAvatar)\b|\.comment-avatar-cover", re.I),
        "comment avatar rendering must not restore the delayed cover lifecycle",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*background-color:\s*var\(--avatar-placeholder\)", re.I | re.S),
        "loading avatar cover must not render as a visible blank circle",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*transition:\s*background-color", re.I | re.S),
        "reply reload cover must not fade in after the iframe has already changed",
    ),
    (
        re.compile(r"\.form-inner::before", re.I),
        "comment form must not create a second avatar-shaped theme layer",
    ),
    (
        re.compile(r"\.form-inner\s*\{[^}]*contain:\s*paint", re.I | re.S),
        "collapsed editors must not discard the iframe and avatar compositor surfaces",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*clip-path", re.I | re.S),
        "comment avatar correction must not add a second antialiased circular edge",
    ),
    (
        re.compile(r"\.comment-avatar-window-lower\[data-avatar-layout=\"lower\"\]:not\(\[hidden\]\)\s*\{[^}]*filter:\s*none", re.I | re.S),
        "lower avatar correction must retain profile-chrome presence detection",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*will-change:\s*(?:filter|backdrop-filter)", re.I | re.S),
        "avatar correction must not pre-rasterize stale iframe pixels",
    ),
    (
        re.compile(r"\.top-actions\s*\{[^}]*(?:-webkit-)?backdrop-filter", re.I | re.S),
        "top controls must not rebuild a backdrop-filter layer during theme changes",
    ),
    (
        re.compile(r"--comment-avatar-top", re.I),
        "the upper avatar probe must stay fixed while Blogger changes editor height",
    ),
    (
        re.compile(r"\b(?:has-static-avatar|comment-avatar-static|adminAvatar)\b", re.I),
        "comment editor avatar must come from the active Blogger iframe, not a copied author avatar",
    ),
    (
        re.compile(r"#custom-comment-form-container(?:\.[^{\s]+)?\s*\{[^}]*\bopacity\s*:", re.I | re.S),
        "comment form opacity grouping breaks iframe blend compositing while opening",
    ),
    (
        re.compile(r"\.comments-wrapper\s+iframe#comment-editor\s*\{[\s\S]*?mix-blend-mode\s*:\s*difference", re.I),
        "difference blending destroys comment contrast and avatar restoration",
    ),
    (
        re.compile(r"\.comment-avatar-window\.is-ready\s*\{[^}]*mix-blend-mode\s*:\s*color-dodge", re.I | re.S),
        "color-dodge recolours the signed-in avatar in light mode",
    ),
    (
        re.compile(r"letter-spacing\s*:\s*-\d", re.I),
        "negative letter-spacing is not allowed",
    ),
    (
        re.compile(r"transition\s*:\s*all\b", re.I),
        "transition: all is too broad",
    ),
    (
        re.compile(r"word-break\s*:\s*break-word\b", re.I),
        "word-break: break-word is too weak; use anywhere/normal or break-all deliberately",
    ),
    (
        re.compile(r"<a\b(?=[^>]*\bhref=)(?=[^>]*\baria-hidden=['\"]true['\"])[^>]*>", re.I),
        "aria-hidden links are still links; remove href or remove aria-hidden",
    ),
    (
        re.compile(r"\.title-chunk\s*\{[^}]*display\s*:\s*inline-block", re.I | re.S),
        ".title-chunk must not be inline-block",
    ),
    (
        re.compile(r"^\s*h2\.post-title\s*\{[^}]*text-wrap\s*:\s*balance", re.I | re.S | re.M),
        "h2.post-title must not use balanced wrapping; long titles can overflow",
    ),
    (
        re.compile(r"^\s*h2\.post-title\s*\{(?![^}]*min-width\s*:\s*0\b)", re.I | re.S | re.M),
        "h2.post-title must keep min-width: 0",
    ),
    (
        re.compile(r"^\s*h2\.post-title\s*\{(?![^}]*line-break\s*:\s*anywhere\b)", re.I | re.S | re.M),
        "h2.post-title must allow emergency line breaks",
    ),
    (
        re.compile(r"h2\.post-title\s+a\s*\{(?![^}]*display\s*:\s*block\b)", re.I | re.S),
        "h2.post-title a must remain block-level for long-title wrapping",
    ),
    (
        re.compile(r"h2\.post-title\s+a\s*\{(?![^}]*min-width\s*:\s*0\b)", re.I | re.S),
        "h2.post-title a must keep min-width: 0",
    ),
    (
        re.compile(r"\.header-logo-link\s*>\s*span:last-child\s*\{(?![^}]*min-width\s*:\s*0\b)", re.I | re.S),
        "header title span must keep min-width: 0",
    ),
    (
        re.compile(r"logo-steam-motion", re.I),
        "old combined logo steam animation target must not return",
    ),
)
THEME_REQUIRED_CHECKS = (
    (
        re.compile(r"#custom-comment-form-container\.is-returning-main\s*\{[^}]*grid-template-rows\s+0\.22s\s+var\(--ease\)[\s\S]*?#custom-comment-form-container\.is-returning-main\.is-expanded\s*\{[^}]*grid-template-rows\s+0\.28s\s+var\(--ease\)", re.I),
        "reply-to-main comment motion must stay responsive",
    ),
    (
        re.compile(r"#custom-comment-form-container\s*\{[^}]*transition:\s*grid-template-rows\s+0\.28s\s+var\(--ease\),\s*margin\s+0\.28s\s+var\(--ease\)[\s\S]*?#custom-comment-form-container\.is-expanded\s*\{[^}]*transition:\s*grid-template-rows\s+0\.32s\s+var\(--ease\),\s*margin\s+0\.32s\s+var\(--ease\)", re.I),
        "main comment motion must use the site's balanced easing",
    ),
    (
        re.compile(r"if\s*\(wasExpanded\s*&&\s*!alreadyAtTop\)\s*\{\s*customFormContainer\.classList\.add\(\"is-returning-main\"\);\s*setFormExpanded\(false\)", re.I),
        "reply-to-main speed override must cover both motion phases",
    ),
    (
        re.compile(r"const\s+relocateAndExpand\s*=\s*\(\)\s*=>\s*\{\s*if\s*\(actionToken\s*!==\s*formActionToken\)\s*return;[\s\S]*?if\s*\(!alreadyAtTop\)\s*customFormContainer\.classList\.add\(\"is-loading-mask\"\);\s*if\s*\(!alreadyAtTop\)\s*customFormContainer\.classList\.add\(\"is-returning-main\"\)", re.I),
        "interrupted reply-to-main motion must retain the fast open",
    ),
    (
        re.compile(r"if\s*\(customFormContainer\.classList\.contains\(\"is-expanded\"\)\)\s*\{[\s\S]*?customFormContainer\.classList\.remove\(\"is-returning-main\"\)", re.I),
        "reply-to-main speed override must clear after expansion",
    ),
    (
        re.compile(r"const\s+expandMainForm\s*=\s*\(\)\s*=>[\s\S]*?setFormExpanded\(true\);\s*afterFormOpened\(actionToken,\s*finishMainToggle\);", re.I),
        "main comment form must finish through the transition lifecycle without iframe focus",
    ),
    (
        re.compile(r"#custom-comment-form-container:not\(\.is-expanded\)\s+iframe#comment-editor\s*\{\s*transition:\s*none", re.I | re.S),
        "collapsed comment editor must settle hidden height updates immediately",
    ),
    (
        re.compile(r"if\s*\(alreadyAtTop\)\s*\{[\s\S]*?applyEditorHeight\(editorIframe,\s*settledEditorHeight,\s*true\);[\s\S]*?expandMainForm\(\);\s*\}\s*else\s*\{\s*requestAnimationFrame\(\(\)\s*=>\s*\{[\s\S]*?requestAnimationFrame\(expandMainForm\)", re.I),
        "main comment form must use the closed baseline before reopening",
    ),
    (
        re.compile(r"function\s+normalizeClosedEditorHeight\(iframe\)\s*\{[\s\S]*?classList\.contains\(\"is-expanded\"\)\)\s*return;[\s\S]*?applyEditorHeight\(iframe,\s*MIN_EDITOR_HEIGHT,\s*true\);[\s\S]*?iframe\.setAttribute\(\"height\",\s*MIN_EDITOR_HEIGHT\s*\+\s*\"px\"\)", re.I),
        "closed main editors must commit Blogger's compact reopen baseline",
    ),
    (
        re.compile(r"if\s*\(reduceMotion\(\)\)[\s\S]*?normalizeClosedEditorHeight\(iframe\);[\s\S]*?setEditorState\(\"closed\",\s*iframe\)[\s\S]*?transitionend[\s\S]*?else\s+if\s*\(editorState\s*===\s*\"closing\"\)[\s\S]*?normalizeClosedEditorHeight\(iframe\);[\s\S]*?setEditorState\(\"closed\",\s*iframe\)", re.I),
        "both reduced-motion and animated closes must normalize while hidden",
    ),
    (
        re.compile(r"const\s+afterFormClosed\s*=\s*\(token,\s*callback\)\s*=>[\s\S]*?probeFrame\s*=\s*requestAnimationFrame\([\s\S]*?getComputedStyle\(customFormContainer\)\.gridTemplateRows[\s\S]*?collapsedRow\s*<=\s*2\.5[\s\S]*?finish\(\)", re.I),
        "comment relocation must recover when a collapsed form emits no transitionend",
    ),
    (
        re.compile(r"\.mascot-menu\s+button\s*\{[^}]*transition:\s*transform\s+0\.18s\s+var\(--ease\)", re.I | re.S),
        "mascot menu feedback must stay compositor-friendly",
    ),
    (
        re.compile(r"--icon-color:\s*color-mix\(in srgb,\s*var\(--text-color\)\s*78%,\s*var\(--meta-color\)\)[\s\S]*?--glass-chrome:\s*color-mix\(in srgb,\s*var\(--bg-color\)\s*58%,\s*transparent\)[\s\S]*?--glass-blur:\s*blur\(16px\)\s*saturate\(160%\)[\s\S]*?--glass-edge:\s*inset\s+0\s+1px\s+0\s+color-mix\(in srgb,\s*var\(--text-color\)\s*9%,\s*transparent\)", re.I),
        "floating glass controls must keep readable icons and a subtle shared edge",
    ),
    (
        re.compile(r"\.comments-wrapper\s+iframe#comment-editor\s*\{[^}]*height:\s*var\(--comment-editor-height,\s*66px\)\s*!important", re.I | re.S),
        "comment editor height must preserve the compact fallback",
    ),
    (
        re.compile(r'if\s*\(theme\s*!==\s*"light"\s*&&\s*theme\s*!==\s*"dark"\)', re.I),
        "stored theme preference must be validated before use",
    ),
    (
        re.compile(r'lang\s*!==\s*"zh"\s*&&\s*lang\s*!==\s*"en"[\s\S]*?variant\s*!==\s*"simp"\s*&&\s*variant\s*!==\s*"trad"', re.I),
        "stored language and variant preferences must be validated before use",
    ),
    (
        re.compile(r"chatLevel\s*!==\s*'full'\s*&&\s*chatLevel\s*!==\s*'less'\s*&&\s*chatLevel\s*!==\s*'mute'", re.I),
        "stored mascot chatter preference must be validated before use",
    ),
    (
        re.compile(r"var\s+startMascot\s*=\s*function\s*\(\s*bootFromInteraction\s*\)", re.I),
        "mascot initialization must remain deferred behind startMascot",
    ),
    (
        re.compile(r"requestIdleCallback\s*\(\s*function\s*\(\)\s*\{\s*bootMascot\(false\);\s*\}", re.I),
        "mascot idle boot must remain off the first synchronous pass",
    ),
    (
        re.compile(r"imgEl\.onerror\s*=\s*function\s*\(\)\s*\{[\s\S]*?wrap\.classList\.add\('is-hidden'\);[\s\S]*?wrap\.remove\(\);\s*gear\.remove\(\);\s*menu\.remove\(\);\s*reopen\.remove\(\)", re.I),
        "permanent mascot image failure must disable chatter and remove every mascot control",
    ),
    (
        re.compile(r"if\s*\(idleTimer\)\s*\{\s*clearTimeout\(idleTimer\);\s*idleTimer\s*=\s*null;\s*\}\s*if\s*\(wrap\.classList\.contains\('is-hidden'\)\s*\|\|\s*!ambient\(\)\)\s*return", re.I),
        "mascot idle timer must not run while hidden or quiet",
    ),
    (
        re.compile(r"if\s*\(ambient\(\)\s*&&\s*!wrap\.classList\.contains\('is-hidden'\)\)\s*sayMoods\(IDLE_MOODS\)", re.I),
        "mascot idle callback must re-check hidden and chatter state",
    ),
    (
        re.compile(r"if\s*\(idleTimer\)\s*\{\s*clearTimeout\(idleTimer\);\s*idleTimer\s*=\s*null;\s*\}[\s\S]*?if\s*\(bubbleTimer\)\s*\{\s*clearTimeout\(bubbleTimer\);\s*bubbleTimer\s*=\s*null;\s*bubble\.classList\.remove\('is-shown'\);", re.I),
        "hiding mascot must clear idle and bubble timers",
    ),
    (
        re.compile(r"var\s+clearTuckTimers\s*=\s*function\s*\(\)\s*\{[\s\S]*?clearTimeout\(tuckTimer\);[\s\S]*?clearTimeout\(peekWarmTimer\);", re.I),
        "mascot tuck cleanup must clear both tuck and peek warmup timers",
    ),
    (
        re.compile(r"peekWarmTimer\s*=\s*setTimeout\s*\(\s*function\s*\(\)\s*\{[\s\S]*?peekWarmTimer\s*=\s*null;[\s\S]*?if\s*\(snapSide\)\s*warmPeek\(snapSide\);[\s\S]*?\},\s*2500\)", re.I),
        "mascot peek warmup must be tracked so stale warmups can be cancelled",
    ),
    (
        re.compile(r"if\s*\(bubbleTimer\)\s*\{[\s\S]*?bubble\.classList\.remove\('is-shown'\);\s*\}[\s\S]*?clearTuckTimers\(\);", re.I),
        "hiding mascot must clear tuck and peek warmup timers",
    ),
    (
        re.compile(r"localStorage\.removeItem\(REOPEN_KEY\);[\s\S]*?resetIdle\(\);[\s\S]*?if\s*\(snapSide\)\s*scheduleTuck\(\)", re.I),
        "showing mascot must restore idle scheduling before tucking",
    ),
    (
        re.compile(r"walkTextNodesChunked\s*=\s*\(\s*node,\s*applyConversion,\s*done,\s*token\s*\)", re.I),
        "variant conversion must remain chunked and generation-aware",
    ),
    (
        re.compile(r"const\s+token\s*=\s*\+\+conversionToken[\s\S]*?walkTextNodesChunked\(document\.body,[\s\S]*?\},\s*token\)", re.I),
        "full-page variant conversion must cancel stale conversion work",
    ),
    (
        re.compile(r"triggerContentFade\s*\(\s*done\s*=>\s*\{\s*loadOpenCC", re.I),
        "variant toggle fade must wait for chunked OpenCC conversion",
    ),
    (
        re.compile(r"const\s+loadOpenCCLibrary\s*=\s*callback\s*=>", re.I),
        "OpenCC loading must be shared by full-page and appended-content conversion",
    ),
    (
        re.compile(r"const\s+effectiveVariant\s*=\s*pendingVariant\s*\|\|\s*root\.getAttribute\(\"data-variant\"\)", re.I),
        "appended-content conversion must respect an in-progress variant switch",
    ),
    (
        re.compile(r"const\s+syncChinesePostLangs\s*=\s*\(scope,\s*targetVariant\)\s*=>[\s\S]*?\.post-body\[lang\^=\"zh\"\],[\s\S]*?\.post-title\[lang\^=\"zh\"\]", re.I),
        "Chinese post language attributes must share one variant sync helper",
    ),
    (
        re.compile(r"const\s+commitVariant\s*=\s*targetVariant\s*=>[\s\S]*?root\.setAttribute\(\"data-variant\",\s*targetVariant\);[\s\S]*?syncChinesePostLangs\(document,\s*targetVariant\);[\s\S]*?localStorage\.setItem\(\"variant\",\s*targetVariant\);[\s\S]*?syncToggleLabels\(\);[\s\S]*?pendingVariant\s*=\s*null", re.I),
        "variant state must commit attributes, content lang, storage, UI, and pending state together",
    ),
    (
        re.compile(r"if\s*\(!ok\s*\|\|\s*!window\.OpenCC\)\s*\{\s*commitVariant\(\"simp\"\)", re.I),
        "OpenCC load failure must fall back to an accurate Simplified state",
    ),
    (
        re.compile(r"walkTextNodesChunked\(document\.body,\s*converter,\s*\(\)\s*=>\s*\{[\s\S]*?commitVariant\(targetVariant\)", re.I),
        "successful full-page conversion must commit the target variant",
    ),
    (
        re.compile(r"walkTextNodesChunked\(subtree,\s*s2tConv,[\s\S]*?syncChinesePostLangs\(subtree,\s*\"trad\"\)[\s\S]*?\},\s*token\)", re.I),
        "appended Traditional posts must update their lang attributes after conversion",
    ),
    (
        re.compile(r"const\s+zhLang\s*=\s*document\.documentElement\.getAttribute\('data-variant'\)\s*===\s*'trad'\s*\?\s*'zh-Hant'\s*:\s*'zh-Hans'[\s\S]*?body\.setAttribute\('lang',\s*zhLang\)[\s\S]*?title\.setAttribute\('lang',\s*isEnglish\s*\?\s*'en'\s*:\s*zhLang\)", re.I),
        "initial Chinese post typography must use the active variant lang tag",
    ),
    (
        re.compile(r"clearTimeout\(initialVariantTimer\)", re.I),
        "initial Traditional conversion timer must be cancelled before a manual variant toggle",
    ),
    (
        re.compile(r"cleanupRelatedPosts\s*=\s*\(\)\s*=>", re.I),
        "related-posts JSONP callback must be cleaned up after load/error",
    ),
    (
        re.compile(r"let\s+relatedPostsTimeout\s*=\s*null", re.I),
        "related-posts JSONP cleanup must track a request timeout",
    ),
    (
        re.compile(r"if\s*\(relatedPostsTimeout\)\s*\{[\s\S]*?clearTimeout\(relatedPostsTimeout\);[\s\S]*?relatedPostsTimeout\s*=\s*null;", re.I),
        "related-posts cleanup must clear the request timeout",
    ),
    (
        re.compile(r"relatedPostsTimeout\s*=\s*setTimeout\(\(\)\s*=>\s*\{[\s\S]*?relatedPostsSettled\s*=\s*true;[\s\S]*?cleanupRelatedPosts\(\);[\s\S]*?\},\s*8000\)", re.I),
        "related-posts JSONP request must time out and clean itself up",
    ),
    (
        re.compile(r"relatedPostsScript\s*&&\s*relatedPostsScript\.parentNode\)\s*relatedPostsScript\.remove\(\)", re.I),
        "related-posts JSONP script node must be removed after load/error",
    ),
    (
        re.compile(r"var\s+navList\s*=\s*nav\.querySelector\('ul'\)", re.I),
        "nav overflow detection must measure the inner list, not the class-mutated nav box",
    ),
    (
        re.compile(r"var\s+scrolling\s*=\s*navList\.scrollWidth\s*>\s*nav\.clientWidth\s*\+\s*1", re.I),
        "nav overflow detection must compare list scroll width to visible nav width",
    ),
    (
        re.compile(r"var\s+scheduleCheck\s*=\s*function\s*\(\)\s*\{[\s\S]*?requestAnimationFrame\(check\)", re.I),
        "nav resize checks must be coalesced with requestAnimationFrame",
    ),
    (
        re.compile(r"let\s+formInner\s*=\s*customFormContainer\.querySelector\('\.form-inner'\)", re.I),
        "comment iframe initialization must reuse an existing form-inner wrapper",
    ),
    (
        re.compile(r"placeEditorInForm\(editorIframe,\s*formInner\)", re.I),
        "comment iframe initialization must preserve the editor/avatar wrapper order",
    ),
    (
        re.compile(r"aria-controls='custom-comment-form-container'\s+aria-expanded='true'\s+class='comment-toggle-btn'\s+id='comment-toggle'", re.I),
        "main comment toggle must expose its controlled form and initial expanded state",
    ),
    (
        re.compile(r"<a\s+expr:href='data:post\.commentFormIframeSrc'\s+hidden='hidden'\s+id='comment-editor-src'\s*/>", re.I),
        "comment iframe source must stay an <a href> so BLOG_CMT_createIframe can tokenize it",
    ),
    (
        re.compile(r"getElementById\(\"comment-editor-src\"\)[\s\S]*?searchParams\.set\(\"m\",\s*\"1\"\)[\s\S]*?searchParams\.set\(\"hl\",\s*locale\)[\s\S]*?link\.href\s*=\s*url\.href", re.I),
        "comment editor must use its final renderer and locale on the first request",
    ),
    (
        re.compile(r"<link\s+href='https://www\.blogger\.com'\s+rel='preconnect'\s*/>[\s\S]*?<link\s+href='https://blogger\.googleusercontent\.com'\s+rel='preconnect'\s*/>", re.I),
        "comment editor and avatar must warm their connections before iframe creation",
    ),
    (
        re.compile(r"<iframe\s+allowtransparency='allowtransparency'\s+class='blogger-iframe-colorize blogger-comment-from-post'\s+fetchpriority='high'\s+frameborder='0'\s+height='66'\s+id='comment-editor'\s+loading='eager'\s+name='comment-editor'\s+scrolling='no'", re.I),
        "comment editor must load eagerly without an independently scrollable viewport",
    ),
    (
        re.compile(r"#custom-comment-form-container\.is-reserved\s*\{\s*min-height:\s*66px", re.I),
        "comment editor reservation must match its compact initial height",
    ),
    (
        re.compile(r"#custom-comment-form-container:not\(\.is-expanded\)\s+\.form-inner\s*\{[^}]*border-color:\s*transparent[^}]*box-shadow:\s*none", re.I | re.S),
        "collapsed comment form must not leave a flattened border line",
    ),
    (
        re.compile(r"\.form-inner\s*\{[^}]*transition:\s*var\(--comment-theme-transition\)", re.I | re.S),
        "comment form background must share the page theme transition",
    ),
    (
        re.compile(r"\.is-theme-switching\s+\.top-actions\s*\{[^}]*background-color\s+0s\s*,\s*box-shadow\s+0s", re.I | re.S),
        "toolbar surface must switch with foreground colours without blur repaints",
    ),
    (
        re.compile(r"\.top-actions\s+\.action-btn:focus-visible\s*\{[^}]*position:\s*relative[^}]*z-index:\s*1", re.I | re.S),
        "focused toolbar controls must paint above adjacent buttons",
    ),
    (
        re.compile(r"const\s+rect\s*=\s*form\s*&&\s*form\.getBoundingClientRect\(\)[\s\S]*?const\s+visible\s*=\s*rect\s*&&\s*rect\.bottom\s*>\s*0\s*&&\s*rect\.top\s*<\s*window\.innerHeight\s*&&\s*rect\.right\s*>\s*0\s*&&\s*rect\.left\s*<\s*window\.innerWidth[\s\S]*?typeof\s+document\.startViewTransition\s*!==\s*\"function\"\s*\|\|\s*!visible", re.I),
        "offscreen comment editors must not start a native theme snapshot",
    ),
    (
        re.compile(r"\.is-comment-view-transition\s*\{[^}]*view-transition-name:\s*none[^}]*\}[\s\S]*?\.is-comment-view-transition\s+\.form-inner\s*\{[^}]*view-transition-name:\s*comment-form[^}]*transition:\s*none[\s\S]*?\.is-comment-view-transition\s+\.top-actions\s*\{[^}]*view-transition-name:\s*comment-theme-actions[\s\S]*?\.is-comment-view-transition\s+\.reading-bar\s*\{[^}]*view-transition-name:\s*comment-reading-progress[\s\S]*?::view-transition-(?:old|new)\(comment-theme-actions\)[\s\S]*?::view-transition-(?:old|new)\(comment-reading-progress\)[\s\S]*?applyThemeWithCommentSnapshot\s*=\s*theme\s*=>\s*\{[\s\S]*?#custom-comment-form-container\.is-expanded\s+\.form-inner[\s\S]*?reduceContentMotion\(\)[\s\S]*?document\.startViewTransition[\s\S]*?transition\.finished\.then\(cleanup,\s*cleanup\)", re.I),
        "visible comment editor theme changes must snapshot the form and fixed reading chrome with a safe fallback",
    ),
    (
        re.compile(r"\.comments-wrapper\s+iframe#comment-editor\s*\{[\s\S]*?filter:\s*invert\(0\)\s+hue-rotate\(0deg\)\s+brightness\(1\)[\s\S]*?mix-blend-mode:\s*multiply[\s\S]*?transition:\s*height", re.I),
        "light comment editor must keep its stable multiply identity and geometry motion",
    ),
    (
        re.compile(r"\.header-desc\s*\{[^}]*color:\s*inherit[^}]*opacity:\s*0\.62[^}]*transition:\s*none", re.I | re.S),
        "header subtitle must inherit the body's in-flight colour without a second transition",
    ),
    (
        re.compile(r"\.comment-author,\s*\.datetime\s*\{[^}]*color:\s*inherit[^}]*transition:\s*none[\s\S]*?\.comment-author\s+a,\s*\.datetime\s+a\s*\{[^}]*transition:\s*none", re.I),
        "comment metadata and links must not stack inherited colour transitions",
    ),
    (
        re.compile(r"\.top-actions\s*\{[^}]*background-color:\s*var\(--glass-chrome\)[^}]*transition:[^}]*background-color\s+0\.3s[^}]*box-shadow\s+0\.3s", re.I | re.S),
        "top controls must animate an interpolable chrome colour with their edge shadow",
    ),
    (
        re.compile(r"\.mascot-reopen\s*\{[^}]*background-color:\s*var\(--glass-chrome\)[^}]*transition:[^}]*background-color\s+0\.3s[^}]*box-shadow\s+0\.3s", re.I | re.S),
        "mascot reopen control must animate an interpolable chrome colour with its edge shadow",
    ),
    (
        re.compile(r"height='40'\s+loading='lazy'\s+width='40'[\s\S]*?targetPixels\s*=\s*isReply\s*\?\s*64\s*:\s*96[\s\S]*?\(\[\?&\]sz=\)\\d\+", re.I),
        "published comment avatars must request high-resolution path, suffix, and sz URL variants",
    ),
    (
        re.compile(r"\[data-theme=\"dark\"\]\s+\.comments-wrapper\s+iframe#comment-editor\s*\{[\s\S]*?filter:\s*invert\(1\)\s+hue-rotate\(180deg\)\s+brightness\(1\)[\s\S]*?mix-blend-mode:\s*screen", re.I),
        "dark comment editor must use the cross-origin-safe CSS filter path",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*top:\s*16px[^}]*left:\s*10\.5px[^}]*width:\s*35px[^}]*height:\s*35px[\s\S]*?const\s+LOWER_AVATAR_EDITOR_HEIGHT\s*=\s*220[\s\S]*?settledEditorHeight\s*=\s*parsed[\s\S]*?setProperty\('--comment-editor-height',\s*parsed\s*\+\s*'px'\)", re.I | re.S),
        "editor height updates must not move the fixed upper avatar probe",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*-webkit-backdrop-filter:\s*invert\(0\)\s+hue-rotate\(0deg\)[^}]*backdrop-filter:\s*invert\(0\)\s+hue-rotate\(0deg\)[^}]*filter:\s*url\(\"#comment-avatar-presence\"\)[^}]*\}[\s\S]*?\[data-theme=\"dark\"\]\s+\.comment-avatar-window:not\(\[hidden\]\)\s*\{[^}]*-webkit-backdrop-filter:\s*invert\(1\)\s+hue-rotate\(180deg\)[^}]*backdrop-filter:\s*invert\(1\)\s+hue-rotate\(180deg\)", re.I | re.S),
        "both avatar probes must use the same pixel-synchronous presence filter",
    ),
    (
        re.compile(r"\.comment-avatar-window\s*\{[^}]*border-radius:\s*50%[^}]*\}[\s\S]*?\.comment-avatar-window-lower\[data-avatar-layout=\"lower\"\]:not\(\[hidden\]\)\s*\{[^}]*display:\s*block[^}]*top:\s*69px[^}]*filter:\s*url\(\"#comment-avatar-presence\"\)[\s\S]*?\.comment-avatar-window\[data-avatar-layout=\"lower\"\]:not\(\.comment-avatar-window-lower\):not\(\[hidden\]\)\s*\{[^}]*display:\s*none[\s\S]*?@media\s*\(max-width:\s*600px\)\s*\{[\s\S]*?\.comment-avatar-window-lower\[data-avatar-layout=\"lower\"\]:not\(\[hidden\]\)\s*\{[^}]*top:\s*94px", re.I | re.S),
        "lower layout must disable the upper probe and keep one rounded profile-aware slot",
    ),
    (
        re.compile(r"avatarLowerWindow\.dataset\.avatarLayout\s*=\s*parsed\s*>=\s*LOWER_AVATAR_EDITOR_HEIGHT\s*\?\s*'lower'\s*:\s*'upper';\s*avatarLowerWindow\.hidden\s*=\s*!avatarWindow\s*\|\|\s*avatarWindow\.hidden\s*\|\|\s*parsed\s*<\s*LOWER_AVATAR_EDITOR_HEIGHT", re.I | re.S),
        "lower avatar probe visibility must follow every confirmed editor height change",
    ),
    (
        re.compile(r"<filter[^>]*height='100%'[^>]*id='comment-avatar-presence'[^>]*width='100%'[^>]*x='0'[^>]*y='0'[^>]*>[\s\S]*?<feBlend[^>]*result='avatarChroma'[^>]*/>[\s\S]*?<feColorMatrix[^>]*result='avatarColorSeed'[^>]*values='1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  20 20 20 0 -2\.2'[^>]*/>[\s\S]*?<feComponentTransfer[^>]*in='avatarColorSeed'[^>]*result='avatarColorPresence'>[\s\S]*?<feMorphology[^>]*in='avatarColorPresence'[^>]*operator='erode'[^>]*radius='2'[^>]*result='avatarSolidColor'[^>]*/>[\s\S]*?<feMorphology[^>]*in='avatarSolidColor'[^>]*operator='dilate'[^>]*radius='20'[^>]*/>[\s\S]*?<feComposite[^>]*in='SourceGraphic'[^>]*operator='in'[^>]*/>[\s\S]*?</filter>", re.I),
        "avatar presence must reject thin profile chrome before expanding the 35px mask",
    ),
    (
        re.compile(r"\[data-theme=\"dark\"\]\s+#custom-comment-form-container\[data-editor-state=\"loading\"\]\s+\.comment-avatar-window:not\(\[hidden\]\),\s*\[data-theme=\"dark\"\]\s+#custom-comment-form-container\[data-editor-state=\"settling\"\]\s+\.comment-avatar-window:not\(\[hidden\]\)\s*\{[^}]*opacity:\s*0", re.I | re.S),
        "avatar correction must remain visible throughout the closing animation",
    ),
    (
        re.compile(r"avatarWindow\.dataset\.avatarLayout\s*=\s*parsed\s*>=\s*LOWER_AVATAR_EDITOR_HEIGHT\s*\?\s*'lower'\s*:\s*'upper'[\s\S]*?avatarWindow\.dataset\.avatarLayout\s*=\s*settledEditorHeight\s*>=\s*LOWER_AVATAR_EDITOR_HEIGHT\s*\?\s*'lower'\s*:\s*'upper'", re.I),
        "avatar layout state must stay synchronized before and after iframe creation",
    ),
    (
        re.compile(r"\.comments-wrapper\s+iframe#comment-editor\s*\{[\s\S]*?transition:\s*height\s+0\.24s\s+var\(--ease-out\),\s*opacity\s+0\.22s\s+var\(--ease-out\);?", re.I),
        "comment iframe compositing must switch atomically without a discrete transition",
    ),
    (
        re.compile(r"const\s+prepareEditorReload\s*=\s*\(iframe,\s*replyReload\s*=\s*false,\s*preserveAvatarLayer\s*=\s*replyReload\)\s*=>[\s\S]*?replyReloadPending\s*=\s*replyReload[\s\S]*?keepAvatarWindowMounted\s*=\s*preserveAvatarLayer[\s\S]*?if\s*\(!replyReload\)[\s\S]*?settledEditorHeight\s*=\s*MIN_EDITOR_HEIGHT[\s\S]*?setProperty\('--comment-editor-height',\s*MIN_EDITOR_HEIGHT\s*\+\s*'px'\)[\s\S]*?iframe\.setAttribute\(\"height\",\s*\"66\"\)[\s\S]*?iframe\.removeAttribute\(\"data-resized\"\)", re.I),
        "identity reloads must reset geometry while reply reloads keep the confirmed frame",
    ),
    (
        re.compile(r"#custom-comment-form-container\[data-editor-state=\"loading\"\]\s+iframe#comment-editor\s*\{[^}]*opacity:\s*0[\s\S]*?const\s+restoreEditorVisibility\s*=\s*\(iframe,\s*token\)\s*=>\s*\{\s*if\s*\(!iframe\s*\|\|\s*token\s*!==\s*formActionToken\s*\|\|\s*editorReloadPending\)\s*return;\s*customFormContainer\.classList\.remove\(\"is-relocating\"\)", re.I),
        "comment iframe must remain hidden until its confirmed reload finishes",
    ),
    (
        re.compile(r"\.comment-editor-loading\s*\{[^}]*display:\s*none[^}]*position:\s*absolute[^}]*z-index:\s*4[^}]*inset:\s*0[^}]*pointer-events:\s*none[^}]*background:\s*var\(--bg-color\)[\s\S]*?#custom-comment-form-container\.is-expanded\[data-editor-state=\"loading\"\]\s+\.comment-editor-loading,\s*#custom-comment-form-container\.is-expanded\[data-editor-state=\"settling\"\]\s+\.comment-editor-loading,\s*#custom-comment-form-container\.is-expanded\.is-loading-mask\s+\.comment-editor-loading,\s*#custom-comment-form-container\.is-expanded\.is-relocating\s+\.comment-editor-loading\s*\{[^}]*display:\s*flex[\s\S]*?\.comment-editor-loading::before\s*\{\s*content:\s*\"加载中\"[\s\S]*?\.comment-editor-loading::after\s*\{[^}]*animation:\s*comment-editor-loading-runner\s+1\.05s\s+linear\s+infinite", re.I | re.S),
        "loading mask must show localized text and an indeterminate runner above every editor layer",
    ),
    (
        re.compile(r"editorLoadingMask\s*=\s*formInner\.querySelector\('\.comment-editor-loading'\)[\s\S]*?document\.createElement\('span'\)[\s\S]*?className\s*=\s*'comment-editor-loading'[\s\S]*?setAttribute\('role',\s*'status'\)[\s\S]*?syncEditorLoadingText\(\)", re.I),
        "loading mask must be mounted with accessible status text before the editor is revealed",
    ),
    (
        re.compile(r"applyEditorHeight\(iframe,\s*measuredHeight\s*\|\|\s*settledEditorHeight,\s*true\)[\s\S]*?editorReloadPending\s*=\s*false[\s\S]*?setEditorState\(\"settling\",\s*iframe\)[\s\S]*?restoreEditorVisibility\(iframe,\s*editorLoadToken\)[\s\S]*?scheduleEditorReveal\(iframe,\s*editorLoadToken\)", re.I),
        "confirmed editor load must paint behind the mask before the relocated iframe is revealed",
    ),
    (
        re.compile(r"scheduleEditorReveal\s*=\s*\(iframe,\s*token\)\s*=>\s*\{\s*requestAnimationFrame\(\(\)\s*=>\s*requestAnimationFrame\(\(\)\s*=>\s*\{[\s\S]*?editorState\s*!==\s*\"settling\"[\s\S]*?classList\.contains\(\"is-expanded\"\)[\s\S]*?setEditorLoading\(iframe,\s*false\)[\s\S]*?classList\.remove\(\"is-loading-mask\"\)[\s\S]*?iframe\.style\.removeProperty\(\"transition\"\)", re.I),
        "reply editor must keep its mask through two expanded compositor frames",
    ),
    (
        re.compile(r"const\s+relocateAndExpand\s*=\s*\(\)\s*=>\s*\{\s*if\s*\(actionToken\s*!==\s*formActionToken\)\s*return;[\s\S]*?if\s*\(!alreadyAtTop\)\s*customFormContainer\.classList\.add\(\"is-loading-mask\"\)[\s\S]*?const\s+relocateAndExpand\s*=\s*\(\)\s*=>\s*\{\s*if\s*\(actionToken\s*!==\s*formActionToken\)\s*return;[\s\S]*?customFormContainer\.classList\.add\(\"is-loading-mask\"\)", re.I),
        "reply relocation mask must mount after closing and before either destination paints",
    ),
    (
        re.compile(r"finishEditorLoad\s*=\s*iframe\s*=>\s*\{\s*if\s*\(!editorReloadPending\s*\|\|\s*!editorFrameLoaded", re.I),
        "a completed editor load must not settle twice and flash the loading mask",
    ),
    (
        re.compile(r"const\s+markEditorFrameReady\s*=\s*\(\)\s*=>\s*\{\s*editorFrameLoaded\s*=\s*true;[\s\S]*?editorResizeConfirmed\s*=\s*editorIframe\.getAttribute\(\"data-resized\"\)\s*===\s*\"true\";[\s\S]*?if\s*\(replyReloadPending\)\s*finishEditorLoad\(editorIframe\);\s*else\s+if\s*\(editorResizeConfirmed\)\s*scheduleEditorSettle\(editorIframe\)", re.I),
        "reply iframe load must reveal immediately while other reloads await confirmed resize",
    ),
    (
        re.compile(r"const\s+placeEditorInForm\s*=\s*\(iframe,\s*formInner\)\s*=>[\s\S]*?formInner\.insertBefore\(iframe,\s*avatarWindow\)[\s\S]*?formInner\.appendChild\(iframe\)", re.I),
        "comment editor must remain immediately before its avatar correction layer",
    ),
    (
        re.compile(r"const\s+mobileEditorUrlParts\s*=\s*src\s*=>[\s\S]*?new\s+URL\(parts\[0\],\s*window\.location\.href\)[\s\S]*?searchParams\.set\(\"m\",\s*\"1\"\)[\s\S]*?return\s*\[url\.href,\s*parts\[1\]\s*\|\|\s*\"\"\]", re.I),
        "comment editor URL must keep Blogger's mobile renderer without discarding its skin fragment",
    ),
    (
        re.compile(r"const\s+captureEditorUrl\s*=\s*iframe\s*=>\s*\{[\s\S]*?const\s+src\s*=\s*iframe\.getAttribute\(\"src\"\)[\s\S]*?editorUrlParts\s*=\s*mobileEditorUrlParts\(src\)", re.I),
        "comment editor URL must be captured from the Blogger-tokenized iframe src",
    ),
    (
        re.compile(r"const\s+setEditorSrc\s*=\s*\(iframe,\s*parentId\)\s*=>\s*\{[\s\S]*?\"&parentID=\"\s*\+\s*parentId[\s\S]*?if\s*\(iframe\.src\s*!==\s*src\)\s*\{\s*if\s*\(!editorReloadPending\)\s*prepareEditorReload\(iframe\);\s*iframe\.src\s*=\s*src", re.I),
        "comment editor src must be rebuilt from tokenized parts, compacted, and assigned only when changed",
    ),
    (
        re.compile(r"const\s+parentId\s*=\s*parentComment\s*&&\s*parentComment\.id\s*\?[\s\S]*?setEditorSrc\(iframe,\s*parentId\)", re.I),
        "replies must pass the parent comment id to the editor frame",
    ),
    (
        re.compile(r"detachEditorForReload\(iframe,\s*true\)[\s\S]*?setEditorSrc\(iframe,\s*parentId\)", re.I),
        "reply relocation must keep the confirmed frame and fast-load state",
    ),
    (
        re.compile(r"detachEditorForReload\(editorIframe,\s*false,\s*true\)[\s\S]*?commentsWrapper\.insertBefore\(customFormContainer,\s*mainComments\)", re.I),
        "reply return must preserve the composited avatar correction layer",
    ),
    (
        re.compile(r"document\.body\.addEventListener\(\"click\",\s*e\s*=>\s*\{\s*const\s+replyBtn\s*=\s*e\.target\.closest\(\"\.comment-reply\"\);\s*if\s*\(!replyBtn\)\s*return;\s*e\.preventDefault\(\);\s*e\.stopPropagation\(\)[\s\S]*?\},\s*true\)", re.I),
        "custom reply handling must capture the click before Blogger's native reply handler",
    ),
    (
        re.compile(r"typeof\s+moveParent\.moveBefore\s*===\s*\"function\"[\s\S]*?prepareEditorReload\(iframe,\s*true\)[\s\S]*?moveParent\.moveBefore\(customFormContainer,\s*moveTarget\)", re.I),
        "modern browsers must move the reply form without an intermediate iframe navigation",
    ),
    (
        re.compile(r"const\s+relocateAndExpand\s*=\s*\(\)\s*=>[\s\S]*?prepareEditorReload\(iframe,\s*true\)[\s\S]*?moveParent\.moveBefore\(customFormContainer,\s*moveTarget\)[\s\S]*?if\s*\(wasExpanded\)\s*\{\s*setFormExpanded\(false\);\s*afterFormClosed\(actionToken,\s*relocateAndExpand\)", re.I),
        "reply relocation must finish the old collapse before moving and reopening",
    ),
    (
        re.compile(r"iframe\.removeAttribute\('src'\)", re.I),
        "editor relocation must drop src via removeAttribute, never src='' (loads the page recursively)",
    ),
    (
        re.compile(r"replyBtn\.classList\.contains\(\"cancel-active\"\)\s*&&\s*commentToggleBtn[\s\S]*?commentToggleBtn\.click\(\);\s*return", re.I),
        "cancelled replies must reuse the stable main-toggle return path",
    ),
    (
        re.compile(r"let\s+mainToggleBusy\s*=\s*false;\s*let\s+queuedMainToggle\s*=\s*false[\s\S]*?if\s*\(mainToggleBusy\)\s*\{[\s\S]*?queuedMainToggle\s*=\s*!queuedMainToggle[\s\S]*?const\s+finishMainToggle\s*=\s*\(\)\s*=>[\s\S]*?commentToggleBtn\.click\(\)[\s\S]*?afterFormClosed\(actionToken,\s*finishMainToggle\)[\s\S]*?afterFormOpened\(actionToken,\s*finishMainToggle\)", re.I),
        "rapid main-toggle clicks must queue final intent until the current transition finishes",
    ),
    (
        re.compile(r"const\s+parentId\s*=\s*parentComment[\s\S]*?let\s+replyNavigationStarted\s*=\s*false[\s\S]*?if\s*\(iframe\s*&&\s*canPreserveFrame\)\s*\{\s*prepareEditorReload\(iframe,\s*true\);[\s\S]*?setEditorSrc\(iframe,\s*parentId\);\s*replyNavigationStarted\s*=\s*true;[\s\S]*?const\s+relocateAndExpand", re.I),
        "reply iframe navigation must overlap the close transition before relocation",
    ),
    (
        re.compile(r"const\s+setMainFormState\s*=\s*expanded\s*=>[\s\S]*?commentToggleBtn\.setAttribute\(\"aria-expanded\",\s*expanded\s*\?\s*\"true\"\s*:\s*\"false\"\)", re.I),
        "main comment toggle aria-expanded must stay in sync with the form state",
    ),
    (
        re.compile(r"gear\.id\s*=\s*'mascot-settings';[\s\S]*?gear\.setAttribute\('aria-controls',\s*'mascot-menu'\);[\s\S]*?topActions\.insertBefore\(gear,\s*topActions\.firstChild\)", re.I),
        "mascot settings gear must live in the top toggle bar and control its menu",
    ),
    (
        re.compile(r"menu\.id\s*=\s*'mascot-menu';[\s\S]*?menu\.setAttribute\('aria-hidden',\s*'true'\);[\s\S]*?menu\.setAttribute\('inert',\s*''\);[\s\S]*?document\.body\.appendChild\(menu\)", re.I),
        "mascot menu must be created hidden and inert as a body-level popover",
    ),
    (
        re.compile(r"menu\.setAttribute\('aria-hidden',\s*open\s*\?\s*'false'\s*:\s*'true'\);[\s\S]*?if\s*\(open\)\s*menu\.removeAttribute\('inert'\);[\s\S]*?else\s*menu\.setAttribute\('inert',\s*''\)", re.I),
        "mascot menu aria-hidden and inert must stay in sync with visual open state",
    ),
    (
        re.compile(r"if\s*\(!open\s*&&\s*restoreFocus\s*&&\s*document\.activeElement\s*&&\s*menu\.contains\(document\.activeElement\)\)\s*gear\.focus\(\)", re.I),
        "mascot menu must return focus when closing from inside the menu",
    ),
    (
        re.compile(r"if\s*\(btn\.getAttribute\('data-act'\)\s*===\s*'hide'\)\s*\{[\s\S]*?menuOpen\(false,\s*false\);[\s\S]*?hide\(\);[\s\S]*?reopen\.focus\(\)", re.I),
        "hiding the mascot from its menu must move focus to the reopen button",
    ),
    (
        re.compile(r"document\.addEventListener\('click',\s*function\s*\(\)\s*\{[\s\S]*?menuOpen\(false,\s*true\)", re.I),
        "outside-click mascot menu close must restore focus when needed",
    ),
    (
        re.compile(r"var\s+vy\s*=\s*Math\.max\(gap,\s*Math\.min\(gr\.bottom\s*\+\s*gap,\s*vh\s*-\s*mh\s*-\s*gap\)\)", re.I),
        "mascot menu top must stay inside short viewports",
    ),
    (
        re.compile(r"var\s+menuResizeRAF\s*=\s*0[\s\S]*?if\s*\(menuResizeRAF\s*\|\|\s*!menu\.classList\.contains\('is-open'\)\)\s*return;[\s\S]*?menuResizeRAF\s*=\s*requestAnimationFrame", re.I),
        "open mascot menu resize work must be coalesced with requestAnimationFrame",
    ),
    (
        re.compile(r"imgEl\.addEventListener\('pointerdown',\s*function\(e\)\s*\{\s*if\s*\(e\.isPrimary\s*===\s*false\s*\|\|\s*\(e\.pointerType\s*===\s*'mouse'\s*&&\s*e\.button\s*!==\s*0\)\)\s*return;", re.I),
        "mascot drag must ignore secondary pointers and non-left mouse buttons",
    ),
    (
        re.compile(r"reopen\.addEventListener\('pointerdown',\s*function\(e\)\s*\{\s*if\s*\(e\.isPrimary\s*===\s*false\s*\|\|\s*\(e\.pointerType\s*===\s*'mouse'\s*&&\s*e\.button\s*!==\s*0\)\)\s*return;", re.I),
        "mascot reopen drag must ignore secondary pointers and non-left mouse buttons",
    ),
    (
        re.compile(r"let\s+replyFoldId\s*=\s*0", re.I),
        "reply-fold wrappers must get stable generated ids",
    ),
    (
        re.compile(r"let\s+restructuringComments\s*=\s*false", re.I),
        "comment restructuring must guard against observer self-triggering",
    ),
    (
        re.compile(r"let\s+observedCommentsContainer\s*=\s*null", re.I),
        "comment observer must remember the container it observes",
    ),
    (
        re.compile(r"const\s+commentScope\s*=\s*observedCommentsContainer\s*\|\|\s*document[\s\S]*?localizeCommentDates\(commentScope\)[\s\S]*?commentScope\.querySelectorAll\(\"\.avatar-image-container", re.I),
        "comment restructuring must query only its observed container",
    ),
    (
        re.compile(r"commentScope\.querySelectorAll\(\"\.item-control a:not\(\[data-cleaned-del\]\)\"\)[\s\S]*?btn\.dataset\.cleanedDel\s*=\s*\"true\";\s*if\s*\(lowerText", re.I),
        "comment actions must be marked after their first delete-label check",
    ),
    (
        re.compile(r"if\s*\(restructuringComments\s*\|\|\s*restructureFrame\)\s*return", re.I),
        "comment observer callbacks must ignore active or queued restructuring",
    ),
    (
        re.compile(r"let\s+restructureFrame\s*=\s*0[\s\S]*?restructureFrame\s*=\s*requestAnimationFrame\([\s\S]*?restructureComments\(\)", re.I),
        "comment mutations must be coalesced with requestAnimationFrame",
    ),
    (
        re.compile(r"commentObserver\.disconnect\(\)", re.I),
        "comment observer must pause while restructuring writes DOM",
    ),
    (
        re.compile(r"\}\s*finally\s*\{[\s\S]*?commentObserver\.observe\(observedCommentsContainer,\s*\{\s*childList:\s*true,\s*subtree:\s*true\s*\}\)", re.I),
        "comment observer must resume after restructuring, even after failures",
    ),
    (
        re.compile(r"wrapper\.id\s*=\s*\"reply-thread-\"\s*\+\s*\(\+\+replyFoldId\)", re.I),
        "reply-fold wrapper ids must be unique per thread",
    ),
    (
        re.compile(r"wrapper\.setAttribute\(\"aria-hidden\",\s*\"true\"\)", re.I),
        "collapsed reply threads must be hidden from assistive technology",
    ),
    (
        re.compile(r"wrapper\.setAttribute\(\"inert\",\s*\"\"\)", re.I),
        "collapsed reply threads must be inert so hidden controls cannot receive focus",
    ),
    (
        re.compile(r"const\s+setReplyThreadState\s*=\s*expanded\s*=>", re.I),
        "reply thread state changes must be centralized",
    ),
    (
        re.compile(r"wrapper\.querySelectorAll\('a,\s*button,\s*input,\s*textarea,\s*select,\s*\[tabindex\]'\)", re.I),
        "collapsed reply threads must scan focusable descendants",
    ),
    (
        re.compile(r"data-rinuan-tabindex", re.I),
        "reply thread focus management must preserve existing tabindex values",
    ),
    (
        re.compile(r"el\.setAttribute\(\"tabindex\",\s*\"-1\"\)", re.I),
        "collapsed reply thread descendants must leave the tab order",
    ),
    (
        re.compile(r"wrapper\.removeAttribute\(\"inert\"\)", re.I),
        "expanded reply threads must remove inert",
    ),
    (
        re.compile(r"let\s+measureArticleRAF\s*=\s*0[\s\S]*?const\s+scheduleMeasureArticle\s*=\s*function\s*\(\)\s*\{[\s\S]*?requestAnimationFrame\(measureArticle\)", re.I),
        "reading progress article measurement must be coalesced with requestAnimationFrame",
    ),
    (
        re.compile(r"let\s+refreshProgressAfterMeasure\s*=\s*function\s*\(\)\s*\{\s*\}[\s\S]*?articleDocBottom\s*=[\s\S]*?refreshProgressAfterMeasure\(\);[\s\S]*?refreshProgressAfterMeasure\s*=\s*onScroll", re.I),
        "reading progress must refresh after a coalesced article measurement",
    ),
    (
        re.compile(r"new\s+ResizeObserver\(scheduleMeasureArticle\)\.observe\(articleBody\)", re.I),
        "reading progress ResizeObserver must use scheduled article measurement",
    ),
    (
        re.compile(r"var\s+measureArtRAF\s*=\s*0[\s\S]*?var\s+scheduleMeasureArt\s*=\s*function\s*\(\)\s*\{[\s\S]*?requestAnimationFrame\(measureArt\)", re.I),
        "mascot article measurement must be coalesced with requestAnimationFrame",
    ),
    (
        re.compile(r"var\s+refreshMascotProgressAfterMeasure\s*=\s*function\s*\(\)\s*\{\s*\}[\s\S]*?artBottom\s*=[\s\S]*?refreshMascotProgressAfterMeasure\(\);[\s\S]*?refreshMascotProgressAfterMeasure\s*=\s*scheduleMascotProgress", re.I),
        "mascot article progress must refresh after a coalesced measurement",
    ),
    (
        re.compile(r"new\s+ResizeObserver\(scheduleMeasureArt\)\.observe\(mascotArticle\)", re.I),
        "mascot article ResizeObserver must use scheduled measurement",
    ),
    (
        re.compile(r"setReplyThreadState\(false\)[\s\S]*?toggleBtn\.onclick", re.I),
        "reply folds must initialize collapsed focus state",
    ),
    (
        re.compile(r"toggleBtn\.setAttribute\(\"aria-controls\",\s*wrapper\.id\)", re.I),
        "reply toggle buttons must point at the controlled reply thread",
    ),
    (
        re.compile(r"toggleBtn\.setAttribute\(\"aria-expanded\",\s*expanded\s*\?\s*\"true\"\s*:\s*\"false\"\)", re.I),
        "reply toggle aria-expanded must stay in sync with visual expansion",
    ),
    (
        re.compile(r"<link\s+href='https://fonts\.gstatic\.com'\s+rel='preconnect'\s+crossorigin='anonymous'\s*/>", re.I),
        "Google font file origin must stay preconnected without blocking first paint",
    ),
    (
        re.compile(r"<link\s+href='https://fonts\.googleapis\.com'\s+rel='preconnect'\s*/>", re.I),
        "Google font stylesheet origin must stay preconnected without blocking first paint",
    ),
    (
        re.compile(r"var\s+link\s*=\s*document\.createElement\('link'\)[\s\S]*?link\.rel\s*=\s*'stylesheet'[\s\S]*?requestIdleCallback\(loadFonts,\s*\{\s*timeout:\s*3000\s*\}\)", re.I),
        "Google Fonts stylesheet must remain dynamically idle-loaded",
    ),
    (
        re.compile(r"<b:if\s+cond='data:i == 0'>\s*<img[^>]*fetchpriority='high'[^>]*loading='eager'", re.I | re.S),
        "first listing cover image must stay eager/high for LCP",
    ),
    (
        re.compile(r"<b:else/>\s*<img(?![^>]*fetchpriority='high')[^>]*loading='lazy'", re.I | re.S),
        "non-first listing cover images must stay lazy and not high priority",
    ),
    (
        re.compile(r"const\s+isPriorityImage\s*=\s*idx\s*===\s*0\s*&&\s*isFullPostView", re.I),
        "body image delivery must identify the single full-post priority image",
    ),
    (
        re.compile(r"img\.setAttribute\('loading',\s*isPriorityImage\s*\?\s*'eager'\s*:\s*'lazy'\)", re.I),
        "body image loading must stay synchronized with priority image selection",
    ),
    (
        re.compile(r"img\.setAttribute\('fetchpriority',\s*isPriorityImage\s*\?\s*'high'\s*:\s*'low'\)", re.I),
        "body image fetchpriority must stay synchronized with loading mode",
    ),
    (
        re.compile(r"class='error-mascot'[^>]*width='400'[^>]*height='600'", re.I),
        "404 mascot markup must use the real chibi image dimensions",
    ),
    (
        re.compile(r"<img class=\"mascot-img\"[^>]*width=\"400\" height=\"600\"", re.I),
        "runtime mascot image must use the real chibi image dimensions",
    ),
    (
        re.compile(r"#comment-popup\s*\{(?=[^}]*position\s*:\s*absolute)(?=[^}]*width\s*:\s*1px)(?=[^}]*height\s*:\s*1px)(?=[^}]*overflow\s*:\s*hidden)", re.I | re.S),
        "comment action popup must stay visually hidden and layout-stable",
    ),
    (
        re.compile(r"<iframe[^>]*aria-hidden='true'[^>]*height='1'[^>]*id='comment-actions'[^>]*tabindex='-1'[^>]*width='1'", re.I | re.S),
        "comment action iframe must keep fixed hidden dimensions",
    ),
    (
        re.compile(r"parent\.closest\s*&&\s*parent\.closest\('pre,\s*code,\s*kbd,\s*samp,\s*textarea,\s*\[contenteditable\]'\)", re.I),
        "OpenCC text walk must skip code/preformatted/editable text",
    ),
    (
        re.compile(r"window\.__rinuanToVariant\)\s*\{\s*window\.__rinuanToVariant\(list\);", re.I),
        "related-post titles must follow the current Simplified/Traditional mode",
    ),
    (
        re.compile(r"appendedPosts\.forEach\(post\s*=>\s*window\.__rinuanToVariant\(post\)\)", re.I),
        "infinite-scroll posts must convert after insertion, not while held in a temporary container",
    ),
    (
        re.compile(r"let\s+infiniteObserver\s*=\s*null", re.I),
        "infinite scroll observer must have a tracked lifecycle",
    ),
    (
        re.compile(r"infiniteObserver\.disconnect\(\);\s*infiniteObserver\s*=\s*null", re.I),
        "infinite scroll observer must disconnect when no more pages remain",
    ),
    (
        re.compile(r"infiniteObserver\s*=\s*new\s+IntersectionObserver", re.I),
        "infinite scroll observer must be stored so it can be disconnected",
    ),
    (
        re.compile(r"infiniteObserver\.observe\(sentinel\)", re.I),
        "infinite scroll sentinel must be observed through the tracked observer",
    ),
    (
        re.compile(r"\.post-outer\s*\{(?=[^}]*min-width\s*:\s*0\b)(?=[^}]*max-width\s*:\s*100%)", re.I | re.S),
        ".post-outer must keep min-width: 0 and max-width: 100% so long titles cannot widen the viewport",
    ),
    (
        re.compile(r"\.blog-posts,\s*\.post-outer\s*>\s*\*\s*\{(?=[^}]*min-width\s*:\s*0\b)(?=[^}]*max-width\s*:\s*100%)", re.I | re.S),
        ".blog-posts and direct post children must keep min-width: 0 and max-width: 100%",
    ),
    (
        re.compile(r"dragFrame\s*=\s*requestAnimationFrame\(applyDragFrame\)", re.I),
        "mascot pointer movement must be coalesced per animation frame",
    ),
    (
        re.compile(r"reDragFrame\s*=\s*requestAnimationFrame\(applyReopenDragFrame\)", re.I),
        "mascot handle movement must be coalesced per animation frame",
    ),
    (
        re.compile(r"@media\s*\(pointer:\s*coarse\)\s*\{[\s\S]*?\.comments\s+\.item-control\s+a,[\s\S]*?\.reply-toggle-btn\s*\{[\s\S]*?min-height:\s*44px", re.I),
        "comment touch controls must keep a 44px target",
    ),
    (
        re.compile(r"\.comments\s+\.item-control\s+a:focus-visible\s*\{[\s\S]*?background:\s*var\(--btn-bg\)", re.I),
        "comment actions must show keyboard focus feedback",
    ),
    (
        re.compile(r"\.reply-toggle-btn:focus-visible\s*\{[\s\S]*?background:\s*var\(--accent-bg\)", re.I),
        "reply toggles must show keyboard focus feedback",
    ),
    (
        re.compile(r"window\.loadRelatedPosts\s*=\s*\(\)\s*=>\s*\{\s*\}", re.I),
        "expired related-post responses must land on a safe callback",
    ),
    (
        re.compile(r"script\.onload\s*=\s*\(\)\s*=>\s*\{[\s\S]*?if\s*\(!loaded\)\s*script\.remove\(\)[\s\S]*?flush\(loaded\)", re.I),
        "failed OpenCC loads must remove their script node",
    ),
    (
        re.compile(r"const\s+notCategory\s*=\s*new\s+Set\([\s\S]*?notCategory\.has\(", re.I),
        "category exclusions must use Set membership",
    ),
    (
        re.compile(r"const\s+seen\s*=\s*new\s+Set\(\)[\s\S]*?seen\.has\([\s\S]*?seen\.add\(", re.I),
        "infinite-scroll deduplication must use Set membership",
    ),
    (
        re.compile(r"if\s*\(mo\s*<\s*1\s*\|\|\s*mo\s*>\s*12\s*\|\|\s*d\s*<\s*1\s*\|\|\s*d\s*>\s*new\s+Date\(y,\s*mo,\s*0\)\.getDate\(\)\)", re.I),
        "card dates must reject invalid month and day values",
    ),
)


def minify_css(m):
    css = m.group(2)
    # Preserve the leading Blogger <Variable> definitions comment: Blogger parses it
    # (stale-font override), but rcssmin would strip it like any other comment.
    prefix = ""
    var_m = re.match(r"\s*(/\*.*?\*/)", css, re.S)
    if var_m and "<Variable" in var_m.group(1):
        prefix = var_m.group(1) + "\n"
        css = css[var_m.end():]
    return m.group(1) + prefix + rcssmin.cssmin(css) + m.group(3)


def minify_js(m):
    return "//<![CDATA[\n" + rjsmin.jsmin(m.group(1)).strip() + "\n//]]>"


def normalize_comment(value):
    return " ".join(part.strip() for part in value.splitlines()).strip()


def iter_theme_comments(text):
    for match in re.finditer(r"<!--(.*?)-->|/\*(.*?)\*/", text, re.S):
        value = next(group for group in match.groups() if group is not None)
        if "<Variable" in value:
            continue
        yield text.count("\n", 0, match.start()) + 1, normalize_comment(value)
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        match = re.match(r"//(.*)$", stripped)
        if not match:
            match = re.search(r"\s//\s+(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if value not in ("<![CDATA[", "]]>"):
            yield line_number, value


def iter_python_comments(text):
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT and not token.string.startswith("#!"):
            yield token.start[0], token.string[1:].strip()
    module = ast.parse(text)
    docstring = ast.get_docstring(module, clean=False)
    if docstring:
        yield 1, normalize_comment(docstring)


def iter_markdown_code_comments(text):
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            continue
        match = re.search(r"(?:^|\s)#\s+(.*)$", line)
        if match:
            yield line_number, match.group(1).strip()


def validate_comment_style():
    paths = [SRC, BASE / "minify.py"]
    paths.extend(sorted(BASE.glob("*.md")))
    paths.extend(sorted((BASE / "mascot").glob("*.md")))
    count = 0
    failures = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        if path == SRC:
            comments = iter_theme_comments(source)
        elif path.suffix == ".py":
            comments = iter_python_comments(source)
        else:
            comments = iter_markdown_code_comments(source)
        for line_number, value in comments:
            if not value:
                continue
            count += 1
            if CJK_RE.search(value):
                failures.append(f"{path.name}:{line_number} comment must use English")
            if len(value) > COMMENT_MAX_CHARS:
                failures.append(
                    f"{path.name}:{line_number} comment is {len(value)} characters; "
                    f"limit is {COMMENT_MAX_CHARS}"
                )
    if failures:
        raise RuntimeError("comment checks failed: " + "; ".join(failures))
    return count


def strip_comments_for_checks(text):
    text = re.sub(
        r"(//<!\[CDATA\[)(.*?)(//\]\]>)",
        lambda match: match.group(1) + rjsmin.jsmin(match.group(2)) + match.group(3),
        text,
        flags=re.S,
    )
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def validate_xml(path):
    xml.dom.minidom.parse(str(path))


def validate_xml_text(text):
    doc = xml.dom.minidom.parseString(text)
    doc.unlink()


def validate_js_blocks(path, text, node):
    cdata_blocks = SCRIPT_BLOCK_RE.findall(text)
    inline_blocks = []
    template_blocks = 0
    for _attrs, body in INLINE_SCRIPT_RE.findall(text):
        stripped = body.strip()
        if not stripped or stripped.startswith("//<![CDATA["):
            continue
        candidate = stripped
        if any(marker in stripped for marker in ("<data:", "<b:", "&#")):
            candidate = html.unescape(candidate)
            candidate = re.sub(r"<(?:data|b):[^>]+/>", "null", candidate)
            if re.search(r"<(?:data|b):", candidate):
                raise RuntimeError(f"{path.name} has an unsupported templated inline script")
            template_blocks += 1
        inline_blocks.append(candidate)
    blocks = cdata_blocks + inline_blocks
    if not blocks:
        return (0, 0, template_blocks)
    check = """
const fs = require('fs');
const blocks = JSON.parse(fs.readFileSync(0, 'utf8'));
for (let i = 0; i < blocks.length; i++) {
  try {
    new Function(blocks[i]);
  } catch (err) {
    console.error(`script block ${i + 1}: ${err.message}`);
    process.exit(1);
  }
}
"""
    result = subprocess.run(
        [node, "-e", check],
        input=json.dumps(blocks),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{path.name} JS parse failed: {detail}")
    return (len(cdata_blocks), len(inline_blocks), template_blocks)


def find_node():
    candidates = []
    env_node = os.environ.get("NODE_BINARY")
    if env_node:
        candidates.append(Path(env_node).expanduser())
    path_node = shutil.which("node")
    if path_node:
        candidates.append(Path(path_node))
    candidates.extend(
        [
            BASE / "node_modules" / ".bin" / "node",
            Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
            Path("/opt/homebrew/bin/node"),
            Path("/usr/local/bin/node"),
        ]
    )
    for candidate in candidates:
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        except OSError:
            continue
    raise RuntimeError("node not found; install Node.js or set NODE_BINARY=/path/to/node")


def validate_dom_ids(text):
    seen = {}
    doc = xml.dom.minidom.parseString(text)
    try:
        for el in doc.getElementsByTagName("*"):
            if el.tagName.startswith("b:"):
                continue
            if el.hasAttribute("id"):
                id_ = el.getAttribute("id")
                seen[id_] = seen.get(id_, 0) + 1
        duplicates = sorted(f"{id_}:{count}" for id_, count in seen.items() if count > 1)
        if duplicates:
            raise RuntimeError("duplicate literal DOM id attributes: " + ", ".join(duplicates))
        return len(seen)
    finally:
        doc.unlink()


def validate_local_mascot_assets(text):
    assets = sorted(set(LOCAL_MASCOT_CDN_RE.findall(text)))
    missing = [asset for asset in assets if not (BASE / asset).exists()]
    if missing:
        raise RuntimeError("missing local mascot assets: " + ", ".join(missing))
    return len(assets)


def split_selectors(selector_text):
    selectors = []
    start = 0
    depth = 0
    for i, char in enumerate(selector_text):
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char == "," and depth == 0:
            selectors.append(selector_text[start:i])
            start = i + 1
    selectors.append(selector_text[start:])
    normalized = []
    for selector in selectors:
        selector = re.sub(r"\s*([>+~])\s*", r" \1 ", selector.strip())
        if selector:
            normalized.append(" ".join(selector.split()))
    return normalized


def parse_css_declarations(body):
    declarations = {}
    for chunk in body.split(";"):
        if ":" not in chunk:
            continue
        prop, value = chunk.split(":", 1)
        prop = prop.strip().lower()
        value = " ".join(value.strip().lower().split())
        if prop:
            declarations[prop] = value
    return declarations


def parse_css_rules(text):
    match = BSKIN_RE.search(text)
    if not match:
        raise RuntimeError("missing <b:skin> CDATA block")
    css = re.sub(r"/\*.*?\*/", "", match.group(1), flags=re.S)
    rules = []
    start = 0
    while True:
        open_brace = css.find("{", start)
        if open_brace < 0:
            break
        prelude = css[start:open_brace].strip()
        depth = 1
        quote = None
        escaped = False
        end = open_brace + 1
        while end < len(css) and depth:
            char = css[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in ("'", '"'):
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            end += 1
        if depth:
            raise RuntimeError("unbalanced CSS block")
        if prelude and not prelude.startswith("@"):
            selectors = split_selectors(prelude)
            if selectors:
                body = css[open_brace + 1:end - 1]
                rules.append((selectors, parse_css_declarations(body)))
        start = end
    return rules


def validate_css_contracts(text):
    rules = parse_css_rules(text)
    failures = []
    for selector, required in CSS_CONTRACT_CHECKS:
        cascaded = {}
        for selectors, rule_declarations in rules:
            if selector in selectors:
                cascaded.update(rule_declarations)
        if not all(cascaded.get(prop) == value for prop, value in required.items()):
            missing = ", ".join(f"{prop}: {value}" for prop, value in required.items())
            failures.append(f"{selector} must include {missing}")
    if failures:
        raise RuntimeError("CSS contract checks failed: " + "; ".join(failures))
    return len(CSS_CONTRACT_CHECKS)


def read_webp_size(path):
    data = path.read_bytes()
    if len(data) < 16 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise RuntimeError(f"{path} is not a WebP file")
    offset = 12
    while offset + 8 <= len(data):
        chunk = data[offset:offset + 4]
        size = int.from_bytes(data[offset + 4:offset + 8], "little")
        payload = data[offset + 8:offset + 8 + size]
        if chunk == b"VP8X" and len(payload) >= 10:
            width = 1 + int.from_bytes(payload[4:7], "little")
            height = 1 + int.from_bytes(payload[7:10], "little")
            return (width, height)
        if chunk == b"VP8L" and len(payload) >= 5:
            bits = int.from_bytes(payload[1:5], "little")
            return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        if chunk == b"VP8 " and len(payload) >= 10:
            return (
                int.from_bytes(payload[6:8], "little") & 0x3FFF,
                int.from_bytes(payload[8:10], "little") & 0x3FFF,
            )
        offset += 8 + size + (size % 2)
    raise RuntimeError(f"could not read WebP dimensions for {path}")


def validate_mascot_dimensions(text):
    assets = sorted(set(LOCAL_MASCOT_CDN_RE.findall(text)))
    checked = 0
    failures = []
    for asset in assets:
        if not asset.startswith("mascot/chibi/") or not asset.endswith(".webp"):
            continue
        path = BASE / asset
        if not path.exists():
            continue
        size = read_webp_size(path)
        checked += 1
        if size != (400, 600):
            failures.append(f"{asset} is {size[0]}x{size[1]}, expected 400x600")
    if failures:
        raise RuntimeError("mascot dimension checks failed: " + "; ".join(failures))
    return checked


def validate_theme_regressions(text):
    checked = strip_comments_for_checks(text)
    failures = [message for pattern, message in THEME_REGRESSION_CHECKS if pattern.search(checked)]
    failures.extend(
        message for pattern, message in THEME_REQUIRED_CHECKS if not pattern.search(checked)
    )
    if failures:
        raise RuntimeError("theme regression checks failed: " + "; ".join(failures))
    return len(THEME_REGRESSION_CHECKS) + len(THEME_REQUIRED_CHECKS)


def main():
    source_text = SRC.read_text(encoding="utf-8")
    validate_xml(SRC)
    comment_count = validate_comment_style()
    dom_id_count = validate_dom_ids(source_text)
    mascot_asset_count = validate_local_mascot_assets(source_text)
    css_contract_count = validate_css_contracts(source_text)
    mascot_dimension_count = validate_mascot_dimensions(source_text)
    regression_count = validate_theme_regressions(source_text)

    text = re.sub(
        r"(<b:skin><!\[CDATA\[)(.*?)(\]\]></b:skin>)",
        minify_css, source_text, flags=re.S,
    )

    text = re.sub(r"//<!\[CDATA\[(.*?)//\]\]>", minify_js, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = "\n".join(line.lstrip() for line in text.splitlines() if line.strip()) + "\n"

    validate_xml_text(text)
    if validate_dom_ids(text) != dom_id_count:
        raise RuntimeError("minification changed literal DOM ids")
    validate_css_contracts(text)
    validate_local_mascot_assets(text)
    validate_mascot_dimensions(text)
    validate_theme_regressions(text)

    node = find_node()
    src_cdata, src_inline, src_templates = validate_js_blocks(SRC, source_text, node)
    out_cdata, out_inline, out_templates = validate_js_blocks(OUT, text, node)
    js_status = (
        "JS valid: "
        f"theme.xml {src_cdata} CDATA + {src_inline} inline blocks "
        f"({src_templates} Blogger-templated), "
        f"theme.min.xml {out_cdata} CDATA + {out_inline} inline blocks "
        f"({out_templates} Blogger-templated)."
    )

    temp_out = OUT.with_suffix(OUT.suffix + ".tmp")
    try:
        temp_out.write_text(text, encoding="utf-8")
        temp_out.replace(OUT)
    finally:
        if temp_out.exists():
            temp_out.unlink()

    before, after = SRC.stat().st_size, OUT.stat().st_size
    print(f"theme.xml     {before:>7,} bytes")
    print(f"theme.min.xml {after:>7,} bytes  ({100 * (before - after) // before}% smaller)")
    print("Source/output XML valid.")
    print(f"DOM ids valid: {dom_id_count} literal ids, no duplicates.")
    print(f"CSS contracts valid: {css_contract_count} checks.")
    print(f"Local mascot assets valid: {mascot_asset_count} referenced files.")
    print(f"Mascot dimensions valid: {mascot_dimension_count} chibi WebP files.")
    print(f"Theme regression checks valid: {regression_count} checks.")
    print(f"Comments valid: {comment_count} concise English comments.")
    print(js_status)
    print("XML valid. Upload theme.min.xml to Blogger.")


if __name__ == "__main__":
    sys.exit(main())
