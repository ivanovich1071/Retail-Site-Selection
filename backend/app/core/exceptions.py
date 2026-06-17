from fastapi import HTTPException, status


class GeocodeError(Exception):
    """Address could not be geocoded."""


class IsochroneError(Exception):
    """Isochrone calculation failed."""


class ExternalAPIError(Exception):
    """External API returned an unexpected response."""


class LocationNotFoundError(Exception):
    """Location does not exist in the database."""


def raise_not_found(resource: str = "Resource") -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


def raise_bad_request(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
