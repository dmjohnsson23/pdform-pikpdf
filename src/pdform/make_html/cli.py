import click
from .make_html import make_html
from .field_renderer import FieldRenderer, PHPFieldRenderer, JinjaFieldRenderer


@click.command('make-html', help='Convert a PDF form into an HTML form')
@click.argument('path', type=click.Path(True, dir_okay=False))
@click.argument('output', type=click.File('w'))
@click.option('--pdf2html', help='Override the path used to call Pdf2HmlEX', default='pdf2htmlex')
@click.option('--zoom', help='The size at which to render the PDF into HTML', type=click.FloatRange(0, None, True), default=1)
@click.option('--sort-widgets/--original-widget-sorting', help='Attempt to re-sort widgets based on their location on the page.', default=False)
@click.option('--rename-fields/--original-fields-naming', help='Rename fields, removing special characters.', default=False)
@click.option('--from-page', help='Start rendering at this page', type=click.IntRange(1), default=1)
@click.option('--to-page', help='Stop rendering after this page', type=click.IntRange(1))
@click.option('--html', 'field_renderer_class', help='Render the page as plain HTML', flag_value='html', default=True)
@click.option('--php', 'field_renderer_class', help='Render the page as PHP code', flag_value='php')
@click.option('--jinja', 'field_renderer_class', help='Render the page as a Jinja template', flag_value='jinja')
def cli(path, output, *, field_renderer_class, **kwargs):
    kwargs['field_renderer_class'] = {
        'html':FieldRenderer,
        'php':PHPFieldRenderer,
        'jinja':JinjaFieldRenderer,
    }[field_renderer_class]
    soup = make_html(path, **kwargs)
    output.write(str(soup))
    return output