# Session recovery

The client seeds the requests cookie jar for `mysmartenergy.psegliny.com`
instead of pinning a Cookie header. Dashboard responses can rotate the
anti-forgery cookie before the following Chart request. A successful connection
test also requires a nonempty Dashboard `__RequestVerificationToken`.

Setup validates the stored cookie and sends a rejected session through the
existing login/MFA flow so refresh services remain available. DNS, timeout, TLS,
and HTTP reachability failures raise `PSEGConnectionError`; setup and maintenance
preserve the stored cookie for a later retry instead of initiating MFA.

Maintenance checks every five minutes and imports statistics at :00 and :30.
The keepalive is best effort: PSEG can still invalidate an active session.
When MFA is pending, automatic login pauses. One manual `psegli.refresh_cookie`
replaces an abandoned challenge; submit only that challenge's code once with
`psegli.enter_mfa_code`. The app has a single mutable browser session, so
concurrent MFA submissions can invalidate each other.

These changes have been used on a PSEG-LI Home Assistant OS installation.
Run the isolated regressions with `python -m unittest discover -s tests -v`
after installing requests and beautifulsoup4. They cover cookie rotation/reset,
Dashboard authentication, transport failures, and the pending-MFA guard.
