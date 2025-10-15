import os
import json
import shutil
import zipfile
import script_parser as script_parser 
import result_formatter as result_formatter
from typing import Dict, Optional
from common.schemas import ProblemSpecificationSchema, SubmissionSchema, SubmissionResultSchema
import stos_gui_api_client as gui_client


FETCH_TIMEOUT = (5, 15)
GUI_URL = os.environ["GUI_URL"]
QUEUE_COMPILER_DICT: Dict[str, str] = json.loads(os.environ["QUEUE_COMPILER_DICT"])


def fetch_submission(destination_directory: str) -> Optional[SubmissionSchema]:
    submission_workspace = f'/tmp/submission'
    submission_temp_zip_path = os.path.join(submission_workspace, "src.zip")

    for queue_name in QUEUE_COMPILER_DICT.keys():
        # initializing workspace
        os.umask(0)
        if os.path.exists(submission_workspace):
            shutil.rmtree(submission_workspace)
        os.makedirs(submission_workspace)

        # fetching submission
        response = None
        try:
            response = gui_client.get_submission(queue_name, submission_temp_zip_path, GUI_URL, FETCH_TIMEOUT)
        except Exception as e:
            print(f"An error occurred while fetching the submission from {queue_name}: {e}")
            continue
        if response is None:
            continue

        # preparing submission schema
        submission = SubmissionSchema(
            id = response.submission_id,
            comp_image = QUEUE_COMPILER_DICT[queue_name],
            mainfile = None,
            submitted_by = response.student_id,
            problem_specification = ProblemSpecificationSchema(id=response.problem_id)
        )

        # extracting submission files
        with zipfile.ZipFile(submission_temp_zip_path, "r") as zf:
            file_list = zf.infolist()
            if file_list:
                submission.mainfile = file_list[0].filename
            zf.extractall(destination_directory)
       
        return submission

    return None

def report_result(submission_id: str, result: SubmissionResultSchema) -> None:
    score: float = result_formatter.get_result_score(result)
   
    result_content: str = result_formatter.get_result_formatted(result)
    info_content: str = result_formatter.get_info_formatted(result)
    debug_content: str = result_formatter.get_debug_formatted(result)
    
    msg = gui_client.post_result(submission_id, (result_content, info_content, debug_content), GUI_URL, FETCH_TIMEOUT)
    print(f"Reported result for submission {submission_id} with score {score}, response: {msg}")     

def fetch_problem(destination_directory: str, problem_id: str) -> ProblemSpecificationSchema:
    # initializing workspace
    problem_workspace = f'/tmp/problem'
    tmp_script_path = os.path.join(problem_workspace, "script.txt")

    os.umask(0)
    if os.path.exists(problem_workspace):
        shutil.rmtree(problem_workspace)
    os.makedirs(problem_workspace)

    # fetching problem files
    file_list = gui_client.get_problems_files_list(problem_id, GUI_URL, FETCH_TIMEOUT)
    for file_name in file_list:
        if file_name.endswith(".in"):
            gui_client.get_file(file_name, problem_id, os.path.join(destination_directory, file_name), GUI_URL, FETCH_TIMEOUT)
        elif file_name.endswith(".out"):
            gui_client.get_file(file_name, problem_id, os.path.join(destination_directory, file_name), GUI_URL, FETCH_TIMEOUT)
        elif file_name == "script.txt":
            gui_client.get_file(file_name, problem_id, tmp_script_path, GUI_URL, FETCH_TIMEOUT)


    # parsing the script
    problem_specification = ProblemSpecificationSchema(id=problem_id)
    try: 
        with open(tmp_script_path, "r") as script_file:
            problem_specification = script_parser.parse_script(script_file.read(), problem_id) or problem_specification
        print(f"Parsed problem specification:\n {problem_specification}")
    except Exception as e:
        print(f"An error occurred while parsing the script: {e}")

    return problem_specification

