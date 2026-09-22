import io
import errno
import mimetypes
import shutil
from functools import wraps
from pathlib import Path
from datetime import datetime, timezone as datetime_timezone
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
import os
import secrets
import re
import requests
import base64
import json
import uuid
import pyzipper
from django.conf import settings as _settings
from django.db import transaction
from django.db.models import F, Q
from .forms import GenerateForm
from .models import BuildVersionSequence, GithubRun
from PIL import Image
from urllib.parse import quote


ARTIFACT_SUFFIXES = {
    '.exe', '.msi', '.apk', '.deb', '.rpm', '.zst', '.appimage', '.flatpak', '.dmg'
}


def bearer_token_required(setting_name):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            configured = str(getattr(_settings, setting_name, '') or '')
            authorization = request.headers.get('Authorization', '')
            scheme, separator, provided = authorization.partition(' ')
            valid = (
                bool(configured)
                and bool(separator)
                and scheme.lower() == 'bearer'
                and secrets.compare_digest(configured, provided)
            )
            if not valid:
                return HttpResponseForbidden('Forbidden')
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


dashboard_token_required = bearer_token_required('RDGEN_DASHBOARD_TOKEN')
upload_token_required = bearer_token_required('RDGEN_UPLOAD_TOKEN')


def _move_to_trash(source, destination):
    try:
        os.replace(source, destination)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        shutil.move(str(source), str(destination))


def _canonical_build_uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise Http404("Build not found")


def _safe_artifact_name(value):
    name = str(value or '')
    if (
        not name
        or Path(name).name != name
        or Path(name).suffix.lower() not in ARTIFACT_SUFFIXES
    ):
        raise Http404("File not found")
    return name


def _artifact_path(uuid_value, filename, require_exists=True):
    build_uuid = _canonical_build_uuid(uuid_value)
    safe_name = _safe_artifact_name(filename)
    root = Path(_settings.EXE_ROOT).resolve()
    build_dir = (root / build_uuid).resolve()
    file_path = (build_dir / safe_name).resolve()
    if file_path.parent != build_dir or root not in build_dir.parents:
        raise Http404("File not found")
    if require_exists and (not file_path.is_file() or file_path.is_symlink()):
        raise Http404("File not found")
    return file_path


