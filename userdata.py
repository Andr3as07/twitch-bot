import json

class Userdata:
  def __init__(self, data):
    self.id = data["id"]
    self.raw = data

  def get(self, key, fallback = None):
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

  def set(self, key, value):
    parts = key.split('.')
    current = self.raw
    for i, part in enumerate(parts):
      is_end = (i + 1 == len(parts))
      next_is_end = (i + 2 == len(parts))
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

  def has(self, key):
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

  def rem(self, key):
    pass # TODO: Implement

  def view(self, key):
    return UserdataView(self, key)

class UserdataView:
  def __init__(self, data, offset):
    self.data = data
    self.offset = offset

  def _concat_key(self, key):
    return self.offset + "." + key

  def get(self, key, fallback = None):
    return self.data.get(self._concat_key(key), fallback)

  def set(self, key, value):
    return self.data.set(self._concat_key(key), value)

  def has(self, key):
    return self.data.has(self._concat_key(key))

  def rem(self, key):
    return self.data.rem(self._concat_key(key))

  def view(self, key):
    # TODO: Validate
    data = self.data
    offset = self.offset
    while isinstance(data, UserdataView):
      offset = data.offset + "." + offset
      data = data.data

    offset += "." + key

    return data.view(offset)
