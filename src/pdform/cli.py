import click
from .make_html.cli import cli as make_html
from .describe import describe
from .fill_form import cli as fill_form

@click.group()
def cli():
    pass

cli.add_command(make_html)
cli.add_command(describe)
cli.add_command(fill_form)