import json
import threading
from datetime import datetime
from enum import Enum, IntEnum, auto, unique
from typing import Optional, Union
from dataclasses import dataclass
from queue import PriorityQueue

import requests
from redis import Redis
from requests import Response

from libtwitch.irc import IrcChatter

BASE_URL = "https://api.twitch.tv/helix"

RequestUserType = Union[str, int, IrcChatter]

@unique
class RequestPriority(IntEnum):
  High = 0
  Medium = 10
  Low = 20

@unique
class RequestRatelimitBehaviour(IntEnum):
  Mandatory = 0
  Optional = 1

@unique
class RequestCacheBehaviour(IntEnum):
  NoCache = 0
  CacheOnRatelimit = 3
  CacheOnFail = 4
  CacheFirst = 5

@unique
class BroadcasterType(Enum):
  Nothing = ""
  Affiliate = "affiliate"
  Partner = "partner"

@unique
class UserType(Enum):
  Nothing = ""
  GlobalMod = "global_mod"
  Admin = "admin"
  Staff = "staff"

@dataclass
class Follow:
  def __init__(self, jdata):
    self.from_id = int(jdata['from_id'])
    self.to_id = int(jdata['to_id'])
    self.from_login = jdata['from_login']
    self.to_login = jdata['to_login']
    self.from_name = jdata['from_name']
    self.to_name = jdata['to_name']

  followed_at : datetime = None
  from_login : str = None
  from_name : str = None
  from_id : int = -1
  to_login : str = None
  to_name : str = None
  to_id : int = -1

@dataclass
class User:
  def __init__(self, jdata):
    self.offline_image_url : str = jdata['offline_image_url']
    self.profile_image_url : str = jdata['profile_image_url']
    self.broadcaster_type : BroadcasterType = BroadcasterType.Nothing  # TODO
    self.display_name : str = jdata['display_name']
    self.description : str = jdata['description']
    self.created_at : datetime = None  # TODO
    self.view_count : int = int(jdata['view_count'])
    self.login : str = jdata['login']
    self.type : UserType = UserType.Nothing  # TODO
    self.id : int = int(jdata['id'])

  offline_image_url : str = None
  profile_image_url : str = None
  broadcaster_type : BroadcasterType = BroadcasterType.Nothing
  display_name : str = None
  description : str = None
  created_at : datetime = None
  view_count : str = -1
  login : str = None
  type : UserType = UserType.Nothing
  id : int = -1

  def get_display_name(self):
    if self.display_name is not None:
      return self.display_name
    return self.login

