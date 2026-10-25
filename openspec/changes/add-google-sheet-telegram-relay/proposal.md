# Add private Google Sheets Telegram delivery

## Why
The owner already has a working private Apps Script bot and requests sending approved website messages through that bot.

## What Changes
Add an optional Google transport to the existing market channel publishing panel. Queue immutable approved text, use a hashed high-entropy relay credential and one-time delivery claims, and accept idempotent receipts. Provide a complete Apps Script bundle that privately polls the website and sends with the existing bot.

## Impact
Additive messaging schema/API, admin UI, Apps Script extension, deployment and owner setup. No live messages, Google installation or server deployment during development. Preserve direct and MTProto transports and existing private bot features.
