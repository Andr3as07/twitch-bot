import io
import json
import os
from typing import Any, Union

from libtwitch import IrcChannel, IrcChatter, Datastore
from libtwitch.datastore import DatastoreDomain, get_domain

class FileDatastoreFile:
  def __init__(self, path, data):
    self.data = data
    self.dirty = False
    self.path = path

def _ensure_dir(file_path : str):
  dir_path = os.path.dirname(file_path)
  os.makedirs(dir_path, exist_ok=True)

class FileDatastore(Datastore):
  def __init__(self, path):
    self.path = path
    self._cache_global = None # TODO
    self._cache = {}

  def _get_file_raw(self, path : str) -> FileDatastoreFile:
    if path in self._cache:
      pass # Nothing to do
    else:
      data = {}
      if os.path.exists(path):
        with io.open(path, mode="r", encoding="utf-8") as f:
          data = json.load(f)
      self._cache[path] = FileDatastoreFile(path, data)
    return self._cache[path]

  def _get_file(self, subject : Union[None, IrcChannel, IrcChatter]) -> FileDatastoreFile:
    domain = get_domain(subject)
    if domain is None:
      return None

    if domain == DatastoreDomain.Chatter:
      path = self.path + "/chatters/" + subject.channel.name + "/" + str(subject.id) + ".json"
      return self._get_file_raw(path)
    elif domain == DatastoreDomain.Channel:
      path = self.path + "/channels/" + subject.name + ".json"
      return self._get_file_raw(path)
    else:
      print("TODO")

  def get(self, subject : Union[None, IrcChannel, IrcChatter], key : str, fallback = None) -> Any:
    file = self._get_file(subject)
    if file is None:
      return fallback
    if not key in file.data:
      return fallback
    return file.data[key]

  def set(self, subject : Union[None, IrcChannel, IrcChatter], key : str, value) -> None:
    file = self._get_file(subject)
    if file is None:
      return
    file.data[key] = value
    file.dirty = True

  def has(self, subject : Union[None, IrcChannel, IrcChatter], key : str) -> bool:
    file = self._get_file(subject)
    if file is None:
      return False
    return key in file.data

  def rem(self, subject : Union[None, IrcChannel, IrcChatter], key : str) -> None:
    file = self._get_file(subject)
    if file is None:
      return
    if not key in file.data:
      return
    del file.data[key]
    file.dirty = True

  def keys(self, subject : Union[None, IrcChannel, IrcChatter]) -> list[str]:
    file = self._get_file(subject)
    if file is None:
      return []
    keys = []
    for key in file.data:
      keys.append(key)
    return keys

  def sync(self):
    # TODO: Lock
    for path, file in self._cache.items():
      if not file.dirty:
        continue
      print("sync %s" % path)
      _ensure_dir(path)
      with io.open(path, mode="w", encoding="utf-8") as f:
        json.dump(file.data, f)
      file.dirty = False