# ipyslides
Create Interactive Slides in [Jupyter](https://jupyter.org/)/[Voila](https://voila.readthedocs.io/en/stable/) with all kind of rich content. 

Launch example Notebook [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/massgh/ipyslides-voila/HEAD?urlpath=lab%2Ftree%2Fnotebooks%2Fipyslides-0-2-0.ipynb)

![Overview](overview.jpg)

# Changes in Version 0.8
- Before this version, slides were collected using global namespace, which only allowed one presentation per
notebook. Now slides are stored in local namespace, so no restriction on number of slides per notebook.
- To acheive local namespace, functions are moved under class LiveSlide and it registers magics too. So now you will
be able to use `%%slide, %%title` magics. Now you will use context managers as follows
```python
ls = LiveSlides()
ls.convert2slides(True)

with ls.title():
    ...
with ls.slide(<slide number>):
    ...
ls.insert_after(<slide number>,*objs, func)
```
- `ipyslides.initialize()` can write all above code in same cell. 
> Note: For LiveSlides('A'), use %%slideA, %%titleA, LiveSlides('B'), use %%slideB, %%titleB so that they do not overwite each other's slides.
# New in Version >= 0.7
- LiveSlides now collect slides internally, so removing a lot of code user had to put. 
- You can elevate simple cell output to fullscreen in Jupyterlab >= 3.
- You can use `with slide(<N>)` context manager to build multiple slides in for loop from a single cell. This
context manager is equivalent to `%%slide` so make sure none of them overwrite each other.

- From version >= 0.7.2, auto refresh is enabled. Whenever you execute a cell containing `write_title`, `%%slide`, `with slide` or `insert_after`, slides get updated, so no need to build again.
- From version >= 0.8.0, LiveSlides should be only in top cell as it collects slides too in local namespace.
- From Version >= 0.7.5, slides building is simplified to only single command `ipyslides.initialize()`. You can zoom in matplotlib figures embed via `ipyslides.utils.plt2html`.
# Install
```shell
> pip install ipyslides>=0.7.5
```
For development install, clone this repository and then
```shell
> cd ipyslides
> pip install -e .
```
# Demo
See a [Demo Notebook at Kaggle](https://www.kaggle.com/massgh/ipyslides),
[Version 0.2+](https://www.kaggle.com/massgh/ipyslides-0-2-0),
[Version 0.7+](https://www.kaggle.com/massgh/ipyslides-0-7). You can edit it yourself.
![Slides2Video](kaggle.gif)


> For jupyterlab >= 3, do pip install sidecar for better presenting mode.

## Content Types to Embed
You can embed anything that you can include in Jupyter notebook like ipywidgets,HTML,PDF,Videos etc.,including jupyter notebook itself! 
![JupyterLab inside ipyslides](jlabslides.gif)
> Note: Websites may refuse to load in iframe.
> Note: You can embed slides inside other slides using `ipyslides.insert_after(<N>,other_slides.box)`. This is very cool.

# Full Screen Presentation
- Use [Voila](https://voila.readthedocs.io/en/stable/) for full screen prsentations. Your notebook remains same, it is just get run by [Voila](https://voila.readthedocs.io/en/stable/).     
- Install [Jupyterlab-Sidecar](https://github.com/jupyter-widgets/jupyterlab-sidecar) for version < 4. Fullscreen support is added natively in version > 0.4!
- Version >= 0.5.1 is Jupyter Notebook theme aware in `Inherit` theme, so theme of slides changes based on editor theme.
- Version >= 0.6.3 enables full size output in Jupyterlab's `Create New Output View` command. Then in Setting panel, you can toggle fullscreen.
- Version >= 0.7.0 do not require to install sidecar or New Output view. You can make slides fullscreen just from cell output! Note that all this is currently supported only in Jupyterlab, other editors or classic notebook are not supported. 


> Very thankful to [Python-Markdown](https://python-markdown.github.io/) which enabled to create `write` command as well as syntax highliting.