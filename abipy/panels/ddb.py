""""Panels for DDB files."""
import sys
import param
import panel as pn
import panel.widgets as pnw
import bokeh.models.widgets as bkw

from abipy.core.structure import Structure
from abipy.panels.core import (AbipyParameterized, PanelWithStructure, BaseRobotPanel,
        mpl, ply, dfc, depends_on_btn_click, Loading, ActiveBar)
from abipy.dfpt.ddb import PhononBandsPlotter


class PanelWithAnaddbParams(param.Parameterized):
    """
    Mixin for panel classes requiring widgets to invoke Anaddb via AbiPy.
    Used, for instance, by DdbFilePanel and DdbRobotPanel so that we don't have to
    repeat the same parameters over and over again.
    """

    nqsmall = param.Integer(10, bounds=(1, None), doc="Number of divisions for smallest vector to generate the q-mesh")
    ndivsm = param.Integer(5, bounds=(None, None), doc="Number of divisions for smallest vector to generate the q-path")
    lo_to_splitting = param.ObjectSelector(default="automatic", objects=["automatic", True, False])
    chneut = param.ObjectSelector(default=1, objects=[0, 1, 2], doc="Abinit variable")
    dipdip = param.ObjectSelector(default=1, objects=[0, 1, -1], doc="Abinit variable")
    # TODO: Add these widgetd but need to update anaget API.
    #dipquad = param.ObjectSelector(default=0, objects=[0, 1], doc="Abinit variable")
    #quadquad = param.ObjectSelector(default=0, objects=[0, 1], doc="Abinit variable")
    asr = param.ObjectSelector(default=2, objects=[0, 1, 2], doc="Abinit variable")
    units = param.ObjectSelector(default="eV", objects=["eV", "meV", "Ha", "cm-1", "Thz"], doc="Energy units")

    dos_method = param.ObjectSelector(default="tetra", objects=["tetra", "gaussian"], doc="Integration method for DOS")
    temp_range = param.Range(default=(0.0, 300.0), bounds=(0, 1000), doc="Temperature range in K.")

    gamma_ev = param.Number(1e-4, bounds=(1e-20, None), doc="Phonon linewidth in eV")
    w_range = param.Range(default=(0.0, 0.1), bounds=(0.0, 1.0), doc="Frequency range (eV)")

    plot_ifc_yscale = param.ObjectSelector(default="linear", objects=["log", "linear", "symlog", "logit"])

    def __init__(self, **params):
        super().__init__(**params)

        #if self.has_remote_serve:
        #    self.param.nqsmall.bounds = (1, 50)
        #    self.param.ndivsm.bounds = (-30, 30)

        # FIXME
        self.nqsmall_list = pnw.LiteralInput(name='nsmalls (python list)', value=[10, 20, 30], type=list)
        #nqqpt = pnw.LiteralInput(name='nsmalls (list)', value=[10, 20, 30], type=list)

        # Base buttons
        self.plot_check_asr_dipdip_btn = pnw.Button(name="Compute phonons with/wo ASR and DIPDIP", button_type='primary')

    def kwargs_for_anaget_phbst_and_phdos_files(self, **extra_kwargs):
        """
        Return the parameters require to invoke anaget_phbst_and_phdos_files
        Additional kwargs can be specified if needed.
        """
        d = dict(nqsmall=self.nqsmall, qppa=None, ndivsm=self.ndivsm,
                 line_density=None, asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                 dos_method=self.dos_method, lo_to_splitting=self.lo_to_splitting,
                 verbose=self.verbose, mpi_procs=self.mpi_procs)

        if extra_kwargs: d.update(extra_kwargs)

        return d


