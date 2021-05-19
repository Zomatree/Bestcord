from .app import App
import sys
import toml

file = sys.argv[1]

with open(file) as f:
    config = toml.load(f)
    App.run(config)
