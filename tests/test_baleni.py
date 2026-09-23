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

import tomllib
from pathlib import Path

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


def test_package_data_nemiri_mimo_balik():
    """`../neco` setuptools tiše zahodí - balík se postaví, ale bez dat."""
    data = PYPROJECT["tool"]["setuptools"]["package-data"]["mcp_datovka"]

    assert data, "bez package-data by se WSDL do balíku nedostaly"
    for vzor in data:
        assert not vzor.startswith(".."), (
            f"vzor {vzor!r} míří mimo balík a setuptools ho ignoruje"
        )


def test_zavislost_mcp_ma_horni_mez():
    """Bez horní meze stáhne pip mcp 2.x a server se ani nenaimportuje."""
    zavislosti = PYPROJECT["project"]["dependencies"]
    mcp = [z for z in zavislosti if z.replace(" ", "").startswith("mcp[")]

    assert len(mcp) == 1, f"ocekavana prave jedna zavislost na mcp, nalezeno: {mcp}"
    assert "<2" in mcp[0], (
        f"{mcp[0]!r} nema horni mez - mcp 2.x prejmenoval FastMCP na MCPServer"
    )


def test_licence_neni_zaroven_klasifikator():
    """`license = ...` a klasifikátor licence se podle PEP 639 vylučují."""
    assert PYPROJECT["project"].get("license"), "licence se uvádí polem `license`"

    klasifikatory = PYPROJECT["project"].get("classifiers", [])
    licencni = [k for k in klasifikatory if k.startswith("License ::")]

    assert licencni == [], (
        f"klasifikator {licencni} rozbije build na soucasnem setuptools"
    )
