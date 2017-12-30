# coding: utf-8
"""
Utilities for generating matplotlib plots.

.. note::

    Avoid importing matplotlib in the module namespace otherwise startup is very slow.
"""
from __future__ import print_function, division, unicode_literals, absolute_import

import os
import collections
import numpy as np

from monty.string import list_strings
from monty.functools import lazy_property
from pymatgen.util.plotting import add_fig_kwargs, get_ax_fig_plt, get_ax3d_fig_plt, get_axarray_fig_plt


__all__ = [
    "set_axlims",
    "get_ax_fig_plt",
    "get_ax3d_fig_plt",
    "plot_array",
    "ArrayPlotter",
    "data_from_cplx_mode",
    "Marker",
]


def set_axlims(ax, lims, axname):
    """
    Set the data limits for the axis ax.

    Args:
        lims: tuple(2) for (left, right), tuple(1) or scalar for left only.
        axname: "x" for x-axis, "y" for y-axis.

    Return: (left, right)
    """
    left, right = None, None
    if lims is None: return (left, right)

    len_lims = None
    try:
        len_lims = len(lims)
    except TypeError:
        # Asumme Scalar
        left = float(lims)

    if len_lims is not None:
        if len(lims) == 2:
            left, right = lims[0], lims[1]
        elif len(lims) == 1:
            left = lims[0]

    set_lim = getattr(ax, {"x": "set_xlim", "y": "set_ylim"}[axname])
    set_lim(left, right)

    return left, right


def data_from_cplx_mode(cplx_mode, arr):
    """
    Extract the data from the numpy array `arr` depending on the values of `cplx_mode`.

    Args:
        cplx_mode: Possible values in ("re", "im", "abs", "angle")
            "re" for the real part,
            "im" for the imaginary part.
            "abs" means that the absolute value of the complex number is shown.
            "angle" will display the phase of the complex number in radians.
    """
    if cplx_mode == "re": return arr.real
    if cplx_mode == "im": return arr.imag
    if cplx_mode == "abs": return np.abs(arr)
    if cplx_mode == "angle": return np.angle(arr, deg=False)
    raise ValueError("Unsupported mode `%s`" % str(cplx_mode))


@add_fig_kwargs
def plot_xy_with_hue(data, x, y, hue, decimals=None, ax=None,
                     xlims=None, ylims=None, fontsize=12, **kwargs):
    """
    Plot y = f(x) relation for different values of `hue`.
    Useful for convergence tests done wrt to two parameters.

    Args:
        data: DataFrame containing columns `x`, `y`, and `hue`.
        x: Name of the column used as x-value
        y: Name of the column used as y-value
        hue: Variable that define subsets of the data, which will be drawn on separate lines
        decimals: Number of decimal places to round `hue` columns. Ignore if None
        ax: matplotlib :class:`Axes` or None if a new figure should be created.
        xlims ylims: Set the data limits for the x(y)-axis. Accept tuple e.g. `(left, right)`
                     or scalar e.g. `left`. If left (right) is None, default values are used
        fontsize: Legend fontsize.
        kwargs: Keywork arguments are passed to ax.plot method.

    Returns:
        `matplotlib` figure.
    """
    # Check here because pandas messages are a bit criptic.
    miss = [k for k in (x, y, hue) if k not in data]
    if miss:
        raise ValueError("Cannot find `%s` in dataframe.\nAvailable keys are: %s" % (str(miss), str(data.keys())))

    # Truncate values in hue column so that we can group.
    if decimals is not None:
        data = data.round({hue: decimals})

    ax, fig, plt = get_ax_fig_plt(ax=ax)
    for key, grp in data.groupby(hue):
        xvals, yvals = grp[x], grp[y]
        label = "{} = {}".format(hue, key)
        if not kwargs:
            ax.plot(xvals, yvals, 'o-', label=label)
        else:
            ax.plot(xvals, yvals, label=label, **kwargs)

    ax.grid(True)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    set_axlims(ax, xlims, "x")
    set_axlims(ax, ylims, "y")
    ax.legend(loc="best", fontsize=fontsize, shadow=True)

    return fig


@add_fig_kwargs
def plot_array(array, color_map=None, cplx_mode="abs", **kwargs):
    """
    Use imshow for plotting 2D or 1D arrays.

    Example::

        plot_array(np.random.rand(10,10))

    See <http://stackoverflow.com/questions/7229971/2d-grid-data-visualization-in-python>

    Args:
        array: Array-like object (1D or 2D).
        color_map: color map.
        cplx_mode:
            Flag defining how to handle complex arrays. Possible values in ("re", "im", "abs", "angle")
            "re" for the real part, "im" for the imaginary part.
            "abs" means that the absolute value of the complex number is shown.
            "angle" will display the phase of the complex number in radians.

    Returns:
        `matplotlib` figure.
    """
    # Handle vectors
    array = np.atleast_2d(array)
    array = data_from_cplx_mode(cplx_mode, array)

    import matplotlib as mpl
    from matplotlib import pyplot as plt
    if color_map is None:
        # make a color map of fixed colors
        color_map = mpl.colors.LinearSegmentedColormap.from_list('my_colormap',
                                                                 ['blue', 'black', 'red'], 256)

    img = plt.imshow(array, interpolation='nearest', cmap=color_map, origin='lower')

    # Make a color bar
    plt.colorbar(img, cmap=color_map)

    # Set grid
    plt.grid(True, color='white')

    fig = plt.gcf()
    return fig


