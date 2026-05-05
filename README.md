# Verifinsta

This repository contains the code for `verifinsta`, a tool for *ver*ifying
*if* a given planning problem is an *insta*nce of a given planning domain.

The core functionality of `verifinsta` is a conversion of the given domain and
problem such that any planner can do the actual verification. If the planner
finds a solution for the converted domain + problem then the given problem is a
legal instance of the given domain.

For the conversion, `verifinsta` expects the given domain file to be in the
format described by [Grundke et al. (2024)](#grundke-et-al-2024) which is an
extension of [PDDL 2.2](#pddl-22). The problem file should be in PDDL 2.2. The
[Input File Format](#input-file-format) section below describes the relevant
changes between PDDL 2.2 and the extended format by Grundke et al. The
`examples` folder of this repository contains two domains and problems that can
be used as input for `verifinsta` and that are in the required format. For
further details about PDDL 2.2 and the extended format please see the related
papers mentioned in the [References](#references) section.

**NOTE:** `verifinsta` does not check PDDL-conformity of the input files. This
includes, for example, not checking whether atoms in the initial state have the
same arity as their predicate symbols defined in the domain file and whether
they are grounded / initialised with objects of types allowed by the predicate
symbol.


## Setup

Install [Python](https://www.python.org/) if it is not already installed.

Clone this repository:
```
git clone https://github.com/grucla/verifinsta.git verifinsta
```

Optionally, create and activate a virtual environment (to keep your system clean
by capsulating verifinsta and its dependencies):
```
python3 -m venv --prompt verifinsta-env verifinsta/.venv
source verifinsta/.venv/bin/activate
```

(You can deactivate the virtual environment with `deactivate`.)

Install `verifinsta` and its dependencies:
```
pip install verifinsta/
```

You can test your installation with
```
python3 -m verifinsta -h
```
which should show you `verifinsta`'s help message.

If you do not already have a planner or if you want to use `verifinsta`'s
`--full` option, see the following section for setting up the Fast Downward
planner to use with `verifinsta`.

### Setting Up a Planner

If you do not have a planner yet, or if you want to do the conversion and
verification in a single step, you can follow these steps to install the
[Fast Downward](https://github.com/aibasel/downward) planner:

Install [Apptainer](https://github.com/apptainer/apptainer) if it is not
already installed. For installing Apptainer on Ubuntu you can for example
download the AMD64 deb package from
<https://github.com/apptainer/apptainer/releases> and then call (this example
is for Apptainer version 1.4.5) `sudo apt install ./apptainer_1.4.5_amd64.deb`.

After installing Apptainer, call it as follows to download the
Fast Downward (version 24.06) planner:
```
apptainer pull fast-downward.sif docker://aibasel/downward:24.06
```

You can use the obtained `fast-downward.sif` file to do the verification
separately from the conversion, or you can use the `--full` option of
`verifinsta.py` to do both in one step. (This latter part assumes that the
`fast-downward.sif` file is in the folder where you execute `verifinsta`.)
See the following section for an example.


## Example Usage

To convert the childsnack domain and problem (from the `examples` folder) such
that a planner can do the actual verification, execute:

```
python3 -m verifinstay -o verifying verifinsta/examples/childsnack-domain.pddl verifinsta/examples/childsnack-problem.pddl
```

(With the `-o` option and its argument `verifying` the program not just prints
the output but also writes it to the two files `verifying-domain.pddl` and
`verifying-problem.pddl`.)

Then, call a planner on `verifying-domain.pddl` and `verifying-problem.pddl`.
If you obtained the Fast Downward planner as described in the
[Setting Up a Planner](#setting-up-a-planner) section, you can call it for
example like this:
```
./fast-downward.sif verifying-domain.pddl verifying-problem.pddl --search "eager(single(blind()))"
```

If the planner can find a solution (the empty plan) then the original problem
is a legal instance of the original domain.

For the childsnack example above the planner should find a solution, thus
verifying that `childsnack-problem.pddl` is a legal instance of
`childsnack-domain.pddl`. Uncommenting the line with `(at tray1 table1)` (l.20)
in `childsnack-problem.pddl` makes it an illegal instance for
`childsnack-domain.pddl`. Doing the conversion for the modified problem (with
the unchanged domain) results in an unsolvable planning problem.

### Conversion and Verification in One Step

If you obtained the Fast Downward planner as described in the
[Setting Up a Planner](#setting-up-a-planner) section, you can do the
conversion and verification in single step by using `verifinsta`'s `--full`
option. For the childsnack example, call `verifinsta` like this:
```
python3 -m verifinsta --full verifinsta/example/childsnack-domain.pddl verifinsta/example/childsnack-problem.pddl
```


## Input File Format

The format by [Grundke et al. (2024)](#grundke-et-al-2024) extends PDDL domains
with a domain-wide goal formula and a *legality query* defined by a *legality
predicate* and a logic program consisting of PDDL axioms. For these extensions,
`verifinsta` expects the following three keywords in the given domain file:

- `:legality-predicate` is a single derived predicate with arity zero. The
  legality query returns true if this predicate is true in the initial state of
  the given problem.
- `:domain-goal` is a first-order logic formula. It must be identical to the goal
  formula of the given problem file (with the `-s` option the `verifinsta`
  makes an exception for STRIPS goals, see below for details).
- `:axiom` is a PDDL axiom similar to those identified by the keyword
  `:derived`. Some `:axiom` must define the legality predicate because
  otherwise the legality query is not well-defined.

A given problem belongs to a given domain if the problem goal is identical to
the domain goal (see below if you want to allow STRIPS goals) and the legality
query returns true for the initial state of the problem. The legality query is
defined by the legality predicate and the logic program consisting of all
axioms in the domain file. While `:derived`-axioms are relevant for both the
legality query and action applicability, `:axiom`-axioms are only relevant for
the legality query and can be ignored for action applicability.

The difference between the two kinds of PDDL axioms is that `:axiom`s may use
additional predicates, like the linear order predicate `<`, but the derived
predicates they define may not be used in action definitions or the goal
definition. Axioms with the `:derived` keyword may not use derived predicates
defined by `:axiom`s (but `:axiom`s may use predicates defined by `:derived`).
Some `:axiom` must define the legality predicate such that evaluating the logic
program consisting of all axioms (of both kinds) on the initial state of the
given program determines the output of the legality query.

Note: `verifinsta` assumes (without checking) that the legality query of the
given domain is *order-invariant*, i.e., that the specific order of the objects
does not matter for determining whether the legality predicate is true. The
ordering that `verifinsta` uses is the same as the ordering in the given domain
and problem files where the domain constants are ordered before the problem's
objects.


## Allowing STRIPS Goals

In general `verifinsta` requires the goal of the given problem file to be
identical to the goal of the given domain file. However, if the assumptions
below hold and the `--strips-goal` option is set then `verifinsta` extends the
conversion such that the legality query (defined via the `:axiom`s) of the
input domain can also determine the legality of the problem goal.

Choose this option if your problem files are in STRIPS and your domain file
describes with `:axiom`s which kinds of problem goals are allowed. For an
example, see the `:axiom`s at the end of `blocksworld-domain.pddl` in the
`examples` folder.

If the `--strips-goal` option is set then `verifinsta` assumes the following:

- The goal in the problem file is in STRIPS, i.e., a conjunction of
  propositional atoms.
- For each predicate symbol `somePred` occurring in the problem goal, the
  `:predicates` section of the domain file defines a predicate `somePred_g`
  with the same arity (and same argument types if typing is used) as
  `somePred`. Atoms using these `_g` predicate symbols are assumed to be
  static, i.e., that no action can change their truth value.
- The goal in the domain file is a first-order sentence of the following form.
  It is either a universally quantified implication or a conjunction of
  universally quantified implications. In each such implication, the implicant
  and implicate are both the same single atom except that the implicant uses
  the `_g` version of the implicate's predicate.  For an example of such a
  domain goal, see the `:domain-goal` section of `blocksworld-domain.pddl` in
  the `examples` folder.

Under these assumptions a problem goal is legal (i.e., satisfies the legality
query) if the initial state extended with `_g`-versions of the goal atoms is
legal. Note that a goal is trivially legal if the assumptions hold and the
`:axiom`s in the domain not mention any `_g`-atoms.


## References

### Grundke et al. (2024)

C. Grundke, G. Röger, M. Helmert. Formal Representations of Classical Planning
Domains. In Proceedings of the 34th International Conference on Automated
Planning and Scheduling (ICAPS 2024), pp. 239-248. 2024. DOI:
<https://doi.org/10.1609/icaps.v34i1.31481>

### PDDL 2.2

S. Edelkamp, J. Hoffmann. PDDL2.2: The Language for the Classical Part of
the 4th International Planning Competition. Technical Report 195, University of
Freiburg, Department of Computer Science (2004).


## Todo

Mention that verifinsta allows action costs but ignores them.

Explain assumptions about and semantics of '<' and adjust code accordingly
(especially the check in l.182): Only the legality axioms may mention '<'
(e.g., :predicates cannot mention it) and user must assume that it defines
arbitrary order (although verifinsta uses one specific order).

