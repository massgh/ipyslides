"""
Display source code from files/context managers.
"""

import ipywidgets as ipw
import sys, linecache
from io import StringIO
import textwrap
import inspect
from IPython.display import Code
from contextlib import contextmanager
from markdown import markdown

from .utils import alert, details
from .formatter import highlight
    

# Do not use this in main work, just inside a function
class _Source_Widget(ipw.HTML):
    "Source code widget for IPython, give html fixed code as value."
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._code = self.value # Save original code for later operations
        self.raw = '' # Raw code
    
    def _repr_html_(self):
        "Make it available in `write` command as well."
        return self.value
    
    def __format__(self, spec):
        return f'{self.value:{spec}}'
        
    def show_lines(self, lines):
        "Return source object with selected lines from list/tuple/range of lines."
        self.value = self._code # Reset to original code first
        if not isinstance(lines,(list,tuple,range)):
            raise TypeError(f'lines must be list, tuple or range, not {type(lines)}')
        
        start, *middle = self._code.split('<code>')
        middle[-1], end = middle[-1].split('</code>')
        middle[-1] += '</code>'
        _max_index = len(middle) - 1
        
        new_lines = [start]
        picks = [-1,*sorted(lines)]
        for a, b in zip(picks[:-1],picks[1:]):
            if b - a > 1: # Not consecutive lines
                new_lines.append(f'<code class="code-no-focus"> + {b - a - 1} more lines ... </code>')
            new_lines.append('<code>' + middle[b])
        
        if lines and lines[-1] < _max_index:
            new_lines.append(f'<code class="code-no-focus"> + {_max_index - lines[-1]} more lines ... </code>')
        
        self.value = ''.join([*new_lines, end])   # update value 
        return self      
    
    def show_all(self):
        "Show all lines. Call this after you may consumed lines using `show_lines`."
        self.value = self._code
        return self
    
    def focus_lines(self, lines):
        "Return source object with focus on given list/tuple/range of lines."
        self.value = self._code # Reset to original code first
        if not isinstance(lines,(list,tuple,range)):
            raise TypeError(f'lines must be list, tuple or range, not {type(lines)}')
        
        _lines = []
        for i, line in enumerate(self._code.split('<code>'), start = -1):
            if i == -1:
                _lines.append(line) # start things
            elif i not in lines:
                _lines.append('<code class="code-no-focus">' + line)
            else:
                _lines.append('<code class="code-focus">' + line)
        
        self.value = ''.join(_lines)  # update value
        return self

def _file2code(filename,language='python',name=None,**kwargs):
    "Only reads plain text or StringIO, return source object with `show_lines` and `focus_lines` methods."
    try:
        text = filename.read() # if stringIO
    except:
        with open(filename,'r') as f:
            text = f.read()
    
    return _str2code(text,language=language,name=name,**kwargs)


def _str2code(text,language='python',name=None,**kwargs):
    "Only reads plain text source code, return source object with `show_lines` and `focus_lines` methods."
    out = _Source_Widget(value = highlight(text,language = language, name = name).value,**kwargs)
    out.raw = text
    return out

class Source:
    current = None
    def __init__(self):
        raise Exception("""This class is not meant to be instantiated.
        Use Source.context() to get a context manager for source.
        Use Source.current to get the current source object.
        Use Source.from_file(filename) to get a source object from a file.
        Use Source.from_string(string) to get a source object from a string.
        Use Source.from_callable(callable) to get a source object from a callable.
        """)
    @classmethod
    def from_string(cls,text,language='python',name=None,**kwargs):
        "Creates source object from string. `name` is alternate used name for language. `kwargs` are passed to `ipyslides.formatter.highlight`."
        cls.current = _str2code(text,language=language,name=name,**kwargs)
        return cls.current
    
    @classmethod
    def from_file(cls, filename,language='python',name=None,**kwargs):
        "Returns source object with `show_lines` and `focus_lines` methods. `name` is alternate used name for language.`kwargs` are passed to `ipyslides.formatter.highlight`"
        _title = filename if name is None else name
        cls.current = _file2code(filename,language=language,name=_title,**kwargs)
        return cls.current
    
    @classmethod       
    def from_callable(cls, callable,**kwargs):
        "Returns source object from a given callable [class,function,module,method etc.] with `show_lines` and `focus_lines` methods. `kwargs` are passed to `ipyslides.formatter.highlight`"
        for _type in ['class','function','module','method','builtin','generator']:
            if getattr(inspect,f'is{_type}')(callable):
                source = inspect.getsource(callable)
                cls.current = _str2code(source,language='python',name=None)
                return cls.current
    
    @classmethod
    @contextmanager
    def context(cls, collapsed = False, focus_lines = None):
        """Excute and displays source code in the context manager. Set `collapsed = True` to display in collapse.
        `foucs_lines` is a list/tuple/range of line index to be highlighted. Useful when source is written inside context manager itself.
        **Usage**:
        ```python
        with source.context() as s: #if not used as `s`, still it is stored in variable `__current_source_code__` that you can acess by this name or from `LiveSlides.current_source`
            do_something()
            #s is the source code that will be avaialble outside the context manager
        write(s)
        #s.raw, s.value are accesible attributes.
        #s.focus_lines, s.show_lines are methods that return object of same type.
        # iwite(s) will update the source even inside the context manager.
        ```
        """     
        def frame():
            "This is better than traceback as it works same for IPython and script.py"
            return (sys._getframe().f_back.f_back.f_back.f_code.co_filename,
                    sys._getframe().f_back.f_back.f_back.f_lineno) #should be in function and go back three times

        file, l1 = frame()
        _alert = alert('You can get code once you exit context manager for `write` command <center>OR</center>use it will auto update inside `iwrite` command')
        return_obj = _Source_Widget(value=f'{_alert}')
        return_obj.raw = ''

        cls.current = return_obj # add to user namespace, this does not create extra object, just points to same
        try:
            yield return_obj
        finally:
            file, l2 = frame()
            lines = linecache.getlines(file)[l1:l2]

            code = textwrap.dedent(''.join(lines))
            return_obj.raw = code
            out_code = _str2code(code).value #needs further processing

            if collapsed:
                return_obj._code =  details(out_code,summary='Show Code').value #details is _HTML
            else:
                return_obj._code = out_code 
                
            return_obj.value = return_obj._code # Update the value of the widget
        
        if isinstance(focus_lines,(list,tuple,range)):
            _ = return_obj.focus_lines(focus_lines) # highlight lines, no need to return self here
