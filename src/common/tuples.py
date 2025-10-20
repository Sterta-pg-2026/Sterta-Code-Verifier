from typing import NamedTuple


class Timeout(NamedTuple):
    connect: float
    read: float


class StosGuiResultSchema(NamedTuple):
    result: str
    info: str
    debug: str