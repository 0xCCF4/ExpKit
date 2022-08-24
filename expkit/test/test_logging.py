import logging
from expkit.base.logger import get_logger, init_global_logging
import pytest


def test_loglevels():
    init_global_logging(None, logging.DEBUG, logging.DEBUG)

    logger = get_logger("test")
    logger.debug("debug")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        logger.critical("critical")
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == -1
