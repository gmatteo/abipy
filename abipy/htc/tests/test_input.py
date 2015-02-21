"""Tests for htc.FilesFile."""
from __future__ import print_function, division

import numpy as np
import abipy.data as abidata

from abipy.core.testing import AbipyTest
from abipy.htc.input import *


class AbiInputTest(AbipyTest):

    def test_si_input(self):
        """Testing Silicon input with NC pseudo."""
        aequal, atrue = self.assertEqual, self.assertTrue

        # Create an ABINIT input file with 1 dataset. 
        inp = AbiInput(pseudos="14si.pspnc", pseudo_dir=abidata.pseudo_dir, ndtset=1)
        inp.set_comment("Input file with 1 dataset")
        inp.set_mnemonics(True)
        assert inp.mnemonics

        aequal(inp.isnc, True)

        # One can set the value of the variables directly with the syntax.
        inp.ecut = 10.
        inp.tolwfr = 1e-8

        # It's possible to use strings but use them only for special cases such as:
        inp.istwfk = '*1'       

        # One can create a dictionary mapping keywords to values 
        unit_cell = {
            "acell": 3*[10.217],       
            'rprim': [[.0, .5, .5],
                      [.5, .0, .5],
                      [.5, .5, .0]],
            'ntypat': 1,
            'znucl': [14,],
            'natom': 2,
            'typat': [1, 1],
            'xred': [[.0, .0, .0],
                     [.25,.25,.25]]
        }

        # and set the variables in the input file with the call:
        inp.set_vars(**unit_cell)
        # Now we have a structure
        assert len(inp.structure) == 2

        # Alternatively, it's possible to create a dictionary on the fly with the syntax.
        inp.set_vars(kptopt=1,  ngkpt=[2, 2, 2],  nshiftk=1, 
                     shiftk=np.reshape([0.0, 0.0, 0.0], (-1,3)))

        inp.nshiftk = len(inp.shiftk) 
        assert inp.nshiftk == 1

        inp.remove_vars("nshiftk")
        with self.assertRaises(AttributeError): print(inp.nshiftk)

        # To print the input to stdout use:
        print(inp)

        # Test set_structure 
        new_structure = inp.structure.copy() 
        new_structure.perturb(distance=0.1)
        inp.set_structure(new_structure)
        assert inp.structure == new_structure

        # To create a new input with a different variable.
        new = inp.new_with_vars(kptopt=3)
        assert new.kptopt == 3 and inp.kptopt == 1

        # Compatible with deepcopy and Pickle?
        inp.deepcopy()
        self.serialize_with_pickle(inp, test_eq=False)

        # A slightly more complicated example: input file with two datasets
        inp = AbiInput(pseudos="14si.pspnc", pseudo_dir=abidata.pseudo_dir, ndtset=2)

        # Global variable common to all datasets.
        inp.tolwfr = 1e-8

        # To specify values for the different datasets, one can use the syntax
        inp.ecut1 = 10
        inp.ecut2 = 20

        with self.assertRaises(AttributeError): print(inp.ecut)
        inp.remove_vars("ecut", dtset=2)
        assert inp.ecut1 == 10
        with self.assertRaises(AttributeError): print(inp.ecut2)

        # or by passing the index of the dataset to set_vars via the dtset argument.
        inp.set_vars(ngkpt=[2,2,2], tsmear=0.004, dtset=1)
        inp.set_vars(kptopt=[4,4,4], tsmear=0.008, dtset=2)
        print(inp)

        # Compatible with deepcopy and Pickle?
        inp.deepcopy()
        self.serialize_with_pickle(inp, test_eq=False)

        # pseudo file must exist.
        with self.assertRaises(inp.Error):
            AbiInput(pseudos="foobar.pspnc", pseudo_dir=abidata.pseudo_dir, ndtset=2)

        tsmear_list = [0.005, 0.01]
        ngkpt_list = [[4,4,4], [8,8,8]]
        occopt_list = [3, 4]
        inp = AbiInput(pseudos=abidata.pseudos("14si.pspnc"), ndtset=len(tsmear_list))

        inp.linspace("tsmear", start=tsmear_list[0], stop=tsmear_list[-1])
        print(inp)

        inp = AbiInput(pseudos=abidata.pseudos("14si.pspnc"), ndtset=len(tsmear_list) * len(ngkpt_list))

        inp.product("tsmear", "ngkpt", tsmear_list, ngkpt_list)
        print(inp)

        # If you don't want to use multiple datasets in your calculation,
        # you can split the initial input into ndtset different inputs.
        separated_inps = inp.split_datasets()

        for inp in separated_inps:
            print(inp)
            atrue(isinstance(inp, AbiInput))

        # product accepts an arbitrary number of variables.
        inp = AbiInput(pseudos=abidata.pseudos("14si.pspnc"), ndtset=len(tsmear_list) * len(ngkpt_list) * len(occopt_list))

        inp.product("tsmear", "ngkpt", "occopt", tsmear_list, ngkpt_list, occopt_list)
        print(inp)

        # Split datasets.
        inp.split_datasets()

        # Cannot split datasets when we have get* or ird* variables.
        inp[2].set_vars(getwfk=-1)
        with self.assertRaises(inp.Error): inp.split_datasets()

    def test_niopaw_input(self):
        """Testing AbiInput for NiO with PAW."""
        aequal = self.assertEqual

        inp = AbiInput(pseudos=abidata.pseudos("28ni.paw", "8o.2.paw"), ndtset=2, comment="NiO calculation")
        inp.set_structure(abidata.structure_from_ucell("NiO"))
        print(inp)

        aequal(inp.ndtset, 2)
        aequal(inp.ispaw, True)

        # Set global variables.
        inp.set_vars(ecut=10)

        # Compatible with deepcopy and Pickle?
        inp.deepcopy()
        self.serialize_with_pickle(inp, test_eq=False)

        # Setting an unknown variable should raise an error.
        with self.assertRaises(inp.Error): inp.set_vars(foobar=10)


