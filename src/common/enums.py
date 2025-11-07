from enum import Enum

class SubmissionStatus(Enum):
    """
    Enumeration representing the different states of a submission in the system.
    
    This enum tracks the lifecycle of a submission from initial creation
    through completion and reporting.
    
    Attributes:
        NONE: Initial state, no submission has been created
        PENDING: Submission has been created and is waiting to be processed
        RUNNING: Submission is currently being executed/processed
        COMPLETED: Submission has finished processing successfully
        REPORTED: Results have been reported back to the client
    """
    NONE = 0
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3
    REPORTED = 4


class Ansi(Enum):
    """
    ANSI escape codes for terminal text formatting and coloring.
    
    This enum provides a collection of ANSI escape sequences that can be used
    to format terminal output with colors, text styles, and background colors.
    These codes are commonly used in command-line applications for enhanced
    user experience and visual feedback.
    
    Attributes:
        RESET: Resets all formatting to default
        BOLD: Makes text bold/bright
        UNDERLINE: Underlines the text
        REVERSED: Reverses foreground and background colors
        
        BLACK: Sets text color to black
        RED: Sets text color to red
        GREEN: Sets text color to green
        YELLOW: Sets text color to yellow
        BLUE: Sets text color to blue
        MAGENTA: Sets text color to magenta
        CYAN: Sets text color to cyan
        WHITE: Sets text color to white
        
        BG_BLACK: Sets background color to black
        BG_RED: Sets background color to red
        BG_GREEN: Sets background color to green
        BG_YELLOW: Sets background color to yellow
        BG_BLUE: Sets background color to blue
        BG_MAGENTA: Sets background color to magenta
        BG_CYAN: Sets background color to cyan
        BG_WHITE: Sets background color to white
    """
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    REVERSED = "\033[7m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"