import os
from subprocess import run
from .template_soup import TemplateSoup
from bs4 import Tag, BeautifulSoup
import tempfile
from .process_form import add_form_fields
from pathlib import Path
from pikepdf import Pdf
from pikepdf.form import Form
import re
from base64 import urlsafe_b64decode
from io import StringIO
from typing import Optional, Union


def make_html(path:Union[str,Path], *, pdf2html:str='pdf2htmlex', zoom:Union[int,float]=1, from_page:Optional[int]=None, to_page:Optional[int]=None, **process_form_args):
    output_path = tempfile.mktemp()
    
    pdf2html_options = [
        '--zoom', str(zoom), 
        '--no-drm', '1',
        '--printing', '0',
        '--bg-format', 'svg',
    ]
    if from_page is not None:
        pdf2html_options.append('--first-page')
        pdf2html_options.append(str(from_page))
    if to_page is not None:
        pdf2html_options.append('--last-page')
        pdf2html_options.append(str(to_page))

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
    for el in soup.find_all('img'):
        unwrap_svg_img(el)
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
    # Copy any new styles we've created
    sio = StringIO()
    for style, css_class in svg_path_styles.items():
        sio.write('.')
        sio.write(css_class)
        sio.write('{')
        sio.write(style)
        sio.write('}\n')
    sio.seek(0)
    new_styles = soup.new_tag('style')
    new_styles.string = sio.read()
    soup.head.append(new_styles)
    
    # Add our own stuff direct from the PDF
    with Pdf.open(path) as pdf:
        form = Form(pdf)
        add_form_fields(soup, pdf, form,
            zoom=zoom, 
            start_page=from_page,
            **process_form_args
        )

    return soup


path_style_counter = 0
svg_path_styles = {}
def unwrap_svg_img(img_el:Tag):
    global path_style_counter, svg_path_styles
    data_url = img_el['src']
    if not data_url.startswith('data:image/svg+xml;base64,'):
        return
    data_url = data_url[26:]
    svg = BeautifulSoup(urlsafe_b64decode(data_url), 'xml').svg
    del svg['xmlns']
    del svg['xmlns:xlink']
    svg['class'] = img_el['class']
    for path in svg.find_all('path'):
        style = path['style']
        if style in svg_path_styles:
            css_class = svg_path_styles[style]
        else:
            css_class = f"svp{path_style_counter}"
            path_style_counter += 1
            svg_path_styles[style] = css_class
        del path['style']
        path['class'] = css_class
    img_el.replace_with(svg)