import ansi2html
from common.schemas import SubmissionResultSchema

def get_result_score(result: SubmissionResultSchema) -> float:
    return 100*result.points / len(result.test_results) if len(result.test_results) > 0 else 0


def get_result_formatted(result: SubmissionResultSchema) -> str:
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
    score = get_result_score(result)
    border_color = "#202020"
    border_radius = "4px"
    max_width = "250px"
    info_content = \
f"""
<style>

    table {{ 
        border-collapse: collapse; 
        border: 1px solid {border_color};
        border-radius: {border_radius}; 
        overflow: hidden;
    }}
    th {{ 
        border: 1px solid {border_color}; 
        padding: 3px 10px; 
        background-color: #d8d8d8; 
        max-width: {max_width};
        text-align: center;
    }}
    td {{
        border-left: 1px solid {border_color}; 
        border-right: 1px solid {border_color}; 
        padding: 3px 10px; 
        max-width: {max_width};
        white-space: nowrap;
        overflow: hidden;
        text-align: right;
    }}
    tr:hover td {{
    }}
    tbody tr:nth-child(even) {{ filter: brightness(90%); }}
    .success {{ background-color: rgb(109, 156, 109); }}
    .failure {{ background-color: rgb(164, 84, 88); }}
    .eerror {{ background-color: rgb(207, 140, 75); }}

</style>
<b>Score:</b> {score:.2f}%
<br>
<br>
"""
    if len(result.test_results) != 0:
        info_content += \
f"""
<div style="background-color: {border_color}; border-radius: {border_radius}; width: fit-content;">
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
    debug_content = ""
    if result.debug:
        converter = ansi2html.Ansi2HTMLConverter(inline=True)
        debug_parsed = converter.convert(result.debug, full=False)
        debug_content += f"""<pre style='font-family: monospace;'>{debug_parsed}</pre>"""
    return debug_content

    



