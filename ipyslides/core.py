import sys, re
from contextlib import contextmanager, suppress

from IPython import get_ipython
from IPython.display import display
import ipywidgets as ipw

from .extended_md import parse_xmd, _allowed_funcs
from .source import Source
from .writers import write, iwrite
from .formatter import bokeh2html, plt2html, highlight, _HTML, serializer
from . import utils

_under_slides = {k:getattr(utils,k,None) for k in utils.__all__}

from ._base.base import BaseLiveSlides
from ._base.intro import how_to_slide, logo_svg
from ._base.scripts import multi_slides_alert
from ._base.slide import build_slide
from ._base import styles

try:  # Handle python IDLE etc.
    SHELL = get_ipython()
except:
    print("Slides only work in IPython Notebook!")
    sys.exit()
    

class _Citation:
    "Add citation to the slide with a unique key and value. New in 1.7.0"
    def __init__(self, slide, key, value):
        self._slide = slide
        self._key = key
        self._value = value
        self._id = '?'
        
    def __repr__(self):
        return f"Citation(key = {self._key!r}, value = {self._value!r}, id = {self._id!r}, slide_key = {self._slide.label!r})"
    
    @property
    def html(self):
        "HTML of this citation"
        value = parse_xmd(self._value if self._value else f"Set self[{self._slide.label!r}].citations[{self._key!r}].value = 'citation value'",
                        display_inline=False, rich_outputs = False).replace('<p>','',1)[::-1].replace('</p>','',1)[::-1] # Only replace first <p>
        
        return _HTML(f'''<span class = "citation" id="{self._key}">
            <a href="#{self._key}-back">
                <sup style="color:var(--accent-color);">{self._id}</sup>
            </a>{value}</span>''')
        
    @property
    def value(self):
        "Value of citation"
        return self._value
    
    @value.setter
    def value(self, value):
        "Set value of citation as text/html/markdown"
        self._value = value
    
        
