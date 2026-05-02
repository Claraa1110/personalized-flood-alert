import asyncio
from uuid import uuid4
from sqlalchemy import select, text
from app.database import engine, AsyncSessionLocal, Base
from app.models.property import Property


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        prop = Property(
            id=uuid4(),
            user_id=uuid4(),
            name="測試財產",
            type="house",
            latitude=25.03,
            longitude=121.56,
        )
        session.add(prop)
        await session.commit()
        await session.refresh(prop)
        print("新增成功:", prop.id, prop.name)

        result = await session.execute(select(Property).where(Property.id == prop.id))
        fetched = result.scalar_one()
        print("讀取成功:", fetched.name, fetched.latitude, fetched.longitude)

        await session.delete(fetched)
        await session.commit()
        print("刪除成功")


if __name__ == "__main__":
    asyncio.run(main())
