from ipywidgets.widgets.widget_output import Output
import numpy as np
from IPython.display import display, Markdown, HTML
import ipywidgets as ipw
from ipywidgets import Layout,Label,Button,Box,HBox,VBox
from numpy.lib.function_base import iterable
from . import data_variables as dv
import datetime, re #re for updating font-size
from .utils import write 


def _custom_progressbar(intslider,uid,accent_color='red'):
    "This has a box as children[0] where you can put navigation buttons."
    html = ipw.HTML()
    uclass = 'custom-nav-'+ uid
    navclass = 'btn-'+ uid
    style_str = '''
        <style>
    .{uclass} .widget-inline-hbox .widget-readout  {{min-width:auto !important;}}
    .{uclass} {{
        z-index: 20;
        width:100%;
        right: 0px;
        left: 0px;
        vertical-align: bottom;
        height: 4px;
        overflow:hidden;
        border-radius: 0px;
        background: linear-gradient(to right, {accent_color} 0%, {accent_color} {moving_pos}%, transparent {moving_pos}%, transparent 100%) !important;
    }}
    .{uclass}:hover, .{uclass}:focus{{height: 20px;padding:auto;opacity:0.8;margin-top:-16px;}}
    .widget-inline-hbox {{border-radius;4px;}}
    
    .NavWrapper .widget-inline-hbox .widget-readout  {{z-index:30;color:inherit;
        min-width:auto !important;margin: 13.5px 2px 0px 8px;opacity:1;}}
    
    .{uclass} .ui-slider .ui-slider-handle, .{uclass} .ui-slider .ui-slider-handle:hover, .{uclass} .ui-slider .ui-slider-handle:focus {{
        background: transparent; 
        border: 5px solid {accent_color};
        height: 20px;
        width: 40px;
        margin:-1px 0px 0px 0px;
        border-radius: 0px;
    }}
     .{uclass} .ui-slider {{
         background: transparent; 
         border: transparent;
         height:18px;
     }}
     .NavWrapper .{navclass} .menu, .NavWrapper .{navclass} .menu.big-menu  {{ color:{accent_color}; font-size:24px !important; overflow:hidden;}}
     .NavWrapper .{navclass} .menu.big-menu {{font-size:55px !important;}}
     .NavWrapper .{navclass} .menu:hover {{ 
            overflow: hidden;
            animation-name: example; animation-duration: 2s;
            animation-timing-function: ease-in-out;
    }}
    @keyframes example {{
            from {{ opacity: 0.2;}}
            to {{opacity: 1;}}
    }}
    .NavWrapper .{navclass} {{z-index:50;overflow: hidden;}}
    </style><p style="margin-top:-7px;color:{accent_color};width:max-content;"><b>{text}</b></p>'''
    def update(change):
        value = np.rint((intslider.value)/intslider.max*100).astype(int)
        html.value = style_str.format(uclass = uclass, navclass=navclass, accent_color=accent_color,moving_pos=value,text=f'∕  {intslider.max}')
    intslider.observe(update)
    intslider.layout.height='16px'
    intslider.layout.margin= '-5px 2px 0px -6px'
    
    update(True) #First trigger
    return VBox([HBox(layout=Layout(height='20px',justify_content='space-between',align_items='center')).add_class(navclass),
                                    HBox([ intslider, html]).add_class(uclass) ]).add_class('NavWrapper') #class is must