class LiveSlides(BaseLiveSlides):
    # This will be overwritten after creating a single object below!
    __name__ = 'ipyslides.core.LiveSlides' # Used to validate code in markdown, must
    def __init__(self):
        super().__init__() # start Base class in start
        self.shell = SHELL
        
        for k,v in _under_slides.items(): # Make All methods available in slides
            setattr(self,k,v)
            
        self.plt2html   = plt2html
        self.bokeh2html = bokeh2html
        self.highlight  = highlight
        self.source = Source # Code source
        self.write  = write # Write IPython objects in slides
        self.iwrite = iwrite # Write Widgets/IPython in slides
        self.parse_xmd = parse_xmd # Parse extended markdown
        self.serializer = serializer # Serialize IPython objects to HTML
        
        with suppress(Exception): # Avoid error when using setuptools to install
            self.shell.register_magic_function(self.__slide, magic_kind='cell',magic_name='slide')
            self.shell.register_magic_function(self.__title, magic_kind='cell',magic_name='title')
            self.shell.register_magic_function(self.notes.insert, magic_kind='line',magic_name='notes')
            self.shell.register_magic_function(self.__xmd, magic_kind='line_cell',magic_name='xmd')
            self.user_ns = self.shell.user_ns #important for set_dir
            
            # Override print function to display in order in slides
            def pprint(*args, **kwargs):
                "Displays object(s) inline with others in corrct order. args and kwargs are passed to builtin print."
                with self.capture_std() as std:
                    print(*args, **kwargs)
                std.stdout.display() # Display at the end
            
            self.shell.user_ns['pprint'] = pprint
        
        self._citations_per_slide = False # If citations are per slide or just once       
        self._slides_dict = {} # Initialize slide dictionary, updated by user or by _on_displayed.
        self._current_slide = '0' # Initialize current slide for notes at title page
        self._reverse_mapping = {'0':'0'} # display number -> input number of slide
        
        self._iterable = [] #self._collect_slides() # Collect internally
        self._nslides =  0 # Real number of slides
        self._max_index = 0 # Maximum index including frames
        
        self.progress_slider = self.widgets.sliders.progress
        self.progress_slider.label = '0' # Set inital value, otherwise it does not capture screenshot if title only
        self.progress_slider.observe(self._update_content,names=['index'])
        self.markdown_callables = tuple(_allowed_funcs.split('|'))
        # All Box of Slides
        self._box =  self.widgets.mainbox
        self._box.on_displayed(self._on_displayed) 
        self._display_box_ = ipw.VBox() # Initialize display box

    
    def _on_displayed(self, change):
        self.widgets._exec_js(multi_slides_alert)
        
        with build_slide(self, '0'):
            self.parse_xmd('\n'.join(how_to_slide), display_inline=True)
        
        with suppress(Exception): # Does not work everywhere.
            self.widgets.inputs.bbox.value = ', '.join(str(a) for a in self.screenshot.screen_bbox) # Useful for knowing scren size
    
    def __iter__(self): # This is must have for exporting
        return iter(self._iterable)
    
    def __getitem__(self, key):
        "Get slide by index or key(written on slide's bottom)."
        if isinstance(key, int):
            return self._iterable[key]
        elif isinstance(key, str) and key in self._reverse_mapping:
            return self._slides_dict[self._reverse_mapping[key]]
        elif isinstance(key, slice):
            return self._iterable[key.start:key.stop:key.step]
        
        raise KeyError("Slide could be accessed by index, slice or key, got {}".format(key))
    
    @property
    def current(self):
        "Access current visible slide and use operations like insert, set_css etc."
        return self._slides_dict[self._access_key]
    
    @property
    def citations(self):
        "Get All citations."
        return tuple([citation for slide in self[:] for citation in slide.citations.values()])
    
    @property
    def _access_key(self):
        "Access key for slides number to get other things like notes, toasts, etc."
        return self._reverse_mapping.get(self._slidelabel, '') # being on safe, give '' as default

    def clear(self):
        "Clear all slides."
        self._slides_dict = {} # Clear slides
        self.refresh() # Clear interface too
    
    def cite(self,key, citation = None,here = False):
        "Add citation in presentation, key should be a unique string and citation is text/markdown/HTML."
        if here:
            return utils.textbox(citation,left='initial',top='initial') # Just write here
        
        current_slide = self._slides_dict[self._current_slide] # Get current slide, may not be refreshed yet
        _cited = _Citation(slide = current_slide, key = key, 
            value = (citation or current_slide.citations.get(key, None)))
        current_slide._citations[key] = _cited
        
        # Set _id for citation
        if self._citations_per_slide:
            _cited._id = str(list(current_slide.citations.keys()).index(key) + 1) # Get index of key
        else:
            # Find slides created till now
            if current_slide.index: # If index is set
                prev_index = 0 # Start from 0
                for slide in self[:current_slide.index]:
                    prev_index += len(slide.citations)
                    
                _cited._id = str(prev_index + list(current_slide.citations.keys()).index(key) + 1)
                    
            else: # If index is not set, just use key
                _cited._id = key
             
        # Return string otherwise will be on different place
        return f'<a href="#{key}"><sup id ="{key}-back" style="color:var(--accent-color);">{_cited._id}</sup></a>'
    
    def citations_html(self,title='### References'): 
        "Write all citations collected via `cite` method in the end of the presentation."    
        if self._citations_per_slide:
            raise ValueError("Citations are consumed per slide.\n" 
                             "If you want to display them in the end, "
                             "use `citations_per_slide = False` during initialization of `LiveSlides`.")
            
        _html = _HTML(self.parse_xmd(title + '\n',display_inline=False, rich_outputs = False))
        
        for citation in self.citations:
            _html = _html + citation.html
        
        return _html
        
    def write_citations(self,title='### References'):
        "Write all citations collected via `cite` method in the end of the presentation."
        return self.citations_html(title = title).display()
        
    def show(self, fix_buttons = False): 
        "Display Slides. If icons do not show, try with `fix_buttons=True`."
        
        if fix_buttons:
            self.widgets.buttons.next.description = '▶'
            self.widgets.buttons.prev.description = '◀'
            self.widgets.buttons.prev.icon = ''
            self.widgets.buttons.next.icon = ''
        else: # Important as showing again with False will not update buttons. 
            self.widgets.buttons.next.description = ''
            self.widgets.buttons.prev.description = ''
            self.widgets.buttons.prev.icon = 'chevron-left'
            self.widgets.buttons.next.icon = 'chevron-right'
        
        return self._ipython_display_()
    
    def _ipython_display_(self):
        'Auto display when self is on last line of a cell'
        if self.shell is None or self.shell.__class__.__name__ == 'TerminalInteractiveShell':
            raise Exception('Python/IPython REPL cannot show slides. Use IPython notebook instead.')
        
        self.close_view() # Close previous views
        self._display_box_ = ipw.VBox(children=[self.__jlab_in_cell_display(), self._box]) # Initialize display box again
        return display(self._display_box_)
    
    def close_view(self):
        "Close all slides views, but keep slides in memory than can be shown again."
        self._display_box_.close() 
    
    def __jlab_in_cell_display(self): 
        # Can test Voila here too
        try: # SHould try, so error should not block it
            if 'voila' in self.shell.config['IPKernelApp']['connection_file']:
                self.widgets.sliders.width.value = 100 # This fixes dynamic breakpoint in Voila
        except: pass # Do Nothing
         
        return ipw.VBox([
                    ipw.HTML("""<b style='color:var(--accent-color);font-size:24px;'>IPySlides</b>"""),
                    self.widgets.toggles.timer,
                    self.widgets.htmls.notes
                ]).add_class('ExtraControls')
    @property
    def _frameno(self):
        "Get current frame number, return 0 if not in frames in slide"
        if '.' in self._slidelabel:
            return int(self._slidelabel.split('.')[-1])
        return 0
    
    @property
    def _slideindex(self):
        "Get current slide index"
        return self.progress_slider.index
    
    @_slideindex.setter
    def _slideindex(self,value):
        "Set current slide index"
        with suppress(BaseException): # May not be ready yet
            self.progress_slider.index = value
        
    @property
    def _slidelabel(self):
        "Get current slide label"
        return self.progress_slider.label
    
    @_slidelabel.setter
    def _slidelabel(self,value):
        "Set current slide label"
        with suppress(BaseException): # May not be ready yet
            self.progress_slider.label = value
            
    def _switch_slide(self,old_index, new_index): # this change is provide from _update_content
        self.widgets.outputs.slide.clear_output(wait=False) # Clear last slide CSS
        with self.widgets.outputs.slide:
            if self.screenshot.capturing == False:
                self._iterable[new_index].animation.display()
            self._iterable[new_index].css.display()
        
        if (old_index + 1) > len(self.widgets.slidebox.children):
            old_index = new_index # Just safe
            
        self.widgets.slidebox.children[old_index].layout = ipw.Layout(width = '0',margin='0',opacity='0') # Hide old slide
        self.widgets.slidebox.children[old_index].remove_class('SlideArea')
        self.widgets.slidebox.children[new_index].add_class('SlideArea') # First show then set layout
        self.widgets.slidebox.children[new_index].layout = self.settings._slide_layout 
        
    def _update_content(self,change):
        if self._iterable and change:
            self.widgets.htmls.toast.value = '' # clear previous content of notification 
            self._display_toast() # or self.toasts._display_toast . Display in start is fine
            self.notes._display(self._slides_dict.get(self._access_key,None).notes) # Display notes first
        
            n = self._iterable[self._slideindex].position if self._iterable else 0 # keep it from slides
            _number = f'{n} / {self._nslides}' if n != 0 else ''
            self.settings.set_footer(_number_str = _number)
            
            self._switch_slide(old_index= change['old'], new_index= change['new']) 
    
            
    def refresh(self): 
        "Auto Refresh whenever you create new slide or you can force refresh it"
        self._iterable = self._collect_slides() # would be at least one title slide
        if not self._iterable:
            self.progress_slider.options = [('0',0)] # Clear options
            self.widgets.slidebox.children = [] # Clear older slides
            return None
        
        n_last = self._iterable[-1].position
        self._nslides = int(n_last) # Avoid frames number
        self._max_index = len(self._iterable) - 1 # This includes all frames
        self.notify('Refreshing display of slides...')
        # Now update progress bar
        opts = [(f"{s.position}", round(100*float(s.position)/(n_last or 1), 2)) for s in self._iterable]
        self.progress_slider.options = opts  # update options
        # Update Slides
        #slides = [ipw.Output(layout=ipw.Layout(width = '0',margin='0')) for s in self._iterable]
        self.widgets.slidebox.children = [it._widget for it in self._iterable]
        for i, s in enumerate(self._iterable):
            s.update_display() 
            s._index = i # Update index
            self._slideindex = i # goto there to update display
        
        self._slideindex = 0 # goto first slide after refresh
            
        
    def set_slide_css(self,props_dict = {}):
        """props_dict is a dict of css properties in format {'selector': {'prop':'value',...},...}
        'selector' for slide itself should be ''.
        """
        self._slides_dict[self._current_slide].set_css(props_dict)
    
    def set_overall_animation(self, main = 'slide_h',frame = 'slide_v'):
        "Set animation for main and frame slides for all slides. For individual slides, use `self[index or key].set_animation/self.current.set_animation`"
        self._slides_dict[self._current_slide].set_overall_animation(main = main, frame = frame)
    
    # defining magics and context managers
    def __slide(self,line,cell):
        """Capture content of a cell as `slide`.
            ---------------- Cell ----------------
            %%slide 1                             
            #python code here                     
        
        You can use extended markdown to create slides
            ---------------- Cell ----------------
            %%slide 2 -m
            Everything here and below is treated as markdown, not python code.
            (1.5.5+) If Markdown is separated by three underscores (___) on it's own line, multiple frames are created.
            Markdown before the first three underscores is written on all frames. This is equivalent to `@LiveSlides.frames` decorator.
        """
        line = line.strip().split() #VSCode bug to inclue \r in line
        if line and not line[0].isnumeric():
            raise ValueError(f'You should use %%slide integer >= 1 -m(optional), got {line}')
        
        slide_number = int(line[0])
        
        if '-m' in line[1:]:
            _frames = re.split(r'^___$|^___\s+$',cell,flags = re.MULTILINE) # Split on --- or ---\s+
            if len(_frames) == 1:
                if (line[0] in self._slides_dict) and (self._slides_dict[line[0]]._markdown == cell):
                    pass # Do nothing if already exists
                else:
                    with self.slide(slide_number):
                        parse_xmd(cell, display_inline = True, rich_outputs = False)
                
                self._slides_dict[line[0]]._markdown = cell # Update markdown
                
            else:
                for i, obj in enumerate(_frames[1:], start = 1):
                    key = f'{slide_number}.{i}'
                    if (key in self._slides_dict) and (self._slides_dict[key]._markdown == (_frames[0] + obj)):
                        pass # Do nothing if already exists
                    else:
                        with build_slide(self, key):
                            parse_xmd(_frames[0], display_inline = True, rich_outputs = False) # This goes with every frame
                            parse_xmd(obj, display_inline = True, rich_outputs = False)
                    
                    self._slides_dict[key]._markdown = (_frames[0] + obj) # Update markdown      
                    
        else:
            if (line[0] in self._slides_dict) and hasattr(self._slides_dict[line[0]], '_cell_code'):
                if self._slides_dict[line[0]]._cell_code == cell:
                    pass # do nothing
                else:
                    with self.slide(slide_number):
                        self.shell.run_cell(cell)
            else:
                with self.slide(slide_number):
                    self.shell.run_cell(cell)
                    
            self._slides_dict[line[0]]._cell_code = cell # Update code for faster run later
            
    
    @contextmanager
    def slide(self,slide_number,props_dict = {}):
        """Use this context manager to generate any number of slides from a cell
        CSS properties from `props_dict` are applied to current slide."""
        if not isinstance(slide_number, int):
            raise ValueError(f'slide_number should be int >= 1, got {slide_number}')
        
        assert slide_number >= 0 # slides should be >= 1, zero for title slide
        
        self._current_slide = f'{slide_number}'
        
        with build_slide(self, self._current_slide, props_dict=props_dict) as cap:
            yield cap # Useful to use later

    
    def __title(self,line,cell):
        "Turns to cell magic `title` to capture title"
        with self.slide(0):
            if '-m' in line:
                parse_xmd(cell, display_inline = True, rich_outputs = False)
            else:
                self.shell.run_cell(cell)
    
    def __xmd(self, line, cell = None):
        """Turns to cell magics `%%xmd` and line magic `%xmd` to display extended markdown. 
        Can use in place of `write` commnad for strings.
        When using `%xmd`, variables should be `{{{{var}}}}` or `\{\{var\}\}`, not `{{var}}` as IPython 
        does some formatting to line in magic. If you just need to format it in string, then `{var}` works as well.
        Inline columns are supported with ||C1||C2|| syntax."""
        if cell is None:
            return parse_xmd(line, display_inline = True, rich_outputs = False)
        else:
            return parse_xmd(cell, display_inline = True, rich_outputs = False)
            
    @contextmanager
    def title(self,props_dict = {}):
        """Use this context manager to write title.
        CSS properties from `props_dict` are applied to current slide."""
        with self.slide(0, props_dict = props_dict) as s:
            yield s # Useful to use later
    
    def frames(self, slide_number, *objs, repeat = False, frame_height = 'auto', props_dict = {}):
        """Decorator for inserting frames on slide, define a function with one argument acting on each obj in objs.
        You can also call it as a function, e.g. `.frames(slide_number = 1,1,2,3,4,5)()` becuase required function is `write` by defualt.
        
        ```python
        @slides.frames(1,a,b,c) # slides 1.1, 1.2, 1.3 with content a,b,c
        def f(obj):
            do_something(obj)
            
        slides.frames(1,a,b,c)() # Auto writes the frames with same content as above
        slides.frames(1,a,b,c, repeat = True)() # content is [a], [a,b], [a,b,c] from top to bottom
        slides.frames(1,a,b,c, repeat = [(0,1),(1,2)])() # two frames with content [a,b] and [b,c]
        ```
        
        **Parameters**
        
        - slide_number: (int) slide number to insert frames on. 
        - objs: expanded by * (list, tuple) of objects to write on frames. If repeat is False, only one frame is generated for each obj.
        - repeat: (bool, list, tuple) If False, only one frame is generated for each obj.
            If True, one frame are generated in sequence of ojects linke `[a,b,c]` will generate 3 frames with [a], [a,b], [a,b,c] to given in function and will be written top to bottom. 
            If list or tuple, it will be used as the sequence of frames to generate and number of frames = len(repeat).
            [(0,1),(1,2)] will generate 2 frames with [a,b] and [b,c] to given in function and will be written top to bottom or the way you write in your function.
        - frame_height: ('N%', 'Npx', 'auto') height of the frame that keeps incoming frames object at static place.
        
        No return of defined function required, if any, only should be display/show etc.
        CSS properties from `prop_dict` are applied to all slides from *objs."""
        def _frames(func = self.write): # default write if called without function
            if not isinstance(slide_number,int):
                return print(f'slide_number expects integer, got {slide_number!r}')
            
            assert slide_number >= 1 # Should be >= 1, should not add title slide as frames

            if repeat == True:
                _new_objs = [objs[:i] for i in range(1,len(objs)+1)]
            elif isinstance(repeat,(list, tuple)):
                _new_objs =[]
                for k, seq in enumerate(repeat):
                    if not isinstance(seq,(list,tuple)):
                        raise TypeError(f'Expected list or tuple at index {k} of `repeat`, got {seq}')
                    _new_objs.append([objs[s] for s in seq])
            else:
                _new_objs = objs
                    
            for i, obj in enumerate(_new_objs,start=1):
                self._current_slide = f'{slide_number}.{i}' # Update current slide
                with build_slide(self, f'{slide_number}.{i}', props_dict= props_dict):
                    self.write(self.format_css('.SlideArea',height = frame_height))
                    func(obj) # call function with obj
            
        return _frames 

    def _collect_slides(self):
        """Collect cells for an instance of LiveSlides."""
        slides_iterable = []
        if '0' in self._slides_dict:
            self._slides_dict['0'].position = 0
            slides_iterable = [self._slides_dict['0']]
        
        val_keys = sorted([int(k) if k.isnumeric() else float(k) for k in self._slides_dict.keys()]) 
        str_keys = [str(k) for k in val_keys]
        _max_range = int(val_keys[-1]) + 1 if val_keys else 1
        
        nslide = 0 #start of slides - 1
        for i in range(1, _max_range):
            if i in val_keys:
                nslide = nslide + 1 #should be added before slide
                self._slides_dict[f'{i}'].position = nslide
                slides_iterable.append(self._slides_dict[f'{i}']) 
                self._reverse_mapping[str(nslide)] = str(i)
            
            n_ij, nframe = '{}.{}', 1
            while n_ij.format(i,nframe) in str_keys:
                nslide = nslide + 1 if nframe == 1 else nslide
                _in, _out = n_ij.format(i,nframe), n_ij.format(nslide,nframe)
                self._slides_dict[_in].position = float(_out)
                slides_iterable.append(self._slides_dict[_in]) 
                self._reverse_mapping[_out] = _in
                nframe = nframe + 1
            
        return tuple(slides_iterable)

