"""Worker module for STOS distributed task evaluation system.

This module contains the main worker functionality that processes submissions
through a complete evaluation pipeline including compilation, execution,
and judging phases using Docker containers.

The worker continuously polls for new submissions, processes them through
the evaluation workflow, and reports results back to the STOS GUI API.
"""

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
from docker.types import Ulimit
from typing import Dict, List, Optional
from common.schemas import (
    ExecOutputSchema,
    JudgeOutputSchema,
    ProblemSpecificationSchema,
    SubmissionResultSchema,
    TestResultSchema,
    VolumeMappingSchema,
)


POOLING_INTERVAL = 1000e-3  # seconds
FETCH_TIMEOUT = (5, 15)  # seconds
CONTAINERS_TIMEOUT = 250  # seconds
CONTAINERS_FILE_SIZE_LIMIT = "5g"
CONTAINERS_MEMORY_LIMIT = "512m"
HOSTNAME = os.environ["HOSTNAME"]
NAME: str = docker.from_env().containers.get(HOSTNAME).name or HOSTNAME
DATA_LOCAL_PATH = os.path.join(os.environ["WORKERS_DATA_LOCAL_PATH"], NAME)
DATA_HOST_PATH = os.path.join(os.environ["WORKERS_DATA_HOST_PATH"], NAME)

IS_LOGS_IN_RESULT_ENABLED = "true"
IS_DEBUG_MODE_ENABLED = (
    os.environ.get("IS_DEBUG_MODE_ENABLED", "false").lower() == "true"
)
EXEC_IMAGE: str = os.environ["EXEC_IMAGE_NAME"]
JUDGE_IMAGE: str = os.environ["JUDGE_IMAGE_NAME"]


def handle_signal(signum: int, frame: Optional[FrameType]) -> None:
    """Handle interrupt and termination signals.

    Args:
        signum (int): Signal number.
        frame (Optional[FrameType]): Call frame.

    Returns:
        None
    """
    exit(0)


def mainloop() -> None:
    """Main loop that continuously processes submissions.

    Sets up signal handlers and runs the submission processing workflow
    in an infinite loop with configurable polling interval.

    Returns:
        None
    """
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    while True:
        should_wait = True
        try:
            should_wait = process_submission_workflow()
        except Exception as e:
            print(f"An error occurred in the mainloop: {e}")
        if should_wait:
            time.sleep(POOLING_INTERVAL)


def fetch_debug_logs(log_path: Optional[str]) -> Optional[str]:
    """Fetch debug logs from the specified path.

    Args:
        log_path (Optional[str]): Path to the log file.

    Returns:
        Optional[str]: Log content or None if file doesn't exist or error occurred.
    """
    maximum_content_length = 2 * 5000
    try:
        if log_path and os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as log_file:
                content = ""
                for line in log_file:
                    if len(content) + len(line) > maximum_content_length * 2:
                        print("Log file too long, truncating...")
                        break
                    content += line
                return content
    except Exception:
        return None


