import click
from make_html.make_html import make_html
from make_html.field_renderer import FieldRenderer, PHPFieldRenderer
from make_html.template_soup import TemplateSoup
from html import escape
import re
from pikepdf import Pdf, Name, Rectangle, Annotation
from pikepdf.form import Form, SignatureField, _FieldWrapper
from collections import Counter
from pathlib import Path
import requests
from shutil import copyfileobj
from bs4 import Doctype

class VetraSpecFieldRenderer(PHPFieldRenderer):
    def render_html_escape(self, value):
        return f"nonDuplicatedEscape({value})"
    
    def render_template_value_variable(self):
        return f"${self.name}??''"
    
    def render_signature(self):
        ll = self.label.lower()
        if 'representative' in ll:
            sig_type_params = '''signer-type="veteran" signer-id="<?=$vetId??''?>"'''
        elif 'veteran' in ll or 'claimant' in ll or 'required' in ll:
            sig_type_params = '''signer-type="user" signer-id="<?=$sessionUser['user_id']?>"'''
        else:
            sig_type_params = ''
        return f"""
        <input type='hidden' name='{escape(self.name)}' id='{escape(self.name)}' value="{self.render_echo_statement_if(
            f"isset(${self.name})",
            f'"/docs/sigs/${self.name}"'
        )}"/>
        <vs-signature backed-by="{escape(self.name)}" style='{self.render_style_attr_value()}' aria-label='{escape(self.label)}' {sig_type_params}></vs-signature>
        """

FieldRenderer.set_render_type(VetraSpecFieldRenderer)


remove_re = re.compile('F?\[\d+\]|(sub)?form_?\d*\.?|page_?\d*\.?', re.IGNORECASE)
rename_re = re.compile('[^A-Za-z0-9]+')
name_counter = Counter()
mapping = {}
def field_rename(name:str, field:_FieldWrapper):
    global name_counter, mapping
    orig_name = name
    if isinstance(field, SignatureField):
        name = 'sig'
    else:
        name = remove_re.sub('', name)
        name = rename_re.sub('_', name).strip('_')
        if name[0].isdigit():
            name = f"_{name}"
        if name[-1].isdigit():
            name = f"{name}_"
    if name in name_counter:
        name_counter[name] += 1
        name = name+str(name_counter[name])
    else:
        name_counter[name] = 1
        name = name.rstrip('_')
    mapping[orig_name] = name
    return name


def post_process(soup:TemplateSoup):
    for item in soup.contents:
        if isinstance(item, Doctype):
            item.extract()
    for el in soup.find_all(class_='pf'):
        el['class'].append('form-page')
        el['class'].remove('pf')
    for el in soup.find_all('a'):
        el['target'] = '_blank'
    for el in soup.find_all('meta'):
        el.decompose()
    head = soup.find('head')
    for child in head.children:
        if child.name != 'style':
            child.decompose()
    head.unwrap()
    soup.find('body').unwrap()
    soup.find('html').unwrap()
    soup.find('form').unwrap()


def make_map_file(pdf, form, map_file):
    sigs = []
    map_file.writelines((
        "<?php return function($fd){\n",
        "    return [\n",
    ))
    for pageno, page in enumerate(pdf.pages, start=1):
        map_file.write(
            f"\n\n        // ===== Page {pageno} ===== //\n"
        )
        for widget in form.get_widget_annotations_for_page(page):
            field = form.get_field_for_annotation(widget)
            field = form._wrap(field, field.fully_qualified_name)
            value_string = _get_value_string(widget, field, pageno, sigs)
            map_file.writelines((
                f'        // {field.alternate_name}\n',
                f'        "{field.fully_qualified_name}" => {value_string},\n',
            ))
    map_file.writelines((
        "    ];\n",
        "};\n",
    ))
    return sigs


