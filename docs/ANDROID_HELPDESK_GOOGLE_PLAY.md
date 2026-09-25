# Android Helpdesk — wydanie Google Play

Profil `android_helpdesk` buduje jedną aplikację klientów do przyjmowania
połączeń zdalnych. Nie rejestruje telefonu w RDBK, nie dodaje go do książki
adresowej i nie zawiera mobilnych funkcji dla techników.

## Stała tożsamość aplikacji

Przed pierwszym wysłaniem do Google Play sprawdź wartości środowiskowe RDGen:

```text
ANDROID_HELPDESK_APP_ID=pl.prosteit.helpdesk
ANDROID_HELPDESK_APP_NAME=proste IT Helpdesk
ANDROID_HELPDESK_ARTIFACT_BASENAME=proste-it-helpdesk-android
```

`ANDROID_HELPDESK_APP_ID` staje się trwały po pierwszej publikacji. Nie zmieniaj
go później, ponieważ Google Play potraktuje inny identyfikator jako nową
aplikację.

## Podpisywanie

Workflow korzysta z oddzielnego klucza uploadu. W repozytorium GitHub muszą być
ustawione wszystkie sekrety:

```text
ANDROID_SIGNING_KEY
ANDROID_ALIAS
ANDROID_KEY_STORE_PASSWORD
ANDROID_KEY_PASSWORD
```

`ANDROID_SIGNING_KEY` zawiera cały plik keystore zakodowany Base64. Klucza ani
haseł nie dodawaj do Git. W Google Play włącz Play App Signing; klucz z workflow
jest kluczem uploadu, a nie kluczem podpisującym przechowywanym przez Google.

## Wynik kompilacji

Profil wymusza:

- RustDesk 1.4.9;
- połączenia wyłącznie przychodzące;
- stałą nazwę i identyfikator pakietu;
- brak stałego hasła i akceptację połączenia przez użytkownika;
- brak integracji RDBK;
- wyłączenie komunikatu o aktualizacji RustDesk;
- `compileSdkVersion` i `targetSdkVersion` 36;
- Android Gradle Plugin 8.9.1 i Gradle 8.11.1;
- jeden rosnący `versionCode` wyliczony z wersji PROSTE IT.

Workflow zapisuje dwa pliki:

- `*.aab` — właściwy artefakt do Google Play;
- `*.apk` — podpisany, uniwersalny pakiet do testu lokalnego.

AAB zawiera biblioteki `arm64-v8a`, `armeabi-v7a` oraz `x86_64`. Oba pliki są
zapisywane w historii RDGen i jako krótkotrwały artefakt GitHub Actions.

## Pierwsze wydanie

1. Ustaw i zachowaj klucz uploadu oraz cztery sekrety GitHub.
2. Potwierdź docelowy `ANDROID_HELPDESK_APP_ID` przed uruchomieniem builda.
3. W RDGen wybierz profil `Android Helpdesk`, uzupełnij serwer, port i klucz
   publiczny RustDesk, a następnie uruchom kompilację.
4. Pobierz AAB z Centrum pobierania.
5. Utwórz aplikację w Play Console i włącz Play App Signing.
6. Wyślij AAB ręcznie na kanał Internal Testing.
7. Przejdź deklarację użycia `AccessibilityService`, dodaj politykę prywatności
   i materiały wymagane do weryfikacji.
8. Sprawdź instalację z Google Play, nadawanie uprawnień, połączenie przychodzące
   oraz ponowną aktualizację z wyższym `versionCode`.

Automatyczne wysyłanie do Play Console celowo nie jest częścią pierwszego
etapu. Najpierw należy uzyskać akceptację pierwszej wersji i potwierdzić
działanie aktualizacji na kanale Internal Testing.
