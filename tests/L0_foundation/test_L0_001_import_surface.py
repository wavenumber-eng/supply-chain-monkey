from supply_chain_monkey import (
    IMPLEMENTED_SUPPLIERS,
    SupplierInterface,
    SupplierPartInfo,
    SupplierType,
    __version__,
    create_supplier,
    get_available_suppliers,
)


def test_import_surface_has_expected_exports() -> None:
    assert __version__ == "0.1.0"
    assert SupplierType.JLCPCB in IMPLEMENTED_SUPPLIERS
    assert SupplierType.MOUSER in IMPLEMENTED_SUPPLIERS
    assert SupplierPartInfo is not None
    assert SupplierInterface is not None
    assert create_supplier is not None
    assert get_available_suppliers is not None
