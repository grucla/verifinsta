#! /usr/bin/env python3

import argparse
import os.path
import pathlib
import subprocess
import sys

from . import lisp_parser
from . import profiling

# predicate symbol used for defining a linear order
ORDERING_PRED_SYM = '<'


def parse_command_line_args():
    parser = argparse.ArgumentParser(
            description="Verifinsta is a tool to help verifying if a planning problem is a legal instance of a planning domain. It converts the given domain and given problem to a 'verifying' domain and 'verifying' problem where the 'verifying' problem is solvable (by the empty plan) for the 'veriyfing' domain if the input problem is a legal instance of the input domain. See the --full option for doing this conversion and the actual verification in a single call of verifinsta.")
    parser.add_argument("domain", type=pathlib.Path, help="PDDL 2.2 domain with legality query and domain-wide goal")
    parser.add_argument("problem", type=pathlib.Path, help="PDDL 2.2 problem to verify against the domain")
    parser.add_argument("-o", "--output-file-prefix", type=pathlib.Path,
                        help="write the verifying domain into file <OUTPUT_FILE_PREFIX>-domain.pddl and the verifying problem into file <OUTPUT_FILE_PREFIX>-problem.pddl")
    parser.add_argument("-s", "--strips-goal", action='store_true',
                        help="do not check whether domain goal and problem goal are identical and instead add '_g' versions of the problem goal atoms to the initial state such that the legality query of the domain can verify the problem goal via the '_g' atoms. This option assumes that the problem goal is in STRIPS and that the domain goal requires the problem goal atoms to be true if their '_g' versions are true.")
    parser.add_argument("-f", "--full", action='store_true',
                        help="also run the Fast Downward planner to verify the input. This option assumes that the file 'fast-downward.sif' is present (the file can be pulled via Apptainer from 'docker://aibasel/downward:24.06').")
    parser.add_argument("--planner-output", type=pathlib.Path, help="write the planner output to file PLANNER_OUTPUT, this option is only relevant when --full is set.")
    parser.add_argument("--planner-time-limit", type=int, help="pass PLANNER_TIME_LIMIT to the planner as its time limit in seconds, this option is only relevant when --full is set.")
    parser.add_argument("--planner-memory-limit", type=int, help="pass PLANNER_MEMORY_LIMIT to the planner as its memory limit in MiB, this option is only relevant when --full is set.")

    return parser.parse_args()

# Returns the component of the given domain or problem whose keyword fits the
# given keyword. For components that can appear multiple times like :action, it
# returns the first occurrence.
def get_domain_or_problem_component(domain_or_problem, component_keyword):
    for component in domain_or_problem:
        if not isinstance(component, list):
            continue
        if component[0] == component_keyword:
            return component[1:]
    return []

# Checks if the domain goal has the form assumed by the --strips-goal option
# and whether g-versions of all atoms from the problem goal are mentioned in
# the domain goal.
# Assumed form of domain goal: universally quantified implication or a
# conjuntion of universally quantified implications where the implicates are
# single atoms and the implicants are g-versions of the implicates.
# TODO Allow further conjunctions within all-quantors? This would be more
# convenient for the user.
def check_domain_goal_compatible_with_strips_goal(domain_goal,
                                                  strips_goal_predicates):
    warning_start = "Warning: The domain goal does not match the syntax expected by the --strips-goal option."
    warning_end = "The domain goal is not further checked and might lead to unexpected verification results."
    logic_operator_symbols = {"and", "or", "not", "forall", "exists", "imply"}
    strips_goal_predicate_symbols = set(pred[0] for pred in strips_goal_predicates)
    mentioned_non_g_predicate_symbols = set()
    if domain_goal[0] == "and":
        to_check = domain_goal[1:]
    else:
        to_check = [domain_goal]
    for conjunct in to_check:
        if conjunct[0] != "forall":
            print(warning_start, "Expected")
            print(to_pddl_string(conjunct))
            print(f"to start with 'forall' but got '{conjunct[0]}'.", warning_end)
            return
        # TODO Also check for correct length?
        implication = conjunct[2]
        if implication[0] != "imply":
            print(warning_start, "Expected")
            print(to_pddl_string(implication))
            print(f"to be an implication starting with 'imply' but got '{implication[0]}.'", warning_end)
            return
        # TODO Also check for correct length?
        implicant = implication[1]
        implicate = implication[2]
        if not isinstance(implicant[0], str) or implicant[0].lower() in logic_operator_symbols:
            print(warning_start, "Expected the implicant of implication")
            print(to_pddl_string(implication))
            print("to be a single atom but got '{}'. {}".format(to_pddl_string(implicant), warning_end))
            return
        if not isinstance(implicate[0], str) or implicate[0].lower() in logic_operator_symbols:
            print(warning_start, "Expected the implicate of implication")
            print(to_pddl_string(implication))
            print("to be a single atom but got '{}'. {}".format(to_pddl_string(implicate), warning_end))
            return
        implicant_predicate_symbol = implicant[0]
        implicate_predicate_symbol = implicate[0]
        if implicant_predicate_symbol != implicate_predicate_symbol + "_g":
            print(warning_start, "Expected the implicant of implication")
            print(to_pddl_string(implication))
            print(f"to start with '{implicate_predicate_symbol}_g' but got '{implicant_predicate_symbol}'.", warning_end)
            return
        if implicant[1:] != implicate[1:]:
            print(warning_start, "Expected the arguments of the two atoms in the implication")
            print(to_pddl_string(implication))
            print(f"to be the same but got {implicant[1:]} and {implicate[1:]}.", warning_end)
            return
        mentioned_non_g_predicate_symbols.add(implicate_predicate_symbol)
    uncovered_predicates = strips_goal_predicate_symbols - mentioned_non_g_predicate_symbols
    if uncovered_predicates:
        print(f"Warning: Expected to find all predicates from the problem goal in the domain goal but did not find {uncovered_predicates} in the domain goal. The predicate(s) might be underspecified.")

