APP_CSS = """
.display-tabs button:checked {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

.display-tabs button:checked label,
.display-tabs button:checked image {
    color: @accent_fg_color;
}

.idle-timeout button image {
    color: @window_fg_color;
    opacity: 1;
}
"""
