"""Reliability demo: constructs SonarQube typically reports as BUGS.

The module imports cleanly and is never executed by the tests, so it is also
uncovered. Exact findings depend on the analyzer version - record yours.
"""


def unreachable_after_return(value):
    return value * 2
    print("never printed")  # unreachable code (S1763)


def ignores_result(name):
    name.upper()  # return value ignored (S2201)
    return name


def always_false(items):
    if len(items) < 0:  # always false (S3981)
        return "negative length"
    return "ok"


def duplicate_branch_condition(x):
    if x > 10:
        return "big"
    elif x > 10:  # same condition twice (S1862)
        return "huge"
    return "small"


def self_assignment(total):
    total = total  # self assignment (S1656)
    return total


def float_equality():
    return 0.1 + 0.2 == 0.3  # floating point equality (S1244)


def typo_operator(counter):
    counter =+ 1  # looks like += (S2757)
    return counter


def raises_string():
    raise "this is not an exception"  # S5632
