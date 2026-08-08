# app/modules/media_base.py
import os
import string
import random
from typing import Tuple

def is_already_renamed(filename: str) -> bool:
    name, _ = os.path.splitext(filename)
    allowed_chars = string.ascii_letters + string.digits + '-_'
    return len(name) == 11 and all(c in allowed_chars for c in name)

def generate_unique_id(dir_path: str, ext: str, length: int = 11) -> Tuple[str, str]:
    chars = string.ascii_letters + string.digits + '-_'
    while True:
        new_id = ''.join(random.choices(chars, k=length))
        new_filename = new_id + ext
        new_path = os.path.join(dir_path, new_filename)
        if not os.path.exists(new_path):
            return new_id, new_path