import io
import json
import os
from typing import Any, Optional
from redis import Redis

import libtwitch

class FileDatastoreFile:
  def __init__(self, key : str, data : dict):
    self.data = data
    self.dirty = False
    self.key = key

def _ensure_dir(file_path : str):
  dir_path = os.path.dirname(file_path)
  os.makedirs(dir_path, exist_ok=True)

class FileDatastore(libtwitch.Datastore):
  def __init__(self, path : str, redis = Optional[Redis]):
    self.path = path
    self._cache_global = None # TODO
    self._cache : dict[str, FileDatastoreFile] = {}
    self._redis : Optional[Redis] = redis

  def _get_filekey(self, subject : libtwitch.DatastoreDomainType) -> Optional[str]:
    domain = self._get_domain(subject)
    if domain is None:
      return None
    if domain == libtwitch.DatastoreDomain.Chatter:
      return "chatters.%s.%s" % (subject.channel.name, subject.id)
    elif domain == libtwitch.DatastoreDomain.Channel:
      return "channel.%s" % subject.login
    elif domain == libtwitch.DatastoreDomain.Global:
      return "global"
    return None

  def _redis_set(self, file : FileDatastoreFile):
    if self._redis is not None:
      self._redis.set(file.key, json.dumps(file.data).encode("utf-8"))
      self._redis.set(file.key + ".dirty", int(file.dirty))

  def _redis_clear(self, filekey : str):
    if self._redis is not None:
      self._redis.delete(filekey)

  def _filekey2path(self, filekey : str) -> str:
    return "%s/%s.json" % (self.path, filekey.replace('.', '/'))

  def _get_file_from_ram(self, filekey : str) -> Optional[FileDatastoreFile]:
    if filekey in self._cache:
      return self._cache[filekey]
    return None

  def _get_file_from_redis(self, filekey : str) -> Optional[FileDatastoreFile]:
    if self._redis is None:
      return None

    dirty = int(self._redis.get(filekey + ".dirty"))
    raw_str = self._redis.get(filekey).decode("utf-8")

    if dirty == 'None' or raw_str == 'None':
      return None

    data = json.loads(raw_str)
    file = FileDatastoreFile(filekey, data)
    if dirty:
      file.dirty = True
    return file

  def _get_file_from_disk(self, filekey : str) -> Optional[FileDatastoreFile]:
    path = self._filekey2path(filekey)
    if os.path.exists(path):
      with io.open(path, mode="r", encoding="utf-8") as f:
        data = json.load(f)
        return FileDatastoreFile(filekey, data)
    return None

  @staticmethod
  def _gen_file(filekey : str) -> FileDatastoreFile:
    return FileDatastoreFile(filekey, {})

  def _get_file(self, subject : libtwitch.DatastoreDomainType) -> Optional[FileDatastoreFile]:
    filekey = self._get_filekey(subject)
    if filekey is None:
      return None

    # Ram
    file = self._get_file_from_ram(filekey)
    if file is not None:
      return file

    # Redis
    file = self._get_file_from_redis(filekey)
    if file is not None:
      self._cache[filekey] = file
      return file

    # Disk
    file = self._get_file_from_disk(filekey)
    if file is not None:
      self._cache[filekey] = file
      self._redis_set(file)
      return file

    # Create new
    file = self._gen_file(filekey)
    self._cache[filekey] = file
    self._redis_set(file)
    return file

  def get(self, subject : libtwitch.DatastoreDomainType, key : str, fallback = None) -> Any:
    file = self._get_file(subject)
    if file is None:
      return fallback
    if not key in file.data:
      return fallback
    return file.data[key]

  def set(self, subject : libtwitch.DatastoreDomainType, key : str, value) -> None:
    file = self._get_file(subject)
    if file is None:
      return
    file.data[key] = value
    file.dirty = True
    self._redis_set(file)

  def has(self, subject : libtwitch.DatastoreDomainType, key : str) -> bool:
    file = self._get_file(subject)
    if file is None:
      return False
    return key in file.data

  def rem(self, subject : libtwitch.DatastoreDomainType, key : str) -> None:
    file = self._get_file(subject)
    if file is None:
      return
    if not key in file.data:
      return
    del file.data[key]
    file.dirty = True
    self._redis_set(file)

  def keys(self, subject : libtwitch.DatastoreDomainType) -> list[str]:
    file = self._get_file(subject)
    if file is None:
      return []
    keys = []
    for key in file.data:
      keys.append(key)
    return keys

  def sync(self):
    # TODO: Lock
    for filekey in self._cache:
      file = self._cache[filekey]
      if not file.dirty:
        continue
      print("sync %s" % filekey)
      path = self._filekey2path(filekey)
      _ensure_dir(path)
      with io.open(path, mode="w", encoding="utf-8") as f:
        json.dump(file.data, f)
      file.dirty = False
      self._redis_set(file)