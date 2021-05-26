from .app import App
import sys
import toml
import logging

file: str = sys.argv[1]
log_level: str = sys.argv[2]

with open(file) as f:
    config = dict(toml.load(f))
    App.run(config, log_level)
