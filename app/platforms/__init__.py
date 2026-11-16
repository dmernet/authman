from app.platforms.baidu import BaiduPlatform
from app.platforms.juliang import JuliangPlatform
from app.platforms.qihoo import QihooPlatform
from app.platforms.xiaohongshu import XiaohongshuPlatform

# 单例注册表，加新平台只需在这里 import + 加一行
PLATFORM_REGISTRY = {
    p.key: p
    for p in [
        BaiduPlatform(),
        XiaohongshuPlatform(),
        QihooPlatform(),
        JuliangPlatform(),
    ]
}

__all__ = ["PLATFORM_REGISTRY"]