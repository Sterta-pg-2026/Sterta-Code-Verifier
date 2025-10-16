import os
import json
import time
import docker
import shutil
import signal
import adapter
from types import FrameType
from natsort import natsorted
from common.enums import Ansi
from logger import get_logger
from typing import Dict, List, Optional
from common.schemas import ProblemSpecificationSchema, SubmissionResultSchema, TestResultSchema, VolumeMappingSchema


FETCH_TIMEOUT = (5, 15)  # seconds
POOLING_INTERVAL = 1000e-3  # seconds
CONTAINERS_TIMEOUT = 300
INFO_LENGTH_LIMIT = 2*5000
CONTAINERS_FILE_SIZE_LIMIT = "5g"
CONTAINERS_MEMORY_LIMIT = "512m"
HOSTNAME = os.environ['HOSTNAME']
NAME: str =  docker.from_env().containers.get(HOSTNAME).name or HOSTNAME
# HISTORY_LOCAL_PATH = os.path.join(os.environ["WORKERS_HISTORY_LOCAL_PATH"], NAME)
DATA_LOCAL_PATH = os.path.join(os.environ["WORKERS_DATA_LOCAL_PATH"], NAME)
DATA_HOST_PATH = os.path.join(os.environ["WORKERS_DATA_HOST_PATH"], NAME)

IS_DEBUG_MODE_ENABLED = os.environ.get("IS_DEBUG_MODE_ENABLED", "false").lower() == "true"
EXEC_IMAGE: str = os.environ["EXEC_IMAGE_NAME"]
JUDGE_IMAGE: str = os.environ["JUDGE_IMAGE_NAME"]


def handle_signal(signum: int, frame: Optional[FrameType]) -> None:
    exit(0)


def mainloop() -> None:
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    while True:
        should_wait = execute_submission_pipeline()
        if should_wait:
            time.sleep(POOLING_INTERVAL)

def fetch_compilation_info(path: str) -> Optional[str]:
    comp_file_path = os.path.join(path, "comp.txt")
    try:
        with open(comp_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = ""
            for line in f:
                if len(content) + len(line) > INFO_LENGTH_LIMIT:
                    break
                content += line
           
    except Exception:
        return None
    return content if content else None

def fetch_debug_logs(log_path: Optional[str]) -> Optional[str]:
    try:
        if log_path and os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as log_file:
                content = ""
                for line in log_file:
                    if len(content) + len(line) > INFO_LENGTH_LIMIT*2:
                        print("Log file too long, truncating...")
                        break
                    content += line
                return content
    except Exception:
        return None

def get_results(path: str) -> SubmissionResultSchema:
    submission_result = SubmissionResultSchema()
    submission_result.info = fetch_compilation_info(path)

    points = 0
    test_names: List[str] = []
    for file in os.listdir(path):
        if file.endswith(".judge.json"):
            test_names.append(file.split(".")[0])

    test_names = natsorted(test_names) # type: ignore
    for test_name in test_names:
        exec_file_path = os.path.join(path, f"{test_name}.exec.json")
        judge_file_path = os.path.join(path, f"{test_name}.judge.json")
        test_result: TestResultSchema = TestResultSchema(test_name=test_name)

        with open(exec_file_path, "r") as exec_file:
            exec = json.load(exec_file)
            test_result.ret_code = exec["return_code"]
            test_result.time = float(exec["user_time"])
            test_result.memory = float(exec["memory"])

        with open(judge_file_path, "r") as judge_file:
            judge = json.load(judge_file)
            test_result.grade = True if judge["grade"] == 1 else False
            test_result.info = judge["info"]
            if judge["grade"]:
                points += 1

        submission_result.test_results.append(test_result)

    submission_result.points = points
    return submission_result

def report_result(submission_id: str, result: Optional[SubmissionResultSchema]) -> None:
    if result is None:
        result = SubmissionResultSchema()
        try:
            result.info = fetch_compilation_info(os.path.join(DATA_LOCAL_PATH, "out"))
        except Exception:
            result.info = "Error while running submission"    
    adapter.report_result(submission_id, result)

def init_worker_files() -> None:
    os.umask(0)
    if os.path.exists(DATA_LOCAL_PATH):
        shutil.rmtree(DATA_LOCAL_PATH)
    os.makedirs(DATA_LOCAL_PATH)
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "bin"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "std"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "out"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "conf"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "src"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "lib"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "logs"))
    os.makedirs(os.path.join(DATA_LOCAL_PATH, "tests"))

