from .app import App
import sys
import toml

file: str = sys.argv[1]

with open(file) as f:
    config = dict(toml.load(f))
    App.run(config)
