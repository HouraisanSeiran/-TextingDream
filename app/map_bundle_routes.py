"""Author-only map bundle routes; installed inside existing token middleware."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.map_bundle import BundleIdentityError, BundleMissing, BundleRegistry

Month = Annotated[int, Field(strict=True, ge=1, le=12)]
Index = Annotated[int, Field(strict=True, ge=0)]


class PointBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x_m: float = Field(strict=True, allow_inf_nan=False)
    z_m: float = Field(strict=True, allow_inf_nan=False)
    month: Month = 1


class QueryBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fields: list[Annotated[str, Field(max_length=120)]] = Field(min_length=1, max_length=64)
    window: list[Index] = Field(min_length=4, max_length=4)
    months: list[Month] = Field(default_factory=lambda: [1], min_length=1, max_length=12)


def install(app, root, registry=None):
    """No changes to authentication, player map/fog or legacy map APIs."""
    bundles = registry if registry is not None else BundleRegistry(root)
    app.state.map_bundles = bundles
    router = APIRouter(prefix='/api/inner/map-bundles')

    def call(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (BundleMissing, FileNotFoundError) as error:
            raise HTTPException(404, str(error)) from error
        except BundleIdentityError as error:
            raise HTTPException(409, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    def selected(bundle_id):
        return call(bundles.get, bundle_id)

    @router.get('')
    def list_bundles():
        return call(bundles.list)

    @router.get('/{bundle_id}')
    def detail(bundle_id: str):
        return call(selected(bundle_id).detail)

    @router.get('/{bundle_id}/preview/{key}')
    def preview(bundle_id: str, key: str, month: int = Query(1, ge=1, le=12)):
        path = call(selected(bundle_id).preview, key, month)
        return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store'})

    @router.post('/{bundle_id}/point')
    def point(bundle_id: str, body: PointBody):
        return call(selected(bundle_id).point, body.x_m, body.z_m, body.month)

    @router.post('/{bundle_id}/query')
    def query(bundle_id: str, body: QueryBody):
        return call(selected(bundle_id).query, body.fields, body.window, body.months)

    @router.get('/{bundle_id}/vectors/{kind}')
    def vectors(bundle_id: str, kind: str, month: int = Query(1, ge=1, le=12),
                offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return call(selected(bundle_id).vectors, kind, month, offset, limit)

    app.include_router(router)
