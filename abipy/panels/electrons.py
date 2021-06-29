""""AbiPy panels for electronic properties."""

import param
import panel as pn
import panel.widgets as pnw

from .core import AbipyParameterized, ply, mpl, depends_on_btn_click


class SkwPanelWithFileInput(AbipyParameterized):

    def __init__(self, **params):

        super().__init__(**params)

        help_md = pn.pane.Markdown("""
This panel alllows users to upload two files with KS energies.
The first file gives the energies in the IBZ used to perform the SKW interpolation
The second file contains the enegies along a k-path.
The interpolated energies are then compared with the ab-initio ones on the k-path.
The user can change the SKW intepolation parameters to gauge the quality of the SKW fit.
        """)

        self.main_area = pn.Column(help_md,
                                   self.get_alert_data_transfer(),
                                   sizing_mode="stretch_width")

        self.ibz_file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.ibz_file_input.param.watch(self.on_ibz_file_input, "value")
        self.ebands_ibz = None

        self.kpath_file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.kpath_file_input.param.watch(self.on_kpath_file_input, "value")
        self.ebands_kpath = None

    def on_ibz_file_input(self, event):
        self.ebands_ibz = self.get_ebands_from_file_input(self.ibz_file_input)
        self.update_main_area()

    def on_kpath_file_input(self, event):
        self.ebands_kpath = self.get_ebands_from_file_input(self.kpath_file_input)
        self.update_main_area()

    def update_main_area(self):

        if self.ebands_kpath is None or self.ebands_ibz is None: return

        # SKW interpolation
        r = self.ebands_ibz.interpolate(lpratio=5, filter_params=None)

        # Build plotter.
        plotter = self.ebands_kpath.get_plotter_with("Ab-initio", "SKW interp", r.ebands_kpath)
        mpl_pane = mpl(plotter.combiplot(**self.mpl_kwargs))

        col = pn.Column(mpl_pane, sizing_mode="stretch_width")

        self.main_area.objects = [col]

    def get_panel(self):
        col = pn.Column(
            "## Upload a *nc* file with energies in the IBZ (possibly a *GSR.nc* file):",
            self.get_fileinput_section(self.ibz_file_input),
            "## Upload a *nc* file with energies along a **k**-path (possibly a *GSR.nc* file):",
            self.get_fileinput_section(self.kpath_file_input),
            sizing_mode="stretch_width")

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")

        #cls, kwds = self.get_abinit_template_cls_and_kwargs()
        #cls(main=main, **kwds)

        cls = self.get_template_cls_from_name("FastList")
        template = cls(main=main, title="SKW Analyzer", header_background="#ff8c00") # Dark orange
        return template


class CompareEbandsWithMP(AbipyParameterized):

    with_gaps = param.Boolean(True)
    ylims_ev = param.Range(default=(-10, +10), doc="Energy window around the Fermi energy.")

    def __init__(self, **params):

        super().__init__(**params)

        help_md = pn.pane.Markdown("""
This panel alllows users to upload two files with KS energies.
        """)

        self.main_area = pn.Column(help_md,
                                   self.get_alert_data_transfer(),
                                   sizing_mode="stretch_width")

        self.replot_btn = pnw.Button(name="Replot", button_type='primary')

        self.file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.file_input.param.watch(self.on_file_input, "value")
        self.mp_progress = pn.indicators.Progress(name='Fetching data from the MP website',
                                                  active=False, width=200, height=10, align="center")

    def on_file_input(self, event):
        self.abinit_ebands = self.get_ebands_from_file_input(self.file_input)

        # Match Abinit structure with MP
        mp = self.abinit_ebands.structure.mp_match()
        if not mp.structures:
            raise RuntimeError("No structure found in the MP database")

        # Get structures from MP as AbiPy ElectronBands.
        from abipy.electrons.ebands import ElectronBands
        self.mp_progress.active = True
        self.mp_ebands_list = []
        for mp_id in mp.ids:
            if mp_id == "this": continue
            eb = ElectronBands.from_mpid(mp_id)
            self.mp_ebands_list.append(eb)
        self.mp_progress.active = False

        self.update_main()

    def update_main(self):
        #col = pn.Column(sizing_mode="stretch_width")

        col = self.pws_col(["### Plot options", "with_gaps", "ylims_ev", "replot_btn"])
        ca = col.append

        ca("## Abinit Electronic band structure:")
        ylims = self.ylims_ev
        fig =  self.abinit_ebands.plotly(e0="fermie", ylims=ylims, with_gaps=self.with_gaps, show=False)
        ca(ply(fig))

        for mp_ebands in self.mp_ebands_list:
            ca("## MP Electronic band structure:")
            fig =  mp_ebands.plotly(e0="fermie", ylims=ylims, with_gaps=self.with_gaps, show=False)
            ca(ply(fig))

        #self.main_area.objects = [col]
        self.main_area.objects = col.objects

    @depends_on_btn_click('replot_btn')
    def on_replot_btn(self):
        self.update_main()

    def get_panel(self):
        col = pn.Column(
            "## Upload a *nc* file with energies along a **k**-path (possibly a *GSR.nc* file):",
            self.get_fileinput_section(self.file_input),
            pn.Row("### Fetching data from MP website: ", self.mp_progress, sizing_mode="stretch_width",
                ),
            sizing_mode="stretch_width")

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")

        #cls, kwds = self.get_abinit_template_cls_and_kwargs()
        #cls(main=main, **kwds)

        cls = self.get_template_cls_from_name("FastList")
        template = cls(main=main, title="Compare with MP Ebands", header_background="#ff8c00") # Dark orange
        return template
