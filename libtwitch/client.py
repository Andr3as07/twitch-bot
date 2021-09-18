import json
from datetime import datetime
from enum import Enum, unique
from typing import Optional, Union
from dataclasses import dataclass

import requests
from redis import Redis
from requests import Response
from twitch.tmi import Chatter

BASE_URL = "https://api.twitch.tv/helix"

RequestUserType = Union[str, int, Chatter]

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
    self.offline_image_url = jdata['offline_image_url']
    self.profile_image_url = jdata['profile_image_url']
    self.broadcaster_type = None  # TODO
    self.display_name = jdata['display_name']
    self.description = jdata['description']
    self.created_at = None  # TODO
    self.view_count = int(jdata['view_count'])
    self.login = jdata['login']
    self.type = None  # TODO
    self.id = int(jdata['id'])

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
  def __init__(self, client_id : str, token : str, cache_duration : int = 60, redis = Optional[Redis]):
    self._client_id : str = client_id
    self._token : str = token
    self._redis : Optional[Redis] = redis
    self._cache_duration : int = cache_duration

  def _get_request_web(self, url : str) -> Response:
    headers = {
      'Authorization': "Bearer %s" % self._token,
      'Client-ID': self._client_id
    }

    return requests.get(url, headers=headers)

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

  def _get_request(self, url : str) -> dict:
    result = self._get_request_redis(url)
    if result is not None:
      return result

    response = self._get_request_web(url)
    # TODO: Handle errors

    self._get_request_redis_set(url, response)

    return response.json()

  def get_user(self, user : RequestUserType) -> Optional[User]:
    users = self.get_users([user])
    if len(users) < 1:
      return None
    return users[user]

  def get_users(self, users : list[RequestUserType]) -> Optional[dict[RequestUserType, User]]:
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
      elif isinstance(user, Chatter):
        url += "login=%s" % user.name
      elif isinstance(user, str):
        url += "login=%s" % user
      else:
        raise RuntimeError()

    jdata = self._get_request(url)
    # TODO: Handle error response

    response_dict = {}
    jusers = jdata["data"]

    for juser in jusers:
      user = User(juser)

      for key in users:
        if isinstance(key, int) and key == user.id:
          response_dict[key] = user
          continue
        elif isinstance(key, Chatter) and key.name == user.login:
          response_dict[key] = user
          continue
        elif isinstance(key, str) and key == user.login:
          response_dict[key] = user
          continue

    return response_dict

  def get_follow(self, from_user : int, to_user : int) -> Optional[Follow]:
    url = BASE_URL + "/users/follows?from_id=%s&to_id=%s" % (from_user, to_user)

    jdata = self._get_request(url)
    # TODO: Handle error response

    if len(jdata['data']) == 0:
      return None

    return Follow(jdata['data'][0])

  def get_follows(self, *, from_user : Optional[int] = None, to_user : Optional[int] = None, after : Optional[str] = None) -> (list[Follow], int, Optional[str]):
    if from_user is None and to_user is None:
      raise RuntimeError()

    url = BASE_URL + "/users/follows?first=100"

    if from_user is not None:
      url += "&from_id=%s" % from_user
    if to_user is not None:
      url += "&to_id=%s" % to_user
    if after is not None:
      url += "&after=%s" % after

    jdata = self._get_request(url)
    # TODO: Handle error response

    result = []
    if len(jdata['data']) == 0:
      return result, 0, None

    for jfollow in jdata['data']:
      result.append(Follow(jfollow))

    cursor = None
    if 'cursor' in jdata['pagination']:
      cursor = jdata['pagination']['cursor']

    return result, jdata['total'], cursor
