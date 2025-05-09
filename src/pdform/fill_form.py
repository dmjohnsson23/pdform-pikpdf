from io import BytesIO
from pikepdf import Name, Pdf, Page, Rectangle
from pikepdf.form import Form, TextField, CheckboxField, RadioButtonGroup, ChoiceField, SignatureField, ExtendedAppearanceStreamGenerator
from PIL import Image


def img_to_pdf(img) -> Pdf:
    """
    Convert an image to a PDF.

    The input image may be:

    * An open file-like object
    * A path
    * A base64 data URL
    """
    if isinstance(img, str) and img.startswith('data:'):
        # embedded base64
        from base64 import b64decode
        _, path = path.split(',', 2)
        path = BytesIO(b64decode(path))
    # Open image and convert to RGB (Greyscale images cause issues)
    img = Image.open(img).convert('RGB')
    # Convert the image to a PDF
    pdf_img = BytesIO()
    img.save(pdf_img, 'pdf')
    pdf_img.seek(0)
    return Pdf.open(pdf_img)


def stamp(img, page:Page, rect:Rectangle):
    """
    Stamp an image on the page, fitting it in the box of the given rect.

    :param img: The image to stamp. Can be a file path, open file object, or base64 data URL.
    :param page: The page to stamp the image on.
    :param rect: The box in which to place the image. The image will be scaled to fit.
    """
    with img_to_pdf(img) as stamp_pdf:
        page.add_overlay(stamp_pdf.pages[0], rect)


def fill_form(pdf:Pdf, data:dict):
    """
    Fill the form fields of the given PDF with the data provided.

    :param pdf: The PDF to populate with data
    :param data: The data to populate the form with. The keys of this dictionary should match
        the field's fully-qualified name. The values should be as follows:

        * For text fields, provide the value to set
        * For checkboxes, provide a boolean
        * For radio buttons, provide the value in the button's AP.N dictionary
        * For signature fields, provide the path to an image which will be stamped in its place (real
          cryptographic signatures are not supported)
    """
    # Populate form
    form = Form(pdf, ExtendedAppearanceStreamGenerator)
    for key, field in form.items():
        if key and key in data and data[key] is not None:
            value = data[key]
            if isinstance(field, (TextField, ChoiceField)):
                field.value = value
            elif isinstance(field, CheckboxField):
                if value is True:
                    field.checked = True
                elif value is None or value is False:
                    field.checked = False
                else:
                    field.value = to_name(value)
            elif isinstance(field, RadioButtonGroup):
                field.value = to_name(value)
            elif isinstance(field, SignatureField):
                if isinstance(value, str):
                    img = value
                    expand = None
                else:
                    img = value['img']
                    expand = value.get('expand_rect')
                with img_to_pdf(img) as stamp_pdf:
                    field.stamp_overlay(stamp_pdf.pages[0], expand_rect=expand)
    if '.stamps' in data:
        # Custom stamps not associated with fields
        for stamp_data in data['.stamps']:
            if not stamp_data['img']:
                continue
            stamp(stamp_data['img'], pdf.pages[stamp_data['page']-1], Rectangle(*stamp_data['rect']))


def to_name(value: str):
    if not value.startswith('/'):
        value = f"/{value}"
    return Name(value)