class ArrayPlotter(object):

    def __init__(self, *labels_and_arrays):
        """
        Args:
            labels_and_arrays: List [("label1", arr1), ("label2", arr2")]
        """
        self._arr_dict = collections.OrderedDict()

        for label, array in labels_and_arrays:
            self.add_array(label, array)

    def __len__(self):
        return len(self._arr_dict)

    def __iter__(self):
        return self._arr_dict.__iter__()

    def keys(self):
        return self._arr_dict.keys()

    def items(self):
        return self._arr_dict.items()

    def add_array(self, label, array):
        """Add array with the given name."""
        if label in self._arr_dict:
            raise ValueError("%s is already in %s" % (label, list(self._arr_dict.keys())))

        self._arr_dict[label] = array

    def add_arrays(self, labels, arr_list):
        """
        Add a list of arrays

        Args:
            labels: List of labels.
            arr_list: List of arrays.
        """
        assert len(labels) == len(arr_list)
        for label, arr in zip(labels, arr_list):
            self.add_array(label, arr)

    @add_fig_kwargs
    def plot(self, cplx_mode="abs", color_map="jet", **kwargs):
        """
        Args:
            cplx_mode: "abs" for absolute value, "re", "im", "angle"
            color_map: matplotlib colormap
        """
        # Build grid of plots.
        num_plots, ncols, nrows = len(self), 1, 1
        if num_plots > 1:
            ncols = 2
            nrows = num_plots // ncols + (num_plots % ncols)

        import matplotlib.pyplot as plt
        fig, axmat = plt.subplots(nrows=nrows, ncols=ncols, sharex=False, sharey=False, squeeze=False)
        # don't show the last ax if num_plots is odd.
        if num_plots % ncols != 0: axmat[-1, -1].axis("off")

        from mpl_toolkits.axes_grid1 import make_axes_locatable
        from matplotlib.ticker import MultipleLocator

        for ax, (label, arr) in zip(axmat.flat, self.items()):
            data = data_from_cplx_mode(cplx_mode, arr)
            # use origin to place the [0,0] index of the array in the lower left corner of the axes.
            #img = ax.imshow(data, interpolation='nearest', cmap=color_map, origin='lower', aspect="auto")
            img = ax.matshow(data, interpolation='nearest', cmap=color_map, origin='lower', aspect="auto")
            #img = ax.matshow(data, cmap=color_map)

            ax.set_title(label + " (%s)" % cplx_mode)

            # Make a color bar for this ax
            # Create divider for existing axes instance
            # http://stackoverflow.com/questions/18266642/multiple-imshow-subplots-each-with-colorbar
            divider3 = make_axes_locatable(ax)
            # Append axes to the right of ax, with 10% width of ax
            cax3 = divider3.append_axes("right", size="10%", pad=0.05)
            # Create colorbar in the appended axes
            # Tick locations can be set with the kwarg `ticks`
            # and the format of the ticklabels with kwarg `format`
            cbar3 = plt.colorbar(img, cax=cax3, ticks=MultipleLocator(0.2), format="%.2f")
            # Remove xticks from ax
            ax.xaxis.set_visible(False)
            # Manually set ticklocations
            #ax.set_yticks([0.0, 2.5, 3.14, 4.0, 5.2, 7.0])

            # Set grid
            ax.grid(True, color='white')

        fig.tight_layout()
        return fig


class Marker(collections.namedtuple("Marker", "x y s")):
    """
    Stores the position and the size of the marker.
    A marker is a list of tuple(x, y, s) where x, and y are the position
    in the graph and s is the size of the marker.
    Used for plotting purpose e.g. QP data, energy derivatives...

    Example::

        x, y, s = [1, 2, 3], [4, 5, 6], [0.1, 0.2, -0.3]
        marker = Marker(x, y, s)
        marker.extend((x, y, s))

    """
    def __new__(cls, *xys):
        """Extends the base class adding consistency check."""
        if not xys:
            xys = ([], [], [])
            return super(cls, Marker).__new__(cls, *xys)

        if len(xys) != 3:
            raise TypeError("Expecting 3 entries in xys got %d" % len(xys))

        x = np.asarray(xys[0])
        y = np.asarray(xys[1])
        s = np.asarray(xys[2])
        xys = (x, y, s)

        for s in xys[-1]:
            if np.iscomplex(s):
                raise ValueError("Found ambiguous complex entry %s" % str(s))

        return super(cls, Marker).__new__(cls, *xys)

    def __bool__(self):
        return bool(len(self.s))

    __nonzero__ = __bool__

    def extend(self, xys):
        """
        Extend the marker values.
        """
        if len(xys) != 3:
            raise TypeError("Expecting 3 entries in xys got %d" % len(xys))

        self.x.extend(xys[0])
        self.y.extend(xys[1])
        self.s.extend(xys[2])

        lens = np.array((len(self.x), len(self.y), len(self.s)))
        if np.any(lens != lens[0]):
            raise TypeError("x, y, s vectors should have same lengths but got %s" % str(lens))

    def posneg_marker(self):
        """
        Split data into two sets: the first one contains all the points with positive size.
        the first set contains all the points with negative size.
        """
        pos_x, pos_y, pos_s = [], [], []
        neg_x, neg_y, neg_s = [], [], []

        for x, y, s in zip(self.x, self.y, self.s):
            if s >= 0.0:
                pos_x.append(x)
                pos_y.append(y)
                pos_s.append(s)
            else:
                neg_x.append(x)
                neg_y.append(y)
                neg_s.append(s)

        return Marker(pos_x, pos_y, pos_s), Marker(neg_x, neg_y, neg_s)


