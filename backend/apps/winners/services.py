import os
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from django.core.exceptions import ValidationError

from apps.winners.models import WinnerProof


ALLOWED_PROOF_TYPES = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}
MAX_PROOF_SIZE = 10 * 1024 * 1024


def _matches_image_signature(content_type, header):
    if content_type == 'image/jpeg':
        return header.startswith(b'\xff\xd8\xff')
    if content_type == 'image/png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if content_type == 'image/webp':
        return len(header) >= 12 and header[:4] == b'RIFF' and header[8:12] == b'WEBP'
    return False


class StorageUnavailable(Exception):
    pass


def store_winner_proof(upload, winner_id):
    content_type = getattr(upload, 'content_type', '')
    extension = ALLOWED_PROOF_TYPES.get(content_type)
    if extension is None:
        raise ValidationError({'proof': 'Upload a JPEG, PNG, or WebP image.'})
    if upload.size > MAX_PROOF_SIZE:
        raise ValidationError({'proof': 'Proof images must be 10 MB or smaller.'})
    header = upload.read(12)
    upload.seek(0)
    if not _matches_image_signature(content_type, header):
        raise ValidationError({'proof': 'The uploaded file does not match its declared image type.'})

    storage_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    bucket = os.getenv('SUPABASE_WINNER_PROOF_BUCKET', 'winner-proofs').strip()
    if not storage_url or not service_key:
        raise StorageUnavailable('Supabase Storage is not configured.')

    object_path = f'{winner_id}/{uuid4().hex}{extension}'
    endpoint = f'{storage_url}/storage/v1/object/{quote(bucket, safe="")}/{quote(object_path, safe="/")}'
    request = Request(
        endpoint,
        data=upload.read(),
        headers={
            'Authorization': f'Bearer {service_key}',
            'apikey': service_key,
            'Content-Type': content_type,
            'x-upsert': 'false',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=20):
            pass
    except (HTTPError, URLError, TimeoutError) as error:
        raise StorageUnavailable('The proof image could not be stored.') from error

    return WinnerProof.objects.create(
        winner_id=winner_id,
        bucket=bucket,
        object_path=object_path,
    )


def create_signed_proof_url(proof, expires_in=900):
    storage_url = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not storage_url or not service_key:
        raise StorageUnavailable('Supabase Storage is not configured.')

    endpoint = (
        f'{storage_url}/storage/v1/object/sign/{quote(proof.bucket, safe="")}'
        f'/{quote(proof.object_path, safe="/")}'
    )
    request = Request(
        endpoint,
        data=json.dumps({'expiresIn': expires_in}).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {service_key}',
            'apikey': service_key,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise StorageUnavailable('The proof image could not be accessed.') from error

    signed_path = result.get('signedURL')
    if not signed_path:
        raise StorageUnavailable('The storage service did not return a signed image URL.')
    if signed_path.startswith('https://'):
        return signed_path
    return f'{storage_url}/storage/v1{signed_path if signed_path.startswith("/") else f"/{signed_path}"}'
