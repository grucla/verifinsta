#! /usr/bin/env python3

import argparse

import lisp_parser


def convert_domain_to_verifiable(domain):
    legality_predicate = ""
    to_remove = []
    for index, component in enumerate(domain):
        if not isinstance(component, list):
            continue
        if component[0] == ":predicates":
            component.append(['<', '?obj1', '?obj2'])
        if component[0] == ":domain-goal":
            to_remove.append(index)
        if component[0] == ":action":
            to_remove.append(index)
        if component[0] == ":legality-predicate":
            legality_predicate = component[1]
            to_remove.append(index)
        if component[0] == ":axiom":
            component[0] =  ":derived"
    domain = [component for (index, component) in enumerate(domain) if index not in to_remove]
    return (domain, legality_predicate)

def extract_objects(problem_component):
    to_remove = []
    for index, element in enumerate(problem_component):
        if element == ":objects":
            to_remove.append(index)
        if element == "-":
            to_remove.append(index)
            to_remove.append(index+1)
    objects = [element for (index, element) in enumerate(problem_component) if index not in to_remove]
    return objects

def add_ordering(initial_state, objects):
    for index, smaller_obj in enumerate(objects):
        ordering_atoms = [['<', smaller_obj, larger_obj] for larger_obj in objects[index+1:]]
        initial_state.extend(ordering_atoms)
    return initial_state

def convert_problem_to_verifiable(problem, legality_predicate):
    init_index = None
    objects = []
    for index, component in enumerate(problem):
        if not isinstance(component, list):
            continue
        if component[0] == ":objects":
            objects = extract_objects(component)
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

def stringify(pddl_input):
    if not isinstance(pddl_input, list):
        return pddl_input + " "

    output = ""
    for element in pddl_input:
        output = output + stringify(element)

    output = "(" + output + ")"
    if isinstance(pddl_input[0], str) and (pddl_input[0] == "problem" or
                                           pddl_input[0] == "domain" or ':' in
                                           pddl_input[0]):
        output = output + "\n"
    return output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", help="PDDL domain with legality constraints")
    parser.add_argument("problem", help="PDDL problem to verify against domain")
    parser.add_argument("-o", "--output-file-prefix",
                        help="write the verifying domain into file '<prefix>-domain.pddl' and the verifying problem into file '<prefix>-problem.pddl'.")

    args = parser.parse_args()

    with open(args.domain, 'r') as domain_file:
        domain = lisp_parser.parse_nested_list(domain_file)
    with open(args.problem, 'r') as problem_file:
        problem = lisp_parser.parse_nested_list(problem_file)

    (domain, legality_predicate) = convert_domain_to_verifiable(domain)
    problem = convert_problem_to_verifiable(problem, legality_predicate)

    output_domain_string = stringify(domain)
    output_problem_string = stringify(problem)

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

    # output: PDDL domain file without actions, PDDL problem file with
    # legality predicate as goal

if __name__ == "__main__":
    main()

