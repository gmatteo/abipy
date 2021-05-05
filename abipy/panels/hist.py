""""Panels for HIST files."""
import param
import panel as pn
import bokeh.models.widgets as bkw

from abipy.panels.core import AbipyParameterized, ButtonContext, mpl, ply


_what_list = ["pressure", "forces", "energy", "abc", "angles", "volume"]


class HistFilePanel(AbipyParameterized):
    """
    Panel with widgets to interact with a |HistFile|.
    """
    what_list = pn.widgets.CheckBoxGroup(name="Select", value=_what_list, options=_what_list, inline=False)
    plot_relax_btn = pn.widgets.Button(name="Show relaxation", button_type="primary")

    sizing_mode = "stretch_width"

    appname = pn.widgets.Select(name="Viewer", value="ovito", options=["ovito", "mayavi", "vtk"])
    to_unit_cell = pn.widgets.Checkbox(name="To unit cell")
    view_relax_btn = pn.widgets.Button(name="View relaxation", button_type="primary")

    def __init__(self, hist, **params):
        super().__init__(**params)
        self.hist = hist

    def get_plot_relax_widgets(self):
        """Widgets to visualize the structure relaxation."""
        return pn.Column(self.what_list, self.sizing_mode, self.plot_relax_btn)

    @param.depends('plot_relax_btn.clicks')
    def on_plot_relax_btn(self):
        """
        Plot the evolution of structural parameters (lattice lengths, angles and volume)
        as well as pressure, info on forces and total energy.
        """
        if self.plot_relax_btn.clicks == 0: return

        with ButtonContext(self.plot_relax_btn):

            num_plots, nrows, ncols = len(self.what_list.value), 1, 1
            if num_plots > 1:
                ncols = 2
                nrows = (num_plots // ncols) + (num_plots % ncols)

            box = pn.GridBox(nrows=nrows, ncols=ncols, sizing_mode=self.sizing_mode.value) #'scale_width')
            for i, what in enumerate(self.what_list.value):
                irow, icol = divmod(i, ncols)
                box.append(mpl(self.hist.plot(what, title=what, **self.mpl_kwargs)))

            return box
            #return pn.Column(box, box.controls(jslink=True))

    @param.depends('view_relax_btn.clicks')
    def on_view_relax_btn(self):
        if self.view_relax_btn.clicks == 0: return

        with ButtonContext(self.view_relax_btn):
            return self.hist.visualize(appname=self.appname.value, to_unit_cell=self.to_unit_cell.value)

    def get_panel(self, **kwargs):
        """Return tabs with widgets to interact with the HIST.nc file."""
        tabs = pn.Tabs(); app = tabs.append

        app(("Summary", pn.Row(bkw.PreText(text=self.hist.to_string(verbose=self.verbose),
                               sizing_mode="scale_both"))))

        app(("Relaxation", pn.Row(self.get_plot_relax_widgets(),
                                 self.on_plot_relax_btn)))

        app(("Visualize", pn.Row(pn.Column(self.appname, self.to_unit_cell, self.view_relax_btn),
                                 self.on_view_relax_btn)))

        return self.get_template_from_tabs(tabs, template=kwargs.get("template", None))