class DdbFilePanel(PanelWithStructure, PanelWithAnaddbParams):
    """
    A panel to analyze a |DdbFile|.
    Provides widgets to invoke anaddb and visualize the results.
    """

    def __init__(self, ddb, **params):
        PanelWithStructure.__init__(self, structure=ddb.structure, **params)
        PanelWithAnaddbParams.__init__(self)
        self.ddb = ddb

        # Add buttons
        self.get_epsinf_btn = pnw.Button(name="Compute", button_type='primary')
        self.plot_phbands_btn = pnw.Button(name="Plot Bands and DOS", button_type='primary')
        self.plot_eps0w_btn = pnw.Button(name="Plot eps0(omega)", button_type='primary')
        self.plot_vsound_btn = pnw.Button(name="Calculate speed of sound", button_type='primary')

        self.plot_ifc_btn = pnw.Button(name="Compute IFC(R)", button_type='primary')

        self.plot_phbands_quad_btn = pnw.Button(name="Plot PHbands with/without quadrupoles", button_type='primary')
        self.plot_dos_vs_qmesh_btn = pnw.Button(name="Plot PHDos vs Qmesh", button_type='primary')

        self.stacked_pjdos = pnw.Checkbox(name="Stacked PJDOS", value=True)

    @depends_on_btn_click('get_epsinf_btn')
    def get_epsinf(self):
        """Compute eps_infinity and Born effective charges from DDB."""

        epsinf, becs = self.ddb.anaget_epsinf_and_becs(chneut=self.chneut,
                                                       mpi_procs=self.mpi_procs, verbose=self.verbose)

        gen, inp = self.ddb.anaget_dielectric_tensor_generator(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                                                               mpi_procs=self.mpi_procs, verbose=self.verbose,
                                                               return_input=True)

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append
        #df_kwargs = dict(auto_edit=False, autosize_mode="fit_viewport")

        eps0 = gen.tensor_at_frequency(w=0, gamma_ev=self.gamma_ev)
        df_kwargs = {}

        from abipy.panels.core import MyMarkdown as m
        m = pn.pane.LaTeX
        def m(s):
            return pn.Row(pn.pane.LaTeX(s, style={'font-size': '18pt'}), sizing_mode="stretch_width")

        #ca(m(r"$\epsilon^0$ in Cart. coords (computed with Gamma_eV):"))
        ca(m(r"$\epsilon^0$ in Cart. coords:"))
        ca(dfc(eps0.get_dataframe(cmode="real"), **df_kwargs))
        ca(m(r"$\epsilon^\infty$ in Cart. coords:"))
        ca(dfc(epsinf.get_dataframe(), **df_kwargs))
        ca("## Born effective charges in Cart. coords:")
        ca(dfc(becs.get_voigt_dataframe(), **df_kwargs))
        ca("## Anaddb input file.")
        ca(pn.pane.HTML(inp._repr_html_()))

        return col

    @depends_on_btn_click('plot_eps0w_btn')
    def plot_eps0w(self):
        """Compute eps0(omega) from DDB and plot the results."""
        gen, inp = self.ddb.anaget_dielectric_tensor_generator(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                                                               mpi_procs=self.mpi_procs, verbose=self.verbose,
                                                               return_input=True)
        ws = self.w_range
        w_max = ws[1]
        if w_max == 1.0: w_max = None # Will compute w_max in plot routine from ph freqs.

        def p(component, reim):
            # Matplotlib
            #return mpl(gen.plot(w_min=ws[0], w_max=w_max, gamma_ev=self.gamma_ev, num=500, component=component,
            #                reim=reim, units=self.units, **self.mpl_kwargs))
            fig = gen.plotly(w_min=ws[0], w_max=w_max, gamma_ev=self.gamma_ev, num=500, component=component,
                              reim=reim, units=self.units, show=False)
            return ply(fig, with_help=False)

        col = pn.Column(sizing_mode='stretch_width'); ca = col.append

        # Add figures
        ca("## epsilon(w):")
        ca(p("diag", "re"))
        ca(p("diag", "im"))
        ca(p("offdiag", "re"))
        ca(p("offdiag", "im"))

        #gspec[2, :] = gen.get_oscillator_dataframe(reim="all", tol=1e-6)
        # TODO: FIX
        # TypeError: Object of type complex is not JSON serializable
        #dfc(gen.get_oscillator_dataframe(reim="all", tol=1e-6))
        ca("## Oscillator matrix elements:")
        ca(gen.get_oscillator_dataframe(reim="all", tol=1e-6))
        # Add HTML pane with input.
        ca("## Anaddb input file:")
        ca(pn.pane.HTML(inp._repr_html_()))

        #return gspec
        return col

    @depends_on_btn_click('plot_phbands_btn')
    def on_plot_phbands_and_phdos(self):
        """
        Compute phonon bands and DOS from DDB by invoking Anaddb then plot results.
        """
        # Computing phbands
        kwargs = self.kwargs_for_anaget_phbst_and_phdos_files(return_input=True)

        with self.ddb.anaget_phbst_and_phdos_files(**kwargs) as g:
            phbst_file, phdos_file = g
            phbands, phdos = phbst_file.phbands, phdos_file.phdos

            # Fill column
            col = pn.Column(sizing_mode='stretch_width'); ca = col.append

            ca("## Phonon band structure and DOS:")
            ca(ply(phbands.plotly_with_phdos(phdos, units=self.units, show=False)))

            ca("## Brillouin zone and q-path:")
            qpath_pane = ply(phbands.qpoints.plotly(show=False), with_divider=False)
            df_qpts = phbands.qpoints.get_highsym_datataframe()
            ca(pn.Row(qpath_pane, df_qpts))
            ca(pn.layout.Divider())

            ca("## Type-projected phonon DOS:")
            ca(ply(phdos_file.plotly_pjdos_type(units=self.units, stacked=self.stacked_pjdos.value, show=False)))

            ca("## Thermodynamic properties in the harmonic approximation:")
            temps = self.temp_range
            ca(ply(phdos.plotly_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50, show=False)))
            #ca(mpl(phdos_file.msqd_dos.plot(units=self.units, **self.mpl_kwargs)))
            #msqd_dos.plot_tensor(**self.mpl_kwargs)

            # Add Anaddb input file
            ca("## Anaddb input file:")
            ca(self.html_with_clipboard_btn(g.input._repr_html_()))

            return col

    @depends_on_btn_click('plot_vsound_btn')
    def plot_vsound(self):
        """
        Compute the speed of sound by fitting phonon frequencies
        along selected directions by linear least-squares fit.
        """
        col = pn.Column(sizing_mode="stretch_width"); ca = col.append

        from abipy.dfpt.vsound import SoundVelocity
        sv = SoundVelocity.from_ddb(self.ddb.filepath, num_points=20, qpt_norm=0.1,
                                    ignore_neg_freqs=True, asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                                    verbose=self.verbose, mpi_procs=self.mpi_procs)

        ca("## Linear least-squares fit:")
        ca(ply(sv.plotly(show=False)))
        ca("## Speed of sound computed along different q-directions in reduced coords:")
        ca(dfc(sv.get_dataframe()))

        return col

    @depends_on_btn_click('plot_check_asr_dipdip_btn')
    def plot_without_asr_dipdip(self):
        """
        Compare phonon bands and DOSes computed with/without the acoustic sum rule
        and the treatment of the dipole-dipole interaction in the dynamical matrix.
        Requires DDB file with eps_inf, BECS.
        """
        asr_plotter = self.ddb.anacompare_asr(asr_list=(0, 2), chneut_list=(1, ), dipdip=1,
                                              lo_to_splitting=self.lo_to_splitting,
                                              nqsmall=self.nqsmall, ndivsm=self.ndivsm,
                                              dos_method=self.dos_method, ngqpt=None,
                                              verbose=self.verbose, mpi_procs=self.mpi_procs)

        dipdip_plotter = self.ddb.anacompare_dipdip(chneut_list=(1,), asr=2, lo_to_splitting=self.lo_to_splitting,
                                                    nqsmall=self.nqsmall, ndivsm=self.ndivsm,
                                                    dos_method=self.dos_method, ngqpt=None,
                                                    verbose=self.verbose, mpi_procs=self.mpi_procs)

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append

        ca("## Phonon bands and DOS with/wo acoustic sum rule:")
        ca(ply(asr_plotter.combiplotly(show=False)))
        ca("## Phonon bands and DOS with/without the treatment of the dipole-dipole interaction:")
        ca(ply(dipdip_plotter.combiplotly(show=False)))

        return col

    @depends_on_btn_click('plot_dos_vs_qmesh_btn')
    def plot_dos_vs_qmesh(self):
        """
        Compare phonon DOSes computed with/without the inclusion
        of the dipole-quadrupole and quadrupole-quadrupole terms in the dynamical matrix.
        Requires DDB file with eps_inf, BECS and dynamical quadrupoles.
        """
        #print(self.nqsmall_list.value)
        r = self.ddb.anacompare_phdos(self.nqsmall_list.value, asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                                      dos_method=self.dos_method, ngqpt=None,
                                      verbose=self.verbose, num_cpus=1, stream=sys.stdout)

        #r.phdoses: List of |PhononDos| objects

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append
        ca("## Phonon DOSes obtained with different q-meshes:")
        ca(ply(r.plotter.combiplotly(show=False)))

        ca("## Convergence of termodynamic properties.")
        temps = self.temp_range
        ca(mpl(r.plotter.plot_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50,
                                              units=self.units, **self.mpl_kwargs)))

        return col

    @depends_on_btn_click('plot_phbands_quad_btn')
    def plot_phbands_quad(self):
        """
        Compare phonon bands and DOSes computed with/without the inclusion
        of the dipole-quadrupole and quadrupole-quadrupole terms in the dynamical matrix.
        Requires DDB file with eps_inf, BECS and dynamical quadrupoles.
        """
        plotter = self.ddb.anacompare_quad(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
                                           lo_to_splitting=self.lo_to_splitting,
                                           nqsmall=0, ndivsm=self.ndivsm, dos_method=self.dos_method, ngqpt=None,
                                           verbose=self.verbose, mpi_procs=self.mpi_procs)

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append
        ca("## Phonon Bands obtained with different q-meshes:")
        ca(ply(plotter.combiplotly(show=False)))

        return col

    @depends_on_btn_click('plot_ifc_btn')
    def on_plot_ifc(self):
        ifc = self.ddb.anaget_ifc(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip)

        kwds = self.mpl_kwargs.copy()
        kwds["yscale"] = self.plot_ifc_yscale
        print(kwds)

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append
        ca(mpl(ifc.plot_longitudinal_ifc(title="Longitudinal IFCs", **kwds)))
        ca(mpl(ifc.plot_longitudinal_ifc_short_range(title="Longitudinal IFCs short range", **kwds)))
        ca(mpl(ifc.plot_longitudinal_ifc_ewald(title="Longitudinal IFCs Ewald", **kwds)))

        return col

    def get_panel(self, as_dict=False, **kwargs):
        """
        Return tabs with widgets to interact with the DDB file.
        """
        ddb = self.ddb
        d = {}
        d["Summary"] = pn.Row(
            bkw.PreText(text=self.ddb.to_string(verbose=self.verbose), sizing_mode="scale_both")
        )

        # Note how we build tabs according to the content of the DDB.
        if ddb.has_at_least_one_atomic_perturbation():
            d["PH-bands"] = pn.Row(
                self.pws_col(["### PH-bands options", "nqsmall", "ndivsm", "asr", "chneut", "dipdip",
                              "lo_to_splitting", "dos_method", "stacked_pjdos", "temp_range", "plot_phbands_btn",
                              self.helpc("on_plot_phbands_and_phdos")]),
                self.on_plot_phbands_and_phdos
            )
        if ddb.has_bec_terms(select="at_least_one"):
            d["BECs"] = pn.Row(
                self.pws_col(["### Born effective charges options", "asr", "chneut", "dipdip", "gamma_ev",
                              "get_epsinf_btn", self.helpc("get_epsinf")]),
                self.get_epsinf
            )
        if ddb.has_epsinf_terms(select="at_least_one_diagoterm"):
            d["eps0"] = pn.Row(
                self.pws_col(["### epsilon_0", "asr", "chneut", "dipdip", "gamma_ev", "w_range", "plot_eps0w_btn",
                              self.helpc("plot_eps0w")]),
                self.plot_eps0w
            )
        if ddb.has_at_least_one_atomic_perturbation():
            d["Speed of sound"] = pn.Row(
                self.pws_col(["### Speed of sound options", "asr", "chneut", "dipdip", "plot_vsound_btn",
                             self.helpc("plot_vsound")]),
                self.plot_vsound
            )
            d["ASR & DIPDIP"] = pn.Row(
                self.pws_col(["### ASR & DIPDIP options", "nqsmall", "ndivsm", "dos_method", "plot_check_asr_dipdip_btn",
                             self.helpc("plot_without_asr_dipdip")]),
                self.plot_without_asr_dipdip
            )
            d["DOS vs q-mesh"] = pn.Row(
                self.pws_col(["### DOS vs q-mesh options", "asr", "chneut", "dipdip", "dos_method", "nqsmall_list",
                             "temp_range", "plot_dos_vs_qmesh_btn", self.helpc("plot_dos_vs_qmesh")]),
                self.plot_dos_vs_qmesh
            )
            if ddb.has_quadrupole_terms():
                d["Quadrupoles"] = pn.Row(
                    self.pws_col(["### Quadrupoles options", "asr", "chneut", "dipdip", "lo_to_splitting", "ndivsm", "dos_method",
                                  "plot_phbands_quad_btn", self.helpc("plot_phbands_quad")]),
                    self.plot_phbands_quad
                )
            d["IFCs"] = pn.Row(
                self.pws_col(["### IFCs options", "asr", "dipdip", "chneut",
                               "plot_ifc_yscale", "plot_ifc_btn", self.helpc("on_plot_ifc")]),
                self.on_plot_ifc
            )

        d["Structure"] = self.get_struct_view_tab_entry()
        d["Global"] = pn.Row(
            self.pws_col(["### Global options", "units", "mpi_procs", "verbose"]),
            self.get_software_stack()
        )

        if as_dict: return d
        return self.get_template_from_tabs(d, template=kwargs.get("template", None))


