from .validator import Spec
import datetime

embed_spec: Spec = {
    "title": {"type": "string", "default": None, "nullable": True, "required": False, "maxlength": 256},
    "type": {"type": "string", "default": "rich", "required": False, "allowed": ["rich"]},
    "description": {"type": "string", "default": None, "nullable": True, "required": False, "maxlength": 2048},
    "url": {"type": "string", "default": None, "nullable": True, "required": False},
    "timestamp": {"type": "string", "default": None, "nullable": True, "required": False, "coerce": datetime.datetime.fromisoformat},
    "color": {"type": "number", "default": 0, "min": 0, "max": 0xFFFFFF, "required": False},
    "footer": {"type": "dict", "default": None, "nullable": True, "required": False, "schema": {
        "text": {"type": "string", "required": True, "maxlength": 2048},
        "icon_url": {"type": "string", "required": False, "default": None, "nullable": True},
    }},
    "image": {"type": "dict", "required": False, "default": {}, "schema": {
        "url": {"type": "string", "required": False},
    }},
    "thumbnail": {"type": "dict", "required": False, "default": {}, "schema": {
        "url": {"type": "string", "required": False}
    }},
    "video": {"type": "dict", "required": False, "default": {}, "schema": {
        "url": {"type": "string", "required": False}
    }},
    "author": {"type": "dict", "required": False, "default": {}, "schema": {
        "name": {"type": "string", "required": False, "maxlength": 256},
        "url": {"type": "string", "required": False,},
        "icon_url": {"type": "string", "required": False},
    }},
    "fields": {"type": "list", "maxlength": 25, "required": False, "default": [], "schema": {"type": "dict", "schema": {
        "name": {"type": "string", "required": True, "maxlength": 256},
        "value": {"type": "string", "required": True, "maxlength": 1024},
        "inline": {"type": "boolean", "required": False, "default": False}
    }}}
}

allowed_mentions_spec: Spec = {
    "parse": {"type": "list", "schema": {"type": "string", "allowed": ["roles", "users", "everyone"]}, "required": True},
    "roles": {"type": "list", "schema": {"type": "string", "maxlength": 100}, "default": [], "required": True},
    "users": {"type": "list", "schema": {"type": "string", "maxlength": 100}, "default": [], "required": True},
    "replied_user": {"type": "boolean", "default": False, "required": False}
}
