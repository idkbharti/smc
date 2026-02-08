"""
Original Pine Script:
export getStyle(string style) =>
    switch style
        '⎯⎯⎯' => line.style_solid
        '----' => line.style_dashed
        '····' => line.style_dotted
        => line.style_solid
"""

def get_style(style: str) -> str:
    """
    Maps a visual style string to a line style constant (represented as string here).
    """
    if style == '⎯⎯⎯':
        return 'solid'
    elif style == '----':
        return 'dashed'
    elif style == '····':
        return 'dotted'
    else:
        return 'solid'
