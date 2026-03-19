#! /usr/bin/env python3

import argparse

import sys

import lisp_parser

# predicate symbol used for defining a linear order
ORDERING_PRED_SYM = '<'


# Returns the component of the given domain or problem whose keyword fits the
# given keyword.
def get_domain_or_problem_component(domain_or_problem, component_keyword):
    for component in domain_or_problem:
        if not isinstance(component, list):
            continue
        if component[0] == component_keyword:
            return component[1]

# Returns a copy of the given domain or problem component where the component's
# keyword and possible type information are removed.
def copy_component_excluding_keyword_and_types(domain_or_problem_component):
    # This function assumes that there is a keyword at index 0.
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
# mentioned in the given goal. The goal is assumed to be STRIPS, i.e. a
# conjunction of (grounded) atoms.
def get_predicates_of_strips_goal(goal):
    predicate_symbols_in_goal = set(atom[0] for atom in goal[1:])
    covered_predicate_symbols = set()
    goal_predicates = []
    for atom in goal[1:]:
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
        if component[0] == ":axiom":
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
                                  move_strips_goal_to_init = False):
    objects = []
    init_index = None
    old_goal = []
    for index, component in enumerate(problem):
        if not isinstance(component, list):
            continue
        if component[0] == ":objects":
            objects = copy_component_excluding_keyword_and_types(component)
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
            g_atoms = []
            for goal_atom in old_goal[1:]:
                g_predicate_symbol = goal_atom[0] + "_g"
                g_atoms.append([g_predicate_symbol] + goal_atom[1:])
            initial_state.extend(g_atoms)
    return problem

# Converts the given list back into a string in PDDL format.
def to_pddl_string(parsed_pddl):
    if not isinstance(parsed_pddl, list):
        return parsed_pddl

    output = ""
    for element in parsed_pddl:
        output = output + to_pddl_string(element) + " "
    output = output[:-1] # remove trailing space character

    output = "(" + output + ")"
    if isinstance(parsed_pddl[0], str) and (parsed_pddl[0] == "problem" or
                                            parsed_pddl[0] == "domain" or ':' in
                                            parsed_pddl[0]):
        output = output + "\n"
    return output

def main():
    parser = argparse.ArgumentParser(
            description="")
            # TODO add description that explains purpose and output of the
            # program, and the assumptions of the -s flag
            # output: PDDL domain file without actions, PDDL problem file with
            # legality predicate as goal; UPDATE NEEDED after added goal
            # verification
    parser.add_argument("domain", help="PDDL domain with legality constraints")
    parser.add_argument("problem", help="PDDL problem to verify against domain")
    parser.add_argument("-o", "--output-file-prefix",
                        help="write the verifying domain into file <OUTPUT_FILE_PREFIX>-domain.pddl and the verifying problem into file <OUTPUT_FILE_PREFIX>-problem.pddl.")
    parser.add_argument("-s", "--strips-goal", action='store_true',
                        help="With this option the program assumes that the goal is a STRIPS goal and, instead of verifying the goal directly, adds g-versions (see program description) of the goal atoms to the initial state.")

    args = parser.parse_args()

    with open(args.domain, 'r') as domain_file:
        domain = lisp_parser.parse_nested_list(domain_file)
    with open(args.problem, 'r') as problem_file:
        problem = lisp_parser.parse_nested_list(problem_file)

    legality_predicate = get_domain_or_problem_component(domain,
                                                         ":legality-predicate")
    goal = get_domain_or_problem_component(problem, ":goal")
    domain_goal = get_domain_or_problem_component(domain, ":domain-goal")

    # The list of predicates of the output domain must include the
    # ORDERING_PRED_SYM (defining a linear order over the objects). If the
    # strips_goal flag is set then also g-versions of the predicates mentioned
    # in the goal must be included.
    needed_predicates = [[ORDERING_PRED_SYM, '?x1', '?x2']]
    if args.strips_goal:
        # TODO check more thoroughly whether goal is STRIPS?
        if goal[0] != "and":
            print(f"Error: Expected goal to start with 'and' but got '{old_goal[0]}'.")
            sys.exit(1)
        for predicate in get_predicates_of_strips_goal(goal):
            needed_predicates.append([predicate[0] + "_g"] + predicate[1:])
    else:
        verify_non_strips_goal(goal, domain_goal)

    domain = convert_domain_to_verifiable(domain, needed_predicates)
    problem = convert_problem_to_verifiable(problem,
                                            legality_predicate,
                                            args.strips_goal)

    output_domain_string = to_pddl_string(domain)
    output_problem_string = to_pddl_string(problem)

    print("Verifying domain:")
    print("-----------------")
    print(output_domain_string)
    print("")
    print("Verifying problem:")
    print("------------------")
    print(output_problem_string)
    print("")

    if args.output_file_prefix:
        print("Writing verifying domain to file")
        print(f"{args.output_file_prefix}-domain.pddl")
        print("and verifying problem to file")
        print(f"{args.output_file_prefix}-problem.pddl")
        with open(f"{args.output_file_prefix}-domain.pddl", "w") as f:
            f.write(output_domain_string)
        with open(f"{args.output_file_prefix}-problem.pddl", "w") as f:
            f.write(output_problem_string)
        print("Done writing")

if __name__ == "__main__":
    main()