def _get_value_string(widget: Annotation, field: _FieldWrapper, pageno:int, sigs:list):
    input_name = mapping.get(field.fully_qualified_name, 'vs_form_input_name')
    if isinstance(field, SignatureField):
        sigs.append((pageno, widget, field))
        return f"\\Vetraspec\\Utilities\\File::locateFile('docs/sigs', $fd->{input_name})"
    elif field.is_checkbox:
        return f"checkbox($fd->{input_name})"
    elif field.is_radio_button:
        nl = '\n            '
        return f"""radioCheckboxes([{nl}{f',{nl}'.join([
            f'// {opt._annot_dict.NM or opt._annot_dict.TU}{nl}"{opt.on_state}" => $fd->{input_name}'
            for opt in field.options
        ])}\n        ])"""
    else:
        return f"$fd->{input_name}"


def make_vetsign_file(pdf, codename, sign_file, sigs):
    sign_file.writelines((
        "<?php return new \\Vetraspec\\Integrations\\VetSign\\Form(\n",
        f"    '{codename}', // Name that will be shown to users\n",
        "    1, // starting page number\n",
        "    [ // Choose the appropriate signature below and change the key to 'veteran'\n",
    ))
    for pageno, widget, sig in sigs:
        rect = widget.rect
        mbox = Rectangle(pdf.pages.p(pageno).trimbox)
        # Convert the coords.
        # PDF coords are in pt from the bottom left. Vetsign coords are in px from the top left.
        # Scale factor from `getScale()` at https://vbaturnkey-vetsign.echo.tylerfederal.com/page.request.do?page=com.micropact.product.component.pdf.page.pdfeditorjs
        scale_factor = 1.25
        x = round((rect.llx) * scale_factor)
        y = round((mbox.height - rect.ury) * scale_factor)
        sign_file.writelines((
                f'        // {sig.alternate_name}\n',
                f'        "{sig.fully_qualified_name}" => [\n',
                f'            {pageno}, // Page number\n',
                f'            {x}, // X Coordinate\n',
                f'            {y}, // Y Coordinate\n',
                f'            "", // Name of corresponding date field\n',
                f'        ],\n',
            ))
    sign_file.writelines((
        "    ],\n",
        ");\n",
    ))


def calc_form_pages(pdf: Pdf, form: Form):
    first_page = 1
    last_page = None
    for pageno, page in enumerate(pdf.pages, start=1):
        widgets = form._acroform.get_widget_annotations_for_page(page)
        if widgets:
            last_page = pageno
        elif last_page is None:
            # No widgets, and we have't seen any widgets yet either
            first_page = pageno+1
    return first_page, last_page


def make_formdef_file(form_file, instructions_url=None):
    form_file.write(
        "<?php return new class ($form_name, $vet_id, $id) extends \Vetraspec\Forms\Form{\n"
    )
    if instructions_url is not None:
        form_file.write(
            f"    public $instructions = '{instructions_url}';\n"
        )
    form_file.write(
        "    function new_form($vetData, $questionnaire){\n"
        "        // Fill the array below with any values that need mapped from the veteran's data. Some\n"
        "        // guesses have been made, but should be reviewed. Delete any items that are not needed.\n"
        "        // Pull additional data from the database as needed.\n"
        "        return [\n"
    )
    for real_name, fieldname in mapping.items():
        form_file.write(
            f"            '{fieldname}'=>{_guess_vs_mapping(real_name)},\n"
        )
    form_file.write(
        "        ];\n"
        "    }\n"
        "};"
    )

_vs_mapping_guesses = (
    (re.compile('(dob|birth).?month', re.I), "normalizeDate($vetData['dob'], 'm')"),
    (re.compile('(dob|birth).?day', re.I), "normalizeDate($vetData['dob'], 'd')"),
    (re.compile('(dob|birth).?year', re.I), "normalizeDate($vetData['dob'], 'Y')"),
    (re.compile('va.?(file|claim).?number', re.I), "$vetData['va_claim_num']"),
    (re.compile('vet(eran)?s?.?last.?name', re.I), "$vetData['f_name']"),
    (re.compile('vet(eran)?s?.?middle.?(name|initial)', re.I), "$vetData['m_name']"),
    (re.compile('vet(eran)?s?.?first.?name', re.I), "$vetData['l_name']"),
    (re.compile('vet(eran)?s?.?(social.?security(.?number)?|ssn).?first.?(three|3)', re.I), "explodeFixed('-', $vetData['ssn'])[0]"),
    (re.compile('vet(eran)?s?.?(social.?security(.?number)?|ssn).?(second|middle).?(two|2)', re.I), "explodeFixed('-', $vetData['ssn'])[1]"),
    (re.compile('vet(eran)?s?.?(social.?security(.?number)?|ssn).?last.?(four|4)', re.I), "explodeFixed('-', $vetData['ssn'])[2]"),
    (re.compile('vet(eran)?s?.?(social.?security(.?number)?|ssn)', re.I), "$vetData['ssn']"),
)
def _guess_vs_mapping(name):
    for regex, value in _vs_mapping_guesses:
        if regex.search(name):
            return value
    return 'null'

