import argparse
from importlib.metadata import distributions

from nicegui import app, ui

@ui.page("/")
def main_page():
    with ui.grid(columns="auto auto"):
        for dist in distributions():
            ui.label(dist.metadata["Name"])
            ui.label(dist.version)

if __name__ == '__main__':
    ui.run()

