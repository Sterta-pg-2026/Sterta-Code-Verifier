import os
import json
import zipfile
import script_parser as script_parser 
import result_formatter as result_formatter
from typing import Dict, Optional
from common.schemas import ProblemSpecificationSchema, SubmissionSchema, SubmissionResultSchema
import stos_gui_api_client as gui_client
# get_submission, list_problems_files, get_file


FETCH_TIMEOUT = (5, 15)
GUI_URL = os.environ["GUI_URL"]
QUEUE_COMPILER_DICT: Dict[str, str] = json.loads(os.environ["QUEUE_COMPILER_DICT"])


def fetch_problem(problem_directory_path: str, problem_id: str) -> Optional[ProblemSpecificationSchema]:
    work_directory_path = f'/tmp/problems/{problem_id}'
    zip_file_path = f"{work_directory_path}/tests.zip"
    os.system(f"mkdir -p {work_directory_path}")
    os.system(f"rm -rf {work_directory_path}/*")
    os.system(f"mkdir -p {work_directory_path}/in")
    os.system(f"mkdir -p {work_directory_path}/out")
    os.system(f"mkdir -p {work_directory_path}/other")
    
    file_list = gui_client.get_problems_files_list(problem_id, GUI_URL, FETCH_TIMEOUT)
    with zipfile.ZipFile(zip_file_path, 'w') as tests_zip:
        for file_name in file_list:
            # print(f"\tfetching {file_name}...")
            if file_name.endswith(".in"):
                gui_client.get_file(file_name, problem_id, f"{work_directory_path}/in/{file_name}", GUI_URL, FETCH_TIMEOUT)
                tests_zip.write(f"{work_directory_path}/in/{file_name}", file_name)
            elif file_name.endswith(".out"):
                gui_client.get_file(file_name, problem_id, f"{work_directory_path}/out/{file_name}", GUI_URL, FETCH_TIMEOUT)
                tests_zip.write(f"{work_directory_path}/out/{file_name}", file_name)
            elif file_name == "script.txt":
                gui_client.get_file(file_name, problem_id, f"{work_directory_path}/other/{file_name}", GUI_URL, FETCH_TIMEOUT)

    # parsing the script
    problem_specification = None
    try: 
        with open(f"{work_directory_path}/other/script.txt", "r") as script_file:
            problem_specification = script_parser.parse_script(script_file.read(), problem_id)
        print(problem_specification)
    except Exception as e:
        print(f"An error occurred while parsing the script: {e}")

    with zipfile.ZipFile(zip_file_path, "r") as zf:
        zf.extractall(problem_directory_path)
   
    os.system(f"rm -rf {work_directory_path}")
    return problem_specification




def report_result(submission_id: str, result: SubmissionResultSchema) -> None:
    score: float = result_formatter.get_result_score(result)
   
    result_content: str = result_formatter.get_result_formatted(result)
    info_content: str = result_formatter.get_info_formatted(result)
    debug_content: str = result_formatter.get_debug_formatted(result)
    
    msg = gui_client.post_result(submission_id, (result_content, info_content, debug_content), GUI_URL, FETCH_TIMEOUT)
    print("Response:", msg)
    print(f"Reported result for submission {submission_id} with score {score}")     



def get_submission(submission_path: str, problem_path: str) -> SubmissionSchema:
    for queue_name in QUEUE_COMPILER_DICT.keys():

        submission_workspace = f'/tmp/submission'
        submission_workspace_path = f"{submission_workspace}/src.zip"
        
        os.system(f"mkdir -p {submission_workspace}")
        os.system(f"rm -rf {submission_workspace}/*")
        
        try:
            response_schema = gui_client.get_submission(queue_name, submission_workspace_path, GUI_URL, FETCH_TIMEOUT)
        except Exception as e:
            print(f"An error occurred while fetching the submission: {e}")
            continue
        
        if response_schema is None:
            continue

        mainfile = None
        with zipfile.ZipFile(submission_workspace_path, "r") as zf:
            file_list = zf.infolist()
            if file_list:
                mainfile = file_list[0].filename
            zf.extractall(submission_path)
       
        submission_id = response_schema.submission_id
        problem_id = response_schema.problem_id
        author = response_schema.student_id
        

        # fetching the problem tests
        problem_specification = None
        try:
            problem_specification = fetch_problem(problem_path, problem_id)
        except Exception as e:
            print(f"An error occurred while fetching the problem: {e}")
            continue
    
        return SubmissionSchema(
            id = submission_id,
            comp_image = QUEUE_COMPILER_DICT[queue_name],
            mainfile = mainfile,
            submitted_by = author,
            problem_specification = problem_specification
        )
    
    raise FileNotFoundError("No valid submission found")

