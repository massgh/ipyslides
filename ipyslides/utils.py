__all__ = ['print_context', 'write', 'iwrite', 'ihtml', 'details', 'plt2html', 'set_dir', 'textbox',
            'image','svg','file2img','file2text','file2code','fmt2cols','alert','colored','keep_format',
            'source','raw','enable_zoom','html_node','sig','doc']
__all__.extend(['rows','block'])
__all__.extend([f'block_{c}' for c in ['r','g','b','y','c','m','k','o','w','p']])


import sys, linecache, os
import textwrap
import inspect
from io import BytesIO # For PIL image
from contextlib import contextmanager
from IPython.core.getipython import get_ipython
from markdown import markdown
from IPython.display import HTML, display, Code, SVG
from IPython.utils.capture import capture_output
from IPython.core.display import Image, __all__ as __all
import ipywidgets as ipw
from .objs_formatter import format_object, syntax_css, _fix_code, fix_ipy_image
from .objs_formatter import plt2html # For backward cimpatibility and inside class

__reprs__ = [rep.replace('display_','') for rep in __all if rep.startswith('display_')] # Can display these in write command

__md_extensions = ['fenced_code','tables','codehilite','footnotes'] # For MArkdown Parser
@contextmanager
def print_context():
    "Use `print` or function printing with onside in this context manager to display in order."
    with capture_output() as cap:
        yield
    if cap.stderr:
        return cap.stderr
    write(raw(cap.stdout)) # clean whitspace preserved 
    
@contextmanager
def set_dir(path):
    current = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(current)


def _fix_repr(obj):
    if isinstance(obj,str):
        _obj = obj.strip().replace('\n','  \n') #Markdown doesn't like newlines without spaces
        _html = markdown(_obj,extensions=__md_extensions) 
        return _fix_code(_html)
        
    else:
        # Next prefer custom methods of objects. 
        is_true, _html = format_object(obj)
        if is_true:
            return _html
        # Ipython objects
        _reprs_ = [rep for rep in [getattr(obj,f'_repr_{r}_',None) for r in __reprs__] if rep]   
        for _rep_ in _reprs_:
            _out_ = _rep_()
            if _out_: # If there is object in _repr_<>_, don't return None
                return _out_
        
        # Return __repr__ if nothing above
        return f"<div class='PyRepr'>{obj.__repr__()}</div>"
    
def _fmt_write(*columns,width_percents=None):
    if not width_percents and len(columns) >= 1:
        widths = [f'{int(100/len(columns))}%' for _ in columns]
    else:
        widths = [f'{w}%' for w in width_percents]
    _cols = [_c if isinstance(_c,(list,tuple)) else [_c] for _c in columns] 
    _cols = ''.join([f"""<div style='width:{w};overflow-x:auto;height:auto'>
                     {''.join([_fix_repr(row) for row in _col])}
                     </div>""" for _col,w in zip(_cols,widths)])
    _cols = syntax_css() + _cols if 'codehilite' in _cols else _cols
    if len(columns) == 1:
        return _cols
    return f'''<div class="columns">{_cols}</div>'''
        
def write(*columns,width_percents=None): 
    '''Writes markdown strings or IPython object with method `_repr_<html,svg,png,...>_` in each column of same with. If width_percents is given, column width is adjusted.
    Each column should be a valid object (text/markdown/html/ have _repr_<format>_ or to_<format> method) or list/tuple of objects to form rows or explictly call `rows`. 
    
    - Pass int,float,dict,function etc. Pass list/tuple in a wrapped list for correct print as they used for rows writing too.
    - Give a code object from `ipyslides.get_cell_code()` to it, syntax highlight is enabled.
    - Give a matplotlib `figure/Axes` to it or use `ipyslides.utils.plt2html()`.
    - Give an interactive plotly figure.
    - Give a pandas dataframe `df` or `df.to_html()`.
    - Give any object which has `to_html` method like Altair chart. (Note that chart will not remain interactive, use display(chart) if need interactivity like brushing etc.)
    - Give an IPython object which has `_repr_<repr>_` method where <repr> is one of ('html','markdown','svg','png','jpeg','javascript','pdf','pretty','json','latex').
    - Give a function/class/module (without calling) and it will be displayed as a pretty printed code block.
    
    If an object is not in above listed things, `obj.__repr__()` will be printed. If you need to show other than __repr__, use `display(obj)` outside `write` command or use
    methods specific to that library to show in jupyter notebook.
    
    Note: Use `keep_format` method to keep format of object for example `keep_format(altair_chart.to_html())`.
    Note: You can give your own type of data provided that it is converted to an HTML string.
    Note: `_repr_<format>_` takes precedence to `to_<format>` methods. So in case you need specific output, use `object.to_<format>`.
    
    ''' 
    return display(HTML(_fmt_write(*columns,width_percents=width_percents)))

