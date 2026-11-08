"""Legacy code: a collection of classic CODE SMELLS (maintainability, tech debt).

Not covered by any test on purpose -> 0% coverage for this file.
"""
import os  # unused import (S1128)
import sys  # unused import (S1128)
import json


# def old_discount(price):          <- commented-out code (S125)
#     return price * 0.9


class order_manager:  # class name violates naming convention (S101)
    pass


def Process_Legacy(a, b, c, d, e, f, g, h, history=[]):  # S100, S107, S5717
    # TODO: refactor this whole function (S1135)
    unused_local = 42  # unused local variable (S1481)
    status = "pending"
    if a == b:
        status = "pending"
    elif a == c:
        status = "pending"
    elif a == d:
        status = "pending"
    else:
        status = "pending"  # duplicated literal "pending" (S1192)
    try:
        history.append(json.dumps({"a": a, "status": status}))
    except:  # bare except (S5754)
        pass
    return status


def uses_eval_but_suppressed(expression):
    return eval(expression)  # NOSONAR  <- shows how suppression comments work
