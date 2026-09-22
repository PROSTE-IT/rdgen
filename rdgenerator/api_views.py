import json
import mimetypes
import re
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings as _settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import GithubRun
from .views import (
    _artifact_path,
    _available_builds,
    _get_run_status,
    _trash_artifact,
    _trash_build,
    dashboard_token_required,
    generate_custom_client,
)


# Field validation constraints (mirrored from GenerateForm)
PLATFORM_CHOICES = ['windows', 'windows-x86', 'linux', 'android', 'macos']
VERSION_CHOICES = ['master', '1.4.9', '1.4.8', '1.4.7', '1.4.6', '1.4.5', '1.4.4', '1.4.3', '1.4.2', '1.4.1', '1.4.0']
DIRECTION_CHOICES = ['incoming', 'outgoing', 'both']
INSTALLATION_CHOICES = ['installationY', 'installationN']
SETTINGS_CHOICES = ['settingsY', 'settingsN']
THEME_CHOICES = ['light', 'dark', 'system']
THEME_DORO_CHOICES = ['default', 'override']
PASS_APPROVE_MODE_CHOICES = ['password', 'click', 'password-click']
PERMISSIONS_DORO_CHOICES = ['default', 'override']
PERMISSIONS_TYPE_CHOICES = ['custom', 'full', 'view']
BUILD_PROFILE_CHOICES = ['standard', 'quick_support']

# Boolean fields
BOOL_FIELDS = [
    'delayFix', 'xOffline', 'hidecm', 'removeNewVersionNotif', 'supportAddressBook',
    'denyLan', 'enableDirectIP', 'autoClose',
    'enableKeyboard', 'enableClipboard', 'enableFileTransfer', 'enableAudio',
    'enableTCP', 'enableRemoteRestart', 'enableRecording', 'enableBlockingInput',
    'enableRemoteModi', 'removeWallpaper', 'enablePrinter', 'enableCamera', 'enableTerminal',
]

# Optional string fields (no validation needed, just accept as-is)
OPTIONAL_STR_FIELDS = [
    'sh_secret_field', 'serverIP', 'serverPort', 'key', 'apiServer', 'urlLink', 'downloadLink',
    'appname', 'compname', 'androidappid', 'permanentPassword',
    'defaultManual', 'overrideManual', 'supportAddressBookUrl',
    'iconbase64', 'logobase64', 'privacybase64',
]


