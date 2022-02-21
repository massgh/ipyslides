from ipyslides.objs_formatter import bokeh2html, plt2html
import matplotlib.pyplot as plt # plt for imshow here
import itertools, sys
import time, datetime
from collections import namedtuple
from time import sleep
from PIL import ImageGrab
from IPython.display import display, Javascript, HTML, Image
import ipywidgets as ipw
from ipywidgets import Layout,Button,Box,HBox,VBox
from . import data_variables as dv
import datetime, os 
from IPython.utils.capture import capture_output
from contextlib import contextmanager
from .utils import textbox
from . import utils
_under_slides = {k:getattr(utils,k,None) for k in utils.__all__}
from .objs_formatter import fix_ipy_image
from .source import Source
from .writers import write, iwrite


def custom_progressbar(intslider):
    "This has a box as children[0] where you can put navigation buttons."
    html = ipw.HTML('''<style>
     .NavWrapper .nav-box .menu {font-size:24px !important; overflow:hidden;opacity:0.4;z-index:55;}
     .NavWrapper .nav-box .menu:hover {opacity:1;}

    .NavWrapper .nav-box {z-index:50;overflow: hidden;}
    .NavWrapper .widget-hprogress {height:4px; !impportant;}
    .NavWrapper, .NavWrapper>div {padding:0px;margin:0px;overflow:hidden;max-width:100%;}
    .NavWrapper .progress, .NavWrapper .progress .progress-bar {
        border-radius:0px; margin:0px;padding:0px;height:4px !important;overflow:hidden;left:0px;bottom:0px;}
    .NavWrapper .progress {width:100% !important;transform:translate(-2px,1px) !important;}
    </style>''')
    intprogress = ipw.IntProgress(min=intslider.min, max=intslider.max, layout=Layout(width='100%'))
    for prop in ('min','max','value'):
        ipw.link((intprogress, prop), (intslider, prop)) # These links enable auto refresh from outside
    return VBox([HBox(layout=Layout(height='0px')).add_class('nav-box'),
                            VBox([ html,intprogress]) ]).add_class('NavWrapper') #class is must


