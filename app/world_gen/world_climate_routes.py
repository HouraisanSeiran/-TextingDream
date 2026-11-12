"""Token-protected author queries over explicitly selected saved climate products."""
from __future__ import annotations

from pathlib import Path, PureWindowsPath
from typing import Annotated

import numpy as np
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, model_validator

from .world_climate_adapter import SavedClimateMap

# Same scalar-cell limit as the existing map_source crop contract. Count all
# requested monthly/field values so a JSON response stays within that budget.
MAX_QUERY_VALUES = 16_777_216
Identity = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
FieldName = Annotated[str, StringConstraints(min_length=1)]


class ClimateSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source_map: str = Field(min_length=1)
    climate_product: str = Field(min_length=1)
    expected_source_identity: Identity
    expected_climate_identity: Identity
    fields: list[FieldName] = Field(min_length=1)
    months: list[StrictInt] | None = Field(default=None, min_length=1, max_length=12)

    @model_validator(mode='after')
    def valid_months(self):
        if self.months is not None and any(month not in range(1, 13) for month in self.months):
            raise ValueError('Months must be 1..12')
        return self


class ClimateWindowRequest(ClimateSelection):
    window: list[StrictInt] = Field(min_length=4, max_length=4)

    @model_validator(mode='after')
    def bounded_window(self):
        z0, x0, z1, x1 = self.window
        if not 0 <= z0 < z1 or not 0 <= x0 < x1:
            raise ValueError('Window must be nonempty, nonnegative and half-open [z0,x0,z1,x1]')
        if (z1-z0) * (x1-x0) > MAX_QUERY_VALUES:
            raise ValueError('Climate window exceeds map crop size limit')
        return self


class ClimatePointRequest(ClimateSelection):
    x_m: float = Field(allow_inf_nan=False)
    z_m: float = Field(allow_inf_nan=False)


def _artifact_product(root, relative):
    normalized = relative.replace('\\', '/')
    path = Path(normalized)
    if (path.is_absolute() or PureWindowsPath(relative).drive or ':' in relative
            or '..' in path.parts or '\0' in relative):
        raise ValueError('Product paths must be relative to artifacts and cannot escape it')
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Product path escapes artifacts')
    if not (target / 'manifest.json').is_file():
        raise FileNotFoundError('Selected saved product manifest is missing: ' + normalized)
    return target


def _json_value(value):
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _query(request, body, *, point):
    try:
        root = Path(request.app.state.worldgen.artifacts)
        view = SavedClimateMap(_artifact_product(root, body.source_map),
                               _artifact_product(root, body.climate_product),
                               expected_source_identity=body.expected_source_identity,
                               expected_climate_identity=body.expected_climate_identity)
        descriptors = view.fields
        if any(name not in descriptors for name in body.fields):
            raise ValueError('Requested saved climate/environment field is unavailable')
        cells = 1 if point else (body.window[2]-body.window[0]) * (body.window[3]-body.window[1])
        months = 12 if body.months is None else len(body.months)
        values = cells * sum(months if len(descriptors[name].get('shape', [])) == 3 else 1
                             for name in body.fields)
        if values > MAX_QUERY_VALUES:
            raise ValueError('Selected climate values exceed map crop size limit')
        if point:
            result = view.point(body.x_m, body.z_m, body.fields, months=body.months)
        else:
            result = view.query(body.fields, months=body.months, window=body.window)
        return _json_value(result)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def install(app):
    # /api/inner uses the application's existing local-origin/token middleware.
    @app.post('/api/inner/worldgen/climate/query')
    def climate_query(request: Request, body: ClimateWindowRequest):
        return _query(request, body, point=False)

    @app.post('/api/inner/worldgen/climate/point')
    def climate_point(request: Request, body: ClimatePointRequest):
        return _query(request, body, point=True)