def validate_generate_params(data):
    """
    Validate JSON API parameters against the same constraints as GenerateForm.

    Returns:
        tuple: (cleaned_data dict, errors dict)
        If errors is non-empty, validation failed.
    """
    errors = {}
    cleaned = {}

    # Required string field
    exename = data.get('exename', '')
    if not exename:
        errors['exename'] = 'This field is required.'
    else:
        cleaned['exename'] = exename

    # Choice fields
    choice_validations = {
        'platform': (PLATFORM_CHOICES, 'windows'),
        'version': (VERSION_CHOICES, '1.4.9'),
        'direction': (DIRECTION_CHOICES, 'both'),
        'installation': (INSTALLATION_CHOICES, 'installationY'),
        'settings': (SETTINGS_CHOICES, 'settingsY'),
        'theme': (THEME_CHOICES, 'system'),
        'themeDorO': (THEME_DORO_CHOICES, 'default'),
        'passApproveMode': (PASS_APPROVE_MODE_CHOICES, 'password-click'),
        'permissionsDorO': (PERMISSIONS_DORO_CHOICES, 'default'),
        'permissionsType': (PERMISSIONS_TYPE_CHOICES, 'custom'),
        'buildProfile': (BUILD_PROFILE_CHOICES, 'standard'),
    }
    for field, (choices, default) in choice_validations.items():
        value = data.get(field, default)
        if value not in choices:
            errors[field] = f'Invalid choice. Must be one of: {choices}'
        else:
            cleaned[field] = value

    # Boolean fields
    for field in BOOL_FIELDS:
        value = data.get(field, False)
        if not isinstance(value, bool):
            errors[field] = 'Must be a boolean value.'
        else:
            cleaned[field] = value

    # Optional string fields
    for field in OPTIONAL_STR_FIELDS:
        cleaned[field] = data.get(field, '')

    # Free-text names flow into single/double-quoted bash sed scripts
    # (same rule as GenerateForm.clean_appname/clean_compname).
    for field in ('appname', 'compname'):
        value = cleaned.get(field, '')
        if isinstance(value, str) and re.search(r'[&\\|\'"$`\r\n]', value):
            errors[field] = (
                'Contains characters unsupported in build scripts '
                '(& \\ | \' " $ `, newlines).'
            )

    if cleaned.get('buildProfile') == 'quick_support':
        if cleaned.get('platform') != 'windows':
            errors['platform'] = 'Quick Support requires Windows 64Bit.'
        if cleaned.get('version') != '1.4.9':
            errors['version'] = 'Quick Support requires RustDesk 1.4.9.'
        cleaned.update({
            'direction': 'incoming',
            'installation': 'installationY',
            'settings': 'settingsN',
            'supportAddressBook': False,
            'removeNewVersionNotif': True,
            'permanentPassword': '',
            'hidecm': False,
        })

    if cleaned.get('supportAddressBook'):
        if cleaned.get('platform') != 'windows':
            errors['platform'] = 'Shared address book requires Windows 64Bit.'
        if cleaned.get('version') != '1.4.9':
            errors['version'] = 'Shared address book requires RustDesk 1.4.9.'
        if not cleaned.get('supportAddressBookUrl'):
            errors['supportAddressBookUrl'] = 'This field is required when shared address book is enabled.'
        if cleaned.get('direction') == 'incoming':
            if not str(cleaned.get('permanentPassword') or '').strip():
                errors['permanentPassword'] = (
                    'Windows Helpdesk requires a permanent password for unattended access.'
                )
            if cleaned.get('passApproveMode') == 'click':
                errors['passApproveMode'] = (
                    'Windows Helpdesk must allow password authentication.'
                )

    # File fields are not used in API mode (base64 fields are used instead)
    cleaned['iconfile'] = None
    cleaned['logofile'] = None
    cleaned['privacyfile'] = None

    return cleaned, errors


@csrf_exempt
def api_generate(request):
    """
    POST /api/generate

    Accepts a JSON body with client configuration parameters and triggers
    the custom client generation process via GitHub Actions.

    Returns JSON with success status, uuid, filename, platform, and log_url.
    """
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"success": False, "error": f"Invalid JSON: {str(e)}"}, status=400)

    cleaned, errors = validate_generate_params(data)
    if errors:
        return JsonResponse({
            "success": False,
            "error": "Validation errors",
            "details": errors
        }, status=400)

    # Build full_url the same way as generator_view
    full_url = f"{_settings.PROTOCOL}://{request.get_host()}" if _settings.GENURL else f"{_settings.PROTOCOL}://{request.get_host()}"

    result = generate_custom_client(cleaned, full_url)

    if result['success']:
        # Add convenience URLs for the API consumer
        result['status_url'] = f"/api/status?uuid={result['uuid']}&platform={result['platform']}&filename={result['filename']}"
        return JsonResponse(result)
    else:
        return JsonResponse({"success": False, "error": result['error']}, status=result.get('status_code', 500))


def api_status(request):
    """
    GET /api/status

    Checks the generation status for a given UUID.
    Returns JSON with status, uuid, and optional log_url/filename/platform.
    """
    if request.method != 'GET':
        return JsonResponse({"success": False, "error": "Method not allowed. Use GET."}, status=405)

    uuid_val = request.GET.get('uuid')
    if not uuid_val:
        return JsonResponse({"error": "Missing required parameter: uuid"}, status=400)

    filename = request.GET.get('filename', '')
    platform = request.GET.get('platform', '')

    result = _get_run_status(uuid_val)

    if not result['found']:
        return JsonResponse({"error": "Run not found"}, status=404)

    response_data = {
        "status": result['status'],
        "uuid": uuid_val,
        "log_url": result['github_log_url'],
        "progress_percent": result.get('progress_percent'),
        "current_stage": result.get('current_stage'),
        "completed_steps": result.get('completed_steps'),
        "total_steps": result.get('total_steps'),
    }
    if filename:
        response_data['filename'] = filename
    if platform:
        response_data['platform'] = platform

    return JsonResponse(response_data)