#class Node(object):
#    def __init__(self, path):
#        self.path = path
#        self.basename = os.path.basename(path)
#        self.isdir = os.path.isdir(self.path)
#        self.isfile = os.path.isfile(self.path)
#
#    def __eq__(self, other):
#        if not isinstance(other, self.__class__): return False
#        return self.path == other.path
#
#    def __ne__(self, other):
#        return not self.__eq__(other)
#
#    def __hash__(self):
#        return hash(self.path)
#
#
#class FileNode(Node):
#    color = np.array((255, 0, 0)) / 255
#
#
#class DirNode(Node):
#    color = np.array((0, 0, 255)) / 255
#
#    @lazy_property
#    def isempty(self):
#        """True if empty directory."""
#        return bool(os.listdir(self.path))
#
#
#class DirTreePlotter(object):
#
#    def __init__(self, top):
#        self.top = os.path.abspath(top)
#        self.build_graph()
#
#    def build_graph(self):
#        import networkx as nx
#        g = nx.Graph()
#        g.add_node(DirNode(self.top))
#
#        for root, dirs, files in os.walk(self.top):
#            for dirpath in dirs:
#                dirpath = os.path.join(root, dirpath)
#                head, basename = os.path.split(dirpath)
#                node = DirNode(dirpath)
#                g.add_node(node)
#                g.add_edge(DirNode(head), node)
#
#            for f in files:
#                filepath = os.path.join(root, f)
#                node = FileNode(filepath)
#                g.add_node(node)
#                g.add_edge(DirNode(os.path.dirname(filepath)), node)
#
#        self.graph = g
#
#    @add_fig_kwargs
#    def plot(self, filter_ends=None, ax=None, **kwargs):
#        """
#        Plot directory tree with files
#
#        Args:
#            filter_ends: List of file extensions (actually file ends) that should be displayed.
#                If None, all files are displayed
#            ax: matplotlib :class:`Axes` or None if a new figure should be created.
#
#        Returns:
#            `matplotlib` figure.
#        """
#        ax, fig, plt = get_ax_fig_plt(ax=ax)
#        fixed, initial_pos = None, None
#        fixed = True
#        arrows = False
#
#        g = self.graph
#        if filter_ends:
#            filter_ends = list_strings(filter_ends)
#            g = self.graph.subgraph([n for n in self.graph.nodes() if n.isdir # and not n.isempty)
#                or (n.isfile and any(n.basename.endswith(e) for e in filter_ends))])
#
#        if arrows:
#            g = nx.convert_to_directed(g)
#
#        top = self.top
#        top_nodes = [DirNode(os.path.join(top, d)) for d in os.listdir(top) if os.path.isdir(os.path.join(top, d))]
#        #print("top_nodes", top_nodes)
#        import networkx as nx
#        t = nx.Graph()
#        t.add_nodes_from(top_nodes)
#        initial_pos = nx.circular_layout(t)
#
#        # Get positions for all nodes using layout_type.
#        # e.g. pos = nx.spring_layout(g)
#        #layout_type = "spring"
#        #pos = getattr(nx, layout_type + "_layout")(g)
#
#        pos = nx.spring_layout(g, iterations=50, fixed=top_nodes, pos=initial_pos)
#
#        nx.draw_networkx(g, pos,
#                         labels={n: n.basename for n in g.nodes()},
#                         node_color=[n.color for n in g.nodes()],
#                         #node_size=[make_node_size(task) for task in g.nodes()],
#                         #node_size=50,
#                         width=1,
#                         style="dotted",
#                         with_labels=True,
#                         font_size=10,
#                         arrows=arrows,
#                         alpha= 0.6,
#                         ax=ax,
#        )
#
#        ax.axis("off")
#        return fig
#
#    #def __str__(self)
#    #    from monty.pprint import _draw_tree
#    #    return _draw_tree(node, prefix, child_iter, text_str)
