# Changelog
Content below assumes you have `ls = LiveSlides()`.

# 1.4.0
Use `ls.load_docs()` to see updated documentation for this and above versions. No more changelogs will be created.
# 1.3.9
- Use `ls.css_styles` to get a list of predefined CSS classes to use in argument `className` of writing/formatting functions. 
- Use `className = 'Right RTL'` to type right to left langauges in correct format. 
- Use `ls.vspace(em = <int,float>) to have vertical spacings in unit of em. (1em = 1 text line height). Useful to adjust content.
- Bugs fixes. 

# 1.3.7/8
- Use `ls.settings.set_layout(content_width='<N>%')` to display slides in a desired width. This will not change with in small devices.
- Bugs fixes. 

# 1.3.6
- Use `ls.pre_compute_display()` to load all slides into memory. This is useful if you have a lot of Maths or Widgets.
- You can use some predefined classed like `Info, Warning, Success, Error` in `write` command to have special colored messages. 
# 1.3.4/5
- Demo is under main class now. Access as `ls.demo()`. 
- `@ls.frames` now accept `repeat` arguement to design frames in different ways. See `ls.demo()` slides. 
- Now contet on slides is updated in real time on cell execution, so you see the result of you just ran. 
- `@ls.notify_at` is deprecated in favor of `@ls.notify_later` which does not require you to give slide number, picks current slide number under which itb is run. Under `@ls.frames`, notifications are shown on first frame only.
- `ls.notes.insert` now work under `@ls.frames`and notes are shown on first frame only.
- Bugs in PDF printing and some other places fixed.

# 1.3.3
- Added `ls.close_view` method, which closes widgets view but available on next run. 
- You will get warning if running slides in two or more notebooks in Jupyterlab, because keyboard navigation and CSS does not behave well when two slides are in single browser's tab. In that case, you don't need to delete slides, just call `ls.close_view()` to remove unwanted displays from frontend.
- Slide navigation slider (hover between two buttons to see) now displays actual slide number. 
- Javascript optimzations for single instnace of slides. 
- Bug fixes

# 1.3.2
- You can now load slides from a markdown file/StringIO object using `ls.from_markdown` and later edit or use it's content in combination with other type of contents using `ls.md_content` attribute. 
```python
ls.from_markdown(path)
with ls.slide(2):
    write(ls.md_content[2]) # write content of slide 2 from file
    plot_something() # Add other things to same file
    write_something()
```
- `ipyslides.initialize` is depreacted in favor of `ipyslides.LiveSlides.from_markdown`.
- Each time you run `LiveSlides` or `ipyslides.demo` command, you will get same instance without throwing any error. 
- When you call `ls.show()` or `ls` on last line of cell, other displays will be cleared in favor of smooth keyboard interactions via javascript. 
# 1.3.1
- Use `ls.settings.set_code_style(style,background)` to set any style available in `pygments` module. 
```python
ls.settings.set_code_style('material','#003')
```
![Code Sample](code_sample.png)
- Almost every utility object like `image`,`svg`, `doc`, etc. is an HTML object which can autodisplay on last line of cell. 
- Bugs fixes.
# 1.3.0 (Single Instance Restriction)
Now there exists only one instance of `LiveSlides` per notebook. Multiple instnaces do not behave well with each other and as we see almost every presentation software is one presentation per file, so is `ipyslides` now. You can still create it from markdown file or import a previously created presentation.
## Notable Change
- `LiveSlides` now does not accept any argument because single instance can not be modified later. Parameters are transferred to corresponding functions in `ls.settings`. 
- Functionality is modularized now. most commnads starting with `set` are now accessible as `ls.settings.<set_function>`. 
    - Printing functions are under `ls.print.<function>`
    - Notes can be added using `ls.notes.insert` now. 
    - Other functionality is available as `ls.<function>` like `ls.write`, `ls.source` etc.
    - `ls.clear` cleans up all slides. You can rerun cells to fill up content. 

```python
ls = LiveSlides()
ls.settings.set_logo(...)
ls.settings.set_animation('zoom')
ls.notes.insert('Slide Notes')
ls.print.screenshots # returns all captured images
ls.notify(...)
```


# 1.2.1
- Speaker Notes are added inside notebook as well, so in case you are sharing slides area of notebook in softwares like Zoom, Google Meets etc., that will be useful. No need to check `Show Notes` in this case. 
- Miscalleneous bug fixes. 
# 1.2.0
### Speaker Notes 
- You can turn on speaker notes with a `Show Notes` check in side panel. Notes can be added to slides using `ls.notes` command. 
- Notes is an experimantal feuture, so use at your own risk. Do not share full screen, share a brwoser tab for slides and you can keep notes hidden from audience this way. 
### Source Overhauled
- `ls.source` is now to include sources from `strings`, `files`, and objects like `class, module, function`.  etc
Resulting object a widget that can be passed to both `write`, `iwrite` commands. Now use this to retrive a code block:
```python
with ls.source.context() as s:
    ...
    iwrite(s) # auto updates inside context manager in iwrite
