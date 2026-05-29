class BaseController:
    """
    Shared base for all controllers.

    Controllers return a standardised result dict so Views always
    have a consistent shape to work with, regardless of which
    controller produced it:

        {
            "success": bool,
            "data":    any,      # the payload the view needs
            "message": str,      # human-readable status or error
        }

    Use the _ok() and _err() helpers to build these consistently.
    """

    def _ok(self, data=None, message: str = "") -> dict:
        return {"success": True, "data": data, "message": message}

    def _err(self, message: str, data=None) -> dict:
        return {"success": False, "data": data, "message": message}