def archive_worker_files() -> None:
    os.umask(0)
    history_local_path = f"{DATA_LOCAL_PATH}_debug"
    if os.path.exists(history_local_path):
        shutil.rmtree(history_local_path)

    backup_path = os.path.join(history_local_path)
    shutil.copytree(DATA_LOCAL_PATH, backup_path)

def save_problem_specification(problem_specification: Optional[ProblemSpecificationSchema]) -> None:
     if problem_specification:
        problem_specification_local_path = os.path.join(DATA_LOCAL_PATH, "conf", "problem_specification.json")
        with open(problem_specification_local_path, "w") as f:
            json.dump(problem_specification.model_dump(), f)

def run_container(
    client: docker.DockerClient,
    image: str,
    memory_limit: str = CONTAINERS_MEMORY_LIMIT,
    timeout: int = CONTAINERS_TIMEOUT,
    environment: Dict[str, str] = {},
    volume_mappings: List[VolumeMappingSchema] = [],
) -> None:
    container = client.containers.run( # type: ignore
        image=image,
        detach=True,
        remove=True,
        mem_limit=memory_limit,
        network_disabled=True,
        security_opt=["no-new-privileges"],
        # storage_opt={"size": CONTAINERS_FILE_SIZE_LIMIT},
        environment=environment,
        volumes={volume_mapping.key(): volume_mapping.value() for volume_mapping in volume_mappings},
    )
    container.wait(timeout=timeout)

def execute_submission_pipeline() -> bool:
    problem_local_path: str = os.path.join(DATA_LOCAL_PATH, "tests")
    problem_host_path: str = os.path.join(DATA_HOST_PATH, "tests")
    submission_local_path: str = os.path.join(DATA_LOCAL_PATH, "src")
    submission_host_path: str = os.path.join(DATA_HOST_PATH, "src")
    lib_local_path: str = os.path.join(DATA_LOCAL_PATH, "lib")
    # lib_host_path: str = os.path.join(DATA_HOST_PATH, "lib") # todo: use lib path
    logs_local_path: str = os.path.join(DATA_LOCAL_PATH, "logs")

    # * ----------------------------------
    # * Initialize worker files
    # * ----------------------------------
    try:
        init_worker_files()
    except Exception as e:
        print(f"Error while initializing worker files: {e}")
        
    logger = get_logger("worker_submission_proccessing_workflow", os.path.join(logs_local_path, "worker.log"))

    logger.info(f"{Ansi.BOLD.value}{NAME}{Ansi.RESET.value} is starting submission processing workflow.")

    # * ----------------------------------
    # * Fetch submission
    # * ----------------------------------
    try:
        submission = adapter.fetch_submission(submission_local_path)
    except Exception as e:
        logger.error(f"Error while fetching submission: {e}")
        return True

    
    if submission is None:
        logger.info("No submission fetched.")
        return True
    
    if submission.problem_specification.id is None:
        logger.info("No problem found.")
        return True

    logger.info(f"Fetched submission {submission.id} for problem {submission.problem_specification.id} by {submission.submitted_by}")


    # * ----------------------------------
    # * Fetch problem
    # * ----------------------------------
    try:
        problem = adapter.fetch_problem(submission.problem_specification.id, problem_local_path, lib_local_path)
        submission.problem_specification = problem
        logger.info(f"Fetched problem {problem.id} for submission {submission.id}")
    except Exception as e:
        logger.error(f"Error while fetching problem: {e}")
        return True
    

    # * ----------------------------------
    # * Save problem specification
    # * ----------------------------------
    try:
        save_problem_specification(submission.problem_specification)
        logger.info(f"Problem specification saved successfully: \n\n{submission.problem_specification}\n")
    except Exception as e:
        logger.error(f"Error while saving problem specification: {e}")


    # * ----------------------------------
    # * Run subcontainers
    # * ----------------------------------
    logger.info(f"Running containers for submission {submission.id} with image {submission.comp_image} and mainfile {submission.mainfile}")
    result: Optional[SubmissionResultSchema] = run_containers(
        submission_host_path,
        problem_host_path,
        submission.comp_image,
        submission.mainfile,
    )
    logger.info(f"Containers finished for submission {submission.id}")
    logger.info(f"Result for submission {submission.id}: \n\n{result}\n")
    logger.info(f"{Ansi.BOLD.value}{NAME}{Ansi.RESET.value} has finished processing submission {submission.id}.")
    if result:
        result.debug = fetch_debug_logs(os.path.join(logs_local_path, "worker.log"))

    # * ----------------------------------
    # * Report result
    # * ----------------------------------
    try:
        report_result(submission.id, result)
    except Exception as e:
        print(f"Error while reporting result: {e}")


    # * ----------------------------------
    # * Archive worker files if debug mode is enabled
    # * ----------------------------------


    if IS_DEBUG_MODE_ENABLED:
        try:
            archive_worker_files()
        except Exception as e:
            print(f"Error while archiving worker files: {e}")
            return True
    
    return False