class TwitchAPIClient:
  def __init__(self, client_id : str, token : str, cache_duration : int = 60, redis : Optional[Redis] = None):
    self._client_id : str = client_id
    self._token : str = token
    self._redis : Optional[Redis] = redis
    self._cache_duration : int = cache_duration

    self._queue : PriorityQueue = PriorityQueue()
    self._queue_lock : threading.Lock = threading.Lock()

    self._request_thread : Optional[threading.Thread] = None
    self._running : bool = False

  def _queue_request(self, priority : int, url : str, callback):
    with self._queue_lock:
      print("_queue_request: priority=%s, url=%s" % (priority, url))
      self._queue.put((priority, url, callback))

  def _get_request_web(self, url : str, callback : callable = None) -> None:
    headers = {
      'Authorization': "Bearer %s" % self._token,
      'Client-ID': self._client_id
    }

    response = requests.get(url, headers=headers)
    callback(response)

  def _get_request_redis(self, url : str) -> Optional[dict]:
    if self._redis is None:
      return None

    raw_str = self._redis.get("GET %s" % url)
    if raw_str is None:
      return None

    return json.loads(raw_str.decode("utf-8"))

  def _get_request_redis_set(self, url : str, response : Response) -> None:
    if self._redis is None:
      return None

    self._redis.setex("GET %s" % url, self._cache_duration, json.dumps(response.json()))

  @staticmethod
  def _calc_queue_priority(priority : RequestPriority, ratelimit_behaviour : RequestRatelimitBehaviour, cache_behaviour : RequestCacheBehaviour) -> int:
    return int(priority) + int(ratelimit_behaviour) + int(cache_behaviour)

  def _get_request(self, url : str, callback : callable = None,
                   priority : RequestPriority = RequestPriority.Low,
                   ratelimit_behaviour : RequestRatelimitBehaviour = RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : RequestCacheBehaviour = RequestCacheBehaviour.CacheFirst):
    # TODO: Respect Cache behaviour
    result = self._get_request_redis(url)
    if result is not None:
      return callback(True, result)

    def on_web_callback(response):
      # TODO: Handle errors
      self._get_request_redis_set(url, response)

      return callback(False, response.json())

    queue_priority = self._calc_queue_priority(priority, ratelimit_behaviour, cache_behaviour)
    self._queue_request(queue_priority, url, on_web_callback)

  def get_user(self, user : RequestUserType, callback : callable,
                   priority : RequestPriority = RequestPriority.Low,
                   ratelimit_behaviour : RequestRatelimitBehaviour = RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : RequestCacheBehaviour = RequestCacheBehaviour.CacheFirst) -> None:

    def get_users_callback(is_cached, users):
      if users is None or len(users) < 1 or not user in users:
        callback(is_cached, None)
      callback(is_cached, users[user])

    self.get_users([user], get_users_callback, priority, ratelimit_behaviour, cache_behaviour)

  def get_users(self, users : list[RequestUserType], callback : callable,
                   priority : RequestPriority = RequestPriority.Low,
                   ratelimit_behaviour : RequestRatelimitBehaviour = RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : RequestCacheBehaviour = RequestCacheBehaviour.CacheFirst) -> None:
    url = BASE_URL + "/users"

    if len(users) > 100:
      return None

    first = True
    for user in users:
      if first:
        url += "?"
        first = False
      else:
        url += "&"

      if isinstance(user, int):
        url += "id=%s" % user
      elif isinstance(user, IrcChatter):
        url += "login=%s" % user.name
      elif isinstance(user, str):
        url += "login=%s" % user
      else:
        raise RuntimeError()

    def on_request_callback(is_cached, jdata):
      response_dict = {}
      jusers = jdata["data"]

      for juser in jusers:
        user = User(juser)

        for key in users:
          if isinstance(key, int) and key == user.id:
            response_dict[key] = user
            break
          elif isinstance(key, IrcChatter) and key.name == user.login:
            response_dict[key] = user
            break
          elif isinstance(key, str) and key.lower() == user.login:
            response_dict[key] = user
            break

      callback(is_cached, response_dict)

    self._get_request(url, on_request_callback, priority, ratelimit_behaviour, cache_behaviour)
    # TODO: Handle error response

  def get_follow(self, from_user : int, to_user : int, callback : callable,
                   priority : RequestPriority = RequestPriority.Low,
                   ratelimit_behaviour : RequestRatelimitBehaviour = RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : RequestCacheBehaviour = RequestCacheBehaviour.CacheFirst) -> None:
    url = BASE_URL + "/users/follows?from_id=%s&to_id=%s" % (from_user, to_user)

    def on_request_callback(is_cached, jdata):
      if len(jdata['data']) == 0:
        callback(is_cached, None)

      callback(is_cached, Follow(jdata['data'][0]))

    self._get_request(url, on_request_callback, priority, ratelimit_behaviour, cache_behaviour)
    # TODO: Handle error response

  def get_follows(self, callback : callable, from_user : Optional[int] = None, to_user : Optional[int] = None, after : Optional[str] = None,
                   priority : RequestPriority = RequestPriority.Low,
                   ratelimit_behaviour : RequestRatelimitBehaviour = RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : RequestCacheBehaviour = RequestCacheBehaviour.CacheFirst):
    if from_user is None and to_user is None:
      raise RuntimeError()

    url = BASE_URL + "/users/follows?first=100"

    if from_user is not None:
      url += "&from_id=%s" % from_user
    if to_user is not None:
      url += "&to_id=%s" % to_user
    if after is not None:
      url += "&after=%s" % after

    def on_request_callback(is_cached, jdata):
      result = []
      if len(jdata['data']) == 0:
        callback(is_cached, result, 0, None)

      for jfollow in jdata['data']:
        result.append(Follow(jfollow))

      cursor = None
      if 'cursor' in jdata['pagination']:
        cursor = jdata['pagination']['cursor']

      callback(is_cached, result, jdata['total'], cursor)

    self._get_request(url, on_request_callback, priority, ratelimit_behaviour, cache_behaviour)
    # TODO: Handle error response

  def _request_thread_func(self):
    while self._running:
      item = self._queue.get()
      with self._queue_lock:
        priority : int = item[0]
        url : str = item[1]
        callback : callable = item[2]

        self._get_request_web(url, callback)
        self._queue.task_done()

  def start(self):
    if self._running:
      return False
    self._running = True
    self._request_thread = threading.Thread(target=self._request_thread_func)
    self._request_thread.start()
    return True

  def stop(self):
    if not self._running:
      return False
    self._running = False
    self._request_thread.json()
    return True

  @property
  def is_running(self) -> bool:
    return self._running