# Make available as Singleton LiveSlides
_private_instance = LiveSlides() # Singleton in use namespace
# This is overwritten below to just have a singleton

class LiveSlides:
    """Interactive Slides in IPython Notebook. Only one instance can exist. 
    
    **Example**
    ```python 
    import ipyslides as isd 
    ls = isd.LiveSlides(citations_per_slide = True) # Citations will show up on bottom of each slide if any (New in 1.7.0)
    ls.demo() # Load demo slides
    ls.from_markdown(...) # Load slides from markdown files
    ```
    
    Instead of builtin `print` in slides use following to display printed content in correct order.
    ```python
    with ls.capture_std() as std:
        print('something')
        function_that_prints_something()
        display('Something') # Will be displayed here
        ls.write(std.stdout) # Will be written here whatever printed above this line
        
    std.stdout.display() #ls.write(std.stdout)
    ```
    In version 1.5.9+ function `pprint` is avalible in IPython namespace when LiveSlide is initialized. This displays objects in intended from rather than just text.
    > `ls.demo` and `ls.from_markdown`, `ls.load_docs` overwrite all previous slides.
    
    Aynthing with class name 'report-only' will not be displayed on slides, but appears in document when `ls.export.report` is called.
    This is useful to fill-in content in document that is not required in slides.
    
    > All arguments are passed to corresponding methods in `ls.settings`, so you can use those methods to change settings as well.
    
    ### Changes in version 1.7.0+
    
    - You can now show citations on bottom of each slide by setting `citations_per_slide = True` in `LiveSlides` constructor.
    - You can now access individual slides by indexing `ls[i]` where `i` is the slide index or by key as `ls['3.1'] will give you slide which shows 3.1 at bottom.
    - Basides indexing, you can access current displayed slide by `ls.current`.
    - You can add new content to existing slides by using `with ls[index].insert(where)` context. All new chnaged can be reverted by `ls[index].reset()`.
    - If a display is not complete, e.g. some widget missing on a slide, you can use `(ls.current, ls[index], ls[key]).update_display()` to update display.
    - You can set overall animation by `ls.set_overall_animation` or per slide by `ls[i].set_animation`
    - You can now set CSS for each slide by `ls[i].set_css` or `ls.set_slide_css` at current slide.
    - `ls.pre_compute_display` is deprecated and slides now are computed on-demand with each new slide.
    """
    def __new__(cls,
                citations_per_slide = False,
                center        = True, 
                content_width = '90%', 
                footer_text   = 'IPySlides | <a style="color:blue;" href="https://github.com/massgh/ipyslides">github-link</a>', 
                show_date     = True,
                show_slideno  = True,
                logo_src      = logo_svg, 
                font_scale    = 1, 
                text_font     = 'sans-serif', 
                code_font     = 'var(--jp-code-font-family)', 
                code_style    = 'default', 
                code_lineno   = True
                ):
        "Returns Same instance each time after applying given settings. Encapsulation."
        _private_instance.__doc__ = cls.__doc__ # copy docstring
        _private_instance._citations_per_slide = citations_per_slide
        _private_instance.settings.set_layout(center = center, content_width = content_width)
        _private_instance.settings.set_footer(text = footer_text, show_date = show_date, show_slideno = show_slideno)
        _private_instance.settings.set_logo(src = logo_src,width = 60)
        _private_instance.settings.set_font_scale(font_scale = font_scale)
        _private_instance.settings.set_font_family(text_font = text_font, code_font = code_font)
        _private_instance.settings.set_code_style(style = code_style, lineno = code_lineno)
        return _private_instance
    
    # No need to define __init__, __new__ is enough to show signature and docs
    
    
