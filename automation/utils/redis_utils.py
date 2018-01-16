from settings import CACHES


def get_con(con_name):
    con = None
    if CACHES.has_key(con_name):
        con = get_cache(con_name).raw_client
    return con
