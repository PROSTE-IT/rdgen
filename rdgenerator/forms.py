import re

from django import forms
from django.conf import settings
from PIL import Image

from .settings_catalog import ADVANCED_SETTING_GROUPS, ADVANCED_SETTINGS

# App/company names are interpolated into single/double-quoted bash sed
# scripts in every generator workflow: & \ | corrupt the substitution
# silently, ' " $ ` break shell quoting, CR/LF break sed addressing.
UNSAFE_NAME_CHARS = re.compile(r'[&\\|\'"$`\r\n]')

class GenerateForm(forms.Form):
    sh_secret_field = forms.CharField(required=False)
    #Platform
    platform = forms.ChoiceField(choices=[('windows','Windows 64-bit'),('windows-x86','Windows 32-bit'),('linux','Linux'),('android','Android'),('macos','macOS')], initial='windows')
    version = forms.ChoiceField(choices=[('master','nightly'),('1.4.9','1.4.9'),('1.4.8','1.4.8'),('1.4.7','1.4.7'),('1.4.6','1.4.6'),('1.4.5','1.4.5'),('1.4.4','1.4.4'),('1.4.3','1.4.3'),('1.4.2','1.4.2'),('1.4.1','1.4.1'),('1.4.0','1.4.0')], initial='1.4.9')
    help_text="Wersja „master” to kompilacja rozwojowa (nightly) z najnowszymi funkcjami, która może być mniej stabilna."
    delayFix = forms.BooleanField(initial=True, required=False)

    #General
    exename = forms.CharField(label="Nazwa pliku EXE", required=True)
    appname = forms.CharField(label="Niestandardowa nazwa aplikacji", required=False)
    buildProfile = forms.ChoiceField(
        label="Profil aplikacji",
        choices=[
            ('standard', 'Aplikacja standardowa'),
            (
                'android_helpdesk',
                'Android Helpdesk (Google Play, tylko połączenia przychodzące)',
            ),
            (
                'quick_support',
                'Quick Support (przenośna lub instalowalna, tylko połączenia przychodzące)',
            ),
        ],
        initial='standard',
        required=False,
    )
    direction = forms.ChoiceField(widget=forms.RadioSelect, choices=[
        ('incoming', 'Tylko przychodzące'),
        ('outgoing', 'Tylko wychodzące'),
        ('both', 'Dwukierunkowe')
    ], initial='both')
    installation = forms.ChoiceField(label="Wyłączenie instalacji", choices=[
        ('installationY', 'Nie — zezwól na instalację'),
        ('installationN', 'Tak — wyłącz instalację')
    ], initial='installationY')
    settings = forms.ChoiceField(label="Wyłączenie ustawień", choices=[
        ('settingsY', 'Nie — pokaż ustawienia'),
        ('settingsN', 'Tak — wyłącz ustawienia')
    ], initial='settingsY')
    androidappid = forms.CharField(label="Niestandardowy identyfikator aplikacji Android", required=False)

    #Custom Server
    serverIP = forms.CharField(label="Host", required=False)
    serverPort = forms.CharField(label="Port", required=False)
    apiServer = forms.CharField(label="Serwer API", required=False)
    key = forms.CharField(label="Klucz publiczny", required=False)
    urlLink = forms.CharField(label="Niestandardowy adres odnośników", required=False)
    downloadLink = forms.CharField(label="Niestandardowy adres pobierania aktualizacji", required=False)
    compname = forms.CharField(label="Nazwa firmy",required=False)

    #Visual
    iconfile = forms.FileField(label="Niestandardowa ikona aplikacji (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    logofile = forms.FileField(label="Niestandardowe logo aplikacji (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    privacyfile = forms.FileField(label="Niestandardowy ekran prywatności (PNG)", required=False, widget=forms.FileInput(attrs={'accept': 'image/png'}))
    iconbase64 = forms.CharField(required=False)
    logobase64 = forms.CharField(required=False)
    privacybase64 = forms.CharField(required=False)
    theme = forms.ChoiceField(choices=[
        ('light', 'Jasny'),
        ('dark', 'Ciemny'),
        ('system', 'Zgodny z systemem')
    ], initial='system')
    themeDorO = forms.ChoiceField(choices=[('default', 'Domyślne'),('override', 'Wymuszone')], initial='default')

    #Security
    passApproveMode = forms.ChoiceField(choices=[('password','Akceptuj hasłem'),('click','Akceptuj kliknięciem'),('password-click','Akceptuj hasłem lub kliknięciem')],initial='password-click')
    permanentPassword = forms.CharField(widget=forms.PasswordInput(), required=False)
    #runasadmin = forms.ChoiceField(choices=[('false','No'),('true','Yes')], initial='false')
    denyLan = forms.BooleanField(initial=False, required=False)
    enableDirectIP = forms.BooleanField(initial=False, required=False)
    #ipWhitelist = forms.BooleanField(initial=False, required=False)
    autoClose = forms.BooleanField(initial=False, required=False)

    #Permissions
    permissionsDorO = forms.ChoiceField(choices=[('default', 'Domyślne — użytkownik może zmienić'),('override', 'Wymuszone — użytkownik nie może zmienić')], initial='default')
    permissionsType = forms.ChoiceField(choices=[('custom', 'Niestandardowe'),('full', 'Pełny dostęp'),('view','Tylko udostępnianie ekranu')], initial='custom')
    enableKeyboard =  forms.BooleanField(initial=True, required=False)
    enableClipboard = forms.BooleanField(initial=True, required=False)
    enableFileTransfer = forms.BooleanField(initial=True, required=False)
    enableAudio = forms.BooleanField(initial=True, required=False)
    enableTCP = forms.BooleanField(initial=True, required=False)
    enableRemoteRestart = forms.BooleanField(initial=True, required=False)
    enableRecording = forms.BooleanField(initial=True, required=False)
    enableBlockingInput = forms.BooleanField(initial=True, required=False)
    enableRemoteModi = forms.BooleanField(initial=False, required=False)
    hidecm = forms.BooleanField(initial=False, required=False)
    enablePrinter = forms.BooleanField(initial=True, required=False)
    enableCamera = forms.BooleanField(initial=True, required=False)
    enableTerminal = forms.BooleanField(initial=True, required=False)

    #Other
    removeWallpaper = forms.BooleanField(initial=True, required=False)

    defaultManual = forms.CharField(widget=forms.Textarea, required=False)
    overrideManual = forms.CharField(widget=forms.Textarea, required=False)

    #custom added features
    xOffline = forms.BooleanField(initial=False, required=False)
    removeNewVersionNotif = forms.BooleanField(initial=False, required=False)
    supportAddressBook = forms.BooleanField(initial=False, required=False)
    supportAddressBookUrl = forms.URLField(
        initial='https://rdbk.prosteit.pl', required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        grouped_settings = {
            group: [] for group in ADVANCED_SETTING_GROUPS
        }
        for setting in ADVANCED_SETTINGS:
            common = {
                'label': setting['label'],
                'required': False,
                'help_text': setting.get('help', ''),
            }
            if setting['kind'] == 'boolean':
                field = forms.BooleanField(**common)
            elif setting['kind'] == 'choice':
                field = forms.ChoiceField(
                    choices=[('', 'Nie ustawiaj')] + setting['choices'],
                    **common,
                )
            elif setting['kind'] == 'number':
                field = forms.IntegerField(
                    min_value=setting.get('min'),
                    max_value=setting.get('max'),
                    widget=forms.NumberInput(attrs={'placeholder': 'Nie ustawiaj'}),
                    **common,
                )
            else:
                widget = (
                    forms.PasswordInput(render_value=True)
                    if setting['kind'] == 'password'
                    else forms.TextInput(attrs={'placeholder': 'Nie ustawiaj'})
                )
                field = forms.CharField(widget=widget, **common)
            self.fields[setting['field']] = field
            grouped_settings[setting['group']].append({
                'field': self[setting['field']],
                'key': setting['key'],
                'kind': setting['kind'],
                'search': f"{setting['label']} {setting['key']}",
            })

        self.advanced_setting_groups = [
            {
                'id': group,
                'label': label,
                'settings': grouped_settings[group],
            }
            for group, label in ADVANCED_SETTING_GROUPS.items()
        ]

    def clean(self):
        cleaned_data = super().clean()
        build_profile = cleaned_data.get('buildProfile') or 'standard'
        cleaned_data['buildProfile'] = build_profile
        if build_profile == 'quick_support':
            if cleaned_data.get('platform') != 'windows':
                self.add_error(
                    'platform',
                    'Quick Support jest obecnie dostępny tylko dla Windows 64-bit.',
                )
            if cleaned_data.get('version') != '1.4.9':
                self.add_error(
                    'version',
                    'Quick Support wymaga obecnie RustDesk 1.4.9.',
                )
            cleaned_data.update({
                'direction': 'incoming',
                'installation': 'installationY',
                'settings': 'settingsN',
                'supportAddressBook': False,
                'removeNewVersionNotif': True,
                'permanentPassword': '',
                'hidecm': False,
            })
        elif build_profile == 'android_helpdesk':
            if cleaned_data.get('platform') != 'android':
                self.add_error(
                    'platform',
                    'Profil Android Helpdesk wymaga platformy Android.',
                )
            if cleaned_data.get('version') != '1.4.9':
                self.add_error(
                    'version',
                    'Profil Android Helpdesk wymaga obecnie RustDesk 1.4.9.',
                )
            cleaned_data.update({
                'direction': 'incoming',
                'supportAddressBook': False,
                'removeNewVersionNotif': True,
                'androidappid': settings.ANDROID_HELPDESK_APP_ID,
                'appname': settings.ANDROID_HELPDESK_APP_NAME,
                'permanentPassword': '',
                'passApproveMode': 'click',
                'hidecm': False,
            })
        if cleaned_data.get('supportAddressBook'):
            if cleaned_data.get('platform') != 'windows':
                self.add_error(
                    'platform',
                    'Integracja RDBK jest obecnie dostępna tylko dla Windows 64-bit.',
                )
            if cleaned_data.get('version') != '1.4.9':
                self.add_error(
                    'version',
                    'Integracja RDBK wymaga obecnie RustDesk 1.4.9.',
                )
            if not cleaned_data.get('supportAddressBookUrl'):
                self.add_error(
                    'supportAddressBookUrl',
                    'Podaj adres URL API backendu RDBK.',
                )
            if cleaned_data.get('direction') == 'incoming':
                if not (cleaned_data.get('permanentPassword') or '').strip():
                    self.add_error(
                        'permanentPassword',
                        'Windows Helpdesk wymaga stałego hasła do dostępu nienadzorowanego.',
                    )
                if cleaned_data.get('passApproveMode') == 'click':
                    self.add_error(
                        'passApproveMode',
                        'Windows Helpdesk musi zezwalać na uwierzytelnianie hasłem.',
                    )
        return cleaned_data

    def clean_iconfile(self):
        print("checking icon")
        image = self.cleaned_data['iconfile']
        if image:
            try:
                # Open the image using Pillow
                img = Image.open(image)

                # Check if the image is a PNG (optional, but good practice)
                if img.format != 'PNG':
                    raise forms.ValidationError("Dozwolone są wyłącznie obrazy PNG.")

                # Get image dimensions
                width, height = img.size

                # Check for square dimensions
                if width != height:
                    raise forms.ValidationError("Ikona aplikacji musi być kwadratowa.")
                
                return image
            except OSError:  # Handle cases where the uploaded file is not a valid image
                raise forms.ValidationError("Nieprawidłowy plik ikony.")
            except Exception as e: # Catch any other image processing errors
                raise forms.ValidationError(f"Błąd przetwarzania ikony: {e}")

    def _reject_unsafe_name_chars(self, field):
        value = self.cleaned_data.get(field, '')
        if value and UNSAFE_NAME_CHARS.search(value):
            raise forms.ValidationError(
                "Zawiera znaki nieobsługiwane przez skrypty budowania "
                "(& \\ | ' \" $ ` lub znak nowej linii)."
            )
        return value

    def clean_appname(self):
        return self._reject_unsafe_name_chars('appname')

    def clean_compname(self):
        return self._reject_unsafe_name_chars('compname')