class NavBar:
    def __init__(self,N=10, accent_color='red'):
        "N is number of slides here."
        self.accent_color = accent_color
        self.N = N
        
        self.uid = ''.join(np.random.randint(9, size=(20)).astype(str)) #To use in _custom_progressbar
        self.progressbar = ipw.IntSlider(max = self.N,continuous_update=False,readout=True,layout =  Layout(width='100%'))
        
        self.btn_prev =  Button(icon='angle-left',layout= Layout(width='auto',height='auto')).add_class('menu').add_class('big-menu')
        self.btn_next =  Button(icon='angle-right',layout= Layout(width='auto',height='auto')).add_class('menu').add_class('big-menu')
        self.btn_setting =  Button(icon='bars',layout= Layout(width='auto',height='auto')).add_class('menu')
        for btn in [self.btn_next, self.btn_prev, self.btn_setting]:
                btn.style.button_color= 'transparent'
                btn.layout.min_width = 'max-content' #very important parameter
                
        self.info_html = ipw.HTML('Put Your Info Here using `self.info_html.value`')
        self.group_1 =  HBox([self.btn_setting,self.info_html],
                             layout=Layout(justify_content='flex-start',align_items='center'))
        self.group_2 = HBox([self.btn_prev,self.btn_next],
                            layout=Layout(justify_content='flex-end',align_items='center',min_width='max-content'))
        self.build_navbar() # this is the main function to build the navbar
        
        self.btn_prev.on_click(self.__shift_left)
        self.btn_next.on_click(self.__shift_right)
    
    def build_navbar(self):
        self.nav_bar = _custom_progressbar(self.progressbar, self.uid, accent_color=self.accent_color)
        self.nav_bar.children[0].children = (self.group_1, self.group_2)
        self.nav_bar.children[0].layout.height = '50px'
       
    def __shift_right(self,change):
        if change:
            self.progressbar.value = (self.progressbar.value + 1) % (self.N + 1)     
    
    def __shift_left(self,change):
        if change:
            self.progressbar.value = (self.progressbar.value - 1) % (self.N + 1)
    
    def show(self):
        return self.nav_bar
        
         
class LiveSlides(NavBar):
    def __init__(self,
                 func=lambda x: display(Markdown(x)), 
                 iterable=['# First Slide','# Second Slide'],
                 accent_color='olive'):
        """Interactive Slides in IPython Notebook. Use `display(Markdown('text'))` instead of `print` in slides.
        - **Parameters**
            - func : An outside defined function which act on elements of `iterable`  and handle required situations. 
                    Return value is not guranteed for output rendering except for IPython.display.display object. Use display
                    inside the function for rich formats rending as many time as you want.
            - iterable: Anything from list/tuple/dict etc whose each element is given as argument to `func`.
            - accent_color: Valid CSS color. Applies to buttons, progressbar etc.
        - **Example**
            ```python
            from IPython.display import display, Markdown
            def fn(x):
                if isinstance(x,int):
                    display(Markdown(f'{x**2}'))
                if isinstance(x, str):
                    display(Markdown(x*10))
            slides = LiveSlides(fn, [0,2,5,'Python '],height=200)
            slides.show()
            #See result as ![Slides](https://github.com/massgh/pivotpy/tree/master/slides.gif)
            ```
        """
        self.func = func
        self.iterable = iterable
        self.user_ns = get_ipython().user_ns 
        self.accent_color = accent_color 
        self.out = ipw.Output(layout= Layout(width='auto',height='auto',margin='auto',overflow='auto',padding='2px 16px'))
        
        _max = len(self.iterable) if self.iterable else 1
        super().__init__(N=_max,accent_color=self.accent_color)
        self.theme_colors = dv.style_colors
        self.font_scale = 1 #Scale 1 corresponds to 16px
        self.theme_html = ipw.HTML(dv.style_html(dv.style_root.format(**self.theme_colors,text_size='16px')))
        self.main_style_html = ipw.HTML('''<style>
            .SlidesWrapper .textfonts { align-items: center;}
            a.jp-InternalAnchorLink { display: none !important;}
            .widget-inline-hbox .widget-readout  { min-width:auto !important;}
            .jupyterlab-sidecar .SlidesWrapper {width: 100% !important; height: 100% !important;}
            .SlidesWrapper pre, code { background:inherit !important; color: inherit !important;
                            height: auto !important; overflow:hidden;}
            .jupyterlab-sidecar .SlidesWrapper .voila-sidecar-hidden {display: none;}
            #rendered_cells .SlidesWrapper .voila-sidecar-hidden {display: none;}
            #rendered_cells .SlidesWrapper {
                position: absolute;
                width:100% !important;
                height: 100% !important;
                bottom: 0px !important;
                top: 0px !important;
                tight: 0px !important;
                left: 0px !important;
            }
            .SlidesWrapper {z-index: 10 !important;}
            <style>''')
        
        self.progressbar.observe(self.__update_content,names=['value'])
        self.__update_content(True)
        
        self.setting = Customize(self)
        self.box_setting = self.setting.box
        
        self.box =  VBox([self.main_style_html, 
                          self.theme_html,
                          HBox([self.box_setting,self.out.add_class('textfonts')
                          ],layout= Layout(width='100%',height='100%',margin='auto')),
                          self.nav_bar
                          ],layout= Layout(width=f'{self.setting.width_slider.value}vw', height=f'{self.setting.height_slider.value}px',margin='auto'))
        self.box.add_class('SlidesWrapper') #Very Important   
    
     
    def show(self):
        self.setting.theme_dd.value = 'Light' #default theme is light, also Voila makes issue with inherit theme
        try:   #JupyterLab Case, Interesting in SideCar
            from sidecar import Sidecar 
            sc = Sidecar(title='Live Presentation')
            with sc:
                display(self.box)
        except:
            return self.box
        
    def set_font_scale(self,font_scale=1):
        self.font_scale= font_scale
        self.setting.update_theme()
        
    def get_theme_colors(self):
        return self.theme_colors
    
    def set_theme_colors(self, theme_colors= None):
        if theme_colors and theme_colors.keys() == self.theme_colors.keys():
            self.theme_colors = theme_colors
            self.setting.theme_dd.value = 'Inherit' #Custom Changes only effect this mode. 
            self.setting.update_theme()   
           
    def __update_content(self,change):
        if self.iterable and change:
            self.info_html.value = self.info_html.value.replace('</p>', '| Loading...</p>')
            self.out.clear_output(wait=True)
            with self.out:
                if self.progressbar.value == 0:
                    title = self.user_ns.get('__slides_title_page','#### No Title page found. Create one using %%title in a cell.')
                    if isinstance(title,str):
                        display(Markdown(title)) #Markdown String
                    else:
                        title.show() #Ipython Captured Output
                else:
                    self.func(self.iterable[self.progressbar.value-1])
            self.info_html.value = self.info_html.value.replace('| Loading...','')
            
    def set_footer(self, text = 'Abdul Saboor | <a style="color:blue;" href="www.google.com">google@google.com</a>', show_slide_number=True, show_date=True):
        if show_date:
            text += f' | <text style="color:{self.accent_color};">' + datetime.datetime.now().strftime('%b-%d-%Y')+ '</text>'
        if show_slide_number:
            text += f' | <b style="color:{self.accent_color};">{self.progressbar.value} / {self.N}<b>'
        self.info_html.value = f'<p style="white-space:nowrap;"> {text} </p>'

