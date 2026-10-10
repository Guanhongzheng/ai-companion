"""所有 ORM 模型的声明基类。

约定：模型实体一律继承本基类，元数据统一挂在 Base.metadata 上，
建表与迁移只认这一个入口。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 声明式基类。"""