def _trash_artifact(uuid_value, filename):
    build_uuid = _canonical_build_uuid(uuid_value)
    safe_name = _safe_artifact_name(filename)
    source = _artifact_path(build_uuid, safe_name)
    trash_root = Path(_settings.EXE_TRASH_ROOT).resolve()
    trash_dir = (trash_root / build_uuid).resolve()
    if trash_root not in trash_dir.parents:
        raise Http404("File not found")
    trash_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(datetime_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = trash_dir / f'{timestamp}-{secrets.token_hex(4)}-{safe_name}'
    _move_to_trash(source, destination)
    return destination


def _trash_build(uuid_value):
    build_uuid = _canonical_build_uuid(uuid_value)
    root = Path(_settings.EXE_ROOT).resolve()
    source = root / build_uuid
    if source.is_symlink() or not source.is_dir():
        raise Http404("Build not found")
    if source.resolve().parent != root:
        raise Http404("Build not found")
    trash_root = Path(_settings.EXE_TRASH_ROOT).resolve()
    trash_dir = (trash_root / build_uuid).resolve()
    if trash_root not in trash_dir.parents:
        raise Http404("Build not found")
    trash_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(datetime_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = trash_dir / f'{timestamp}-{secrets.token_hex(4)}-build'
    _move_to_trash(source, destination)
    return destination


def _available_builds():
    root = Path(_settings.EXE_ROOT)
    if not root.exists():
        return []

    builds = []
    for build_dir in root.iterdir():
        if not build_dir.is_dir() or build_dir.is_symlink():
            continue
        try:
            build_uuid = _canonical_build_uuid(build_dir.name)
        except Http404:
            continue

        artifacts = []
        newest_timestamp = 0
        for candidate in build_dir.iterdir():
            if not candidate.is_file() or candidate.is_symlink():
                continue
            try:
                safe_name = _safe_artifact_name(candidate.name)
                safe_path = _artifact_path(build_uuid, safe_name)
            except Http404:
                continue
            stat = safe_path.stat()
            newest_timestamp = max(newest_timestamp, stat.st_mtime)
            artifacts.append({
                'name': safe_name,
                'size': stat.st_size,
            })

        if artifacts:
            artifacts.sort(key=lambda artifact: artifact['name'].lower())
            builds.append({
                'uuid': build_uuid,
                'created_at': datetime.fromtimestamp(
                    newest_timestamp,
                    tz=datetime_timezone.utc,
                ),
                'artifacts': artifacts,
                'timestamp': newest_timestamp,
            })

    builds.sort(key=lambda build: build['timestamp'], reverse=True)
    return builds[:100]


def use_self_hosted_runner(user_secret):
    """Enable self-hosted builds only for an explicit, non-empty secret."""
    configured_secret = str(_settings.SH_SECRET or "")
    provided_secret = str(user_secret or "")
    return bool(configured_secret and provided_secret) and secrets.compare_digest(
        configured_secret,
        provided_secret,
    )


def remove_new_version_notification(params):
    """Support builds never show the upstream RustDesk update prompt."""
    return bool(
        params.get('supportAddressBook')
        or params.get('buildProfile') == 'quick_support'
        or params.get('removeNewVersionNotif', False)
    )


def allocate_pit_version(base_version):
    """Allocate one shared PROSTE IT revision for a RustDesk base version."""
    base_version = str(base_version or "").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", base_version):
        return "", None

    with transaction.atomic():
        sequence, _ = (
            BuildVersionSequence.objects.select_for_update().get_or_create(
                base_version=base_version,
                defaults={"last_revision": 0},
            )
        )
        BuildVersionSequence.objects.filter(pk=sequence.pk).update(
            last_revision=F("last_revision") + 1,
        )
        sequence.refresh_from_db(fields=["last_revision"])

    revision = sequence.last_revision
    return f"{base_version}-pit.{revision}", revision


def managed_update_channel(
    *, enabled, platform, direction, build_profile='standard'
):
    """Return the immutable managed-update channel compiled into this build."""
    if not enabled or platform != 'windows':
        return ''
    if build_profile == 'quick_support':
        return 'windows_helpdesk'
    if direction == 'incoming':
        return 'windows_helpdesk'
    return 'windows_support'


def generate_custom_client(params, full_url):
    """
    Core generation logic shared by web form and JSON API.

    Args:
        params: dict containing all configuration fields (keys match GenerateForm field names)
        full_url: the full URL of this service (protocol + host)

    Returns:
        dict with 'success' key. On success: also includes 'uuid', 'filename', 'platform', 'log_url'.
        On failure: includes 'error' and optionally 'status_code'.
    """
    user_secret = params.get('sh_secret_field', '')
    selfhosted = use_self_hosted_runner(user_secret)
    platform = params.get('platform', 'windows')
    version = params.get('version', '1.4.9')
    build_profile = params.get('buildProfile') or 'standard'
    quick_support = build_profile == 'quick_support'
    delayFix = params.get('delayFix', True)
    xOffline = params.get('xOffline', False)
    hidecm = params.get('hidecm', False)
    supportAddressBook = bool(
        params.get('supportAddressBook', False) and not quick_support
    )
    removeNewVersionNotif = remove_new_version_notification(params)
    supportAddressBookUrl = (
        params.get('supportAddressBookUrl') or 'https://rdbk.prosteit.pl'
    ).strip()
    if quick_support and (platform != 'windows' or version != '1.4.9'):
        return {
            'success': False,
            'error': 'Quick Support builds require Windows 64Bit and RustDesk 1.4.9.',
            'status_code': 400,
        }
    if supportAddressBook and (platform != 'windows' or version != '1.4.9'):
        return {
            'success': False,
            'error': 'Shared address book builds require Windows 64Bit and RustDesk 1.4.9.',
            'status_code': 400,
        }
    if supportAddressBook and not supportAddressBookUrl:
        return {
            'success': False,
            'error': 'Shared address book API URL is required.',
            'status_code': 400,
        }
    server = params.get('serverIP', '')
    serverPort = params.get('serverPort', '')
    key = params.get('key', '')
    apiServer = params.get('apiServer', '')
    urlLink = params.get('urlLink', '')
    downloadLink = params.get('downloadLink', '')
    if not server:
        server = 'rs-ny.rustdesk.com' #default rustdesk server
    if not serverPort:
        serverPort = '21116' #default rustdesk rendezvous port
    if not key:
        key = 'OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=' #default rustdesk key
    if not apiServer:
        apiServer = server+":21114"
    if not urlLink:
        urlLink = "https://rustdesk.com"
    if not downloadLink:
        downloadLink = "https://rustdesk.com/download"
    direction = 'incoming' if quick_support else params.get('direction', 'both')
    installation = (
        'installationY'
        if quick_support
        else params.get('installation', 'installationY')
    )
    settings = (
        'settingsN'
        if quick_support
        else params.get('settings', 'settingsY')
    )
    appname = params.get('appname', '')
    if not appname:
        appname = "proste IT Quick Support" if quick_support else "rustdesk"
    filename = params.get('exename', 'rustdesk')
    compname = params.get('compname', '')
    if not compname:
        compname = "Purslane Ltd"
    androidappid = params.get('androidappid', '')
    if not androidappid:
        androidappid = "com.carriez.flutter_hbb"
    compname = compname.replace("&","\\&")
    permPass = '' if quick_support else params.get('permanentPassword', '')
    theme = params.get('theme', 'system')
    themeDorO = params.get('themeDorO', 'default')
    passApproveMode = params.get('passApproveMode', 'password-click')
    if supportAddressBook and direction == 'incoming':
        if not str(permPass or '').strip():
            return {
                'success': False,
                'error': 'Windows Helpdesk requires a permanent password for unattended access.',
                'status_code': 400,
            }
        if passApproveMode == 'click':
            return {
                'success': False,
                'error': 'Windows Helpdesk must allow password authentication.',
                'status_code': 400,
            }
    denyLan = params.get('denyLan', False)
    enableDirectIP = params.get('enableDirectIP', False)
    autoClose = params.get('autoClose', False)
    permissionsDorO = params.get('permissionsDorO', 'default')
    permissionsType = params.get('permissionsType', 'custom')
    enableKeyboard = params.get('enableKeyboard', True)
    enableClipboard = params.get('enableClipboard', True)
    enableFileTransfer = params.get('enableFileTransfer', True)
    enableAudio = params.get('enableAudio', True)
    enableTCP = params.get('enableTCP', True)
    enableRemoteRestart = params.get('enableRemoteRestart', True)
    enableRecording = params.get('enableRecording', True)
    enableBlockingInput = params.get('enableBlockingInput', True)
    enableRemoteModi = params.get('enableRemoteModi', False)
    removeWallpaper = params.get('removeWallpaper', True)
    defaultManual = params.get('defaultManual', '')
    overrideManual = params.get('overrideManual', '')
    enablePrinter = params.get('enablePrinter', True)
    enableCamera = params.get('enableCamera', True)
    enableTerminal = params.get('enableTerminal', True)

    if all(char.isascii() for char in filename):
        filename = re.sub(r'[^\w\s-]', '_', filename).strip()
        filename = filename.replace(" ","_")
    else:
        filename = "rustdesk"
    if quick_support and not re.search(r'(?:-qs|_qs)$', filename, re.IGNORECASE):
        filename = f"{filename}-qs"
    if not all(char.isascii() for char in appname):
        appname = "rustdesk"
    myuuid = str(uuid.uuid4())
    pit_version, pit_revision = allocate_pit_version(version)
    update_channel = managed_update_channel(
        enabled=supportAddressBook or quick_support,
        platform=platform,
        direction=direction,
        build_profile=build_profile,
    )

    try:
        iconfile = params.get('iconfile')
        if not iconfile:
            iconfile = params.get('iconbase64')
        iconlink_url, iconlink_uuid, iconlink_file = save_png(iconfile,myuuid,full_url,"icon.png")
    except:
        print("failed to get icon, using default")
        iconlink_url = "false"
        iconlink_uuid = "false"
        iconlink_file = "false"
    try:
        logofile = params.get('logofile')
        if not logofile:
            logofile = params.get('logobase64')
        logolink_url, logolink_uuid, logolink_file = save_png(logofile,myuuid,full_url,"logo.png")
    except:
        print("failed to get logo")
        logolink_url = "false"
        logolink_uuid = "false"
        logolink_file = "false"
    try:
        privacyfile = params.get('privacyfile')
        if not privacyfile:
            privacyfile = params.get('privacybase64')
        privacylink_url, privacylink_uuid, privacylink_file = save_png(privacyfile,myuuid,full_url,"privacy.png")
    except:
        print("failed to get logo")
        privacylink_url = "false"
        privacylink_uuid = "false"
        privacylink_file = "false"

    ###create the custom.txt json here and send in as inputs below
    decodedCustom = {}
    if direction != "Both":
        decodedCustom['conn-type'] = direction
    if installation == "installationN":
        decodedCustom['disable-installation'] = 'Y'
    if settings == "settingsN":
        decodedCustom['disable-settings'] = 'Y'
    if appname.upper != "rustdesk".upper and appname != "":
        decodedCustom['app-name'] = appname
    decodedCustom['override-settings'] = {}
    decodedCustom['default-settings'] = {}
    if permPass != "":
        decodedCustom['password'] = permPass
    if theme != "system":
        if themeDorO == "default":
            if platform == "windows-x86":
                decodedCustom['default-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['default-settings']['theme'] = theme
        elif themeDorO == "override":
            if platform == "windows-x86":
                decodedCustom['override-settings']['allow-darktheme'] = 'Y' if theme == "dark" else 'N'
            else:
                decodedCustom['override-settings']['theme'] = theme
    decodedCustom['enable-lan-discovery'] = 'N' if denyLan else 'Y'
    #decodedCustom['direct-server'] = 'Y' if enableDirectIP else 'N'
    decodedCustom['allow-auto-disconnect'] = 'Y' if autoClose else 'N'

    if permissionsDorO == "default":
        decodedCustom['default-settings']['access-mode'] = permissionsType
        decodedCustom['default-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['default-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['default-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['default-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['default-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['default-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['default-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['default-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['default-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['default-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['default-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['default-settings']['approve-mode'] = passApproveMode
        decodedCustom['default-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['default-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['default-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['default-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['default-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        

    else:
        decodedCustom['override-settings']['access-mode'] = permissionsType
        decodedCustom['override-settings']['enable-keyboard'] = 'Y' if enableKeyboard else 'N'
        decodedCustom['override-settings']['enable-clipboard'] = 'Y' if enableClipboard else 'N'
        decodedCustom['override-settings']['enable-file-transfer'] = 'Y' if enableFileTransfer else 'N'
        decodedCustom['override-settings']['enable-audio'] = 'Y' if enableAudio else 'N'
        decodedCustom['override-settings']['enable-tunnel'] = 'Y' if enableTCP else 'N'
        decodedCustom['override-settings']['enable-remote-restart'] = 'Y' if enableRemoteRestart else 'N'
        decodedCustom['override-settings']['enable-record-session'] = 'Y' if enableRecording else 'N'
        decodedCustom['override-settings']['enable-block-input'] = 'Y' if enableBlockingInput else 'N'
        decodedCustom['override-settings']['allow-remote-config-modification'] = 'Y' if enableRemoteModi else 'N'
        decodedCustom['override-settings']['direct-server'] = 'Y' if enableDirectIP else 'N'
        decodedCustom['override-settings']['verification-method'] = 'use-permanent-password' if hidecm else 'use-both-passwords'
        decodedCustom['override-settings']['approve-mode'] = passApproveMode
        decodedCustom['override-settings']['allow-hide-cm'] = 'Y' if hidecm else 'N'
        decodedCustom['override-settings']['allow-remove-wallpaper'] = 'Y' if removeWallpaper else 'N'
        decodedCustom['override-settings']['enable-remote-printer'] = 'Y' if enablePrinter else 'N'
        decodedCustom['override-settings']['enable-camera'] = 'Y' if enableCamera else 'N'
        decodedCustom['override-settings']['enable-terminal'] = 'Y' if enableTerminal else 'N'
        if direction == 'incoming':
            decodedCustom['override-settings']['custom-rendezvous-server'] = server
            decodedCustom['override-settings']['api-server'] = apiServer

    if defaultManual:
        for line in defaultManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['default-settings'][k.strip()] = value.strip()

    if overrideManual:
        for line in overrideManual.splitlines():
            if '=' in line:
                k, value = line.split('=', 1)
                decodedCustom['override-settings'][k.strip()] = value.strip()
    
    decodedCustomJson = json.dumps(decodedCustom)

    string_bytes = decodedCustomJson.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    encodedCustom = base64_bytes.decode("ascii")

    ####from here run the github action, we need user, repo, access token.
    if platform == 'windows':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'
    if platform == 'windows-x86':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows-x86.yml/dispatches'
    elif platform == 'linux':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-linux.yml/dispatches'
    elif platform == 'android':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-android.yml/dispatches'
    elif platform == 'macos':
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-macos.yml/dispatches'
    else:
        url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-windows.yml/dispatches'
        if selfhosted:
            url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/sh-generator-windows.yml/dispatches'

    inputs_raw = {
        "server":server,
        "serverPort":serverPort,
        "key":key,
        "apiServer":apiServer,
        "custom":encodedCustom,
        "uuid":myuuid,
        "iconlink_url":iconlink_url,
        "iconlink_uuid":iconlink_uuid,
        "iconlink_file":iconlink_file,
        "logolink_url":logolink_url,
        "logolink_uuid":logolink_uuid,
        "logolink_file":logolink_file,
        "privacylink_url":privacylink_url,
        "privacylink_uuid":privacylink_uuid,
        "privacylink_file":privacylink_file,
        "appname":appname,
        "genurl":_settings.GENURL,
        "urlLink":urlLink,
        "downloadLink":downloadLink,
        "delayFix": 'true' if delayFix else 'false',
        "rdgen":'true',
        "xOffline": 'true' if xOffline else 'false',
        "removeNewVersionNotif": 'true' if removeNewVersionNotif else 'false',
        "supportAddressBook": 'true' if supportAddressBook else 'false',
        "RDBK_API_URL": (
            supportAddressBookUrl if supportAddressBook or quick_support else ''
        ),
        "RDBK_UPDATE_CHANNEL": update_channel,
        "RDBK_BUILD_UUID": myuuid,
        "CLIENT_VARIANT": build_profile,
        "PIT_BASE_VERSION": version if pit_version else '',
        "PIT_VERSION": pit_version,
        "PIT_REVISION": str(pit_revision) if pit_revision is not None else '',
        "compname": compname,
        "androidappid":androidappid,
        "filename":filename
    }

    temp_json_path = f"data_{uuid.uuid4()}.json"
    zip_filename = f"secrets_{uuid.uuid4()}.zip"
    zip_path = "temp_zips/%s" % (zip_filename)
    Path("temp_zips").mkdir(parents=True, exist_ok=True)

    with open(temp_json_path, "w") as f:
        json.dump(inputs_raw, f)

    with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(_settings.ZIP_PASSWORD.encode())
        zf.write(temp_json_path, arcname="secrets.json")

    if os.path.exists(temp_json_path):
        os.remove(temp_json_path)

    zipJson = {}
    zipJson['url'] = full_url
    zipJson['file'] = zip_filename

    zip_url = json.dumps(zipJson)

    data = {
        "ref":_settings.GHBRANCH,
        "inputs":{
            "version":version,
            "zip_url":zip_url
        },
        "return_run_details": True
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2026-03-10'
    }
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait",
        filename=filename,
        platform=platform,
        base_version=version if pit_version else '',
        pit_revision=pit_revision,
        pit_version=pit_version,
        connection_direction=direction,
        update_channel=update_channel,
        build_profile=build_profile,
    )
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 204 or response.status_code == 200:
            github_data = response.json()
            print(github_data)
            new_github_run.github_run_id = github_data.get('workflow_run_id')
            new_github_run.status = "in_progress"
            new_github_run.save()

            return {
                "success": True,
                "uuid": myuuid,
                "filename": filename,
                "platform": platform,
                "pit_version": pit_version,
                "update_channel": update_channel,
                "build_profile": build_profile,
                "log_url": github_data.get('html_url')
            }
        else:
            return {
                "success": False,
                "error": "GitHub rejected the start request",
                "status_code": 500
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
            "status_code": 500
        }


def _get_run_status(uuid_val):
    """
    Core status-check logic shared by web form and JSON API.

    Args:
        uuid_val: the UUID string of the generation run

    Returns:
        dict with 'found', 'status', 'github_log_url', and optionally 'gh_run'.
        If not found, 'found' is False.
    """
    try:
        gh_run = GithubRun.objects.get(uuid=uuid_val, deleted_at__isnull=True)
    except GithubRun.DoesNotExist:
        return {"found": False}

    github_log_url = f"https://github.com/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"

    progress = {}
    if gh_run.status not in ['success', 'failure', 'cancelled', 'timed_out', 'skipped', 'action_required']:
        headers = {
            "Authorization": f"Bearer {_settings.GHBEARER}",
            "Accept": "application/vnd.github+json"
        }
        api_url = f"https://api.github.com/repos/{_settings.GHUSER}/{_settings.REPONAME}/actions/runs/{gh_run.github_run_id}"
        
        try:
            gh_response = requests.get(api_url, headers=headers, timeout=10)
            if gh_response.status_code == 200:
                gh_data = gh_response.json()
                
                if gh_data['status'] == 'completed':
                    gh_run.status = gh_data['conclusion']
                    gh_run.save()
                else:
                    progress = _get_run_progress(gh_run.github_run_id, headers)
        except Exception as e:
            print(f"Error checking GitHub: {e}")

    result = {
        "found": True,
        "status": gh_run.status,
        "github_log_url": github_log_url,
        "gh_run": gh_run
    }
    result.update(progress)
    return result


def _get_run_progress(github_run_id, headers):
    """Return approximate step progress for one active GitHub Actions run."""
    fallback = {
        "progress_percent": 5,
        "current_stage": "Oczekiwanie na runner GitHub Actions",
        "completed_steps": 0,
        "total_steps": 0,
    }
    if not github_run_id:
        return fallback

    jobs_url = (
        f"https://api.github.com/repos/{_settings.GHUSER}/"
        f"{_settings.REPONAME}/actions/runs/{github_run_id}/jobs?per_page=100"
    )
    try:
        response = requests.get(jobs_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return fallback
        jobs = response.json().get("jobs") or []
    except (requests.RequestException, ValueError, AttributeError):
        return fallback

    steps = []
    current_stage = ""
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_steps = job.get("steps") or []
        for step in job_steps:
            if not isinstance(step, dict):
                continue
            steps.append(step)
            if not current_stage and step.get("status") == "in_progress":
                current_stage = str(step.get("name") or job.get("name") or "Kompilowanie")
        if not current_stage and job.get("status") == "in_progress":
            current_stage = str(job.get("name") or "Kompilowanie")

    total_steps = len(steps)
    completed_steps = sum(step.get("status") == "completed" for step in steps)
    if total_steps:
        progress_percent = 5 + round((completed_steps / total_steps) * 90)
        progress_percent = max(5, min(95, progress_percent))
    else:
        progress_percent = 5

    return {
        "progress_percent": progress_percent,
        "current_stage": current_stage or fallback["current_stage"],
        "completed_steps": completed_steps,
        "total_steps": total_steps,
    }


def generator_view(request):
    if request.method == 'POST':
        form = GenerateForm(request.POST, request.FILES)
        if form.is_valid():
            params = form.cleaned_data
            full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"
            result = generate_custom_client(params, full_url)
            if result['success']:
                return render(request, 'waiting.html', {
                    'filename': result['filename'],
                    'uuid': result['uuid'],
                    'status': "Starting generator...please wait",
                    'platform': result['platform'],
                    'log_url': result['log_url'],
                    'download_center_url': _settings.RDBK_DOWNLOAD_CENTER_URL,
                })
            else:
                return JsonResponse({"error": result['error']}, status=result.get('status_code', 500))
    else:
        form = GenerateForm()
    #return render(request, 'maintenance.html')
    return render(request, 'generator.html', {
        'form': form,
        'download_center_url': _settings.RDBK_DOWNLOAD_CENTER_URL,
    })


def check_for_file(request):
    filename = request.GET.get('filename')
    uuid = request.GET.get('uuid')
    platform = request.GET.get('platform')

    result = _get_run_status(uuid)
    if not result['found']:
        from django.http import Http404
        raise Http404("Run not found")

    gh_run = result['gh_run']
    github_log_url = result['github_log_url']

    if gh_run.status == "success":
        return render(request, 'generated.html', {
            'filename': filename, 
            'uuid': uuid, 
            'platform': platform,
            'download_center_url': _settings.RDBK_DOWNLOAD_CENTER_URL,
        })
        
    elif gh_run.status in ['failure', 'cancelled', 'timed_out', 'skipped', 'action_required']:
        return render(request, 'failure.html', {
            'log_url': github_log_url, 
            'filename': filename, 
            'uuid': uuid, 
            'platform': platform,
            'status': gh_run.status,
            'download_center_url': _settings.RDBK_DOWNLOAD_CENTER_URL,
        })
        
    else:
        return render(request, 'waiting.html', {
            'filename': filename, 
            'uuid': uuid, 
            'status': gh_run.status, 
            'platform': platform, 
            'log_url': github_log_url,
            'download_center_url': _settings.RDBK_DOWNLOAD_CENTER_URL,
        })

@dashboard_token_required
def download(request):
    filename = _safe_artifact_name(request.GET.get('filename'))
    file_path = _artifact_path(request.GET.get('uuid'), filename)
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return FileResponse(
        file_path.open('rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )

def get_png(request):
    filename = request.GET['filename']
    uuid = request.GET['uuid']
    #filename = filename+".exe"
    file_path = os.path.join('png',uuid,filename)
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response

def create_github_run(myuuid):
    new_github_run = GithubRun(
        uuid=myuuid,
        status="Starting generator...please wait"
    )
    new_github_run.save()

@csrf_exempt
@upload_token_required
def update_github_run(request):
    data = json.loads(request.body)
    myuuid = data.get('uuid')
    mystatus = data.get('status')
    GithubRun.objects.filter(Q(uuid=myuuid)).update(status=mystatus)
    return HttpResponse('')

def resize_and_encode_icon(imagefile):
    maxWidth = 200
    try:
        with io.BytesIO() as image_buffer:
            for chunk in imagefile.chunks():
                image_buffer.write(chunk)
            image_buffer.seek(0)

            img = Image.open(image_buffer)
            imgcopy = img.copy()
    except (IOError, OSError):
        raise ValueError("Uploaded file is not a valid image format.")

    # Check if resizing is necessary
    if img.size[0] <= maxWidth:
        with io.BytesIO() as image_buffer:
            imgcopy.save(image_buffer, format=imagefile.content_type.split('/')[1])
            image_buffer.seek(0)
            return_image = ContentFile(image_buffer.read(), name=imagefile.name)
        return base64.b64encode(return_image.read())

    # Calculate resized height based on aspect ratio
    wpercent = (maxWidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))

    # Resize the image while maintaining aspect ratio using LANCZOS resampling
    imgcopy = imgcopy.resize((maxWidth, hsize), Image.Resampling.LANCZOS)

    with io.BytesIO() as resized_image_buffer:
        imgcopy.save(resized_image_buffer, format=imagefile.content_type.split('/')[1])
        resized_image_buffer.seek(0)

        resized_imagefile = ContentFile(resized_image_buffer.read(), name=imagefile.name)

    # Return the Base64 encoded representation of the resized image
    resized64 = base64.b64encode(resized_imagefile.read())
    #print(resized64)
    return resized64
 
#the following is used when accessed from an external source, like the rustdesk api server
@csrf_exempt
def startgh(request):
    #print(request)
    data_ = json.loads(request.body)
    ####from here run the github action, we need user, repo, access token.
    url = 'https://api.github.com/repos/'+_settings.GHUSER+'/'+_settings.REPONAME+'/actions/workflows/generator-'+data_.get('platform')+'.yml/dispatches'  
    data = {
        "ref": _settings.GHBRANCH,
        "inputs":{
            "server":data_.get('server'),
            "key":data_.get('key'),
            "apiServer":data_.get('apiServer'),
            "custom":data_.get('custom'),
            "uuid":data_.get('uuid'),
            "iconlink":data_.get('iconlink'),
            "logolink":data_.get('logolink'),
            "appname":data_.get('appname'),
            "extras":data_.get('extras'),
            "filename":data_.get('filename')
        }
    } 
    headers = {
        'Accept':  'application/vnd.github+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+_settings.GHBEARER,
        'X-GitHub-Api-Version': '2026-03-10'
    }
    response = requests.post(url, json=data, headers=headers)
    print(response)
    return HttpResponse(status=204)

def save_png(file, uuid, domain, name):
    file_save_path = "png/%s/%s" % (uuid, name)
    Path("png/%s" % uuid).mkdir(parents=True, exist_ok=True)

    if isinstance(file, str):  # Check if it's a base64 string
        try:
            header, encoded = file.split(';base64,')
            decoded_img = base64.b64decode(encoded)
            file = ContentFile(decoded_img, name=name) # Create a file-like object
        except ValueError:
            print("Invalid base64 data")
            return None  # Or handle the error as you see fit
        except Exception as e:  # Catch general exceptions during decoding
            print(f"Error decoding base64: {e}")
            return None
        
    with open(file_save_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    # imageJson = {}
    # imageJson['url'] = domain
    # imageJson['uuid'] = uuid
    # imageJson['file'] = name
    #return "%s/%s" % (domain, file_save_path)
    return domain, uuid, name

@csrf_exempt
@upload_token_required
def save_custom_client(request):
    file = request.FILES['file']
    file_save_path = _artifact_path(
        request.POST.get('uuid'),
        file.name,
        require_exists=False,
    )
    file_save_path.parent.mkdir(parents=True, exist_ok=True)
    with file_save_path.open("wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)

    return HttpResponse("File saved successfully!")

@csrf_exempt
def cleanup_secrets(request):
    # Pass the UUID as a query param or in JSON body
    data = json.loads(request.body)
    my_uuid = data.get('uuid')
    
    if not my_uuid:
        return HttpResponse("Missing UUID", status=400)

    # 1. Find the files in your temp directory matching the UUID
    temp_dir = os.path.join('temp_zips')
    
    # We look for any file starting with 'secrets_' and containing the uuid
    for filename in os.listdir(temp_dir):
        if my_uuid in filename and filename.endswith('.zip'):
            file_path = os.path.join(temp_dir, filename)
            try:
                os.remove(file_path)
                print(f"Successfully deleted {file_path}")
            except OSError as e:
                print(f"Error deleting file: {e}")

    return HttpResponse("Cleanup successful", status=200)

def get_zip(request):
    filename = request.GET['filename']
    base_dir = os.path.abspath('temp_zips')
    file_path = os.path.abspath(os.path.join(base_dir, filename))
    if not file_path.startswith(base_dir + os.sep):
        return HttpResponseForbidden("Invalid filename")
    with open(file_path, 'rb') as file:
        response = HttpResponse(file, headers={
            'Content-Type': 'application/vnd.microsoft.portable-executable',
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    return response
