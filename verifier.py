#! /usr/bin/env python3

import argparse

import lisp_parser


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
def extract_predicates_from_strips_goal(goal):
    # TODO convert each goal atom (assert that 'goal' is a conjunction of
    # atoms?) into a predicate with parameters (remember to preserve the
    # arity); return a list of those predicates
    return []

def verify_goal(problem, domain_goal):
    # TODO check whether (problem) goal is identical to domain_goal
    # (technically equivalence is sufficient but this is much more difficult to
    # check; is it? think about this)
    pass

def convert_domain_to_verifiable(domain, predicates_to_include):
    to_remove = []
    for index, component in enumerate(domain):
        if not isinstance(component, list):
            continue
        if component[0] == ":predicates":
            for predicate in predicates_to_include:
                # TODO this check fails for typed g-predicates, if parameters
                # use different names, and if arities do not match; Fix: only
                # check if the predicate symbol appears in some predicate list
                # (this check overlooks arity mismatches (between g-predicates
                # extracted from the goal and g-predicates in :predicates) but
                # such mismatches should only happen if something is wrong
                # witht the input of the program
                if not predicate in component:
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

# Adds atoms to the given initial state that define a linear order over the
# given objects.
def add_ordering(initial_state, objects):
    for index, smaller_obj in enumerate(objects):
        ordering_atoms = [['<', smaller_obj, larger_obj] for larger_obj in objects[index+1:]]
        initial_state.extend(ordering_atoms)
    return initial_state

def convert_problem_to_verifiable(problem,
                                  legality_predicate,
                                  move_strips_goal_to_init = False):
    # TODO if move_strips_goal_to_init is True: assert that goal is STRIPS? add
    # g-versions of goal-atoms to initial state
    init_index = None
    objects = []
    for index, component in enumerate(problem):
        if not isinstance(component, list):
            continue
        if component[0] == ":objects":
            objects = copy_component_excluding_keyword_and_types(component)
        if component[0] == ":init":
            init_index = index
        if component[0] == ":goal":
            # replace the original goal with the legality predicate
            component[1] = [legality_predicate]

        if init_index:
            initial_state = problem[init_index]
            predicates = set(atom[0] for atom in initial_state)
            if not '<' in predicates:
                problem[init_index] = add_ordering(initial_state, objects)
            # TODO else verify whether '<' actually defines a linear order over all objects?
    return problem

# Converts the given list back into a string in PDDL format.
def to_pddl_string(parsed_pddl):
    if not isinstance(parsed_pddl, list):
        return parsed_pddl + " "

    output = ""
    for element in parsed_pddl:
        output = output + to_pddl_string(element)

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
                        help="write the verifying domain into file '<prefix>-domain.pddl' and the verifying problem into file '<prefix>-problem.pddl'.")
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

    # The list of predicates of the output domain must include the predicate <
    # (defining a linear order over the objects). If the strips_goal flag is
    # set then also g-versions of the predicates mentioned in the goal must be
    # included.
    needed_predicates = [['<', '?obj1', '?obj2']]
    if args.strips_goal:
        predicates = get_domain_or_problem_component(domain, ":predicates")
        predicates = copy_component_excluding_keyword_and_types(
                [":predicates"] + predicates)
        # TODO check if domain-goal is STRIPS?
        goal_predicates = extract_predicates_from_strips_goal(goal)
        needed_predicates.extend(goal_predicates)
    else:
        verify_goal(goal, domain_goal)

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

    if args.output_file_prefix:
        with open(f"{args.output_file_prefix}-domain.pddl", "w") as f:
            f.write(output_domain_string)
        with open(f"{args.output_file_prefix}-problem.pddl", "w") as f:
            f.write(output_problem_string)

if __name__ == "__main__":
    main()

