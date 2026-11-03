import os


def vercel_analytics(_request):
    return {"vercel_analytics_enabled": os.environ.get("VERCEL") == "1"}
