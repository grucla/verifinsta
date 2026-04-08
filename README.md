This repository contains a preprocessor for verifying whether a given planning
problem is an instance of a given planning domain. The preprocessor converts
the given domain and problem such that any planner can do the actual
verification. If the planner finds a solution for the converted domain +
problem then the given problem is a legal instance of the given domain.

The preprocessor expects the given domain file to be in the format described by
[Grundke et al. (2024)](#grundke-et-al-2024) which is an extension of
[PDDL 2.2](#pddl-22). The problem file should be in PDDL 2.2. The relevant
parts of the extended format by Grundke et al. are described in the [Input File
Format](#input-file-format) section below. For details about PDDL 2.2 and the
extended format we refer to the related papers mentioned in the
[References](#references) section. The `example` folder contains two example
domains and problems in the required format.


# Example Usage

Convert the domain and problem files such that a planner can do the verification:

```
./verifier.py -o verifying example/childsnack-domain.pddl example/childsnack-problem.pddl
```

(With the `-o` option and its argument `verifying` the program not just prints
the output but also writes it to the two files `verifying-domain.pddl` and
`verifying-problem.pddl`.)

Then, call a planner (e.g.
[Fast Downward](https://github.com/aibasel/downward)) on
`verifying-domain.pddl` and `verifying-problem.pddl`. If the planner can find a
solution (the empty plan) then the original problem is a legal instance of the
original domain.

For the childsnack example above the planner should find a solution, thus
verifying that childsnack-problem.pddl is a legal instance of
childsnack-domain.pddl. Uncommenting the line with `(at tray1 table1)` (l.20)
in childsnack-problem.pddl makes it an illegal for childsnack-domain.pddl.


# Input File Format

The format by [Grundke et al. (2024)](#grundke-et-al-2024) extends PDDL domains
with a domain-wide goal formula and a *legality query* defined by a *legality
predicate* and a logic program consisting of PDDL axioms. For these extensions,
the preprocessor expects the following three keywords in the given domain file:

- `:legality-predicate` is a single derived predicate with arity zero. The
  legality query returns true if this predicate is true in the initial state of
  the given problem.
- `:domain-goal` is a first-order logic formula. It must be identical to the goal
  formula of the given problem file (with the `-s` option the preprocessor
  makes an exception for STRIPS goals, see below for details).
- `:axiom` is a PDDL axiom similar to those identified by the keyword
  `:derived`. Some `:axiom` must define the legality predicate because
  otherwise the legality query is not well-defined.

A given problem belongs to a given domain if the problem goal is identical to
the domain goal (see below for an exception) and the legality query returns
true for the initial state of the problem. The legality query is defined by the
legality predicate and the logic program consisting of all axioms in the domain
file. While `:derived`-axioms are relevant for both the legality query and
action applicability, `:axiom`-axioms are only relevant for the legality query
and can be ignored for action applicability.

The difference between the two kinds of PDDL axioms is that `:axiom`s may use
additional predicates, like the linear order predicate `<`, but the derived
predicates they define may not be used in action definitions or the goal
definition. Axioms with the `:derived` keyword may not use derived predicates
defined by `:axiom`s (but `:axiom`s may use predicates defined by `:derived`).
Some `:axiom` must define the legality predicate such that evaluating the logic
program consisting of all axioms (of both kinds) on the initial state of the
given program determines the output of the legality query.


# References

## Grundke et al. (2024)

C. Grundke, G. Röger, M. Helmert. Formal Representations of Classical Planning
Domains. In Proceedings of the 34th International Conference on Automated
Planning and Scheduling (ICAPS 2024), pp. 239-248. 2024. DOI:
<https://doi.org/10.1609/icaps.v34i1.31481>

## PDDL 2.2

S. Edelmap, J. Hoffmann. PDDL2.2: The Language for the Classical Part of
the 4th International Planning Competition. Technical Report 195, University of
Freiburg, Department of Computer Science (2004).


# Todo

The program not checks PDDL-conformity. This includes not checking whether
atoms in the initial state have the same arity as their predicate symbols and
whether they are grounded / initialised with objects of types allowed by the
predicate symbol.

The program not checks order invariance. TODO should we check this?

TODO Explain the assumptions of the `-s` option: the domain goal must have a
specific form and to describe allowed STRIPS goals special g-versions of the
goal atoms must be used in the axioms (and be mentioned in the domain goal).