def ihtml(*columns,width_percents=None):
    "Returns an ipywidgets.HTML widget. Accepts content types same as in `write` command but does not allow javascript, so interactive graphs may not render."
    return ipw.HTML(_fmt_write(*columns,width_percents=width_percents))

def _fmt_iwrite(*columns,width_percents=None):
    if not width_percents:
        widths = ['auto' for _ in columns]
    else:
        widths = [f'{w}%' for w in width_percents]
        
    _cols = [_c if isinstance(_c,(list,tuple)) else [_c] for _c in columns] #Make list if single element
    children = [ipw.VBox(children = _c, layout = ipw.Layout(width=f'{_w}')) for _c, _w in zip(_cols,widths)]
    return ipw.HBox(children = children).add_class('columns')

def iwrite(*columns,width_percents=None):
    """Each obj in columns should be an IPython widget like `ipywidgets`,`bqplots` etc or list/tuple (or wrapped in `rows` function) of widgets to display as rows in a column. 
    Text and other rich IPython content like charts can be added with `ihtml`"""
    return display(_fmt_iwrite(*columns,width_percents=width_percents))

def fmt2cols(c1,c2,w1=50,w2=50):
    """Useful when you want to split a column in `write` command in small 2 columns, e.g displaying a firgure with text on left.
    Both `c1` and c2` should be in text format or have  `_repr_<repr>_` method where <repr> is one of 
    ('html','markdown','svg','png','jpeg','javascript','pdf','pretty','json','latex').
    `w1, w2` as their respective widths(int) in percents."""
    return f"""<div class='columns'>
        <div style='width:{w1}%;overflow-x:auto;'>{_fix_repr(c1)}</div>
        <div style='width:{w2}%;overflow-x:auto;'>{_fix_repr(c2)}</div></div>"""  
        
def details(str_html,summary='Click to show content'):
    "Show/Hide Content in collapsed html."
    return f"""<details style='max-height:100%;overflow:auto;'><summary>{summary}</summary>{str_html}</details>"""

def __check_pil_image(data):
    "Check if data is a PIL Image or numpy array"
    if data.__repr__().startswith('<PIL'):
        im_bytes = BytesIO()
        data.save(im_bytes,data.format,quality=95) #Save image to BytesIO in format of given image
        return im_bytes.getvalue()
    return data # if not return back data

def image(data=None,width='80%',caption=None, zoomable=True,**kwargs):
    """Displays PNG/JPEG files or image data etc, `kwrags` are passed to IPython.display.Image. 
    You can provide following to `data` parameter:
        - An opened PIL image. Useful for image operations and then direct writing to slides. 
        - A file path to image file.
        - A url to image file.
        - A str/bytes object containing image data.  
    """
    if isinstance(width,int):
        width = f'{width}px'
    _data = __check_pil_image(data) #Check if data is a PIL Image or return data
    img = fix_ipy_image(Image(data = _data,**kwargs),width=width)
    if caption:
        img = img + textbox(caption)  # Add caption
    if zoomable:
        return f'<div class="zoom-container">{img}</div>'
    return img
    
file2img = image #alias must be there

def svg(data=None,caption=None,zoomable=True,**kwargs):
    "Display svg file or svg string/bytes with additional customizations. `kwrags` are passed to IPython.display.SVG. You can provide url/string/bytes/filepath for svg."
    svg = SVG(data=data, **kwargs)._repr_svg_()
    if caption:
        svg = svg + textbox(caption)  # Add caption 
    if zoomable:
        return f'<div class="zoom-container">{svg}</div>'
    return svg