class PanelWithFileInput(AbipyParameterized):

    info_str = """
Post-process the data stored in one of the ABINIT output files.
"""

    def __init__(self, use_structure=False, **params):

        super().__init__(**params)

        self.use_structure = use_structure
        #self.with_input_gen = with_input_gen
        help_md = pn.pane.Markdown(f"""
## Description

{self.info_str}

Use the **Choose File** to upload one of the files supported by this app.
Drop one of of the files supported by AbiPy onto the FileInput area or
click the **Choose File** button to upload
Keep in mind that the **file extension matters**!
Also, avoid uploading big files (size > XXX).
""")

        self.main_area = pn.Column(help_md, sizing_mode="stretch_width")
        self.abifile = None

        self.file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.file_input.param.watch(self.on_file_input, "value")

        self.mpid_input = pnw.TextInput(name='mp-id', placeholder='Enter e.g. mp-149 for Silicon and press ⏎')
        self.mpid_input.param.watch(self.on_mpid_input, "value")
        self.mpid_err_wdg = pn.pane.Markdown("")
        #self.mp_progress = pn.indicators.Progress(name='Fetching data from the MP website', bar_color="warning",
        #                                          active=False, width=200, height=10, align="center")

    def on_file_input(self, event):
        new_abifile = self.get_abifile_from_file_input(self.file_input, use_structure=self.use_structure)

        if self.abifile is not None:
            self.abifile.remove()

        self.abifile = new_abifile
        self.main_area.objects = [self.abifile.get_panel()]

    def on_mpid_input(self, event):

        with Loading(self.mpid_input, err_wdg=self.mpid_err_wdg):
            self.abifile = Structure.from_mpid(self.mpid_input.value)

        self.main_area.objects = [self.abifile.get_panel()]

    def get_panel(self):

        if self.use_structure:
            title = "Structure Analyzer"
            msg = "## Upload (or drag & drop) **any file** with a structure (*.nc*, *.abi*, *.cif*, *.xsf*, POSCAR):"
        else:
            title = "Output File Analyzer"
            msg = "## Upload (or drag & drop) **any file** supported by AbiPy-Panel. See list below:"

        col = pn.Column(
            msg,
            self.get_fileinput_section(self.file_input),
            self.wdg_exts_with_get_panel(),
            sizing_mode="stretch_width")

        if self.use_structure:
            col.extend([
                "## or get the structure from the [Materials Project](https://materialsproject.org/) database:",
                pn.Row(self.mpid_input, pn.Column(self.mpid_err_wdg), sizing_mode="stretch_width"),
            ])

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")

        cls, kwds = self.get_abinit_template_cls_kwds()

        return cls(main=main, title=title, **kwds)


