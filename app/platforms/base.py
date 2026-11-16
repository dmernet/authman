from abc import ABC, abstractmethod


class BasePlatform(ABC):
    key: str = ""
    display: str = ""
    client_id: str = "REPLACE_ME"
    client_secret: str = "REPLACE_ME"
    redirect_uri: str = ""

    @abstractmethod
    async def get_auth_url(self, state: str) -> str: ...

    @abstractmethod
    async def exchange_code(self, code: str, 
                        user_id: str | int | None = None,
                        user_name: str | int | None = None,
                        password: str | int | None = None,
                        app_id: str | int | None = None,
                        secret_key: str | int | None = None,) -> dict: ...

    @abstractmethod
    async def refresh(self, refresh_token: str,
                        user_id: str | int | None = None,
                        user_name: str | int | None = None,
                        password: str | int | None = None,
                        app_id: str | int | None = None,
                        secret_key: str | int | None = None,) -> dict: ...

    @abstractmethod
    async def check_token(self, access_token: str, 
                            user_id: str | None = None, 
                            user_name: str | None = None,
                            app_id: str | int | None = None,) -> bool: ...
