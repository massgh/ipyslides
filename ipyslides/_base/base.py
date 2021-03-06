"Inherit LiveSlides class from here. It adds useful attributes and methods."
import os, re, textwrap
from .widgets import Widgets
from .screenshot import ScreenShot
from .navigation import Navigation
from .settings import LayoutSettings
from .notes import Notes
from .export_html import _HhtmlExporter

class BaseLiveSlides:
    def __init__(self):
        self.__widgets = Widgets()
        self.__screenshot = ScreenShot(self.__widgets)
        self.__navigation = Navigation(self.__widgets) # Not accessed later, just for actions
        self.__settings = LayoutSettings(self.__widgets)
        self.__export = _HhtmlExporter(self)
        self.__notes = Notes(self, self.__widgets) # Needs main class for access to notes
        
        self.toast_html = self.widgets.htmls.toast
        
        self.widgets.checks.toast.observe(self.__toggle_notify,names=['value'])
    
    @property
    def notes(self):
        return self.__notes
    
    @property
    def widgets(self):
        return self.__widgets
    
    @property
    def export(self):
        return self.__export
    
    @property
    def screenshot(self):
        return self.__screenshot
    
    @property
    def settings(self):
        return self.__settings
    
    def notify(self,content,title='IPySlides Notification',timeout=5):
        "Send inside notifications for user to know whats happened on some button click. Set `title = None` if need only content. Remain invisible in screenshot."
        return self.widgets._push_toast(content,title=title,timeout=timeout)
    
    def __toggle_notify(self,change):
        "Blocks notifications."
        if self.widgets.checks.toast.value:
            self.toast_html.layout.visibility = 'hidden' 
        else:
            self.toast_html.layout.visibility = 'visible'
    
    @property
    def css_styles(self):
        """CSS styles for write(..., className = style)."""
        # self.html will be added from Chid class
        return self.html('div', '''Use any or combinations of these styles in className argument of writing functions:
        className = 'Center'            ------Text------
        className = 'Left'              Text------------
        className = 'Right'             ------------Text
        className = 'RTL'               ------ ???????? ???????? 
        className = 'Info'              Blue Text
        className = 'Warning'           Orange Text
        className = 'Success'           Green Text
        className = 'Error'             Red Text
        className = 'Note'              Text with info icon
        className = 'slides-only'       Text will not appear in exported html with `build_report`
        className = 'report-only'       Text will not appear on slides. Useful to fill content in report.
        className = 'Block'             Block of text/objects
        className = 'Block-[color]'      Block of text/objects with specific background color from red, green, blue, yellow, cyan, magenta and gray.
        ''',className= 'PyRepr')
        
    def get_source(self, title = 'Source Code'):
        "Return source code of all slides created using `from_markdown` or `%%slide`."
        sources = []
        for slide in self[:]:
            if slide._from_cell and slide._markdown:
                sources.append(slide._get_source(name=f'Markdown: Slide {slide.label}'))
            elif slide._from_cell and slide._cell_code:
                sources.append(slide._get_source(name=f'Python: Slide {slide.label}'))
        
        if sources:
            return self.keep_format(f'<h2>{title}</h2>' + '\n'.join(s.value for s in sources))
        else:
            self.html('p', 'No source code found.', className='Info')

    
    def notify_later(self, title='IPySlides Notification', timeout=5):
        """Decorator to push notification at slide under which it is run. 
        It should return a string that will be content of notifictaion.
        The content is dynamically generated by underlying function, 
        so you can set timer as well. Remains invisible in screenshot through app itself.
        ```python
        @notify_at(title='Notification Title', timeout=5)
        def push_notification():
            time = datetime.now()
            return f'Notification at {time}'
        ```
        """
        def _notify(func): 
            self._slides_dict[f'{self._current_slide}']._toast = dict(func = func, kwargs = dict(title=title, timeout=timeout))
        return _notify
        
    def clear_toasts(self):
        "Remove all toast notifications that show up with any slide."
        for s in self._slides_dict.values():
            s.toast = None
    
    @property
    def toasts(self):
        "Get all toast notifications attached to slides."
        return tuple([{'slide_key': s.label, 'slide_index': s._index, 'slide_toast': s.toast} for s in self._slides_dict.values() if s.toast])
    
    def _display_toast(self):
        toast = self._slides_dict[self._access_key].toast #_access_key is current slide's number from LiveSlides
        if toast:
            # clear previous content of notification as new one is about to be shown, this will ensure not to see on wrong slide
            self.widgets.htmls.toast.value = ''
            self.notify(content = toast['func'](), **toast['kwargs'])
    
    def from_markdown(self, start, file_or_str, trusted = False):
        """You can create slides from a markdown file or tex block as well. It creates slides start + (0,1,2,3...) in order.
        You should add more slides by higher number than the number of slides in the file/text, or it will overwrite.
        Slides separator should be --- (three dashes) in start of line.
        Frames separator should be ___ (three underscores) in start of line. All markdown before first ___ will be written on all frames.
        **Markdown Content**
        ```markdown
        # Talk Title
        ---
        # Slide 1 
        || Inline - Column A || Inline - Column B ||
        {{some_var}} that will be replaced by it's html value.
         ```python run source
         from ipyslides import parsers as prs # import parser functions from this module (1.5.6+)
         # code here will be executed and it's output will be shown in slide.
         ```
         {{source}} from above code block will be replaced by it's html value.
        ---
        # Slide 2
        ___
        ## First Frame
         ```multicol 40 60
        # Block column 1
        +++
        # Block column 2
        || Mini - Column A || Mini - Column B ||
         ```
        ___
        ## Second Frame
        ```
        This will create two slides along with title page if start = 0. Second slide will have two frames.
        
        Markdown content of each slide is stored as .markdown attribute to slide. You can append content to it like this:
        ```python
        with slides.slide(2):
            self.parse_xmd(slides[2].markdown) # Instead of write, parse_xmd take cares of code blocks
            plot_something()
            write_something()
        ```
        Starting from version 1.6.2, only those slides will be updated whose content is changed from last run of this function. This increases speed.
        
        **New in 1.7.2**:     
        - You can add slides from text blocks/file with a start number. 
        - It will create slides at numbers `start, start + 1, .... start + N+1` if there are `N` `---` (three dashes) separators in the text.
        - Find special syntax to be used in markdown by `LiveSlides.xmd_syntax`.
        
        **Returns**:       
        A tuple of handles to slides created. These handles can be used to access slides and set properties on them.
        """
        if self.shell is None or self.shell.__class__.__name__ == 'TerminalInteractiveShell':
            raise Exception('Python/IPython REPL cannot show slides. Use IPython notebook instead.')
        
        if not isinstance(file_or_str, str): #check path later or it will throw error
            raise ValueError(f"file_or_str expects a makrdown file path(str) or text block, got {file_or_str!r}")
        
        if not trusted:
            try: # Try becuase long string will through error for path
                os.path.isfile(file_or_str) # check if file exists then check code blocks
                with open(file_or_str, 'r') as f:
                    lines = f.readlines()
            except:
                lines = file_or_str.splitlines()
                    
            untrusted_lines = []
            for i, line in enumerate(lines, start = 1):
                if re.match(r'```python\s+run', line):
                    untrusted_lines.append(i)
            
            if untrusted_lines:
                raise Exception(f'Given file/text may contain unsafe code to be executed at lines: {untrusted_lines}'
                    ' Verify code is safe and try again with argument `trusted = True`.'
                    ' Never run files that you did not create yourself or not verified by you.')
        
        try:
            if os.path.isfile(file_or_str):
                with open(file_or_str, 'r') as f:
                    chunks = _parse_markdown_text(f.read())
            elif file_or_str.endswith('.md'): # File but does not exits
                raise FileNotFoundError(f'File {file_or_str} does not exist.')
            else:
                chunks = _parse_markdown_text(file_or_str)
        except:
            chunks = _parse_markdown_text(file_or_str)
        
        for i,chunk in enumerate(chunks, start = start):
            # Must run under this to create frames with triple underscore (___)
            self.shell.run_cell_magic('slide', f'{i} -m', chunk)
        
        # Return refrence to slides for quick update
        handles = [[self._slides_dict[key] for key in self._slides_dict.keys() if key.startswith(f'{i}')] for i in range(start, start + len(chunks))]
        return tuple([h for handle in handles for h in handle]) # flatten list of lists
    
    
    def demo(self):
        """Demo slides with a variety of content."""
        self.close_view() # Close any previous view to speed up loading 10x faster on average
        self.clear() # Clear previous content
        
        import runpy
        file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_demo.py') # Relative path to this file
        slides = runpy.run_path(file, init_globals= {'slides': self})['slides']
        
        N = len(slides)
        with slides.slide(N + 1):
            slides.write('## This is all code to generate slides')
            slides.write(self.demo)
            slides.source.from_file(file).display()
            
        with slides.slide(N + 2):
            slides.write('Slides made by using `from_markdown` or `%%slide` magic preserve their full code\n{.Note .Info}')
            slides.get_source().display()
            
        with slides.slide(N + 3, props_dict = {'': dict(background='#9ACD32')}):
            with slides.source.context() as s:
                slides.write_citations()
            s.display()
        
        # Just for func, set theme of all even slides to be fancy, and zoom animation
        fancy_even_slides_css = {       
            '--heading-fg': '#105599',
	        '--primary-fg': '#755',
	        '--primary-bg': '#efefef',
	        '--secondary-bg': '#effffe',
	        '--secondary-fg': '#89E',
	        '--tr-odd-bg': '#deddde',
	        '--tr-hover-bg': '#D1D9E1',
	        '--accent-color': '#955200',
            '--pointer-color': '#FF7722'
        }   
        
        for s in slides[::2]: 
            s.set_css({'slide': fancy_even_slides_css})
            s.set_animation('zoom')
        
        slides._slideindex = 0 # Go to title
        return slides
    
    def load_docs(self):
        "Create presentation from docs of IPySlides."
        self.close_view() # Close any previous view to speed up loading 10x faster on average
        self.clear() # Clear previous content
        
        from ..core import LiveSlides
        from ..__version__ import __version__
        
        self.settings.set_footer('IPySlides Documentation')
        
        with self.title(): # Title
            self.write(f'## IPySlides {__version__} Documentation\n### Creating slides with IPySlides')
            self.write(self.doc(LiveSlides))
        
        with self.slide(1):
            self.write('## Adding Slides')
            self.write('Besides functions below, you can add slides with `%%title`,  `%%slide <slide number>` and `%%slide <slide number>` -m`,`%%slide <slide number> -s` magics as well.\n{.Note .Info}')
            self.write([self.doc(self.title,'LiveSlides'),self.doc(self.slide,'LiveSlides'),self.doc(self.frames,'LiveSlides'),self.doc(self.from_markdown,'LiveSlides')])
        
        with self.slide(2):
            self.write('## Adding Content')
            self.write('Besides functions below, you can add content to slides with `%%xmd`,`%xmd`, `display(obj)` as well.\n{.Note .Info}')
            self.xmd_syntax.display() # This will display information about Markdown extended syntax
            self.write([self.doc(self.write,'LiveSlides'),self.doc(self.iwrite,'LiveSlides'), self.doc(self.parse_xmd,'LiveSlides'),self.doc(self.cite,'LiveSlides')])
        
        with self.slide(3):
            self.write('## Adding Speaker Notes')
            self.write('You can use line magic `%notes` to add notes as well.\n{.Note .Success}')
            self.doc(self.notes,'LiveSlides.notes', members = True, itself = False).display()
                   
        with self.slide(4):
            self.write('## Displaying Source Code')
            self.doc(self.source,'LiveSlides.source', members = True, itself = False).display()
        
        with self.slide(5):
            self.write('## Layout and Theme Settings')
            self.doc(self.settings,'LiveSlides.settings', members=True,itself = False).display()
                
        with self.slide(6):
            self.write('## Useful Functions for Rich Content')
            members = ['alert','block', 'bokeh2html', 'capture_std', 'citations_html', 'cite',
                       'colored', 'cols', 'details', 'doc', 'enable_zoom', 'format_css', 'format_html', 'highlight',
                       'html', 'iframe', 'image', 'keep_format', 'notify', 'notify_later', 'plt2html', 'raw', 'rows',
                       'set_dir', 'sig', 'svg', 'textbox', 'vspace', 'write_citations', 'set_slide_css']
            self.doc(self, 'LiveSlides', members = members, itself = False).display()
            
        with self.slide(7):
            self.write('## Content Styling')
            with self.source.context() as c:
                self.write(('You can **style**{.Error} your *content*{: style="color:hotpink;"} with `className` attribute in writing/content functions. ' 
                       'Provide **CSS**{.Info} for that using `.format_css` or use some of the available styles. '
                       'See these **styles**{.Success} with `.css_styles` property as below:'))
                self.css_styles.display()
                c.display()
        
        s8, = self.from_markdown(8, '''
        ## Highlighting Code
        You can **highlight**{.Error} code using `highlight` function or within markdown like this:
        ```python
        import ipyslides as isd
        ```
        ```javascript
        import React, { Component } from "react";
        ```
        ''', trusted= True)
        
        # Update with source of slide
        with s8.insert(-1): # Insert source code
            self.write('<hr/>This slide was created with `from_markdown` function. '
                'So its source code can be inserted in the slide later! '
                'See at last slide how it was done!<hr/>')
            s8.source.display()
        
        with self.slide(9):
            self.write('## Loading from File/Exporting to HTML')
            self.write('You can parse and view a markdown file w. The output you can save by exporting notebook in other formats.\n{.Note .Info}')
            self.write([self.doc(self.from_markdown,'LiveSlides'),
                        self.doc(self.demo,'LiveSlides'), 
                        self.doc(self.load_docs,'LiveSlides'),
                        self.doc(self.export.slides,'LiveSlides.export'),
                        self.doc(self.export.report,'LiveSlides.export')])
        
        with self.slide(10):
            self.write('## Adding User defined Objects/Markdown Extensions')
            self.write('If you need to serialize your own or third party objects not serialized by this module, you can use `@LiveSlides.serializer.register` to serialize them to html.\n{.Note .Info}')
            self.doc(self.serializer,'LiveSlides.serializer', members = True, itself = False).display()
            self.write('**You can also extend markdown syntax** using `markdown extensions`, ([See here](https://python-markdown.github.io/extensions/) and others to install, then use as below):')
            self.doc(self.extender,'LiveSlides.extender', members = True, itself = False).display()
        
        with self.slide(11):
            self.write(['## Presentation Code',self.load_docs])
        
        self._slideindex = 0 # Go to title
        return self


def _parse_markdown_text(text_block):
    "Parses a Markdown text block and returns text for title and each slide."
    lines = textwrap.dedent(text_block).splitlines() # Remove overall indentation
    breaks = [-1] # start, will add +1 next
    for i,line in enumerate(lines):
        if line and line.strip() =='---':
            breaks.append(i)
    breaks.append(len(lines)) # Last one
    
    ranges = [range(j+1,k) for j,k in zip(breaks[:-1],breaks[1:])]
    return ['\n'.join(lines[x.start:x.stop]) for x in ranges]
        