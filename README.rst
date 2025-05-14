======
PDForm
======

A library and command-line tool for working with PDF forms.

Uses `Pikepdf <https://pikepdf.readthedocs.io/en/latest/index.html>`_.


----------------
Describing Forms
----------------

The :command:`pdform describe` command can be used to get information about a PDF form, such as the names and types of fields, allowable options, and so forth. Use `pdform describe --help` for command-line options.


-------------
Filling Forms
-------------

Filling forms is done using the `pdform fill-form` command. Typically, this will be done using JSON-formatted data, such as:

.. code-block:: json

    {
        "TextField1": "Some Text",
        "Checkbox1": true,
        "RadioGroup1": "3",
        "ChoiceField1": "Option 4",
        "SignatureField": "/home/myself/signature.png"
    }

You can then pipe this JSON into the command.


------------------
Converting to HTML
------------------

Converting to HTML relies on `pdf2htmlEX <https://pdf2htmlex.github.io/pdf2htmlEX/>`_ to generate the initial HTML. We then use `BeautifulSoup <https://beautiful-soup-4.readthedocs.io/en/latest/>`_ to strip away most of the unnessesary code, and add the form fields.

This function can be activated in one of two ways:


1. The :command:`pdform make-html` command. Use :command:`pdform make-html --help` for details.
2. Directly via Python.

The command-line interface is sufficient for basic usage. However, it is likely you may wish to customize the rendered HTML. The Python interfaces gives much more flexibility for this.

.. code-block:: python

    from pdform.make_html import FieldRenderer, make_html

    # Define your own field renderer to control the emitted code for form fields
    class MyFieldRenderer(FieldRenderer):
        ...

    soup = make_html(path, field_renderer_class=MyFieldRenderer)
    # Use the BeutifulSoup object to perform any post-processing to the generated HTML
    ...
    # Output the rendered HTML
    print(soup.prettify())