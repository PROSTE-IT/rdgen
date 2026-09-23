"""Catalog of RustDesk 1.4.9 advanced client settings exposed by RDGen.

Unchecked boolean controls intentionally do not write ``N``.  They mean
"leave the RustDesk default unchanged".  A checked control writes the action
described by its Polish label (usually ``Y``, occasionally ``N`` for options
worded as "disable ...").
"""

from collections import OrderedDict


ADVANCED_SETTING_GROUPS = OrderedDict([
    ('display', 'Obraz i sesja zdalna'),
    ('general', 'Ogólne i nagrywanie'),
    ('security', 'Bezpieczeństwo i sieć'),
    ('interface', 'Interfejs i zachowanie aplikacji'),
    ('mobile', 'Android i urządzenia mobilne'),
    ('identity', 'Identyfikacja, książka i ustawienia tekstowe'),
])


def _boolean(field, key, label, group, help_text='', checked_value='Y'):
    return {
        'field': field,
        'key': key,
        'label': label,
        'group': group,
        'kind': 'boolean',
        'help': help_text,
        'checked_value': checked_value,
    }


def _choice(field, key, label, group, choices, help_text=''):
    return {
        'field': field,
        'key': key,
        'label': label,
        'group': group,
        'kind': 'choice',
        'choices': choices,
        'help': help_text,
    }


def _number(field, key, label, group, minimum=None, maximum=None, help_text=''):
    return {
        'field': field,
        'key': key,
        'label': label,
        'group': group,
        'kind': 'number',
        'min': minimum,
        'max': maximum,
        'help': help_text,
    }


def _text(field, key, label, group, help_text='', secret=False):
    return {
        'field': field,
        'key': key,
        'label': label,
        'group': group,
        'kind': 'password' if secret else 'text',
        'help': help_text,
    }


LANGUAGE_CHOICES = [
    ('default', 'Język systemu'),
    ('pl', 'Polski'),
    ('en', 'English'),
    ('de', 'Deutsch'),
    ('cs', 'Čeština'),
    ('sk', 'Slovenčina'),
    ('uk', 'Українська'),
    ('ar', 'العربية'),
    ('bg', 'Български'),
    ('ca', 'Català'),
    ('da', 'Dansk'),
    ('el', 'Ελληνικά'),
    ('eo', 'Esperanto'),
    ('es', 'Español'),
    ('et', 'Eesti'),
    ('fa', 'فارسی'),
    ('fr', 'Français'),
    ('he', 'עברית'),
    ('hr', 'Hrvatski'),
    ('hu', 'Magyar'),
    ('id', 'Bahasa Indonesia'),
    ('it', 'Italiano'),
    ('ja', '日本語'),
    ('ko', '한국어'),
    ('kz', 'Қазақша'),
    ('lt', 'Lietuvių'),
    ('lv', 'Latviešu'),
    ('nb', 'Norsk bokmål'),
    ('nl', 'Nederlands'),
    ('pt', 'Português'),
    ('ro', 'Română'),
    ('ru', 'Русский'),
    ('sl', 'Slovenščina'),
    ('sq', 'Shqip'),
    ('sr', 'Srpski'),
    ('sv', 'Svenska'),
    ('th', 'ไทย'),
    ('tr', 'Türkçe'),
    ('vn', 'Tiếng Việt'),
    ('zh-cn', '简体中文'),
    ('zh-tw', '繁體中文'),
]


