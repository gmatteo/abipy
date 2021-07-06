""""Panels to interact with the AbiPy tasks."""
import param
import panel as pn
import panel.widgets as pnw
import bokeh.models.widgets as bkw

from io import StringIO
from abipy.panels.core import AbipyParameterized, mpl, ply, dfc, depends_on_btn_click


class WorkPanel(AbipyParameterized):
    """
    Panel to interact with an AbiPy Flow.
    """

    def __init__(self, work, **params):
        self.work = work
        self.flow = work.flow
        self.nids = work.node_id

        self.engine = pnw.Select(value="fdp",
                      options=['dot', 'neato', 'twopi', 'circo', 'fdp', 'sfdp', 'patchwork', 'osage'])
        self.dirtree = pnw.Checkbox(name='Dirtree', value=False)
        self.graphviz_btn = pnw.Button(name="Show graph", button_type='primary')

        self.status_btn = pnw.Button(name="Show status", button_type='primary')
        #self.task_btn = pnw.Button(name="Show Task", button_type='primary')
        ##self.work_btn = pnw.Button(name="Show Task", button_type='primary')
        self.history_btn = pnw.Button(name="Show history", button_type='primary')
        self.debug_btn = pnw.Button(name="Debug", button_type='primary')
        self.events_btn = pnw.Button(name="Events", button_type='primary')
        #self.corrections_btn = pnw.Button(name="Corrections", button_type='primary')
        self.handlers_btn = pnw.Button(name="Handlers", button_type='primary')

        #self.vars_text = pnw.TextInput(name='Abivars', placeholder='Enter list of variables separate
        #self.vars_btn = pnw.Button(name="Show Variables", button_type='primary')

        #self.dims_btn = pnw.Button(name="Show Dimensions", button_type='primary')

        #self.structures_btn = pnw.Button(name="Show Structures", button_type='primary')
        #self.structures_io_checkbox = pnw.CheckBoxGroup(
        #    name='Input/Output Structure', value=['output'], options=['input', 'output'], inline=Tru

        ## Widgets to plot ebands.
        #self.ebands_btn = pnw.Button(name="Show Ebands", button_type='primary')
        #self.ebands_plotter_mode = pnw.Select(name="Plot Mode", value="gridplot",
        #    options=["gridplot", "combiplot", "boxplot", "combiboxplot"]) # "animate",
        #self.ebands_plotter_btn = pnw.Button(name="Plot", button_type='primary')
        #self.ebands_df_checkbox = pnw.Checkbox(name='With Ebands DataFrame', value=False)
        #self.ebands_ksamp_checkbox = pnw.CheckBoxGroup(
        #    name='Input/Output Structure', value=["with_path", "with_ibz"], options=['with_path', 'w

        #TODO: Implement widget for selected_nids(flow, options),
        #radio_group = pn.widgets.RadioButtonGroup(
        #   name='Radio Button Group', options=['Biology', 'Chemistry', 'Physics'], button_type='suc

        #files = pn.widgets.FileSelector('~')

        super().__init__(**params)

    @depends_on_btn_click("status_btn")
    def on_status_btn(self):
        stream = StringIO()
        self.flow.show_status(stream=stream, nids=self.nids, verbose=self.verbose)
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    @depends_on_btn_click("history_btn")
    def on_history_btn(self):
        stream = StringIO()
        self.flow.show_history(nids=self.nids, stream=stream)
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    @depends_on_btn_click("graphviz_btn")
    def on_graphviz_btn(self):
        """
        Visualize the flow with graphviz.
        """
        node = self.task
        if self.dirtree.value:
            graph = node.get_graphviz_dirtree(engine=self.engine.value)
        else:
            graph = node.get_graphviz(engine=self.engine.value)

        return pn.Column(graph)

    @depends_on_btn_click("debug_btn")
    def on_debug_btn(self):
        #TODO https://github.com/ralphbean/ansi2html ?
        stream = StringIO()
        #flow.debug(status=options.task_status, nids=selected_nids(flow, options))
        self.flow.debug(stream=stream, nids=self.nids)
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    @depends_on_btn_click("events_btn")
    def on_events_btn(self):
        stream = StringIO()
        self.flow.show_events(nids=self.nids, stream=stream)
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    @depends_on_btn_click("corrections_btn")
    def on_corrections_btn(self):
        stream = StringIO()
        self.flow.show_corrections(stream=stream, nids=self.nids)
        #flow.show_corrections(status=options.task_status, nids=selected_nids(flow, options))
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    @depends_on_btn_click("handlers_btn")
    def on_handlers_btn(self):
        stream = StringIO()
        #if options.doc:
        #    flowtk.autodoc_event_handlers()
        #else:
        #show_events(self, status=None, nids=None, stream=sys.stdout):
        self.flow.show_event_handlers(verbose=self.verbose, nids=self.nids, stream=stream)
        return pn.Row(bkw.PreText(text=stream.getvalue()))

    #@depends_on_btn_click("vars_btn")
    #def on_vars_btn(self):
    #    if not self.vars_text.value: return
    #    varnames = [s.strip() for s in self.vars_text.value.split(",")]
    #    df = self.flow.compare_abivars(varnames=varnames, # nids=selected_nids(flow, options),
    #                                   printout=False, with_colors=False)
    #    return pn.Row(dfc(df))

    @depends_on_btn_click("dims_btn")
    def on_dims_btn(self):
        df = self.flow.get_dims_dataframe(nids=self.nids,
                                          printout=False, with_colors=False)
        return pn.Row(dfc(df), sizing_mode="scale_width")

    @depends_on_btn_click("structures_btn")
    def on_structures_btn(self):
        what = ""
        if "input" in self.structures_io_checkbox.value: what += "i"
        if "output" in self.structures_io_checkbox.value: what += "o"
        dfs = self.flow.compare_structures(nids=None, # select_nids(flow, options),
                                           what=what,
                                           verbose=self.verbose, with_spglib=False, printout=False,
                                           with_colors=False)

        return pn.Row(dfc(dfs.lattice), sizing_mode="scale_width")

    def get_panel(self, as_dict=False, **kwargs):
        """Return tabs with widgets to interact with the flow."""

        d = {}

        #row = pn.Row(bkw.PreText(text=self.ddb.to_string(verbose=self.verbose), sizing_mode="scale_
        d["Status"] = pn.Row(self.status_btn, self.on_status_btn)
        d["History"] = pn.Row(self.history_btn, self.on_history_btn)
        d["Events"] = pn.Row(self.events_btn, self.on_events_btn)
        ##d["Corrections"] = pn.Row(self.corrections_btn, self.on_corrections_btn)
        ##d["Handlers"] = pn.Row(self.handlers_btn, self.on_handlers_btn)
        ##d["Structures"] = pn.Row(pn.Column(self.structures_io_checkbox, self.structures_btn), self
        ###ws = pn.Column(self.ebands_plotter_mode, self.ebands_ksamp_checkbox, self.ebands_df_check
        ###d["Ebands"] = pn.Row(ws, self.on_ebands_btn)
        ###d["Abivars"] = pn.Row(pn.Column(self.vars_text, self.vars_btn), self.on_vars_btn)
        ###d["Dims"] = pn.Row(pn.Column(self.dims_btn), self.on_dims_btn)
        ##d["Debug"] = pn.Row(self.debug_btn, self.on_debug_btn)
        d["Graphviz"] = pn.Row(pn.Column(self.engine, self.dirtree, self.graphviz_btn), self.on_graphviz_btn)

        if as_dict: return d

        return self.get_template_from_tabs(d, template=kwargs.get("template", None), closable=False)
