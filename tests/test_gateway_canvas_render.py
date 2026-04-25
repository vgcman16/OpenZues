from openzues.services.gateway_canvas_render import extract_canvas_shortcodes


def test_extract_canvas_shortcodes_builds_preview_from_ref() -> None:
    result = extract_canvas_shortcodes(
        'Before\n[embed ref="cv_123" title="Status" height="320" /]\nAfter'
    )

    assert result == {
        "text": "Before\n\nAfter",
        "previews": [
            {
                "kind": "canvas",
                "surface": "assistant_message",
                "render": "url",
                "url": "/__openclaw__/canvas/documents/cv_123/index.html",
                "viewId": "cv_123",
                "title": "Status",
                "preferredHeight": 320,
            }
        ],
    }


def test_extract_canvas_shortcodes_uses_explicit_url_and_ignores_fences() -> None:
    result = extract_canvas_shortcodes(
        "\n".join(
            [
                "```",
                '[embed ref="cv_ignored" /]',
                "```",
                '[embed url="/__openclaw__/canvas/documents/cv_456/index.html" /]',
            ]
        )
    )

    assert result["text"] == "```\n[embed ref=\"cv_ignored\" /]\n```\n"
    assert result["previews"] == [
        {
            "kind": "canvas",
            "surface": "assistant_message",
            "render": "url",
            "url": "/__openclaw__/canvas/documents/cv_456/index.html",
        }
    ]


def test_extract_canvas_shortcodes_leaves_invalid_targets_visible() -> None:
    text = '[embed ref="cv_123" target="sidebar" /]'

    assert extract_canvas_shortcodes(text) == {"text": text, "previews": []}