@dashboard_token_required
def api_builds(request):
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed."}, status=405)

    file_builds = {build['uuid']: build for build in _available_builds()}
    builds = []

    active_runs = GithubRun.objects.filter(deleted_at__isnull=True)
    for run in active_runs.order_by('-created_at')[:100]:
        result = _get_run_status(run.uuid)
        status_value = result.get('status', run.status)
        file_build = file_builds.pop(run.uuid, None)
        artifacts = file_build['artifacts'] if file_build else []
        if status_value == 'success' and not artifacts:
            status_value = 'artifact_missing'
        completed_at = file_build['created_at'].isoformat() if file_build else None
        builds.append({
            'uuid': run.uuid,
            'product': 'RustDesk',
            'filename': run.filename,
            'platform': run.platform,
            'status': status_value,
            'created_at': run.created_at.isoformat(),
            'completed_at': completed_at,
            'github_run_id': run.github_run_id,
            'base_version': run.base_version,
            'pit_revision': run.pit_revision,
            'pit_version': run.pit_version,
            'connection_direction': run.connection_direction,
            'update_channel': run.update_channel,
            'build_profile': run.build_profile,
            'github_log_url': result.get('github_log_url'),
            'artifacts': artifacts,
            'progress_percent': result.get('progress_percent'),
            'current_stage': result.get('current_stage'),
            'completed_steps': result.get('completed_steps'),
            'total_steps': result.get('total_steps'),
        })

    for build_uuid, file_build in file_builds.items():
        builds.append({
            'uuid': build_uuid,
            'product': 'RustDesk',
            'filename': '',
            'platform': '',
            'status': 'success',
            'created_at': file_build['created_at'].isoformat(),
            'completed_at': file_build['created_at'].isoformat(),
            'github_run_id': None,
            'base_version': '',
            'pit_revision': None,
            'pit_version': '',
            'connection_direction': '',
            'update_channel': '',
            'build_profile': 'standard',
            'github_log_url': None,
            'artifacts': file_build['artifacts'],
        })

    builds.sort(
        key=lambda build: build.get('created_at') or '',
        reverse=True,
    )
    return JsonResponse({'builds': builds[:100]})


@csrf_exempt
@dashboard_token_required
def api_build(request, build_uuid):
    if request.method != 'DELETE':
        return JsonResponse({"error": "Method not allowed."}, status=405)

    build_uuid = str(build_uuid)
    runs = GithubRun.objects.filter(uuid=build_uuid, deleted_at__isnull=True)
    run = runs.order_by('-created_at').first()
    terminal_statuses = {
        'success', 'failure', 'cancelled', 'timed_out', 'skipped',
        'action_required',
    }
    if run is not None and run.status not in terminal_statuses:
        return JsonResponse(
            {"error": "An active build cannot be deleted."},
            status=409,
        )

    destination = None
    try:
        destination = _trash_build(build_uuid)
    except Http404:
        if run is None:
            raise

    if run is None and destination is None:
        raise Http404("Build not found")

    runs.update(deleted_at=timezone.now())
    return JsonResponse({
        'deleted': True,
        'uuid': build_uuid,
        'recoverable': destination is not None,
        'trash_name': destination.name if destination is not None else '',
    })


@csrf_exempt
@dashboard_token_required
def api_build_artifact(request, build_uuid, filename):
    if request.method == 'DELETE':
        destination = _trash_artifact(build_uuid, filename)
        return JsonResponse({
            'deleted': True,
            'uuid': str(build_uuid),
            'filename': filename,
            'recoverable': True,
            'trash_name': destination.name,
        })

    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed."}, status=405)

    file_path = _artifact_path(build_uuid, filename)
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return FileResponse(
        file_path.open('rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )
