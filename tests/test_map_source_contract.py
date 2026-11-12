"""The same frozen-source contract runs against every registered product schema."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from app import map_source as ms

WORLD_LAYOUT = ("world-map-product", "terragenesis-local30")  # same on-disk layout; local30 is a relabelled world-map product
# Climate uses TG query_climate + a different on-disk layout; covered in test_map_source_climate.py.
CASES = [(kind, schema) for kind, schemas in ms.SUPPORTED_SCHEMAS.items()
         for schema in schemas if kind != "terragenesis-regional-climate"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(manifest, native=False):
    excluded = {"identity", "source_path"} if native or manifest["schema"] in ("world-map-product-v1", "td-world-960m-v1", "terragenesis-local30-v1") else {"identity"}
    manifest["identity"] = hashlib.sha256(json.dumps({k: v for k, v in manifest.items() if k not in excluded}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class Fixture:
    def __init__(self, root, kind, schema):
        self.kind, self.schema = kind, schema
        self.path = root / ("product.npz" if kind == "tectonic-macro-v2" else "product")
        self.spacing = {"native-terrain-v3": 30, "tectonic-macro-v2": 300, "world-relief-pilot": 60, "world-map-product": 120, "terragenesis-local30": 30}[kind]
        self.bed = (10 + np.arange(20)).reshape(4, 5).astype(np.float32)
        self.ocean = np.zeros((4, 5), bool)
        self.ocean[0, 4] = True
        self.closed = np.zeros((4, 5), bool)
        self.closed[1, 4] = True
        self.manifest = dict(schema=schema, world_seed=17)
        if kind == "tectonic-macro-v2":
            self.bed = self.bed.astype(np.float64)
            self.bed[1, 4] = -2
            self.arrays = {"final/elevation_m": self.bed, "final/ocean_connected": self.ocean}
            self.manifest = dict(schema=schema, config=dict(shape=[4, 5], cell_size_m=self.spacing, origin_x_m=-self.spacing/2, origin_z_m=-self.spacing/2, world_seed=17), coordinates={"grid": "cell centres; periodic source"}, arrays={key: {"sha256": hashlib.sha256(a.tobytes()).hexdigest()} for key, a in self.arrays.items()})
        else:
            self.path.mkdir()
            if kind == "native-terrain-v3":
                unknown = np.zeros((4, 5), bool)
                unknown[3, 4] = True
                self.arrays = dict(bed_m=self.bed, valid_mask=np.ones((4, 5), bool), ocean_mask=self.ocean, unknown_mask=unknown, closed_below_sea_mask=self.closed)
                self.manifest.update(spacing_m=30, sea_m=0, origin_native_xz=[0, 0], shape_zx=[4, 5], files={})
                for name, array in self.arrays.items():
                    filename = self.path / (name + ".npy")
                    np.save(filename, array)
                    self.manifest["files"][name] = digest(filename)
            elif kind == "world-relief-pilot":
                lake = self.bed.copy()
                lake[2, 2] += 4
                self.arrays = dict(elevation_m=self.bed, ocean_mask=self.ocean, inland_depression_mask=self.closed, lake_surface_m=lake, drainage_area_m2=np.full((4, 5), 1e6, np.float32))
                self.manifest.update(shape_zx=[4, 5], spacing_m=self.spacing, first_sample_xz_m=[0, 0], axes="arrays [z,x]; X east; Z south; metres; cell centres; sea=0", boundary="finite; no wrap", files={}, subseeds={"test": 19}, source_identity="a"*64, declared_generated=["test surface"], limitations=["test only"])
                for name, array in self.arrays.items():
                    filename = self.path / (name + ".npy")
                    np.save(filename, array)
                    self.manifest["files"][filename.name] = digest(filename)
                rivers = dict(schema="coordinate-river-segments-v1", lines=[dict(id="r-stable", coordinates_xz_m=[[0, 0], [self.spacing, 0]], downstream_id=None, upstream_ids=[], head_area_km2=1, outlet_area_km2=2)])
                self.write_json("rivers.json", rivers)
                self.manifest["files"]["rivers.json"] = digest(self.path / "rivers.json")
            else:
                status = np.where(self.ocean, 3, np.where(self.closed, 4, 5)).astype(np.uint8)
                status[3, 4] = 2
                self.arrays = dict(elevation_m=self.bed, status=status, drainage_area_m2=np.full((4, 5), 1e6, np.float32))
                self.manifest.update(producer="test", algorithm_version="1", lineage=[], subseed_method="test", subseeds={"test": 19}, ready=True, declared_generated=["test surface"], limitations=["test only"], grid=dict(first_sample_xz_m=[0, 0], spacing_m=self.spacing, shape_zx=[4, 5], semantics="native-sample" if kind == "terragenesis-local30" else "cell-centre", axes="X east, Z south; arrays [z,x]", length_unit="m", sea_level_m=0), layers={}, vectors={})
                (self.path / "layers").mkdir()
                for name, array in self.arrays.items():
                    filename = "layers/" + name + ".npy"
                    np.save(self.path / filename, array)
                    self.manifest["layers"][name] = dict(file=filename, sha256=digest(self.path / filename), dtype=str(array.dtype), unit=ms.STANDARD_LAYERS[name], meaning="test bed" if name == "elevation_m" else "test", nodata=None)
                rivers = dict(schema="rivers-v1", lines=[dict(id="r-stable", points_xz_m=[[0, 0], [self.spacing, 0]], downstream_id=None, upstream_ids=[], drainage_area_m2=2e6, outlet="edge")])
                lakes = dict(schema="lakes-v1", lakes=[dict(id="lake-stable", ring_xz_m=[[0, 0], [120, 0], [120, 120], [0, 0]], surface_m=20)])
                for name, value in (("rivers", rivers), ("lakes", lakes)):
                    self.write_json(name + ".json", value)
                    self.manifest["vectors"][name] = dict(file=name + ".json", sha256=digest(self.path / (name + ".json")), schema=name + "-v1")
        self.save()

    def write_json(self, name, value):
        (self.path / name).write_text(json.dumps(value), encoding="utf-8")

    def save(self, reseal=True):
        if reseal:
            seal(self.manifest, self.kind == "native-terrain-v3")
        if self.kind == "tectonic-macro-v2":
            np.savez(self.path, manifest_json=np.array(json.dumps(self.manifest)), **self.arrays)
        else:
            self.write_json("manifest.json", self.manifest)

    def load(self, **kwargs):
        return ms.load_source(self.kind, self.path, **kwargs)


def test_environment_layers_are_bound_to_same_saved_process_revision(tmp_path):
    fixture=Fixture(tmp_path,'world-map-product','world-map-product-v1')
    name='groundwater_storage_m3'
    value=np.arange(20,dtype=np.float64).reshape(4,5)
    process=fixture.path/'world-processes'
    process.mkdir()
    np.save(process/(name+'.npy'),value)
    metadata=dict(world_seed=17,first_xz_m=[0,0],spacing_m=fixture.spacing)
    saved=dict(identity='process-current',metadata=metadata,
        arrays={name:dict(file=name+'.npy',sha256=digest(process/(name+'.npy')))})
    (process/'manifest.json').write_text(json.dumps(saved),encoding='utf8')
    fixture.manifest['world_processes']=dict(file='world-processes/manifest.json',
        sha256=digest(process/'manifest.json'),metadata=metadata)
    np.save(fixture.path/(name+'.npy'),value)
    fixture.manifest['layers'][name]=dict(file=name+'.npy',sha256=digest(fixture.path/(name+'.npy')),
        dtype='float64',unit='m3',meaning='actual retained finite owner',nodata=None,
        process_identity='process-current')
    fixture.save()
    loaded=fixture.load()
    assert name in loaded.info.layers
    assert loaded.sample([0.],[0.],layers=[name])[name][0]==0.
    fixture.manifest['layers'][name]['process_identity']='another-version'
    fixture.save()
    with pytest.raises(ms.MapSourceError,match='another process revision'):
        fixture.load()


@pytest.fixture(params=CASES, ids=[kind + ":" + schema for kind, schema in CASES])
def product(request, tmp_path):
    return Fixture(tmp_path, *request.param)


def test_source_coordinates_status_and_broadcast(product):
    source = product.load(expected_identity=product.manifest["identity"])
    info = source.info
    assert isinstance(info, ms.SourceInfo)
    assert (info.kind, info.schema, info.world_seed) == (product.kind, product.schema, 17)
    assert info.first_sample_xz_m == (0, 0)
    assert info.shape_zx == (4, 5)
    assert info.extent_m == (0, 0, 4*product.spacing, 3*product.spacing)
    result = source.sample([0, product.spacing, product.spacing/2], [0, 0, product.spacing/2])
    np.testing.assert_allclose(result["elevation_m"], [10, 11, 13])
    assert source.sample(4*product.spacing, 0)["status"] == ms.OCEAN
    assert source.sample(4*product.spacing, product.spacing)["status"] == ms.CLOSED_BELOW_SEA
    assert source.sample(np.zeros((2, 1)), np.arange(3)*product.spacing)["status"].shape == (2, 3)
    assert result["status"].dtype == np.uint8
    assert result["elevation_m"].dtype == np.float64


def test_out_of_bounds(product):
    source = product.load()
    result = source.sample([-0.01, 4*product.spacing+0.01], [0, 0])
    assert np.all(result["status"] == ms.OUT_OF_BOUNDS)
    assert np.all(np.isnan(result["elevation_m"]))
    for value in (np.nan, np.inf):
        with pytest.raises(ms.MapSourceError):
            source.sample(value, 0)


def test_identity_and_expected_seed(product):
    with pytest.raises(ms.MapSourceError, match="identity"):
        product.load(expected_identity="0"*64)
    assert product.load(expected_world_seed=17).info.world_seed == 17
    with pytest.raises(ms.MapSourceError, match="world_seed"):
        product.load(expected_world_seed=18)
    product.manifest["tampered"] = True
    product.save(reseal=False)
    with pytest.raises(ms.MapSourceError, match="identity"):
        product.load()


def test_consumed_hash_tamper(product):
    if product.kind == "tectonic-macro-v2":
        product.arrays["final/elevation_m"][0, 0] = 999
        product.save()
    else:
        name = "bed_m.npy" if product.kind == "native-terrain-v3" else "layers/elevation_m.npy" if product.kind in WORLD_LAYOUT else "elevation_m.npy"
        np.save(product.path / name, product.bed + 1)
    with pytest.raises(ms.MapSourceError, match="hash"):
        product.load()


def test_shape_validation(product):
    if product.kind == "tectonic-macro-v2":
        product.manifest["config"]["shape"] = [3, 5]
    elif product.kind in WORLD_LAYOUT:
        product.manifest["grid"]["shape_zx"] = [3, 5]
    else:
        product.manifest["shape_zx"] = [3, 5]
    product.save()
    with pytest.raises(ms.MapSourceError, match="array"):
        product.load()


def test_dtype_validation(product):
    if product.kind == "tectonic-macro-v2":
        key = "final/elevation_m"
        product.arrays[key] = product.bed.astype(np.float32)
        product.manifest["arrays"][key]["sha256"] = hashlib.sha256(product.arrays[key].tobytes()).hexdigest()
    else:
        name = "bed_m.npy" if product.kind == "native-terrain-v3" else "layers/elevation_m.npy" if product.kind in WORLD_LAYOUT else "elevation_m.npy"
        np.save(product.path / name, product.bed.astype(np.int32))
        if product.kind in WORLD_LAYOUT:
            product.manifest["layers"]["elevation_m"]["sha256"] = digest(product.path / name)
        else:
            product.manifest["files"]["bed_m" if product.kind == "native-terrain-v3" else name] = digest(product.path / name)
    product.save()
    with pytest.raises(ms.MapSourceError, match="array"):
        product.load()


def test_missing_layer_no_fabrication(product):
    source = product.load()
    for method in (lambda: source.sample(0, 0, ("temperature_c",)), lambda: source.crop(0, 0, 1, 1, ("temperature_c",)), lambda: ms.MapCatalog([source]).sample(0, 0, ("temperature_c",))):
        with pytest.raises(ms.MissingLayerError):
            method()


def test_readonly_crop_copy_vectors(product):
    source = product.load()
    sample = source.sample(0, 0)
    with pytest.raises(ValueError):
        sample["elevation_m"][...] = 999
    assert not source._grid._elevation.flags.writeable
    crop = source.crop(-product.spacing, -product.spacing, 2*product.spacing, 2*product.spacing)
    assert crop["source_info"] == source.info
    assert crop["shape_zx"] == (3, 3)
    assert crop["first_sample_xz_m"] == (-product.spacing, -product.spacing)
    assert np.all(crop["status"][0] == ms.OUT_OF_BOUNDS)
    assert np.all(np.isnan(crop["elevation_m"][0]))
    crop["elevation_m"][1, 1] = 999
    assert source.sample(0, 0)["elevation_m"] == 10
    with pytest.raises(ms.MapSourceError):
        source.crop(0, 0, 10*product.spacing, 10*product.spacing, max_cells=5)
    for kind in ("rivers", "lakes"):
        vectors = source.vectors(kind)
        assert len({v["id"] for v in vectors}) == len(vectors)
        if vectors:
            vectors[0]["id"] = "changed"
            assert source.vectors(kind)[0]["id"] != "changed"


def test_catalog_unknown_never_falls_back(product, tmp_path):
    # Every adapter participates as a coarse source; a fine UNKNOWN must win.
    coarse = product.load()
    fine_root = tmp_path / "fine"
    fine_root.mkdir()
    fine = Fixture(fine_root, "world-map-product", "world-map-product-v1")
    fine.manifest["grid"]["spacing_m"] = product.spacing / 2
    fine.arrays["status"][:] = ms.UNKNOWN
    np.save(fine.path / "layers/status.npy", fine.arrays["status"])
    fine.manifest["layers"]["status"]["sha256"] = digest(fine.path / "layers/status.npy")
    fine.save()
    fine_source = fine.load()
    catalog = ms.MapCatalog([coarse, fine_source])
    result = catalog.sample([0, 3*product.spacing, 1e9], [0, 0, 1e9])
    np.testing.assert_array_equal(result["source"], [fine_source.identity, coarse.identity, None])
    assert result["status"][0] == ms.UNKNOWN
    assert np.isnan(result["elevation_m"][0])
    assert result["status"][-1] == ms.UNPREPARED
    assert result["source_info"][0] is fine_source.info
    if "water_surface_m" in coarse.info.layers:
        with pytest.raises(ms.MissingLayerError):
            catalog.sample(0, 0, ("water_surface_m",))


def test_config_and_schema_rejection(product, tmp_path, monkeypatch):
    entry = dict(kind=product.kind, path=product.path.name, identity=product.manifest["identity"], expected_world_seed=17)
    config = tmp_path / "sources.json"
    config.write_text(json.dumps({"sources": [entry]}), encoding="utf-8")
    assert len(ms.load_catalog(config).sources) == 1
    monkeypatch.setenv("DREAM_TERRAIN_SOURCES", str(config))
    assert ms.load_default_catalog().sample(0, 0)["source"].item() == entry["identity"]
    entry["expected_world_seed"] = 18
    config.write_text(json.dumps({"sources": [entry]}), encoding="utf-8")
    with pytest.raises(ms.MapSourceError, match="world_seed"):
        ms.load_catalog(config)
    del entry["identity"]
    config.write_text(json.dumps({"sources": [entry]}), encoding="utf-8")
    with pytest.raises(ms.MapSourceError, match="identity"):
        ms.load_catalog(config)
    with pytest.raises(ms.UnsupportedSourceError, match="bogus"):
        ms.load_source("bogus", product.path)
    product.manifest["schema"] = "future-schema-99"
    product.save()
    with pytest.raises(ms.UnsupportedSourceError, match="future-schema-99"):
        product.load()
    monkeypatch.delenv("DREAM_TERRAIN_SOURCES")
    assert ms.load_default_catalog().sample(0, 0)["status"] == ms.UNPREPARED


def test_relief_water_and_river_conversion(tmp_path):
    fixture = Fixture(tmp_path, "world-relief-pilot", "world-relief-pilot-2.0")
    source = fixture.load()
    s = fixture.spacing
    result = source.sample([0, 4*s, 2*s, 4*s], [0, 0, 2*s, s], ("water_surface_m", "drainage_area_m2"))
    assert np.isnan(result["water_surface_m"][:2]).all()
    np.testing.assert_allclose(result["water_surface_m"][2:], [26, 19])
    assert source.vectors("rivers")[0]["drainage_area_m2"] == 2e6
    assert any("potential water" in note for note in source.info.derivations)
    assert source.info.declared_generated == fixture.manifest["declared_generated"]


def test_world_map_validation_and_mapping(tmp_path):
    fixture = Fixture(tmp_path, "world-map-product", "world-map-product-v1")
    fixture.manifest["status_codes"] = {str(i): i for i in range(6)}
    fixture.save()
    assert fixture.load().sample(0, 0)["status"] == ms.LAND
    fixture.manifest["ready"] = False
    fixture.save()
    with pytest.raises(ms.MapSourceError, match="ready"):
        fixture.load()
    fixture.manifest["ready"] = True
    fixture.manifest["layers"]["elevation_m"]["dtype"] = "float64"
    fixture.save()
    with pytest.raises(ms.MapSourceError, match="dtype"):
        fixture.load()


def test_duplicate_vector_ids_rejected(tmp_path):
    fixture = Fixture(tmp_path, "world-map-product", "world-map-product-v1")
    filename = fixture.path / "rivers.json"
    value = json.loads(filename.read_text(encoding="utf-8"))
    value["lines"] *= 2
    fixture.write_json("rivers.json", value)
    fixture.manifest["vectors"]["rivers"]["sha256"] = digest(filename)
    fixture.save()
    with pytest.raises(ms.MapSourceError, match="Duplicate"):
        fixture.load()


def test_real_native():
    path = os.environ.get("DREAM_TERRAIN_V3_FIXTURE")
    if not path:
        pytest.skip("DREAM_TERRAIN_V3_FIXTURE is not set")
    source = ms.load_source("native-terrain-v3", path)
    result = ms.MapCatalog([source]).sample(0, 0)
    assert result["source"].item() == source.identity
    assert np.isfinite(result["elevation_m"])


def test_real_relief():
    path = Path(os.environ.get("DREAM_WORLD_RELIEF_V2_FIXTURE", str(Path(__file__).resolve().parents[1] / "artifacts/world-relief-pilot-v2")))
    if not path.is_dir():
        pytest.skip("world-relief-pilot-v2 fixture is not available")
    source = ms.load_source("world-relief-pilot", path)
    assert source.info.schema == "world-relief-pilot-2.0"
    assert source.info.world_seed == 20260903
    assert np.isfinite(ms.MapCatalog([source]).sample(0, 0)["elevation_m"])
    assert len(source.vectors("rivers")) == 3644
