"""Manually exchange a Strava authorization code without exposing tokens."""

import argparse
import subprocess

from src.strava.auth import (
    REQUESTED_AUTHORIZATION_SCOPES,
    build_authorization_url,
    exchange_authorization_code,
    persist_refresh_token,
)


def main() -> None:
    """Prepare or complete the local Strava authorization-code flow."""
    parser = argparse.ArgumentParser(
        description="Exchange a Strava authorization code for OAuth tokens."
    )
    parser.add_argument(
        "authorization_code",
        nargs="?",
        help="Authorization code from Strava",
    )
    parser.add_argument(
        "--authorization-url",
        action="store_true",
        help="Print an authorization URL requesting the required activity-read scopes.",
    )
    parser.add_argument(
        "--redirect-uri",
        help="Registered redirect URI to use when creating an authorization URL.",
    )
    arguments = parser.parse_args()

    if arguments.authorization_url:
        if arguments.authorization_code:
            parser.error("Do not provide an authorization code with --authorization-url.")
        if not arguments.redirect_uri:
            parser.error("--redirect-uri is required with --authorization-url.")
        print(build_authorization_url(arguments.redirect_uri))
        return

    if not arguments.authorization_code:
        parser.error("authorization_code is required unless --authorization-url is used.")

    token_data = exchange_authorization_code(arguments.authorization_code)
    refresh_token = token_data.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise RuntimeError("Strava authorization response did not include a refresh token.")

    granted_scope = token_data.get("scope")
    granted_scopes = set(granted_scope.split()) if isinstance(granted_scope, str) else set()
    missing_scopes = set(REQUESTED_AUTHORIZATION_SCOPES) - granted_scopes
    if missing_scopes:
        raise RuntimeError("Strava authorization did not grant the required scopes.")

    persist_refresh_token(refresh_token)

    try:
        subprocess.run(["pbcopy"], input=refresh_token, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("Could not copy the refresh token to the clipboard.") from error

    print(f"Granted OAuth scope: {granted_scope}")
    print("Authorization-code exchange succeeded.")
    print("The new refresh token has been copied to the clipboard.")


if __name__ == "__main__":
    main()
