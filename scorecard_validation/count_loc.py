from subprocess import Popen, PIPE

from scorecard_validation.utils import REPO_PATH


def count_loc() -> int:
    raw_count = _run_count_in_shell()
    return _parse_count(raw_count)


def _parse_count(raw_count_out: str) -> int:
    all_files = raw_count_out.splitlines()
    lines_per_file = {e.lstrip().rstrip().split(" ")[1]: e.lstrip().rstrip().split(" ")[0] for e in all_files}
    filtered_files = dict()
    for path, loc in lines_per_file.items():
        if path == "total":
            # Ignore the total line as its not accurate - not all files should count towards this LoC measure
            continue
        elif "docs" in path.split("/")[0]:
            # Ignore any python code in a top level docs directory - likely examples etc.
            continue
        elif "tests" in path.split("/")[0]:
            # Ignore any python code in a top level tests directory - likely unit tests etc.
            continue
        else:
            filtered_files[path] = int(loc)

    total = sum(filtered_files.values())
    return total


def _run_count_in_shell() -> str:
    """
    Runs the command:
    git ls-files | grep '\.py' | xargs wc -l
    and returns the string output
    """
    cmd = "git ls-files | grep '\.py' | xargs wc -l"
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=REPO_PATH, shell=True)
    stdout, stderr = p.communicate()
    raw_count_output = stdout.decode("utf-8")

    return raw_count_output
