from scm import __version__
from scm.models import (
    PARAMETER_FIELD_NAMES,
    SUPPLIERS,
    SUPPLIER_LOOKUP,
    DetailEnvelope,
    HealthResponse,
    HttpErrorDetail,
    PartResponse,
    ProviderStatusResponse,
    RateLimitSnapshot,
    SearchEnvelope,
    ServiceEnvelope,
    SpnBatchEnvelope,
    SpnBatchItem,
    SpnBatchRequest,
    SpnEnvelope,
    StreamDoneEvent,
    SupplierCapabilities,
    SupplierType,
    ValidationErrorDetail,
)
from scm.client import SCMClient


def test_version():
    assert __version__ == "2026.9.1"


def test_supplier_enum():
    assert SupplierType.JLCPCB.value == "JLCPCB"
    assert SupplierType.LCSC.value == "LCSC"
    assert SupplierType.DIGIKEY.value == "Digikey"
    assert SupplierType.MOUSER.value == "Mouser"


def test_suppliers_list():
    assert "jlcpcb" in SUPPLIERS
    assert "lcsc" in SUPPLIERS
    assert "digikey" in SUPPLIERS
    assert "mouser" in SUPPLIERS
    assert len(SUPPLIERS) == 4


def test_supplier_lookup():
    assert SUPPLIER_LOOKUP["jlcpcb"] == SupplierType.JLCPCB
    assert SUPPLIER_LOOKUP["digikey"] == SupplierType.DIGIKEY


def test_parameter_field_names():
    assert PARAMETER_FIELD_NAMES[SupplierType.JLCPCB] == "JLCPCB Part #"
    assert PARAMETER_FIELD_NAMES[SupplierType.LCSC] == "LCSC Part #"
    assert PARAMETER_FIELD_NAMES[SupplierType.DIGIKEY] == "Digikey Part #"
    assert PARAMETER_FIELD_NAMES[SupplierType.MOUSER] == "Mouser Part #"


def test_contract_models_importable():
    assert DetailEnvelope is not None
    assert HealthResponse is not None
    assert HttpErrorDetail is not None
    assert PartResponse is not None
    assert ProviderStatusResponse is not None
    assert RateLimitSnapshot is not None
    assert SearchEnvelope is not None
    assert ServiceEnvelope is not None
    assert SpnBatchEnvelope is not None
    assert SpnBatchItem is not None
    assert SpnBatchRequest is not None
    assert SpnEnvelope is not None
    assert StreamDoneEvent is not None
    assert ValidationErrorDetail is not None
    assert SupplierCapabilities is not None


def test_client_importable():
    assert SCMClient is not None
