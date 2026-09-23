"""
Balení: co musí platit, aby se server dal nainstalovat a nastartovat.

PROČ TENHLE TEST EXISTUJE. Při nasazení na server 23. 9. 2026 zastavily
instalaci tři různé vady za sebou a každá vypadala jako jiný problém:

1. `pip install .` skončil na `InvalidConfigError: License classifiers have
   been superseded by license expressions` - `pyproject.toml` měl zároveň
   `license = "MIT"` i zrušený klasifikátor `License :: OSI Approved`.
2. Po instalaci server nenašel WSDL: cesta vedla o úroveň výš než balík
   (`<balík>/../../wsdl`), což platí jen v checkoutu, ne v `site-packages`.
   `package-data` navíc mířilo na `../wsdl/*`, což setuptools mlčky ignoruje.
3. Server se nenaimportoval: `ModuleNotFoundError: mcp.server.fastmcp`.
   Závislost `mcp[cli]>=1.0.0` neměla horní mez, pip stáhl mcp 2.x, kde se
   FastMCP přejmenoval na MCPServer.

Všechny tři jsou v `pyproject.toml` nebo v jedné cestě, takže je snadné je
omylem vrátit. Proto se tu měří, ne komentuje.

Spuštění: python -m pytest tests/test_baleni.py -q
"""

import fnmatch
import importlib.util
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

KOREN = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((KOREN / "pyproject.toml").read_text(encoding="utf-8"))


def test_wsdl_lezi_uvnitr_balicku():
    """Cesta k WSDL musí zůstat uvnitř balíku, jinak instalace nefunguje."""
    from mcp_datovka.services import isds

    balik = Path(isds.__file__).resolve().parent.parent

    assert isds.WSDL_DIR.resolve().parent == balik, (
        "WSDL_DIR ukazuje mimo balík - po instalaci tam nic nebude"
    )
    assert isds.WSDL_DIR.exists()

    soubory = {p.name for p in isds.WSDL_DIR.iterdir()}
    for potreba in ("dm_info.wsdl", "dm_operations.wsdl", "db_search.wsdl"):
        assert potreba in soubory, f"chybí {potreba}, který kód jmenovitě otevírá"


def test_package_data_pokryva_kazdy_soubor_wsdl():
    """Každý soubor ve `wsdl/` musí padnout pod nějaký vzor, jinak ve wheelu chybí.

    Původní verze tohohle testu jen koukala, že seznam vzorů není prázdný a
    nezačíná `..`. Nezávislý review 23. 9. 2026 to změřil dvěma mutacemi:
    `["missing/*.nothing"]` i vypuštění `wsdl/*.xsd` prošly zeleně, přitom
    druhá z nich dá wheel, ve kterém zeep spadne na chybějícím `dmBaseTypes.xsd`
    u všech čtyř WSDL.
    """
    vzory = PYPROJECT["tool"]["setuptools"]["package-data"]["mcp_datovka"]
    assert vzory, "bez package-data by se WSDL do balíku nedostaly"

    slozka = KOREN / "mcp_datovka" / "wsdl"
    soubory = sorted(p.name for p in slozka.iterdir() if p.is_file())
    assert len(soubory) >= 6, f"cekal jsem aspon 6 souboru, naslo se {soubory}"

    for jmeno in soubory:
        cesta = f"wsdl/{jmeno}"
        assert any(fnmatch.fnmatch(cesta, v) for v in vzory), (
            f"{cesta} nepadne pod zadny vzor {vzory} - ve wheelu bude chybet"
        )


