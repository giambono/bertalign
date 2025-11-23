from pathlib import Path


class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False

    ROOT = Path(__file__).parent