class PanelWithStructureInput(PanelWithFileInput):

    info_str = """
This application allows user to upload a file with structural info and operate on it.
"""

    def __init__(self, **params):
        super().__init__(use_structure=True, **params)


class DdbPanelWithFileInput(AbipyParameterized):

    info_str = """
This application allows users to post-process the data stored in one of the Abinit output files.
The main difference with respect to [Abinit Output File Analyzer](/outfile) is that
it is also possible to fetch the DDB file from the Materials Project Database.
"""

    def __init__(self, **params):

        super().__init__(**params)

        help_md = pn.pane.Markdown(f"""
## Description

{self.info_str}
""")

        self.main_area = pn.Column(help_md,
                                   self.get_alert_data_transfer(),
                                   sizing_mode="stretch_width")
        self.abifile = None

        self.file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.file_input.param.watch(self.on_file_input, "value")

        self.mpid_input = pnw.TextInput(name='mp-id', placeholder='Enter e.g. mp-149 for Silicon and press ⏎')
        self.mpid_input.param.watch(self.on_mpid_input, "value")
        self.mpid_err_wdg = pn.pane.Markdown("")
        #self.mp_progress = pn.indicators.Progress(name='Fetching data from the MP website', bar_color="warning",
        #                                          active=False, width=200, height=10, align="center")

    def on_file_input(self, event):
        self.mpid_err_wdg.object = ""
        new_abifile = self.get_abifile_from_file_input(self.file_input)

        if self.abifile is not None:
            self.abifile.remove()

        self.abifile = new_abifile
        self.main_area.objects = [self.abifile.get_panel()]

    def on_mpid_input(self, event):

        from abipy.dfpt.ddb import DdbFile
        with Loading(self.mpid_input, err_wdg=self.mpid_err_wdg):
            self.abifile = DdbFile.from_mpid(self.mpid_input.value)

        self.main_area.objects = [self.abifile.get_panel()]

    def get_panel(self):

        col = pn.Column(
            "## Upload (or drag & drop) a DDB file:",
            self.get_fileinput_section(self.file_input),
            "## or get the DDB from the [Materials Project](https://materialsproject.org/) database (*if available*):",
            pn.Row(self.mpid_input, pn.Column(self.mpid_err_wdg), sizing_mode="stretch_width"),
            sizing_mode="stretch_width")

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")
        cls, kwds = self.get_abinit_template_cls_kwds()

        return cls(main=main, title="DDB Analyzer", **kwds)