def enable_zoom(obj):
    "Add zoom-container class to given object, whether a widget or html/IPYthon object"
    try:
        return ipw.Box([obj]).add_class('zoom-container')
    except:
        return {'__keep_format__': f'<div class="zoom-container">{_fix_repr(obj)}</div>'}
    
def html_node(tag,children = [],className = None,**node_attrs):
    """Returns html node with given children and node attributes like style, id etc.
    `tag` can be any valid html tag name.
    `children` expects:
        - str: A string to be added as node's text content.
        - html_node: A html_node to be added as child node.
        - list/tuple of [str, html_node]: A list of str and html_node to be added as child nodes.
    Example:
        html_node('img',src='ir_uv.jpg') #Returns IPython.display.HTML("<img src='ir_uv.jpg'></img>") and displas image if last line in notebook's cell.
        """
    if isinstance(children,str):
        content = children
    elif isinstance(children,(list,tuple)):
        content = ''.join(child if isinstance(child,str) else child._repr_html_() for child in children)
    else:
        try:
            content = children._repr_html_() #Try to get html representation of children if HTML object
        except:
            raise ValueError(f'Children should be a list/tuple of html_node or str, not {type(children)}')
    attrs = ' '.join(f'{k}="{v}"' for k,v in node_attrs.items()) # Join with space is must
    if className:
        attrs = f'class="{className}"' + ' ' + attrs # space is must after className
    return HTML(f'<{tag} {attrs}>{content}</{tag}>')
  
def file2text(filename):
    "Only reads plain text, not bytes"
    with open(filename,'r') as f:
        text = ''.join(f.readlines())   
    return text

def file2code(filename,language='python',max_height='350px'):
    "Only reads plain text"
    if 'ython' in language:
        code = markdown(f'```{language}\n{file2text(filename)}\n```',extensions=__md_extensions)
    else:
        code = Code(filename=filename,language=language)._repr_html_()
    return f'<div style="max-height:{max_height};overflow:auto;">{code}</div>'

def _cell_code(shell,line_number=True,this_line=True,magics=False,comments=False,lines=None):
    "Return current cell's code in slides for educational purpose. `lines` should be list/tuple of line numbers to include if filtered."
    try:
        current_cell_code = shell.get_parent()['content']['code'].splitlines()
    except:
        return '<pre>get_cell_code / _cell_code</pre><p style="color:red;">can only return code from a cell execution, not from a function at run time</p>'
        
    if isinstance(lines,(list,tuple,range)):
        current_cell_code = [line for i, line in enumerate(current_cell_code) if i+1 in lines]
    if not this_line:
        current_cell_code = [line for line in current_cell_code if '_cell_code' not in line]
    if not magics:
        current_cell_code = [line for line in current_cell_code if not line.lstrip().startswith('%')]
    if not comments:
        current_cell_code = [line for line in current_cell_code if not line.lstrip().startswith('#')]
    source = markdown("```python\n{}\n```".format('\n'.join(current_cell_code)),extensions=__md_extensions)
    return _fix_code(source)

def textbox(text, **css_props):
    """Formats text in a box for writing e.g. inline refrences. `css_props` are applied to box and `-` should be `_` like `font-size` -> `font_size`. 
    `text` is not parsed to general markdown i.e. only bold italic etc. applied, so if need markdown, parse it to html before. You can have common CSS for all textboxes using class `TextBox`."""
    css_props = {'display':'inline-block','white-space': 'pre', **css_props} # very important to apply text styles in order
    # white-space:pre preserves whitspacing, text will be viewed as written. 
    _style = ' '.join([f"{key.replace('_','-')}:{value};" for key,value in css_props.items()])
    return f"<span class='TextBox' style = {_style!r}> {text} </span>"  # markdown="span" will avoid inner parsing

def alert(text):
    "Alerts text!"
    return f"<span style='color:#DC143C;'>{text}</span>"
    
def colored(text,fg='blue',bg=None):
    "Colored text, `fg` and `bg` should be valid CSS colors"
    return f"<span style='background:{bg};color:{fg};'>{text}</span>"

