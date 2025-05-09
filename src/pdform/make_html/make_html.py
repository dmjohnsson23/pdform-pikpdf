import os
from subprocess import run
from .template_soup import TemplateSoup
import tempfile
from .process_form import add_form_fields
from pathlib import Path
from pikepdf import Pdf
from pikepdf.form import Form
import re


def make_html(path:str|Path, *, pdf2html:str='pdf2htmlex', zoom:int|float=1, from_page:int|None=None, to_page:int|None=None, **process_form_args):
    output_path = tempfile.mktemp()
    
    pdf2html_options = [
        '--zoom', str(zoom), 
        '--no-drm', '1',
        '--printing', '0',
    ]
    if from_page is not None:
        pdf2html_options.append('--first-page')
        pdf2html_options.append(str(from_page))
    if to_page is not None:
        pdf2html_options.append('--last-page')
        pdf2html_options.append(str(to_page))
    print(pdf2html_options)

    # Run pdf2htmlex to get the initial base HTML
    result = run([
        pdf2html,
        *pdf2html_options,
        path,
        os.path.relpath(output_path)
    ])
    result.check_returncode()

    with open(output_path, 'r') as file:
        soup = TemplateSoup(file, 'lxml')

    # Remove all the extra stuff we don't need
    for script in soup.find_all('script'):
        script.decompose()
    for el in soup.find_all(id='sidebar'):
        el.decompose()
    for el in soup.find_all(class_='loading-indicator'):
        el.decompose()
    for el in soup.find_all(class_='pi'):
        el.decompose()
    for el in soup.find_all('style'):
        if '* Fancy styles for pdf2htmlEX' in el.string:
            el.decompose()
        elif '* Base CSS for pdf2htmlEX' in el.string:
            # This one also has a lot of junk we don't need, but some stuff we do.
            css = el.string
            # All the UI-related stuff right after the header
            css = re.sub('(?<=\*/).*?(?=\.pf\{)', '', css)
            # Selection, page info (.pi), css drawings (.d), text input (.it), radio input (.ir) 
            css = re.sub('::(-moz-)?selection\{background:rgba\(127,255,255,0\.4\)\}.*', '', css)
            el.string = css
    
    # Add our own stuff direct from the PDF
    with Pdf.open(path) as pdf:
        form = Form(pdf)
        add_form_fields(soup, pdf, form,
            zoom=zoom, 
            start_page=from_page,
            **process_form_args
        )

    return soup