class NavBar:
    def __init__(self,N=10):
        "N is number of slides here."
        self.N = N
        self.__images = {} #Store screenshots
        self.__print_settings = {'load_time':0.5,'quality':100,'bbox':None}
        self.prog_slider = ipw.IntSlider(options= [(f'{i}',i) for i in range(N)],continuous_update=False,readout=True)
        self.btn_prev =  Button(icon='chevron-left',layout= Layout(width='auto',height='auto')).add_class('arrows')
        self.btn_next =  Button(icon='chevron-right',layout= Layout(width='auto',height='auto')).add_class('arrows')
        self.btn_setting =  Button(description= '\u2630',layout= Layout(width='auto',height='auto')).add_class('menu').add_class('float-cross-btn')
        self.btn_capture =  Button(icon='camera',layout= Layout(width='auto',height='auto'),
                                   tooltip='Take Screen short in full screen. Order of multiple shots in a slide is preserved!',
                                   ).add_class('screenshot-btn') # .add_class('menu')
        for btn in [self.btn_next, self.btn_prev, self.btn_setting,self.btn_capture]:
                btn.style.button_color= 'transparent'
                btn.layout.min_width = 'max-content' #very important parameter
        
        self.dd_clear = ipw.Dropdown(description='Delete',options = ['None','Delete Current Slide Screenshots','Delete All Screenshots'])
        self.btn_pdf = Button(description='Save PDF',layout= Layout(width='auto',height='auto'))
        self.btn_png = Button(description='Save PNG',layout= Layout(width='auto',height='auto'))
        self.btn_print = Button(description='Print PDF',layout= Layout(width='auto',height='auto'))
                
        self.info_html = ipw.HTML('<p>Put Your Info Here using `self.set_footer` function</p>')
        self.toast_html = ipw.HTML() # For notifications
        self.cursor_html = ipw.HTML().add_class('LaserPointer') # For beautiful cursor
        self.nav_footer =  HBox([self.btn_setting,
                              HBox([self.info_html],layout= Layout(overflow_x = 'auto',overflow_y='hidden')),
                              self.btn_capture
                              ])
        self.controls = HBox([self.btn_prev,ipw.Box([self.prog_slider]).add_class('ProgBox'),self.btn_next],
                            ).add_class('controls')
        self.toast_check = ipw.Checkbox(value = False, description='Hide Notifications')
        
        self.build_navbar() # this is the main function to build the navbar
         
        self.toast_check.observe(self.__toggle_notify,names=['value'])
        self.btn_prev.on_click(self.__shift_left)
        self.btn_next.on_click(self.__shift_right)
        self.btn_capture.on_click(self.capture_screen)
        self.btn_pdf.on_click(self.__save_pdf)
        self.btn_png.on_click(self.__save_images)
        self.btn_print.on_click(self.__print_pdf)
        self.dd_clear.observe(self.__clear_images)
    
    def build_navbar(self):
        self.nav_bar = custom_progressbar(self.prog_slider)
        self.nav_bar.children[0].children = (self.nav_footer,)
        self.nav_bar.children[0].layout.height = '32px'
       
    def __shift_right(self,change):
        if change:
            self.prog_slider.value = (self.prog_slider.value + 1) % self.N  
    
    def __shift_left(self,change):
        if change:
            self.prog_slider.value = (self.prog_slider.value - 1) % self.N
    
    def show(self):
        return self.nav_bar
    __call__ = show
    
    def notify(self,content,title='IPySlides Notification',timeout=5):
        "Send inside notifications for user to know whats happened on some button click. Set `title = None` if need only content. Remain invisible in screenshot."
        if content and isinstance(content,str):
            self.toast_html.value = '' # Set first to '', otherwise may not trigger for same value again.
            self.toast_html.value = dv.notification(content=content,title=title,timeout=timeout)
    
    def __toggle_notify(self,change):
        "Blocks notifications."
        if self.toast_check.value:
            self.toast_html.layout.visibility = 'hidden' 
        else:
            self.toast_html.layout.visibility = 'visible' 
        
    @contextmanager
    def __print_context(self):
        hide_widgets = [self.controls,self.btn_setting,self.btn_capture,self.float_ctrl,self.toast_html,self.cursor_html]
        old_pref = self.toast_html.layout.visibility # To keep user prefernce back after screenshot
        for w in hide_widgets:
            w.layout.visibility = 'hidden'
        try:    
            yield
        finally:
            for w in hide_widgets:
                w.layout.visibility = 'visible' 
            self.toast_html.layout.visibility = old_pref 
                
    def screen_bbox(self):
        "Return screen's bounding box on windows, return None on other platforms which works as full screen too in screenshot."
        try:
            import ctypes
            user = ctypes.windll.user32
            user.SetProcessDPIAware()
            return (0, 0, user.GetSystemMetrics(0), user.GetSystemMetrics(1))
        except:
            return None

    def set_print_settings(self,load_time=0.5,quality=95,bbox = None):
        """Print settings. 
        - load_time: 0.5; time in seconds for each slide to load before print, only applied to Print PDF, not on manual screenshot. 
        - quality: 95; In term of current screen. Will not chnage too much above 95. 
        - bbox: None; None for full screen on any platform. Given screen position of slides in pixels as [left,top,right,bottom].
        > Note: Auto detection of bbox in frontends where javascript runs is under progress. """
        if bbox and len(bbox) != 4:
            return print("bbox expects [left,top,right,bottom] in integers")
        self.__print_settings = {'load_time':load_time,'quality':quality,'bbox':bbox if bbox else self.screen_bbox()} # better to get on windows
        # Display what user sets
        if bbox:
            img = ImageGrab.grab(bbox=bbox)
            _ = plt.figure(figsize = (3, 3*img.height/img.height), dpi=720) # For clear view
            _ = plt.imshow(img)
            plt.gca().set_axis_off()
            plt.subplots_adjust(left=0,bottom=0,top=1,right=1)
            plt.show() # Display in Output widget too.     
    
    def get_print_settings(self):
        return self.__print_settings    
    
    def __set_resolution(self,image):
        "Returns resolution to make PDF printable on letter/A4 page."
        w, h = image.size
        short, res = (h, w/11) if w > h else (w, h/11) # letter page size landscape else portrait
        
        if short/res > 8.25: # if short side out of page, bring inside A4 size so work for both A4/Letter
            return short/8.25  # change resolution to shrink pages size to fit for print,long side already inside page
        
        return res   # Return previous resolution
    
    def capture_screen(self,btn):
        "Saves screenshot of current slide into self.__images dictionary when corresponding button clicked. Use in fullscreen mode"
        with self.__print_context():
            sleep(0.05) # Just for above clearance of widgets views
            img = ImageGrab.grab(bbox=self.__print_settings['bbox']) 
        for i in itertools.count():
            if not f'im-{self.prog_slider.value}-{i}' in self.__images:
                self.__images[f'im-{self.prog_slider.value}-{i}'] =  img 
                return # Exit loop
    
    def __sort_images(self):
        ims = [] #sorting
        for i in range(self.prog_slider.max + 1): # That's maximum number of slides
            for j in range(len(self.__images)): # To be on safe side, no idea how many captures
                if f'im-{i}-{j}' in self.__images:
                    ims.append(self.__images[f'im-{i}-{j}'])
        return tuple(ims)
            
    def save_pdf(self,filename='IPySlides.pdf'):
        "Converts saved screenshots to PDF!"
        ims = self.__sort_images()    
        if ims: # make sure not empty
            self.btn_pdf.description = 'Generatingting PDF...'
            ims[0].save(filename,'PDF',quality= self.__print_settings['quality'] ,save_all=True,append_images=ims[1:],
                        resolution=self.__set_resolution(ims[0]),subsampling=0)
            self.btn_pdf.description = 'Save PDF'
            self.notify(f'File "{filename}" is created')
        else:
            self.notify('No images found to convert. Take screenshots of slides, then use this option.')
    
    def __save_pdf(self,btn):
        self.save_pdf() # Runs on button
        
    def __print_pdf(self,btn):
        "Quick Print"
        self.btn_setting.click() # Close side panel
        imgs = []
        for i in range(self.prog_slider.max + 1):  
            with self.__print_context():
                self.prog_slider.value = i #keep inside context manger to avoid slide transitions
                sleep(self.__print_settings['load_time']) #keep waiting here until it almost loads 
                imgs.append(ImageGrab.grab(bbox=self.__print_settings['bbox']))
                  
        if imgs:
            imgs[0].save('IPySlides-Print.pdf','PDF',quality= self.__print_settings['quality'],save_all=True,append_images=imgs[1:],
                         resolution=self.__set_resolution(imgs[0]),subsampling=0)
            self.notify("File 'IPySlides-Print.pdf' saved.") 
        # Clear images at end
        for img in imgs:
            img.close()    
    
    @property
    def screenshots(self):
        "Get all captured screenshots in order."
        return self.__sort_images()
    
    def save_images(self,directory='ipyslides-images'):
        "Save all screenshots as PNG in given `directory`. Names are auto ordered"
        self.btn_png.description = 'Saving PNGs...'
        if not os.path.isdir(directory):
            os.mkdir(directory)
        
        ims = self.images
        if ims:    
            for i,im in enumerate(ims):
                im.save(os.path.join(directory,f'Slide-{i:03}.png'),'PNG',quality= self.__print_settings['quality'],subsampling=0,optimize=True)  # Do not lose image quality at least here
            md_file = os.path.join(directory,'Make-PPT.md')
            with open(md_file,'w') as f:
                f.write(dv.how_to_ppt)
            self.notify(f'''All captured images are saved in "{directory}"<br/> 
                         <em>See file "{md_file}" as bonus option!</em>''',timeout=10)
        else:
            self.notify('No images found to save. Take screenshots of slides, then use this option.')
        
        self.btn_png.description = 'Save PNG'
        
    def __save_images(self,btn):
        "With Button call"
        self.save_images()
    
    def __clear_images(self,change):
        if 'Current' in self.dd_clear.value:
            self.__images = {k:v for k,v in self.__images.items() if f'-{self.prog_slider.value}-' not in k}
            for k,img in self.__images.items():
                if f'-{self.prog_slider.value}-' in k:
                    img.close() # Close image to save mememory
            self.notify('Deleted screenshots of current slide')
        elif 'All' in self.dd_clear.value:
            for k,img in self.__images.items():
                img.close() # Close image to save mememory
            self.__images = {} # Cleaned up
            self.notify('Deleted screenshots of all slides')
        
        self.dd_clear.value = 'None' # important to get back after operation
    
    
        
