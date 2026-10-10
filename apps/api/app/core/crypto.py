"""记忆内容加密。

对话内容是用户最私密的数据，记忆又是从对话里提炼出来的，敏感度更高。
开启 ``MEMORY_ENCRYPT=true`` 且配置了 ``MEMORY_ENCRYPTION_KEY`` 后，
记忆正文在落库前用 Fernet（对称加密）加密，检索时再解密。

未配置 Key 时**不静默降级为明文存储**，而是保持原样存明文并在日志里明确提示 ——
让使用者知道自己当前的数据是明文还是密文，比悄悄降级要诚实。
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "enc::"  # 密文标记，便于识别历史数据里哪些是加密的

_fernet: Fernet | None = None
_ready = False


def _build() -> Fernet | None:
    global _fernet, _ready
    if _ready:
        return _fernet
    _ready = True

    if not settings.memory_encrypt:
        return None
    raw = settings.memory_encryption_key.strip()
    if not raw or raw.startswith("change-me"):
        logger.warning(
            "MEMORY_ENCRYPT=true 但 MEMORY_ENCRYPTION_KEY 未正确配置，"
            "记忆将以明文存储。生产环境请务必设置一个足够长的随机串。"
        )
        return None

    # 任意长度的口令都能用：先做一次 SHA256 派生，凑成 Fernet 要的 32 字节 key
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    _fernet = Fernet(base64.urlsafe_b64encode(digest))
    logger.info("记忆加密已启用")
    return _fernet


def is_enabled() -> bool:
    return _build() is not None


def encrypt(plain: str) -> str:
    """加密。未启用时原样返回。"""
    fernet = _build()
    if fernet is None:
        return plain
    return _PREFIX + fernet.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """解密。对历史明文数据和无标记数据直接返回原文。"""
    if not token.startswith(_PREFIX):
        return token
    fernet = _build()
    if fernet is None:
        # 服务端重启且配置丢了：宁可报错也不要返回乱码
        logger.error("记忆是密文，但当前未启用加密，无法解密")
        return token
    try:
        return fernet.decrypt(token[len(_PREFIX) :].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("记忆解密失败：密钥不对或数据损坏")
        return token


def reset() -> None:
    """测试用。"""
    global _fernet, _ready
    _fernet = None
    _ready = False