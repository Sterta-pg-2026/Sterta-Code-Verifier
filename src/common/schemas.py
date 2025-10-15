from pydantic import BaseModel
from typing import List, Optional


class TestResultSchema(BaseModel):
    test_name: str = ""
    grade: bool = False
    ret_code: int = 0
    time: float = 0
    memory: float = 0
    info: str = ""
 

class SubmissionResultSchema(BaseModel):
    points: int = 0
    info: Optional[str] = None
    test_results: List[TestResultSchema] = []
    
    def __str__(self) -> str:
        ret = ""
        if len(self.test_results) > 0:
            ret += "+------+------+--------+-----+\n"
            ret += "| name | time | memory | ret |\n"
            ret += "+------+------+--------+-----+\n"
            for result in self.test_results:
                color = 131
                if result.grade:
                    color = 65
                if result.ret_code != 0:
                    color = 173
                ret += f"|\033[48;5;{color}m\033[38;5;232m {result.test_name:>4} | "
                ret += f"{result.time:.2f} |{result.memory:>7.0f} | {result.ret_code:>3} \033[0m| {result.info}\n"
            ret += "+------+------+--------+-----+\n"
            ret += "| " + f"points: {self.points}".center(26) + " |\n"
            ret += "+------+------+--------+-----+"
        else:
            ret += "+-------------------+\n"
            ret += "| compilation error |\n"
            ret += "+-------------------+"
        if self.info:
            ret += "\n\033[33mDebug info\033[0m: " + self.info[:-2]
        return ret


class TestSpecificationSchema(BaseModel):
    test_name: str = ""
    time_limit: float = 2
    total_memory_limit: int = 256*1024*1024  # 256 MB
    stack_size_limit: Optional[int] = None


class ProblemSpecificationSchema(BaseModel):
    id: Optional[str]
    tests: List[TestSpecificationSchema] = []

    def __str__(self) -> str:
        ret = ""
        if len(self.tests) > 0:
            ret += "+------+------+-----------+\n"
            ret += "| name | time | memory    |\n"
            ret += "+------+------+-----------+\n"
            for test in self.tests:
                ret += f"| {test.test_name:>4} | "
                ret += f"{test.time_limit:.2f} | {test.total_memory_limit:>9} |\n"
            ret += "+------+------+-----------+"
        return ret


class SubmissionSchema(BaseModel):
    id: str
    comp_image: str
    mainfile: Optional[str] = None
    submitted_by: Optional[str] = None
    problem_specification: Optional[ProblemSpecificationSchema] = None
    

class SubmissionGuiSchema(BaseModel):
    submission_id: str
    problem_id: str
    student_id: str
