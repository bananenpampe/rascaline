from typing import List

import metatensor
import pytest

import featomic
from featomic.calculators import (
    LodeSphericalExpansion,
    SoapPowerSpectrum,
    SoapRadialSpectrum,
    SphericalExpansion,
    SphericalExpansionByPair,
)

from ..test_systems import SystemForTests


@pytest.mark.parametrize(
    "CalculatorClass",
    [
        SphericalExpansion,
        SphericalExpansionByPair,
        SoapPowerSpectrum,
        SoapRadialSpectrum,
    ],
)
def test_soap_hypers(CalculatorClass):
    message = (
        "hyper parameter changed recently, please update your code. "
        "Here are the new equivalent parameters"
    )
    with pytest.raises(ValueError, match=message) as err:
        CalculatorClass(
            atomic_gaussian_width=0.3,
            center_atom_weight=1.0,
            cutoff=3.4,
            cutoff_function={"ShiftedCosine": {"width": 0.5}},
            max_angular=5,
            max_radial=3,
            radial_basis={"Gto": {"spline_accuracy": 1e-3}},
            radial_scaling={"Willatt2018": {"exponent": 3, "rate": 2.2, "scale": 1.1}},
        )

    error_message = str(err.value.args[0])
    first_line = error_message.find("\n")
    code = error_message[first_line:]

    # max radial meaning changed
    assert '"max_radial": 2' in code

    # check that the error message contains valid code that can be copy/pasted
    eval(code)


def test_lode_hypers():
    message = (
        "hyper parameter changed recently, please update your code. "
        "Here are the new equivalent parameters"
    )
    with pytest.raises(ValueError, match=message) as err:
        LodeSphericalExpansion(
            atomic_gaussian_width=0.3,
            center_atom_weight=0.5,
            cutoff=3.4,
            cutoff_function={"Step": {}},
            max_angular=5,
            max_radial=3,
            radial_basis={"Gto": {"splined_radial_integral": False}},
            potential_exponent=3,
            k_cutoff=26.2,
        )

    error_message = str(err.value.args[0])
    first_line = error_message.find("\n")
    code = error_message[first_line:]

    # max radial meaning changed
    assert '"max_radial": 2' in code

    # check that the error message contains valid code that can be copy/pasted
    eval(code)


def test_hypers_classes():
    hypers = {
        "cutoff": {
            "radius": 3.4,
            "smoothing": {"type": "ShiftedCosine", "width": 0.5},
        },
        "density": {
            "type": "Gaussian",
            "width": 0.3,
            "center_atom_weight": 0.3,
            "scaling": {
                "type": "Willatt2018",
                "exponent": 3,
                "rate": 2.2,
                "scale": 1.1,
            },
        },
        "basis": {
            "type": "Explicit",
            "by_angular": {
                3: {"type": "Gto", "max_radial": 5},
                5: {"type": "Gto", "max_radial": 2},
            },
        },
    }

    with_dict = SphericalExpansion(**hypers)

    with_classes = SphericalExpansion(
        cutoff=featomic.cutoff.Cutoff(
            radius=3.4,
            smoothing=featomic.cutoff.ShiftedCosine(width=0.5),
        ),
        density=featomic.density.Gaussian(
            width=0.3,
            scaling=featomic.density.Willatt2018(exponent=3, rate=2.2, scale=1.1),
            center_atom_weight=0.3,
        ),
        basis=featomic.basis.Explicit(
            by_angular={
                3: featomic.basis.Gto(max_radial=5),
                5: featomic.basis.Gto(max_radial=2),
            }
        ),
    )

    system = SystemForTests()
    metatensor.equal_raise(with_dict.compute(system), with_classes.compute(system))


def test_hypers_custom_classes_errors():
    class MyCustomSmoothing(featomic.cutoff.SmoothingFunction):
        def compute(self, cutoff, positions, derivative):
            pass

    message = (
        "this smoothing function \\(MyCustomSmoothing\\) does not have "
        "matching hyper parameters in the native calculators"
    )
    with pytest.raises(NotImplementedError, match=message):
        SphericalExpansion(
            cutoff=featomic.cutoff.Cutoff(radius=3.4, smoothing=MyCustomSmoothing()),
            density=featomic.density.Gaussian(width=0.3),
            basis=featomic.basis.TensorProduct(
                max_angular=5,
                radial=featomic.basis.Gto(max_radial=5),
            ),
        )

    class MyCustomScaling(featomic.density.RadialScaling):
        def compute(self, positions, derivative):
            pass

    message = (
        "this density scaling \\(MyCustomScaling\\) does not have matching hyper "
        "parameters in the native calculators"
    )
    with pytest.raises(NotImplementedError, match=message):
        SphericalExpansion(
            cutoff=featomic.cutoff.Cutoff(radius=3.4, smoothing=None),
            density=featomic.density.Gaussian(
                width=0.3,
                scaling=MyCustomScaling(),
            ),
            basis=featomic.basis.TensorProduct(
                max_angular=5,
                radial=featomic.basis.Gto(max_radial=5),
            ),
        )

    class MyCustomDensity(featomic.density.AtomicDensity):
        def compute(self, positions, derivative):
            pass

    message = (
        "This density \\(MyCustomDensity\\) does not have matching hyper "
        "parameters in the native calculators. It should be used "
        "through one of the spliner class instead of directly"
    )
    with pytest.raises(NotImplementedError, match=message):
        SphericalExpansion(
            cutoff=featomic.cutoff.Cutoff(radius=3.4, smoothing=None),
            density=MyCustomDensity(),
            basis=featomic.basis.TensorProduct(
                max_angular=5,
                radial=featomic.basis.Gto(max_radial=5),
            ),
        )

    class MyCustomExpansionBasis(featomic.basis.ExpansionBasis):
        def angular_channels(self) -> List[int]:
            return [0]

        def radial_basis(self, angular) -> featomic.basis.RadialBasis:
            return featomic.basis.Gto(width=0.3)

    message = (
        "This basis functions set \\(MyCustomExpansionBasis\\) does not have "
        "matching hyper parameters in the native calculators. It should be used "
        "through one of the spliner class instead of directly"
    )
    with pytest.raises(NotImplementedError, match=message):
        SphericalExpansion(
            cutoff=featomic.cutoff.Cutoff(radius=3.4, smoothing=None),
            density=featomic.density.Gaussian(width=0.3),
            basis=MyCustomExpansionBasis(),
        )

    class MyCustomRadialBasis(featomic.basis.RadialBasis):
        def __init__(self):
            super().__init__(max_radial=3, radius=2)

        def compute_primitive(self, positions, n, derivative):
            pass

    message = (
        "This radial basis function \\(MyCustomRadialBasis\\) does not have "
        "matching hyper parameters in the native calculators. It should be used "
        "through one of the spliner class instead of directly"
    )
    with pytest.raises(NotImplementedError, match=message):
        SphericalExpansion(
            cutoff=featomic.cutoff.Cutoff(radius=3.4, smoothing=None),
            density=featomic.density.Gaussian(width=0.3),
            basis=featomic.basis.TensorProduct(
                max_angular=5, radial=MyCustomRadialBasis()
            ),
        )
