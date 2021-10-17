import io
import json
import os
from typing import Any, Optional

from libtwitch import Plugin

JsonData = dict[str, Any]

def load_config(plugin: Plugin, fallback: Optional[JsonData] = None) -> Optional[JsonData]:
  config_path = plugin.get_config_dir() + "/config.json"
  if not os.path.exists(config_path):
    if fallback is None:
      return None
    config = fallback
    _write_fallback_config(plugin, fallback)
  else:
    with io.open(config_path) as f:
      jdata = json.load(f)
    if jdata is None and fallback is not None:
      _write_fallback_config(plugin, fallback)
      config = fallback
    else:
      config = jdata
  return config

def _write_fallback_config(plugin: Plugin, fallback: JsonData = None) -> None:
  config_path = plugin.get_config_dir() + "/config.json"
  with io.open(config_path, 'w') as f:
    json.dump(fallback, f, indent=2)