from loguru import logger


class EmailReader:

    def fetch_unread_emails(
        self,
        gmail_services,
        max_results: int = 10,
        ):
        unread_emails = []

        for gmail_account in gmail_services:

            account_name = gmail_account[
                "account"
            ]

            service = gmail_account[
                "service"
            ]

            logger.info(
                f"Fetching unread emails "
                f"for: {account_name}"
            )

            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[
                        "INBOX",
                        "UNREAD",
                    ],
                    q="-category:promotions "
                    "-category:social",
                    maxResults=max_results,
                )
                .execute()
            )

            messages = results.get(
                "messages",
                []
            )

            logger.info(
                f"Unread found: "
                f"{len(messages)}"
            )

            for message in messages:

                message_data = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message["id"],
                    )
                    .execute()
                )

                headers = (
                    message_data
                    .get(
                        "payload",
                        {}
                    )
                    .get(
                        "headers",
                        []
                    )
                )

                subject = self._extract_header(
                    headers,
                    "Subject",
                )

                sender = self._extract_header(
                    headers,
                    "From",
                )

                snippet = message_data.get(
                    "snippet",
                    ""
                )

                unread_emails.append(
                    {
                        "account":
                        account_name,
                        "subject":
                        subject,
                        "sender":
                        sender,
                        "snippet":
                        snippet,
                    }
                )

        logger.success(
            f"Fetched total emails: "
            f"{len(unread_emails)}"
        )

        return unread_emails

    @staticmethod
    def _extract_header(
        headers,
        header_name,
    ):
        for header in headers:
            if (
                header["name"]
                == header_name
            ):
                return header["value"]

        return "Unknown"