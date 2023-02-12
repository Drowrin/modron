import hikari


async def get_me(app: hikari.RESTAware) -> hikari.OwnUser:
    """
    Get the bot user from the cache if available, otherwise fetch it.
    """
    if isinstance(app, hikari.CacheAware):
        return app.cache.get_me() or await app.rest.fetch_my_user()
    else:
        return await app.rest.fetch_my_user()
