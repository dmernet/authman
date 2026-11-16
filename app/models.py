from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base, utcnow


class Token(Base):
    __tablename__ = "Tokens"

    id = Column(Integer, primary_key=True)
    platform = Column(String, index=True)
    userId = Column(String, index=True)
    userName = Column(String)
    password = Column(String)
    appId = Column(String, index=True)
    secretKey = Column(String)
    accessToken = Column(String)
    refreshToken = Column(String)
    accessTokenExpireTime = Column(DateTime, nullable=True)
    refreshTokenExpireTime = Column(DateTime, nullable=True)
    createAt = Column(DateTime, default=utcnow)
    updateAt = Column(DateTime, default=utcnow, onupdate=utcnow)


def token_to_dict(r: Token) -> dict:
    def iso(dt):
        return dt.isoformat() if dt else None

    return {
        "id": r.id,
        "platform": r.platform,
        "userId": r.userId,
        "userName": r.userName,
        "password": r.password,
        "appId": r.appId,
        "secretKey": r.secretKey,
        "accessToken": r.accessToken,
        "refreshToken": r.refreshToken,
        "accessTokenExpireTime": iso(r.accessTokenExpireTime),
        "refreshTokenExpireTime": iso(r.refreshTokenExpireTime),
        "createAt": iso(r.createAt),
        "updateAt": iso(r.updateAt),
    }