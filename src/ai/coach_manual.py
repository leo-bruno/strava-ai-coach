"""Developer-only opt-in execution of the existing synthetic context fixture."""

import argparse
import sys

from src.ai.coach import CoachError, CoachInvalidResponseError, generate_coach_response
from src.ai.training_knowledge import load_training_knowledge
from src.ui.coach_response import render_coach_response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-real-api-call", action="store_true",
        help="Opt in to one potentially paid OpenAI request using synthetic data.",
    )
    parser.add_argument(
        "--diagnose-validation", action="store_true",
        help="Show only a safe code and fixed explanation if response validation fails.",
    )
    args = parser.parse_args(argv)
    if not args.allow_real_api_call:
        parser.error("A real call requires --allow-real-api-call.")
    # Only this developer command imports a test fixture; runtime does not.
    from src.ai.coach_response_fixtures_test import context_fixture

    context = context_fixture()
    try:
        response = generate_coach_response(context)
        output = render_coach_response(response, context=context, knowledge=load_training_knowledge())
    except CoachError as error:
        if args.diagnose_validation and isinstance(error, CoachInvalidResponseError):
            print(error.validation_diagnostic, file=sys.stderr)
        else:
            print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
