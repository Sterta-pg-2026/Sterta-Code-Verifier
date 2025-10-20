import shutil
import zipfile
from pathlib import Path

# SET = 358
SET = 1571

WD = "/home/stos/Projekt_Inzynierski-2025"
DIR = Path(f"{WD}/test_files/")
SUBMISSIONS_DIR = DIR / f"submissions-{SET}"
TESTS_FILE = DIR / f"tests-{SET}.zip"

TESTS_DST_DIR = f"{WD}/src/gui_mock/test_files/tests-{SET}"
SUBMISSIONS_DST_DIR = Path(f"{WD}/src/gui_mock/test_files/submissions-{SET}")

def extract_test_files():
    # unzip test files
    shutil.rmtree(TESTS_DST_DIR, ignore_errors=True)
    if not Path(TESTS_DST_DIR).exists():
        Path(TESTS_DST_DIR).mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(TESTS_FILE, 'r') as zip_ref:
        zip_ref.extractall(TESTS_DST_DIR)
    

def copy_submission_files():
    # copy submission files
    shutil.rmtree(SUBMISSIONS_DST_DIR, ignore_errors=True)
    if SUBMISSIONS_DST_DIR.exists():
        for item in SUBMISSIONS_DST_DIR.iterdir():
            if item.is_file():
                item.unlink()
    else:
        SUBMISSIONS_DST_DIR.mkdir(parents=True, exist_ok=True)

    for item in SUBMISSIONS_DIR.iterdir():
        if item.is_file():
            dest_file = SUBMISSIONS_DST_DIR / item.name
            with item.open('rb') as src_f, dest_file.open('wb') as dst_f:
                dst_f.write(src_f.read())

if __name__ == "__main__":
    extract_test_files()
    copy_submission_files()