class LiveSlides(NavBar):
    __slides__ = {} # Collect all instances here
    def __init__(self,magic_suffix='',animation_css = dv.animations['slide_h']):
        """Interactive Slides in IPython Notebook. Use `display(Markdown('text'))` instead of `print` in slides.
        - **Parameters**
            - magic_suffix: str, append a string to %%slide and %%title in case you have many instances of this class, they do not overwrite each other's magics.
                    So for LiveSlides('A'), use %%slideA, %%titleA, for LiveSlides('B'), use %%slideB, %%titleB and so on.
            - animation_css: CSS for animation. Set to '' if not animating. You can define yourself by editing `ipysildes.data_variables.animations`.
        - **Example**
            ```python 
            import ipyslides as isd 
            isd.initilize() #This will generate code in same cell including this class, which is self explainatory 
            ```
        """
        self.uid = f's{id(self)}' # For uniqueness in javascript
        for k,v in _under_slides.items(): # Make All methods available in slides
            setattr(self,k,v)
        self.plt2html = plt2html
        self.bokeh2html = bokeh2html
        self.source = Source # Code source
        self.write = write # Write IPython objects in slides
        self.iwrite = iwrite # Write Widgets/IPython in slides
        
        try:  # Handle python IDLE etc.
            self.shell = get_ipython()
        except:
            print("Slides only work in IPython Notebook!")
            sys.exit()
            
        self.shell.register_magic_function(self.__slide, magic_kind='cell',magic_name=f'slide{magic_suffix}')
        self.shell.register_magic_function(self.__title, magic_kind='cell',magic_name=f'title{magic_suffix}')
        self.user_ns = self.shell.user_ns #important for set_dir
        self.__class__.__slides__[self.uid] = self # Collect all instances
        self.animation_css = animation_css
        self.__citations = {} # Initialize citations
        self.__slides_mode = False
        with capture_output() as captured:
            write('''## Create title page using `%%title` magic or `self.title()` context manager.\n> Author: Abdul Saboor\n<div>
        <h4 style="color:green;">Create Slides using <pre>%%slide</pre> or with <pre>self.slide(slide_number)</pre> context manager.</h4>
        <h4 style="color:olive;">Read instructions by clicking on left-bottom button</h4></div>
        ''')
        self.__slides_title_page = captured
        self.__slides_title_notes = None #must be None, not True/False
        self.__slides_dict = {} # Initialize slide dictionary
        self.__dynamicslides_dict = {} # initialize dynamic slides dictionary
        self.__slides_notes = {} # Initialize notes dictionary
        self.__current_slide = 'title' # Initialize current slide for notes at title page
        
        self.__iterable = self.__collect_slides() # Collect internally
        self.nslides = int(self.__iterable[-1]['n']) if self.__iterable else 0
        self.out = ipw.Output(layout= Layout(width='auto',height='auto',margin='auto',overflow='auto',padding='2px 36px')
                              ).add_class('SlideArea').add_class(self.uid)
        
        _max = len(self.__iterable) if self.__iterable else 0
        super().__init__(N=_max)
        self.controls.children[1].add_class(self.uid) # Add to pro_slider_box, 
        self.theme_root = dv.theme_roots['Inherit']
        self.font_scale = 1 #Scale 1 corresponds to 16px
        self._font_family = {'code':'var(--jp-code-font-family)','text':'sans-serif'}
        self.theme_html = ipw.HTML(dv.style_html(self.theme_root.replace('__text_size__','16px')).replace(
                                '__breakpoint_width__','650px').replace(
                                '__textfont__',self._font_family['text']).replace(
                                '__codefont__',self._font_family['code']))
        self.main_style_html = ipw.HTML(dv.main_layout_css)
        self.sidebar_html = ipw.HTML(dv.sidebar_layout_css()) # Should be separate CSS
        self.loading_html = ipw.HTML() #SVG Animation in it
        self.prog_slider.observe(self.__set_class,names=['value'])
        self.prog_slider.observe(self.__update_content,names=['value'])
        # For controlling slide's display mode, should be before Customize call
        self.display_switch =  ipw.ToggleButtons(description='Display Mode',options=[('Inline',0),('Sidebar',1)],value = 1).add_class('DisplaySwitch')
        
        self.setting = Customize(self)  # Call settings now
        self.panel_box = self.setting.box
        self.slide_box = Box([self.out],layout= Layout(min_width='100%',overflow='auto')).add_class('SlideBox').add_class(self.uid)
        self.logo_html = ipw.HTML()
        self.float_ctrl = ipw.IntSlider(description='View (%)',min=0,value=100,max=100,orientation='vertical').add_class('float-control')
        self.float_ctrl.observe(self.__set_hidden_height,names=['value'])
        self.__footer_text = ""
        # All Box of Slides
        self.box =  VBox([self.loading_html, self.toast_html,self.main_style_html,
                          self.theme_html,self.logo_html, self.sidebar_html,
                          self.panel_box, self.cursor_html.add_class(self.uid),
                          HBox([ #Slide_box must be in a box to have animations work
                            self.slide_box,
                          ],layout= Layout(width='100%',max_width='100%',height='100%',overflow='hidden')), #should be hidden for animation purpose
                          self.controls.add_class(self.uid), # Importnat for unique display
                          self.float_ctrl,
                          self.nav_bar
                          ],layout= Layout(width=f'{self.setting.width_slider.value}vw', height=f'{self.setting.height_slider.value}px',margin='auto'))
        self.box.add_class('SlidesWrapper') #Very Important 
        self.__update_content(True) # First attmpt
        self.app = self.box # Alias 
        self.__toasts = {} # Collecting slides' notification toasts
        self._notes_html = ipw.HTML('Notes Area').add_class('Inline-Notes') # For below slides area
        
        for w in (self.btn_next,self.btn_prev,self.btn_setting,self.btn_capture,self.box):
            w.add_class(self.uid)
            
    
    @property
    def slides(self):
        "Get slides list"
        nt = namedtuple('SLIDE','slide n notes')
        return tuple([nt(**d) for d in self.__iterable])
    
    def notes(self,content):
        "Add notes to current slide. Content could be any object except javascript and interactive widgets."
        if self.__current_slide == 'title':
            self.__slides_title_notes, = self.format_html(content).values()
        elif self.__current_slide == 'frames':
            raise ValueError("Notes can't be added under slide frames")
        else:
            self.__slides_notes[self.__current_slide], = self.format_html(content).values()
        
        
    def _push2sidebar(self,span_percent = 50): # Value should be same as width_slider's initial value
        """Pushes this instance of LiveSlides to sidebar and other instances inline."""
        if not getattr(self,'setting',False):
            return None # Do not process unless setting is displayed is done
        
        # Now Work on process
        if isinstance(span_percent,int) and self.display_switch.value == 1:
            self.sidebar_html.value = dv.sidebar_layout_css(span_percent=span_percent).replace('__uid__',self.uid)
            self.setting.height_slider.layout.display = 'none'
            
            for other in self.__class__.__slides__.values():    
                if other.uid != self.uid: # Add robust check 
                    other.display_switch.value = 0 # This will trigger many events but in else block,so nothing to worry
        else:
            self.sidebar_html.value = '' # Should be empty to avoid competition of style
            self.setting.height_slider.layout.display = 'inline-flex' #Very impprtant
        return self.setting.emit_resize_event() # Must return this event so it work in other functions.
            
            
    def set_font_family(self,text_font=None,code_font=None):
        "Set main fonts for text and code."
        if text_font:
            self._font_family['text'] = text_font
        if code_font:
            self._font_family['code'] = code_font  
        self.setting.update_theme() # Changes Finally  
    
    def __set_hidden_height(self,change):
        self.slide_box.layout.height = f'{self.float_ctrl.value}%'
        self.slide_box.layout.margin='auto 4px'
            
    def set_logo(self,src,width=80,top=0,right=16):
        "`src` should be PNG/JPEG file name or SVG string. width,top,right are pixels, should be integer."
        if '<svg' in src and '</svg>' in src:
            image = src
        else:
            image = fix_ipy_image(Image(src,width=width),width=width) #width both in Image and its fixing
            
        self.logo_html.value = f"""<div style='position:absolute;right:{right}px;top:{top}px;width:{width}px;height:auto;'>
                                    {image}</div>"""
    
    def notify_at(self, slide, title='IPySlides Notification', timeout=5):
        """Decorartor to push notification at given slide. It should return as string. `slide` here is what you see on slides's footer like 3.1, not just int.
        The content is dynamically generated by underlying function, so you can set timer as well. Remains invisible in screenshot through app itself.
        
        @notify_at(slide=1)
        def push_to(slide): #you can refer slide number in noteification function. 
            ..."""
        def _notify(func): 
            self.__toasts[f'{slide}'] = dict(func = func,arg = slide,kwargs = dict(title=title, timeout=timeout))
        return _notify
    
    def clear_notifications(self):
        "Remove all redundent notifications that show up."
        self.__toasts = {} # Free up
    
    @property
    def notifications(self):
        "See all stored notifications."
        return self.__toasts
    
    def __display_toast(self):
        slide_id = str(self.__iterable[self.prog_slider.value - 1]['n'])
        try:
            toast = self.__toasts[slide_id]
            self.notify(content=toast['func'](toast['arg']),**toast['kwargs'])
        except:pass 
    
    def __add__(self,other):
        "Add two slides instance, title page of other is taken as a slide."
        slides = LiveSlides()
        slides.convert2slides(True)
        slides.set_footer() #starting text
        with slides.title():
            self.__slides_title_page.show() #Ipython Captured Output 
        # Make slide from other slides' title page
        _slide = {'slide': other.__slides_title_page}
            
        for i, s in enumerate([*self.__iterable, _slide, *other.__iterable]):
            with slides.slide(i+1):
                s['slide'].show() # Pre-Calculated Slides
        return slides
    
    def cite(self,key, citation,here=False):
        "Add citation in presentation, both key and citation are text/markdown/HTML."
        if here:
            return textbox(citation,left='initial',top='initial') # Just write here
        self.__citations[key] = citation
        _id = list(self.__citations.keys()).index(key)
        return f'<sup style="color:var(--accent-color);">{_id + 1}</sup>'
    
    def write_citations(self,title='### References'):     
        collection = [f'<span><sup style="color:var(--accent-color);">{i+1}</sup>{v}</span>' for i,(k,v) in enumerate(self.__citations.items())]
        return write(title + '\n' +'\n'.join(collection))      
    
    def show(self, fix_buttons = False): 
        "Display Slides. If icons do not show, try with `fix_buttons=True`."
        if not self.__slides_mode:
            return print('Set "self.convert2slides(True)", then it will work.')
        if fix_buttons:
            self.btn_next.description = '▶'
            self.btn_prev.description = '◀'
            self.btn_prev.icon = ''
            self.btn_next.icon = ''
        else: # Important as showing again with False will not update buttons. 
            self.btn_next.description = ''
            self.btn_prev.description = ''
            self.btn_prev.icon = 'chevron-left'
            self.btn_next.icon = 'chevron-right'
        self.__jlab_in_cell_display()
        return self.box
    __call__ = show
    
    def _ipython_display_(self):
        'Auto display when self is on last line of a cell'
        self.__jlab_in_cell_display()
        return display(self.box)
    
    def __jlab_in_cell_display(self): 
        # Can test Voila here too
        try: # SHould try, so error should not block it
            if 'voila' in self.shell.config['IPKernelApp']['connection_file']:
                self.setting.width_slider.value = 100 # This fixes dynamic breakpoint in Voila
        except: pass # Do Nothing
         
        self.display_switch.observe(self.__relocate_displays,names=['value'])        
        self.display_switch.value = 0 # Initial Call must be inline, so that things should be shown outside Jupyterlab always
        return display(VBox([
                            HBox([
                                ipw.HTML("""<b style='color:var(--accent-color);font-size:24px;'>IPySlides</b>"""),
                                self.display_switch
                            ]),
                            self.setting.btn_timer,
                            self._notes_html
                        ])
                )
    
    def __relocate_displays(self,change):
        if change and change['new']: # Turns ON at value 1 of display_switch
            self._push2sidebar(span_percent = self.setting.width_slider.value)
        else:
            self._push2sidebar(False)

    def align8center(self,b=True):
        "Central aligment of slide by default. If False, left-top aligned."
        if b:
            self.out.layout.margin = 'auto'
            self.out.layout.width = 'auto'
            self.out.layout.max_width = '100%'
        else:
            self.out.layout.margin = '2px 8px 2px 8px'
            self.out.layout.width = '100%'
        
    def set_font_scale(self,font_scale=1):
        self.font_scale= font_scale
        self.setting.update_theme()  
        
    def __set_class(self,change):
        "Set Opposite animation for backward navigation"
        self.slide_box.remove_class('Prev') # Safely Removes without error
        if change['new'] == self.prog_slider.max and change['old'] == 0:
            self.slide_box.add_class('Prev')
        elif (change['new'] < change['old']) and (change['old'] - change['new'] != self.prog_slider.max):
            self.slide_box.add_class('Prev')
    
    def __display_slide(self):
        self.__display_toast() # Display in start is fine
        item = self.__iterable[self.prog_slider.value]
        self.setting.show_notes(item['notes']) # Display notes first
        _number = f'{item["n"]} / {self.nslides}' if self.prog_slider.value != 0 else ''
        self.info_html.value = self.__footer_text.replace('__number__',_number) #Slide Number
        
        if not self.controls.layout.visibility == 'hidden': # No animations while printing
            check = round(item["n"] - int(item["n"]), 2) # Must be rounded
            if check <= 0.1: # First frame should slide only to make consistent look
                write(self.animation_css) 
        return item['slide'].show() 
           
    def __update_content(self,change):
        if self.__slides_title_page or (self.__iterable and change):
            self.loading_html.value = dv.loading_svg
            self.out.clear_output(wait=True)
            with self.out:
                self.__display_slide()

            self.loading_html.value = ''       
            
    def set_footer(self, text = 'Abdul Saboor | <a style="color:blue;" href="www.google.com">google@google.com</a>', show_slide_number=True, show_date=True):
        if show_date:
            text += f' | <text style="color:var(--secondary-fg);">' + datetime.datetime.now().strftime('%b-%d-%Y')+ '</text>'
        if show_slide_number: #Slide number should be replaced from __number__ 
            text += '<b style="color:var(--accent-color);white-space:pre;">  __number__<b>'
        self.__footer_text = f'<p style="white-space:nowrap;"> {text} </p>'
        self.info_html.value = self.__footer_text.replace('__number__','')
        
    def refresh(self): 
        "Auto Refresh whenever you create new slide or you can force refresh it"
        self.__iterable = self.__collect_slides()
        if self.__iterable:
            self.nslides = int(self.__iterable[-1]['n']) # Avoid frames number
            self.N = len(self.__iterable)
        else:
            self.nslides = 0
            self.N = 0
        self.prog_slider.max = self.N - 1
        self.__update_content(True) # Force Refresh
        
    def write_slide_css(self,**css_props):
        "Provide CSS values with - replaced by _ e.g. font-size to font_size."
        _css_props = {k.replace('_','-'):f"{v}" for k,v in css_props.items()} #Convert to CSS string if int or float
        _css_props = {k:v.replace('!important','').replace(';','') + '!important;' for k,v in _css_props.items()}
        props_str = ''.join([f"{k}:{v}" for k,v in _css_props.items()])
        out_str = "<style>\n" + f".SlidesWrapper.{self.uid}, .SlideArea.{self.uid} .block " + "{" + props_str + "}\n"
        if 'color' in _css_props:
            out_str += f".SlidesWrapper.{self.uid} p, .SlidesWrapper.{self.uid}>:not(div){{ color: {_css_props['color']}}}"
        return write(out_str + "\n</style>") # return a write object for actual write
    
    # defining magics and context managers
    
    def __slide(self,line,cell):
        "Turns to cell magic `slide` to capture slide. Moves to this slide when executed."
        line = line.strip() #VSCode bug to inclue \r in line
        if line and not line.isnumeric():
            return print(f'You should use %%slide integer, not %%slide {line}')
        
        self.__current_slide = f'{line}'
        if self.__slides_mode:
            self.shell.run_cell_magic('capture',line,cell)
            if line: #Only keep slides with line number
                self.__slides_dict[line] = self.shell.user_ns[line]
                del self.shell.user_ns[line] # delete the line from shell
                self.refresh()
        else:
            self.shell.run_cell(cell)
    
    @contextmanager
    def slide(self,slide_number,**css_props):
        """Use this context manager to generate any number of slides from a cell
        `css_props` are applied to current slide. `-` -> `_` as `font-size` -> `font_size` in python."""
        if not isinstance(slide_number,int):
            return print(f'slide_number expects integer, got {slide_number!r}')
        
        self.__current_slide = f'{slide_number}'
        with capture_output() as cap:
            self.write_slide_css(**css_props)
            yield
        # Now Handle What is captured
        if not self.__slides_mode:
            cap.show()
        else:
            self.__slides_dict[f'{slide_number}'] = cap 
            self.refresh()
    
    def code_line_numbering(self,b=True):
        if b:
            return display(HTML('<style> code:before{ display:inline-block !important; } </style>'))
        return display(HTML('<style> code:before{ display:none !important; } </style>'))
    
    def __title(self,line,cell):
        "Turns to cell magic `title` to capture title"
        self.__current_slide = 'title'
        if self.__slides_mode:
            self.shell.run_cell_magic('capture','title_output',cell)
            self.__slides_title_page = self.shell.user_ns['title_output']
            del self.shell.user_ns['title_output'] # delete from shell
            self.refresh()
        else:
            self.shell.run_cell(cell)
            
    @contextmanager
    def title(self,**css_props):
        """Use this context manager to write title.
        `css_props` are applied to current slide. `-` -> `_` as `font-size` -> `font_size` in python."""
        self.__current_slide = 'title'
        with capture_output() as cap:
            self.write_slide_css(**css_props)
            yield
        # Now Handle What is captured
        if not self.__slides_mode:
            cap.show()
        else:
            self.__slides_title_page = cap 
            self.refresh()
    
    def frames(self, slide_number, *objs, **css_props):
        """Decorator for inserting frames on slide, define a function with one argument acting on each obj in objs.
        Every `obj` is shown on it's own frame. No return of function required, if any, only should be display/show etc.
        `css_props` are applied to all slides from *objs. `-` -> `_` as `font-size` -> `font_size` in python."""
        self.__current_slide = 'frames'
        def _frames(func):
            if not isinstance(slide_number,int):
                return print(f'slide_number expects integer, got {slide_number!r}')

            if not self.__slides_mode:
                print(f'Showing raw form of given objects, will be displayed in slides using function {func} dynamically')
                return objs
            else:
                _slides = []
                for obj in objs:
                    with capture_output() as cap:
                        self.write_slide_css(**css_props)
                        func(obj)
                    _slides.append(cap)
                 
                self.__dynamicslides_dict[f'd{slide_number}'] = {'objs': _slides}
                    
                self.refresh() # Content change refreshes it.
        return _frames
        
    def convert2slides(self,b=False):
        "Turn ON/OFF slides vs editing mode. Should be in same cell as `LiveSLides`"
        self.__slides_mode = b

        
    def __collect_slides(self):
        """Collect cells for an instance of LiveSlides."""
        if not self.__slides_mode:
            return [] # return empty in any case

        dynamic_slides = [k.replace('d','') for k in self.__dynamicslides_dict.keys()]
        # If slide number is mistaken, still include that. 
        all_slides = [int(k) for k in [*self.__slides_dict.keys(), *dynamic_slides]]

        try: #handle dynamic slides if empty
            _min, _max = min(all_slides), max(all_slides) + 1
        except:
            _min, _max = 0, 0
        slides_iterable,n = [], 1 # n is start of slides, no other way
        for i in range(_min,_max):
            if f'{i}' in self.__slides_dict.keys():
                notes = self.__slides_notes[f'{i}'] if f'{i}' in self.__slides_notes else None
                slides_iterable.append({'slide':self.__slides_dict[f'{i}'],'n':n,'notes':notes}) 
                n = n + 1
            if f'd{i}' in self.__dynamicslides_dict.keys():
                __dynamic = self.__dynamicslides_dict[f'd{i}']
                slides = [{'slide':obj,'n':float(f'{n}.{j}'),'notes':None} for j, obj in enumerate(__dynamic['objs'],start=1)]
                if len(slides) == 1:
                    slides[0]['n'] = slides[0]['n'].split('.')[0] # No float in single frame
                slides_iterable = [*slides_iterable,*slides] 
                n = n + 1
        slides_iterable =[{'slide':self.__slides_title_page,'n':0,'notes': self.__slides_title_notes}, *slides_iterable]
        return tuple(slides_iterable)