def keep_format(plaintext_or_html):
    "Bypasses from being parsed by markdown parser. Useful for some graphs, e.g. keep_raw(obj.to_html()) preserves its actual form."
    if not isinstance(plaintext_or_html,str):
        return plaintext_or_html # if not string, return as is
    return {'__keep_format__':plaintext_or_html} 

def raw(text):
    "Keep shape of text as it is, preserving whitespaces as well."
    return {'__keep_format__':f"<div class='PyRepr'>{text}<div>"}

def rows(*objs):
    "Returns tuple of objects. Use in `write`, `iwrite` for better readiability of writing rows in a column."
    return objs # Its already a tuple

def block(title,*objs,bg = 'olive'):
    "Format a block like in LATEX beamer. *objs expect to be writable with `write` command."
    _title = f"""<center style='background:var(--secondary-bg);margin:0px -4px;'>
                <b>{title}</b></center>"""
    _out = _fmt_write(objs) # single column
    return keep_format(f"""<div style='padding:4px' class='block'>
        <div style='border-top:4px solid {bg};box-shadow: 0px 0px 4px {bg};border-radius:4px;padding:0 4px;'>
        {_title}
        {_out}
        </div></div>""")
    
def block_r(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='crimson')
def block_b(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='navy')
def block_g(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='#006400')
def block_y(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='#E4D00A')
def block_o(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='orange')
def block_p(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='purple')
def block_c(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='#48d1cc')
def block_m(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='magenta')
def block_w(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='whitesmoke')
def block_k(title,*objs):
    "See documentation of `block`."
    return block(title,*objs,bg='#343434')

@contextmanager
def source(collapsed = False):
    """Excute and displays source code in the context manager. Set `collapsed = True` to display in collapse.
    **Usage**:
    ```python
    with source() as s: #if not used as `s`, still it is stored in variable `__current_source_code__` that you can acess by this name or from `LiveSlides.current_source`
        do_something()
        #s is the source code that will be avaialble outside the context manager
    write(s)
    #s.raw, s.html are accesible attributes.
    ```
    """
    def frame():
        "This is better than traceback as it works same for IPython and script.py"
        return (sys._getframe().f_back.f_back.f_back.f_code.co_filename,
                sys._getframe().f_back.f_back.f_back.f_lineno) #should be in function and go back three times
        
    file, l1 = frame()
    #return_obj = SimpleNamespace(raw='',html='',_repr_html_ = lambda:'')
    _alert = alert('You can get code once you exit context manager <center>OR</center>use `ipywidgets.HTML` as placeholder and change its value later, but it will show up at desiered place.')
    return_obj = type("SourceCode",(object,),{'raw':'','html':'','_repr_html_': lambda self=None: _alert})() # create an empty object
    get_ipython().user_ns['__current_source_code__'] = return_obj # add to user namespace, this does not create extra object, just points to same
    try:
        yield return_obj
    finally:
        file, l2 = frame()
        lines = linecache.getlines(file)[l1:l2]
    
        code = textwrap.dedent(''.join(lines))
        return_obj.raw = code
        out_code = _fix_code(markdown("```python\n{}\n```".format(code),extensions=__md_extensions))
        if collapsed:
            return_obj._repr_html_ = lambda self = None: details(out_code,summary='Show Code')
        else:
            return_obj._repr_html_ = lambda self = None: out_code
            
        return_obj.html = return_obj._repr_html_()
            
def sig(callable,prepend_str = None):
    "Returns signature of a callable. You can prepend a class/module name."
    try:
        _sig = f'<b>{callable.__name__}</b><span style="font-size:85%;color:var(--secondary-fg);">{str(inspect.signature(callable))}</span>'
        if prepend_str: 
            _sig = alert(prepend_str + '.') + _sig
        return {'__keep_format__':_sig}
    except:
        raise TypeError(f'Object {callable} is not a callable')

def doc(callable,prepend_str = None):
    "Returns documentation of a callable. You can prepend a class/module name."
    try:
        _doc = _fix_repr(inspect.getdoc(callable))
        _sig = sig(callable,prepend_str)['__keep_format__']
        return {'__keep_format__':f"<div class='PyRepr'>{_sig}<br>{_doc}</div>"}
    except:
        raise TypeError(f'Object {callable} is not a callable')
