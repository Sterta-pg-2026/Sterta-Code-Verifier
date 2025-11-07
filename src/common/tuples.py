from typing import NamedTuple


class Timeout(NamedTuple):
    """
    Named tuple representing timeout settings for network connections.
    
    Attributes:
        connect: Timeout in seconds for establishing a connection
        read: Timeout in seconds for reading data from an established connection
    """
    connect: float
    read: float


class StosGuiResultSchema(NamedTuple):
    """
    Named tuple representing the result data sent to the STOS GUI.
    
    This tuple encapsulates the evaluation results that will be sent back
    to the graphical user interface after processing a submission.
    
    Attributes:
        result: The main result data (typically JSON-formatted submission results)
        info: Additional information or messages about the evaluation
        debug: Debug information for troubleshooting and diagnostics
    """
    result: str
    info: str
    debug: str