@click.command('make-form')
@click.argument('codename')
@click.option('--url', prompt='Direct download URL for the PDF')
@click.option('--output-dir', '-o', help='Output to this directory', type=click.Path(True, file_okay=False, dir_okay=True, writable=True), default=Path.cwd())
@click.option('--pdf2html', help='Override the path used to call Pdf2HmlEX', default='pdf2htmlex')
def cli(codename, url, output_dir, **kwargs):
    pdf_filename = f'{codename}.fillable.pdf'
    map_filename = f'{codename}.fillable.php'
    sign_filename = f'{codename}.vetsign.php'
    template_filename = f'{codename}.tpl.php'
    formdef_filename = f'{codename}.form.php'
    instructions_filename = f'{codename}.instructions.pdf'

    result = requests.get(url, stream=True)
    result.raise_for_status()
    with open(output_dir / pdf_filename, 'w+b') as pdf_file:
        copyfileobj(result.raw, pdf_file)
        pdf_file.seek(0)
        pdf = Pdf.open(pdf_file)
        form = Form(pdf)
        # Find page rage of real form
        first_page, last_page = calc_form_pages(pdf, form)
        # Extract the instructional pages from before/after the form
        has_instructions = False
        inst_pdf = Pdf.new()
        for pageno, page in enumerate(pdf.pages, start=1):
            if pageno < first_page or pageno > last_page:
                has_instructions = True
                inst_pdf.pages.append(page)
        inst_pdf.remove_unreferenced_resources()
        if has_instructions:
            inst_pdf.save(output_dir / instructions_filename, min_version=max(inst_pdf.pdf_version, pdf.pdf_version))
        inst_pdf.close()
        # Create the other, vetraspec-specific files
        with open(output_dir / map_filename, 'w') as map_file:
            sigs = make_map_file(pdf, form, map_file)
        with open(output_dir / sign_filename, 'w') as sign_file:
            make_vetsign_file(pdf, codename, sign_file, sigs)
        with open(output_dir / formdef_filename, 'w') as formdef_file:
            make_formdef_file(formdef_file, f"/forms/{instructions_filename}" if has_instructions else None)
    # Make the HTML version of the PDF
    soup = make_html(output_dir / pdf_filename, sort_widgets=True, rename_fields=field_rename, zoom=2, from_page=first_page, to_page=last_page, **kwargs)
    with open(output_dir / (template_filename+'.raw.html'), 'w') as file:
        file.write(soup.prettify())
    post_process(soup)
    with open(output_dir / template_filename, 'w') as file:
        file.write(soup.prettify())
    click.echo(
        click.style("The conversion process is complete!\n\n", fg='green'),
        "Some manual work is still needed to create a fully-functional form in VetraSpec:\n"
        f"1. The data mapping in {map_filename} will need to be updated.\n"
        f"2. The correct signature will need to be selected in {sign_filename}.\n"
        f"3. The field order in {template_filename} may need to be adjusted.\n"
        f"4. You will need to determine how the form is to be printed. Either,\n"
        f"   a. Use the `fill-form` printer option, or\n"
        f"   b. Manually build a print version ({template_filename}.raw.html can be used as a base).\n"
        f"5. Perform other customizations if needed, such as to suport Benefits Claims.\n"
        f"6. Copy the files into the appropriate places.\n"
        f"6. Create or update the `resources.form_config` entry.\n"
    )


cli()