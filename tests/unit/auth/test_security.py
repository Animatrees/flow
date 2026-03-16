from app.services.security import hash_password, verify_password


def test_hash_password_returns_non_plain_value():
    password = "StrongPass1!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash


def test_hash_password_uses_unique_salt():
    password = "StrongPass1!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_accepts_matching_password():
    password = "StrongPass1!"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash)


def test_verify_password_rejects_invalid_password():
    password_hash = hash_password("StrongPass1!")

    assert not verify_password("WrongPass1!", password_hash)


def test_verify_password_rejects_invalid_hash_format():
    assert not verify_password("StrongPass1!", "invalid-hash")
