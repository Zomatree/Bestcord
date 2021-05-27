from .app import App
import sys
import toml
import io

file: str = sys.argv[1]
log_level: str = sys.argv[2]

with open(file, "r") as f:
    f: io.TextIOWrapper
    config: dict = dict(toml.load(f))
    App.run(config, log_level)