class Customize:
    def __init__(self,instance_LiveSlides):
        "Provide instance of LivSlides to work."
        self.master = instance_LiveSlides
        describe = lambda value: {'description': value, 'description_width': 'initial','layout':Layout(width='auto')}
        
        self.height_slider = ipw.IntSlider(**describe('Height (px)'),min=200,max=1000, value = 500,continuous_update=False)
        self.width_slider = ipw.IntSlider(**describe('Width (vw)'),min=40,max=100, value = 65,continuous_update=False)
        self.scale_slider = ipw.FloatSlider(**describe('Font Scale'),min=0.5,max=3,step=0.0625, value = 1.0,readout_format='5.3f',continuous_update=False)
        for slider in [self.height_slider,self.width_slider,self.scale_slider]:
            slider.style.handle_color = self.master.accent_color
            
        self.theme_dd = ipw.Dropdown(**describe('Theme'),options=['Inherit','Light','Dark'])
        self.__instructions = ipw.Output(clear_output=False, layout=Layout(width='100%',height='100%',overflow='auto'))
        layout = Layout(width='100%',height='70px',margin='auto',overflow_y='hidden',align_items='center',justify_content='space-between')
        self.box = VBox([ipw.HTML('<h3>Settings</h3>'), 
                        self.height_slider.add_class('voila-sidecar-hidden'), 
                        self.width_slider.add_class('voila-sidecar-hidden'),
                        self.scale_slider,
                        self.theme_dd,
                        self.__instructions
                        ],layout=Layout(width='0px',height='100%',padding='0px',overflow='hidden'))
        with self.__instructions:
            display(Markdown(dv.settings_instructions))
            
        self.theme_dd.observe(self.update_theme)
        self.scale_slider.observe(self.__set_font_scale)
        self.height_slider.observe(self.__update_size,names=['value'])
        self.width_slider.observe(self.__update_size,names=['value'])
        self.master.btn_setting.on_click(self.__toggle_panel)
        self.update_theme() #Trigger
        
    def __update_size(self,change):
            self.master.box.layout.height = '{}px'.format(self.height_slider.value)
            self.master.box.layout.width = '{}vw'.format(self.width_slider.value)
            
    def __toggle_panel(self,change):
        if self.master.btn_setting.icon == 'bars':
            self.master.btn_setting.icon = 'close'
            self.box.layout.width = '50%'
            self.box.layout.padding = '10px'
        else:
            self.master.btn_setting.icon = 'bars'
            self.box.layout.width = '0px'
            self.box.layout.padding = '0px' 
                     
    def __set_font_scale(self,change):
        # Below line should not be in update_theme to avoid loop call.
        self.master.set_font_scale(self.scale_slider.value)
        
    def update_theme(self,change=None):  
        text_size = '{}px'.format(int(self.master.font_scale*16))
        if self.theme_dd.value == 'Inherit':
            root = dv.style_root.format(**self.master.theme_colors,text_size = text_size)
        elif self.theme_dd.value == 'Light':
            light_c = {'heading_fg': 'navy', 'text_fg': 'black', 'text_bg': '#F3F3F3', 'quote_bg': 'white', 'quote_fg': 'purple'}
            root = dv.style_root.format(**light_c,text_size = text_size)
        elif self.theme_dd.value == 'Dark':
            dark_c = {'heading_fg': 'snow', 'text_fg': 'white', 'text_bg': '#21252B', 'quote_bg': '#22303C', 'quote_fg': 'powderblue'}
            root = dv.style_root.format(**dark_c,text_size = text_size)
        self.master.theme_html.value = dv.style_html(root)   
     
    
