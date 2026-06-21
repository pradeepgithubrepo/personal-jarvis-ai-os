# skills/mobile/mobile_noise_filter.py

from loguru import logger


class MobileNoiseFilter:

    @staticmethod
    def is_noise(signal: dict) -> bool:
        """
        Returns True if the signal is classified as noise/garbage and should be dropped.
        """
        sender = (signal.get("sender") or "").strip().lower()
        message = (signal.get("message") or "").strip().lower()
        source = (signal.get("source") or "").strip().lower()

        # 1. Obvious empty or null values
        if not message:
            logger.info("Mobile Noise Filter: Dropped empty message.")
            return True

        # Discard OTPs right away
        if (
            "otp" in message or
            "verification code" in message or
            "one-time password" in message or
            "securesubmit" in message
        ):
            logger.info(f"Mobile Noise Filter: Dropped OTP message: '{message}'")
            return True

        # 2. WhatsApp system notifications
        if source == "whatsapp":
            # "You may have new messages", "WhatsApp is running", etc.
            whatsapp_noise = [
                "checking for new messages",
                "whatsapp is running",
                "this message was deleted",
                "you deleted this message",
                "incoming voice call",
                "incoming video call",
                "missed voice call",
                "missed video call",
                "photo", # just photo status without text
                "video", # just video status without text
                "audio",
                "sticker",
                "gif"
            ]
            for term in whatsapp_noise:
                if term in message:
                    logger.info(f"Mobile Noise Filter: Dropped WhatsApp system/media noise: '{message}'")
                    return True

        # 3. SMS noise/spam system senders or known overlay keywords
        if source == "sms":
            sms_noise_keywords = [
                "tap to view",
                "click here to view",
                "truecaller",
                "overlay notification"
            ]
            for term in sms_noise_keywords:
                if term in message:
                    logger.info(f"Mobile Noise Filter: Dropped SMS noise keyword: '{message}'")
                    return True

        return False
