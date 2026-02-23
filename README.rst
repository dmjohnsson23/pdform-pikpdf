======
PDForm
======

A library and command-line tool for working with PDF interactive forms. It can:

* Describe the available fields in the form
* Convert the PDF to an HTML form
* Populate the PDF form with data

Uses `Pikepdf <https://pikepdf.readthedocs.io/en/latest/index.html>`_.


----------------
Describing Forms
----------------

The ``pdform describe`` command can be used to get information about a PDF form, such as the names and types of fields, allowable options, and so forth. Use ``pdform describe --help`` for command-line options.

.. code-block:: shell

    pdform describe form.pdf

By default, it will show every field in the form, together with all the relevant details about the field. Command-line options exist to filter this view for easier parsing.

.. code-block::

    =========================================================================
    stream <_io.BufferedReader name='../../pikepdf/tests/resources/form.pdf'>
    =========================================================================

    Text1
    -----

    Label:
            Text1

    Type:
            TextField

    Required:
            No

    Read Only:
            No

    Multiline:
            No

    Max Length:
            None

    Default Value:


    Current Value:

    ... and so on ...

-------------
Filling Forms
-------------

Filling forms is done using the ``pdform fill-form`` command. Typically, this will be done using JSON-formatted data, such as:

.. code-block:: json

    {
        "TextField1": "Some Text",
        "Checkbox1": true,
        "RadioGroup1": "3",
        "ChoiceField1": "Option 4",
        "SignatureField": "/home/myself/signature.png"
    }

You can then call the command with this JSON:

.. code-block:: shell

    pdform fill-form template.pdf output.pdf data.json

Or pipe this JSON into the command:

.. code-block:: shell

    echo {your json here} | pdform fill-form template.pdf output.pdf -


------------------
Converting to HTML
------------------

Converting to HTML relies on `pdf2htmlEX <https://pdf2htmlex.github.io/pdf2htmlEX/>`_ to generate the initial HTML. We then use `BeautifulSoup <https://beautiful-soup-4.readthedocs.io/en/latest/>`_ to strip away most of the unnessesary code, and add the form fields.

This function can be activated in one of two ways:


1. The ``pdform make-html`` command. Use ``pdform make-html --help`` for details.
2. Directly via Python.

The command-line interface is sufficient for basic usage. It provides a handful of different output formats: plain HTML, Jinja, and PHP.

.. code-block:: shell

    pdform make-html --jinja input.pdf output.jinja

However, it is likely you may wish to customize the rendered HTML. The Python interfaces gives much more flexibility for this.

.. code-block:: python

    from pdform.make_html import FieldRenderer, make_html

    # Define your own field renderer to control the emitted code for form fields
    class MyFieldRenderer(FieldRenderer):
        # See the source code for details on how to implement this class
        ...

    soup = make_html(path, field_renderer_class=MyFieldRenderer)
    # Use the BeautifulSoup object to perform any post-processing to the generated HTML
    # (See the BeautifulSoup documentation for how to use it to manipulate the DOM)
    ...
    # Output the rendered HTML
    print(soup.prettify())