def test_wheel_opravdu_obsahuje_wsdl():
    """Jediné tvrzení, které sahá na postavený artefakt, ne na zdrojový strom.

    Ostatní testy čtou checkout, kde soubory leží bez ohledu na `package-data`.
    Tenhle balík skutečně postaví (přes `setuptools.build_meta`, aby nebyl
    potřeba žádný další nástroj) a podívá se dovnitř.
    """
    import tempfile

    if importlib.util.find_spec("setuptools") is None:
        pytest.skip(
            "setuptools neni v tomhle prostredi - wheel se postavit neda. "
            "Preskoceny test NIC nemeri: kdyz na tomhle zalezi, pust "
            "`pytest --with setuptools` nebo `pip install setuptools` predem."
        )

    with tempfile.TemporaryDirectory() as ven:
        r = subprocess.run(
            [sys.executable, "-c",
             "from setuptools import build_meta as b; print(b.build_wheel(r'''" + ven + "'''))"],
            cwd=KOREN, capture_output=True, text=True, timeout=600,
        )
        assert r.returncode == 0, f"wheel se nepostavil:\n{r.stdout}\n{r.stderr}"
        wheel = sorted(Path(ven).glob("*.whl"))
        assert len(wheel) == 1, f"cekal jsem prave jeden wheel, je jich {len(wheel)}"

        uvnitr = zipfile.ZipFile(wheel[0]).namelist()

    data = [n for n in uvnitr if "/wsdl/" in n]
    assert len(data) >= 6, f"ve wheelu je jen {len(data)} souboru wsdl: {data}"
    for potreba in ("dm_info.wsdl", "dm_operations.wsdl", "db_search.wsdl",
                    "dmBaseTypes.xsd", "dbTypes.xsd"):
        assert any(n.endswith("mcp_datovka/wsdl/" + potreba) for n in data), (
            f"ve wheelu chybi {potreba} - zeep na nem spadne az u uzivatele"
        )


def test_zavislost_mcp_vylucuje_verzi_2():
    """Mez se čte jako specifikátor, ne jako podřetězec.

    `assert "<2" in ...` projde i pro `<2.5`, což mcp 2.x pustí dovnitř -
    změřeno nezávislým reviewem 23. 9. 2026 (mutace na `<2.5` i `<20` prošly).
    """
    zavislosti = PYPROJECT["project"]["dependencies"]
    mcp = [z for z in zavislosti if z.replace(" ", "").startswith("mcp[")]
    assert len(mcp) == 1, f"ocekavana prave jedna zavislost na mcp, nalezeno: {mcp}"

    specifikator = Requirement(mcp[0]).specifier
    assert Version("1.30.0") in specifikator, "verze 1.x musi projit"
    for zakazana in ("2.0.0", "2.2.0", "3.0.0"):
        assert Version(zakazana) not in specifikator, (
            f"{mcp[0]!r} pousti dovnitr {zakazana}, kde uz `mcp.server.fastmcp` neexistuje"
        )


def test_fastmcp_v_nainstalovane_verzi_existuje():
    """Chování, ne zápis: modul, na kterém server stojí, musí jít naimportovat."""
    import mcp.server.fastmcp  # noqa: F401


def test_build_system_umi_pep639_licenci():
    """`license = "MIT"` jako SPDX výraz umí až setuptools 77.

    Nezávislý review 23. 9. 2026 to změřil: s 75.8.2 i 76.1.0 build končí
    hláškou `invalid pyproject.toml config: 'project.license'`, která vypadá
    jako chyba v souboru, ne jako stará verze nástroje. Běžná build isolation
    to zakryje (pip si stáhne nejnovější); projeví se to při
    `--no-build-isolation` a na offline strojích - tedy přesně tam, kde
    tahle větev vznikla.
    """
    pozadavky = PYPROJECT["build-system"]["requires"]
    setuptools = [p for p in pozadavky if p.replace(" ", "").startswith("setuptools")]
    assert len(setuptools) == 1, f"ocekavan prave jeden pozadavek, nalezeno: {setuptools}"

    specifikator = Requirement(setuptools[0]).specifier
    assert Version("76.1.0") not in specifikator, (
        f"{setuptools[0]!r} pousti verzi, ktera PEP 639 licenci neumi"
    )
    assert Version("77.0.3") in specifikator


def test_licence_neni_zaroven_klasifikator():
    """`license = ...` a klasifikátor licence se podle PEP 639 vylučují."""
    assert PYPROJECT["project"].get("license"), "licence se uvádí polem `license`"

    klasifikatory = PYPROJECT["project"].get("classifiers", [])
    licencni = [k for k in klasifikatory if k.startswith("License ::")]

    assert licencni == [], (
        f"klasifikator {licencni} rozbije build na soucasnem setuptools"
    )
