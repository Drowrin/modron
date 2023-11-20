from devenv import reset_schema, with_model
from hikari.api import RESTClient

from modron.model import Model


@with_model
async def reset(app: RESTClient, model: Model):
    await reset_schema(model)


if __name__ == "__main__":
    import asyncio

    asyncio.run(reset())
