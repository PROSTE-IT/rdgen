# RDGen, a RustDesk client generator to use with your self-hosted RustDesk server

> PROSTE IT: kanoniczna dokumentacja rozwiązania znajduje się w prywatnym
> repozytorium [PROSTE-IT/rdbk](https://github.com/PROSTE-IT/rdbk/blob/feature/shared-address-book/docs/PROSTE_IT_RUSTDESK.md).

The client generator is currently hosted [here](https://rdgen.crayoneater.org).
If you would like to host the generator yourself, see [here](setup.md)

## Features

- Embed server and key into client
- Custom app name
- Custom icon/logo
- Set default settings for the client
- Support for rustdesk advanced settings (https://rustdesk.com/docs/en/self-host/client-configuration/advanced-settings/)

## Generate RustDesk clients from command line instead of using a web browser

Save your configuration from the rdgen web interface, or generate your own, then use that json file with [@AlekseyLapunov's rdgen-cli](https://github.com/AlekseyLapunov/rdgen-cli) to build from the command line on Windows, Linux, or MacOS like this: `python rdgen-cli -f my_config.json --set-version 1.4.5 --set-platform windows -s https://rdgen.crayoneater.org`

## Notes

- Icons should be square (256x256 recommended)
- Avoid special characters or non-English characters in app name and file name
- Build time is currently 30 - 45 minutes

## PROSTE IT managed Helpdesk

RDGen must receive `RDBK_HOST_REGISTRATION_SECRET` with the same long random
value as RDBK before it can build Windows Helpdesk with the background host
agent. Keep it only in deployment secrets; do not commit it. Production should
also set `RDBK_WINDOWS_SIGNER_SUBJECT` to the expected Authenticode certificate
subject after Artifact Signing is enabled.

## PROSTE IT Android Helpdesk

RDGen contains a dedicated `android_helpdesk` profile for the single customer
application distributed through Google Play. It produces a signed AAB plus a
test APK, forces an incoming-only configuration and deliberately has no RDBK
address-book integration. Before the first store build, follow
[`docs/ANDROID_HELPDESK_GOOGLE_PLAY.md`](docs/ANDROID_HELPDESK_GOOGLE_PLAY.md).

