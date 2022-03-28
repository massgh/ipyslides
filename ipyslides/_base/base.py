"Inherit LiveSlides class from here. It adds useful attributes and methods."
import os, io
from turtle import width
from IPython import get_ipython
from contextlib import suppress
from .widgets import Widgets
from .print_pdf import PdfPrint
from .navigation import Navigation
from .settings import LayoutSettings
from .notes import Notes
from .report_template import doc_html, doc_css

from ..formatter import code_css

class BaseLiveSlides:
    def __init__(self):
        "Both instnaces should be inside `_PrivateSlidesClass` class."
        # print(f'Inside: {self.__class__.__name__}')
        self.__widgets = Widgets()
        self.__print = PdfPrint(self.__widgets)
        self.__navigation = Navigation(self.__widgets) # Not accessed later, just for actions
        self.__settings = LayoutSettings(self.__widgets)
        self.notes = Notes(self, self.__widgets) # Needs main class for access to notes
        
        self._md_content = 'Slides not loaded from markdown.'
        
        self._toasts = {} #Store notifications
        self.toast_html = self.widgets.htmls.toast
        
        self.widgets.checks.toast.observe(self.__toggle_notify,names=['value'])
    
    @property
    def widgets(self):
        return self.__widgets
    
    @property
    def print(self):
        return self.__print
    
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
        print('Use any or combinations of these styles in className argument of writing functions:')
        print('''
        className = 'Center'            ------Text------
        className = 'Left'              Text------------
        className = 'Right'             ------------Text
        className = 'RTL'               ------ اردو عربی 
        className = 'Info'              Blue Text
        className = 'Warning'           Orange Text
        className = 'Success'           Green Text
        className = 'Error'             Red Text
        className = 'Note'              Text with info icon
        className = 'slides-only'       Text will not appear in exported html with `build_report`
        className = 'report-only'       Text will not appear on slides. Useful to fill content in report. 
        ''')

    
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
            self._toasts[f'{self._current_slide}'] = dict(func = func, kwargs = dict(title=title, timeout=timeout))
        return _notify
    
    def clear_notifications(self):
        "Remove all redundent notifications that show up."
        self._toasts = {} # Free up
    
    @property
    def notifications(self):
        "See all stored notifications."
        return self._toasts
    
    def _display_toast(self):
        toast = self._toasts.get(self._access_key,None) #_access_key is current slide's number from LiveSlides
        if toast:
            # clear previous content of notification as new one is about to be shown, this will ensure not to see on wrong slide
            self.widgets.htmls.toast.value = ''
            self.notify(content = toast['func'](), **toast['kwargs'])
    
    @property
    def md_content(self):
        "Get markdown content from loaded file."
        return self._md_content
        
    
    def from_markdown(self, path):
        """You can create slides from a markdown file or StringIO object as well. It creates slides 1,2,3... in order.
        You should add more slides by higher number than the number of slides in the file, or it will overwrite.
        Slides separator should be --- (three dashes) in start of line.
        **Markdown File Content**
        ```markdown
        # Talk Title
        ---
        # Slide 1 
        ---
        # Slide 2
        ```
        This will create two slides along with title page.
        
        Content of each slide from imported file is stored as list in `slides.md_content`. You can append content to it like this:
        ```python
        with slides.slide(2):
            self.parse_xmd(slides.md_content[2]) # Instead of write, parse_xmd take cares of code blocks
            plot_something()
            write_something()
        ```
        
        > Note: With this method you can add more slides besides created ones.
        """
        self._check_computed('add slides from markdown file')
        if not (isinstance(path, io.StringIO) or os.path.isfile(path)): #check path later or it will throw error
            raise ValueError(f"File {path!r} does not exist or not a io.StringIO object.")
        
        self.convert2slides(True)
        self.clear()
        
        if isinstance(path, io.StringIO):
            chunks = _parse_md_file(path)
        else:
            with open(path, 'r') as fp:
                chunks = _parse_md_file(fp)

        with self.title():
            self.parse_xmd(chunks[0], display_inline=True)
            
        for i,chunk in enumerate(chunks[1:],start=1):
            with self.slide(i):
                self.parse_xmd(chunk, display_inline=True)
            
        self._md_content = chunks # Store for later use
        
        return self
    
    def demo(self):
        """Demo slides with a variety of content."""
        self._check_computed('load demo')
        get_ipython().user_ns['_s_l_i_d_e_s_'] = self
        from .. import _demo
        slides = _demo.slides # or it is self
        with slides.slide(100):
            slides.write('## This is all code to generate slides')
            slides.write(_demo)
            slides.write(self.demo)
        with slides.slide(101,background='#9ACD32'):
            with slides.source.context() as s:
                slides.write_citations()
            slides.write(s)
        
        slides.progress_slider.index = 0 # back to title
        return slides
    
    def load_docs(self):
        "Create presentation from docs of IPySlides."
        self._check_computed('load docs')
        from ..core import LiveSlides
        
        self.clear()
        self.settings.set_footer('IPySlides Documentation')
        
        with self.title(): # Title
            self.write('## IPySlides Documentation\n### Creating slides with IPySlides')
            self.write(self.doc(LiveSlides))
        
        with self.slide(1):
            self.write('## Adding Slides')
            self.write('Besides functions below, you can add slides with `%%title`,  `%%slide <slide number>` and `%%slide <slide number>` -m` magics as well.\n{.Note .Info}')
            self.write([self.doc(self.title,'LiveSlides'),self.doc(self.slide,'LiveSlides'),self.doc(self.frames,'LiveSlides')])
        
        with self.slide(2):
            self.write('## Adding Content')
            self.write('Besides functions below, you can add content to slides with `display(obj)` as well.\n{.Note .Info}')
            self.write([self.doc(self.write,'LiveSlides'),self.doc(self.iwrite,'LiveSlides'), self.doc(self.parse_xmd,'LiveSlides')])
        
        with self.slide(3):
            self.write('## Adding Speaker Notes')
            for item in [getattr(self.notes,a) for a in dir(self.notes) if not a.startswith('_')]:
                with suppress(Exception):
                    self.write(self.doc(item,'LiveSlides.notes'))
                   
        with self.slide(4):
            self.write('## Displaying Source Code')
            for item in [getattr(self.source,a) for a in dir(self.source) if not a.startswith('_')]:
                with suppress(Exception):
                    self.write(self.doc(item,'LiveSlides.source'))
        
        with self.slide(5):
            self.write('## Layout and Theme Settings')
            for item in [getattr(self.settings,a) for a in dir(self.settings) if not a.startswith('_')]:
                with suppress(Exception):
                    self.write(self.doc(item,'LiveSlides.settings'))
                
        with self.slide(6):
            self.write('## Useful Functions for Rich Content')
            for attr in dir(self):
                if not attr.startswith('_'):
                    if not attr in ['write','iwrite','parse_xmd','source','notes','settings','title','slide','frames','css_styles','load_docs','demo','from_markdown']:
                        with suppress(Exception):
                            if not 'block_' in attr:
                                self.write(self.doc(getattr(self,attr),'LiveSlides'))
                        if attr == 'block':
                            self.write(f"`block` has other shortcut colored versions {', '.join(f'`block_{c}`' for c in 'rgbycmkowp')}.\n{{.Note .Info}}")
        
        with self.slide(7):
            self.write('## Content Styling')
            with self.source.context() as c:
                self.write(('You can **style**{.Error} your *content*{: style="color:hotpink;"} with `className` attribute in writing/content functions. ' 
                       'Provide **CSS**{.Info} for that using `.format_css` or use some of the available styles. '
                       'See these **styles**{.Success} with `.css_styles` property as below:'))
                self.iwrite(c)
                
            with self.print_context():
                self.css_styles # Auto prints css styles
        
        with self.slide(8):
            self.write('## Highlighting Code')
            with self.source.context() as s:
                self.write(('You can **highlight**{.Error} code using `highlight` function or within markdown like this: \n'
                        '```python\n'
                        'import ipyslides as isd\n```\n'
                        '```javascript\n'
                        'import React, { Component } from "react";\n```\n'))
                self.iwrite(s)
        
        with self.slide(9):
            self.write('## Loading from/to File/Other Contexts')
            self.write('You can parse and view a markdown file with `ipyslides.display_markdown` as well. The output you can save by exporting notebook in other formats.\n{.Note .Info}')
            self.write([self.doc(self.from_markdown,'LiveSlides'), 
                        self.doc(self.demo,'LiveSlides'), 
                        self.doc(self.load_docs,'LiveSlides'),
                        self.doc(self.build_report,'LiveSlides')])
        
        self.progress_slider.index = 0 # back to title
        return self
    
    def build_report(self, path = 'report.html', page_size = 'letter', allow_non_html_repr = False, text_font = 'sans-serif',code_font = 'monospace'):
        """Build a beutiful html report from the slides that you can print. Widgets are not supported for this purpose.
        Use 'overrides.css' file in same folder to override CSS.
        Use 'slides-only' and 'report-only' classes to generate slides only or report only content.
        """
        content = ''
        for item in self.slides:
            content += '<section>' # section for each slide
            for out in item.slide.outputs:
                if 'text/html' in out.data:
                    content += out.data['text/html']
                elif allow_non_html_repr:
                    if 'text/plain' in out.data:
                        content += out.data['text/plain']
                    else:
                        content += 'No HTML or text for this object'
            content += '</section>'
        
        content  = content.replace('<section></section>','') # Remove empty sections
        
        __style_css__ = doc_css.replace('__textfont__', f'"{text_font}"').replace('__codefont__', f'"{code_font}"')
        html = doc_html.replace(
            '__page_size__',page_size).replace(
            '__code_css__', code_css(background = 'none')).replace(
            '__style_css__', __style_css__).replace(
            '__content__', content)
        
        # Save now
        _path = path.split('.')[0] + '.html' if path != 'report.html' else path
        with open(_path,'w') as f:
            f.write(html)

def _parse_md_file(fp):
    "Parse a Markdown file or StringIO to put in slides and returns text for title and each slide."
    lines = fp.readlines()
    breaks = [-1] # start, will add +1 next
    for i,line in enumerate(lines):
        if line and line.strip() =='---':
            breaks.append(i)
    breaks.append(len(lines)) # Last one
    
    ranges = [range(j+1,k) for j,k in zip(breaks[:-1],breaks[1:])]
    return [''.join(lines[x.start:x.stop]) for x in ranges]
        