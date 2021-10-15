import threading
from queue import PriorityQueue
from typing import Optional

import requests
from redis import Redis
from requests import Response

import libtwitch

class RequestHandler:
  def __init__(self, cache_duration : int = 60, redis : Optional[Redis] = None):
    self._cache_duration : int = cache_duration
    self._redis : Optional[Redis] = redis

    self._queue : PriorityQueue = PriorityQueue()
    self._queue_lock : threading.Lock = threading.Lock()

    self._request_thread : Optional[threading.Thread] = None
    self._running : bool = False

  def _queue_request(self, priority : int, url : str, callback):
    with self._queue_lock:
      print("_queue_request: priority=%s, url=%s" % (priority, url))
      self._queue.put((priority, url, callback))

  @staticmethod
  def get_request_web_sync(url: str) -> str:
    print("get_request_web_sync: url=%s" % url)
    response = requests.get(url)
    return response.text

  @staticmethod
  def _get_request_web(url : str, callback : callable = None) -> None:
    response = requests.get(url)
    callback(response.text)

  def get_request_redis_sync(self, url : str) -> Optional[dict]:
    if self._redis is None:
      return None

    raw_str = self._redis.get("GET %s" % url)
    if raw_str is None:
      return None

    return raw_str

  def get_request_redis_set_sync(self, url : str, text : str) -> None:
    if self._redis is None:
      return None

    self._redis.setex("GET %s" % url, self._cache_duration, text)

  @staticmethod
  def _calc_queue_priority(priority : libtwitch.RequestPriority,
                           ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour,
                           cache_behaviour : libtwitch.RequestCacheBehaviour) -> int:
    return int(priority) + int(ratelimit_behaviour) + int(cache_behaviour)

  def get_request_sync(self, url: str, cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst) -> (bool, str):
    # TODO: Respect Cache behaviour
    text = self.get_request_redis_sync(url)
    if text is not None:
      return True, text

    text = self.get_request_web_sync(url)
    if text is not None:
      self.get_request_redis_set_sync(url, text)

    return False, text

  def _get_request(self, url : str, callback : callable = None,
                   priority : libtwitch.RequestPriority = libtwitch.RequestPriority.Low,
                   ratelimit_behaviour : libtwitch.RequestRatelimitBehaviour = libtwitch.RequestRatelimitBehaviour.Mandatory,
                   cache_behaviour : libtwitch.RequestCacheBehaviour = libtwitch.RequestCacheBehaviour.CacheFirst):
    # TODO: Respect Cache behaviour
    text = self.get_request_redis_sync(url)
    if text is not None:
      return callback(True, text)

    def on_web_callback(response_text):
      # TODO: Handle errors
      self.get_request_redis_set_sync(url, response_text)

      return callback(False, response_text)

    queue_priority = self._calc_queue_priority(priority, ratelimit_behaviour, cache_behaviour)
    self._queue_request(queue_priority, url, on_web_callback)

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
    self._request_thread.join()
    return True

  @property
  def is_running(self) -> bool:
    return self._running