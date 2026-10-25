# Sticky verified purchase inquiry

## Why
The owner requests an inviting sticky purchase inquiry button opening a compact form like the supplied screenshot, and explicitly selects SMS phone verification.

## What Changes
Add a storefront-only floating action and accessible dialog with sheet/rebar, catalog size suggestions, kilogram quantity, optional city/name, mobile and SMS code steps. Submit an existing AssistantInquiry and CRM lead only after verifying a bounded, hashed OTP. Add public request/options/verification endpoints and an optional dedicated Kavenegar OTP template setting.

## Impact
Additive assistant challenge and messaging template migrations. No login, AI call, production SMS or live deployment in development. Existing CRM inquiry flow remains the intake destination.
