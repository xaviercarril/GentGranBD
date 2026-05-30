import base64
import hashlib
import hmac
import secrets
from datetime import datetime

from sqlalchemy import func, select

from database import SessionLocal
from models import Usuario, UsuarioRol


PBKDF2_ITERATIONS = 260_000


def _normalizar_username(username: str) -> str:
    value = (username or "").strip()
    if not value:
        raise ValueError("El nom d'usuari és obligatori.")
    return value


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("La contrasenya és obligatòria.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text.encode("ascii"))
        expected = base64.b64decode(digest_text.encode("ascii"))
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def usuario_to_dict(usuario: Usuario) -> dict:
    return {
        "id": usuario.id,
        "username": usuario.username,
        "rol": usuario.rol.value if isinstance(usuario.rol, UsuarioRol) else usuario.rol,
        "activo": bool(usuario.activo),
        "created_at": usuario.created_at,
        "updated_at": usuario.updated_at,
        "last_login": usuario.last_login,
    }


def bootstrap_admin_si_no_hay_usuarios() -> bool:
    with SessionLocal() as db:
        total = db.scalar(select(func.count(Usuario.id))) or 0
        if total:
            return False
        db.add(
            Usuario(
                username="admin",
                password_hash=hash_password("admin"),
                rol=UsuarioRol.ADMIN,
                activo=True,
            )
        )
        db.commit()
        return True


def autenticar_usuario(username: str, password: str) -> dict:
    username = _normalizar_username(username)
    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.username == username))
        if not usuario or not usuario.activo:
            raise ValueError("Usuari o contrasenya incorrectes.")
        if not verify_password(password, usuario.password_hash):
            raise ValueError("Usuari o contrasenya incorrectes.")
        usuario.last_login = datetime.utcnow()
        db.commit()
        db.refresh(usuario)
        return usuario_to_dict(usuario)


def listar_usuarios() -> list[dict]:
    with SessionLocal() as db:
        usuarios = db.scalars(select(Usuario).order_by(Usuario.username.asc())).all()
        return [usuario_to_dict(usuario) for usuario in usuarios]


def _normalizar_rol(rol: str | UsuarioRol) -> UsuarioRol:
    if isinstance(rol, UsuarioRol):
        return rol
    try:
        return UsuarioRol((rol or "").strip().upper())
    except ValueError:
        raise ValueError("Rol d'usuari no vàlid.")


def _contar_admins_activos(db) -> int:
    return db.scalar(
        select(func.count(Usuario.id)).where(
            Usuario.rol == UsuarioRol.ADMIN,
            Usuario.activo.is_(True),
        )
    ) or 0


def crear_usuario(username: str, password: str, rol: str = "USER", activo: bool = True) -> dict:
    username = _normalizar_username(username)
    user_rol = _normalizar_rol(rol)
    with SessionLocal() as db:
        existente = db.scalar(select(Usuario).where(Usuario.username == username))
        if existente:
            raise ValueError("Ja existeix un usuari amb aquest nom.")
        usuario = Usuario(
            username=username,
            password_hash=hash_password(password),
            rol=user_rol,
            activo=bool(activo),
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario_to_dict(usuario)


def modificar_usuario(
    usuario_id: int,
    *,
    username: str | None = None,
    rol: str | UsuarioRol | None = None,
    activo: bool | None = None,
    password: str | None = None,
) -> dict:
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ValueError("Usuari no trobat.")
        era_admin_activo = usuario.rol == UsuarioRol.ADMIN and usuario.activo

        if username is not None:
            nuevo_username = _normalizar_username(username)
            existente = db.scalar(
                select(Usuario).where(
                    Usuario.username == nuevo_username,
                    Usuario.id != usuario_id,
                )
            )
            if existente:
                raise ValueError("Ja existeix un usuari amb aquest nom.")
            usuario.username = nuevo_username

        if rol is not None:
            usuario.rol = _normalizar_rol(rol)
        if activo is not None:
            usuario.activo = bool(activo)
        if password is not None:
            usuario.password_hash = hash_password(password)

        deja_de_ser_admin_activo = era_admin_activo and (
            usuario.rol != UsuarioRol.ADMIN or not usuario.activo
        )
        if deja_de_ser_admin_activo:
            if _contar_admins_activos(db) <= 1:
                raise ValueError("No es pot deixar el sistema sense cap administrador actiu.")

        db.commit()
        db.refresh(usuario)
        return usuario_to_dict(usuario)


def eliminar_usuario(usuario_id: int) -> None:
    with SessionLocal() as db:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            raise ValueError("Usuari no trobat.")
        if usuario.rol == UsuarioRol.ADMIN and usuario.activo and _contar_admins_activos(db) <= 1:
            raise ValueError("No es pot eliminar l'últim administrador actiu.")
        db.delete(usuario)
        db.commit()