def run_containers(
    submission_path: str,
    tests_path: str,
    comp_image: str,
    mainfile: Optional[str] = None,
) -> Optional[SubmissionResultSchema]:
    
    mainfile = mainfile or "main.py"
    conf_path = os.path.join(DATA_HOST_PATH, "conf")
    artifacts_bin_path = os.path.join(DATA_HOST_PATH, "bin")
    artifacts_std_path = os.path.join(DATA_HOST_PATH, "std")
    artifacts_out_path = os.path.join(DATA_HOST_PATH, "out")
    
    try: 
        client = docker.from_env()
        run_container(
            client=client,
            image=comp_image,
            environment={
                "SRC": "/data/src",
                "OUT": "/data/out",
                "BIN": "/data/bin",
                "MAINFILE": mainfile,
            },
            volume_mappings=[
                VolumeMappingSchema(host_path=submission_path, container_path="/data/src"),
                VolumeMappingSchema(host_path=artifacts_bin_path, container_path="/data/bin", read_only=False),
                VolumeMappingSchema(host_path=artifacts_out_path, container_path="/data/out", read_only=False),
            ],
        )
    except Exception as e:
        print(f"Error while running compiler container: {e}")
        return None

    try:
        run_container(
            client=client,
            image=EXEC_IMAGE,
            environment={
                "LOGS": "off",
                "IN": "/data/in",
                "OUT": "/data/out",
                "STD": "/data/std",
                "BIN": "/data/bin",
                "CONF": "/data/conf",
            },
            volume_mappings=[
                VolumeMappingSchema(host_path=tests_path, container_path="/data/in"),
                VolumeMappingSchema(host_path=conf_path, container_path="/data/conf"),
                VolumeMappingSchema(host_path=artifacts_bin_path, container_path="/data/bin"),
                VolumeMappingSchema(host_path=artifacts_std_path, container_path="/data/std", read_only=False),
                VolumeMappingSchema(host_path=artifacts_out_path, container_path="/data/out", read_only=False),
            ],
        )
    except Exception as e:
        print(f"Error while running execution container: {e}")
        return None


    try:
        run_container(
            client=client,
            image=JUDGE_IMAGE,
            volume_mappings=[
                VolumeMappingSchema(host_path=tests_path, container_path="/data/ans"),
                VolumeMappingSchema(host_path=artifacts_std_path, container_path="/data/in"),
                VolumeMappingSchema(host_path=artifacts_out_path, container_path="/data/out", read_only=False),
            ],
            environment={
                "LOGS": "off",
                "IN": "/data/in",
                "OUT": "/data/out",
                "ANS": "/data/ans",
            },
        )
    except Exception as e:
        print(f"Error while running judge container: {e}")
        return None


    try:
        result: SubmissionResultSchema = get_results(os.path.join(DATA_LOCAL_PATH, "out"))
    except Exception as e:
        print(f"Error while getting results: {e}")
        return None

    return result


if __name__ == "__main__":
    mainloop()