class CompareDdbWithMP(AbipyParameterized):

    info_str = """
This panel alllows users to upload a DDB file and compare it with the one available on the MP.
"""

    def __init__(self, **params):

        super().__init__(**params)

        help_md = pn.pane.Markdown(f"""
## Description

{self.info_str}
""")

        self.main_area = pn.Column(help_md,
                                   self.get_alert_data_transfer(),
                                   sizing_mode="stretch_width")

        self.file_input = pnw.FileInput(height=60, css_classes=["pnx-file-upload-area"])
        self.file_input.param.watch(self.on_file_input, "value")

        self.mp_progress = pn.indicators.Progress(name='Fetching DDB from the MP website', bar_color="warning",
                                                  active=False, width=100, height=10, align="center")
        self.mp_err_wdg = pn.pane.Markdown("")

    def on_file_input(self, event):
        abinit_ddb = self.get_abifile_from_file_input(self.file_input)
        from abipy.dfpt.ddb import DdbFile, DdbRobot

        # Match Abinit structure with MP.
        mp = abinit_ddb.structure.mp_match()

        with ActiveBar(self.mp_progress, err_wdg=self.mp_err_wdg):
            mpid_list = [mp_id for mp_id in mp.ids if mp_id != "this"]
            ddb_robot = DdbRobot.from_mpid_list(mpid_list)
            ddb_robot.add_file("Yours DDB", abinit_ddb)

        self.main_area.objects = [DdbRobotPanel(ddb_robot).get_panel()]

    def get_panel(self):
        col = pn.Column(
            "## Upload (or drag & drop) a DDB file:",
            self.get_fileinput_section(self.file_input),
            pn.Row("### Fetching data from the MP website: ", self.mp_progress, self.mp_err_wdg,
                   sizing_mode="stretch_width"),
            sizing_mode="stretch_width")

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")
        cls, kwds = self.get_abinit_template_cls_kwds()

        return cls(main=main, title="Compare with MP DDB", **kwds)


