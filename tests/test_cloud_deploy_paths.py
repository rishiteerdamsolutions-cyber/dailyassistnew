"""Cloud deploy must not write to ~/.aha (Vercel sandbox is read-only)."""

import os
from unittest.mock import patch

from aha.firebase_session import save_firebase_session
from aha.license import save_license, sync_license_for_uid, validate_license


def test_save_firebase_session_skips_on_vercel():
    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
        save_firebase_session(id_token="tok", uid="u1", email="a@b.c")
    # no exception — would fail on read-only /home/sbx_user* if it wrote


def test_save_license_skips_on_vercel():
    with patch.dict(os.environ, {"VERCEL_ENV": "production"}, clear=False):
        save_license({"valid": True, "license_key": "AHA-TEST"})


def test_validate_license_no_disk_write_on_vercel():
    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
        with patch("aha.license._validate_license_cloud", return_value=None):
            with patch("aha.subscription.allow_dev_license_keys", return_value=False):
                result = validate_license("AHA-NOPE-NOPE-NOPE")
    assert result["valid"] is False


def test_sync_license_for_uid_no_disk_write_on_vercel():
    row = {
        "license_key": "AHA-TEST-KEY-1234",
        "plan": "core",
        "expires_at": "2099-12-31T00:00:00+00:00",
    }
    with patch.dict(os.environ, {"VERCEL": "1"}, clear=False):
        with patch("aha.supabase_client.get_active_license", return_value=row):
            with patch("aha.license._validate_license_cloud", return_value={"valid": True, "plan": "core", "expires": row["expires_at"], "reason": None}):
                with patch("aha.license.save_license_from_cloud") as mock_save:
                    out = sync_license_for_uid("uid-1")
    assert out.get("valid") is True
    mock_save.assert_not_called()