def collect_slides():
    """Collect cells with variables `__slide_[N]` and `__next_to_[N]` in user's namespace."""
    ns = get_ipython().user_ns
    if not '__slides_mode' in ns.keys() or not ns['__slides_mode']:
        return print('Set "__slides_mode = True" in top cell and run again.')
    
    dynamic_slides = [k.replace('d','') for k in ns['__dynamicslides_dict'].keys()]
    # If slide number is mistaken, still include that. 
    all_slides = [int(k) for k in [*ns['__slides_dict'].keys(), *dynamic_slides]]
    
    try: #handle dynamic slides if empty
        _min, _max = min(all_slides), max(all_slides) + 1
    except:
        _min, _max = 0, 0
    slides_iterable = []
    for i in range(_min,_max):
        if f'{i}' in ns['__slides_dict'].keys():
            slides_iterable.append(ns['__slides_dict'][f'{i}']) 
        if f'd{i}' in ns['__dynamicslides_dict'].keys():
            slides_iterable = [*slides_iterable,*ns['__dynamicslides_dict'][f'd{i}']]
            
    return tuple(slides_iterable)

def get_cell_code(this_line=False,magics=False,comments=False,lines=None):
    "Return current cell's code in slides for educational purpose. `lines` should be list/tuple of line numbers to include if filtered."
    current_cell_code = [line.strip() for line in get_ipython().get_parent()['content']['code'].splitlines() if line]
    if isinstance(lines,(list,tuple,range)):
        current_cell_code = [line for i, line in enumerate(current_cell_code) if i+1 in lines]
    if not this_line:
        current_cell_code = [line for line in current_cell_code if 'display_cell_code' not in line]
    if not magics:
        current_cell_code = [line for line in current_cell_code if not line.lstrip().startswith('%')]
    if not comments:
        current_cell_code = [line for line in current_cell_code if not line.lstrip().startswith('#')]
    return "```python\n{}\n```".format('\n'.join(current_cell_code))

def display_cell_code(this_line=False,magics=False,comments=False,lines=None):
    "Display cell data. `lines` should be list/tuple of line numbers to include if filtered."
    code = get_cell_code(this_line=this_line,magics=magics,comments=comments,lines=lines)
    return write(code)