class DdbRobotPanel(BaseRobotPanel, PanelWithAnaddbParams):
    """
    A panel to analyze multiple DdbFiles via the low-level API provided by DdbRobot.
    Provides widgets to invoke anaddb and visualize the results.
    """
    def __init__(self, robot, **params):
        BaseRobotPanel.__init__(self, robot=robot, **params)
        PanelWithAnaddbParams.__init__(self)

        # Buttons
        self.plot_combiplot_btn = pnw.Button(name="Compute", button_type='primary')
        self.combiplot_check_btn = pnw.CheckButtonGroup(name='Check Button Group',
                                                        value=['combiplot'], options=['combiplot', 'gridplot'])

    def kwargs_for_anaget_phbst_and_phdos_files(self, **extra_kwargs):
        """Extend method of base class to handle lo_to_splitting"""
        kwargs = super().kwargs_for_anaget_phbst_and_phdos_files(**extra_kwargs)

        if kwargs["lo_to_splitting"] == "automatic":
            if any(not ddb.has_lo_to_data() for ddb in self.robot.abifiles):
                kwargs["lo_to_splitting"] = False
                if self.verbose:
                    print("Setting lo_to_splitting to False since at least one DDB file does not have LO-TO data.")

        return kwargs

    @depends_on_btn_click('plot_combiplot_btn')
    def plot_combiplot(self, **kwargs):
        """Plot phonon band structures."""
        kwargs = self.kwargs_for_anaget_phbst_and_phdos_files()

        #TODO: Recheck lo-to automatic.
        r = self.robot.anaget_phonon_plotters(**kwargs)
        #r = self.robot.anaget_phonon_plotters()

        # Fill column
        col = pn.Column(sizing_mode='stretch_both'); ca = col.append

        if "combiplot" in self.combiplot_check_btn.value:
            ca("## Combiplot:")
            ca(ply(r.phbands_plotter.combiplotly(units=self.units, show=False)))

        if "gridplot" in self.combiplot_check_btn.value:
            ca("## Gridplot:")
            # FIXME implement with_dos = True
            ca(ply(r.phbands_plotter.gridplotly(units=self.units, with_dos=False, show=False)))

        #if "temp_range" in self.combiplot_check_btn.value:
        #temps = self.temp_range.value
        #ca("## Thermodynamic properties in the harmonic approximation:")
        ##ca(phdos.plot_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50, **self.mpl_kwargs))
        #ca(ply(phdos.plotly_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50, show=False)))

        return col

    #@param.depends('get_epsinf_btn.clicks')
    #def get_epsinf(self):
    #    """Compute eps_infinity and Born effective charges from DDB."""
    #    if self.get_epsinf_btn.clicks == 0: return

    #    with ButtonContext(self.get_epsinf_btn):
    #        epsinf, becs = self.ddb.anaget_epsinf_and_becs(chneut=self.chneut,
    #                                                       mpi_procs=self.mpi_procs, verbose=self.verbose)

    #        gen, inp = self.ddb.anaget_dielectric_tensor_generator(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
    #                                                               mpi_procs=self.mpi_procs, verbose=self.verbose,
    #                                                               return_input=True)

    #        # Fill column
    #        col = pn.Column(sizing_mode='stretch_width'); ca = col.append
    #        df_kwargs = dict(auto_edit=False, autosize_mode="fit_viewport")
    #        #l = pn.pane.LaTeX

    #        eps0 = gen.tensor_at_frequency(w=0, gamma_ev=self.gamma_ev)
    #        ca(r"## $\epsilon^0$ in Cart. coords (computed with Gamma_eV):")
    #        ca(dfc(eps0.get_dataframe(cmode="real"), **df_kwargs))
    #        ca(r"## $\epsilon^\infty$ in Cart. coords:")
    #        ca(dfc(epsinf.get_dataframe(), **df_kwargs))
    #        ca("## Born effective charges in Cart. coords:")
    #        ca(dfc(becs.get_voigt_dataframe(), **df_kwargs))
    #        ca("## Anaddb input file.")
    #        ca(pn.pane.HTML(inp._repr_html_()))

    #        return col

    #@param.depends('plot_eps0w_btn.clicks')
    #def plot_eps0w(self):
    #    """Compute eps0(omega) from DDB and plot the results."""
    #    if self.plot_eps0w_btn.clicks == 0: return

    #    with ButtonContext(self.plot_eps0w_btn):
    #        gen, inp = self.ddb.anaget_dielectric_tensor_generator(asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
    #                                                               mpi_procs=self.mpi_procs, verbose=self.verbose,
    #                                                               return_input=True)
    #        ws = self.w_range
    #        w_max = ws[1]
    #        if w_max == 1.0: w_max = None # Will compute w_max in plot routine from ph freqs.

    #        def p(component, reim):
    #            return gen.plot(w_min=ws[0], w_max=w_max, gamma_ev=self.gamma_ev, num=500, component=component,
    #                            reim=reim, units=self.units, **self.mpl_kwargs)

    #        # Build grid
    #        gspec = pn.GridSpec(sizing_mode='scale_width')
    #        gspec[0, 0] = p("diag", "re")
    #        gspec[0, 1] = p("diag", "im")
    #        gspec[1, 0] = p("offdiag", "re")
    #        gspec[1, 1] = p("offdiag", "im")
    #        gspec[2, :] = gen.get_oscillator_dataframe(reim="all", tol=1e-6)
    #        # Add HTML pane with input.
    #        gspec[3, 0] = pn.pane.HTML(inp._repr_html_())

    #        return gspec

    #@param.depends('plot_phbands_btn.clicks')
    #def on_plot_phbands_and_phdos(self, event=None):
    #    """Compute phonon bands and DOSes from DDB and plot the results."""
    #    if self.plot_phbands_btn.clicks == 0: return

    #    with ButtonContext(self.plot_phbands_btn):
    #        # Computing phbands
    #        with self.ddb.anaget_phbst_and_phdos_files(
    #                nqsmall=self.nqsmall, qppa=None, ndivsm=self.ndivsm,
    #                line_density=None, asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
    #                dos_method=self.dos_method, lo_to_splitting=self.lo_to_splitting,
    #                verbose=self.verbose, mpi_procs=self.mpi_procs, return_input=True) as g:

    #            phbst_file, phdos_file = g
    #            phbands, phdos = phbst_file.phbands, phdos_file.phdos

    #        # Fill column
    #        col = pn.Column(sizing_mode='stretch_width'); ca = col.append

    #        ca("## Phonon band structure and DOS:")
    #        ca(ply(phbands.plotly_with_phdos(phdos, units=self.units, show=False)))
    #        #ca(mpl(phbands.plot_with_phdos(phdos, units=self.units, **self.mpl_kwargs)))
    #        #ca(mpl(phdos_file.plot_pjdos_type(units=self.units, exchange_xy=True, **self.mpl_kwargs)))
    #        #ca(mpl(phdos_file.msqd_dos.plot(units=self.units, **self.mpl_kwargs)))
    #        temps = self.temp_range.value
    #        ca("## Thermodynamic properties in the harmonic approximation:")
    #        #ca(phdos.plot_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50, **self.mpl_kwargs))
    #        ca(ply(phdos.plotly_harmonic_thermo(tstart=temps[0], tstop=temps[1], num=50, show=False)))
    #        #msqd_dos.plot_tensor(**self.mpl_kwargs)
    #        #self.plot_phbands_btn.button_type = "primary"

    #        # Add HTML pane with input
    #        ca("## Anaddb input file:")
    #        ca(pn.pane.HTML(g.input._repr_html_()))

    #        return col

    #@param.depends('plot_vsound_btn.clicks')
    #def plot_vsound(self):
    #    """
    #    Compute the speed of sound by fitting phonon frequencies
    #    along selected directions by linear least-squares fit.
    #    """
    #    if self.plot_vsound_btn.clicks == 0: return

    #    with ButtonContext(self.plot_vsound_btn):
    #        from abipy.dfpt.vsound import SoundVelocity
    #        sv = SoundVelocity.from_ddb(self.ddb.filepath, num_points=20, qpt_norm=0.1,
    #                                    ignore_neg_freqs=True, asr=self.asr, chneut=self.chneut, dipdip=self.dipdip,
    #                                    verbose=self.verbose, mpi_procs=self.mpi_procs)

    #        # Insert results in grid.
    #        gspec = pn.GridSpec(sizing_mode='scale_width')
    #        gspec[0, :1] = sv.get_dataframe()
    #        gspec[1, :1] = sv.plot(**self.mpl_kwargs)

    #        return gspec

    # THIS OK but I don't think it's very useful
    @depends_on_btn_click('plot_check_asr_dipdip_btn')
    def plot_without_asr_dipdip(self):
        """
        Compare phonon bands and DOSes computed with/without the acoustic sum rule
        and the treatment of the dipole-dipole interaction in the dynamical matrix.
        Requires DDB file with eps_inf, BECS.
        """
        asr_plotter = PhononBandsPlotter()
        dipdip_plotter = PhononBandsPlotter()

        for label, ddb in self.robot.items():
            asr_p = ddb.anacompare_asr(asr_list=(0, 2), chneut_list=(1, ), dipdip=1,
                                       lo_to_splitting=self.lo_to_splitting,
                                       nqsmall=self.nqsmall, ndivsm=self.ndivsm,
                                       dos_method=self.dos_method, ngqpt=None,
                                       verbose=self.verbose, mpi_procs=self.mpi_procs,
                                       pre_label=label)

            asr_plotter.append_plotter(asr_p)

            dipdip_p = ddb.anacompare_dipdip(chneut_list=(1,), asr=2, lo_to_splitting=self.lo_to_splitting,
                                             nqsmall=self.nqsmall, ndivsm=self.ndivsm,
                                             dos_method=self.dos_method, ngqpt=None,
                                             verbose=self.verbose, mpi_procs=self.mpi_procs,
                                             pre_label=label)

            dipdip_plotter.append_plotter(dipdip_p)

        # Fill column
        col = pn.Column(sizing_mode='stretch_width'); ca = col.append

        ca("## Phonon bands and DOS with/wo acoustic sum rule:")
        ca(ply(asr_plotter.combiplotly(show=False)))
        ca("## Phonon bands and DOS with/without the treatment of the dipole-dipole interaction:")
        ca(ply(dipdip_plotter.combiplotly(show=False)))

        return col

    def get_panel(self, as_dict=False, **kwargs):
        """Return tabs with widgets to interact with the DDB file."""
        robot = self.robot

        d = {}
        d["Summary"] = pn.Row(
            bkw.PreText(text=robot.to_string(verbose=self.verbose), sizing_mode="scale_both")
        )

        d["Params"] = self.get_compare_params_widgets()

        d["Plot"] = pn.Row(
            self.pws_col(["# PH-bands options",
                           "nqsmall", "ndivsm", "asr", "chneut", "dipdip",
                           "lo_to_splitting", "dos_method", "temp_range",
                           "combiplot_check_btn", "plot_combiplot_btn",
                           self.helpc("plot_combiplot")]),
            self.plot_combiplot
        )
        #app(("PH-bands", pn.Row(
        #    pn.Column("# PH-bands options",
        #              *self.pws("nqsmall", "ndivsm", "asr", "chneut", "dipdip",
        #                        "lo_to_splitting", "dos_method", "temp_range", "plot_phbands_btn",
        #                        self.helpc("on_plot_phbands_and_phdos")),
        #              ),
        #    self.on_plot_phbands_and_phdos)
        #))
        #app(("BECs", pn.Row(
        #    pn.Column("# Born effective charges options",
        #              *self.pws("asr", "chneut", "dipdip", "gamma_ev", "get_epsinf_btn",
        #                        self.helpc("get_epsinf")),
        #             ),
        #    self.get_epsinf)
        #))
        #app(("eps0", pn.Row(
        #    pn.Column("# epsilon_0",
        #              *self.pws("asr", "chneut", "dipdip", "gamma_ev", "w_range", "plot_eps0w_btn",
        #                        self.helpc("plot_eps0w")),
        #              ),
        #    self.plot_eps0w)
        #))
        #app(("Speed of sound", pn.Row(
        #    pn.Column("# Speed of sound options",
        #              *self.pws("asr", "chneut", "dipdip", "plot_vsound_btn",
        #                        self.helpc("plot_vsound")),
        #              ),
        #    self.plot_vsound)
        #))
        #d["ASR & DIPDIP"] = pn.Row(
        #    self.pws_col(["### ASR & DIPDIP options", "nqsmall", "ndivsm", "dos_method", "plot_check_asr_dipdip_btn",
        #                  self.helpc("plot_without_asr_dipdip")]),
        #    self.plot_without_asr_dipdip
        #)
        #app(("DOS vs q-mesh", pn.Row(
        #    pn.Column("# DOS vs q-mesh options",
        #              *self.pws("asr", "chneut", "dipdip", "dos_method", "nqsmall_list", "plot_dos_vs_qmesh_btn",
        #                        self.helpc("plot_dos_vs_qmesh")),
        #              ),
        #    self.plot_dos_vs_qmesh)
        #))
        #app(("Quadrupoles", pn.Row(
        #    pn.Column("# Quadrupoles options",
        #              *self.pws("asr", "chneut", "dipdip", "lo_to_splitting", "ndivsm", "dos_method", "plot_phbands_quad_btn",
        #                        self.helpc("plot_phbands_quad")),
        #              ),
        #    self.plot_phbands_quad)
        #))
        #app(("IFCs", pn.Row(
        #    pn.Column("# IFCs options",
        #              *self.pws("asr", "dipdip", "chneut", "plot_ifc_btn",
        #                        self.helpc("on_plot_ifc")),
        #              ),
        #    self.on_plot_ifc)
        #))
        d["Global"] = pn.Row(
            self.pws_col(["### Global options", "units", "mpi_procs", "verbose"]),
            self.get_software_stack()
        )

        if as_dict: return d
        return self.get_template_from_tabs(d, template=kwargs.get("template", None))