# Returns a copy of the given domain or problem component where the component's
# keyword and possible type information are removed.
def copy_component_excluding_keyword_and_types(domain_or_problem_component):
    # TODO Make this function consistent with get_domain_or_problem_component
    # such that either this function not expects the input to start with a
    # keyword, or get_domain_or_problem_component does not remove the keyword.
    assert(domain_or_problem_component[0].startswith(':'))
    # The index of the keyword is stored in to_remove such that it can be
    # ignored when copying the input later.
    to_remove = [0]
    for index, element in enumerate(domain_or_problem_component):
        if element == "-":
            # ignore the type information
            to_remove.append(index)
            to_remove.append(index+1)
    cleaned_component_copy = [element for (index, element) in enumerate(domain_or_problem_component) if index not in to_remove]
    return cleaned_component_copy

# Returns a list of all predicates (together with their parameters) that are
# mentioned in the given goal. The goal is assumed to be STRIPS, i.e., a
# conjunction of (grounded) atoms.
def get_predicates_of_strips_goal(goal):
    if len(goal) > 1 and isinstance(goal[1], list):
        normalized_goal = goal
    else:
        normalized_goal = ["and", goal]
    predicate_symbols_in_goal = set(atom[0] for atom in normalized_goal[1:])
    covered_predicate_symbols = set()
    goal_predicates = []
    for atom in normalized_goal[1:]:
        if atom[0] in covered_predicate_symbols:
            continue
        covered_predicate_symbols.add(atom[0])
        goal_pred = [atom[0]]
        for i in range(1,len(atom)):
            goal_pred.append(f"?x{i}")
        goal_predicates.append(goal_pred)
    return goal_predicates

def verify_non_strips_goal(problem_goal, domain_goal):
    if problem_goal != domain_goal:
        print("Warning: The goal in the problem file and the goal in the domain file differ. For full legality they must be equal. STRIPS goals (from problem files) can be treated specially with the -s option.")
        # The program does not exit here because we assume that users are
        # mostly interested in the legality of the initial state, not of the
        # goal.

def convert_domain_to_verifiable(domain, predicates_to_include):
    to_remove = []
    for index, component in enumerate(domain):
        if not isinstance(component, list):
            continue
        if component[0] == ":predicates":
            predicate_symbols = set(pred[0] for pred in component[1:])
            for predicate in predicates_to_include:
                if not predicate[0] in predicate_symbols:
                    component.append(predicate)
        if component[0] == ":domain-goal":
            to_remove.append(index)
        if component[0] == ":action":
            to_remove.append(index)
        if component[0] == ":legality-predicate":
            to_remove.append(index)
        if component[0] == ":legality-axiom" or component[0] == ":axiom":
            # Consider ':axiom' for backwards compatibility reasons.
            component[0] =  ":derived"
    domain = [component for (index, component) in enumerate(domain) if index not in to_remove]
    return domain

