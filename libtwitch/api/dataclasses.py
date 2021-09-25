from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime

import libtwitch

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
    self.broadcaster_type : libtwitch.BroadcasterType = libtwitch.BroadcasterType.Nothing  # TODO
    self.display_name : str = jdata['display_name']
    self.description : str = jdata['description']
    self.created_at : datetime = None  # TODO
    self.view_count : int = int(jdata['view_count'])
    self.login : str = jdata['login']
    self.type : libtwitch.UserType = libtwitch.UserType.Nothing  # TODO
    self.id : int = int(jdata['id'])

  offline_image_url : str = None
  profile_image_url : str = None
  broadcaster_type : libtwitch.BroadcasterType = libtwitch.BroadcasterType.Nothing
  display_name : str = None
  description : str = None
  created_at : datetime = None
  view_count : str = -1
  login : str = None
  type : libtwitch.UserType = libtwitch.UserType.Nothing
  id : int = -1

  def get_display_name(self):
    if self.display_name is not None:
      return self.display_name
    return self.login