class RobotWithFileInput(AbipyParameterized):

    info_str = """
This application allows users to create an AbiPy robot to post-process
a set of ABINIT output files of the same type.
 """

    def __init__(self, **params):

        help_md = pn.pane.Markdown(f"""
 ## Description

 {self.info_str}
""")

        super().__init__(**params)

        self.main_area = pn.Column(help_md,
                                   self.get_alert_data_transfer(),
                                   sizing_mode="stretch_width")
        self.robot = None
        import os
        top = os.getcwd()
        top = "/Users/gmatteo/git_repos/abipy/abipy/data/refs/mgb2_phonons_nkpt_tsmear"
        top = "~"
        self.file_selector = pnw.FileSelector(top)
        self.robot_files_btn = pnw.Button(name="Load files", button_type='primary', sizing_mode="stretch_width")
        self.robot_files_btn.on_click(self.on_load_files)

    #@depends_on_btn_click("robot_files_btn")
    def on_load_files(self, event):
        if not self.file_selector.value: return
        #self.mpid_err_wdg.object = ""
        #new_abifile = self.get_abifile_from_file_input(self.file_input)
        #print("in on_load_files")
        #print(self.file_selector.value)

        # This should be executed only if server mode: TODO
        #if self.robot is not None:
        #    self.robot.remove()

        from abipy.abilab import abirobot
        self.robot = abirobot(self.file_selector.value)

        self.main_area.objects = [self.robot.get_panel()]

    def get_panel(self):

        # Add help section explaining how to use the filesector. See:
        # https://panel.holoviz.org/reference/widgets/FileSelector.html
        help_md = pn.pane.Markdown("""
Back (◀): Goes to the previous directory

Forward (▶): Returns to the last directory after navigating back

Up (⬆): Goes one directory up.

Address bar: Display the directory to navigate to

Enter (⬇): Navigates to the directory in the address bar

Reload (↻): Reloads the contents of the current directory

To navigate to a subfolder click on a directory in the file selector and then
hit the down arrow (⬇) in the navigation bar.
Files and folders may be selected by selecting them in the browser on the left and moving them
to the right with the arrow buttons.
""")
        col = pn.Column(
            "## Select files (all with the same extension e.g. *_DDB:)",
            self.file_selector,
            pn.Row(self.robot_files_btn, pn.Accordion(("Help", help_md), sizing_mode="stretch_width"),
                   sizing_mode="stretch_width"),
            pn.layout.Divider(),
            sizing_mode="stretch_width")

        main = pn.Column(col, self.main_area, sizing_mode="stretch_width")
        cls, kwds = self.get_abinit_template_cls_kwds()

        return cls(main=main, title="Robot Analyzer", **kwds)
