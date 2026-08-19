"""Minimal SMS adapter used for mobile OTP delivery.

No SMS gateway is wired up yet (there's no Twilio/MSG91/etc. account
configured for this project). When SMS_PROVIDER is left as "console" (the
default), the message is just logged instead of sent, so the OTP flow can
still be developed and tested end-to-end without a paid SMS account — the
code also comes back in the API response's debug_code field in that case.

To go live: set SMS_PROVIDER to a real value and fill in send_sms() below
with that provider's API call (e.g. Twilio's client.messages.create(...)).
"""
import logging

from core.settings import Settings

log = logging.getLogger(__name__)


def send_sms(*, to_phone: str, message: str) -> bool:
    if Settings.SMS_PROVIDER == "console" or not Settings.SMS_PROVIDER:
        log.warning("SMS_PROVIDER is not configured; SMS to %s would read:\n%s", to_phone, message)
        return False

    # Plug in a real provider here once one is configured, e.g.:
    #
    # if Settings.SMS_PROVIDER == "twilio":
    #     from twilio.rest import Client
    #     client = Client(Settings.TWILIO_ACCOUNT_SID, Settings.TWILIO_AUTH_TOKEN)
    #     client.messages.create(to=to_phone, from_=Settings.TWILIO_FROM_NUMBER, body=message)
    #     return True

    log.warning("SMS_PROVIDER=%s has no implementation in utils/sms.py yet", Settings.SMS_PROVIDER)
    return False