ADVANCED_SETTINGS = [
    # Display/session defaults.
    _boolean('adv_view_only', 'view-only', 'Domyślnie uruchamiaj sesję tylko do podglądu', 'display'),
    _boolean('adv_show_monitors_toolbar', 'show-monitors-toolbar', 'Pokazuj pasek monitorów', 'display'),
    _boolean('adv_collapse_toolbar', 'collapse-toolbar', 'Domyślnie zwijaj pasek narzędzi', 'display'),
    _boolean('adv_show_remote_cursor', 'show-remote-cursor', 'Pokazuj zdalny kursor', 'display'),
    _boolean('adv_follow_remote_cursor', 'follow-remote-cursor', 'Podążaj za zdalnym kursorem', 'display'),
    _boolean('adv_follow_remote_window', 'follow-remote-window', 'Podążaj za aktywnym zdalnym oknem', 'display'),
    _boolean('adv_zoom_cursor', 'zoom-cursor', 'Skaluj kursor razem z obrazem', 'display'),
    _boolean('adv_show_quality_monitor', 'show-quality-monitor', 'Pokazuj monitor jakości połączenia', 'display'),
    _boolean('adv_disable_audio', 'disable-audio', 'Wycisz dźwięk z komputera zdalnego', 'display'),
    _boolean('adv_enable_file_copy_paste', 'enable-file-copy-paste', 'Włącz kopiowanie plików przez schowek (Windows)', 'display'),
    _boolean('adv_disable_clipboard', 'disable-clipboard', 'Wyłącz tekstowy schowek w sesji', 'display'),
    _boolean('adv_lock_after_session_end', 'lock-after-session-end', 'Blokuj komputer po zakończeniu sesji', 'display'),
    _boolean('adv_privacy_mode', 'privacy-mode', 'Domyślnie włączaj tryb prywatności dla hosta', 'display'),
    _boolean('adv_i444', 'i444', 'Używaj pełnego koloru 4:4:4', 'display'),
    _boolean('adv_reverse_mouse_wheel', 'reverse-mouse-wheel', 'Odwróć kierunek kółka myszy', 'display'),
    _boolean('adv_swap_mouse_buttons', 'swap-left-right-mouse', 'Zamień lewy i prawy przycisk myszy', 'display'),
    _boolean('adv_individual_display_windows', 'displays-as-individual-windows', 'Otwieraj monitory w osobnych oknach', 'display'),
    _boolean('adv_use_all_displays', 'use-all-my-displays-for-the-remote-session', 'Używaj wszystkich lokalnych monitorów', 'display'),
    _boolean('adv_terminal_persistent', 'terminal-persistent', 'Utrzymuj terminal po rozłączeniu', 'display'),
    _boolean('adv_sync_init_clipboard', 'sync-init-clipboard', 'Synchronizuj schowek przy rozpoczęciu sesji', 'display'),
    _choice('adv_view_style', 'view-style', 'Sposób dopasowania obrazu', 'display', [
        ('original', 'Oryginalny rozmiar'),
        ('adaptive', 'Dopasuj do okna'),
    ]),
    _choice('adv_scroll_style', 'scroll-style', 'Sposób przewijania obrazu', 'display', [
        ('scrollauto', 'Automatyczny'),
        ('scrollbar', 'Paski przewijania'),
        ('scrolledge', 'Przewijanie przy krawędzi'),
    ]),
    _choice('adv_image_quality', 'image-quality', 'Jakość obrazu', 'display', [
        ('best', 'Najlepsza'),
        ('balanced', 'Zrównoważona'),
        ('low', 'Niska'),
        ('custom', 'Niestandardowa'),
    ]),
    _choice('adv_codec_preference', 'codec-preference', 'Preferowany kodek', 'display', [
        ('auto', 'Automatycznie'), ('vp8', 'VP8'), ('vp9', 'VP9'),
        ('av1', 'AV1'), ('h264', 'H.264'), ('h265', 'H.265'),
    ]),
    _number('adv_edge_scroll_thickness', 'edge-scroll-edge-thickness', 'Grubość strefy przewijania przy krawędzi', 'display', 20, 150, 'Zakres: 20–150.'),
    _number('adv_custom_image_quality', 'custom-image-quality', 'Niestandardowa jakość obrazu', 'display', 10, 2000, 'Zakres: 10–2000; używane przy jakości „Niestandardowa”.'),
    _number('adv_custom_fps', 'custom-fps', 'Liczba klatek na sekundę', 'display', 5, 120, 'Zakres: 5–120.'),
    _number('adv_trackpad_speed', 'trackpad-speed', 'Prędkość gładzika', 'display', 10, 1000, 'Zakres: 10–1000.'),

    # General behaviour.
    _choice('adv_lang', 'lang', 'Język aplikacji RustDesk', 'general', LANGUAGE_CHOICES),
    _boolean('adv_auto_record_incoming', 'allow-auto-record-incoming', 'Automatycznie nagrywaj sesje przychodzące', 'general'),
    _boolean('adv_auto_record_outgoing', 'allow-auto-record-outgoing', 'Automatycznie nagrywaj sesje wychodzące', 'general'),
    _boolean('adv_hide_recording_button', 'hide-recording-button', 'Ukryj przycisk nagrywania w sesji', 'general'),
    _text('adv_video_save_directory', 'video-save-directory', 'Folder nagrań użytkownika', 'general'),
    _text('adv_windows_service_video_directory', 'windows-service-video-save-directory', 'Folder nagrań usługi Windows', 'general', 'Wymagana bezwzględna ścieżka Windows.'),
    _boolean('adv_allow_auto_update', 'allow-auto-update', 'Zezwól na automatyczne aktualizacje RustDesk', 'general', 'Dotyczy oficjalnego mechanizmu aktualizacji; dla buildów zarządzanych PROSTE IT pozostaw wyłączone.'),
    _boolean('adv_confirm_closing_tabs', 'enable-confirm-closing-tabs', 'Pytaj przed zamknięciem wielu kart', 'general'),
    _boolean('adv_enable_abr', 'enable-abr', 'Włącz adaptacyjny bitrate', 'general'),
    _boolean('adv_open_connections_in_tabs', 'enable-open-new-connections-in-tabs', 'Otwieraj nowe połączenia w kartach', 'general'),
    _boolean('adv_software_render', 'allow-always-software-render', 'Zawsze używaj renderowania programowego', 'general'),
    _boolean('adv_hwcodec', 'enable-hwcodec', 'Włącz kodowanie sprzętowe', 'general'),
    _choice('adv_peer_card_ui', 'peer-card-ui-type', 'Widok kafelków urządzeń', 'general', [
        ('0', 'Duże kafelki'), ('1', 'Małe kafelki'), ('2', 'Lista'),
    ]),
    _choice('adv_peer_sorting', 'peer-sorting', 'Sortowanie urządzeń', 'general', [
        ('Remote ID', 'Identyfikator zdalny'),
        ('Remote Host', 'Nazwa hosta'),
        ('Username', 'Nazwa użytkownika'),
    ]),
    _boolean('adv_sync_ab_recent', 'sync-ab-with-recent-sessions', 'Synchronizuj książkę z ostatnimi sesjami', 'general'),
    _boolean('adv_sync_ab_tags', 'sync-ab-tags', 'Sortuj tagi książki adresowej', 'general'),
    _boolean('adv_filter_ab_intersection', 'filter-ab-by-intersection', 'Filtruj książkę po przecięciu tagów', 'general'),
    _boolean('adv_texture_render', 'use-texture-render', 'Używaj renderowania tekstur', 'general'),

    # Security/network settings not already represented by the main form.
    _boolean('adv_enable_privacy_mode_permission', 'enable-privacy-mode', 'Zezwól technikowi na użycie trybu prywatności', 'security'),
    _text('adv_direct_access_port', 'direct-access-port', 'Port bezpośredniego dostępu IP', 'security', 'Domyślnie 21118.'),
    _text('adv_whitelist', 'whitelist', 'Dozwolone adresy IP / podsieci', 'security', 'Lista rozdzielona przecinkami, np. 192.168.1.0/24,10.0.0.5.'),
    _number('adv_auto_disconnect_timeout', 'auto-disconnect-timeout', 'Limit bezczynności sesji (minuty)', 'security', 1, None, 'Działa z opcją automatycznego zamykania sesji.'),
    _boolean('adv_only_when_window_open', 'allow-only-conn-window-open', 'Zezwalaj na połączenie tylko przy otwartym oknie RustDesk', 'security'),
    _choice('adv_temporary_password_length', 'temporary-password-length', 'Długość hasła jednorazowego', 'security', [
        ('6', '6 znaków'), ('8', '8 znaków'), ('10', '10 znaków'),
    ]),
    _text('adv_proxy_url', 'proxy-url', 'Adres serwera proxy', 'security', 'Obsługiwane: http://, https:// i socks5://.'),
    _text('adv_proxy_username', 'proxy-username', 'Użytkownik proxy', 'security'),
    _text('adv_proxy_password', 'proxy-password', 'Hasło proxy', 'security', 'Wartość poufna — nie udostępniaj zapisanego pliku konfiguracji.', secret=True),
    _boolean('adv_disable_udp_punch', 'enable-udp-punch', 'Wyłącz zestawianie połączeń UDP (hole punching)', 'security', checked_value='N'),
    _boolean('adv_enable_ipv6_punch', 'enable-ipv6-punch', 'Włącz bezpośrednie połączenia IPv6', 'security'),
    _boolean('adv_disable_udp', 'disable-udp', 'Całkowicie wyłącz UDP', 'security'),
    _boolean('adv_allow_insecure_tls', 'allow-insecure-tls-fallback', 'Zezwól na awaryjne połączenie TLS bez weryfikacji', 'security', 'Obniża bezpieczeństwo; używaj wyłącznie świadomie.'),
    _boolean('adv_allow_websocket', 'allow-websocket', 'Zezwól na połączenia WebSocket', 'security'),
    _boolean('adv_allow_https_21114', 'allow-https-21114', 'Zezwól na HTTPS na porcie 21114', 'security'),
    _boolean('adv_allow_numeric_otp', 'allow-numeric-one-time-password', 'Używaj wyłącznie cyfr w haśle jednorazowym', 'security'),
    _boolean('adv_enable_trusted_devices', 'enable-trusted-devices', 'Włącz zaufane urządzenia', 'security'),
    _boolean('adv_allow_logon_password', 'allow-logon-screen-password', 'Zezwól na hasło z ekranu logowania Windows', 'security'),
    _boolean('adv_allow_hostname_as_id', 'allow-hostname-as-id', 'Zezwól używać nazwy hosta jako identyfikatora', 'security'),
    _text('adv_relay_server', 'relay-server', 'Wymuszony serwer relay', 'security'),

    # Interface and policy switches.
    _boolean('adv_disable_group_panel', 'disable-group-panel', 'Ukryj panel dostępnych urządzeń / grup', 'interface'),
    _boolean('adv_disable_discovery_panel', 'disable-discovery-panel', 'Ukryj panel wykrywania urządzeń', 'interface'),
    _boolean('adv_pre_elevate_service', 'pre-elevate-service', 'Automatycznie podnoś uprawnienia wersji portable (Windows)', 'interface'),
    _boolean('adv_allow_remote_cm_modification', 'allow-remote-cm-modification', 'Zezwól na zdalną zmianę ustawień menedżera połączeń', 'interface'),
    _boolean('adv_perm_change_accept_window', 'enable-perm-change-in-accept-window', 'Zezwól zmieniać uprawnienia w oknie akceptacji', 'interface'),
    _boolean('adv_remove_preset_password_warning', 'remove-preset-password-warning', 'Ukryj ostrzeżenie o zapisanym haśle', 'interface'),
    _boolean('adv_hide_general_settings', 'hide-general-settings', 'Ukryj ustawienia ogólne', 'interface'),
    _boolean('adv_hide_security_settings', 'hide-security-settings', 'Ukryj ustawienia bezpieczeństwa', 'interface'),
    _boolean('adv_hide_network_settings', 'hide-network-settings', 'Ukryj ustawienia sieci', 'interface'),
    _boolean('adv_hide_server_settings', 'hide-server-settings', 'Ukryj ustawienia serwera', 'interface'),
    _boolean('adv_hide_proxy_settings', 'hide-proxy-settings', 'Ukryj ustawienia proxy', 'interface'),
    _boolean('adv_hide_websocket_settings', 'hide-websocket-settings', 'Ukryj ustawienia WebSocket', 'interface'),
    _boolean('adv_hide_remote_printer_settings', 'hide-remote-printer-settings', 'Ukryj ustawienia drukarki zdalnej', 'interface'),
    _boolean('adv_hide_username', 'hide-username-on-card', 'Ukryj nazwę użytkownika na karcie urządzenia', 'interface'),
    _boolean('adv_hide_help_cards', 'hide-help-cards', 'Ukryj karty pomocy', 'interface'),
    _boolean('adv_hide_tray', 'hide-tray', 'Ukryj ikonę w zasobniku systemowym', 'interface'),
    _boolean('adv_hide_stop_service', 'hide-stop-service', 'Ukryj możliwość zatrzymania usługi', 'interface'),
    _boolean('adv_one_way_clipboard', 'one-way-clipboard-redirection', 'Włącz jednokierunkowe przekierowanie schowka', 'interface'),
    _boolean('adv_one_way_file_transfer', 'one-way-file-transfer', 'Włącz jednokierunkowy transfer plików', 'interface'),
    _boolean('adv_d3d_render', 'allow-d3d-render', 'Zezwól na renderowanie Direct3D', 'interface'),
    _boolean('adv_main_window_on_top', 'main-window-always-on-top', 'Główne okno zawsze na wierzchu', 'interface'),
    _boolean('adv_ask_for_note', 'allow-ask-for-note', 'Zezwól pytać o notatkę po sesji', 'interface'),
    _boolean('adv_disable_change_password', 'disable-change-permanent-password', 'Zablokuj zmianę stałego hasła', 'interface'),
    _boolean('adv_disable_change_id', 'disable-change-id', 'Zablokuj zmianę identyfikatora', 'interface'),
    _boolean('adv_disable_unlock_pin', 'disable-unlock-pin', 'Zablokuj odblokowanie ustawień kodem PIN', 'interface'),
    _boolean('adv_allow_cli_settings', 'allow-command-line-settings-when-settings-disabled', 'Zezwól zmieniać ustawienia z wiersza poleceń mimo blokady UI', 'interface'),
    _boolean('adv_keep_awake_incoming', 'keep-awake-during-incoming-sessions', 'Nie usypiaj urządzenia podczas sesji przychodzących', 'interface'),
    _boolean('adv_keep_awake_outgoing', 'keep-awake-during-outgoing-sessions', 'Nie usypiaj urządzenia podczas sesji wychodzących', 'interface'),
    _boolean('adv_disable_directx_capture', 'enable-directx-capture', 'Wyłącz przechwytywanie DirectX i użyj GDI (Windows)', 'interface', checked_value='N'),

    # Android/mobile-only settings.
    _boolean('adv_disable_floating_window', 'disable-floating-window', 'Wyłącz pływające okno Android', 'mobile'),
    _number('adv_floating_window_size', 'floating-window-size', 'Rozmiar pływającego okna Android', 'mobile', 32, 320),
    _boolean('adv_floating_window_untouchable', 'floating-window-untouchable', 'Przepuszczaj dotyk przez pływające okno', 'mobile'),
    _number('adv_floating_window_transparency', 'floating-window-transparency', 'Przezroczystość pływającego okna', 'mobile', 0, 10, '0 = niewidoczne, 10 = pełna widoczność.'),
    _choice('adv_keep_screen_on', 'keep-screen-on', 'Utrzymuj ekran Android włączony', 'mobile', [
        ('never', 'Nigdy'),
        ('during-controlled', 'Podczas udostępniania ekranu'),
        ('service-on', 'Gdy usługa działa'),
    ]),
    _boolean('adv_android_half_scale', 'enable-android-software-encoding-half-scale', 'Skaluj obraz o połowę przy kodowaniu programowym Android', 'mobile'),
    _boolean('adv_show_virtual_mouse', 'show-virtual-mouse', 'Pokazuj wirtualną mysz na urządzeniu mobilnym', 'mobile'),
    _boolean('adv_show_virtual_joystick', 'show-virtual-joystick', 'Pokazuj wirtualny joystick na urządzeniu mobilnym', 'mobile'),

    # Textual/specialized values.
    _text('adv_display_name', 'display-name', 'Nazwa wyświetlana klienta', 'identity'),
    _text('adv_preset_ab_name', 'preset-address-book-name', 'Domyślna książka adresowa', 'identity'),
    _text('adv_preset_ab_tag', 'preset-address-book-tag', 'Domyślny tag książki adresowej', 'identity'),
    _text('adv_preset_ab_alias', 'preset-address-book-alias', 'Domyślny alias urządzenia w książce', 'identity'),
    _text('adv_preset_ab_note', 'preset-address-book-note', 'Domyślna notatka urządzenia', 'identity'),
    _text('adv_preset_ab_password', 'preset-address-book-password', 'Domyślne hasło urządzenia w książce', 'identity', 'Wartość poufna — nie udostępniaj zapisanego pliku konfiguracji.', secret=True),
    _text('adv_preset_user_name', 'preset-user-name', 'Domyślna nazwa użytkownika', 'identity'),
    _text('adv_preset_strategy_name', 'preset-strategy-name', 'Domyślna strategia', 'identity'),
    _text('adv_preset_device_group', 'preset-device-group-name', 'Domyślna grupa urządzenia', 'identity'),
    _text('adv_preset_device_username', 'preset-device-username', 'Domyślny użytkownik urządzenia', 'identity'),
    _text('adv_preset_device_name', 'preset-device-name', 'Domyślna nazwa urządzenia', 'identity'),
    _text('adv_preset_note', 'preset-note', 'Domyślna notatka rejestracji', 'identity'),
    _text('adv_default_connect_password', 'default-connect-password', 'Domyślne hasło używane przy łączeniu', 'identity', 'Wartość poufna — nie udostępniaj zapisanego pliku konfiguracji.', secret=True),
]


ADVANCED_BOOLEAN_FIELDS = [
    setting['field'] for setting in ADVANCED_SETTINGS
    if setting['kind'] == 'boolean'
]

ADVANCED_VALUE_SETTINGS = [
    setting for setting in ADVANCED_SETTINGS
    if setting['kind'] != 'boolean'
]


def apply_advanced_settings(target, params):
    """Apply explicit catalog selections to one custom-client settings layer."""
    for setting in ADVANCED_SETTINGS:
        value = params.get(setting['field'])
        if setting['kind'] == 'boolean':
            if value:
                target[setting['key']] = setting.get('checked_value', 'Y')
            continue
        if value not in (None, ''):
            target[setting['key']] = str(value)

