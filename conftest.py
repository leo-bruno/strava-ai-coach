"""Label existing test levels for Allure without changing pytest execution."""

import warnings

import allure
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    if not item.config.getoption("allure_report_dir", default=None):
        return

    name = item.path.name
    if name.endswith("_unit_test.py"):
        level = "Unit"
    elif name.endswith("_integration_test.py"):
        level = "Integration"
    else:
        warnings.warn(
            f"Allure test level is undefined for {item.nodeid}; "
            "expected *_unit_test.py or *_integration_test.py.",
            pytest.PytestWarning,
            stacklevel=2,
        )
        return

    allure.dynamic.parent_suite(level)
