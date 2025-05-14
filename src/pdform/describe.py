import click
from pikepdf import Pdf
from pikepdf.form import Form, TextField, CheckboxField, RadioButtonGroup, ChoiceField, SignatureField
import re

@click.command
@click.argument('path', type=click.File('rb'))
@click.option('--text', 'filter_types', help='Show text fields. (If no type filters are provided, all will be implied true)', multiple=True, flag_value='text')
@click.option('--checkbox', 'filter_types', help='Show checkbox fields. (If no type filters are provided, all will be implied true)', multiple=True, flag_value='checkbox')
@click.option('--radio', 'filter_types', help='Show radio fields. (If no type filters are provided, all will be implied true)', multiple=True, flag_value='radio')
@click.option('--choice', 'filter_types', help='Show choice fields. (If no type filters are provided, all will be implied true)', multiple=True, flag_value='choice')
@click.option('--signature', 'filter_types', help='Show signature fields. (If no type filters are provided, all will be implied true)', multiple=True, flag_value='signature')
@click.option('--name', '-n', 'filter_name', help='Show only fields with a name containing the given string. Use slashes to build a regex.', multiple=True, type=click.STRING)
@click.option('--label', '-l', 'filter_label', help='Show only fields with a label containing the given string. Use slashes to build a regex.',multiple=True, type=click.STRING)
@click.option('--names-only/--full-info', 'names_only', help='Determines if detailed information should be shown, or only field names.', default=False)
def describe(path, filter_types, filter_name, filter_label, names_only):
    """
    Describe the fields in a form
    """
    something_shown = False
    with Pdf.open(path) as pdf:
        form = Form(pdf)

        with pdf.open_metadata() as meta:
            title = meta.get('dc:title', pdf.filename)
            click.secho('=' * len(title), reverse=True)
            click.secho(title, reverse=True)
            click.secho('=' * len(title), reverse=True)
            click.echo()

        if not form.exists:
            click.secho("No interactive form exists in this document.", fg='yellow')
            return


        for name, field in form.items():
            if filter_types:
                if isinstance(field, TextField) and 'text' not in filter_types:
                    continue
                if isinstance(field, CheckboxField) and 'checkbox' not in filter_types:
                    continue
                if isinstance(field, RadioButtonGroup) and 'radio' not in filter_types:
                    continue
                if isinstance(field, ChoiceField) and 'choice' not in filter_types:
                    continue
                if isinstance(field, SignatureField) and 'signature' not in filter_types:
                    continue
            
            if filter_name and not filter_match(filter_name, name):
                continue
            if filter_label and not filter_match(filter_label, field.alternate_name):
                continue

            something_shown = True

            if names_only:
                click.echo(name)
                continue

            click.secho(name, reverse=True, fg='cyan')
            click.secho('-' * len(name), reverse=True, fg='cyan')
            click.echo()
            click.secho('Label:', fg='cyan')
            click.echo("\t"+field.alternate_name)
            click.echo()
            click.secho('Type:', fg='cyan')
            click.echo("\t"+type(field).__name__)
            click.echo()
            click.secho('Required:', fg='cyan')
            click.echo("\t"+('Yes' if field.is_required else 'No'))
            click.echo()
            click.secho('Read Only:', fg='cyan')
            click.echo("\t"+('Yes' if field.is_read_only else 'No'))
            click.echo()

            if isinstance(field, TextField):
                click.secho('Multiline:', fg='cyan')
                click.echo("\t"+('Yes' if field.is_multiline else 'No'))
                click.echo()
                click.secho('Max Length:', fg='cyan')
                click.echo("\t"+str(field.max_length))
                click.echo()
            elif isinstance(field, CheckboxField):
                click.secho('"On" Value:', fg='cyan')
                click.echo("\t"+str(field.on_value))
                click.echo()
            elif isinstance(field, RadioButtonGroup):
                click.secho('Can Toggle Off:', fg='cyan')
                click.echo("\t"+('Yes' if field.can_toggle_off else 'No'))
                click.echo()
                click.secho('Possible Values:', fg='cyan')
                for option in field.options:
                    click.echo("\t* "+str(option.on_value))
                click.echo()
            elif isinstance(field, ChoiceField):
                click.secho('Possible Values:', fg='cyan')
                for option in field.options:
                    click.echo("\t* "+str(option.display_value))
                click.echo()
            
            click.secho('Default Value:', fg='cyan')
            click.echo("\t"+str(field.default_value))
            click.echo()
            click.secho('Current Value:', fg='cyan')
            click.echo("\t"+str(field.value))
            click.echo()
    
    if not something_shown:
        click.secho("No fields match the given criteria.", fg='yellow')
            

def filter_match(filters, match_against):
    matched = False
    for fl in filters:
        if fl.startswith('/') and fl.endswith('/'):
            if re.search(fl[1:-2], match_against):
                matched = True
        elif fl.lower() in match_against.lower():
            matched = True
    return matched


if __name__ == '__main__':
    describe()