# Builds an (arbitrary) linear ordering over the given objects and returns it
# as a list of atoms using predicate symbol ORDERING_PRED_SYM.
def get_ordering_over(objects):
    ordering = []
    for index, smaller_obj in enumerate(objects):
        for larger_obj in objects[index+1:]:
            ordering.append([ORDERING_PRED_SYM, smaller_obj, larger_obj])
    return ordering

def convert_problem_to_verifiable(problem,
                                  legality_predicate,
                                  domain_constants = [],
                                  move_strips_goal_to_init = False):
    objects = domain_constants
    init_index = None
    old_goal = []
    for index, component in enumerate(problem):
        if not isinstance(component, list):
            continue
        if component[0] == ":objects":
            objects += copy_component_excluding_keyword_and_types(component)
        if component[0] == ":init":
            init_index = index
        if component[0] == ":goal":
            old_goal = component[1]
            # replace the original goal with the legality predicate
            component[1] = [legality_predicate]

    if init_index:
        initial_state = problem[init_index]
        predicate_symbols = set(atom[0] for atom in initial_state)

        # Add an (arbitrary) ordering over all objects to the initial state
        # (if there is not yet an ordering defined).
        if not ORDERING_PRED_SYM in predicate_symbols:
            initial_state.extend(get_ordering_over(objects))
        # TODO else verify whether ORDERING_PRED_SYM actually defines a
        # linear order over all objects?

        if move_strips_goal_to_init:
            # Add goal-versions of the atoms in the STRIPS goal to the initial
            # state such that the STRIPS goal can be verified based on the
            # legality constraints from the domain.
            if len(old_goal) > 1 and isinstance(old_goal[1], list):
                normalized_goal = old_goal
            else:
                normalized_goal = ["and", old_goal]
            g_atoms = []
            for goal_atom in normalized_goal[1:]:
                g_predicate_symbol = goal_atom[0] + "_g"
                g_atoms.append([g_predicate_symbol] + goal_atom[1:])
            initial_state.extend(g_atoms)
    return problem

# Converts the given list back into a string in PDDL format.
def to_pddl_string(parsed_pddl):
    if not isinstance(parsed_pddl, list):
        return parsed_pddl

    def transform_list(to_transform):
        if isinstance(to_transform, list):
            yield "("
            first = True
            for item in to_transform:
                if not first:
                    yield " "
                first = False
                yield from transform_list(item)
            if isinstance(to_transform[0], str) and (
                    to_transform[0] == "problem" or
                    to_transform[0] == "domain" or
                    ':' in to_transform[0]):
                yield ")\n"
            else:
                yield ")"
        else:
            yield to_transform

    return "".join(transform_list(parsed_pddl))

def build_verifying_task(domain, problem, args):
    legality_predicate = get_domain_or_problem_component(domain,
                                                         ":legality-predicate")[0]
    domain_constants_component = [":constants"] + get_domain_or_problem_component(domain, ":constants")
    domain_constants = copy_component_excluding_keyword_and_types(domain_constants_component)
    goal = get_domain_or_problem_component(problem, ":goal")[0]
    domain_goal = get_domain_or_problem_component(domain, ":domain-goal")[0]

    # The list of predicates of the output domain must include the
    # ORDERING_PRED_SYM (defining a linear order over the objects). If the
    # strips_goal flag is set then the list of predicates must also include
    # g-versions of the predicates mentioned in the problem goal.
    needed_predicates = [[ORDERING_PRED_SYM, '?x1', '?x2']]
    if get_domain_or_problem_component(domain, ":types"):
        needed_predicates = [[ORDERING_PRED_SYM, '?x1', '-', 'object', '?x2', '-', 'object']]
    if args.strips_goal:
        # TODO Check more thoroughly whether goal is STRIPS?
        if len(goal) > 1 and isinstance(goal[1], list) and goal[0] != "and":
            pddl_goal = to_pddl_string(goal)
            print(f"Error: Expected the (problem) goal to be a single atom or to start with 'and' but got '{pddl_goal}'.")
            sys.exit(1)
        goal_predicates = get_predicates_of_strips_goal(goal)
        check_domain_goal_compatible_with_strips_goal(domain_goal, goal_predicates)

        domain_predicates = get_domain_or_problem_component(domain, ":predicates")
        for goal_predicate in goal_predicates:
            typed_goal_pred = next(
                    pred for pred in domain_predicates if pred[0] ==
                    goal_predicate[0])
            needed_predicates.append([typed_goal_pred[0] + "_g"] +
                                     typed_goal_pred[1:])
    else:
        verify_non_strips_goal(goal, domain_goal)

    verifying_domain = convert_domain_to_verifiable(domain, needed_predicates)
    verifying_problem = convert_problem_to_verifiable(problem,
                                            legality_predicate,
                                            domain_constants,
                                            args.strips_goal)
    return (verifying_domain, verifying_problem)

