from typing import Any, Optional, Union

def substitute_variables(text : str, data : dict[str, Any]) -> str:
  if not "{" in text:
    return text

  result = ""
  var = ""
  in_var = False
  for char in text:
    if char == "{":
      in_var = True
    elif char == "}":
      if var in data:
        result += str(data[var])
      else:
        result += "{" + var + "}"
      in_var = False
      var = ""
    else:
      if in_var:
        var += char
      else:
        result += char

  return result

def _is_in_range(char : chr, start : Union[int, chr], end : Union[int, chr]):
  c = ord(char)

  if not isinstance(start, int):
    start = ord(start)
  if not isinstance(end, int):
    end = ord(end)

  return start <= c <= end

def contains_symbols(raw : str) -> (bool, Optional[str]):
  # Source: https://unicode-table.com/en/blocks/emoticons/

  ranges = {
    # Arrows
    "Simple arrows": ['←', '↙'],
    "Arrows with modifications": ['↚', '↯'],
    "Arrows with bent tips": ['↰', '↳'],
    "Keyboard symbols and circle arrows": ['↴', '↻'],
    "Harpoons": ['↼', '⇃'],
    "Paired arrows and harpoons": ['⇄', '⇌'],
    "Double arrows": ['⇍', '⇙'],
    "Miscellaneous arrows and keyboard symbols": ['⇚', '⇥'],
    "White arrows and keyboard symbols": ['⇦', '⇳'],
    "Miscellaneous arrows": ['⇴', '⇿'],

    # Supplemental Arrows-A
    "Arrows": ['⟰', '⟴'],
    "Long arrows": ['⟵', '⟿'],

    # Supplemental Arrows-B
    "Miscellaneous arrows 2": ['⤀', '⤘'],
    "Arrow tails": ['⤙', '⤜'],
    "Miscellaneous arrows 3": ['⤝', '⤦'],
    "Crossing arrows for knot theory": ['⤧', '⤲'],
    "Miscellaneous curved arrows": ['⤳', '⥁'],
    "Arrows combined with operators": ['⥂', '⥉'],
    "Double-barbed harpoons": ['⥊', '⥑'],
    "Modified harpoons": ['⥒', '⥡'],
    "Paired harpoons": ['⥢', '⥯'],
    "Miscellaneous arrow": ['⥰', '⥰'],
    "Arrows combined with relations": ['⥱', '⥻'],
    "Fish tails": ['⥼', '⥿'],

    # OCR
    "OCR-A": ['⑀', '⑅'],
    "MICR": ['⑆', '⑉'],
    "OCR": ['⑊', 0x245F],

    # Enclosed Alphanumerics
    "Circled numbers": ['①', '⑳'],
    "Parenthesized numbers": ['⑴', '⒇'],
    "Numbers period": ['⒈', '⒛'],
    "Parenthesized Latin letters": ['⒜', '⒵'],
    "Circled Latin letters": ['Ⓐ', 'ⓩ'],
    "Additional circled number": ['⓪', '⓪'],
    "White on black circled numbers": ['⓫', '⓴'],
    "Double circled numbers": ['⓵', '⓾'],
    "Additional white on black circled number": ['⓿', '⓿'],

    # Box Drawing
    "Light and heavy solid lines": ['─', '┃'],
    "Light and heavy dashed lines": ['┄', '┋'],
    "Light and heavy line box components": ['┌', '╋'],
    "Light and heavy dashed lines 2": ['╌', '╏'],
    "Double lines": ['═', '║'],
    "Light and double line box components": ['╒', '╬'],
    "Character cell arcs": ['╭', '╰'],
    "Character cell diagonals": ['╱', '╳'],
    "Light and heavy half lines": ['╴', '╻'],
    "Mixed light and heavy lines": ['╼', '╿'],

    # Block Elements
    "Block elements": ['▀', '▐'],
    "Shade characters": ['░', '▓'],
    "Block elements 2": ['▔', '▕'],
    "Terminal graphic characters": ['▖', '▟'],

    # Geometric shapes
    "Geometric shapes": ['■', '◯'],
    "Control code graphics": ['◰', '◷'],
    "Geometric shapes 2": ['◸', '◿'],

    # Miscellaneous Symbols
    "Miscellaneous Symbols": ['☀', '⛿'],
    "Dingbats": ['✀', '➿'],
    "Mahjong Tiles": ['🀀', '🀯'],
    "Domino Tiles": ['🀰', '🂟'],
    "Playing Cards": ['🂠', '🃿'],
    "Chess Symbols": ['🨀', '🩟'],
    "Xiangqi symbols": ['🩠', '🩯'],

    # Braille Patterns
    "Braille patterns": ['⠀', '⣿']
  }

  for char in raw:
    for name, symbol_range in ranges.items():
      if _is_in_range(char, symbol_range[0], symbol_range[1]):
        return True, name
  return False, None
