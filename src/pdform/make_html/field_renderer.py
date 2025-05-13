from html import escape
from pikepdf.form import _FieldWrapper

class FieldRenderer:
    """
    Used to render HTML inputs in the output HTML. Subclass to output the inputs in various different template formats (e.g. Jinja, PHP, etc...).
    """
    _renderer_type = None
    type: str
    name: str
    label: str
    style: dict
    field: _FieldWrapper

    def __init__(self, field):
        self.field = field

    @classmethod
    def set_render_type(cls, renderer):
        if not issubclass(renderer, cls):
            raise TypeError('Renderer type must be a subclass of FieldRenderer')
        cls._renderer_type = renderer
    
    @classmethod
    def make(cls, type, field):
        renderer = (cls._renderer_type or cls)(field)
        renderer.type = type
        return renderer
    
    def __str__(self):
        return self.render()

    def render(self):
        if self.type == 'button':
            return self.render_button()
        if self.type == 'checkbox':
            return self.render_checkbox()
        if self.type == 'file':
            return self.render_file()
        if self.type == 'password':
            return self.render_password()
        if self.type == 'radio':
            return self.render_radio()
        if self.type == 'select':
            return self.render_select()
        if self.type == 'signature':
            return self.render_signature()
        if self.type == 'text':
            return self.render_text()
        if self.type == 'textarea':
            return self.render_textarea()
        raise ValueError(f'Unknown input type: {self.type}')

    def render_style_attr_value(self):
        if self.style is None:
            return None
        return escape(';'.join([f"{key}:{value}" for key,value in self.style.items()]))
    
    def render_template_value_variable(self):
        """If this renderer is for a template type, returns the variable name that should contain the value of this field."""
        return ''

    def render_button(self):
        """Render a push button using the properties of this renderer"""
        return f""""""

    def render_checkbox(self):
        """Render a checkbox using the properties of this renderer"""
        return f"""<input type='checkbox' {self.render_basic_attrs()} {self.render_value_checked_if()}/>"""

    def render_file(self):
        """Render a file input using the properties of this renderer"""
        return f""""""

    def render_password(self):
        """Render a password input using the properties of this renderer"""
        return f"""<input type='password' {self.render_basic_attrs()} {self.render_value_attr()}/>"""

    def render_radio(self):
        """Render a radio button using the properties of this renderer"""
        return f"""<input type='radio' {self.render_basic_attrs()} {self.render_value_checked_if()}/>"""

    def render_select(self):
        """Render a select element using the properties of this renderer"""
        return f"""<select {self.render_basic_attrs()}>
        {''.join(f"<option>{opt.display_value}</option>" for opt in self.field.options)}
        </select>"""

    def render_signature(self):
        """Render a signature field using the properties of this renderer"""
        return f"""<input type='file' data-real-type='signature' {self.render_basic_attrs()}/>"""

    def render_text(self):
        """Render a text field using the properties of this renderer"""
        return f"""<input type='text' {self.render_basic_attrs()} {self.render_value_attr()}/>"""

    def render_textarea(self):
        """Render a multiline text field using the properties of this renderer"""
        return f"""<textarea {self.render_basic_attrs()}>{self.render_value_content()}</textarea>"""

    def render_basic_attrs(self):
        """Render the basic attributes (name and style) to apply to the field, regardless of type."""
        return f"""name='{escape(self.name)}' aria-label='{escape(self.label)}' style='{self.render_style_attr_value()}'"""
    
    def render_value_attr(self):
        """Render the value attribute of a field, or template code to generate such"""
        return ''
    
    def render_value_content(self):
        """Render the raw value of a field (e.g. for use in a textarea), or template code to generate such"""
        return ''
    
    def render_value_checked_if(self):
        """Render the 'checked' attribute for checkboxes or radio buttons, or template code to generate such"""
        return ''

    def render_html_escape(self, value:str):
        """Given a string, which should be a statement in the target template language, and add the 
        code necessary to escape the results for safe inclusion in HTML source."""
        return value
    
    def render_echo_statement(self, stmt:str):
        """Given a string, which should be a statement in the target template language, render the 
        necessary syntax to output the result of the statement into the rendered HTML."""
        return ''
    
    def render_echo_statement_if(self, condition:str, stmt:str, *, html_escape=True):
        """Given two strings, which should be statements in the target template language, render the 
        necessary syntax to output the result of the second statement into the rendered HTML, 
        conditional on the value of the first."""
        return ''
    
    def render_if(self, condition:str, html:str):
        """Given two strings, the first of which should be a statement in the target template 
        language, and the second of which is raw HTML or template code, render the necessary syntax 
        to output the raw value conditional on the statement."""
        return html



class PHPFieldRenderer(FieldRenderer):
    """
    Render the HTML as PHP source code.
    """
    def render_echo_statement(self, stmt:str):
        return f"<?={stmt}?>"
    
    def render_echo_statement_if(self, condition:str, stmt:str, *, html_escape=True):
        if html_escape:
            stmt = self.render_html_escape(stmt)
        return self.render_echo_statement(
            f"{condition} ? '' : {stmt}"
        )
    
    def render_if(self, condition:str, html:str):
        return f"<?php if ({condition}):?>{html}<?endif;?>"

    def render_template_value_variable(self):
        return f"""$fd['{self.name}']"""
    
    def render_value_attr(self):
        return self.render_echo_statement_if(
            f"empty({self.render_template_value_variable()})",
            f"""'value="'.{self.render_html_escape(self.render_template_value_variable())}.'"'""",
            html_escape=False
        )
    
    def render_value_content(self):
        return self.render_echo_statement_if(
            f"empty({self.render_template_value_variable()})",
            self.render_template_value_variable()
        )
    
    def render_value_checked_if(self):
        return self.render_echo_statement_if(
            f"empty({self.render_template_value_variable()})",
            f"'checked'",
            html_escape=False
        )

    def render_html_escape(self, value:str):
        return f"htmlspecialchars({value})"


class JinjaFieldRenderer(FieldRenderer):
    """
    Render the HTML as a Jinja template. This does not use advanced Jinja features, so templates 
    produced may work in other template engines with a similar syntax, requiring little or no 
    modification.
    """
    def render_echo_statement(self, stmt:str):
        return f"{{{{{stmt}}}}}"
    
    def render_echo_statement_if(self, condition:str, stmt:str, *, html_escape=True):
        if html_escape:
            stmt = self.render_html_escape(stmt)
        return self.render_if(condition, self.render_echo_statement(stmt))
    
    def render_if(self, condition:str, html:str):
        return f"""{{% if {condition} %}}{html}{{% endif %}}"""
    
    def render_template_value_variable(self):
        return f"""fd['{self.name}']"""
    
    def render_value_attr(self):
        value = self.render_echo_statement(self.render_html_escape(self.render_template_value_variable()))
        return self.render_if(
            self.render_template_value_variable(),
            f"value='{value}'"
        )
    
    def render_value_content(self):
        return self.render_echo_statement_if(
            self.render_template_value_variable(),
            self.render_template_value_variable()
        )
    
    def render_value_checked_if(self):
        return self.render_if(
            self.render_template_value_variable(),
            'checked'
        )

    def render_html_escape(self, value:str):
        return f"{value} | e"