class Customize:
    def __init__(self,instance_LiveSlides):
        "Provide instance of LivSlides to work."
        self.main = instance_LiveSlides
        self.start_time = None
        def describe(value): return {'description': value, 'description_width': 'initial','layout':Layout(width='auto')}
        
        self.height_slider = ipw.IntSlider(**describe('Height (px)'),min=200,max=2160, value = 400,continuous_update=False).add_class('height-slider') #2160 for 4K screens
        self.width_slider = ipw.IntSlider(**describe('Width (vw)'),min=20,max=100, value = 50,continuous_update=False).add_class('width-slider')
        self.scale_slider = ipw.FloatSlider(**describe('Font Scale'),min=0.5,max=3,step=0.0625, value = 1.0,readout_format='5.3f',continuous_update=False)
        self.theme_dd = ipw.Dropdown(**describe('Theme'),options=[*dv.theme_roots.keys(),'Custom'],value='Inherit')
        self.reflow_check = ipw.Checkbox(value=False,description='Reflow Code',layout=self.theme_dd.layout)
        self.notes_check = ipw.Checkbox(value=False,description='Display Notes',layout=self.theme_dd.layout) # do not observe, just keep track when slides work
        self.bbox_input = ipw.Text(description='L,T,R,B (px)',layout=self.theme_dd.layout,value='Type left,top,right,bottom pixel values and press ↲')
        self.main.toast_check.layout = self.theme_dd.layout # Fix same
        self.main.dd_clear.layout = self.theme_dd.layout # Fix same
        self.__instructions = ipw.Output(clear_output=False, layout=Layout(width='100%',height='100%',overflow='auto',padding='4px')).add_class('panel-text')
        self.out_js_fix = ipw.Output(layout=Layout(width='auto',height='0px'))
        self.out_js_var = ipw.Output(layout=Layout(width='auto',height='0px'))
        self.btn_fs = ipw.ToggleButton(description='Window',icon='expand',value = False).add_class('sidecar-only').add_class('window-fs')
        self.btn_zoom = ipw.ToggleButton(description='Zoom Items',icon='toggle-off',value = False).add_class('sidecar-only').add_class('mpl-zoom')
        self.btn_timer = ipw.ToggleButton(description='Timer',icon='play',value = False).add_class('sidecar-only').add_class('presenter-btn')
        btns_layout = Layout(justify_content='space-around',padding='8px',height='max-content',min_height='30px',overflow='auto')
        self.box = VBox([Box([self.__instructions,self.main.btn_setting,],layout=Layout(width='100%',height='auto',overflow='hidden')),
                        self.out_js_fix, self.out_js_var, # Must be in middle so that others dont get disturbed.
                        VBox([
                            self.height_slider.add_class('voila-sidecar-hidden'), 
                            self.width_slider.add_class('voila-sidecar-hidden'),
                            self.scale_slider,
                            self.theme_dd,
                            ipw.HTML('<hr/>'),
                            self.bbox_input,
                            ipw.HBox([self.notes_check, self.main.toast_check, self.reflow_check],layout=btns_layout),
                            self.main.dd_clear,
                            HBox([self.main.btn_png, self.main.btn_pdf, self.main.btn_print], layout=btns_layout),
                            ipw.HTML('<hr/>'),
                            HBox([self.btn_fs,self.btn_zoom, self.btn_timer], layout=btns_layout),
                            ],layout=Layout(width='100%',height='max-content',min_height='400px',overflow='auto'))
                        ],layout=Layout(width='70%',min_width='50%',height='100%',padding='4px',overflow='auto',display='none')
                        ).add_class('panel').add_class(self.main.uid)
        
        self.box.on_displayed(lambda change: self.__add_js()) # First attempt of Javascript to work
        
        with self.__instructions:
            write(dv.settings_instructions) 
        
        self.theme_dd.observe(self.update_theme)
        self.theme_dd.observe(self.__sync_other_themes,names=['value']) # Change themes of other, thats only way to troubleshoot it
        self.scale_slider.observe(self.__set_font_scale)
        self.height_slider.observe(self.__update_size,names=['value'])
        self.width_slider.observe(self.__update_size,names=['value'])
        self.main.btn_setting.on_click(self.__toggle_panel)
        self.btn_fs.observe(self.update_theme,names=['value'])
        self.btn_zoom.observe(self.update_theme,names=['value'])
        self.reflow_check.observe(self.update_theme)
        self.notes_check.observe(self.__open_close_notes, names=['value'])
        self.update_theme() #Trigger Theme and Javascript in it
        self.bbox_input.on_submit(self.__set_bbox)
        self.btn_timer.observe(self.__timeit,names=['value'])
        
        for w in (self.btn_zoom,self.btn_fs,self.box, self.btn_timer):
            w.add_class(self.main.uid)
    
    def show_notes(self, html_str):
        self.main._notes_html.value = 'Notes Area' # Must be, so when no notes, should not be there
        if html_str and isinstance(html_str,str):
            current_time = time.localtime()
            if current_time.tm_hour > 12:
                time_str = f'{current_time.tm_hour-12:0>2}:{current_time.tm_min:0>2} PM'
            else:
                time_str = f'{current_time.tm_hour:0>2}:{current_time.tm_min:0>2} AM'
            
            
            if self.start_time:
                spent = time.time() - self.start_time 
                h, sec = divmod(spent,3600) # Houres
                m, _ = divmod(sec,60) # Minutes
                spent_str = f'{int(h):0>2}:{int(m):0>2}' # They are floats by default
            else:
                spent_str = '00:00'

            _time = f'''<div style="border-radius:4px;padding:8px;background:var(--secondary-bg);min-width:max-content;">
                        <h2>Time: {time_str}</h2><hr/>
                        <h3>Elapsed Time: {spent_str}</h3><div>'''
                        
            self.main._notes_html.value = f'''<div style="margin:-4px;padding:4px;background:var(--secondary-bg);border-radius:4px 4px 0 0;">
                    <b style="font-size:110%;color:var(--accent-color);">Time: {time_str} | Elapsed Time: {spent_str}</b>
                    </div>''' + html_str # show alaways
            
            # Next everything for Browser window case
            if self.notes_check.value:  # Only show on demand
                theme = self.main.theme_html.value.replace(f'.{self.main.uid}','').replace('FullScreen','') #important
                code_theme = '''<style> 
                                pre { display:flex; flex-direction:column; } 
                                .SlideBox { display:flex; flex-direction:row; justify-content:space-between;}
                                .SlideBox > div:first-child { margin:auto; }
                            </style>'''
                node = f'''{theme}<div class="SlidesWrapper"> 
                        <div class="SlideBox"> 
                            <div class="SlideArea"> {code_theme}{html_str} </div> <div>{_time}</div>
                        </div></div>'''
                    

                with self.out_js_var:
                    display(Javascript(f'''
                    let notes_win = window.open("","__Notes_Window__","popup");
                    notes_win.document.title = 'Notes';
                    notes_win.document.body.innerHTML = {node!r};
                    notes_win.document.body.style.background = 'var(--primary-bg)';
                    '''))
    
    def __open_close_notes(self,change):
        if change['new'] == True:
            with self.out_js_var:
                display(Javascript('''
                let notes_win = window.open("","__Notes_Window__","popup");
                notes_win.resizeTo(screen.width/2,screen.height/2);
                notes_win.moveTo(screen.width/4,screen.height*2/5);
                notes_win.document.title = 'Notes';
                notes_win.document.body.innerHTML = "<h1> Notes will show up here, do not close it manually, just navigate away!</h1>";
                '''))
        else:
            with self.out_js_var:
                display(Javascript('window.open("","__Notes_Window__","popup").close();'))
    
    def __timeit(self,change):
        if change['new'] == True:
            self.btn_timer.icon = 'pause'
            self.start_time = time.time() # Start time here
        else:
            self.btn_timer.icon = 'play'
            self.start_time = None
            
    def __sync_other_themes(self,change): 
        # Only way to have a better experience with themes
        for other in self.main.__class__.__slides__.values():
            other.setting.theme_dd.value = self.theme_dd.value # This will change theme everywhere 
    
    def __set_bbox(self,change):
        bbox = [int(v) for v in self.bbox_input.value.split(',')][:4]    
        print_settings = {**self.main.get_print_settings(), 'bbox':bbox}
        with self.__instructions:
            self.__instructions.clear_output(wait=True)
            self.main.set_print_settings(**print_settings)
            write(dv.settings_instructions) 
        self.main.notify(f'See Screenshot of your selected bbox = {bbox} 👇')
    
    def __add_js(self):
        with self.out_js_fix: 
            display(Javascript(dv.navigation_js.replace('__uid__',self.main.uid)))
    
    def emit_resize_event(self):
        with self.out_js_var: 
            self.out_js_var.clear_output(wait=True)
            display(Javascript("window.dispatchEvent(new Event('resize'));"))
        
    def __update_size(self,change):
        self.main.box.layout.height = '{}px'.format(self.height_slider.value)
        self.main.box.layout.width = '{}vw'.format(self.width_slider.value)  
        self.main._push2sidebar(span_percent = self.width_slider.value)
        self.emit_resize_event() # Although its in _push2sidebar, but for being safe, do this
        self.update_theme(change=None) # For updating size and breakpoints
            
    def __toggle_panel(self,change):
        if self.main.btn_setting.description == '\u2630':
            self.main.btn_setting.description  = '⨉'
            self.box.layout.display = 'flex'
            self.main.btn_next.disabled = True
            self.main.btn_prev.disabled = True
        else:
            self.main.btn_setting.description = '\u2630'
            self.box.layout.display = 'none'
            self.main.btn_next.disabled = False
            self.main.btn_prev.disabled = False
                     
    def __set_font_scale(self,change):
        # Below line should not be in update_theme to avoid loop call.
        self.main.set_font_scale(self.scale_slider.value)
        
    def update_theme(self,change=None):  
        text_size = '{}px'.format(int(self.main.font_scale*16))
        if self.theme_dd.value == 'Custom': # In case of Custom CSS
            with self.main.set_dir(self.main.shell.starting_dir):
                if not os.path.isfile('custom.css'):
                    with open('custom.css','w') as f:
                        _str = dv.style_html(dv.theme_roots['Light']).replace('<style>','').replace('</style>','')
                        f.writelines(['/* Author: Abdul Saboor */'])
                        f.write(_str)
                # Read CSS from file
                with open('custom.css','r') as f:
                    theme_css = '<style>' + ''.join(f.readlines()) + '</style>'
        else:
            theme_css = dv.style_html(dv.theme_roots[self.theme_dd.value])
            
        # Replace font-size and breakpoint size
        theme_css = theme_css.replace(
                        '__text_size__',text_size).replace(
                        '__textfont__',self.main._font_family['text']).replace(
                        '__codefont__',self.main._font_family['code'])
        if self.reflow_check.value:
            theme_css = theme_css.replace('</style>','') + f".SlideArea.{self.main.uid} * "+ "{max-height:max-content !important;}\n</style>"
        
        # Zoom Container 
        if self.btn_zoom.value:
            if self.btn_fs.value:
                self.btn_zoom.icon= 'toggle-on'
                theme_css = theme_css.replace('</style>','\n') + dv.mpl_fs_css.replace('<style>','')
            else:
                self.main.notify('Objects are only zoomable in Fullscreen mode!',timeout=2)
        else:
            self.btn_zoom.icon= 'toggle-off'
        
        # Catch Fullscreen too.
        if self.btn_fs.value:
            theme_css = theme_css.replace('__breakpoint_width__','650px').replace('</style>','\n') + dv.fullscreen_css.replace('<style>','')
            self.btn_fs.icon = 'compress'
            self.main._push2sidebar(False) # Remove edit mode style safely
            
            if getattr(self.main,'box',False): # Wait for main.__init__ to complete
                for other in self.main.__class__.__slides__.values():
                    other.box.remove_class('FullScreen') # Bring them down if this goes fullscrren
                self.main.box.add_class('FullScreen') # Add this to fullscreen
            
        else:
            theme_css = theme_css.replace('__breakpoint_width__',f'{int(100*650/self.width_slider.value)}px') #Will break when slides is 650px not just window
            self.btn_fs.icon = 'expand'
            self.main._push2sidebar(self.width_slider.value) #Bring in edit mode back
            
            if getattr(self.main,'box',False): # Wait for main.__init__ to complete
                self.main.box.remove_class('FullScreen')
        
        # Now Set Theme and emit a resize event just for being smooth in GUI transformations
        for selector in ['.controls', '.SlideArea', '.SlideBox', '.ProgBox', '.panel','.LaserPointer']:
            theme_css = theme_css.replace(selector, f'{selector}.{self.main.uid}')
        
        self.main.theme_html.value = theme_css
        self.emit_resize_event()