from bs4 import BeautifulSoup
from bs4.element import PreformattedString
from string import Template
from secrets import token_hex

class TemplateSoup(BeautifulSoup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = {}
        self._substitutions = {}

    def __str__(self):
        return Template(super().__str__()).safe_substitute(self._substitutions)
    
    def prettify(self, *args, **kwargs):
        return Template(super().prettify(*args, **kwargs)).safe_substitute(self._substitutions)
    
    def make_placeholder(self, name:str|None = None, value=None)->'Placeholder':
        if name is None:
            name = substitution_name = 'p'+token_hex(16)
        else:
            substitution_name = name+token_hex(8)
        pl = Placeholder(substitution_name)
        if value is not None:
            pl.substitution_value = value
        self.template[name] = pl
        self._substitutions[substitution_name] = pl.substitution_string_proxy
        return pl


class Placeholder(PreformattedString):
    PREFIX: str = "${"
    SUFFIX: str = "}"

    substitution_value = None
    
    @property
    def substitution_string(self):
        return str(self.substitution_value)
    
    @property
    def substitution_string_proxy(self):
        return _SubstitutionStringProxy(self)


class _SubstitutionStringProxy:
    def __init__(self, placeholder:Placeholder):
        self.placeholder = placeholder
    
    def __str__(self):
        return self.placeholder.substitution_string