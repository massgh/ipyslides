"""
Export Slides to HTML report and static HTML slides. It is used by program itself, 
not by end user.
"""
import re
import os
from .export_template import doc_css, doc_html, slides_css
from ..formatter import code_css

class _HhtmlExporter:
    # Should be used inside LiveSlides class only.
    def __init__(self, _instance_BaseLiveSlides):
        self.main = _instance_BaseLiveSlides
        
    def _htmlize(self, allow_non_html_repr = False, as_slides = False, **kwargs):
        "page_size, text_font, code_font, slide_number are in kwargs"
        content = ''
        for item in self.main:
            _html = ''
            for out in item.contents:
                if 'text/html' in out.data:
                    _html += out.data['text/html']
                elif allow_non_html_repr and (as_slides == False):
                    if 'text/plain' in out.data:
                        _html += out.data['text/plain']
                    else:
                        _html += f'<p style="color:red;">Object at {hex(id(out))} has no text/HTML representation.</p>'  
            if _html != '':  # If a slide has no content or only widgets, it is not added to the report/slides.    
                _sn = (f'<span class="html-slide-number">{item.position}/{int(self.main[-1].position)}</span>' 
                        if kwargs.get("slide_number",False) and item.position != 0 else '')
                content += (f'<section><div class="SlideArea">{_html}</div>{_sn}</section>' 
                            if as_slides else f'<section>{_html}</section>')
                
        
        __style_css__ = (re.sub('\(.*-width.*\)','(max-width: 650px)',self.main.widgets.htmls.theme.value) + slides_css # Column break width
                            if as_slides else doc_css.replace(
                                '__textfont__', f'"{kwargs.get("text_font","STIX Two Text")}"').replace(
                                '__codefont__', f'"{kwargs.get("code_font","monospace")}"')
                        )
        __code_css__ = self.main.widgets.htmls.hilite.value if as_slides else code_css(color='var(--primary-fg)')
        
        return doc_html.replace(
            '__page_size__',kwargs.get('page_size','letter')).replace(
            '__code_css__', __code_css__).replace(
            '__style_css__', __style_css__).replace(
            '__content__', content)

    def _writefile(self, path, content, overwrite = False):
        if os.path.isfile(path) and not overwrite:
            print(f'File {path!r} already exists. Use overwrite=True to overwrite.')
            return
        
        with open(path,'w') as f:
            f.write(content) 
            
        print(f'File {path!r} saved!')
    
    def report(self, path='report.html', allow_non_html_repr = True, page_size = 'letter', text_font = 'STIX Two Text', code_font = 'monospace', overwrite = False):
        """Build a beutiful html report from the slides that you can print. Widgets are not supported for this purpose.
        
        - allow_non_html_repr: (True), then non-html representation of the slides like text/plain will be used in report.
        - Use 'overrides.css' file in same folder to override CSS styles.
        - Use 'report-only' class to generate additional content that only appear in report.
        - Use 'slides-only' class to generate content that only appear in slides.
        
        New in 1.5.2
        """
        if self.main.citations and (self.main._citation_mode != 'global'):
            raise ValueError(f'''Citations in {self.main._citation_mode!r} mode are not supported in report. 
            Use LiveSLides(citation_mode = "global" and run all slides again before generating report.''')
        
        _path = os.path.splitext(path)[0] + '.html' if path != 'report.html' else path
        content = self._htmlize(allow_non_html_repr = allow_non_html_repr, as_slides = False, page_size = page_size, text_font = text_font, code_font = code_font)
        self._writefile(_path, content, overwrite = overwrite)
    
    def slides(self, path = 'slides.html', slide_number = True, overwrite = False):
        """Build beutiful html slides that you can print. Widgets are not supported for this purpose.
        
        - Use 'overrides.css' file in same folder to override CSS styles.
        - Use 'slides-only' and 'report-only' classes to generate slides only or report only content.
        - If a slide has only widgets or does not have single object with HTML representation, it will be skipped.
        - You can take screenshot (using system's tool) of a widget and add it back to slide using `LiveSlides.image` to keep PNG view of a widget. 
        - To keep an empty slide, use at least an empty html tag inside an HTML like `IPython.display.HTML('<div></div>')`.
        
        New in 1.5.2
        """
        _path = os.path.splitext(path)[0] + '.html' if path != 'slides.html' else path
        content = self._htmlize(allow_non_html_repr = False, as_slides = True, slide_number = slide_number)
        self._writefile(_path, content, overwrite = overwrite)