write(s) # Can be only accessed outside conetext for other uses
```
`ls.source.from_[file,string,callable]` are other available functions and `ls.source.current` gives currently available source. 
You can show other languages' code from file/strings as well. 


### Other changes 
- `ls.enum_slides`, `ls.repeat` are removed.
- Added `ls.format_css` function, you can add a `className` in `[i]write` commnads and use CSS inside this. 


# 1.1.0
- Commnd `iwrite` now returns a displayed grid and references to objects passed. So you can update live things on slides (see `ipyslides.demo` for it). It now accept other objects like matplotlib's figure etc.
```python
grid, x = iwrite('X') 
grid, (x,y) = iwrite('X','Y')
grid, (x,y) = iwrite(['X','Y'])
grid, [(x,y),z] = iwrite(['X','Y'],'Z')
#We unpacked such a way that we can replace objects with new one using `grid.update`
new_obj = grid.update(x, 'First column, first row with new data') #You can update same `new_obj` withit's own widget methods.
```
- `ls.source` is now an HTML widget, so it can update itself within context manager block when written inside `iwrite` command. Same widget can be passed to `write` command but will not be updated.
- `ls.get_cell_code` is no more there in favor for `ls.source`.
- `ls.fmt2cols` is renamed to `ls.format_html` and expanded to any number of objects/columns. Result can be passed to both writing commands. `ls.ihtml` is deprecated for same reason. Just a single function is okay.
# 1.0.9
- `ls.source` now let you capture source code into a variable and do not show bydefault, but this way you can write source code anywhere you want. 
```python
with ls.source() as src:
    x = do_something()
