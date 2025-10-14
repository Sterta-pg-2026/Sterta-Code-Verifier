import requests
from urllib.parse import urljoin
from common.schemas import SubmissionGuiSchema
from typing import Any, Dict, List, Optional, Tuple


MAX_FILE_SIZE = 50 * 1024 * 1024


def report_result(submission_id: str, result: Tuple[str, str, str], gui_url: str, timeout: Tuple[float, float]) -> str:
    res_url: str = urljoin(gui_url, "io-result.php")
    files = {
        'result': ('result.txt', result[0], 'text/plain'),
        'info': ('info.txt', result[1], 'text/plain'),
        'debug': ('debug.txt', result[2], 'text/plain'),
    }
    data = {
        "id": submission_id
    }

    with requests.post(res_url, data=data, files=files, timeout=timeout) as response:
        return response.text


def list_problems_files(problem_id: str, gui_url: str, timeout: Tuple[float, float]) -> List[str]:
    fsapi_url: str = urljoin(gui_url, "fsapi/fsctrl.php")
    params: Dict[str, Any] = {
        "f": "list",
        "area": 0, # problem files area
        "pid": problem_id,
    }
    
    with requests.get(fsapi_url, params=params, timeout=timeout) as response:
        response.raise_for_status()
        raw_file_list = response.text
        
        # parse the response to extract file names
        problem_file_list: List[str] = []
        for line in raw_file_list.splitlines():
            if not line.strip():
                continue
            file_name = line.split(':')[0].strip()
            problem_file_list.append(file_name)
    
        return problem_file_list


def get_file(file_name: str, problem_id: str, output_storage_path: str, gui_url: str, timeout: Tuple[float, float]) -> None:
    fsapi_url: str = urljoin(gui_url, "fsapi/fsctrl.php")
    params: Dict[str, Any] = {
        "f": "get",
        "area": 0,
        "pid": problem_id,
        "name": file_name
    }

    with requests.get(fsapi_url, params=params, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        with open(output_storage_path, "wb") as file:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > MAX_FILE_SIZE:
                        raise ValueError("File too large, download aborted")
                    file.write(chunk)


def get_submission(queue_name: str, output_storage_path: str, gui_url: str, timeout: Tuple[float, float]) -> Optional[SubmissionGuiSchema]:
    qapi_url: str = urljoin(gui_url, "qapi/qctrl.php")
    params: Dict[str, str] = {
        "f": "get",
        "name": queue_name
    }

    with requests.get(qapi_url, params=params, timeout=timeout, stream=True) as response:
        # handle HTTP errors
        if response.status_code == 404:
            return None
        else:
            response.raise_for_status()

        # validate headers
        xparam = response.headers.get('X-Param')
        submission_id = response.headers.get('X-Server-Id')
        if not submission_id or not xparam:
            raise ValueError("Missing X-Server-Id or X-Param header")

        parts = xparam.split(";")
        if len(parts) != 2:
            raise ValueError(f"Invalid X-Param header format: {xparam}")

        problem_id = parts[0]
        student_id = parts[1]

        # save response content to output_storage_path
        downloaded_size = 0
        with open(output_storage_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded_size += len(chunk)
                    if downloaded_size > MAX_FILE_SIZE:
                        raise ValueError("File too large, download aborted")
                    file.write(chunk)

        # return structured response
        return SubmissionGuiSchema(
            submission_id=submission_id,
            problem_id=problem_id,
            student_id=student_id,
        )
