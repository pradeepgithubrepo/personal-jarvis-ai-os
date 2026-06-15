import json
from pathlib import Path

from google.auth.transport.requests import (
    Request,
)
from google.oauth2.credentials import (
    Credentials,
)
from google_auth_oauthlib.flow import (
    InstalledAppFlow,
)
from googleapiclient.discovery import (
    build,
)
from loguru import logger

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


class GmailClient:

    def __init__(self):
        self.credentials_path = (
            "configs/google_credentials.json"
        )

        self.token_dir = Path("tokens")

    def authenticate_all_accounts(self):
        registry_path = (
            "configs/mailbox_registry.json"
        )

        with open(
            registry_path,
            "r",
        ) as file:
            accounts = json.load(file)

        gmail_services = []

        for account in accounts:
            account_name = account["name"]

            logger.info(
                f"Authenticating: "
                f"{account_name}"
            )

            service = (
                self.authenticate_account(
                    account_name
                )
            )

            gmail_services.append(
                {
                    "account": account_name,
                    "service": service,
                }
            )

        return gmail_services

    def authenticate_account(
        self,
        account_name: str,
    ):
        token_path = (
            self.token_dir
            / f"{account_name}_token.json"
        )

        creds = None

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path),
                SCOPES,
            )

        if (
            creds
            and creds.expired
            and creds.refresh_token
        ):
            creds.refresh(Request())

        elif not creds:
            flow = (
                InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    SCOPES,
                )
            )

            creds = (
                flow.run_local_server(
                    port=0
                )
            )

            token_path.write_text(
                creds.to_json()
            )

        service = build(
            "gmail",
            "v1",
            credentials=creds,
        )

        profile = (
            service.users()
            .getProfile(userId="me")
            .execute()
        )

        logger.success(
            f"Connected Gmail: "
            f"{profile['emailAddress']}"
        )

        return service