write(x,src) #will be displayed in two side by side columns, it was not that flexible before
```
- Even if you do not explicitly assign `ls.source() as s:`, you can still access current code block using `ls.current_source`. 
- `ls.get_cell_code` will be deprecated in future in favor of verstile `ls.source`.
- Theming is modified a little bit and a new `Fancy` theme is added. 
- Bug fixes and improvements in CSS. 
# 1.0.7 
- Layout/Functionality is fixed for [RetroLab](https://github.com/jupyterlab/retrolab) which will be base for classical notebook version 7 in future.
- `ls.sig(callable)` displays signature and `ls.doc(callable)` display signature alongwith docs in contrast to `write(callable)` directly which displays code as well. 

# 1.0.5
- `ls.image` now accepts `im = PIL.Image.open('path')` object and displays if `im` is not closed. You can display `numpy.array` from `numpy` or `opencv` image by converting it to `PIL.Image.fromarry(array)` or using `plt.imshow(array)` on it and then `write(plt.gcf())`. 
- `html_node` (`html` in 1.4+) function is added to separaetly add HTML without parsing it. It can display itself if on the last line of notebook's cell or can be passed to `write`,`iwrite` commands as well.

# 1.0.4
- Laser pointer ???? is added, you can customize it's color in custom theme. 
- `ipyslides.initialize`(deprecated in 1.3.2) now has argument `markdown_file`. You can write presentation from a markdown file. Slides separator is `---` (three dashes). For example:
```
_________ Markdown File Content __________
# Talk Title
---
# Slide 1 
---
# Slide 2
___________________________________________
```
This will create two slides along with title page. 
- `ls.enable_zoom(object)` will zoom that object when hovered on it while `Zoom Items` button is ON (or `Z` pressed in Jupyterlab)
- `ls.raw` will print a string while preserving whitspaces and new lines. 
- `ls.svg`,`ls.image`(ls.file2image is just an alias now for ls.image) can now take url or data to display image.
- `ls.repeat` (dropped in 1.2.0) can be used to remind you of something via notification at given time interval. You can infact create a timer with combination of `ls.repeat` and `ls.notify`. 
- Besides just matplotlib's figure, now everything inside `ls.image`, `ls.svg`,`ls.enable_zoom` will go full screen on hover with `Zoom Items` toggle button ON. 

# 1.0.3
- Now you can send notificatios based on slide using `@ls.notify_at` decorator. This is dynamic operation, so if you need to show time during slides(look at demo slide), it will show current time. Notifications are hidden during screenshot by app's mechanism, not external ones. You can turn ON/OFF notifications from settings panel. 
- Use `Save PNG` button to save all screenshots in a folder in sequence. You can create a `Powerpoint Presentation` from these picture by following instructions in side panel or from the generated file `Make-PPT.md` along pictures.
# 1.0.2
- Javascript navigation works now after browser's refresh.
- User can now decide whether to display slides inline or in sidebar using a button in Jupyterlab. (Sorry other IDEs, you are not flexible to do this, use Voila in that case.)
- Multiple views of slides can capture keyboard events separately.
- All instances of LivSlides are now aware of each other for theme switch and inline/sidebar toggle. If one instance go in sidebar, others fall to inline. If one go fullscreen, others go minimized. 
- Bugs fixed and improvements added.
# 1.0.1
- Animations now have slide direction based on going left or right. `ipysides.data_variables.animations` now have `slide_h` and `slide_v` for horizontal and vertical sliding respectively. 
- You can now set text and code fonts using `ls.set_font_family(text_font, code_font)`.
- Many bugs fixed including Voila's static breakpoint. 
# 1.0.0 
- `ipyslides.initialize(**kwargs)` now returns a `LiveSlides` instance instead of changing cell contents. This works everywhere including Google Colab.
- `LiveSlides`,`initialize` and  `init` cause exit from a terminal which is not based on `IPython`.
- Markdown and other than slides output now does not appear (height suppressed using CSS) in Voila.
- Keyboard vavigation now works in Voila. (Tested on Voila == 0.2.16) 
- Test and add slides bounding box form slides left panel's box using `L,T,R,B` input and see screenshot immediately there. This is in addition and independent to `ls.set_print_settings(bbox)`.

# 0.9.9
- Javascript navigation is improved for Jupyterlab.
- The decorator `ls.slides` is renamed as `ls.frames` and now it adds one slide with many frames. This is useful to reveal slide contents in steps e.g. bullet points one by one.
# 0.9.8
- PDF printing is optimized. See [PDF-Slides](IPySlides-Print.pdf). You can hover over top right corner to reveal a slider to change view area while taking screenshot. Also you can select a checkbox from side panel to remove scrolling in output like code.
- You can now display source code using context manager `slides.source` (later `slides.source.context`).
- You can (not recommended) use browser's print PDF by pressing key `P` in jupyterlab but it only gives you current slide with many limitations, e.g. you need to collect all pages manually.

# 0.9.6
- Code line numbering is ON by default. You can set `ls.code_lineno(False)` to turn OFF.
- Add slides in for loop using `slides.enum_slides` (later deprecated)function. It create pairs of index and slides. 
#### PDF Printing (Tested on Windows)
- PDF printing is now available. Always print in full screen or set `bbox` of slides. Read instructions in side panel. [PDF-Slides](IPySlides-Print.pdf)

# 0.9.5
- You can now give `function/class/modules` etc. (without calling) in `write` and source code is printed.
- Objects like `dict/set/list/numpy.ndarray/int/float` etc. are well formatted now.
- Any object that is not implemented yet returns its `__repr__`. You can alternatively show that object using `display` or library's specific method. 

# 0.9.4
- Now you can set logo image using `ls.set_logo` function (later `ls.settings.set_logo`).
- LaTeX's Beamer style blcoks are defined. Use `ls.block(...,bg='color')`, or with few defined colors like `ls.block_r`, `ls.block_g` etc.
- `@ls.slides` (later `ls.frames`) no more support live calculating slides, this is to avoid lags while presenting. 
# 0.9.3
- Add custom css under %%slide as well using `ls.write_slide_css`.
- Slides now open in a side area in Jupyterlab, so editing cells and output can be seen side by side. No more need of Output View or Sidecar.
## 0.9.1
- In Jupyterlab (only inline cell output way), you can use `Ctrl + Shift + C` to create consoles/terminals, set themes etc.
- Use `Ctrl + Shift + [`, `Ctrl + Shift + ]` to switch back and forth between notebooks/console/terminals and enjoy coding without leaving slides!

## 0.8.11
- All utilities commnads are now under `LiveSlides` class too, so you can use either 
`ipyslides.utils.command` or `ls.command` for `command` in `write`,`iwrite` etc.
## 0.8.10
- You can add two slides together like `ls1 + ls2`, title of `ls2` is converted to a slide inplace (dropped in 1.3.0). 
- You can now change style of each slide usig `**css_props` in commands like `@ls.slides`, `with ls.slide` and `with ls.title`. 
- A new command `textbox` is added which is useful to write inline references. Same can be acheived with `slides.cite(...here=True)`. 
- You can use `ls.alert('text')`, `ls.colored('text',fg,bg)` to highlight text.

## 0.8.7
- Support added for objects `matplotlib.pyplot.Figure`, `altair.Chart`, `pygal.Graph`, `pydeck.Deck`, `pandas.DataFrame`, `bokeh.plotting.Figure` to be directly in `write` command.
- `write` command now can accept `list/tuple` of content, items are place in rows.
## 0.8.5
- `@ls.slides(...,calculate_now=True)` (`ls.frames` in recent versions) could be used to calculate slides in advance or just in time. Default is `True`. 
- You can now use `ipyslides.utils.iwrite` to build complex layout of widgets like ipywidgets, bqplot etc. (and text using `ipyslides.utils.ihtml`(deprecated later, write directly)).  

## 0.8.3
- You can now use `ls.cite` method to create citations which you can write at end by `ls.write_citations` command.
- `ls.insert_after` no longer works, use 
```python
@ls.slides(after_slide_number,*objs)
def func(obj):
    write(obj) #etc. for each obj in objs
```
decorator which is more pythonic way. 
## 0.8.0 +
> Note: All these points may not or only partially apply to earlier versions. So use stable API above version 8.
- Before this version, slides were collected using global namespace, but now are stored in local namespace.
- To acheive local namespace, functions are moved under class `LiveSlide` and it registers magics too. So now you will
be able to use `%%slide, %%title` magics. Now you will use context managers as follows
```python
ls = LiveSlides()
ls.convert2slides(True)

with ls.title():
    ...
with ls.slide(<slide number>):
    ...
```

- `with ls.slide` content manager is equivalent to `%%slide` so make sure none of them overwrite each other.

- Auto refresh is enabled. Whenever you execute a cell containing `%%title`, `with ls.title`, `%%slide`, `with ls.slide`  slides get updated automatically.
- LiveSlides should be only in top cell. As it collects slides in local namespace, it can not take into account the slides created above itself.