class LdauLexxTest(AbipyTest):

    def test_nio(self):
        """Test LdauParams and LexxParams."""
        aequal, atrue = self.assertEqual, self.assertTrue

        structure = abidata.structure_from_ucell("NiO")
        pseudos = abidata.pseudos("28ni.paw", "8o.2.paw")

        u = 8.0
        luj_params = LdauParams(usepawu=1, structure=structure)
        luj_params.luj_for_symbol("Ni", l=2, u=u, j=0.1*u, unit="eV")
        vars = luj_params.to_abivars()

        self.serialize_with_pickle(luj_params, test_eq=False)

        atrue(vars["usepawu"] == 1),
        aequal(vars["lpawu"], "2 -1"),
        aequal(vars["upawu"], "8.0 0.0 eV"),
        aequal(vars["jpawu"], "0.8 0.0 eV"),

        # Cannot add UJ for non-existent species.
        with self.assertRaises(ValueError):
            luj_params.luj_for_symbol("Foo", l=2, u=u, j=0.1*u, unit="eV")

        # Cannot overwrite UJ.
        with self.assertRaises(ValueError):
            luj_params.luj_for_symbol("Ni", l=1, u=u, j=0.1*u, unit="eV")

        lexx_params = LexxParams(structure)
        lexx_params.lexx_for_symbol("Ni", l=2)
        vars = lexx_params.to_abivars()

        self.serialize_with_pickle(lexx_params, test_eq=False)

        aequal(vars["useexexch"], 1),
        aequal(vars["lexexch"], "2 -1"),

        # Cannot add LEXX for non-existent species.
        with self.assertRaises(ValueError):
            lexx_params.lexx_for_symbol("Foo", l=2)
                                                                            
        # Cannot overwrite LEXX.
        with self.assertRaises(ValueError):
            lexx_params.lexx_for_symbol("Ni", l=1)


class AnaddbInputTest(AbipyTest):
    """Tests for AnaddbInput."""

    def setUp(self):
        self.structure = abidata.structure_from_ucell("Si")

    def test_phbands_and_dos(self):
        """Test phbands_and_dos constructor."""
        inp = AnaddbInput(self.structure, comment="hello anaddb", brav=1)
        self.assertTrue("brav" in inp)
        self.assertEqual(inp["brav"], 1)
        self.assertEqual(inp.get("brav"), 1)

        # Unknown variable.
        with self.assertRaises(AnaddbInput.Error):
            AnaddbInput(self.structure, foo=1)

        ndivsm = 1
        nqsmall = 3
        ngqpt = (4, 4, 4)

        inp2 = AnaddbInput.phbands_and_dos(self.structure, ngqpt, ndivsm, nqsmall, asr=0, dos_method="tetra")
        self.assertEqual(inp2['ifcflag'], 1)

        s2 = inp2.to_string(sortmode="a")
        print(s2)

        inp3 = AnaddbInput.phbands_and_dos(self.structure, ngqpt, ndivsm, nqsmall,
                                           qptbounds=[0,0,0,1,1,1], dos_method="gaussian:0.001 eV")
        self.assertEqual(inp3['ifcflag'], 1)
        self.assertEqual(inp3['prtdos'], 1)
        s3 = inp3.to_string(sortmode="a")
        print(s3)

        # Compatible with deepcopy and Pickle?
        for i in (inp, inp2, inp3):
            self.serialize_with_pickle(i, test_eq=False)
            i.deepcopy()

    def test_thermo(self):
        """Test the thermodynamics constructor"""
        anaddb_input = AnaddbInput.thermo(self.structure, ngqpt=(40, 40, 40), nqsmall=20)
        self.assertTrue(anaddb_input.make_input())
        for var in ('thmtol', 'ntemper', 'temperinc', 'thmtol'):
            self.assertTrue(anaddb_input[var] >= 0)
        for flag in ('ifcflag', 'thmflag'):
            self.assertEqual(anaddb_input[flag], 1)

        self.serialize_with_pickle(anaddb_input, test_eq=False)
        anaddb_input.deepcopy()

    def test_modes(self):
        """Test the modes constructor"""
        anaddb_input = AnaddbInput.modes(self.structure)
        self.assertTrue(anaddb_input.make_input())
        for flag in ('ifcflag', 'dieflag'):
            self.assertEqual(anaddb_input[flag], 1)

        self.serialize_with_pickle(anaddb_input, test_eq=False)
        anaddb_input.deepcopy()


if __name__ == "__main__":
    import unittest
    unittest.main()
