# Telegram channel connection via MTProto

Deploy both committed archives and update.sh with the usual APP_ROOT=/srv/tirexa updater. The updater installs Telethon from requirements.txt and runs messaging migration 0011. Existing HTTPS/Bale settings remain the default.

In Admin > Messaging > Commodity channel drafts:
1. Select MTProto proxy as the Telegram connection method.
2. Obtain an application API ID and API Hash in your own https://my.telegram.org account under API development tools. Enter them in the admin form, never in a chat or source control. The API Hash is write-only and an empty save preserves it.
3. Keep the bot token and @channel destination configured; the bot must administer the channel with post_messages permission.
4. Paste one tg://proxy or https://t.me/proxy link per line, or import a UTF-8 .txt file under 50 KB. Up to 20 saved links are allowed. Only classic hexadecimal and dd links are supported; ee/FakeTLS and base64 links are explicitly rejected.
5. Save, then test individual proxies from the server. The test authenticates the bot and checks channel membership/permission but does not publish anything. Put a passing proxy first; sending considers at most the first three links.
6. Generate a preview, then explicitly publish the selected report. If a previous attempt is uncertain, first inspect the channel. Only if the message is absent should an administrator use the explicit not-delivered review action; it enables a separate retry without sending by itself.

MTProto requires no personal user session, phone number or login code in this application. A transient in-memory bot session is used and discarded after each operation. Proxy DNS is restricted and pinned to public IPs. Failover happens only before sendMessage begins. Once sending starts, a network failure remains uncertain and is never automatically repeated. Telegram RPC rejection after sending starts is conservatively treated as uncertain too.

Verification: backend unit/API tests and frontend browser tests use mocked transports; they do not publish to real channels. A live end-to-end check requires the owner's application credentials and a proxy reachable from the production server. Local dependency download was blocked by DNS/network access during development; deployment must successfully install requirements before using MTProto.

References: https://docs.telethon.dev/en/stable/basic/signing-in.html and https://core.telegram.org/method/auth.importBotAuthorization
