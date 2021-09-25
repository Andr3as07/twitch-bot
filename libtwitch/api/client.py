import json
from typing import Optional, Union

import requests
from redis import Redis

import libtwitch
from libtwitch import IrcChatter

BASE_URL = "https://api.twitch.tv/helix"

RequestUserType = Union[str, int, IrcChatter]

class TwitchAPIClient(libtwitch.RequestHandler):
  def __init__(self, client_id : str, token : str, cache_duration : int = 60, redis : Optional[Redis] = None):
    super().__init__(cache_duration, redis)
    self._client_id : str = client_id
    self._token : str = token

  def _get_request_web(self, url : str, callback : callable = None) -> None:
    headers = {
      'Authorization': "Bearer %s" % self._token,
      'Client-ID': self._client_id
    }

    response = requests.get(url, headers=headers)
    callback(response.text)

  def get_user(self, user : RequestUserType, callback : callable,
                   priority : libtwitch.RequestPriority = libtwitch.RequestPriority.Low,
                   ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour = libtwitch.RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst) -> None:

    def get_users_callback(is_cached, users):
      if users is None or len(users) < 1 or not user in users:
        callback(is_cached, None)
      callback(is_cached, users[user])

    self.get_users([user], get_users_callback, priority, ratelimit_behaviour, cache_behaviour)

  def get_users(self, users : list[RequestUserType], callback : callable,
                   priority : libtwitch.RequestPriority = libtwitch.RequestPriority.Low,
                   ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour = libtwitch.RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst) -> None:
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

    def on_request_callback(is_cached, text):
      response_dict = {}
      jdata = json.loads(text)
      jusers = jdata["data"]

      for juser in jusers:
        user = libtwitch.User(juser)

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
                   priority : libtwitch.RequestPriority = libtwitch.RequestPriority.Low,
                   ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour = libtwitch.RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst) -> None:
    url = BASE_URL + "/users/follows?from_id=%s&to_id=%s" % (from_user, to_user)

    def on_request_callback(is_cached, text):
      jdata = json.loads(text)
      if len(jdata['data']) == 0:
        callback(is_cached, None)

      callback(is_cached, libtwitch.Follow(jdata['data'][0]))

    self._get_request(url, on_request_callback, priority, ratelimit_behaviour, cache_behaviour)
    # TODO: Handle error response

  def get_follows(self, callback : callable, from_user : Optional[int] = None, to_user : Optional[int] = None, after : Optional[str] = None,
                   priority : libtwitch.RequestPriority = libtwitch.RequestPriority.Low,
                   ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour = libtwitch.RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst):
    if from_user is None and to_user is None:
      raise RuntimeError()

    url = BASE_URL + "/users/follows?first=100"

    if from_user is not None:
      url += "&from_id=%s" % from_user
    if to_user is not None:
      url += "&to_id=%s" % to_user
    if after is not None:
      url += "&after=%s" % after

    def on_request_callback(is_cached, text):
      result = []
      jdata = json.loads(text)
      if len(jdata['data']) == 0:
        callback(is_cached, result, 0, None)

      for jfollow in jdata['data']:
        result.append(libtwitch.Follow(jfollow))

      cursor = None
      if 'cursor' in jdata['pagination']:
        cursor = jdata['pagination']['cursor']

      callback(is_cached, result, jdata['total'], cursor)

    self._get_request(url, on_request_callback, priority, ratelimit_behaviour, cache_behaviour)
    # TODO: Handle error response