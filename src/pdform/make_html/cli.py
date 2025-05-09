import click
import  sys
from io import TextIOBase, IOBase, StringIO, TextIOWrapper
from .make_html import make_html


@click.command('make-html')
@click.argument('path', type=click.Path(True, dir_okay=False))
@click.argument('output', type=click.File('w'))
@click.option('--pdf2html', help='Override the path used to call Pdf2HmlEX', default='pdf2htmlex')
@click.option('--zoom', help='The size at which to render the PDF into HTML', type=click.FloatRange(0, None, True), default=1)
@click.option('--sort-widgets/--original-widget-sorting', help='Attempt to re-sort widgets based on their location on the page.', default=False)
@click.option('--rename-fields/--original-fields-naming', help='Rename fields, removing special characters.', default=False)
@click.option('--from-page', help='Start rendering at this page', type=click.IntRange(1), default=1)
@click.option('--to-page', help='Stop rendering after this page', type=click.IntRange(1))
def cli(path, output, **kwargs):
    soup = make_html(path, **kwargs)
    output.write(str(soup))
    return output