from __future__ import annotations
from .template_soup import TemplateSoup
from pikepdf import Pdf, Annotation
from pikepdf.form import Form, TextField, CheckboxField, RadioButtonGroup, ChoiceField, SignatureField
from .field_renderer import FieldRenderer
from typing import Type, Union
from functools import cmp_to_key


def add_form_fields(soup: TemplateSoup, pdf:Pdf, form: Form, zoom: Union[int,float] = 1, rename_fields = {}, field_labels = {}, sort_widgets=False, start_page:int=1, field_renderer_class:Type[FieldRenderer]=FieldRenderer):
    """
    :param rename_fields: A mapping of PDF field names to desired HTML field names.
    :param field_labels: A mapping of PDF field names to human-readable labels.
    :param sort_widgets: Attempt to sort widgets according to their visual placement on the page. 
        This can be useful for PDF forms where the tab order is illogical, though some manual 
        refinement may still be needed afterward for a truly logical tab order.
    """

    html_form = soup.find(id='page-container').wrap(soup.new_tag('form'))
    html_pages = html_form.find_all(class_='pf')
    rendered_fields = {}
    i = 0
    for page_no, pdf_page in enumerate(pdf.pages, 1):
        if page_no < start_page: continue
        widgets = form.get_widget_annotations_for_page(pdf_page)
        if not widgets: continue
        html_page = html_pages[page_no-start_page]
        fieldset = soup.new_tag('div', attrs={'class':'form-inputs'})
        if callable(sort_widgets):
            widgets = sort_widgets(widgets)
        elif sort_widgets is True:
            widgets = sorted(widgets, key=cmp_to_key(_cmp_widgets))
        for widget in widgets:
            widget: Annotation
            field = form.get_field_for_annotation(widget)
            i += 1
            if field.is_radio_button:
                field = RadioButtonGroup(form, field)
                input = field_renderer_class.make('radio', field)
            elif field.is_checkbox:
                field = CheckboxField(form, field)
                input = field_renderer_class.make('checkbox', field)
            elif field.is_pushbutton:
                input = field_renderer_class.make('button', field)
            elif field.is_text:
                field = TextField(form, field)
                if field.is_multiline:
                    input = field_renderer_class.make('textarea', field)
                elif field.is_password:
                    input = field_renderer_class.make('password', field)
                elif field.is_password:
                    input = field_renderer_class.make('file', field)
                else:
                    input = field_renderer_class.make('text', field)
            elif field.is_choice:
                field = ChoiceField(form, field)
                input = field_renderer_class.make('select', field)
            elif field.field_type == "/Sig":
                field = SignatureField(form, field)
                input = field_renderer_class.make('signature', field)
            else:
                continue
            name = field.fully_qualified_name
            if callable(rename_fields):
                input.name = rename_fields(name, field)
            elif isinstance(rename_fields, dict) and name in rename_fields:
                input.name = rename_fields[name]
            elif rename_fields is True:
                input.name = _auto_rename(name)
            else:
                input.name = name
            if name in field_labels:
                input.label = field_labels[name]
            else:
                input.label = field.alternate_name
            # The PDF format considers the bottom-left corner to be the origin, so we use that to place
            scale = zoom
            input.style = {
                'position': 'absolute',
                'left': f'{widget.rect.llx*scale}px',
                'bottom': f'{widget.rect.lly*scale}px',
                'width': f'{widget.rect.width*scale}px',
                'height': f'{widget.rect.height*scale}px',
            }
            fieldset.append(soup.make_placeholder(value=input))
        html_page.append(fieldset)
    style = soup.new_tag('style')
    style.append("""
        .form-inputs{
            bottom: 0;
            left: 0;
            position: absolute;
        }
        .form-inputs input,
        .form-inputs textarea,
        .form-inputs select{
            border: none;
            background: rgba(0,0,0,.05);
            resize: none;
            appearance: none;
            margin: 0
        }
        .form-inputs input:hover,
        .form-inputs textarea:hover,
        .form-inputs select:hover{
            box-shadow: inset 0 0 5px 5px rgba(0, 0, 0, .1);
        }
        .form-inputs input:checked::after{
            display: block;
            content: '\\2714';
            width: 100%;
            height: 100%;
            text-align: center;
        }
    """)
    soup.find('head').append(style)
    return rendered_fields


_rename_re = None
def _auto_rename(name:str):
    global _rename_re
    if _rename_re is None:
        import re
        _rename_re = re.compile('[^A-Za-z0-9]+')
    name = _rename_re.sub('_', name).strip('_')
    if name[0].isdigit():
        return f"_{name}"
    return name


def _cmp_widgets(wig1: Annotation, wig2: Annotation):
    rect1 = wig1.rect
    rect2 = wig2.rect
    w1_then_w2 = -1
    w2_then_w1 = 1
    if rect1.lly >= rect2.ury:
        # Bottom of wig1 above top of wig2; wig2 is after wig1
        return w1_then_w2
    if rect1.ury <= rect2.lly:
        # Top of wig1 below bottom of wig2; wig2 is before wig1
        return w2_then_w1
    # The two are in line, or at leaest overlapping in the y direction; compare x values
    if rect1.urx <= rect2.llx:
        # Right of wig1 before left of wig2; wig2 is after wig1
        return w1_then_w2
    if rect1.llx >= rect2.urx:
        # Left of wig1 after right of wig2; wig2 is before wig1
        return w2_then_w1
    # Rectangles overlap in both x and y directions, let's just compare top-left corner
    if rect1.ury > rect2.ury:
        # rect1 higher than rect2; wig2 is after wig1
        return w1_then_w2
    if rect1.ury < rect2.ury:
        # rect1 lower than rect2; wig2 is before wig1
        return w2_then_w1
    if rect1.llx > rect2.llx:
        # rect1 further than rect2; wig2 is before wig1
        return w2_then_w1
    if rect1.llx < rect2.llx:
        # rect2 further than rect1; wig2 is after wig1
        return w1_then_w2
    # Okay, we give up, they share the same upper-left
    return 0
