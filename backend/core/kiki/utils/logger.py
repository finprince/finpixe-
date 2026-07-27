import logging

kiki_logger = logging.getLogger("kiki.investigation")

if not kiki_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[KIKI INVESTIGATION LOG] %(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    kiki_logger.addHandler(handler)
    kiki_logger.setLevel(logging.INFO)
