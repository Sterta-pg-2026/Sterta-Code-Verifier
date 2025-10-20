"""Result formatter module for STOS submission evaluation results.

This module provides functionality to format submission evaluation results
into various output formats including HTML tables, debug information,
and result summaries for display in the STOS GUI.

The formatter handles test results, compilation information, debug logs,
and generates styled HTML output with proper formatting and color coding.
"""
import ansi2html
from common.schemas import SubmissionResultSchema

def get_result_score(result: SubmissionResultSchema) -> float:
    """Calculate the percentage score for a submission result.
    
    Args:
        result (SubmissionResultSchema): The submission result containing test results and points.
    
    Returns:
        float: Percentage score (0-100) based on passed tests vs total tests.
    """
    return 100*result.points / len(result.test_results) if len(result.test_results) > 0 else 0


def get_result_formatted(result: SubmissionResultSchema) -> str:
    """Format submission result into STOS GUI result format.
    
    Creates a formatted result string containing the score, format specifications,
    and basic info message for the STOS GUI API.
    
    Args:
        result (SubmissionResultSchema): The submission result to format.
    
    Returns:
        str: Formatted result string with score and format specifications.
    """
    score = get_result_score(result)
    result_content = \
f"""
result={score}
infoformat=html
debugformat=html
info=All tests passed
"""
    return result_content
    
    
def get_info_formatted(result: SubmissionResultSchema) -> str:
    """Format submission result into detailed HTML info display.
    
    Creates a comprehensive HTML table showing test results with styling,
    color coding for pass/fail/error states, and compilation information.
    Includes CSS styling for professional presentation.
    
    Args:
        result (SubmissionResultSchema): The submission result to format.
    
    Returns:
        str: HTML formatted string with test results table and compilation info.
    """
    score = get_result_score(result)
    info_content = \
f"""
<style>

    table {{ 
        border-collapse: collapse; 
        border: 1px solid #202020;
        border-radius: 5px; 
        overflow: hidden;
    }}
    th {{ 
        border: 1px solid #202020; 
        padding: 3px 10px; 
        background-color: #d8d8d8; 
        max-width: 350px;
        text-align: center;
    }}
    td {{
        border-left: 1px solid #202020; 
        border-right: 1px solid #202020; 
        padding: 3px 10px; 
        max-width: 350px;
        white-space: nowrap;
        overflow: hidden;
        text-align: right;
    }}
    tr:hover td {{
    }}
    tbody tr:nth-child(even) {{ filter: brightness(90%); }}
    .success {{ background-color: #6fb65d; }}
    .failure {{ background-color: #b65d62; }}
    .eerror {{ background-color: #e69c53; }}

</style>
<b>Score:</b> {score:.2f}%
<br>
<br>
"""
    if len(result.test_results) != 0:
        info_content += \
f"""
<div style="background-color: #202020; border-radius: 5px; width: fit-content;">
    <table>
        <tr>
            <th>Name</th>
            <th>Time [s]</th>
            <th>Maxrss [KiB]</th>
            <th>Code</th>
            <th>Info</th>
        </tr>
        {''.join(f"<tr class='{'success' if test.grade else ('failure' if (test.ret_code is None or test.ret_code >= 0) else 'eerror')}'><td>{test.test_name}</td><td>{test.time:.2f}</td><td>{(test.memory or 0)/1024:.0f}</td><td>{test.ret_code if (test.ret_code is not None and test.ret_code >= 0) else ''}</td><td>{test.info}</td></tr>" for test in result.test_results)}
    </table>
</div>
"""
    if result.info:
        converter = ansi2html.Ansi2HTMLConverter(inline=True)
        info_parsed = converter.convert(result.info, full=False)
        info_content += f"""<pre style='font-family: monospace;'>{info_parsed}</pre>"""
    
    return info_content

def get_debug_formatted(result: SubmissionResultSchema) -> str:
    """Format debug information into HTML display.
    
    Converts ANSI escape sequences in debug logs to HTML format
    for proper display in the STOS GUI.
    
    Args:
        result (SubmissionResultSchema): The submission result containing debug information.
    
    Returns:
        str: HTML formatted debug information or empty string if no debug info.
    """
    debug_content = ""
    if result.debug:
        converter = ansi2html.Ansi2HTMLConverter(inline=True)
        debug_parsed = converter.convert(result.debug, full=False)
        debug_content += f"""<pre style='font-family: monospace;'>{debug_parsed}</pre>"""
    return debug_content

    



