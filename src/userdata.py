from __future__ import annotations
from typing import Any, Union

class Userdata:
  def __init__(self, data : dict):
    self.id : int = data["id"]
    self.raw : dict = data

  def get(self, key : str, fallback = None) -> Any:
    parts = key.split('.')
    current = self.raw
    for part in parts:
      if current is None:
        return None # TODO: FIX only on the end of the path
      elif isinstance(current, int) or isinstance(current, float) or isinstance(current, str) or isinstance(current, bool):
        return fallback
      elif isinstance(current, dict):
        if not part in current:
          return fallback
        current = current[part]
      elif isinstance(current, list):
        pass # TODO
    return current

  def set(self, key : str, value) -> Any:
    parts = key.split('.')
    current = self.raw
    for i, part in enumerate(parts):
      is_end = (i + 1 == len(parts))
      if current is None or isinstance(current, int) or isinstance(current, float) or isinstance(current, str) or isinstance(current, bool):
        return False
      elif isinstance(current, dict):
        if is_end:
          current[part] = value
          return True
        if not part in current:
          current[part] = {}
        current = current[part]
      elif isinstance(current, list):
        pass # TODO
    return False

  def has(self, key : str) -> bool:
    parts = key.split('.')
    current = self.raw
    for part in parts:
      if current is None:
        return True # TODO: FIX only on the end of the path
      elif isinstance(current, int) or isinstance(current, float) or isinstance(current, str) or isinstance(current, bool):
        return False
      elif isinstance(current, dict):
        if not part in current:
          return False
        current = current[part]
      elif isinstance(current, list):
        pass # TODO
    return True

  def rem(self, key : str) -> bool:
    pass # TODO: Implement

  def view(self, key : str) -> UserdataView:
    return UserdataView(self, key)

class UserdataView:
  def __init__(self, data : Union[Userdata, UserdataView], offset : str):
    self.data : Union[Userdata, UserdataView] = data
    self.offset : str = offset

  def _concat_key(self, key : str) -> str:
    return self.offset + "." + key

  def get(self, key : str, fallback = None) -> Any:
    return self.data.get(self._concat_key(key), fallback)

  def set(self, key : str, value) -> Any:
    return self.data.set(self._concat_key(key), value)

  def has(self, key : str) -> bool:
    return self.data.has(self._concat_key(key))

  def rem(self, key : str) -> bool:
    return self.data.rem(self._concat_key(key))

  def view(self, key : str) -> UserdataView:
    # TODO: Validate
    data = self.data
    offset = self.offset
    while isinstance(data, UserdataView):
      offset = data.offset + "." + offset
      data = data.data

    offset += "." + key

    return data.view(offset)
