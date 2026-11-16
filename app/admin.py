from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from app.config import ADMIN_BASE_URL, ADMIN_SECRET, ADMIN_TITLE
from app.database import engine
from app.models import Token


class NoAuthBackend(AuthenticationBackend):
    async def login(self, request) -> bool:
        return True

    async def logout(self, request) -> bool:
        return True

    async def authenticate(self, request) -> bool:
        return True


class TokenAdmin(ModelView, model=Token):
    name = "Token"
    name_plural = "Tokens"
    icon = "fa-solid fa-key"

    column_list = [
        Token.platform,
        Token.userId,
        Token.userName,
        Token.appId,
    ]
    column_searchable_list = [Token.platform, Token.userId, Token.userName, Token.appId]
    column_sortable_list = [Token.platform, Token.userId, Token.userName, Token.appId]

    can_create = True
    can_edit = True
    can_delete = True


def setup_admin(app):
    admin = Admin(
        app,
        engine,
        title=ADMIN_TITLE,
        base_url=ADMIN_BASE_URL,
        authentication_backend=NoAuthBackend(secret_key=ADMIN_SECRET),
    )
    admin.add_view(TokenAdmin)
    return admin