def get_results(path: str) -> SubmissionResultSchema:
    """Get submission evaluation results from the specified path.

    Args:
        path (str): Path to the directory containing test results and compilation file.

    Returns:
        SubmissionResultSchema: Object containing test results, compilation info and points.
    """

    def fetch_compilation_info(path: str) -> Optional[str]:
        maximum_content_length = 2 * 5000
        comp_file_path = os.path.join(path, "comp.txt")
        try:
            with open(comp_file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = ""
                for line in f:
                    if len(content) + len(line) > maximum_content_length:
                        break
                    content += line

        except Exception:
            return None
        return content if content else None

    result = SubmissionResultSchema()
    points = 0
    test_names: List[str] = []
    for file in os.listdir(path):
        if file.endswith(".judge.json"):
            test_names.append(file.split(".")[0])

    test_names = natsorted(test_names)  # type: ignore
    for test_name in test_names:
        try:
            exec_file_path = os.path.join(path, f"{test_name}.exec.json")
            judge_file_path = os.path.join(path, f"{test_name}.judge.json")
            test_result: TestResultSchema = TestResultSchema(test_name=test_name)

            with open(exec_file_path, "r") as exec_file:
                exec_output = ExecOutputSchema.model_validate_json(
                    json_data=exec_file.read()
                )
                test_result.ret_code = exec_output.return_code
                test_result.time = exec_output.user_time
                test_result.memory = exec_output.total_memory

            with open(judge_file_path, "r") as judge_file:
                judge_output = JudgeOutputSchema.model_validate_json(
                    json_data=judge_file.read()
                )
                test_result.grade = judge_output.grade
                test_result.info = judge_output.info
                if judge_output.grade:
                    points += 1

            result.test_results.append(test_result)
        except Exception:
            test_result = TestResultSchema(
                test_name=test_name, grade=False, info="error while running test"
            )
            result.test_results.append(test_result)

    result.points = points
    try:
        result.info = fetch_compilation_info(path)
    except Exception:
        result.info = "Error while running submission."
        print("Error while fetching compilation info.")

    return result


def init_worker_files() -> None:
    """Initialize worker directory structure.

    Creates necessary directories for worker operations including
    bin, std, out, conf, src, lib, logs, and tests directories.

    Returns:
        None
    """
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
    """Archive worker files to debug directory.

    Creates a backup copy of all worker files in a debug directory
    for troubleshooting and analysis purposes.

    Returns:
        None
    """
    os.umask(0)
    history_local_path = f"{DATA_LOCAL_PATH}_debug"
    if os.path.exists(history_local_path):
        shutil.rmtree(history_local_path)

    backup_path = os.path.join(history_local_path)
    shutil.copytree(DATA_LOCAL_PATH, backup_path)


def save_problem_specification(
    problem_specification: Optional[ProblemSpecificationSchema],
    destination_directory: str,
    name: str = "problem_specification.json",
) -> None:
    """Save problem specification to JSON file.

    Args:
        problem_specification (Optional[ProblemSpecificationSchema]): Problem specification to save.
        destination_directory (str): Destination directory.
        name (str): File name (default: "problem_specification.json").

    Returns:
        None
    """
    if problem_specification:
        problem_specification_local_path = os.path.join(destination_directory, name)
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
    """Run Docker container with specified parameters.

    Args:
        client (docker.DockerClient): Docker client for running containers.
        image (str): Docker image name to run.
        memory_limit (str): Memory limit for the container.
        timeout (int): Timeout limit for container execution.
        environment (Dict[str, str]): Environment variables to pass to container.
        volume_mappings (List[VolumeMappingSchema]): Volume mappings for the container.

    Returns:
        None
    """
    container = client.containers.run(  # type: ignore
        image=image,
        name=f"{NAME}-{image.replace('/', '-').replace(':', '-')}-{int(time.time())}",
        detach=True,
        remove=True,
        mem_limit=memory_limit,
        pids_limit=50,
        ulimits=[
            Ulimit(name="fsize", soft=5 * 1024**3, hard=5 * 1024**3),
            Ulimit(name="nofile", soft=1024, hard=4096),
        ],
        network_disabled=True,
        security_opt=["no-new-privileges"],
        # storage_opt={"size": CONTAINERS_FILE_SIZE_LIMIT},
        environment=environment,
        volumes={
            volume_mapping.key(): volume_mapping.value()
            for volume_mapping in volume_mappings
        },
    )
    container.wait(timeout=timeout)


def process_submission_workflow() -> bool:
    """Process a single submission through the complete evaluation workflow.

    This function handles the entire submission processing pipeline including:
    - Fetching submission and problem data
    - Running compilation, execution, and judging containers
    - Collecting results and reporting back to the API

    Returns:
        bool: True if worker should wait before next attempt, False otherwise.
    """
    submission_local_path: str = os.path.join(DATA_LOCAL_PATH, "src")
    problem_local_path: str = os.path.join(DATA_LOCAL_PATH, "tests")
    lib_local_path: str = os.path.join(DATA_LOCAL_PATH, "lib")
    conf_local_path: str = os.path.join(DATA_LOCAL_PATH, "conf")
    logs_local_path: str = os.path.join(DATA_LOCAL_PATH, "logs")

    submission_host_path: str = os.path.join(DATA_HOST_PATH, "src")
    problem_host_path: str = os.path.join(DATA_HOST_PATH, "tests")
    lib_host_path: str = os.path.join(DATA_HOST_PATH, "lib")
    conf_host_path = os.path.join(DATA_HOST_PATH, "conf")

    artifacts_bin_host_path = os.path.join(DATA_HOST_PATH, "bin")
    artifacts_std_host_path = os.path.join(DATA_HOST_PATH, "std")
    artifacts_out_host_path = os.path.join(DATA_HOST_PATH, "out")

    # * ----------------------------------
    # * 1. Initialize worker files
    # * ----------------------------------
    try:
        init_worker_files()
    except Exception as e:
        print(f"Error while initializing worker files: {e}")
        return True

    logger = get_logger(
        "worker_submission_proccessing_workflow",
        os.path.join(logs_local_path, "worker.log"),
        True,
    )

    # * ----------------------------------
    # * 2. Fetch submission
    # * ----------------------------------
    try:
        submission = adapter.fetch_submission(submission_local_path)
    except Exception as e:
        logger.error(f"Error while fetching submission: {e}")
        return True

    if submission is None:
        # logger.info("No submission fetched.")
        return True

    logger.info(
        f"{Ansi.BOLD.value}{NAME}{Ansi.RESET.value} is starting submission processing workflow."
    )
    logger.info(f"Worker files initialized successfully.")
    logger.info(
        f"Fetched submission {submission.id} for problem {submission.problem_specification.id} by {submission.submitted_by}"
    )
    adapter.change_status(submission.id, "Processing submission...")

    # * ----------------------------------
    # * 3. Fetch problem
    # * ----------------------------------
    adapter.change_status(submission.id, "Fetching problem...")
    try:
        problem = adapter.fetch_problem(
            submission.problem_specification.id, problem_local_path, lib_local_path
        )
        submission.problem_specification = problem
        logger.info(f"Fetched problem {problem.id} for submission {submission.id}")
    except Exception as e:
        logger.error(f"Error while fetching problem: {e}")
        return True

    # * ----------------------------------
    # * 4. Save problem specification
    # * ----------------------------------
    adapter.change_status(submission.id, "Saving problem specification...")
    try:
        save_problem_specification(submission.problem_specification, conf_local_path)
        logger.info(
            f"Problem specification (script.txt) parsed and saved successfully: \n\n{submission.problem_specification}\n"
        )
    except Exception as e:
        logger.error(f"Error while saving problem specification: {e}")
        # * continue processing even if saving problem specification fails

    # * ----------------------------------
    # * 5. Prepare subcontainer parameters
    # * ----------------------------------
    adapter.change_status(submission.id, "Preparing compiler container...")
    logger.info(
        f"Running containers for submission {submission.id} with image {submission.comp_image} and mainfile {submission.mainfile}"
    )

    # * ----------------------------------
    # * 6. Run compiler subcontainer
    # * ----------------------------------
    adapter.change_status(submission.id, "Compiling...")
    logger.info(f"Running compiler container for submission {submission.id}")
    try:
        client = docker.from_env()
        run_container(
            client=client,
            image=submission.comp_image,
            environment={
                "SRC": "/data/src",
                "LIB": "/data/lib",
                "OUT": "/data/out",
                "BIN": "/data/bin",
                "MAINFILE": submission.mainfile or "main.py",
            },
            volume_mappings=[
                VolumeMappingSchema(
                    host_path=submission_host_path, container_path="/data/src"
                ),
                VolumeMappingSchema(
                    host_path=lib_host_path, container_path="/data/lib"
                ),
                VolumeMappingSchema(
                    host_path=artifacts_bin_host_path,
                    container_path="/data/bin",
                    read_only=False,
                ),
                VolumeMappingSchema(
                    host_path=artifacts_out_host_path,
                    container_path="/data/out",
                    read_only=False,
                ),
            ],
        )
    except Exception as e:
        logger.error(f"Error while running compiler container: {e}")
        return True

    # * ----------------------------------
    # * 7. Run execution subcontainer
    # * ----------------------------------
    adapter.change_status(submission.id, "Executing...")
    logger.info(f"Running execution container for submission {submission.id}")
    try:
        client = docker.from_env()
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
                VolumeMappingSchema(
                    host_path=problem_host_path, container_path="/data/in"
                ),
                VolumeMappingSchema(
                    host_path=conf_host_path, container_path="/data/conf"
                ),
                VolumeMappingSchema(
                    host_path=artifacts_bin_host_path, container_path="/data/bin"
                ),
                VolumeMappingSchema(
                    host_path=artifacts_std_host_path,
                    container_path="/data/std",
                    read_only=False,
                ),
                VolumeMappingSchema(
                    host_path=artifacts_out_host_path,
                    container_path="/data/out",
                    read_only=False,
                ),
            ],
        )
    except Exception as e:
        logger.error(f"Error while running execution container: {e}")
        return True

    # * ----------------------------------
    # * 8. Run judge subcontainer
    # * ----------------------------------
    adapter.change_status(submission.id, "Judging...")
    logger.info(f"Running judge container for submission {submission.id}")
    try:
        client = docker.from_env()
        run_container(
            client=client,
            image=JUDGE_IMAGE,
            environment={
                "LOGS": "off",
                "IN": "/data/in",
                "OUT": "/data/out",
                "ANS": "/data/ans",
                "CONF": "/data/conf",
            },
            volume_mappings=[
                VolumeMappingSchema(
                    host_path=problem_host_path, container_path="/data/ans"
                ),
                VolumeMappingSchema(
                    host_path=conf_host_path, container_path="/data/conf"
                ),
                VolumeMappingSchema(
                    host_path=artifacts_std_host_path, container_path="/data/in"
                ),
                VolumeMappingSchema(
                    host_path=artifacts_out_host_path,
                    container_path="/data/out",
                    read_only=False,
                ),
            ],
        )
    except Exception as e:
        logger.error(f"Error while running judge container: {e}")
        return True

    # * ----------------------------------
    # * 9. Fetch results
    # * ----------------------------------
    adapter.change_status(submission.id, "Fetching results...")
    logger.info(f"Fetching results for submission {submission.id}")
    try:
        result: SubmissionResultSchema = get_results(
            os.path.join(DATA_LOCAL_PATH, "out")
        )
    except Exception as e:
        logger.error(f"Error while getting results: {e}")
        return True

    logger.info(f"Containers finished for submission {submission.id}")
    logger.info(f"Result for submission {submission.id}: \n\n{result}\n")
    logger.info(
        f"{Ansi.BOLD.value}{NAME}{Ansi.RESET.value} has finished proccessing submission {submission.id}."
    )
    try:
        result.debug = fetch_debug_logs(os.path.join(logs_local_path, "worker.log"))
    except Exception:
        pass

    # * ----------------------------------
    # * 10. Report result
    # * ----------------------------------
    adapter.change_status(submission.id, "Reporting result...")
    try:
        adapter.report_result(submission.id, result)
    except Exception as e:
        print(f"Error while reporting result: {e}")

    # * ----------------------------------
    # * 11. Archive worker files if debug mode is enabled
    # * ----------------------------------
    if IS_DEBUG_MODE_ENABLED:
        try:
            archive_worker_files()
        except Exception as e:
            print(f"Error while archiving worker files: {e}")
            return True

    return False


if __name__ == "__main__":
    mainloop()
