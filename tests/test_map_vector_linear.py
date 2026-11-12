"""River reciprocity validation must not rescan the full vector catalog per river."""
import pytest
from app.map_source.adapters import _validate_vectors
from app.terrain_source import TerrainSourceError

class CountedList(list):
    def __iter__(self):
        self.visits += len(self)
        return super().__iter__()

def chain(n):
    rows = CountedList(dict(id=str(i), points_xz_m=[[i,0],[i+1,0]],
        downstream_id=str(i+1) if i+1<n else None,
        upstream_ids=[str(i-1)] if i else [], outlet='ocean',drainage_area_m2=1.) for i in range(n))
    rows.visits = 0
    return rows

def test_large_catalog_scanned_linearly():
    rows = chain(20000)
    assert _validate_vectors('rivers', rows) is rows
    assert rows.visits <= 6*len(rows)

@pytest.mark.parametrize('bad', ['reciprocity','missing','cycle','duplicate'])
def test_bad_topology_still_rejected(bad):
    rows = list(chain(3))
    if bad == 'reciprocity': rows[1]['upstream_ids']=[]
    elif bad == 'missing': rows[0]['downstream_id']='missing'
    elif bad == 'cycle':
        rows[2]['downstream_id']='0'; rows[0]['upstream_ids']=['2']
    else: rows[1]['id']='0'
    with pytest.raises(TerrainSourceError): _validate_vectors('rivers',rows)
