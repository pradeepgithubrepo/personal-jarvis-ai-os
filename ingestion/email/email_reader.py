import base64

from loguru import logger


class EmailReader:

    def fetch_unread_emails(
        self,
        gmail_services,
        max_results: int = 40,
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
                    q=(
                        "category:primary "
                        "OR "
                        "category:updates "
                        "-category:promotions "
                        "-category:social"
                    ),
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
                        format="full",
                    )
                    .execute()
                )

                payload = (
                    message_data.get(
                        "payload",
                        {}
                    )
                )

                headers = (
                    payload.get(
                        "headers",
                        []
                    )
                )

                subject = (
                    self._extract_header(
                        headers,
                        "Subject",
                    )
                )

                sender = (
                    self._extract_header(
                        headers,
                        "From",
                    )
                )

                snippet = (
                    message_data.get(
                        "snippet",
                        ""
                    )
                )

                email_body = (
                    self._extract_email_body(
                        payload
                    )
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

                        "body":
                        email_body,
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
                return (
                    header["value"]
                )

        return "Unknown"

    def _extract_email_body(
        self,
        payload,
    ):
        """
        Extract plain text body
        from Gmail payload.
        """

        body = ""

        try:

            if "parts" in payload:

                for part in payload[
                    "parts"
                ]:

                    mime_type = (
                        part.get(
                            "mimeType",
                            ""
                        )
                    )

                    if (
                        mime_type
                        == "text/plain"
                    ):

                        data = (
                            part[
                                "body"
                            ].get(
                                "data"
                            )
                        )

                        if data:

                            decoded = (
                                base64
                                .urlsafe_b64decode(
                                    data
                                )
                                .decode(
                                    "utf-8",
                                    errors="ignore",
                                )
                            )

                            body += (
                                decoded
                            )

            else:

                data = (
                    payload
                    .get(
                        "body",
                        {}
                    )
                    .get(
                        "data"
                    )
                )

                if data:

                    body = (
                        base64
                        .urlsafe_b64decode(
                            data
                        )
                        .decode(
                            "utf-8",
                            errors="ignore",
                        )
                    )

        except Exception as ex:

            logger.warning(
                f"Email body parse "
                f"failed: {ex}"
            )

        return body.strip()