def main():
    timer = profiling.CombinedTimer()
    memory_measurement = profiling.MemoryMeasurement()

    args = parse_command_line_args()

    with profiling.profiling("Parsing input files"):
        with open(args.domain, 'r') as domain_file:
            domain = lisp_parser.parse_nested_list(domain_file)
        with open(args.problem, 'r') as problem_file:
            problem = lisp_parser.parse_nested_list(problem_file)

    with profiling.profiling("Building verifying domain and problem", block=True):
        (verifying_domain, verifying_problem) = build_verifying_task(domain, problem, args)
        output_domain_string = to_pddl_string(verifying_domain)
        output_problem_string = to_pddl_string(verifying_problem)

    if not args.output_file_prefix and not args.full:
        print("Verifying domain:")
        print("-----------------")
        print(output_domain_string)
        print("")
        print("Verifying problem:")
        print("------------------")
        print(output_problem_string)
        print("")

    output_file_prefix = "verifying"
    if args.output_file_prefix:
        output_file_prefix = args.output_file_prefix

    if args.output_file_prefix or args.full:
        with profiling.profiling("Writing verifying domain and problem to file"):
            with open(f"{output_file_prefix}-domain.pddl", "w") as f:
                f.write(output_domain_string)
            with open(f"{output_file_prefix}-problem.pddl", "w") as f:
                f.write(output_problem_string)

    if args.full:
        print(f"Running the Fast Downward planner on the verifying domain and problem to verify whether the input problem is legal for the input domain. Executing command:")
        # Fast Downward call option explanations:
        # - '--search "eager(single(blind()))"': use a very simple search because
        #   we do not have any actions
        # - '--translate-options --invariant-generation-max-candidates 0':
        #   disable the invariant synthesis because we only have one reachable
        #   state
        downward_arguments = [f'{output_file_prefix}-domain.pddl',
                              f'{output_file_prefix}-problem.pddl',
                              '--search "eager(single(blind()))"',
                              '--translate-options --invariant-generation-max-candidates 0']
        if args.planner_memory_limit:
            downward_arguments.insert(0, f'--overall-memory-limit {args.planner_memory_limit}')
        if args.planner_time_limit:
            downward_arguments.insert(0, f'--overall-time-limit {args.planner_time_limit}')

        downward_call_string = './fast-downward.sif ' + ' '.join(downward_arguments)
        print("'" + downward_call_string + "'")

        if not os.path.isfile("fast-downward.sif"):
            print("Error: Could not find file 'fast-downward.sif'. The input problem could not be verified for the given domain.")
            sys.exit(1)

        with profiling.timing("Running Fast Downward", block=True, children=True):
            planner_result = subprocess.run(downward_call_string, shell=True, capture_output=True)
            planner_exit_code = planner_result.returncode
            if planner_exit_code > 128:
                # Convert exit codes that should have been negative back to
                # their original value
                planner_exit_code = planner_result.returncode - 256
            print(f"Planner exit code: {planner_exit_code}")
            # Clean up temporary files created by Fast Downward
            subprocess.run("./fast-downward.sif --cleanup", shell=True)

        planner_output = planner_result.stdout.decode('unicode_escape')
        translate_memory = [line for line in planner_output.splitlines() if line.startswith("Translator peak memory:")]
        search_memory = [line for line in planner_output.splitlines() if line.startswith("Peak memory:")]
        if translate_memory or search_memory:
            print("Memory reported by planner:")
        if translate_memory:
            print(translate_memory[0])
        if search_memory:
            print(search_memory[0].replace("Peak", "Search peak"))

        if args.planner_output:
            with profiling.profiling("Writing planner output to file"):
                with open(f"{args.planner_output}", "w") as f:
                    f.write(planner_output)

        if "Solution found." in str(planner_result.stdout):
            print("The planner found a solution, verification successful!")
        elif "Search stopped without finding a solution." in str(planner_result.stdout):
            print("The planner did not find a solution. The input problem could not be verified for the given domain.")
        else:
            print("Something went wrong when running the planner. For more details run the planner separately by executing the above mentioned command manually.")

    print(f"Runtime total: {timer}")
    print(f"Memory total: {memory_measurement}")

if __name__ == "__main__":
    main()

