This repository contains the code for an instance verifier that checks for a
given planning domain and planning problem if the problem is an
instance of the domain.

TODO: reference grundke-et-al-icaps2024 for formalism that input domain and
input problem are assumed to adhere to; also, explain expected syntax and
mention which keywords are associated with parts added on top of PDDL 2.2

not checks PDDL-conformity

not checks order invariance (TODO should we check this?)

TODO The naming is misleading at the moment. The script is called 'verifier.py'
but does not actually verify something. It only converts the given domain and
instance into a (PDDL-conform) form such that any planner can do the actual
verification (solvable means legal instance, unsolvable means illegal
instance).

TODO explain assumptions of `-s` option: goal should / must have specific form
and g-versions of all goal predicates must be in :predicates

# Example Usage

Convert the domain and problem files such that a planner can do the verification:
```
./verifier.py -o verifying example/domain.pddl example/problem.pddl
```

(With the `-o` option and its argument `verifying` the program also writes the
output to the two files `verifying-domain.pddl` and `verifying-problem.pddl`
instead of only printing it.)

Then, call a planner (e.g.
[Fast Downward](https://github.com/aibasel/downward)) on
`verifying-domain.pddl` and `verifying-problem.pddl`. If the planner can find a
solution (the empty plan) then the original problem is a legal instance of the
original domain.

